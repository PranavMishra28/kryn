#!/usr/bin/env python3
"""Exercise OpenCode's browser tool wire and dispatch with canned local inference."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread
import time

RESEARCH = Path(__file__).resolve().parents[1]
ROOT = RESEARCH.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(RESEARCH))
from native_client import BINARY, NativeServer  # noqa: E402
from run_external_patch import configuration  # noqa: E402
from ui_gateway.preflight import broker_start, stop_group  # noqa: E402
from ui_gateway.trial_config import with_ui_gateway  # noqa: E402

MODEL = "Qwen3.5-9B-6bit"
URL = "http://candidate.invalid/index.html"
ADAPTER = Path(__file__).with_name("adapter.py").resolve()
PYTHON = Path(sys.executable).resolve()
TOOLS = [("browser_browser_navigate", {"url": URL}),
         ("browser_browser_click", {"selector": "#toggle"}),
         ("browser_browser_snapshot", {})]


class FakeInference(ThreadingHTTPServer):
    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.calls = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/v1/models":
            self.send_error(404)
            return
        self._json({"object": "list", "data": [{"id": MODEL, "object": "model"}]})

    def _json(self, value):
        data = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= 2 * 1024 * 1024:
            self.send_error(413)
            return
        try:
            payload = json.loads(self.rfile.read(size))
            tools = [item["function"]["name"] for item in payload.get("tools", [])]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            self.send_error(400)
            return
        self.server.calls.append({"model": payload.get("model"), "tools": tools,
                                  "stream": payload.get("stream")})
        number = len(self.server.calls)
        if (payload.get("model") != MODEL or
                (number <= len(TOOLS) and TOOLS[number - 1][0] not in tools)):
            self.send_error(400)
            return
        if number <= len(TOOLS):
            name, arguments = TOOLS[number - 1]
            delta = {"role": "assistant", "tool_calls": [{"index": 0,
                "id": "call_kryn_browser_" + str(number), "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments)}}]}
            finish = "tool_calls"
        else:
            delta = {"role": "assistant", "content": "Browser tool call finished."}
            finish = "stop"
        chunks = [
            {"id": "chatcmpl-kryn-wire", "object": "chat.completion.chunk", "created": 0,
             "model": MODEL, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {"id": "chatcmpl-kryn-wire", "object": "chat.completion.chunk", "created": 0,
             "model": MODEL, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]},
            {"id": "chatcmpl-kryn-wire", "object": "chat.completion.chunk", "created": 0,
             "model": MODEL, "choices": [],
             "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}},
        ]
        data = b"".join(("data: " + json.dumps(chunk) + "\n\n").encode() for chunk in chunks) + b"data: [DONE]\n\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


def trial(workspace, image, arm, receipt):
    broker_child = None
    broker = None
    inference = FakeInference()
    thread = Thread(target=inference.serve_forever, daemon=True)
    thread.start()
    report = {"arm": arm, "passed": False, "synthetic_inference": True}
    try:
        broker_child, broker = broker_start(image, workspace)
        state = workspace / ".git" / ("synthetic-ui-" + arm)
        state.mkdir(mode=0o700, exist_ok=True)
        config, products, dependencies = configuration(
            workspace, state, arm, f"http://127.0.0.1:{inference.server_address[1]}/v1")
        config = with_ui_gateway(config, python=PYTHON, adapter=ADAPTER, repo=workspace,
                                 port=broker["port"], token=broker["token"])
        dependencies += [PYTHON, Path(sys.base_prefix).resolve(), ADAPTER]
        with NativeServer(workspace, config, receipt / (arm + "-native.log"),
                          background={"dependencies": dependencies,
                                      "inference_port": inference.server_address[1],
                                      "broker_port": broker["port"]}) as server:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                mcp = server.request("GET", "/api/mcp", timeout=5).get("data", [])
                if any(item.get("name") == "browser" and
                       item.get("status", {}).get("status") == "connected" for item in mcp):
                    break
                time.sleep(.25)
            else:
                raise RuntimeError("OpenCode MCP browser did not connect")
            sid = server.request("POST", "/api/session", {
                "title": "synthetic-browser-dispatch", "agent": "browse",
                "model": {"providerID": "local", "id": "qwen", "variant": "default"},
                "location": {"directory": str(workspace)}}, timeout=5)["data"]["id"]
            argv = server.background_prefix + [str(BINARY), "run", "--server", server.url,
                "--session", sid, "--agent", "browse", "--model", "local/qwen",
                "--format", "json", "--thinking"]
            cli = subprocess.run(argv, cwd=workspace, env=server.env,
                                 input=b"Open the fixed browser page.\n", capture_output=True, timeout=60)
            events = []
            for line in cli.stdout.splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            calls = [part for event in events if isinstance((part := event.get("part")), dict)
                     and part.get("type") == "tool" and part.get("tool", "").startswith("browser_")]
            report.update(cli_exit=cli.returncode, inference_calls=inference.calls,
                          browser_calls=[{"tool": part.get("tool"),
                                          "status": part.get("state", {}).get("status")}
                                         for part in calls],
                          stderr=cli.stderr.decode(errors="replace")[-500:])
            (receipt / (arm + "-events.jsonl")).write_bytes(cli.stdout[:2 * 1024 * 1024])
            observed = [(part.get("tool"), part.get("state", {}).get("status")) for part in calls]
            report["passed"] = bool(cli.returncode == 0 and len(inference.calls) >= 4 and
                                    observed == [(name, "completed") for name, _ in TOOLS] and
                                    "Activated" in calls[-1].get("state", {}).get("output", ""))
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    finally:
        inference.shutdown()
        inference.server_close()
        thread.join(timeout=3)
        if broker_child is not None:
            stop_group(broker_child)
            cleaned = subprocess.run(["docker", "ps", "-a", "--filter",
                "name=" + broker["container"], "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=10)
            report["container_cleaned"] = cleaned.returncode == 0 and not cleaned.stdout.strip()
        report["passed"] = report["passed"] and report.get("container_cleaned", False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path, help="public checkout with one index.html")
    parser.add_argument("receipt", type=Path, help="new /private/tmp receipt directory")
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    workspace = args.workspace.absolute()
    receipt = args.receipt.absolute()
    if (workspace != workspace.resolve() or not workspace.is_relative_to(Path("/private/tmp"))
            or receipt != receipt.resolve() or not receipt.is_relative_to(Path("/private/tmp"))
            or receipt.exists() or not (workspace / ".git").is_dir()
            or not (workspace / "index.html").is_file()):
        parser.error("Use a canonical public /private/tmp Git checkout and fresh receipt")
    receipt.mkdir(mode=0o700)
    results = [trial(workspace, args.image, arm, receipt) for arm in ("native", "kryn")]
    passed = all(result["passed"] for result in results)
    native_tools = results[0].get("inference_calls", [{}])[0].get("tools", [])
    kryn_tools = results[1].get("inference_calls", [{}])[0].get("tools", [])
    output = {"schema": 1, "kind": "synthetic_browser_wire_dispatch",
              "real_model_requests": 0, "protected_score": False,
              "source_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                                       text=True).strip(),
              "source_dirty": bool(subprocess.check_output(["git", "-C", str(ROOT),
                                                            "status", "--porcelain"], text=True)),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "adapter_sha256": hashlib.sha256(ADAPTER.read_bytes()).hexdigest(),
              "candidate_html_sha256": hashlib.sha256((workspace / "index.html").read_bytes()).hexdigest(),
              "browser_image": args.image,
              "full_tool_catalog_equal": native_tools == kryn_tools,
              "browser_tool_catalog_equal": [name for name in native_tools if name.startswith("browser_")] ==
                                            [name for name in kryn_tools if name.startswith("browser_")],
              "results": results, "passed": passed}
    (receipt / "result.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
