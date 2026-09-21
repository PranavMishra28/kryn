#!/usr/bin/env python3
"""Disposable oMLX protocol checks; stdlib only, literal loopback HTTP only.

No inference runs with --self-check. Real runs retain prompts, raw replies and
metrics in a new directory. Use only disposable images with --image.
"""

import argparse
import base64
import datetime as dt
import http.client
import ipaddress
import json
import mimetypes
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
import uuid


def endpoint(url):
    p = urlsplit(url)
    host = p.hostname
    if host == "localhost":
        host = "127.0.0.1"  # Never resolve a user-controlled hostname.
    try:
        valid = ipaddress.ip_address(host).is_loopback
        port = p.port or 80
    except (ValueError, TypeError):
        valid, port = False, 0
    if (p.scheme != "http" or not valid or not 0 < port < 65536
            or p.username is not None or p.password is not None
            or p.path not in ("", "/") or p.query or p.fragment):
        raise ValueError("base URL must be loopback HTTP, without credentials/path/query")
    return host, port


def save_json(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")


def memory_snapshot():
    result = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(), "platform": sys.platform}
    if sys.platform == "darwin":
        for name, command in {
            "physical_bytes": ["/usr/sbin/sysctl", "-n", "hw.memsize"],
            "swap": ["/usr/sbin/sysctl", "-n", "vm.swapusage"],
            "vm_stat": ["/usr/bin/vm_stat"],
            "memory_pressure": ["/usr/bin/memory_pressure", "-Q"],
        }.items():
            try:
                p = subprocess.run(command, capture_output=True, text=True, timeout=5)
                result[name] = {"exit_code": p.returncode, "stdout": p.stdout.strip()}
            except (OSError, subprocess.TimeoutExpired) as e:
                result[name] = {"unavailable": type(e).__name__}
    return result


class SSE:
    """Assemble fragmented OpenAI Chat Completions deltas and usage-only events."""

    def __init__(self):
        self.pending = []
        self.content = ""
        self.reasoning = ""
        self.tools = {}
        self.finish = None
        self.usage = None
        self.done = False
        self.errors = []
        self.events = 0
        self.first = {"reasoning": None, "content": None, "tool": None}

    def line(self, raw, elapsed):
        try:
            line = raw.decode("utf-8").rstrip("\r\n")
        except UnicodeDecodeError:
            self.errors.append("invalid UTF-8 in SSE")
            return
        if not line:
            if self.pending:
                self.event("\n".join(self.pending), elapsed)
                self.pending.clear()
        elif line.startswith("data:"):
            self.pending.append(line[5:].removeprefix(" "))
        elif line.startswith((":", "event:", "id:", "retry:")):
            pass
        else:
            self.errors.append("unexpected non-SSE line")

    def event(self, data, elapsed):
        if self.done:
            self.errors.append("event after [DONE]")
            return
        if data.strip() == "[DONE]":
            self.done = True
            return
        self.events += 1
        try:
            obj = json.loads(data)
            if not isinstance(obj, dict):
                raise ValueError("event is not an object")
            if obj.get("error"):
                self.errors.append(obj["error"])
            if obj.get("usage") is not None:
                self.usage = obj["usage"]
            for choice in obj.get("choices", []):
                if choice.get("index", 0) != 0:
                    self.errors.append("unexpected additional choice")
                    continue
                if choice.get("finish_reason") is not None:
                    self.finish = choice["finish_reason"]
                delta = choice.get("delta", {})
                for field, target, clock in [("content", "content", "content"),
                                              ("reasoning_content", "reasoning", "reasoning"),
                                              ("reasoning", "reasoning", "reasoning")]:
                    part = delta.get(field)
                    if part:
                        if not isinstance(part, str):
                            raise ValueError("non-string " + field)
                        setattr(self, target, getattr(self, target) + part)
                        if self.first[clock] is None:
                            self.first[clock] = round(elapsed, 6)
                for call in delta.get("tool_calls", []):
                    index = call.get("index", 0)
                    entry = self.tools.setdefault(index, {
                        "id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    if call.get("id"):
                        entry["id"] = call["id"]
                    if call.get("type"):
                        entry["type"] = call["type"]
                    for key in ("name", "arguments"):
                        entry["function"][key] += call.get("function", {}).get(key, "")
                    if self.first["tool"] is None:
                        self.first["tool"] = round(elapsed, 6)
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            self.errors.append("invalid SSE event: " + str(e))

    def result(self):
        message = {"role": "assistant", "content": self.content}
        if self.reasoning:
            message["reasoning_content"] = self.reasoning
        if self.tools:
            message["tool_calls"] = [self.tools[k] for k in sorted(self.tools)]
        usage_complete = isinstance(self.usage, dict) and all(
            type(self.usage.get(k)) is int and self.usage[k] >= 0
            for k in ("prompt_tokens", "completion_tokens", "total_tokens"))
        if usage_complete:
            usage_complete = self.usage["total_tokens"] == (
                self.usage["prompt_tokens"] + self.usage["completion_tokens"])
        return {
            "assistant": message, "usage": self.usage,
            "metrics": {
                "first_seconds": self.first, "finish_reason": self.finish,
                "done": self.done, "usage_complete": usage_complete,
                "events": self.events, "content_chars": len(self.content),
                "reasoning_chars": len(self.reasoning), "tool_calls": len(self.tools),
                "truncated": self.finish == "length", "errors": self.errors,
                "protocol_complete": bool(self.done and self.finish in
                    ("stop", "length", "tool_calls", "content_filter")
                    and usage_complete and not self.errors and not self.pending),
            },
        }


def request(base, folder, label, path, payload=None, timeout=120, cancel_after=None,
            cancel_event=None, cancel_reason=None):
    host, port = endpoint(base)
    save_json(folder / (label + ".request.json"), {
        "method": "POST" if payload is not None else "GET", "path": path, "body": payload})
    start = time.monotonic()
    budget = min(timeout, cancel_after) if cancel_after is not None else timeout
    conn = http.client.HTTPConnection(host, port, timeout=budget)
    transport = None
    response = None
    parser = SSE()
    stream = bool(payload and payload.get("stream"))
    result = {"http_status": None, "cancelled_by_probe": False, "transport_error": None}
    received = 0
    finished = threading.Event()
    event_cancelled = threading.Event()
    def watch_cancel():
        while not finished.wait(.05):
            if cancel_event.is_set():
                event_cancelled.set()
                owned_socket = transport if transport is not None else conn.sock
                if owned_socket is not None:
                    try:
                        owned_socket.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    return
    watcher = None
    with (folder / (label + ".response.raw")).open("xb") as raw:
        try:
            if cancel_event is not None:
                if cancel_event.is_set():
                    event_cancelled.set()
                    raise OSError("request cancelled before connection")
                watcher = threading.Thread(target=watch_cancel, name="protocol-owned-cancel", daemon=True)
                watcher.start()
            data = json.dumps(payload).encode() if payload is not None else None
            conn.request("POST" if payload is not None else "GET", path, body=data,
                         headers={"Content-Type": "application/json", "Accept-Encoding": "identity"})
            transport = conn.sock
            response = conn.getresponse()
            result["http_status"] = response.status
            result["headers_seconds"] = round(time.monotonic() - start, 6)
            result["content_type"] = response.getheader("Content-Type", "")
            # http.client never follows redirects or uses environment proxies.
            if stream and 200 <= response.status < 300 and "text/event-stream" in result["content_type"]:
                while True:
                    remaining = budget - (time.monotonic() - start)
                    if remaining <= 0:
                        raise TimeoutError("request deadline")
                    if transport is not None:
                        transport.settimeout(remaining)
                    line = response.readline(1024 * 1024 + 1)
                    if not line:
                        break
                    raw.write(line)
                    received += len(line)
                    if len(line) > 1024 * 1024 or received > 32 * 1024 * 1024:
                        raise ValueError("response exceeded probe byte limit")
                    parser.line(line, time.monotonic() - start)
                    if parser.done:
                        break
                if parser.pending:
                    parser.errors.append("unterminated SSE event at EOF")
                result.update(parser.result())
            else:
                body = response.read(4 * 1024 * 1024 + 1)
                raw.write(body)
                received = len(body)
                if len(body) > 4 * 1024 * 1024:
                    raise ValueError("JSON response exceeded probe byte limit")
                try:
                    result["json"] = json.loads(body)
                except (ValueError, UnicodeDecodeError):
                    result["transport_error"] = "non-JSON response"
        except (OSError, ValueError, http.client.HTTPException) as e:
            elapsed = time.monotonic() - start
            cancelled = cancel_after is not None and elapsed >= cancel_after * 0.95
            result["cancelled_by_probe"] = cancelled
            result["transport_error"] = None if cancelled else type(e).__name__ + ": " + str(e)
            if stream:
                result.update(parser.result())
        finally:
            finished.set()
            if watcher is not None:
                watcher.join(timeout=1)
            # Close the transport rather than merely abandoning the iterator.
            if transport is not None:
                try:
                    transport.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            if response is not None:
                response.close()
            conn.close()
    if cancel_event is not None:
        result["cancel_event_observed"] = event_cancelled.is_set()
        if event_cancelled.is_set():
            result["cancelled_by_probe"] = True
            result["cancel_reason"] = cancel_reason or "external cancellation event"
    result["wall_seconds"] = round(time.monotonic() - start, 6)
    result["bytes_received"] = received
    result["cancel_after_seconds"] = cancel_after
    save_json(folder / (label + ".response.json"), result)
    return result


def body(model, variant, messages, max_tokens):
    thinking = variant != "fast"
    kwargs = {"enable_thinking": thinking}
    return {
        "model": model, "messages": messages, "stream": True,
        "stream_options": {"include_usage": True}, "max_tokens": max_tokens,
        "temperature": 0.6 if thinking else 0.7, "top_p": 0.95 if thinking else 0.8,
        "top_k": 20, "min_p": 0, "presence_penalty": 0 if thinking else 1.5,
        "repetition_penalty": 1, "chat_template_kwargs": kwargs,
    }


def healthy_stream(result):
    return (result.get("http_status") == 200 and not result.get("transport_error")
            and not result.get("cancelled_by_probe")
            and result.get("metrics", {}).get("protocol_complete", False))


def compact(result):
    return {k: v for k, v in result.items() if k not in ("assistant", "json")}


def run(args, folder, cases):
    def get(label, path):
        r = request(args.base_url, folder, label, path, timeout=args.timeout)
        cases[label] = compact(r)
        cases[label]["pass"] = r["http_status"] == 200 and not r["transport_error"] and "json" in r
        return r

    def send(label, payload, cancel_after=None):
        r = request(args.base_url, folder, label, "/v1/chat/completions", payload,
                    args.timeout, cancel_after)
        cases[label] = compact(r)
        cases[label]["pass"] = healthy_stream(r)
        return r

    get("health", "/health")
    models = get("models", "/v1/models")
    ids = [m.get("id") for m in models.get("json", {}).get("data", []) if isinstance(m, dict)]
    cases["models"]["selected_model_listed"] = args.model in ids
    cases["models"]["pass"] &= args.model in ids
    if not all(c["pass"] for c in cases.values()):
        return cases
    messages = [{"role": "user", "content": "What is 17 multiplied by 19? Your entire final response must be only the integer, with no explanation, equation or formatting."}]
    variants = [args.variant] if args.mode == "stream" else ["fast", "think"]
    for variant in variants:
        label = "stream-" + variant
        r = send(label, body(args.model, variant, messages, args.max_tokens), args.cancel_after)
        answer = r.get("assistant", {}).get("content", "").strip()
        cases[label]["answer_is_323"] = answer == "323"
        cases[label]["variant"] = variant
        if args.cancel_after is not None:
            cases[label]["pass"] = r["cancelled_by_probe"]
        else:
            cases[label]["pass"] &= answer == "323" and r["metrics"]["finish_reason"] == "stop"
    if args.mode == "stream":
        return cases

    tools = [{"type": "function", "function": {
        "name": "sum_integers", "description": "Add two integers using the local test tool.",
        "parameters": {"type": "object", "properties": {"a": {"type": "integer"},
                        "b": {"type": "integer"}}, "required": ["a", "b"], "additionalProperties": False}}}]
    history = [{"role": "user", "content": "Call sum_integers exactly once with a=23 and b=19. After its result, reply with only the sum."}]
    payload = body(args.model, "think", history, args.max_tokens)
    payload.update(tools=tools, tool_choice="auto")
    first = send("tool-first", payload)
    assistant = first.get("assistant", {})
    calls = assistant.get("tool_calls", [])
    valid = len(calls) == 1
    try:
        call = calls[0]
        arguments = json.loads(call["function"]["arguments"])
        valid &= (bool(call["id"]) and call["function"]["name"] == "sum_integers"
                  and arguments == {"a": 23, "b": 19}
                  and all(type(v) is int for v in arguments.values()))
    except (IndexError, KeyError, TypeError, ValueError):
        valid = False
    cases["tool-first"]["arguments_correct"] = valid
    cases["tool-first"]["reasoning_observed"] = bool(assistant.get("reasoning_content"))
    cases["tool-first"]["pass"] &= valid and first.get("metrics", {}).get("finish_reason") == "tool_calls"
    if cases["tool-first"]["pass"]:
        # Replay the received reasoning_content verbatim, not a reconstructed think tag.
        history += [assistant, {"role": "tool", "tool_call_id": call["id"],
                    "content": json.dumps({"sum": arguments["a"] + arguments["b"]})}]
        second_payload = body(args.model, "think", history, args.max_tokens)
        second_payload.update(tools=tools, tool_choice="auto")
        second = send("tool-replay", second_payload)
        cases["tool-replay"]["reasoning_replayed_chars"] = len(assistant.get("reasoning_content", ""))
        cases["tool-replay"]["reasoning_replay_exercised"] = bool(assistant.get("reasoning_content"))
        cases["tool-replay"]["pass"] &= (second.get("assistant", {}).get("content", "").strip() == "42"
                                          and not second.get("assistant", {}).get("tool_calls")
                                          and second.get("metrics", {}).get("finish_reason") == "stop"
                                          and bool(assistant.get("reasoning_content")))
    if args.image:
        image = Path(args.image)
        mime = mimetypes.guess_type(image.name)[0]
        if mime not in ("image/png", "image/jpeg", "image/webp") or image.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("image must be PNG/JPEG/WebP, at most 8 MiB")
        with image.open("rb") as f:
            data = f.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise ValueError("image grew beyond 8 MiB")
        parts = [{"type": "text", "text": "Read the visible text and describe the positions of the main objects. Do not invent unreadable details."},
                 {"type": "image_url", "image_url": {"url": "data:" + mime + ";base64," + base64.b64encode(data).decode()}}]
        send("vision", body(args.model, "think", [{"role": "user", "content": parts}], args.max_tokens))
        cases["vision"]["semantic_result"] = "REQUIRES_IMAGE_GROUND_TRUTH_REVIEW"
    if args.extra_checks:
        malformed = send("malformed", {"model": args.model, "messages": "invalid", "stream": True})
        cases["malformed"]["pass"] = malformed["http_status"] in (400, 422)
        long_prompt = [{"role": "user", "content": "Print all integers from 1 through 100, separated by spaces."}]
        limited = send("max-output", body(args.model, "fast", long_prompt, 4))
        cases["max-output"]["pass"] &= (limited.get("metrics", {}).get("finish_reason") == "length"
                                         and 0 < (limited.get("usage") or {}).get("completion_tokens", 0) <= 4)
        cancelled = send("cancel", body(args.model, "think", long_prompt, 2048), 2.0)
        cases["cancel"]["pass"] = cancelled["cancelled_by_probe"]
        recovery = send("after-cancel", body(args.model, "fast", messages, args.max_tokens))
        cases["after-cancel"]["pass"] &= recovery.get("assistant", {}).get("content", "").strip() == "323"
    return cases


def self_check():
    import tempfile
    from unittest.mock import patch
    assert endpoint("http://127.0.0.1:8000") == ("127.0.0.1", 8000)
    assert endpoint("http://[::1]:8000") == ("::1", 8000)
    for bad in ["https://api.openai.com", "http://example.com", "http://127.0.0.1@evil.test",
                "http://127.0.0.1/v1", "http://127.0.0.1?secret=x", "http://0.0.0.0"]:
        try:
            endpoint(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("accepted nonlocal or ambiguous endpoint")
    p = SSE()
    events = [
        {"choices": [{"index": 0, "delta": {"reasoning_content": "Compute."}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "type": "function",
            "function": {"name": "sum_integers", "arguments": '{"a":23,'}}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '"b":19}'}}]}, "finish_reason": "tool_calls"}]},
        {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}},
    ]
    p.line(b": keepalive\n", 0)
    for i, event in enumerate(events):
        p.line(("data: " + json.dumps(event) + "\r\n").encode(), i + 0.1)
        p.line(b"\r\n", i + 0.2)
    p.line(b"data: [DONE]\n", 5)
    p.line(b"\n", 5)
    r = p.result()
    assert r["metrics"]["protocol_complete"]
    assert r["assistant"]["reasoning_content"] == "Compute."
    assert json.loads(r["assistant"]["tool_calls"][0]["function"]["arguments"]) == {"a": 23, "b": 19}
    assert r["metrics"]["first_seconds"]["reasoning"] == 0.2
    for tail in [b'data: {broken}\n\n', b'data: {"error":{"message":"failed"}}\n\ndata: [DONE]\n\n']:
        q = SSE()
        for line in tail.splitlines(keepends=True):
            q.line(line, 0)
        assert q.errors and not q.result()["metrics"]["protocol_complete"]
    assert not SSE().result()["metrics"]["protocol_complete"]
    fast = body("test", "fast", [], 8)
    assert fast["chat_template_kwargs"]["enable_thinking"] is False
    assert "reasoning_effort" not in fast["chat_template_kwargs"]
    assert len({json.dumps(body("test", v, [], 8)["chat_template_kwargs"], sort_keys=True)
                for v in ("fast", "think")}) == 2
    # In-memory transport only: no listener, runtime or network connection.
    stopped = threading.Event()
    class FakeSocket:
        def shutdown(self, *_): stopped.set()
        def settimeout(self, *_): pass
    class FakeResponse:
        status = 200
        def __init__(self, block):
            self.block = block
            event = {"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}],
                     "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
            self.lines = iter([("data: " + json.dumps(event) + "\n").encode(), b"\n", b"data: [DONE]\n", b"\n"])
        def getheader(self, *_): return "text/event-stream"
        def readline(self, *_):
            if self.block:
                assert stopped.wait(2), "owned transport was not cancelled"
                return b""
            return next(self.lines, b"")
        def close(self): pass
    class FakeConnection:
        block = False
        sent = 0
        def __init__(self, *_args, **_kwargs): self.sock = FakeSocket()
        def request(self, *_args, **_kwargs): type(self).sent += 1
        def getresponse(self): return FakeResponse(self.block)
        def close(self): pass
    with tempfile.TemporaryDirectory() as tmp, patch.object(http.client, "HTTPConnection", FakeConnection):
        folder, cancel = Path(tmp), threading.Event()
        normal = request("http://127.0.0.1", folder, "normal", "/test", {"stream": True}, cancel_event=cancel)
        assert healthy_stream(normal) and not normal["cancel_event_observed"]
        assert not any(t.name == "protocol-owned-cancel" for t in threading.enumerate())
        cancel.set()  # Completion has already joined its watcher.
        sent = FakeConnection.sent
        early = request("http://127.0.0.1", folder, "early", "/test", {"stream": True}, cancel_event=cancel)
        assert early["cancelled_by_probe"] and FakeConnection.sent == sent
        cancel.clear(); stopped.clear(); FakeConnection.block = True
        timer = threading.Timer(.02, cancel.set)
        timer.start()
        aborted = request("http://127.0.0.1", folder, "aborted", "/test", {"stream": True},
                          cancel_event=cancel, cancel_reason="offline guard")
        timer.join()
        assert aborted["cancelled_by_probe"] and aborted["cancel_reason"] == "offline guard"
        assert not healthy_stream(aborted) and not aborted["metrics"]["protocol_complete"]
        assert not any(t.name == "protocol-owned-cancel" for t in threading.enumerate())
        FakeConnection.block = False
        default = request("http://127.0.0.1", folder, "default", "/test", {"stream": True})
        assert healthy_stream(default) and "cancel_event_observed" not in default
    print("Offline self-check passed: endpoint restrictions, SSE/errors/tools, variants, owned cancellation and watcher cleanup.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-check", action="store_true")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--model")
    p.add_argument("--runs-dir", type=Path)
    p.add_argument("--mode", choices=("smoke", "stream"), default="smoke")
    p.add_argument("--variant", choices=("fast", "think"), default="fast")
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--cancel-after", type=float, help="stream mode only; close transport after this deadline")
    p.add_argument("--extra-checks", action="store_true", help="smoke mode: malformed, token cap, cancel and recovery")
    p.add_argument("--image", help="smoke mode: disposable PNG/JPEG/WebP; raw request retains its bytes")
    args = p.parse_args()
    if args.self_check:
        self_check()
        return 0
    try:
        endpoint(args.base_url)
        if not args.model or not args.runs_dir:
            raise ValueError("--model and --runs-dir are required")
        if not 1 <= args.max_tokens <= 16384 or not 0 < args.timeout <= 3600:
            raise ValueError("max-tokens must be 1..16384; timeout must be >0 and <=3600")
        if args.cancel_after is not None and (args.mode != "stream" or not 0 < args.cancel_after < args.timeout):
            raise ValueError("--cancel-after requires stream mode and 0 < cancel-after < timeout")
        if args.mode == "stream" and (args.extra_checks or args.image):
            raise ValueError("--extra-checks and --image require smoke mode")
    except ValueError as e:
        p.error(str(e))
    args.runs_dir.mkdir(parents=True, exist_ok=True)
    folder = args.runs_dir / ("protocol-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8])
    folder.mkdir()
    report = {"schema_version": 1, "probe_revision": 2, "base_url": args.base_url, "model": args.model,
              "mode": args.mode, "protocol_pass": False, "memory_before": memory_snapshot(),
              "cases": {}, "limitations": [
                  "Vision semantics need external image ground truth.",
                  "Client cancellation plus recovery does not alone prove immediate GPU quiescence.",
                  "Request variant differences do not prove the server honored every setting.",
                  "This probe does not establish long-context fit or task-level coding quality."]}
    try:
        run(args, folder, report["cases"])
        report["protocol_pass"] = bool(report["cases"]) and all(c.get("pass") for c in report["cases"].values())
    except Exception as e:
        report["fatal_error"] = type(e).__name__ + ": " + str(e)
    finally:
        report["memory_after"] = memory_snapshot()
        save_json(folder / "metrics.json", report)
    print(json.dumps({"protocol_pass": report["protocol_pass"], "metrics": str((folder / "metrics.json").resolve())}))
    return 0 if report["protocol_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
