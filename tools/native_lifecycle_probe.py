#!/usr/bin/env python3
"""DRAFT: serial native-API task-11 stimulus; --self-check is entirely offline.

Historical source only: its plugin admission and variants predate the current stack;
it is excluded from the wheel and cannot qualify a current release.
A real run sends local inference and temporarily stops the owned oMLX app server.
Root must review this draft before execution. No candidate code is edited.
"""
import argparse
from contextlib import contextmanager
import copy
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
sys.dont_write_bytecode = True
from native_client import BINARY, MODEL_ID, NativeServer, environment, owned_config
from localai import OMLX, RUNTIME, inventory, validate_owned_config
from context_probe import resources, summarize_resources
from run_native_trial import NativeResourceGuard

TOOLS = Path(__file__).resolve().parent
APP = OMLX.parents[2].resolve()
CONTROL = Path.home() / "Library/Application Support/oMLX/control.sock"
DENY_TOOLS = [{"action": "*", "resource": "*", "effect": "deny"}]


def host_telemetry_ready(sample):
    return (type(sample.get("swap_used_bytes")) is int and sample["swap_used_bytes"] >= 0
            and sample.get("pressure_level") in {1, 2, 4, 6})


class LifecycleResourceGuard(NativeResourceGuard):
    """Reuse the native trial sampler; expected outage has real host-only telemetry."""
    def __init__(self, folder, samples, baseline_swap, expected_pid, host_only, on_abort):
        super().__init__(folder, samples)
        self.guard.baseline_swap, self.guard.pid = baseline_swap, expected_pid
        self.host_only, self.on_abort = host_only, on_abort
        self.armed = self.signalled = False
        self.expect_absent = False
        self.signal_lock = threading.Lock()

    def sample(self):
        try:
            if not self.host_only:
                super().sample()
                return
            try:
                item = resources(RUNTIME)
            except Exception as error:
                item = {"unavailable": type(error).__name__}
            item["runtime_telemetry_required"] = False
            item["expected_runtime_absent"] = self.expect_absent
            guard = self.guard
            if not guard.reason:
                if not host_telemetry_ready(item):
                    guard.reason = "host telemetry missing during intentional runtime transition/outage"
                elif self.expect_absent and item.get("listener_processes"):
                    guard.reason = "runtime listener returned during declared outage"
                else:
                    swap, level = item["swap_used_bytes"], item["pressure_level"]
                    if guard.baseline_swap is None:
                        guard.baseline_swap = swap
                    guard.warnings = guard.warnings + 1 if level & 2 else 0
                    if level & 4:
                        guard.reason = "critical host memory pressure"
                    elif swap - guard.baseline_swap > guard.max_swap_growth:
                        guard.reason = "whole-probe swap growth exceeded the declared budget"
                    elif guard.warnings >= guard.warning_samples:
                        guard.reason = "sustained host memory warning"
            if guard.reason:
                item["guard_reason"] = guard.reason
                self.cancel.set()
            self.samples.append(item)
            try:
                self.log.write(json.dumps(item) + "\n")
                self.log.flush()
            except Exception:
                guard.reason = "resource evidence write failed"
                self.cancel.set()
                raise
        finally:
            self.signal_if_cancelled()

    def signal_if_cancelled(self):
        with self.signal_lock:
            if self.armed and self.cancel.is_set() and not self.signalled:
                self.signalled, self.armed = True, False
                self.on_abort(self.guard.reason)
                # Disarm cannot return until this one own-process signal is sent.
                # The main thread then performs verified owned-session cleanup.
                os.kill(os.getpid(), signal.SIGTERM)

    def arm(self):
        with self.signal_lock:
            self.armed = True
        self.signal_if_cancelled()

    def disarm(self):
        with self.signal_lock:
            self.armed = False

    def is_closed(self):
        return self.log.closed and (self.watcher is None or not self.watcher.is_alive())

    def finish(self):
        self.disarm()  # Never interrupt cleanup after synchronized disarm returns.
        self.close()
        result = summarize_resources(self.samples)
        result.update(host_only=self.host_only, baseline_swap_bytes=self.guard.baseline_swap,
                      guard_reason=self.guard.reason, cancellation_signalled=self.signalled)
        if self.host_only:
            # Preserve the original process-telemetry result; absence is not fabricated success.
            result["required_telemetry_complete"] = bool(self.samples) and all(map(host_telemetry_ready, self.samples))
        else:
            result["required_telemetry_complete"] = result["telemetry_complete"]
        result["whole_probe_swap_peak_growth_bytes"] = (
            result["swap_peak_bytes"] - self.guard.baseline_swap
            if result["swap_peak_bytes"] is not None and self.guard.baseline_swap is not None else None)
        result["clean"] = bool(result["required_telemetry_complete"]
            and not result["warning_or_critical_observed"] and not self.cancel.is_set()
            and result["whole_probe_swap_peak_growth_bytes"] <= self.guard.max_swap_growth)
        return result


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def save(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")


def port_open():
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", 8000)) == 0


def runtime_status():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(RUNTIME + "/api/status", timeout=3) as response:
        raw = json.load(response)
    return {k: raw.get(k) for k in ("status", "version", "default_model", "active_requests", "waiting_requests")}


def app_status():
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(3)
        s.connect(str(CONTROL))
        s.sendall(b'{"command":"status"}\n')
        raw = b""
        while b"\n" not in raw and len(raw) < 16384:
            chunk = s.recv(4096)
            if not chunk:
                break
            raw += chunk
    parsed = json.loads(raw.split(b"\n", 1)[0])
    return {k: parsed.get(k) for k in ("ok", "state", "port", "pid")}


def control_matches(app, listener_pid, expected_pid=None):
    return (app.get("ok") is True and app.get("state") == "running" and app.get("port") == 8000
            and type(app.get("pid")) is int and app["pid"] == listener_pid
            and (expected_pid is None or listener_pid == expected_pid))


def runtime_identity(expected_pid=None):
    p = subprocess.run(["/usr/sbin/lsof", "-nP", "-a", "-iTCP:8000", "-sTCP:LISTEN", "-Fpu"],
                       capture_output=True, text=True, timeout=5, check=True)
    rows = []
    for line in p.stdout.splitlines():
        if line.startswith("p"):
            rows.append({"pid": int(line[1:])})
        elif line.startswith("u") and rows:
            rows[-1]["uid"] = int(line[1:])
    require(len(rows) == 1, "Port 8000 must have exactly one listener")
    row = rows[0]
    require(row.get("uid") == os.getuid() and (expected_pid is None or row["pid"] == expected_pid),
            "Runtime PID/owner differs from the operator's identity")
    lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    fn = lib.proc_pidpath
    fn.argtypes, fn.restype = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32], ctypes.c_int
    buf = ctypes.create_string_buffer(4096)
    require(fn(row["pid"], buf, len(buf)) > 0, "Cannot verify runtime executable; do not stop it")
    executable = Path(buf.value.decode()).resolve()
    require(executable.is_relative_to(APP), "Listener executable is outside the owned oMLX bundle")
    row.update(executable=str(executable), app=app_status(), status=runtime_status())
    require(control_matches(row["app"], row["pid"], expected_pid),
            "Control PID, listener PID and operator PID must identify the same owned server")
    require(row["status"].get("default_model") == MODEL_ID, "Unexpected model runtime")
    require(row["status"].get("active_requests") == 0 and row["status"].get("waiting_requests") == 0,
            "Runtime is not idle")
    return row


def messages(exported):
    return exported["data"]["messages"]


def text_of(items):
    return "".join(p.get("text", "") for m in items if m.get("type") == "assistant"
                   for p in m.get("content", []) if p.get("type") == "text")


def answer_evidence(text, expected):
    """Grade literal content separately from format; never repair or rewrite output."""
    result = {"raw_text": text, "exact_format": False, "content_ok": False}
    if isinstance(expected, dict):
        def pairs(items):
            require(len({k for k, _ in items}) == len(items), "Duplicate JSON keys")
            return dict(items)
        def constant(value):
            raise ValueError("Non-JSON constant: " + value)
        decoder = json.JSONDecoder(object_pairs_hook=pairs, parse_constant=constant)
        objects, cursor = [], 0
        try:
            while (start := text.find("{", cursor)) != -1:
                value, end = decoder.raw_decode(text, start)
                objects.append((start, end, value))
                cursor = end
            if len(objects) == 1:
                start, end, value = objects[0]
                result.update(literal=text[start:end], span=[start, end])
                # Canonical comparison distinguishes 731 from 731.0 and True from 1.
                result["content_ok"] = json.dumps(value, sort_keys=True) == json.dumps(expected, sort_keys=True)
                result["exact_format"] = text.strip() == text[start:end]
        except (ValueError, RuntimeError):
            pass
    else:
        family = next((prefix for prefix in ("ACK_", "REVIEW_", "RECOVERY_") if expected.startswith(prefix)), None)
        pattern = re.escape(family) + r"[A-Za-z0-9_]+" if family else re.escape(expected)
        tokens = re.findall(r"(?<![A-Za-z0-9_])(?:" + pattern + r")(?![A-Za-z0-9_])", text)
        result["content_ok"] = tokens == [expected]
        if re.fullmatch(r"(?:RECOVERY_)?[a-f0-9]{32}", expected):
            nonces = re.findall(r"(?<![A-Za-z0-9])[a-fA-F0-9]{32}(?![A-Za-z0-9])", text)
            result["content_ok"] &= nonces == [expected.removeprefix("RECOVERY_")]
        result["exact_format"] = text.strip() == expected
    return result


def completion_checks(exported, items, allow_tools=False):
    assistants = [m for m in items if m.get("type") == "assistant"]
    tools = [p for m in assistants for p in m.get("content", []) if p.get("type") == "tool"]
    return {"native_succeeded": exported["data"]["info"].get("outcome") == "succeeded",
        "terminal_stop": bool(assistants) and assistants[-1].get("finish") == "stop"
            and bool(assistants[-1].get("time", {}).get("completed")),
        "no_new_errors": not any(m.get("error") for m in items),
        "tool_policy": all(p.get("state", {}).get("status") == "completed" for p in tools) if allow_tools else not tools}


def foreground_checks(call, child_export):
    """Native subagent defaults to foreground; completed result and ordering must agree."""
    state, info = call.get("state", {}), child_export["data"]["info"]
    inputs, metadata = state.get("input", {}), state.get("metadata", {})
    assistants = [m for m in messages(child_export) if m.get("type") == "assistant"]
    times = [call.get("time", {}).get("ran"), info.get("time", {}).get("created"),
             assistants[-1].get("time", {}).get("completed") if assistants else None,
             info.get("time", {}).get("idle"), call.get("time", {}).get("completed")]
    return {"foreground": "background" not in inputs or inputs["background"] is False,
        "completed_child_result": state.get("status") == "completed" and metadata.get("status") == "completed"
            and bool(info.get("id")) and metadata.get("sessionID") == info["id"],
        "child_finished_before_tool_return": all(type(t) is int and t > 0 for t in times)
            and times == sorted(times)}


def native_exited(server):
    return server is None or server.process is None or server.process.poll() is not None


def wait_runtime_idle(timeout=30):
    deadline, quiet = time.monotonic() + timeout, 0
    while time.monotonic() < deadline:
        state = runtime_status()
        quiet = quiet + 1 if state.get("active_requests") == state.get("waiting_requests") == 0 else 0
        if quiet >= 3:
            return state
        time.sleep(0.5)
    raise RuntimeError("Runtime did not become idle within cleanup deadline")


def fixture_hashes(workspace):
    return {str(p.relative_to(workspace)): "SYMLINK" if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest()
            for p in workspace.rglob("*") if ".git" not in p.relative_to(workspace).parts and (p.is_file() or p.is_symlink())}


def transport_error(value):
    if isinstance(value, dict) and value.get("type") == "provider.transport":
        return True
    return bool(re.search(r"ECONNREFUSED|connection refused|unable to connect|failed to connect|fetch failed|network error|connection error",
                          json.dumps(value), re.I))


def no_generated_output(items):
    return not any(p.get("type") == "tool" or p.get("text", "").strip()
        for m in items if m.get("type") == "assistant" for p in m.get("content", []))


def routes_ok(rows):
    requests = [r for r in rows if r.get("event") in ("model.request", "http.request")]
    return bool(requests) and all(r.get("ok") is True and r.get("model", {}).get("providerID") == "local"
        and r.get("model", {}).get("id") == "qwen"
        and re.fullmatch(r"http://127\.0\.0\.1:8000/v1(?:/[A-Za-z0-9_/-]+)?", r.get("destination", ""))
        for r in requests) and not any(r.get("ok") is False or r.get("event") == "unexpected.websocket" for r in rows)


class APIError(Exception):
    def __init__(self, record):
        self.record = record
        super().__init__(record.get("error_type", "native API error"))


class Probe:
    def __init__(self, args, folder, report):
        self.args, self.folder, self.report = args, folder, report
        self.count, self.sessions = 0, []
        self.initial_titles, self.pending_titles, self.settled_titles = {}, set(), {}
        self.audit_path = folder / "inference.jsonl"
        self.before_cleanup = lambda: None

    def api(self, server, method, path, body=None, timeout=20):
        self.count += 1
        row = {"method": method, "path": path, "body": body}
        try:
            result = server.request(method, path, body, timeout)
            row["response"] = result
        except urllib.error.HTTPError as e:
            raw = e.read(65536)
            try:
                detail = json.loads(raw)
            except ValueError:
                detail = {"unparsed_error_bytes": len(raw)}
            row.update(http_status=e.code, error_type="HTTPError", error=detail)
        except (OSError, TimeoutError) as e:
            row.update(error_type=type(e).__name__, timed_out=isinstance(e, TimeoutError))
        save(self.folder / f"api-{self.count:04}.json", row)
        if "error_type" in row:
            raise APIError(row)
        return result

    def audit(self):
        if not self.audit_path.is_file():
            return []
        return [json.loads(line) for line in self.audit_path.read_text().splitlines() if line.strip()]

    def kind_seen(self, start, sid, kind):
        rows = self.audit()[start:]
        require(not any(r.get("ok") is False or r.get("event") == "unexpected.websocket" for r in rows),
                "Hard failure: routing audit rejected a destination")
        return any(r.get("event") == "http.request" and r.get("sessionID") == sid and r.get("kind") == kind for r in rows)

    def record(self, label, checks, unavailable=False):
        status = "PASS" if all(checks.values()) else "PARTIAL" if unavailable else "FAIL"
        self.report["cases"][label] = {"status": status, "checks": checks, "api_record_count": self.count}
        print(json.dumps({"stage": label, "status": status}), flush=True)
        return status == "PASS"

    def create(self, server, agent="plan", title=None):
        permissions = DENY_TOOLS + ([{"action": "subagent", "resource": "reviewer", "effect": "allow"}] if agent == "build" else [])
        body = {"agent": agent, "model": {"providerID": "local", "id": "qwen", "variant": self.args.variant},
                "location": {"directory": str(self.args.run / "workspace")}, "permissions": permissions}
        if title is not None:
            body["title"] = title
        sid = self.api(server, "POST", "/api/session", body)["data"]["id"]
        self.sessions.append(sid)
        initial = self.export(server, sid)["data"]["info"].get("title")
        self.report.setdefault("initial_titles", {})[sid] = initial
        if title is None:
            self.initial_titles[sid] = initial
        return sid

    def export(self, server, sid, timeout=20):
        result = self.api(server, "GET", f"/api/experimental/session/{sid}/export", timeout=timeout)
        info = result["data"]["info"]
        require(Path(info["location"]["directory"]).resolve() == self.args.run / "workspace", "Session escaped fixture directory")
        require(info.get("model", {}).get("providerID") == "local" and info.get("model", {}).get("id") == "qwen", "Session model is not local/qwen")
        return result

    def action(self, server, sid, action, body, timeout):
        before = self.export(server, sid)
        seen = {m["id"] for m in messages(before)}
        start = len(self.audit())
        if action == "prompt" and sid in self.initial_titles and sid not in self.settled_titles:
            self.pending_titles.add(sid)
        self.api(server, "POST", f"/api/session/{sid}/{action}", body)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                self.api(server, "POST", f"/api/experimental/session/{sid}/wait", timeout=min(20, max(1, deadline - time.monotonic())))
            except APIError as e:
                if e.record.get("timed_out"):
                    continue
                raise
            exported = self.export(server, sid)
            delta = [m for m in messages(exported) if m["id"] not in seen]
            if any(m.get("type") == "assistant" and m.get("time", {}).get("completed")
                   or m.get("type") == "compaction" and m.get("status") in ("completed", "failed") for m in delta):
                return exported, delta, start
            time.sleep(0.2)
        self.report["cases"][f"timeout-{action}-{sid}"] = {"status": "PARTIAL", "reason": "bounded wait exhausted; owned-session cleanup required, not an outage pass"}
        raise RuntimeError("Native stage timed out")

    def grade(self, label, text, expected):
        evidence = answer_evidence(text, expected)
        self.report.setdefault("answers", {})[label] = evidence
        return evidence["content_ok"]

    def turn(self, server, sid, prompt, expected, label, allow_tools=False):
        self.idle(server)
        exported, delta, start = self.action(server, sid, "prompt", {"text": prompt}, self.args.timeout)
        passed = self.record(label, {**completion_checks(exported, delta, allow_tools),
            "literal_content": self.grade(label, text_of(delta), expected),
            "local_primary_observed": self.kind_seen(start, sid, "primary")})
        self.idle(server)
        return exported, passed

    def idle(self, server, timeout=30):
        deadline, quiet, previous_audit = time.monotonic() + timeout, 0, None
        while time.monotonic() < deadline:
            active = self.api(server, "GET", "/api/session/active", timeout=min(3, deadline - time.monotonic()))["data"]
            state = runtime_status()
            titles = {}
            for sid in self.pending_titles:
                remaining = deadline - time.monotonic()
                require(remaining > 0, "Detached title helper idle deadline expired")
                title = self.export(server, sid, timeout=min(3, remaining))["data"]["info"].get("title")
                if title and title != self.initial_titles[sid] and self.kind_seen(0, sid, "title"):
                    titles[sid] = {"initial": self.initial_titles[sid], "generated": title, "local_title_observed": True}
            current_audit = len(self.audit())
            settled = (not active and state.get("active_requests") == state.get("waiting_requests") == 0
                       and titles.keys() == self.pending_titles)
            quiet = quiet + 1 if settled and current_audit == previous_audit else 0
            if quiet >= 2:
                self.settled_titles.update(titles)
                self.pending_titles.clear()
                return
            previous_audit = current_audit
            time.sleep(0.5)
        raise RuntimeError("Foreground, runtime or detached title helper did not settle")

    def cancel_owned(self, server):
        """Interrupt and await only this probe's sessions; closing the server settles detached helpers."""
        errors, deadline = [], time.monotonic() + 30
        def request(method, path, wait=False):
            remaining = deadline - time.monotonic()
            require(remaining > 0, "Owned-session cleanup deadline expired")
            return self.api(server, method, path, timeout=min(5 if wait else 3, remaining))
        # Include verified children if a failed parent turn never returned their IDs.
        for sid in list(self.sessions):
            try:
                for info in request("GET", f"/api/session?parentID={sid}&limit=100")["data"]:
                    if info.get("parentID") == sid and info["id"] not in self.sessions:
                        require(Path(info["location"]["directory"]).resolve() == self.args.run / "workspace", "Child escaped fixture")
                        self.sessions.append(info["id"])
            except Exception as error:
                errors.append(type(error).__name__ + ": " + str(error))
        for sid in self.sessions:
            try:
                request("POST", f"/api/session/{sid}/interrupt")
                request("POST", f"/api/experimental/session/{sid}/wait", wait=True)
            except Exception as error:
                errors.append(type(error).__name__ + ": " + str(error))
        try:
            active = request("GET", "/api/session/active")["data"]
            require(isinstance(active, dict), "Unexpected active-session map")
            require(not set(active).intersection(self.sessions), "Owned foreground remains active")
        except Exception as error:
            errors.append(type(error).__name__ + ": " + str(error))
        if errors:
            self.report.setdefault("cleanup_failures", []).extend(errors)
        return not errors

    @contextmanager
    def managed(self, server, label):
        cleaned = False
        try:
            with server:
                try:
                    yield server
                except BaseException:
                    self.before_cleanup()
                    cleaned = True
                    self.cancel_owned(server)
                    raise
                finally:
                    self.before_cleanup()
        finally:
            # __exit__ can fail. Only this concrete Popen handle can establish that retries are gone.
            if not native_exited(server):
                try:
                    if not cleaned:
                        self.cancel_owned(server)
                    server.close()
                except (Exception, KeyboardInterrupt) as error:
                    self.report.setdefault("cleanup_failures", []).append(label + ": " + str(error))
            exited = native_exited(server)
            self.report.setdefault("native_process_exited", {})[label] = exited
            if not exited:
                self.report.setdefault("cleanup_failures", []).append(label + ": owned native process still alive; no runtime restart/recovery")
            elif self.pending_titles:
                self.report.setdefault("detached_titles_cancelled", {})[label] = sorted(self.pending_titles)
                self.pending_titles.clear()

    def positive(self, server):
        token = self.report["nonce"]
        facts = {"nonce": token, "color": "saffron", "number": 731}
        sid = self.create(server)  # Deliberately untitled: exercise native title generation.
        self.report["sessions"] = {"continuity": sid}
        _, ok = self.turn(server, sid, "Remember these facts for later: " + json.dumps(facts)
            + '. Do not use tools. Reply only ACK_ONE.', "ACK_ONE", "first-turn")
        require(ok, "Initial native positive control failed")
        title = self.settled_titles.get(sid, {})
        self.report["title_evidence"] = {"initial": self.initial_titles[sid], **title}
        require(self.record("title", {"title_request_observed": self.kind_seen(0, sid, "title"),
            "generated_title_changed": bool(title.get("generated")) and title["generated"] != title["initial"],
            "helper_idle": sid in self.settled_titles and sid not in self.pending_titles}, unavailable=True), "Title helper unavailable")
        _, ok = self.turn(server, sid, "Keep the earlier facts. Do not repeat them or use tools. Reply only ACK_TWO.", "ACK_TWO", "second-turn")
        require(ok, "Second native positive control failed")
        self.idle(server)
        compacted, delta, start = self.action(server, sid, "compact", {}, self.args.timeout)
        self.idle(server)
        compactions = [m for m in delta if m.get("type") == "compaction"]
        ok = self.record("compaction", {"completed_record": any(m.get("status") == "completed" for m in compactions),
            "local_compaction_observed": self.kind_seen(start, sid, "compaction")}, unavailable=not self.kind_seen(start, sid, "compaction"))
        require(ok, "Native compaction unavailable/failed; preserve evidence before outage")
        _, ok = self.turn(server, sid, 'Return only a JSON object containing the earlier nonce, color and number. No tools.', facts, "retention")
        require(ok, "Facts were not retained after compaction")
        start = len(self.audit())
        before = self.export(server, sid)
        generated = self.api(server, "POST", f"/api/session/{sid}/generate", {"prompt": "Reply only with the earlier nonce. Do not use tools."}, self.args.timeout)
        self.idle(server)
        after = self.export(server, sid)
        require(self.record("generate", {"literal_content": self.grade("generate", generated.get("data", {}).get("text", ""), token),
            "local_generate_observed": self.kind_seen(start, sid, "generate"), "history_unchanged": messages(before) == messages(after)}), "Generate positive control failed")
        parent = self.create(server, "build", "Lifecycle reviewer control")
        wanted = {"agent": "reviewer", "description": "Readonly arithmetic review", "prompt":
            "Read-only isolated review: the statement 2+3=5 is correct. Reply only REVIEW_OK. Use no tools and edit nothing.", "background": False}
        exported, ok = self.turn(server, parent, "Call the native subagent tool exactly once using these arguments, without sessionID or model: "
            + json.dumps(wanted) + " After it completes, reply only REVIEW_DONE. Do nothing else.", "REVIEW_DONE", "review-parent", allow_tools=True)
        require(ok, "Reviewer parent did not complete its positive control")
        children = self.api(server, "GET", f"/api/session?parentID={parent}&limit=10")["data"]
        calls = [p for m in messages(exported) if m.get("type") == "assistant" for p in m.get("content", []) if p.get("type") == "tool"]
        good = len(children) == 1 and len(calls) == 1 and calls[0].get("name") == "subagent" and calls[0].get("state", {}).get("status") == "completed"
        require(self.record("one-reviewer", {"one_completed_native_subagent": good}), "Fresh reviewer helper did not complete exactly once")
        child = children[0]["id"]
        self.sessions.append(child)
        child_export = self.export(server, child)
        self.report["sessions"].update(review_parent=parent, review_child=child)
        save(self.folder / "review-child.export.json", child_export)
        info = child_export["data"]["info"]
        inputs = calls[0]["state"].get("input", {})
        self.report["subagent_argument_evidence"] = {"background_present": "background" in inputs,
            "background_value": inputs.get("background"), "explicit_requested_false": inputs.get("background") is False}
        require(self.record("review-child", {"parent_verified": info.get("parentID") == parent, "fresh_not_fork": not info.get("fork")
            and "sessionID" not in inputs, "reviewer_agent": info.get("agent") == "reviewer", **foreground_checks(calls[0], child_export),
            "configured_reviewer_model_preserved": "model" not in inputs,
            "literal_child_answer": self.grade("review-child", text_of(messages(child_export)), "REVIEW_OK"),
            **completion_checks(child_export, messages(child_export)),
            "independent_local_request": self.kind_seen(0, child, "primary")}), "Reviewer child evidence failed")
        self.idle(server)
        return sid, child

    def outage_action(self, server, sid, action, label):
        require(not port_open(), "Runtime unexpectedly returned during outage")
        exported, delta, start = self.action(server, sid, action,
            {"text": "Without tools, reply only OUTAGE_" + uuid.uuid4().hex} if action == "prompt" else {}, self.args.outage_timeout)
        errors = [m.get("error") for m in delta if m.get("error")]
        unavailable = any(e.get("type") == "compaction.unavailable" for e in errors)
        self.record(label, {"local_request_observed": self.kind_seen(start, sid, "primary" if action == "prompt" else "compaction"),
            "terminal_failure": exported["data"]["info"].get("outcome") == "failed" or any(m.get("status") == "failed" for m in delta),
            "explicit_transport_error": any(transport_error(e) for e in errors), "no_generated_answer": no_generated_output(delta),
            "runtime_stayed_down": not port_open()}, unavailable=unavailable)

    def outage(self, server, sid, child):
        fresh = self.create(server)
        self.report["sessions"]["outage_primary"] = fresh
        self.outage_action(server, fresh, "prompt", "outage-primary")
        self.outage_action(server, child, "prompt", "outage-existing-child")
        self.outage_action(server, sid, "compact", "outage-compaction")
        start = len(self.audit())
        before = self.export(server, sid)
        try:
            result = self.api(server, "POST", f"/api/session/{sid}/generate", {"prompt": "Reply only OUTAGE_" + uuid.uuid4().hex}, self.args.outage_timeout)
            error, no_answer = None, not result.get("data", {}).get("text", "").strip()
        except APIError as e:
            if e.record.get("timed_out"):
                raise RuntimeError("Generate timed out; completion unavailable, not an outage pass")
            error, no_answer = e.record, True
        after = self.export(server, sid)
        self.record("outage-generate", {"local_generate_observed": self.kind_seen(start, sid, "generate"),
            "explicit_transport_error": bool(error and transport_error(error)), "native_error": bool(error),
            "no_generated_answer": no_answer, "history_unchanged": messages(before) == messages(after), "runtime_stayed_down": not port_open()},
            unavailable=bool(error and error.get("http_status") in (404, 405)))


def self_check():
    assert transport_error({"type": "provider.transport", "message": "connection refused"})
    assert not transport_error({"type": "compaction.unavailable", "message": "Nothing to compact"})
    assert text_of([{"type": "assistant", "content": [{"type": "reasoning", "text": "hidden"}, {"type": "text", "text": "OK"}]}]) == "OK"
    facts = {"nonce": "a" * 32, "color": "saffron", "number": 731}
    literal = json.dumps(facts)
    assert answer_evidence(literal, facts)["exact_format"]
    for text in ("Remembered facts: " + literal, "```json\n" + literal + "\n```"):
        grade = answer_evidence(text, facts)
        assert grade["content_ok"] and not grade["exact_format"] and grade["literal"] == literal
        assert text[slice(*grade["span"])] == literal and grade["raw_text"] == text
    for text in (literal + literal, literal.replace('731', '731.0'), literal.replace('731', '732'),
                 literal.replace('731', 'NaN'), '{"nonce":"wrong",' + literal[1:], str(facts)):
        assert not answer_evidence(text, facts)["content_ok"]
    assert answer_evidence(literal.replace('731', '732'), facts)["exact_format"]
    assert answer_evidence("Acknowledged: ACK_ONE.", "ACK_ONE")["content_ok"]
    for text in ("ACK_ONE ACK_TWO", "ACK_ONE ACK_ONE", "NOT_ACK_ONE", "ACK_ONE_EXTRA"):
        assert not answer_evidence(text, "ACK_ONE")["content_ok"]
    recovery = "RECOVERY_" + facts["nonce"]
    assert answer_evidence("Local recovery completed: " + recovery, recovery)["content_ok"]
    assert not answer_evidence(recovery + " or " + "b" * 32, recovery)["content_ok"]
    app = {"ok": True, "state": "running", "port": 8000, "pid": 123}
    assert control_matches(app, 123, 123)
    assert not control_matches(app, 124, 123) and not control_matches({**app, "pid": 124}, 123, 123)
    assert not control_matches({**app, "pid": "123"}, 123, 123)
    exported = {"data": {"info": {"outcome": "succeeded"}}}
    assistant = {"type": "assistant", "time": {"completed": 1}, "finish": "stop", "content": [{"type": "text", "text": "ACK_ONE"}]}
    assert all(completion_checks(exported, [assistant]).values())
    assert not all(completion_checks(exported, [{**assistant, "finish": "length"}]).values())
    assert not all(completion_checks(exported, [{**assistant, "time": {}}]).values())
    assert not all(completion_checks(exported, [{**assistant, "content": [{"type": "tool", "state": {"status": "completed"}}]}]).values())
    child = {"data": {"info": {"id": "child", "time": {"created": 11, "idle": 20}},
        "messages": [{**assistant, "time": {"completed": 19}}]}}
    call = {"state": {"status": "completed", "input": {}, "metadata": {"sessionID": "child", "status": "completed"}},
        "time": {"ran": 10, "completed": 21}}
    assert all(foreground_checks(call, child).values())  # Omitted is native foreground.
    explicit = copy.deepcopy(call); explicit["state"]["input"]["background"] = False
    assert all(foreground_checks(explicit, child).values())
    for value in (True, None, 0, "false"):
        bad = copy.deepcopy(call); bad["state"]["input"]["background"] = value
        assert not foreground_checks(bad, child)["foreground"]
    for key, value in (("status", "running"), ("sessionID", "other")):
        bad = copy.deepcopy(call); bad["state"]["metadata"][key] = value
        assert not foreground_checks(bad, child)["completed_child_result"]
    for completed in (None, 18, True):
        bad = copy.deepcopy(call); bad["time"]["completed"] = completed
        assert not foreground_checks(bad, child)["child_finished_before_tool_return"]
    # A failed __exit__ must never make a still-live native process eligible for restart.
    class StuckServer:
        def __init__(self): self.process = self
        def poll(self): return None
        def __enter__(self): return self
        def __exit__(self, *_): raise RuntimeError("failed close")
        def close(self): raise RuntimeError("still alive")
    probe = Probe(None, Path("unused-offline"), {"cases": {}})
    interrupted = []
    probe.cancel_owned = lambda server: interrupted.append(server) or True
    stuck = StuckServer()
    try:
        with probe.managed(stuck, "offline"):
            pass
    except RuntimeError:
        pass
    assert interrupted == [stuck] and not native_exited(stuck)
    assert probe.report["native_process_exited"]["offline"] is False and probe.report["cleanup_failures"]
    stuck.poll = lambda: 0
    assert native_exited(stuck)
    scoped = Probe(argparse.Namespace(run=Path("/fixture")), Path("unused-offline"), {"cases": {}})
    scoped.sessions = ["owned"]
    calls = []
    def fake_api(server, method, path, body=None, timeout=20):
        calls.append((method, path))
        if path.startswith("/api/session?parentID="):
            return {"data": [{"id": "child", "parentID": "owned", "location": {"directory": "/fixture/workspace"}}]}
        return {"data": {"unrelated": {}} if path == "/api/session/active" else {}}
    scoped.api = fake_api
    assert scoped.cancel_owned(None)
    assert {path for method, path in calls if method == "POST"} == {
        "/api/session/owned/interrupt", "/api/experimental/session/owned/wait",
        "/api/session/child/interrupt", "/api/experimental/session/child/wait"}
    assert no_generated_output([{"type": "assistant", "error": {"type": "provider.transport"}, "content": []}])
    assert not no_generated_output([{"type": "assistant", "content": [{"type": "reasoning", "text": "unexpected generation"}]}])
    row = {"event": "http.request", "ok": True, "model": {"providerID": "local", "id": "qwen"}, "destination": RUNTIME + "/v1/chat/completions"}
    assert routes_ok([row]) and not routes_ok([])
    for bad in ("https://example.test/v1", RUNTIME + "/v1?key=x", RUNTIME + "/v10"):
        assert not routes_ok([{**row, "destination": bad}])
    print("Offline checks passed: PID binding, literal grading vs format, terminal/tool rules, semantic foreground/default with completed child timing, failed-close restart gate and routing; no API/process operations.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", nargs="?", type=Path)
    parser.add_argument("--runtime-pid", type=int, help="operator-observed port-8000 PID; mandatory before a real run")
    parser.add_argument("--stage", default="lifecycle1")
    parser.add_argument("--variant", choices=("fast", "low", "medium", "xhigh"), default="fast")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--outage-timeout", type=int, default=180)
    parser.add_argument("--guard-resources", action="store_true", help="sample host resources across positive/outage/recovery; interrupt only this probe on unsafe conditions")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return 0
    if not args.run or not args.runtime_pid or not 30 <= args.timeout <= 900 or not 30 <= args.outage_timeout <= 300 or not re.fullmatch(r"[A-Za-z0-9_-]+", args.stage):
        parser.error("prepared task11 run and --runtime-pid required; timeout 30..900, outage 30..300; simple stage name")
    args.run = args.run.resolve()
    run = json.loads((args.run / "run.json").read_text())
    require(str(run.get("task")) == "11" and (args.run / "workspace/.git").is_dir(), "Expected prepared task11 fixture")
    require(not (args.run / "workspace").is_symlink() and fixture_hashes(args.run / "workspace") == run["initial_hashes"],
            "Task11 workspace is not an unchanged prepared fixture")
    folder = args.run / "evidence" / args.stage
    folder.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "draft_revision": 5, "status": "PARTIAL", "nonce": uuid.uuid4().hex,
        "expected_model_id": MODEL_ID,
        "variant": args.variant, "cases": {}, "runtime_stop_attempted": False,
        "scope": "Observed native model routes only; not OS-wide network or arbitrary tool egress proof.",
        "limits": ["Fresh-primary outage may not trigger title; absent title-outage coverage is not claimed.",
                   "Automatic title requests are native helpers; the existing runtime must retain its single-generation limit.",
                   "Resource samples can miss transients. Intentional stop/start/outage records host telemetry without requiring a model process."]}
    try:
        config = copy.deepcopy(owned_config())
        validate_owned_config(config)
    except Exception as e:
        report["setup_error"] = type(e).__name__ + ": " + str(e)
        save(folder / "metrics.json", report)
        return 1
    report["owned_config_sha256"] = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    report["source_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__), TOOLS / "native_client.py", TOOLS / "localai.py", TOOLS / "inference-audit/server.js", TOOLS / "run_native_trial.py", TOOLS / "context_probe.py")}
    # Native plugins are watched for changes. Freeze this probe's instrumentation
    # so later source edits cannot unload its hooks while a trial is running.
    audit_source = folder / "audit-plugin"
    audit_source.mkdir()
    report["audit_source_sha256"] = {}
    for name in ("server.js", "package.json"):
        target = audit_source / name
        shutil.copyfile(TOOLS / "inference-audit" / name, target)
        target.chmod(0o400)
        report["audit_source_sha256"][name] = hashlib.sha256(target.read_bytes()).hexdigest()
    probe = Probe(args, folder, report)
    monitor, baseline_swap = None, None
    def disarm_guard():
        if monitor is not None:
            monitor.disarm()
    probe.before_cleanup = disarm_guard
    report["resource_guard"] = {"enabled": args.guard_resources, "sample_interval_seconds": 2,
                                "max_swap_growth_mib": 512, "warning_samples": 2, "segments": {}}
    def resource_abort(reason):
        report["resource_aborted"] = True
        report.setdefault("resource_abort_reason", reason)
    def start_guard(label, pid=None, host_only=False, arm=True):
        nonlocal monitor
        if not args.guard_resources:
            return
        require(monitor is None, "Previous resource segment remains open")
        target = folder / ("resources-" + label)
        target.mkdir()
        monitor = LifecycleResourceGuard(target, [], baseline_swap, pid, host_only, resource_abort)
        monitor.label = label
        monitor.start()
        if arm:
            monitor.arm()
    def finish_guard():
        nonlocal monitor, baseline_swap
        if monitor is None:
            return True
        current = monitor  # Keep the handle until disarm/join/log close are proved.
        try:
            summary = current.finish()
        except (Exception, KeyboardInterrupt) as error:
            summary = {"clean": False, "error": type(error).__name__ + ": " + str(error)}
            report.setdefault("cleanup_failures", []).append("resource sampler: " + summary["error"])
        if current.is_closed():
            monitor = None
        else:
            summary["clean"] = False
            report.setdefault("cleanup_failures", []).append("resource sampler remains open; retained for cleanup")
        if baseline_swap is None:
            baseline_swap = current.guard.baseline_swap
        if current.cancel.is_set():
            resource_abort(current.guard.reason)
        report["resource_guard"]["segments"][current.label] = summary
        return summary["clean"]
    def resource_clean():
        rows = report["resource_guard"]["segments"].values()
        return not args.guard_resources or bool(rows) and all(row["clean"] for row in rows)
    def configured(log):
        out = copy.deepcopy(config)
        out["plugins"].append({"package": str(audit_source),
                               "options": {"log": str(log), "expectedModelID": MODEL_ID}})
        return out
    def cli(action):
        result = subprocess.run([str(OMLX), action, "--timeout", "60"], env=environment({}), capture_output=True, timeout=75)
        save(folder / ("runtime-" + action + ".json"), {"command": [str(OMLX), action], "exit_code": result.returncode})
        require(result.returncode == 0, "Owned oMLX lifecycle command failed: " + action)
    def inspect_native(server):
        inv = inventory(server, config)  # Existing strict local route/model/agent validation.
        plugins = probe.api(server, "GET", "/api/plugin")["data"]
        require(all(p.get("source", {}).get("type") == "builtin" or p.get("id") == "localai.inference-audit"
            and p.get("source", {}).get("path") == str(audit_source / "server.js") for p in plugins), "Unexpected external native plugin")
        require(any(p.get("id") == "localai.inference-audit" and p.get("state", {}).get("status") == "active" for p in plugins), "Audit plugin is not active")
        require(any(r.get("event") == "ready" for r in probe.audit()), "Inference audit unavailable")
        return {"providers": [p["id"] for p in inv["providers"]["data"]],
                "models": [{k: m.get(k) for k in ("id", "providerID", "modelID")} for m in inv["models"]["data"]]}
    native = None
    try:
        report["runtime_before"] = runtime_identity(args.runtime_pid)
        native = NativeServer(args.run / "workspace", configured(probe.audit_path), folder / "native-server.log")
        with probe.managed(native, "main") as server:
            report["inventory_before"] = inspect_native(server)
            start_guard("positive", report["runtime_before"]["pid"])
            sid, child = probe.positive(server)
            probe.idle(server)
            require(not probe.api(server, "GET", "/api/session/active")["data"], "Native sessions active before stop")
            require(finish_guard(), "Positive lifecycle resource guard failed; no outage attempted")
            start_guard("outage", host_only=True)
            # Last identity read before the stop: control target == listener == operator-supplied PID.
            report["runtime_pre_stop"] = runtime_identity(args.runtime_pid)
            report["runtime_stop_attempted"] = True
            cli("stop")
            deadline = time.monotonic() + 30
            while port_open() and time.monotonic() < deadline:
                time.sleep(0.5)
            require(not port_open(), "Owned CLI did not release port; outage not established")
            for _ in range(3):
                time.sleep(1)
                require(not port_open(), "Runtime auto-restarted; outage invalid")
            report["owned_runtime_only_stopped"] = True
            if monitor is not None:
                monitor.expect_absent = True
            probe.outage(server, sid, child)
    except (Exception, KeyboardInterrupt) as e:
        report["error"] = type(e).__name__ + ": " + str(e)
    finally:
        finish_guard()
        # Restart only after explicit process-exit evidence, including failed __exit__ paths.
        safe_to_restore = native_exited(native)
        report["restore_gate_native_exited"] = safe_to_restore
        if not safe_to_restore:
            report["recovery_skipped"] = "Owned native process may still retry; operator attention required"
        elif report["runtime_stop_attempted"]:
            try:
                # Cleanup is never interrupted repeatedly. Preflight still refuses
                # unsafe restoration, and failed resources forbid recovery inference.
                start_guard("restore", host_only=True, arm=False)
                if not port_open():
                    cli("start")
                wait_runtime_idle()
                report["runtime_restored"] = runtime_identity()
                require(finish_guard(), "Resource guard failed while restoring owned runtime")
                if not resource_clean():
                    report["recovery_skipped"] = "Earlier resource failure: runtime restored but recovery inference not attempted"
                else:
                    probe.audit_path = folder / "inference-recovery.jsonl"
                    recovery_server = NativeServer(args.run / "workspace", configured(probe.audit_path), folder / "native-recovery.log")
                    with probe.managed(recovery_server, "recovery") as recovery:
                        report["inventory_recovery"] = inspect_native(recovery)
                        start_guard("recovery", report["runtime_restored"]["pid"])
                        sid = probe.create(recovery, title="Lifecycle recovery")
                        report.setdefault("sessions", {})["recovery"] = sid
                        _, ok = probe.turn(recovery, sid, "Do not use tools. Reply only RECOVERY_" + report["nonce"], "RECOVERY_" + report["nonce"], "recovery")
                        require(ok, "Local recovery response failed")
            except (Exception, KeyboardInterrupt) as e:
                report["recovery_error"] = type(e).__name__ + ": " + str(e)
            finally:
                finish_guard()
        # A pre-stop failure must not hand a still-busy model back to the next trial.
        # This is read-only: never start a runtime that this probe did not attempt to stop.
        try:
            report["runtime_idle_before_return"] = wait_runtime_idle()
        except (Exception, KeyboardInterrupt) as e:
            report.setdefault("cleanup_failures", []).append("runtime idle before return: " + type(e).__name__ + ": " + str(e))
        all_rows = []
        for path in (folder / "inference.jsonl", folder / "inference-recovery.jsonl"):
            if path.exists():
                try:
                    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
                except (OSError, ValueError) as e:
                    rows = []
                    report.setdefault("cleanup_failures", []).append(path.name + ": incomplete audit evidence: " + str(e))
                all_rows.extend(rows)
                report[path.name + "_balanced"] = sum(r.get("event") == "ready" for r in rows) == sum(r.get("event") == "closed" for r in rows) == 1
        report["observed_routes_local"] = routes_ok(all_rows)
        probe.record("fixture-unchanged", {"hashes_match": fixture_hashes(args.run / "workspace") == run["initial_hashes"]})
        report["kinds_observed"] = sorted({r["kind"] for r in all_rows if r.get("event") == "http.request" and r.get("kind")})
        required = {"first-turn", "second-turn", "title", "compaction", "retention", "generate", "review-parent", "one-reviewer", "review-child", "outage-primary", "outage-existing-child", "outage-compaction", "outage-generate", "recovery"}
        complete = required <= report["cases"].keys() and all(c["status"] == "PASS" for c in report["cases"].values())
        hard_route_failure = any(r.get("ok") is False or r.get("event") == "unexpected.websocket" for r in all_rows)
        answers = report.get("answers", {})
        report["format_compliance"] = ("PASS" if all(a["exact_format"] for a in answers.values()) else "FAIL") if answers else "NOT_TESTED"
        report["cleanup_complete"] = (safe_to_restore and all(report.get("native_process_exited", {}).values())
            and not report.get("cleanup_failures") and "runtime_idle_before_return" in report)
        report["resource_guard"]["clean"] = resource_clean()
        if complete and resource_clean() and report["observed_routes_local"] and not report.get("error") and not report.get("recovery_error") and report["cleanup_complete"] and all(report.get(p + "_balanced") for p in ("inference.jsonl", "inference-recovery.jsonl")):
            report["status"] = "PASS"
        elif hard_route_failure:
            report["status"] = "FAIL"
        elif not report["cleanup_complete"]:
            report["status"] = "PARTIAL"
        elif any(c["status"] == "FAIL" for c in report["cases"].values()):
            report["status"] = "FAIL"
        save(folder / "metrics.json", report)
        print(json.dumps({"status": report["status"], "evidence": str(folder)}), flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    def interrupted(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(main())
