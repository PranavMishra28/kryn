#!/usr/bin/env python3
"""Local outcomes, isolated skill proposals and objective promotion controls; no inference.

No autonomous improvement or live quality claim follows from these controls.
Only evaluator-issued receipts can promote one versioned native skill. No runtime,
configuration, permission or credential is modified; existing grades are not proof.
"""
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
import uuid

RETENTION_DAYS = 30
MAX_RECORDS = 500
MAX_CANDIDATES = 20
COMMANDS = {"init", "doctor", "status", "stop", "bench", "run"}
STATUSES = {"success", "failure", "interrupted", "incomplete"}
FAILURES = {"none", "runtime", "config", "tools", "resource", "timeout", "verification", "interrupted", "unknown"}
FIELDS = {"command", "status", "wall_seconds", "exit_code", "failure_code", "interventions",
          "pressure_warning_samples", "swap_growth_bytes", "release_id", "profile_id"}
HYPOTHESES = {
    "verification": ("verify_before_summary", "Run the task's relevant existing checks before the final summary. State which checks actually ran, their results, and any unverified requirement. Never change a check merely to obtain a pass."),
    "timeout": ("bounded_milestone", "Complete one useful milestone with observable checks before expanding scope. After two unsuccessful repair attempts without new evidence, preserve the failure and report the next bounded hypothesis."),
    "tools": ("check_tool_contract", "Read the available tool schema before calling an unfamiliar tool. Supply required fields and inspect its actual result before making a dependent call. Do not invent tool results."),
}


class Deferred(RuntimeError):
    """A foreground owner has priority over optional proposal work."""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _directory(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RuntimeError("Improvement state refuses symlink paths")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise RuntimeError("Improvement state must be an owned, non-shared directory")
    return path


def _regular(path):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_nlink != 1 or info.st_mode & 0o022):
        raise RuntimeError("Refusing changed or linked improvement artifact")
    return info


def _load(path):
    if _regular(path).st_size > 65536:
        raise RuntimeError("Improvement metadata exceeds its bound")
    return json.loads(path.read_text())


def _write_new(path, value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(data)


@contextlib.contextmanager
def _lock(root, name, exclusive, nonblocking=False):
    root = _directory(root)
    path = root / name
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        _regular(path)
        flags = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        try:
            fcntl.flock(fd, flags | (fcntl.LOCK_NB if nonblocking else 0))
        except BlockingIOError as exc:
            raise Deferred("Foreground work is active; optional improvement deferred") from exc
        yield root
    finally:
        os.close(fd)


@contextlib.contextmanager
def foreground(state_dir):
    """Hold during one native foreground session; overlapping work cannot enter.

    No background inference exists here. Optional operations only do bounded local
    metadata work while holding this same nonblocking exclusive lock.
    """
    with _lock(state_dir, "foreground.lock", True, True):
        yield


def _number(value, *, integer=False, nullable=False):
    if value is None and nullable:
        return value
    types = (int,) if integer else (int, float)
    if type(value) not in types or not math.isfinite(value) or value < 0:
        raise ValueError("Expected a finite nonnegative numeric outcome field")
    return value


def _outcome(value):
    if not isinstance(value, dict) or set(value) - FIELDS:
        raise ValueError("Outcome fields are allowlisted; private content is not accepted")
    if value.get("command") not in COMMANDS or value.get("status") not in STATUSES:
        raise ValueError("Unknown outcome command/status")
    out = dict(value)
    out["wall_seconds"] = _number(out.get("wall_seconds"))
    out.setdefault("failure_code", "none" if out["status"] == "success" else "unknown")
    if out["failure_code"] not in FAILURES:
        raise ValueError("Unknown failure code")
    if out["status"] != "success" and out["failure_code"] == "none":
        raise ValueError("A non-success outcome needs a failure classification")
    for key in ("interventions", "pressure_warning_samples", "swap_growth_bytes"):
        out[key] = _number(out.get(key, 0 if key == "interventions" else None), integer=True, nullable=key != "interventions")
    exit_code = out.get("exit_code")
    if exit_code is not None and (type(exit_code) is not int or not -255 <= exit_code <= 255):
        raise ValueError("Invalid exit code")
    out["exit_code"] = exit_code
    for key in ("release_id", "profile_id"):
        token = out.get(key)
        if token is not None and (not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{8,64}", token)):
            raise ValueError("Release/profile IDs must be hexadecimal, never paths")
        out[key] = token
    return out


def _records(root):
    folder = _directory(root / "records")
    result = []
    for path in sorted(folder.iterdir()):
        if not re.fullmatch(r"[0-9]{20}-[0-9a-f]{32}\.json", path.name):
            continue  # Unknown user files are never interpreted or removed.
        item = _load(path)
        if set(item) != {"schema", "id", "unix", "outcome"} or item["schema"] != 1:
            raise RuntimeError("Changed outcome record")
        if path.stem.split("-", 1)[1] != item["id"]:
            raise RuntimeError("Outcome record identity mismatch")
        _number(item["unix"])
        _outcome(item["outcome"])
        result.append((path, item))
    return result


def record_outcome(state_dir, outcome):
    """Persist strictly content-free metadata, not proof of task correctness."""
    clean = _outcome(outcome)
    with _lock(state_dir, "records.lock", True) as root:
        now = time.time()
        record = {"schema": 1, "id": uuid.uuid4().hex, "unix": now, "outcome": clean}
        folder = _directory(root / "records")
        _write_new(folder / f"{time.time_ns():020d}-{record['id']}.json", record)
        records = _records(root)
        keep = [path for path, item in records if item["unix"] >= now - RETENTION_DAYS * 86400][-MAX_RECORDS:]
        for path, _ in records:
            if path not in keep:
                _regular(path)
                path.unlink()
        return record


def observations(state_dir):
    """Return counts only; hidden case records and answers never enter reflection."""
    with _lock(state_dir, "records.lock", True) as root:
        rows = [item["outcome"] for _, item in _records(root)
                if item["unix"] >= time.time() - RETENTION_DAYS * 86400][-20:]
    groups = {}
    for row in rows:
        if row["command"] not in {"run", "bench"} or row["status"] == "success":
            continue
        key = (row["failure_code"], row["release_id"], row["profile_id"])
        groups[key] = groups.get(key, 0) + 1
    return [{"failure_code": key[0], "release_id": key[1], "profile_id": key[2], "count": count,
             "candidate_hypothesis": HYPOTHESES[key[0]][0] if key[0] in HYPOTHESES and all(key[1:]) else None}
            for key, count in groups.items() if count >= 2]


def _skill(hypothesis):
    choices = {name: text for name, text in HYPOTHESES.values()}
    if hypothesis not in choices:
        raise ValueError("Only reviewed instruction hypotheses may be staged")
    return ("---\nname: kryn-verified-work\ndescription: A bounded software-work verification reminder.\n---\n\n"
            + choices[hypothesis] + "\n").encode()


def _candidate(root, candidate_id):
    if not isinstance(candidate_id, str) or not re.fullmatch(r"[0-9a-f]{64}", candidate_id):
        raise ValueError("Invalid candidate ID")
    folder = root / "candidates" / candidate_id
    if not folder.is_dir() or any(p.is_symlink() for p in (folder, *folder.parents)):
        raise RuntimeError("Unknown isolated candidate")
    meta = _load(folder / "candidate.json")
    data = _skill(meta["hypothesis"])
    _regular(folder / "SKILL.md")
    if _sha(data) != candidate_id or (folder / "SKILL.md").read_bytes() != data:
        raise RuntimeError("Candidate was changed after staging")
    return folder, meta


def propose(state_dir, hypothesis):
    """Stage a fixed SKILL artifact; it is never added to native skill search paths."""
    data = _skill(hypothesis)
    with _lock(state_dir, "foreground.lock", True, True) as root:
        matched = [item for item in observations(root) if item["candidate_hypothesis"] == hypothesis]
        if not matched:
            raise RuntimeError("No repeated, release-bound failure supports this hypothesis")
        parent = _directory(root / "candidates")
        candidate_id = _sha(data)
        folder = parent / candidate_id
        if folder.exists():
            _candidate(root, candidate_id)
            return candidate_id
        if len(list(parent.iterdir())) >= MAX_CANDIDATES:
            raise RuntimeError("Candidate retention limit reached; review existing proposals first")
        folder.mkdir(mode=0o700)
        fd = os.open(folder / "SKILL.md", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(data)
        _write_new(folder / "candidate.json", {"schema": 1, "hypothesis": hypothesis, "sha256": candidate_id,
                   "observations": matched, "created_unix": time.time(), "active": False})
        return candidate_id


def register_case(state_dir, candidate_id, split, run_manifest):
    """Bind an existing bench-prepared case without copying answers/source.

    Registration is not evaluation. Different task IDs are required across splits;
    a run cannot move between splits or be silently reused as hidden evidence.
    """
    if split not in {"development", "validation", "hidden"}:
        raise ValueError("Unknown evaluation split")
    run_manifest = Path(run_manifest)
    if any(p.is_symlink() for p in (run_manifest, *run_manifest.parents)):
        raise ValueError("Refusing a linked run manifest")
    if _regular(run_manifest).st_size > 65536:
        raise ValueError("Oversized run manifest")
    data = run_manifest.read_bytes()
    run = json.loads(data)
    if (not re.fullmatch(r"\d{2}", str(run.get("task", ""))) or run["task"] not in {f"{n:02d}" for n in range(1, 13)}
            or not isinstance(run.get("initial_hashes"), dict) or not run["initial_hashes"]
            or not re.fullmatch(r"[0-9a-f]{64}", str(run.get("suite_manifest_sha256", "")))):
        raise ValueError("Expected an existing frozen-bench run manifest")
    if any(not re.fullmatch(r"[0-9a-f]{64}", str(value)) for value in run["initial_hashes"].values()):
        raise ValueError("Invalid seed hash")
    receipt = {"schema": 1, "split": split, "run_sha256": _sha(data), "task": run["task"],
               "suite_sha256": run["suite_manifest_sha256"], "evaluated": False, "registered_unix": time.time()}
    with _lock(state_dir, "foreground.lock", True, True) as root:
        folder, _ = _candidate(root, candidate_id)
        for path in folder.glob("case-*.json"):
            prior = _load(path)
            if prior["run_sha256"] == receipt["run_sha256"] or (prior["task"] == receipt["task"] and prior["split"] != split):
                raise RuntimeError("Development/validation/hidden cases must remain disjoint")
            if prior["suite_sha256"] != receipt["suite_sha256"]:
                raise RuntimeError("Cannot mix frozen suite versions")
        _write_new(folder / ("case-" + receipt["run_sha256"] + ".json"), receipt)
    return receipt


def reject(state_dir, candidate_id, reason="insufficient_evidence"):
    if reason not in {"insufficient_evidence", "regression", "no_benefit", "objective_failure"}:
        raise ValueError("Rejection reasons are content-free enums")
    with _lock(state_dir, "foreground.lock", True, True) as root:
        folder, _ = _candidate(root, candidate_id)
        _write_new(folder / "decision.json", {"decision": "reject", "reason": reason, "unix": time.time()})


def status(state_dir):
    root = _directory(state_dir)
    active = active_skill_directory(root)
    with _lock(root, "records.lock", True):
        count = len(_records(root))
    return {"schema": 1, "outcome_records": count, "retention_days": RETENTION_DAYS,
            "max_records": MAX_RECORDS, "retention_trigger": "next_outcome_write",
            "repeated_failures": observations(root),
            "promotion_enabled": True, "promotion_requires_objective_receipt": True,
            "autonomous_reflection": False, "active_skill": active is not None,
            "background_inference": False, "complete_improvement_loop": False,
            "blocker": "live_matched_skill_evaluation_and_autonomous_cycle_not_qualified",
            "raw_traces_collected": False}

# The following controls execute the existing frozen grader, never an agent loop.
# Simulated fixture receipts can exercise promotion/rollback only in simulation/.
SUITE_SHA256 = "186fd74343eff01992b48ac7d29b9a01ed7543968da6048745e6c42e1ec63ab6"
CHECKER_SHA256 = "cda93b02753efc0a19743e443c7dc75e3a6049a885b9c7d84293138ab6f8b8cd"
_ISSUED = {}


class _Evaluation:
    @property
    def summary(self):
        return json.loads(json.dumps(_ISSUED[self]["report"]))


def skill_prompt(task_text, candidate_id=None, hypothesis=None):
    """Prospective native fresh-user prompt, with exactly one declared treatment."""
    if candidate_id is None:
        return task_text
    data = _skill(hypothesis)
    if _sha(data) != candidate_id:
        raise ValueError("Candidate identity mismatch")
    return task_text + "\n<skill_content>\n" + data.decode() + "</skill_content>\n"


def _suite(path):
    root = Path(path).absolute()
    manifest = root / "frozen.sha256.json"
    if _sha(manifest.read_bytes()) != SUITE_SHA256:
        raise RuntimeError("Unrecognized frozen evaluator")
    expected = _load(manifest)
    for name, digest in expected.items():
        item = root / name
        if not item.resolve().is_relative_to(root.resolve()) or any(p.is_symlink() for p in (item, *item.parents)):
            raise RuntimeError("Evaluator contains a redirected path")
        _regular(item)
        if _sha(item.read_bytes()) != digest:
            raise RuntimeError("Frozen evaluator drift")
    if _sha((root / "checks.py").read_bytes()) != CHECKER_SHA256:
        raise RuntimeError("Unexpected objective checker")
    return root, json.loads((root / "tasks.json").read_text())


def _snapshot(folder):
    result = {}
    for path in sorted(folder.rglob("*")):
        if ".git" in path.relative_to(folder).parts or "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            raise RuntimeError("Evaluation refuses linked artifacts")
        if path.is_file():
            _regular(path)
            result[str(path)] = _sha(path.read_bytes())
    return result


def _native_exposure(run, stage, expected_prompt):
    """Source-backed fresh-user exposure, not a claim of captured wire messages."""
    from datetime import datetime
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", stage):
        raise ValueError("Simple stage name required")
    folder = run / "evidence" / stage
    driver = _load(folder / "driver.json")
    if any(driver.get(key) is not True for key in ("completed", "model_completed", "routing_verified")):
        raise RuntimeError("Native run did not complete cleanly")
    if driver.get("interventions") != 0 or not driver.get("acceptance_checks") or not all(driver["acceptance_checks"].values()):
        raise RuntimeError("Native intervention or incomplete acceptance")
    if (folder / "prompt.txt").read_text() != expected_prompt or driver.get("prompt_sha256") != _sha(expected_prompt.encode()):
        raise RuntimeError("Unexpected treatment prompt")
    expected_audit = {"server.js": "5647fbfd400103e7433e36f56ae48f921425ad8a9c3edce93e4e17f65fe61ee8",
                      "package.json": "a90fc33418afa2b9cbf4768524b021135b965ecdf993457505bfae3ac44a8428"}
    if driver.get("audit_plugin_sha256") != expected_audit or any(
            _sha((folder / "audit-plugin" / name).read_bytes()) != digest for name, digest in expected_audit.items()):
        raise RuntimeError("Actual route audit implementation differs from the pinned source")
    exports = list(folder.glob("*.export.json"))
    if len(exports) != 1:
        raise RuntimeError("Only one fresh, non-delegated session is admitted")
    exported = _load_large(exports[0])["data"]
    info, messages = exported["info"], exported["messages"]
    users = [m for m in messages if m.get("type") == "user"]
    assistants = [m for m in messages if m.get("type") == "assistant"]
    if (len(users) != 1 or users[0].get("text") != expected_prompt or users[0].get("files")
            or any(m.get("type") == "compaction" for m in messages) or not assistants
            or info.get("parentID") or info.get("outcome") != "succeeded"
            or Path(info.get("location", {}).get("directory", "")).resolve() != (run / "workspace").resolve()):
        raise RuntimeError("Exposure requires one fresh user turn without compaction or children")
    if any(m.get("time", {}).get("created", 0) < users[0]["time"]["created"] for m in assistants):
        raise RuntimeError("Prior assistant history is not matched fresh exposure")
    for message in assistants:
        if (message.get("error") or message.get("finish") not in {"stop", "tool-calls"}
                or not message.get("time", {}).get("completed")
                or message.get("model", {}).get("providerID") != "local"
                or message.get("model", {}).get("id") != "qwen"):
            raise RuntimeError("Incomplete or nonlocal native generation")
    if assistants[-1]["finish"] != "stop":
        raise RuntimeError("No completed final answer")
    audit = [json.loads(line) for line in (folder / "inference.jsonl").read_text().splitlines() if line]
    if (sum(e.get("event") == "ready" for e in audit) != 1 or sum(e.get("event") == "closed" for e in audit) != 1
            or any(e.get("ok") is False or e.get("event") in {"retry", "unexpected.websocket"} for e in audit)):
        raise RuntimeError("Incomplete or failing route audit")
    sid = info["id"]
    for kind in ("model.request", "http.request", "http.response", "wire.options"):
        events = [e for e in audit if e.get("event") == kind]
        if len(events) != len(assistants) or any(e.get("kind") != "primary" or e.get("sessionID") != sid for e in events):
            raise RuntimeError("Unexplained helper/child/missing inference")
        if kind in {"model.request", "http.request"} and any(e.get("ok") is not True or not e.get("destination", "").startswith("http://127.0.0.1:8000/v1") for e in events):
            raise RuntimeError("Nonlocal route")
        if kind == "http.response" and any(e.get("status") != 200 for e in events):
            raise RuntimeError("Inference response failed")
    closed = next(e for e in audit if e.get("event") == "closed")
    if datetime.fromisoformat(closed["time"].replace("Z", "+00:00")).timestamp() * 1000 < assistants[-1]["time"]["completed"]:
        raise RuntimeError("Audit closed before completion")
    wire = next(e for e in audit if e.get("event") == "wire.options")
    if wire.get("captureOnly") is not False or wire.get("requestModelID") != driver.get("expected_model_id"):
        raise RuntimeError("No actual intended-model request")
    samples = [json.loads(line) for line in (folder / "resources.jsonl").read_text().splitlines() if line]
    if (not samples or any(sample.get("pressure_level") != 1 or type(sample.get("swap_used_bytes")) is not int
                              or len(sample.get("listener_processes", [])) != 1 for sample in samples)
            or len({sample["listener_processes"][0].get("pid") for sample in samples}) != 1
            or max(sample["swap_used_bytes"] for sample in samples) - samples[0]["swap_used_bytes"] > 512 * 1024**2):
        raise RuntimeError("Raw resource samples do not meet the frozen guard")
    if not samples or driver.get("resources", {}).get("telemetry_complete") is not True or driver.get("resources", {}).get("warning_or_critical_observed") is not False:
        raise RuntimeError("Missing resource qualification")
    if driver["resources"].get("swap_peak_growth_bytes", 2**63) > 512 * 1024**2:
        raise RuntimeError("Swap bound failed")
    config = _load_large(folder / "requested-config.json")
    for plugin in config.get("plugins", []):
        if isinstance(plugin, dict) and plugin.get("options", {}).get("log") == str(folder / "inference.jsonl"):
            plugin["package"] = "<frozen-audit-plugin>"
            plugin["options"]["log"] = "<owned-stage-log>"
    condition = _sha(json.dumps({"config": config, "audit_plugin": driver.get("audit_plugin_sha256"),
             "model": driver.get("expected_model_id"), "agent": driver.get("agent"), "variant": driver.get("variant"),
             "wire": {key: wire.get(key) for key in ("numeric", "thinking", "preserveThinking", "effort", "toolsSha256")}}, sort_keys=True).encode())
    return condition, users[0]["time"]["created"] / 1000


def _load_large(path):
    if _regular(path).st_size > 32 * 1024**2:
        raise RuntimeError("Oversized native evidence")
    return json.loads(path.read_text())


@contextlib.contextmanager
def _checker_boundary(suite, project, workspace, simulation):
    import tempfile
    if simulation:
        # Test-only evaluator execution cannot run arbitrary candidate Python.
        for path in workspace.rglob("*.py"):
            reference = suite / "fixture" / path.relative_to(workspace)
            if not reference.is_file():
                raise RuntimeError("Simulation requires unchanged frozen fixture code")
            allowed = {reference.read_bytes()}
            if path.name == "report.py":
                allowed.add(reference.read_bytes().replace(b'r["date"] < end', b'r["date"] <= end'))
            if path.read_bytes() not in allowed:
                raise RuntimeError("Simulation fixture code differs from the frozen source")
        yield [], {"PATH": "/usr/bin:/bin", "HOME": str(workspace), "PYTHONDONTWRITEBYTECODE": "1"}
        return
    import native_client
    task_tmp, private = project / (".localai-tmp-" + uuid.uuid4().hex), project / ("private-" + uuid.uuid4().hex)
    task_tmp.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    env = native_client.environment()
    env.update(LOCALAI_TASK_TMP=str(task_tmp), TMPPREFIX=str(task_tmp / "zsh"),
               TMPDIR=str(task_tmp), TMP=str(task_tmp), TEMP=str(task_tmp),
               MAC_CHROMIUM_TMPDIR=str(private), BREAKPAD_DUMP_LOCATION=str(private),
               PWTEST_SERVER_REGISTRY=str(private / "pw-registry"))
    prefix, _ = native_client._sandbox_prefix(project, private, task_tmp, env)
    yield prefix, env


def _check(suite, task, workspace, simulation=False):
    """Run the pinned checker on an exact disposable copy, never the original."""
    import shutil
    import tempfile
    source = _snapshot(workspace)
    if sum(Path(path).stat().st_size for path in source) > 50 * 1024**2:
        raise RuntimeError("Evaluation workspace exceeds the 50 MiB bound")
    started = time.monotonic()
    project = Path(tempfile.mkdtemp(prefix="kryn-objective-")).resolve()
    retained = False
    try:
        copied = project / "workspace"
        shutil.copytree(workspace, copied, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        expected = {str(Path(path).relative_to(workspace)): digest for path, digest in source.items()}
        actual = {str(Path(path).relative_to(copied)): digest for path, digest in _snapshot(copied).items()}
        if actual != expected:
            raise RuntimeError("Disposable evaluator copy differs")
        with _checker_boundary(suite, project, copied, simulation) as (prefix, env):
            return _run_checker(prefix, env, suite, task, copied, started)
    except _CheckerCleanupError:
        retained = True
        raise RuntimeError("Owned evaluator group did not settle; retained private copy: " + str(project))
    finally:
        if not retained:
            shutil.rmtree(project)


class _CheckerCleanupError(RuntimeError):
    pass


def _settle_checker(proc):
    import signal
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            proc.wait(timeout=5)
            return
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            proc.poll()  # Reap the leader; its exit alone is not group settlement.
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                proc.wait(timeout=5)
                return
            time.sleep(0.05)
    raise _CheckerCleanupError("Owned evaluator process group remains")


def _run_checker(prefix, env, suite, task, workspace, started):
    import signal
    import subprocess
    import sys
    import tempfile
    # The fixed checker prints one final result object; raw output is ephemeral.
    counts = {"01": 2, "02": 2, "03": 3, "04": 4, "05": 3, "06": 2,
              "07": 0, "08": 1, "09": 1, "10": 5, "11": 0, "12": 2}
    with tempfile.TemporaryFile(dir=workspace) as output:
        proc = subprocess.Popen(prefix + [sys.executable, "-E", "-B", str(suite / "checks.py"), task, str(workspace)],
                                cwd=workspace, env=env, stdout=output, stderr=subprocess.DEVNULL,
                                start_new_session=True)
        try:
            while True:
                if output.tell() > 65536 or time.monotonic() - started > 120:
                    raise RuntimeError("Objective checker exceeded output/time bound")
                try:
                    code = proc.wait(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    pass
            output.seek(0)
            raw = output.read(65537)
            try:
                counters = json.loads(raw.decode().splitlines()[-1])
            except (ValueError, IndexError):
                counters = {}
            complete = len(raw) <= 65536 and counters.get("tests_run") == counts[task] and counts[task] > 0
            passed = (complete and code == 0 and counters.get("passed") is True
                      and counters.get("failures") == 0 and counters.get("errors") == 0)
            return {"passed": bool(passed), "exit_code": code, "checker_completed": complete,
                    "tests_run": counters.get("tests_run") if type(counters.get("tests_run")) is int else None,
                    "seconds": round(time.monotonic() - started, 3)}
        finally:
            try:
                _settle_checker(proc)
            except BaseException as error:
                raise _CheckerCleanupError("Owned evaluator group settlement failed") from error


def evaluate(state_dir, candidate_id, pairs, *, suite_root, simulation=False):
    """Explicit foreground evaluation of three predeclared matched pairs.

    Each pair is {split, baseline: run-path, candidate: run-path, stage}. Simulation
    omits native exposure only and can never create a production activation.
    This is not a scheduler: it starts no model, browser or improvement agent.
    """
    if type(simulation) is not bool or len(pairs) != 3 or {p.get("split") for p in pairs} != {"development", "validation", "hidden"}:
        raise ValueError("Exactly three predeclared development/validation/hidden pairs required")
    with _lock(state_dir, "foreground.lock", True, True) as root:
        folder, meta = _candidate(root, candidate_id)
        if (folder / "decision.json").exists():
            raise RuntimeError("Rejected candidate cannot be promoted")
        suite, tasks = _suite(suite_root)
        rows, snapshots, seen, task_splits, conditions = [], {}, set(), {}, set()
        registrations, starts, snapshot_roots = [], [], {}
        for pair in pairs:
            results, fingerprints = [], []
            for arm in ("baseline", "candidate"):
                run = Path(pair[arm]).resolve()
                if run in seen:
                    raise RuntimeError("Evaluation arms/cases must be distinct")
                seen.add(run)
                run_meta = _load(run / "run.json")
                task = run_meta["task"]
                if task not in tasks or (tasks[task]["manual"] and not simulation) or run_meta.get("suite_manifest_sha256") != SUITE_SHA256:
                    raise RuntimeError("Unqualified/manual-only or changed suite case")
                if not simulation and task in task_splits and task_splits[task] != pair["split"]:
                    raise RuntimeError("Hidden/development task reuse")
                task_splits[task] = pair["split"]
                workspace = run / "workspace"
                for name in ("test_existing.py", "data/entries.csv", "TASK.md"):
                    if _sha((workspace / name).read_bytes()) != run_meta["initial_hashes"][name]:
                        raise RuntimeError("Original checks/data/prompt changed")
                task_text = (workspace / "TASK.md").read_text()
                if task_text != tasks[task]["prompt"] + "\n":
                    raise RuntimeError("Frozen task prompt changed")
                fingerprints.append((task, run_meta["initial_hashes"]))
                if not simulation:
                    prompt = skill_prompt(task_text, candidate_id, meta["hypothesis"]) if arm == "candidate" else task_text
                    case = _load(folder / ("case-" + _sha((run / "run.json").read_bytes()) + ".json"))
                    if case["split"] != pair["split"] or case["task"] != task:
                        raise RuntimeError("Case was not registered in this split")
                    registrations.append(case["registered_unix"])
                    condition, first_user = _native_exposure(run, pair["stage"], prompt)
                    conditions.add(condition)
                    starts.append(first_user)
                before = _snapshot(workspace)
                result = _check(suite, task, workspace, simulation)
                if _snapshot(workspace) != before:
                    raise RuntimeError("Objective checker changed candidate source/artifacts")
                snapshots.update(before)
                snapshot_roots[str(workspace)] = before
                stage_snapshot = _snapshot(run / "evidence")
                snapshots.update(stage_snapshot)
                snapshot_roots[str(run / "evidence")] = stage_snapshot
                snapshots[str(run / "run.json")] = _sha((run / "run.json").read_bytes())
                results.append(result)
            if fingerprints[0] != fingerprints[1]:
                raise RuntimeError("Unmatched initial seed/task")
            rows.append({"split": pair["split"], "baseline": results[0], "candidate": results[1]})
        if not simulation and (len(conditions) != 1 or max(registrations) >= min(starts)):
            raise RuntimeError("Model/role/tool/runtime request conditions differ")
        _suite(suite)  # Recheck after executing candidate code through the grader.
        snapshots.update({str(suite / name): digest for name, digest in _load(suite / "frozen.sha256.json").items()})
        snapshots[str(suite / "frozen.sha256.json")] = SUITE_SHA256
        accepted = all(row["candidate"]["passed"] for row in rows) and any(
            row["split"] == "validation" and not row["baseline"]["passed"] for row in rows)
        report = {"schema": 1, "simulation": simulation, "candidate_id": candidate_id,
                  "objective_results": rows, "accepted": accepted, "suite_sha256": SUITE_SHA256,
                  "exposure": "simulation_only" if simulation else "source_backed_fresh_native_user_turn",
                  "condition_sha256": next(iter(conditions), None), "unix": time.time()}
        receipt_path = folder / ("evaluation-" + uuid.uuid4().hex + ".json")
        _write_new(receipt_path, report)
        receipt = _Evaluation()
        _ISSUED[receipt] = {"root": root, "candidate_id": candidate_id, "report": report,
                            "snapshots": snapshots, "snapshot_roots": snapshot_roots, "receipt_path": receipt_path,
                            "receipt_sha": _sha(receipt_path.read_bytes())}
        return receipt


def _active_path(root, simulation):
    return root / ("simulation-active.json" if simulation else "active.json")


def _version(root, active):
    version, candidate_id = active.get("version", ""), active.get("candidate_id", "")
    if not re.fullmatch(r"[0-9a-f]{32}", version):
        raise RuntimeError("Invalid active version")
    _, meta = _candidate(root, candidate_id)
    base = root / ("simulation" if active.get("simulation") is True else "versions") / version
    skills = base / "skills"
    leaf = skills / "kryn-verified-work"
    for directory in (base, skills, leaf):
        if not directory.is_dir() or any(p.is_symlink() for p in (directory, *directory.parents)):
            raise RuntimeError("Native skill directory was redirected")
        _directory(directory)
    if sorted(p.name for p in skills.iterdir()) != ["kryn-verified-work"] or sorted(p.name for p in leaf.iterdir()) != ["SKILL.md"]:
        raise RuntimeError("Only the evaluated native skill may be loaded")
    skill = leaf / "SKILL.md"
    _regular(skill)
    if skill.read_bytes() != _skill(meta["hypothesis"]):
        raise RuntimeError("Promoted skill drift; preserve for operator inspection")
    return base / "skills"


def _replace_pointer(path, value, expected):
    if path.is_symlink():
        raise RuntimeError("Preserving linked active pointer")
    if path.exists():
        _regular(path)
    current = path.read_bytes() if path.exists() else None
    if current != expected:
        raise RuntimeError("Active version drift; refusing overwrite")
    if current is not None:
        _regular(path)
    if value is None:
        if current is not None:
            path.unlink()
        return
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex)
    _write_new(temporary, value)
    os.replace(temporary, path)


def promote(state_dir, candidate_id, evidence=None):
    """Only an unconsumed evaluator-issued in-memory receipt can authorize a switch."""
    if not isinstance(evidence, _Evaluation) or evidence not in _ISSUED:
        raise RuntimeError("Promotion unavailable: an objective evaluator-issued receipt is required")
    verified = _ISSUED[evidence]
    with _lock(state_dir, "foreground.lock", True, True) as root:
        if verified["root"] != root or verified["candidate_id"] != candidate_id or not verified["report"]["accepted"]:
            raise RuntimeError("Rejected or foreign evaluation")
        folder, meta = _candidate(root, candidate_id)
        if (folder / "decision.json").exists() or _sha(verified["receipt_path"].read_bytes()) != verified["receipt_sha"]:
            raise RuntimeError("Evaluation decision drift")
        if any(_snapshot(Path(path)) != expected for path, expected in verified["snapshot_roots"].items()):
            raise RuntimeError("Evaluated artifacts changed, including added/removed files")
        if any(not Path(p).is_file() or _sha(Path(p).read_bytes()) != digest for p, digest in verified["snapshots"].items()):
            raise RuntimeError("Evaluated artifacts changed")
        simulation = verified["report"]["simulation"]
        pointer = _active_path(root, simulation)
        if pointer.is_symlink():
            raise RuntimeError("Preserving linked active pointer")
        previous = _load(pointer) if pointer.exists() else None
        before = pointer.read_bytes() if previous is not None else None
        if previous:
            _version(root, previous)
        version = uuid.uuid4().hex
        skill_dir = _directory(root / ("simulation" if simulation else "versions") / version / "skills/kryn-verified-work")
        data = _skill(meta["hypothesis"])
        fd = os.open(skill_dir / "SKILL.md", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o400)
        with os.fdopen(fd, "wb") as output:
            output.write(data)
        active = {"schema": 1, "version": version, "candidate_id": candidate_id, "simulation": simulation,
                  "previous": previous, "evaluation_sha256": verified["receipt_sha"],
                  "condition_sha256": verified["report"]["condition_sha256"]}
        _replace_pointer(pointer, active, before)
        del _ISSUED[evidence]
        return {"promoted": True, "simulation": simulation, "version": version, "native_active": not simulation}


def active_skill_directory(state_dir):
    root = _directory(state_dir)
    path = _active_path(root, False)
    if not path.exists() and not path.is_symlink():
        return None
    active = _load(path)
    if active.get("simulation") is not False:
        raise RuntimeError("Simulation cannot activate a native skill")
    return _version(root, active)


def _rollback_locked(root, simulation, expected_version=None):
    pointer = _active_path(root, simulation)
    if not pointer.exists() and not pointer.is_symlink():
        return {"changed": False, "reason": "no_promoted_artifact", "rollback_chain_verified": False}
    before = pointer.read_bytes()
    active = _load(pointer)
    _version(root, active)
    if expected_version is not None and active["version"] != expected_version:
        raise RuntimeError("Active version changed during monitoring")
    previous = active.get("previous")
    if previous:
        _version(root, previous)
    _replace_pointer(pointer, previous, before)
    _write_new(root / ("rollback-" + uuid.uuid4().hex + ".json"),
               {"schema": 1, "version": active["version"], "simulation": simulation, "unix": time.time()})
    return {"changed": True, "simulation": simulation, "restored_version": previous.get("version") if previous else None}


def rollback(state_dir, *, simulation=False):
    with _lock(state_dir, "foreground.lock", True, True) as root:
        return _rollback_locked(root, simulation)


def monitor(state_dir, run, *, stage, suite_root, simulation=False):
    """Explicit objective regression check; no scheduler or inference is started."""
    with _lock(state_dir, "foreground.lock", True, True) as root:
        pointer = _active_path(root, simulation)
        active = _load(pointer)
        _version(root, active)
        _, meta = _candidate(root, active["candidate_id"])
        suite, tasks = _suite(suite_root)
        run = Path(run).resolve()
        run_meta = _load(run / "run.json")
        task = run_meta["task"]
        if task not in tasks or run_meta.get("suite_manifest_sha256") != SUITE_SHA256 or (tasks[task]["manual"] and not simulation):
            raise RuntimeError("Unqualified monitoring case")
        if not simulation:
            prompt = skill_prompt(tasks[task]["prompt"] + "\n", active["candidate_id"], meta["hypothesis"])
            if _native_exposure(run, stage, prompt)[0] != active["condition_sha256"]:
                raise RuntimeError("Monitoring conditions changed")
        workspace = run / "workspace"
        for name in ("test_existing.py", "data/entries.csv", "TASK.md"):
            if _sha((workspace / name).read_bytes()) != run_meta["initial_hashes"][name]:
                raise RuntimeError("Monitoring original checks/data/prompt changed")
        result = _check(suite, task, workspace, simulation)
        _suite(suite)
        if not result["passed"]:
            return {"objective": result, "rollback": _rollback_locked(root, simulation, active["version"])}
        return {"objective": result, "rollback": None}


def main(argv=None):
    """Small explicit operator surface; evaluation never invokes a model."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--state", type=Path, default=Path.home() / "Library/Application Support/LocalAI/state/improvement")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "observe"):
        commands.add_parser(name)
    proposal = commands.add_parser("propose")
    proposal.add_argument("hypothesis", choices=sorted(name for name, _ in HYPOTHESES.values()))
    registration = commands.add_parser("register")
    registration.add_argument("candidate")
    registration.add_argument("split", choices=("development", "validation", "hidden"))
    registration.add_argument("run_manifest", type=Path)
    rejection = commands.add_parser("reject")
    rejection.add_argument("candidate")
    rejection.add_argument("--reason", default="insufficient_evidence", choices=("insufficient_evidence", "regression", "no_benefit", "objective_failure"))
    for name in ("evaluate", "promote"):
        command = commands.add_parser(name)
        command.add_argument("candidate")
        command.add_argument("--plan", type=Path, required=True, help="Three predeclared matched pair objects; never PASS results")
        command.add_argument("--suite", type=Path, required=True)
        command.add_argument("--simulation", action="store_true")
    command = commands.add_parser("monitor")
    command.add_argument("run", type=Path)
    command.add_argument("--stage", required=True)
    command.add_argument("--suite", type=Path, required=True)
    command.add_argument("--simulation", action="store_true")
    command = commands.add_parser("rollback")
    command.add_argument("--simulation", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "status": result = status(args.state)
        elif args.command == "observe": result = observations(args.state)
        elif args.command == "propose": result = {"candidate": propose(args.state, args.hypothesis), "active": False}
        elif args.command == "register": result = register_case(args.state, args.candidate, args.split, args.run_manifest)
        elif args.command == "reject":
            reject(args.state, args.candidate, args.reason)
            result = {"decision": "reject"}
        elif args.command in {"evaluate", "promote"}:
            receipt = evaluate(args.state, args.candidate, _load(args.plan), suite_root=args.suite, simulation=args.simulation)
            result = receipt.summary
            if args.command == "promote":
                result["activation"] = promote(args.state, args.candidate, receipt)
        elif args.command == "monitor": result = monitor(args.state, args.run, stage=args.stage, suite_root=args.suite, simulation=args.simulation)
        else: result = rollback(args.state, simulation=args.simulation)
        print(json.dumps(result, sort_keys=True))
        return 0 if not isinstance(result, dict) or result.get("accepted", True) else 1
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(json.dumps({"status": "refused", "error": type(error).__name__, "reason": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
