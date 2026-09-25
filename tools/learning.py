#!/usr/bin/env python3
"""Finite, local, idle-only native-agent learning. No alternate agent loop.

The plugin observes; OpenCode reasons/edits; this worker schedules bounded trials
and grades their final programs outside the candidate interpreter. Personal
projects, hidden answers and security settings are never optimization artifacts.
"""
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import hashlib
import fcntl
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import uuid

import improvement as state

POLICY = {
    "version": "learning-2026-09-20.4", "idle_seconds": 120, "day_seconds": 600,
    "reflection_seconds": 120, "reflection_tokens": 768, "reflection_variant": "fast", "trial_seconds": 360,
    # One final prospective opportunity can use genuinely new scoped evidence.
    # Prior startup failure/valid deferral and total daily time remain preserved.
    "candidates_per_day": 3, "queue": 2, "pairs_per_family": 3,
    "efficiency_fraction": .15, "yield_target_seconds": 10, "yield_bound_seconds": 30,
    "raw_days": 7, "raw_bytes": 256 * 1024**2, "metadata_days": 30, "metadata_records": 500,
    "holdout_uses_per_candidate": 1,
    "holdout_candidates_per_suite": 3,
}
FAMILIES = ("collections", "records", "text")
EMPTY = hashlib.sha256(b"").hexdigest()
BASELINE = {"revision": EMPTY, "instructions": ""}
DEFAULT_CONTROLS = {"enabled": True, "paused": True}
EVENT_KEYS = {"schema", "task_id", "champion_revision", "profile_id", "state", "wall_seconds",
              "tool_calls", "tool_errors", "check_passes", "check_failures", "compactions",
              "corrections", "output_tokens", "family", "completed_at"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def root(directory):
    return state._directory(Path(directory) / "learning")


def put(path, value):
    before = path.read_bytes() if path.exists() else None
    state._replace_pointer(path, value, before)


def read(path, default=None):
    return state._load(path) if path.exists() else default


def utc_day():
    return datetime.now(timezone.utc).date().isoformat()


def valid_event(item):
    import re
    if not isinstance(item, dict) or set(item) != EVENT_KEYS or item["schema"] != 1:
        raise ValueError("Unrecognized bounded plugin event")
    for key in ("task_id", "champion_revision", "profile_id"):
        if not isinstance(item[key], str) or not re.fullmatch(r"[a-f0-9]{64}", item[key]):
            raise ValueError("Event identities must be hashes")
    if item["state"] not in {"verified", "failed", "incomplete", "unknown"} or item["family"] not in {"coding", "data", "research", "json_cli", "unknown"}:
        raise ValueError("Unknown event classification")
    for key in ("wall_seconds", "tool_calls", "tool_errors", "check_passes", "check_failures", "compactions", "corrections", "output_tokens"):
        if item[key] is None and key in {"corrections", "output_tokens"}:
            continue
        state._number(item[key], integer=key != "wall_seconds")
        if item[key] > 10**9:
            raise ValueError("Event count exceeds bound")
    stamp = datetime.fromisoformat(item["completed_at"].replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.timestamp() > time.time() + 300:
        raise ValueError("Invalid event clock")
    return item


def events(directory):
    folder = state._directory(root(directory) / "events")
    result = []
    for path in sorted(folder.glob("*.json")):
        item = valid_event(state._load(path))
        if path.stem != item["task_id"]:
            raise ValueError("Event filename differs from identity")
        result.append(item)
    return sorted(result, key=lambda item: item["completed_at"])[-POLICY["metadata_records"]:]


def meaningful(item):
    return bool(item["tool_errors"] or item["check_failures"] or item["compactions"] >= 2 or (item["corrections"] or 0))


def _champion(directory):
    base = root(directory)
    current = read(base / "champion.json", BASELINE)
    if set(current) != {"revision", "instructions"}:
        raise RuntimeError("Invalid champion pointer")
    if current == BASELINE:
        return dict(BASELINE)
    version = state._load(base / "versions" / (current["revision"] + ".json"))
    candidate = version["candidate"]
    if candidate["revision"] != hashlib.sha256(candidate["instructions"].encode()).hexdigest() or current != {k: candidate[k] for k in ("revision", "instructions")}:
        raise RuntimeError("Champion instructions drifted")
    return current


def active_champion(directory, *, scope=None):
    """Narrow selection evidence never enables global instructions implicitly."""
    champion = _champion(directory)
    if champion == BASELINE:
        return champion
    version = state._load(root(directory) / "versions" / (champion["revision"] + ".json"))
    return champion if scope == version["candidate"]["scope"] else dict(BASELINE)


def status(directory):
    base = root(directory)
    return {"policy": POLICY, "controls": read(base / "control.json", dict(DEFAULT_CONTROLS)),
            "champion": _champion(directory)["revision"], "default_scope_champion": active_champion(directory)["revision"],
            "activation_scope": "disposable_json_cli", "worker": read(base / "worker.json"),
            "budget": read(base / "budget.json"), "last_decision": read(base / "last-decision.json"),
            "pipeline_implemented": True, "benefit_proven": False}


def failures(directory):
    """Error-triggered local backlog, not a schedule or a successful-learning claim."""
    folder = state._directory(root(directory) / "incidents")
    items = []
    for path in sorted(folder.glob('*.json'))[-POLICY['metadata_records']:]:
        value = state._load(path)
        if value.get('owner') != 'kryn.product' or value.get('task_id') != path.stem:
            raise RuntimeError('Unexpected failure record')
        items.append({key: value[key] for key in ('task_id', 'native_session_id', 'triggers', 'status', 'updated_at')})
    return {'trigger': 'native execution failures, interruptions, failed checks and exhausted reviews',
            'scheduled': False, 'count': len(items), 'incidents': items,
            'note': 'Inspect the linked private native trace, reproduce the error, and validate a candidate '
                    'against that regression and unaffected tasks before adopting it. Capturing a failure is not learning proof.'}


def control(directory, action):
    if action not in {"pause", "resume", "disable", "enable"}:
        raise ValueError("Unknown learning control")
    base = root(directory)
    with state._lock(base, "control.lock", True):
        value = read(base / "control.json", dict(DEFAULT_CONTROLS))
        value["paused" if action in {"pause", "resume"} else "enabled"] = action in {"pause", "enable"}
        put(base / "control.json", value)
    return value


def foreground_requested(directory):
    base = root(directory)
    controls = read(base / "control.json", dict(DEFAULT_CONTROLS))
    if not controls["enabled"] or controls["paused"]:
        return True
    for path in (base / "intent").glob("*.json"):
        try:
            state._regular(path)
            fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
        except FileNotFoundError:
            continue
        try:
            try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: return True
            # A dead launcher releases its descriptor; stale intent cannot block forever.
            path.unlink(missing_ok=True)
        finally: os.close(fd)
    return False


@contextmanager
def foreground(directory):
    """Foreground announces itself before waiting; worker must cancel then unlock."""
    base = root(directory)
    intents = state._directory(base / "intent")
    temporary = intents / (uuid.uuid4().hex + ".pending")
    path = temporary.with_suffix(".json")
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    os.write(fd, json.dumps({"pid": os.getpid(), "unix": time.time()}).encode())
    os.rename(temporary, path)
    started = time.monotonic()
    try:
        while True:
            try:
                lease = state.foreground(directory)
                lease.__enter__()
            except state.Deferred:
                if time.monotonic() - started >= POLICY["yield_bound_seconds"]:
                    raise RuntimeError("Foreground could not acquire the model within 30 seconds; no concurrent inference started")
                time.sleep(.1)
                continue
            try:
                yield
            finally:
                lease.__exit__(None, None, None)
            return
    finally:
        state._regular(path)
        path.unlink()
        os.close(fd)


def budget(directory):
    base = root(directory)
    value = read(base / "budget.json", {})
    if value.get("date") != utc_day():
        value = {"date": utc_day(), "seconds": 0.0, "candidates": 0}
    return value


def record_decision(directory, candidate, decision, reason, **evidence):
    if decision not in {"accept", "reject", "defer", "rollback"}:
        raise ValueError("Invalid learning decision")
    base = root(directory)
    value = {"policy": POLICY["version"], "candidate": candidate, "decision": decision,
             "reason": reason, "unix": time.time(), **evidence}
    folder = state._directory(base / "decisions")
    state._write_new(folder / (f"{time.time_ns():020d}-" + uuid.uuid4().hex + ".json"), value)
    put(base / "last-decision.json", value)
    return value


def reserve_reflection_attempt(directory, observation):
    """Persist the attempt before dispatch; any setup failure prevents inference."""
    base = root(directory)
    allowance = budget(directory)
    consumed = set(read(base / "consumed.json", []))
    if allowance["candidates"] >= POLICY["candidates_per_day"] or observation["task_id"] in consumed:
        raise state.Deferred("Reflection attempt is already consumed or its daily quota is exhausted")
    reservation = {"date": allowance["date"], "candidates_before": allowance["candidates"]}
    allowance["candidates"] += 1
    put(base / "budget.json", allowance)
    consumed.add(observation["task_id"])
    put(base / "consumed.json", sorted(consumed)[-500:])
    return reservation


def finish_reflection_attempt(directory, folder, observation, result, reservation, error_class=None, *, time_charged=False):
    """Release only a proved zero-dispatch reservation after its durable receipt."""
    try:
        telemetry = read(Path(folder) / "evidence/telemetry.json", {})
    except (OSError, ValueError, RuntimeError):
        telemetry = {}
    complete = (telemetry.get("dispatch_evidence_complete") is True
                and isinstance(telemetry.get("requests"), list))
    count = len(telemetry["requests"]) if complete else None
    base = root(directory)
    allowance = budget(directory)
    consumed = set(read(base / "consumed.json", []))
    release = (time_charged and complete and count == 0 and not result.get("native_completed")
               and allowance["date"] == reservation["date"]
               and allowance["candidates"] == reservation["candidates_before"] + 1
               and observation["task_id"] in consumed)
    receipt = {"policy": POLICY["version"], "unix": time.time(), "observation_sha256": digest(observation),
               "dispatch_evidence_complete": complete, "accepted_requests": count,
               "candidate_reserved": True, "release_authorized": release,
               "time_charged": time_charged,
               "native_completed": result.get("native_completed") is True,
               "error_class": error_class}
    state._write_new(Path(folder) / "reflection-attempt.json", receipt)
    if release:
        consumed.remove(observation["task_id"])
        put(base / "consumed.json", sorted(consumed)[-500:])
        allowance["candidates"] -= 1
        put(base / "budget.json", allowance)
    return {**receipt, "candidate_spent": not release}


def parse_proposal(text):
    value = json.loads(text.strip())
    if not isinstance(value, dict) or set(value) != {"decision", "instructions", "scope", "reason"}:
        raise ValueError("Reflection must return the bounded JSON contract")
    if value["decision"] not in {"propose", "defer"} or value["reason"] not in {"repeated_tool_failure", "verification_gap", "context_inefficiency", "insufficient_evidence"}:
        raise ValueError("Unknown reflection decision")
    if value["scope"] != "disposable_json_cli":
        raise ValueError("Initial learner is limited to tested JSON CLI workflows")
    instruction = value["instructions"]
    if not isinstance(instruction, str) or len(instruction) > 1500 or "\x00" in instruction:
        raise ValueError("Instruction size or type invalid")
    if value["decision"] == "propose" and not instruction.strip():
        raise ValueError("Empty proposal")
    value["revision"] = hashlib.sha256(instruction.encode()).hexdigest()
    return value


def selection_plan(revision):
    rows = []
    for family in FAMILIES:
        for repeat in range(POLICY["pairs_per_family"]):
            order = ("baseline", "candidate") if repeat % 2 == 0 else ("candidate", "baseline")
            for arm in order:
                rows.append({"family": family, "repeat": repeat, "arm": arm, "split": "selection"})
    rows += [{"family": family, "repeat": 0, "arm": "candidate", "split": "protected"} for family in FAMILIES]
    return {"policy": POLICY, "candidate": revision, "trials": rows,
            "cache": "serial native sessions; shared runtime prefix cache; exact reuse recorded when available"}


def decide(rows, *, protected_complete=False):
    """Frozen engineering gate; never pretend this small sample is statistical proof."""
    selection = [row for row in rows if row["split"] == "selection"]
    expected = len(FAMILIES) * POLICY["pairs_per_family"] * 2
    if len(selection) < expected:
        return "defer", "insufficient_repeated_pairs"
    if len(selection) != expected or len({(r["family"], r["repeat"], r["arm"]) for r in selection}) != expected:
        return "reject", "invalid_trial_accounting"
    wins, ratios = 0, []
    for family in FAMILIES:
        for repeat in range(POLICY["pairs_per_family"]):
            arms = {r["arm"]: r for r in selection if r["family"] == family and r["repeat"] == repeat}
            if set(arms) != {"baseline", "candidate"}:
                return "reject", "missing_matched_arm"
            a, b = arms["baseline"], arms["candidate"]
            if not a.get("conditions_verified") or not b.get("conditions_verified"):
                return "defer", "unverified_trial_conditions"
            if a["passed"] and not b["passed"]:
                return "reject", "correctness_regression"
            wins += int(b["passed"] and not a["passed"])
            if not b["passed"]:
                return "reject", "candidate_objective_failure"
            if a["passed"] and a["seconds"] > 0:
                ratios.append(b["seconds"] / a["seconds"])
    quality = wins >= 2
    # Shared/unmeasured cache reuse cannot substantiate an efficiency promotion.
    efficiency = len(ratios) == expected // 2 and all(r.get("cache_matched") is True for r in selection) and statistics.median(ratios) <= 1 - POLICY["efficiency_fraction"]
    if not (quality or efficiency):
        return "reject", "no_defensible_benefit"
    protected = [r for r in rows if r["split"] == "protected"]
    if not protected_complete or len(protected) != len(FAMILIES):
        return "defer", "protected_checks_required"
    if not all(r["passed"] and r.get("conditions_verified") for r in protected):
        return "reject", "protected_regression"
    return "accept", "quality_gain" if quality else "noninferior_efficiency_gain"


def promote(directory, candidate, rows):
    decision, reason = decide(rows, protected_complete=True)
    if decision != "accept":
        raise RuntimeError("Promotion lacks accepted repeated-trial evidence")
    base = root(directory)
    previous = _champion(directory)
    folder = state._directory(base / "versions")
    version = {"candidate": candidate, "previous": previous, "rows_sha256": digest(rows),
               "policy": POLICY, "activated_unix": time.time()}
    state._write_new(folder / (candidate["revision"] + ".json"), version)
    put(base / "champion.json", {k: candidate[k] for k in ("revision", "instructions")})
    return record_decision(directory, candidate["revision"], "accept", reason, rows_sha256=digest(rows))


def rollback(directory, revision, pairs):
    """Two matched regressions or operator rollback; never infer causality from exit."""
    if len(pairs) < 2 or not all(p.get("previous_passed") is True and p.get("current_passed") is False for p in pairs):
        raise RuntimeError("Rollback requires repeated matched regression evidence")
    base = root(directory)
    current = _champion(directory)
    if current["revision"] != revision or current == BASELINE:
        raise RuntimeError("Champion changed before rollback")
    version = state._load(base / "versions" / (revision + ".json"))
    put(base / "champion.json", version["previous"])
    return record_decision(directory, revision, "rollback", "repeated_matched_regression", evidence_sha256=digest(pairs))


def fixture(family, protected=False):
    """Small separate selection suite; never advertise as broad agent capability."""
    if family == "collections":
        prompt = "Repair solve.py. Read one JSON array of strings from stdin. Output the first spelling of each distinct casefolded string, preserving input order. Empty strings and Unicode are valid. Keep the JSON stdin/stdout contract. Add and run useful checks."
        source = "import json,sys\nvalues=json.load(sys.stdin)\nprint(json.dumps(sorted(set(values))))\n"
        cases = [(["B", "a", "b", "A"], ["B", "a"]), (["", "", "Ω", "ω"], ["", "Ω"]), ([], [])]
        if protected:
            cases = [(["Straße", "STRASSE", "z", "Z", ""], ["Straße", "z", ""]), (["x", "Y", "X", "y"], ["x", "Y"])]
    elif family == "records":
        prompt = "Repair solve.py. Input is a JSON object with rows [{project, minutes}] and optional project. Return JSON {count, minutes}; project filtering is exact and case-sensitive; no project means all rows. Include zero-minute rows. Add and run useful checks."
        source = "import json,sys\nx=json.load(sys.stdin)\nrows=[r for r in x['rows'] if r['minutes']]\nprint(json.dumps({'count':len(rows),'minutes':sum(r['minutes'] for r in rows)}))\n"
        cases = [({"rows": [{"project": "A", "minutes": 0}, {"project": "a", "minutes": 4}], "project": "A"}, {"count": 1, "minutes": 0}), ({"rows": []}, {"count": 0, "minutes": 0}), ({"rows": [{"project": "x", "minutes": 3}]}, {"count": 1, "minutes": 3})]
        if protected:
            cases = [({"rows": [{"project": "a, Ω", "minutes": 7}, {"project": "a, ω", "minutes": 2}], "project": "a, Ω"}, {"count": 1, "minutes": 7}), ({"rows": [{"project": "x", "minutes": 0}], "project": "missing"}, {"count": 0, "minutes": 0})]
    elif family == "text":
        prompt = "Repair solve.py. Input JSON {text} contains CSV with header name,minutes. Parse CSV including an optional UTF-8 BOM, CRLF, quoted commas and Unicode. Output an array of {name, minutes} with integer minutes; zero is valid. Add and run useful checks."
        source = "import json,sys\nx=json.load(sys.stdin)\nrows=[line.split(',') for line in x['text'].splitlines()[1:]]\nprint(json.dumps([{'name':r[0],'minutes':int(r[1])} for r in rows]))\n"
        cases = [({"text": '\ufeffname,minutes\r\n"a, Ω",0\r\n'}, [{"name": "a, Ω", "minutes": 0}]), ({"text": 'name,minutes\nx,3\n'}, [{"name": "x", "minutes": 3}]), ({"text": "name,minutes\n"}, [])]
        if protected:
            cases = [({"text": 'name,minutes\n"line\nbreak",2\n"say ""hi""",4\n'}, [{"name": "line\nbreak", "minutes": 2}, {"name": 'say "hi"', "minutes": 4}])]
    else:
        raise ValueError("Unknown frozen selection family")
    return prompt, source, cases


def grade(workspace, family, protected=False, *, prefix=(), cancel=lambda: False):
    """Trusted parent compares black-box values; never imports candidate code."""
    _, _, cases = fixture(family, protected)
    results = []
    for given, expected in cases:
        if cancel():
            results.append(False); break
        with tempfile.TemporaryFile(dir=workspace) as output:
            proc = subprocess.Popen([*prefix, sys.executable, "-I", "-S", "-B", str(Path(workspace) / "solve.py")],
                                    stdin=subprocess.PIPE, stdout=output, stderr=subprocess.DEVNULL,
                                    cwd=workspace, env={"PATH": "/usr/bin:/bin", "HOME": str(workspace)}, start_new_session=True)
            try:
                proc.stdin.write(json.dumps(given).encode()); proc.stdin.close()
                deadline = time.monotonic() + 5
                while proc.poll() is None and time.monotonic() < deadline and output.tell() <= 65536 and not cancel():
                    time.sleep(.05)
                if proc.poll() is None: proc.terminate()
                code = proc.wait(timeout=1)
                output.seek(0); raw = output.read(65537)
                # Fake grader JSON and exit(0) are only untrusted program output.
                passed = code == 0 and len(raw) <= 65536 and json.loads(raw) == expected
            except (ValueError, OSError, subprocess.TimeoutExpired):
                passed = False
            finally:
                state._settle_checker(proc)
        results.append(bool(passed))
    return {"passed": all(results), "checks": len(results), "checks_passed": sum(results)}


class InferenceRelay:
    """Security-only forwarding: two routes, one pinned model, one request at a time."""
    def __init__(self, model, max_tokens=4096, request_timeout=360, tools_allowed=True):
        self.model, self.max_tokens = model, max_tokens
        self.cancelled = threading.Event()
        self.gate = threading.Lock()
        self.connections = set()
        self.records = []
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self): self.forward()
            def do_POST(self): self.forward()
            def forward(self):
                if (self.command, self.path) not in {("GET", "/v1/models"), ("POST", "/v1/chat/completions")}:
                    self.send_error(403); return
                if self.command == "GET":
                    data = json.dumps({"object": "list", "data": [{"id": owner.model, "object": "model", "owned_by": "local"}]}).encode()
                    self.send_response(200); self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
                if owner.cancelled.is_set() or not owner.gate.acquire(blocking=False):
                    self.send_error(409); return
                conn = None
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 <= length <= 2 * 1024**2:
                        self.send_error(413); return
                    body = self.rfile.read(length)
                    if self.command == "POST":
                        value = json.loads(body)
                        if value.get("model") != owner.model or len(owner.records) >= 128:
                            self.send_error(403); return
                        if not tools_allowed and value.get("tools"):
                            self.send_error(403); return
                        tokens = value.get("max_tokens", value.get("max_completion_tokens", owner.max_tokens))
                        if type(tokens) is not int or not 1 <= tokens <= owner.max_tokens:
                            self.send_error(403); return
                        numeric = {key: value[key] for key in ("max_tokens", "temperature", "top_p", "top_k", "min_p", "presence_penalty", "repetition_penalty") if type(value.get(key)) in {int, float}}
                        owner.records.append({"model": owner.model, "max_tokens": tokens, "started": time.time(),
                                              "numeric": numeric, "thinking": value.get("chat_template_kwargs", {}),
                                              "tool_count": len(value.get("tools", [])), "tool_schema_sha256": digest(value.get("tools", []))})
                    conn = http.client.HTTPConnection("127.0.0.1", 8000, timeout=2)
                    owner.connections.add(conn)
                    conn.connect()
                    if owner.cancelled.is_set(): return
                    conn.sock.settimeout(request_timeout)
                    conn.request(self.command, self.path, body, {"Content-Type": "application/json"})
                    response = conn.getresponse()
                    self.send_response(response.status)
                    self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    while not owner.cancelled.is_set():
                        data = response.read1(65536)
                        if not data: break
                        self.wfile.write(data); self.wfile.flush()
                except (OSError, ValueError, http.client.HTTPException):
                    self.close_connection = True
                finally:
                    if conn:
                        owner.connections.discard(conn); conn.close()
                    owner.gate.release()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
    def __enter__(self):
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start(); return self
    def cancel(self):
        self.cancelled.set()
        for conn in list(self.connections):
            if conn.sock:
                try: conn.sock.shutdown(socket.SHUT_RDWR)
                except OSError: pass
            conn.close()
    def __exit__(self, *args):
        self.cancel(); self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)


def configured_reference(config):
    reference = config.get("agents", {}).get("build", {}).get("model", config.get("model"))
    if not isinstance(reference, str) or not reference.startswith("local/qwen#"):
        raise RuntimeError("Learning requires the selected explicit local model variant")
    variant = reference.partition("#")[2]
    choices = {item["id"] for item in config["providers"]["local"]["models"]["qwen"].get("variants", [])}
    if variant not in choices:
        raise RuntimeError("Learning variant is not in the installed profile")
    return reference, variant


def plugin_config(config, champion, directory, base_url):
    value = copy.deepcopy(config)
    found = False
    for item in value.get("plugins", []):
        if isinstance(item, dict) and "champion" in item.get("options", {}):
            item["options"].update(champion=champion, stateDir=str(directory), observe=False,
                                   workflowScope="disposable_json_cli", inferenceBaseURL=base_url)
            found = True
    if not found:
        raise RuntimeError("Installed native KRYN policy plugin is required for matched instruction exposure")
    value["providers"]["local"]["settings"]["baseURL"] = base_url
    local_model = value["providers"]["local"]["models"]["qwen"]
    local_model.setdefault("settings", {})["baseURL"] = base_url
    for variant in local_model.get("variants", []):
        if "settings" in variant:
            variant["settings"]["baseURL"] = base_url
    value["mcp"] = {"servers": {}}
    value["skills"] = []
    # The native server still supplies its tools/loop; only disposable filesystem
    # operations are allowed, with OS containment covering every descendant.
    value["permissions"] = [{"action": "*", "resource": "*", "effect": "deny"}] + [
        {"action": action, "resource": "*", "effect": "allow"}
        for action in ("read", "write", "edit", "glob", "grep", "shell")]
    value["agents"] = {"build": {"model": configured_reference(config)[0], "permissions": value["permissions"]}}
    return value


def settle_background(server, root_id, workspace, relay, *, interrupt=False):
    """Verified ownership + acknowledgement + runtime idle, within eight seconds.

    Leave time inside the 30-second foreground bound for a currently running
    bounded resource sample and native process cleanup. Failure stays explicit.
    """
    started = time.monotonic()
    deadline = started + 8
    pending, owned = [root_id], set()
    acknowledgements = []
    def call(method, endpoint, body=None):
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise RuntimeError("Background cancellation settlement exceeded eight seconds")
        return server.request(method, endpoint, body, timeout=min(2, remaining))
    while pending:
        sid = pending.pop()
        if sid in owned or len(owned) >= 8: raise RuntimeError("Unexpected background session descendants")
        info = call("GET", "/api/session/" + sid)["data"]
        if (info.get("id") != sid or Path(info.get("location", {}).get("directory", "")).resolve() != workspace.resolve()
                or info.get("model", {}).get("providerID") != "local" or info.get("model", {}).get("id") != "qwen"):
            raise RuntimeError("Refusing interruption of an unrelated native session")
        owned.add(sid)
        if interrupt:
            response = call("POST", "/api/session/" + sid + "/interrupt", {})
            if type(response.get("interrupted")) is not bool:
                raise RuntimeError("Native cancellation was not acknowledged")
            acknowledgements.append(response["interrupted"])
        children = call("GET", "/api/session?parentID=" + sid + "&limit=10")
        if children.get("cursor", {}).get("next") or not isinstance(children.get("data"), list):
            raise RuntimeError("Incomplete background descendant inventory")
        for child in children["data"]:
            if child.get("parentID") != sid: raise RuntimeError("Unowned background descendant")
            pending.append(child["id"])
    if interrupt: relay.cancel()
    quiet = 0
    while time.monotonic() < deadline:
        active = call("GET", "/api/session/active")["data"]
        connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=min(2, max(.1, deadline - time.monotonic())))
        try:
            connection.request("GET", "/api/status")
            response = connection.getresponse()
            value = json.loads(response.read(65537))
            idle = response.status == 200 and all(type(value.get(k)) is int and value[k] == 0 for k in ("active_requests", "waiting_requests"))
        finally: connection.close()
        quiet = quiet + 1 if idle and not owned.intersection(active) else 0
        if quiet >= 2:
            return {"idle": True, "acknowledged": interrupt, "idle_samples": quiet,
                    "acknowledgement_count": len(acknowledgements), "interrupted_count": sum(acknowledgements),
                    "seconds": round(time.monotonic() - started, 3), "seconds_remaining": deadline - time.monotonic()}
        time.sleep(.1)
    raise RuntimeError("Background runtime did not become idle within cancellation bound")


def python_dependencies():
    """A venv contains package code/answers; only expose the base interpreter."""
    paths = [Path(sys.base_prefix).resolve(), Path(sys.executable).resolve()]
    config = Path(sys.prefix) / "pyvenv.cfg"
    if config.is_file(): paths.append(config.resolve())
    return list(dict.fromkeys(paths))


def record_native_process(logs, output, errors, returncode):
    """Preserve bounded disposable diagnostics even when native startup fails."""
    output, errors = output or b"", errors or b""
    limits = {"stdout": 2 * 1024**2, "stderr": 64 * 1024}
    receipt = {"exit_code": returncode}
    private = {}
    for name, value in (("stdout", output), ("stderr", errors)):
        receipt[name + "_observed_bytes"] = len(value)
        receipt[name + "_truncated"] = len(value) > limits[name]
        private[name] = value[:limits[name]].decode(errors="replace")
    state._write_new(Path(logs) / "native-process.json", {**receipt, **private})
    return receipt


def safe_run_telemetry(metadata):
    """Strict content-free receipt: never serialize prompts, answers or raw APIs."""
    import math
    number = lambda value: type(value) in {int, float} and math.isfinite(value)
    value = {key: metadata[key] for key in ("schema", "policy", "reflection", "requested_model", "requested_variant",
             "champion_revision", "started_unix", "finished_unix", "elapsed_seconds", "error_class") if key in metadata}
    if type(metadata.get("dispatch_evidence_complete")) is bool:
        value["dispatch_evidence_complete"] = metadata["dispatch_evidence_complete"]
    value["requests"] = []
    for request in metadata.get("requests", [])[:128]:
        item = {key: request[key] for key in ("max_tokens", "started", "tool_count") if number(request.get(key))}
        item["numeric"] = {key: request["numeric"][key] for key in ("max_tokens", "temperature", "top_p", "top_k", "min_p", "presence_penalty", "repetition_penalty")
                           if number(request.get("numeric", {}).get(key))}
        thinking = request.get("thinking", {}).get("enable_thinking")
        if type(thinking) is bool: item["enable_thinking"] = thinking
        schema_hash = request.get("tool_schema_sha256")
        if isinstance(schema_hash, str) and len(schema_hash) == 64 and all(c in "0123456789abcdef" for c in schema_hash):
            item["tool_schema_sha256"] = schema_hash
        value["requests"].append(item)
    value["settlement"] = {key: result for key in ("idle", "acknowledged", "idle_samples", "acknowledgement_count", "interrupted_count", "seconds", "seconds_remaining")
                           if (result := metadata.get("settlement", {}).get(key)) is not None and (type(result) is bool or number(result))}
    value["native_process"] = {key: result for key in ("exit_code", "stdout_observed_bytes", "stderr_observed_bytes", "stdout_truncated", "stderr_truncated")
                               if (result := metadata.get("native_process", {}).get(key)) is not None and (type(result) is bool or number(result))}
    value["resources"] = [{key: sample[key] for key in ("pressure_level", "swap_used_bytes") if number(sample.get(key))}
                           for sample in metadata.get("samples", [])[-256:]]
    for target, source in zip(value["resources"], metadata.get("samples", [])[-256:]):
        target["listeners"] = [{key: process[key] for key in ("pid", "rss_bytes", "phys_footprint_bytes") if number(process.get(key))}
                               for process in source.get("listener_processes", [])[:2]]
    return value


def native_turn(directory, config, workspace, prompt, champion, seconds, *, reflection=False):
    """Keep bounded local receipts even when a real native attempt raises."""
    started = time.monotonic()
    metadata = {"schema": 1, "policy": POLICY["version"], "reflection": reflection,
                "requested_model": config["providers"]["local"]["models"]["qwen"]["modelID"],
                "requested_variant": POLICY["reflection_variant"] if reflection else configured_reference(config)[1],
                "champion_revision": champion["revision"], "started_unix": time.time()}
    try:
        return _native_turn(directory, config, workspace, prompt, champion, seconds, reflection=reflection, telemetry=metadata)
    except BaseException as error:
        metadata["error_class"] = type(error).__name__
        raise
    finally:
        metadata.update(finished_unix=time.time(), elapsed_seconds=round(time.monotonic()-started, 3))
        logs = state._directory(Path(workspace).parent / "evidence")
        state._write_new(logs / "telemetry.json", safe_run_telemetry(metadata))


def _native_turn(directory, config, workspace, prompt, champion, seconds, *, reflection=False, telemetry):
    """One genuine native session; no custom tool/agent loop."""
    from native_client import NativeServer, BINARY, background_boundary
    from context_probe import ResourceGuard, resources, summarize_resources
    model_id = config["providers"]["local"]["models"]["qwen"]["modelID"]
    reference, variant = configured_reference(config)
    if reflection:
        variant = POLICY["reflection_variant"]
        available = {item["id"] for item in config["providers"]["local"]["models"]["qwen"].get("variants", [])}
        if variant not in available:
            raise RuntimeError("The frozen reflection variant is absent; no fallback is permitted")
        reference = "local/qwen#" + variant
    started = time.monotonic()
    logs = state._directory(Path(workspace).parent / "evidence")
    dependencies = [BINARY.parent.parent.resolve(), *python_dependencies()]
    for item in config.get("plugins", []):
        if isinstance(item, dict) and Path(item.get("package", "")).is_absolute():
            dependencies.append(Path(item["package"]).resolve())
    result = {"passed": False, "native_completed": False, "seconds": 0, "conditions_verified": False,
              "cache_matched": False, "reason": "incomplete", "text": "", "requests": []}
    guard = ResourceGuard(512 * 1024**2, 2)
    samples = []
    telemetry["samples"] = samples
    model_output = config["providers"]["local"]["models"]["qwen"].get("limit", {}).get("output", 4096)
    token_limit = min(model_output, POLICY["reflection_tokens"]) if reflection else model_output
    with InferenceRelay(model_id, token_limit, seconds, tools_allowed=not reflection) as relay:
        telemetry["requests"] = relay.records
        effective = plugin_config(config, champion, workspace, f"http://127.0.0.1:{relay.port}/v1")
        if reflection:
            effective["permissions"] = [{"action": "*", "resource": "*", "effect": "deny"}]
            effective["agents"]["build"]["permissions"] = effective["permissions"]
            effective["agents"]["build"]["model"] = reference
            model = effective["providers"]["local"]["models"]["qwen"]
            model["body"]["max_tokens"] = token_limit
            for variant_config in model.get("variants", []):
                variant_config.setdefault("body", {})["max_tokens"] = token_limit
        state._write_new(logs / "requested-config.json", effective)
        for n in range(3):
            if foreground_requested(directory): raise RuntimeError("Background preflight yielded")
            sample = resources("http://127.0.0.1:8000")
            samples.append(sample)
            if guard.check(sample) or sample.get("pressure_level") != 1:
                raise RuntimeError("Learning resource preflight failed")
            if n < 2: time.sleep(2)
        with NativeServer(workspace, effective, log=logs / "native.log", background={"dependencies": dependencies, "inference_port": relay.port, "cancel": lambda: foreground_requested(directory)}) as server:
            # A named native session skips automatic title inference, which would
            # contend with the primary request at the single-generation relay.
            create = {"model": {"providerID": "local", "id": "qwen", "variant": variant}, "agent": "build",
                      "title": "KRYN background reflection" if reflection else "KRYN background trial",
                      "location": {"directory": str(workspace)}}
            if reflection: create["permissions"] = [{"action": "*", "resource": "*", "effect": "deny"}]
            session = server.request("POST", "/api/session", create, timeout=3)["data"]
            sid = session["id"]
            command = server.background_prefix + [str(BINARY), "run", "--server", server.url, "--session", sid, "--agent", "build", "--model", reference, "--format", "json"]
            child = subprocess.Popen(command, cwd=workspace, env=server.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            interrupted, first, output, errors, next_sample, settlement_attempted = False, True, b"", b"", time.monotonic(), False
            try:
                while True:
                    now = time.monotonic()
                    if foreground_requested(directory) or now - started > seconds:
                        result["reason"] = "foreground_yield" if foreground_requested(directory) else "timeout"
                        interrupted = True; break
                    if now >= next_sample:
                        sample = resources("http://127.0.0.1:8000"); samples.append(sample)
                        if guard.check(sample):
                            result["reason"] = "resource_guard"; interrupted = True; break
                        next_sample = now + 2
                        size = sum(p.stat().st_size for p in Path(workspace).rglob("*") if p.is_file() and not p.is_symlink())
                        if size > 64 * 1024**2:
                            result["reason"] = "disk_budget"; interrupted = True; break
                    try:
                        output, errors = child.communicate(prompt.encode() if first else None, timeout=.25)
                        break
                    except subprocess.TimeoutExpired as error:
                        first = False
                        output, errors = error.output or b"", error.stderr or b""
                        if len(output) > 2 * 1024**2 or len(errors) > 64 * 1024:
                            result["reason"] = "output_budget"; interrupted = True; break
                settlement_attempted = True
                settlement = settle_background(server, sid, Path(workspace), relay, interrupt=interrupted)
                telemetry["settlement"] = settlement
                if interrupted:
                    relay.cancel()
                result["settled"] = settlement["idle"]
                if not interrupted and child.returncode == 0:
                    exported = server.request("GET", f"/api/experimental/session/{sid}/export", timeout=3)["data"]
                    assistants = [m for m in exported["messages"] if m.get("type") == "assistant"]
                    complete = bool(assistants and assistants[-1].get("finish") == "stop" and exported["info"].get("outcome") == "succeeded"
                                    and all(m.get("model", {}).get("providerID") == "local" and m.get("model", {}).get("id") == "qwen"
                                            and not m.get("error") for m in assistants))
                    result.update(native_completed=complete, conditions_verified=complete and bool(relay.records) and all(s.get("pressure_level") == 1 for s in samples), reason="completed" if complete else "incomplete")
                    if assistants:
                        result["text"] = "".join(p.get("text", "") for p in assistants[-1].get("content", []) if p.get("type") == "text")[:8192]
                    # Disposable diagnostics only; no personal conversation is exported.
                    if len(output) <= 2 * 1024**2:
                        (logs / "native-events.jsonl").write_bytes(output)
                result["requests"] = relay.records
            finally:
                if child.poll() is None:
                    child.terminate()
                    try: child.wait(timeout=2)
                    except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=2)
                try:
                    if not settlement_attempted:
                        telemetry["settlement"] = settle_background(server, sid, Path(workspace), relay, interrupt=True)
                        relay.cancel()
                finally:
                    telemetry["native_process"] = record_native_process(logs, output, errors, child.returncode)
            # Grading uses another sandboxed process, with no model/network access.
            result["grading_prefix"] = background_boundary(workspace, Path(server.temporary.name), python_dependencies(), None)
            result["seconds"] = round(time.monotonic() - started, 3)
            if not reflection and result["native_completed"]:
                # Expected answers remain in this unsandboxed trusted worker.
                result["grade"] = grade(workspace, read(Path(workspace).parent / "case.json")["family"],
                                        read(Path(workspace).parent / "case.json")["split"] == "protected", prefix=result["grading_prefix"],
                                        cancel=lambda: foreground_requested(directory))
                result["passed"] = result["grade"]["passed"]
                if foreground_requested(directory):
                    result.update(reason="foreground_yield", passed=False, conditions_verified=False)
            result.pop("grading_prefix", None)
    # Set only after normal relay shutdown and owned native-process settlement.
    # Exceptions or missing receipts never justify a free candidate attempt.
    telemetry["dispatch_evidence_complete"] = True
    result["seconds"] = round(time.monotonic() - started, 3)
    result["resources"] = summarize_resources(samples)
    return result


def power_ready():
    """Fail closed when power/thermal state cannot be established cheaply."""
    try:
        battery = subprocess.run(["/usr/bin/pmset", "-g", "batt"], text=True, capture_output=True, timeout=3)
        thermal = subprocess.run(["/usr/bin/pmset", "-g", "therm"], text=True, capture_output=True, timeout=3)
        return battery.returncode == thermal.returncode == 0 and "AC Power" in battery.stdout and ("No thermal warning" in thermal.stdout or "Thermal pressure: Nominal" in thermal.stdout)
    except (OSError, subprocess.SubprocessError):
        return False


def prune(directory):
    base, now = root(directory), time.time()
    for name in ("events", "decisions"):
        folder = state._directory(base / name)
        rows = sorted((p for p in folder.glob("*.json") if not p.is_symlink()), key=lambda p: p.stat().st_mtime)
        for path in rows:
            if path.stat().st_mtime < now - POLICY["metadata_days"] * 86400 or len(rows) > POLICY["metadata_records"] and path in rows[:-POLICY["metadata_records"]]:
                state._regular(path); path.unlink()
    folder = state._directory(base / "runs")
    runs = sorted((p for p in folder.iterdir() if p.is_dir() and not p.is_symlink()), key=lambda p: p.stat().st_mtime)
    sizes = {p: sum(f.stat().st_size for f in p.rglob("*") if f.is_file() and not f.is_symlink()) for p in runs}
    import shutil
    for path in runs:
        if path.stat().st_mtime < now - POLICY["raw_days"] * 86400 or sum(sizes.values()) > POLICY["raw_bytes"]:
            # Only worker-marked disposable directories may be removed.
            if read(path / "owned.json", {}).get("owner") != "kryn-learning-v1":
                continue
            if any(p.is_symlink() for p in path.rglob("*")):
                continue
            shutil.rmtree(path); sizes.pop(path)


def new_run(directory):
    folder = state._directory(root(directory) / "runs" / uuid.uuid4().hex)
    state._write_new(folder / "owned.json", {"owner": "kryn-learning-v1"})
    workspace = state._directory(folder / "workspace")
    return folder, workspace


def charge(directory, started):
    value = budget(directory)
    value["seconds"] += max(0, time.monotonic() - started)
    put(root(directory) / "budget.json", value)


def run_case(directory, config, case, champion, seconds, turn):
    folder, workspace = new_run(directory)
    state._write_new(folder / "case.json", case)
    prompt, source, _ = fixture(case["family"], case["split"] == "protected")
    (workspace / "solve.py").write_text(source)
    started = time.monotonic()
    try:
        result = turn(directory, config, workspace, prompt, champion, seconds)
    except Exception as error:
        result = {"passed": False, "native_completed": False, "conditions_verified": False,
                  "reason": "infrastructure_" + type(error).__name__, "seconds": round(time.monotonic() - started, 3)}
    finally: charge(directory, started)
    row = {**case, **{k: result.get(k) for k in ("passed", "native_completed", "conditions_verified", "cache_matched", "reason", "seconds")},
           "profile_sha256": digest(config), "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
           "initial_source_sha256": hashlib.sha256(source.encode()).hexdigest(), "champion_revision": champion["revision"],
           "request_metadata_sha256": digest(result.get("requests", []))}
    state._write_new(folder / "receipt.json", row)
    return row


def monitor_champion(directory, config, turn):
    """Two failures trigger two real paired disposable probes, never direct rollback."""
    base = root(directory)
    champion = _champion(directory)
    if champion == BASELINE: return
    seen = set(read(base / "monitor-consumed.json", []))
    observed = [event for event in events(directory) if event["champion_revision"] == champion["revision"]
                and event["family"] == "json_cli"
                and event["task_id"] not in seen and (event["check_failures"] or event["tool_errors"])]
    probe = read(base / "monitor.json")
    if probe is None:
        if len(observed) < 2: return
        version = state._load(base / "versions" / (champion["revision"] + ".json"))
        probe = {"revision": champion["revision"], "previous": version["previous"], "profile_sha256": digest(config),
                 "observations": [e["task_id"] for e in observed], "rows": []}
        put(base / "monitor.json", probe)
    if probe["revision"] != champion["revision"] or probe["profile_sha256"] != digest(config):
        record_decision(directory, champion["revision"], "defer", "monitor_conditions_changed")
        return
    plan = [{"family": "collections", "repeat": n, "arm": arm, "split": "monitor"}
            for n in range(2) for arm in (("previous", "current") if n == 0 else ("current", "previous"))]
    for case in plan[len(probe["rows"]):]:
        remaining = POLICY["day_seconds"] - budget(directory)["seconds"]
        if remaining < 15 or foreground_requested(directory) or not power_ready():
            record_decision(directory, champion["revision"], "defer", "monitor_budget_or_foreground")
            return
        selected = champion if case["arm"] == "current" else probe["previous"]
        row = run_case(directory, config, case, selected, min(POLICY["trial_seconds"], remaining), turn)
        probe["rows"].append(row); put(base / "monitor.json", probe)
        if row["reason"] == "foreground_yield": return
    pairs = []
    for repeat in range(2):
        arms = {row["arm"]: row for row in probe["rows"] if row["repeat"] == repeat}
        pairs.append({"previous_passed": bool(arms["previous"]["passed"] and arms["previous"]["conditions_verified"]),
                      "current_passed": arms["current"]["passed"] if arms["current"]["conditions_verified"] else None})
    if all(p["previous_passed"] and p["current_passed"] is False for p in pairs):
        rollback(directory, champion["revision"], pairs)
    else:
        record_decision(directory, champion["revision"], "defer", "regression_not_reproduced", rows_sha256=digest(probe["rows"]))
    seen.update(probe["observations"]); put(base / "monitor-consumed.json", sorted(seen)[-500:])
    put(base / "monitor.json", None)


def worker(directory, config, *, turn=native_turn):
    """Finite idle work. Budget exhaustion and uncertainty cause durable deferral."""
    base = root(directory)
    with state._lock(base, "worker.lock", True, True):
        put(base / "worker.json", {"pid": os.getpid(), "state": "debouncing", "started_unix": time.time()})
        try:
            deadline = time.monotonic() + POLICY["idle_seconds"]
            while time.monotonic() < deadline:
                if foreground_requested(directory): return
                time.sleep(min(.25, max(0, deadline - time.monotonic())))
            if not power_ready() or foreground_requested(directory): return
            with state.foreground(directory):
                if foreground_requested(directory): return
                prune(directory)
                monitor_champion(directory, config, turn)
                if foreground_requested(directory): return
                queue = read(base / "queue.json", [])
                if not queue:
                    observed = [e for e in events(directory) if meaningful(e)]
                    consumed = set(read(base / "consumed.json", []))
                    observed = [e for e in observed if e["task_id"] not in consumed]
                    allowance = budget(directory)
                    if not observed or allowance["candidates"] >= POLICY["candidates_per_day"] or allowance["seconds"] >= POLICY["day_seconds"]: return
                    item = observed[-1]
                    folder, workspace = new_run(directory)
                    prompt = ("Analyze this bounded diagnostic metadata from real local work. Do not invent missing content. "
                              "Propose at most one short reusable verification/workflow instruction for disposable JSON CLI programming, "
                              "or defer. Never change security, permissions, providers, credentials, graders, executable code or user files. "
                              'Return ONLY JSON {"decision":"propose|defer","instructions":"...","scope":"disposable_json_cli",'
                              '"reason":"repeated_tool_failure|verification_gap|context_inefficiency|insufficient_evidence"}. Metadata: ' + json.dumps(item))
                    started = time.monotonic()
                    result, error_class = {}, None
                    reservation = reserve_reflection_attempt(directory, item)
                    try:
                        result = turn(directory, config, workspace, prompt, BASELINE, min(POLICY["reflection_seconds"], POLICY["day_seconds"] - allowance["seconds"]), reflection=True)
                    except BaseException as error:
                        error_class = type(error).__name__
                        if not isinstance(error, Exception): raise
                    finally:
                        time_charged = False
                        try:
                            charge(directory, started)
                            time_charged = True
                        finally:
                            attempt = finish_reflection_attempt(directory, folder, item, result, reservation, error_class,
                                                                time_charged=time_charged)
                    if not result.get("native_completed") or not result.get("conditions_verified"):
                        reason = "reflection_incomplete" if attempt["candidate_spent"] else "reflection_startup_no_dispatch"
                        record_decision(directory, None, "defer", reason, attempt_id=folder.name, **attempt); return
                    try: candidate = parse_proposal(result["text"])
                    except (ValueError, KeyError):
                        record_decision(directory, None, "defer", "invalid_reflection"); return
                    if candidate["decision"] == "defer":
                        record_decision(directory, candidate["revision"], "defer", candidate["reason"]); return
                    candidate.update(observation_sha256=digest(item), created_unix=time.time(), champion=active_champion(directory, scope=candidate["scope"]),
                                     profile_sha256=digest(config), rows=[], plan=selection_plan(candidate["revision"]))
                    queue = [candidate]; put(base / "queue.json", queue)
                if len(queue) > POLICY["queue"]: raise RuntimeError("Learning queue exceeded bound")
                candidate = queue[0]
                if candidate["profile_sha256"] != digest(config):
                    record_decision(directory, candidate["revision"], "defer", "profile_changed_new_comparison_required")
                    put(base / "queue.json", queue[1:]); return
                for case in candidate["plan"]["trials"][len(candidate["rows"]):]:
                    allowance = budget(directory)
                    remaining = POLICY["day_seconds"] - allowance["seconds"]
                    if foreground_requested(directory) or remaining < 15 or not power_ready():
                        record_decision(directory, candidate["revision"], "defer", "foreground_or_resource_budget", completed_trials=len(candidate["rows"])); return
                    if case["split"] == "protected":
                        decision, reason = decide(candidate["rows"])
                        if decision != "defer" or reason != "protected_checks_required":
                            record_decision(directory, candidate["revision"], decision, reason, rows_sha256=digest(candidate["rows"]))
                            put(base / "queue.json", queue[1:]); return
                        if not candidate.get("holdout_started"):
                            used = read(base / "holdout-budget.json", {"policy": POLICY["version"], "candidates": []})
                            if used["policy"] != POLICY["version"] or candidate["revision"] in used["candidates"] or len(used["candidates"]) >= POLICY["holdout_candidates_per_suite"]:
                                record_decision(directory, candidate["revision"], "defer", "fresh_protected_suite_required")
                                put(base / "queue.json", queue[1:]); return
                            used["candidates"].append(candidate["revision"]); put(base / "holdout-budget.json", used)
                            candidate["holdout_started"] = True; put(base / "queue.json", queue)
                    champion = candidate["champion"] if case["arm"] == "baseline" else {k: candidate[k] for k in ("revision", "instructions")}
                    row = run_case(directory, config, case, champion, min(POLICY["trial_seconds"], remaining), turn)
                    candidate["rows"].append(row); put(base / "queue.json", queue)
                    if row.get("reason") == "foreground_yield":
                        record_decision(directory, candidate["revision"], "defer", "foreground_yield", completed_trials=len(candidate["rows"])); return
                decision, reason = decide(candidate["rows"], protected_complete=True)
                if decision == "accept": promote(directory, candidate, candidate["rows"])
                else: record_decision(directory, candidate["revision"], decision, reason, rows_sha256=digest(candidate["rows"]))
                put(base / "queue.json", queue[1:])
        finally:
            put(base / "worker.json", {"pid": os.getpid(), "state": "stopped", "finished_unix": time.time()})


def start_after_exit(directory, config):
    """Detach only the finite owned worker; no daemon/LaunchAgent is installed."""
    base = root(directory)
    try:
        with state._lock(base, "worker.lock", True, True):
            # Keep retention bounded even when observations never merit learning.
            prune(directory)
    except state.Deferred:
        return None
    controls = read(base / "control.json", dict(DEFAULT_CONTROLS))
    if not controls["enabled"] or controls["paused"]: return None
    consumed = set(read(base / "consumed.json", []))
    pending = bool(read(base / "queue.json", []) or read(base / "monitor.json"))
    if not pending and not any(meaningful(e) and e["task_id"] not in consumed for e in events(directory)):
        return None
    allowance = budget(directory)
    if allowance["seconds"] >= POLICY["day_seconds"] or not pending and allowance["candidates"] >= POLICY["candidates_per_day"]:
        return None
    # The child acquires worker.lock itself; concurrent duplicate exits fail closed there.
    path = base / "worker-config.json"
    put(path, config)
    from native_client import _open_owned_log
    log = base / "worker.log"
    if log.exists() and state._regular(log).st_size > 65536:
        log.unlink()  # Owned metadata-only errors; decisions remain separately versioned.
    with _open_owned_log(log) as output:
        proc = subprocess.Popen([sys.executable, "-E", "-B", str(Path(__file__).resolve()), "--worker", str(Path(directory).resolve())],
                                cwd=base, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home())}, start_new_session=True)
    return proc.pid


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args(argv)
    if args.worker is None: parser.error("Only the owned worker entrypoint is supported")
    try: worker(args.worker, state._load(root(args.worker) / "worker-config.json"))
    except state.Deferred: return 0
    except Exception as error:
        record_decision(args.worker, None, "defer", "worker_" + type(error).__name__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
