#!/usr/bin/env python3
"""Narrow local MCP browser adapter. Runs inside the candidate read boundary."""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import sys
from urllib.parse import parse_qsl, urlsplit

URL = "http://candidate.invalid/index.html"
MAX_RPC = 65536
MAX_REPLY = 3_000_000
TOOLS = [
    {"name": "browser_navigate", "description": "Open the fixed candidate page, optionally with one bounded q query.",
     "inputSchema": {"type": "object", "properties": {"url": {"type": "string", "maxLength": 256}},
                     "required": ["url"], "additionalProperties": False}},
    {"name": "browser_snapshot", "description": "Read the current page's accessible structure.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "browser_click", "description": "Click one element on the candidate page by CSS selector.",
     "inputSchema": {"type": "object", "properties": {"selector": {"type": "string", "maxLength": 128}},
                     "required": ["selector"], "additionalProperties": False}},
    {"name": "browser_fill_form", "description": "Fill one visible form field on the candidate page.",
     "inputSchema": {"type": "object", "properties": {"selector": {"type": "string", "maxLength": 128},
                                                  "value": {"type": "string", "maxLength": 256}},
                     "required": ["selector", "value"], "additionalProperties": False}},
    {"name": "browser_navigate_back", "description": "Return to the previous candidate-page history entry.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "browser_press_key", "description": "Press one navigation key in the candidate page.",
     "inputSchema": {"type": "object", "properties": {"key": {"type": "string", "enum":
                     ["ArrowLeft", "ArrowRight", "Home", "End", "Tab", "Enter", "Space"]}},
                     "required": ["key"], "additionalProperties": False}},
    {"name": "browser_take_screenshot", "description": "Capture the candidate page as a bounded PNG.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "browser_resize", "description": "Resize the candidate browser viewport.",
     "inputSchema": {"type": "object", "properties": {"width": {"type": "integer", "minimum": 320, "maximum": 1440},
                     "height": {"type": "integer", "minimum": 240, "maximum": 1200}},
                     "required": ["width", "height"], "additionalProperties": False}},
]


def broker_call(port, token, command):
    with socket.create_connection(("127.0.0.1", port), timeout=5) as connection:
        connection.settimeout(10)
        request = json.dumps({"token": token, **command}, separators=(",", ":")).encode() + b"\n"
        if len(request) > 1_500_000:
            raise ValueError("browser request limit")
        connection.sendall(request)
        data = bytearray()
        while b"\n" not in data:
            chunk = connection.recv(min(65536, MAX_REPLY + 1 - len(data)))
            if not chunk or len(data) + len(chunk) > MAX_REPLY:
                raise ValueError("browser response limit")
            data.extend(chunk)
        line, remainder = bytes(data).split(b"\n", 1)
        if remainder:
            raise ValueError("browser response framing")
        response = json.loads(line)
        if not isinstance(response, dict) or type(response.get("ok")) is not bool:
            raise ValueError("browser response schema")
        return response


def exact(value, keys):
    return isinstance(value, dict) and set(value) == set(keys)


def candidate_query(url):
    if not isinstance(url, str) or len(url) > 256:
        return None
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if (parsed.scheme != "http" or parsed.netloc != "candidate.invalid" or
            parsed.path != "/index.html" or parsed.fragment or
            parsed.geturl() != url):
        return None
    if not parsed.query:
        return "" if url == URL else None
    if re.search(r"%(?![0-9A-Fa-f]{2})", parsed.query):
        return None
    try:
        query = parse_qsl(parsed.query, strict_parsing=True, keep_blank_values=True,
                          errors="strict")
    except ValueError:
        return None
    if (len(query) != 1 or query[0][0] != "q" or not 1 <= len(query[0][1]) <= 128 or
            any(ord(character) < 32 or ord(character) == 127 for character in query[0][1])):
        return None
    return query[0][1]


def call_tool(name, arguments, port, token):
    if name == "browser_navigate" and exact(arguments, ("url",)) and (query := candidate_query(arguments["url"])) is not None:
        command = {"op": "open", "query": query}
    elif name == "browser_snapshot" and exact(arguments, ()):
        command = {"op": "snapshot"}
    elif name == "browser_click" and exact(arguments, ("selector",)) and isinstance(arguments["selector"], str) and len(arguments["selector"]) <= 128:
        command = {"op": "click", "selector": arguments["selector"]}
    elif name == "browser_fill_form" and exact(arguments, ("selector", "value")) and isinstance(arguments["selector"], str) and isinstance(arguments["value"], str) and len(arguments["selector"]) <= 128 and len(arguments["value"]) <= 256:
        command = {"op": "fill", "selector": arguments["selector"], "value": arguments["value"]}
    elif name == "browser_navigate_back" and exact(arguments, ()):
        command = {"op": "back"}
    elif name == "browser_press_key" and exact(arguments, ("key",)) and arguments["key"] in {"ArrowLeft", "ArrowRight", "Home", "End", "Tab", "Enter", "Space"}:
        command = {"op": "key", "key": arguments["key"]}
    elif name == "browser_take_screenshot" and exact(arguments, ()):
        command = {"op": "screenshot"}
    elif name == "browser_resize" and exact(arguments, ("width", "height")) and type(arguments["width"]) is int and type(arguments["height"]) is int and 320 <= arguments["width"] <= 1440 and 240 <= arguments["height"] <= 1200:
        command = {"op": "resize", "width": arguments["width"], "height": arguments["height"]}
    else:
        return {"content": [{"type": "text", "text": "UNSUPPORTED_ACTION"}], "isError": True}
    try:
        response = broker_call(port, token, command)
        if not response["ok"]:
            return {"content": [{"type": "text", "text": response.get("error", "BROWSER_FAILURE")}], "isError": True}
        if "image_b64" in response:
            value = response["image_b64"]
            if not isinstance(value, str) or len(value) > 2_800_000:
                raise ValueError("screenshot limit")
            return {"content": [{"type": "image", "data": value, "mimeType": "image/png"}]}
        value = response.get("text")
        if not isinstance(value, str) or len(value) > 16384:
            raise ValueError("snapshot limit")
        return {"content": [{"type": "text", "text": value}]}
    except (OSError, ValueError, TimeoutError):
        return {"content": [{"type": "text", "text": "BROWSER_FAILURE"}], "isError": True}


def serve(repo, port, token):
    root = Path(repo).absolute()
    if root != root.resolve() or any(path.is_symlink() for path in (root, *root.parents)):
        raise ValueError("candidate checkout must be canonical")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        while raw := sys.stdin.buffer.readline(MAX_RPC + 1):
            if len(raw) > MAX_RPC or not raw.endswith(b"\n"):
                raise ValueError("MCP input limit")
            request = None
            try:
                request = json.loads(raw)
                if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
                    raise ValueError("MCP envelope")
                method = request.get("method")
                if method == "notifications/initialized":
                    continue
                if method == "initialize":
                    result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                              "serverInfo": {"name": "kryn-ui-gateway", "version": "0.0.0"}}
                elif method == "tools/list":
                    result = {"tools": TOOLS}
                elif method == "tools/call":
                    params = request.get("params")
                    if (not isinstance(params, dict) or
                            set(params) not in ({"name", "arguments"},
                                                {"name", "arguments", "_meta"}) or
                            ("_meta" in params and not isinstance(params["_meta"], dict)) or
                            not isinstance(params["name"], str)):
                        raise ValueError("MCP tool call schema")
                    result = call_tool(params["name"], params["arguments"], port, token)
                else:
                    raise ValueError("unsupported MCP method")
                reply = {"jsonrpc": "2.0", "id": request["id"], "result": result}
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                reply = {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None,
                         "error": {"code": -32600, "message": "Invalid request"}}
            sys.stdout.write(json.dumps(reply, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    finally:
        os.close(root_fd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535 or len(args.token) != 48 or not all(c in "0123456789abcdef" for c in args.token):
        parser.error("invalid broker address or token")
    serve(args.repo, args.port, args.token)
