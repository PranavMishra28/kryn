"""Bounded, evidence-owned acceptance for one native OpenCode Agent session.

OpenCode owns generation and tools.  This client waits for a native idle record,
runs caller-owned checks, and returns a status that model prose cannot change.
"""

from dataclasses import dataclass
from fnmatch import fnmatchcase
import hashlib
import json
import os
from pathlib import Path
import subprocess
import stat
import tempfile
import time
from urllib.parse import quote


class AcceptanceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Requirement:
    id: str
    source: str
    checks: tuple[str, ...]
    capability: str = "general"
    source_file: str | None = None


@dataclass(frozen=True)
class CommandCheck:
    id: str
    argv: tuple[str, ...]
    timeout: int = 120
    watch: tuple[str, ...] = ("*",)

    def affected_by(self, path):
        return any(fnmatchcase(path, pattern) for pattern in self.watch)

    def run(self, workspace):
        if not self.argv or self.timeout < 1 or self.timeout > 600:
            raise AcceptanceError("Invalid check command or timeout: " + self.id)
        try:
            result = subprocess.run(self.argv, cwd=workspace, capture_output=True, text=True,
                                    errors="replace", timeout=self.timeout, check=False)
        except subprocess.TimeoutExpired:
            return {"status": "blocked", "detail": "check timed out"}
        except OSError as error:
            return {"status": "blocked", "detail": type(error).__name__ + ": " + str(error)}
        detail = (result.stdout + "\n" + result.stderr).strip()[-3000:]
        return {"status": "passed" if result.returncode == 0 else "failed",
                "exit_code": result.returncode, "detail": detail}


def source_state(workspace):
    """Fingerprint current changed paths and HEAD; ignored runtime files stay out."""
    workspace = Path(workspace).resolve()
    def git(*args):
        return subprocess.run(("git", *args), cwd=workspace, capture_output=True, check=True).stdout
    try:
        head = git("rev-parse", "HEAD").strip().decode("ascii")
        paths = set(git("diff", "HEAD", "--name-only", "-z").split(b"\0"))
        paths.update(git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0"))
    except subprocess.CalledProcessError as error:
        raise AcceptanceError("Acceptance requires a readable Git worktree") from error
    paths.discard(b"")
    if len(paths) > 256:
        raise AcceptanceError("Too many changed files for source-bound evidence")
    fingerprints = {}
    for raw in sorted(paths):
        relative = Path(os.fsdecode(raw))
        path = workspace / relative
        if relative.is_absolute() or ".." in relative.parts or not path.resolve().is_relative_to(workspace):
            raise AcceptanceError("Changed path escapes the project")
        if path.is_symlink():
            value = b"symlink\0" + os.fsencode(os.readlink(path))
        elif path.is_file():
            if path.stat().st_size > 2 * 1024 * 1024:
                raise AcceptanceError("Changed file is too large for source-bound evidence")
            value = b"file\0" + str(stat.S_IMODE(path.stat().st_mode)).encode() + b"\0" + path.read_bytes()
        elif not path.exists():
            value = b"deleted\0"
        else:
            raise AcceptanceError("Changed path is not a regular file")
        fingerprints[relative.as_posix()] = hashlib.sha256(value).hexdigest()
    return {"head": head, "paths": fingerprints}


def source_revision(workspace):
    """Hash a source snapshot, including executable bits and untracked files."""
    state = source_state(workspace)
    digest = hashlib.sha256(state["head"].encode() + b"\0")
    for path, fingerprint in sorted(state["paths"].items()):
        digest.update(os.fsencode(path) + b"\0" + fingerprint.encode() + b"\0")
    return digest.hexdigest()


class AcceptanceController:
    def __init__(self, server, session_id, workspace, report_path, requirements, checks,
                 *, max_repairs=2, turn_timeout=1200, poll_interval=.3, revision=source_revision,
                 state=source_state, cancelled=lambda: False):
        self.server, self.session_id = server, session_id
        self.workspace = Path(workspace).resolve()
        self.report_path = Path(report_path).resolve()
        if self.report_path.is_relative_to(self.workspace):
            raise AcceptanceError("Acceptance evidence must live outside the Agent workspace")
        self.requirements = tuple(requirements)
        checks = tuple(checks)
        self.checks = {check.id: check for check in checks}
        self.max_repairs, self.turn_timeout = max_repairs, turn_timeout
        self.poll_interval, self.revision, self.source_state = poll_interval, revision, state
        self.cancelled = cancelled
        if (not 0 <= max_repairs <= 3 or not 1 <= turn_timeout <= 3600 or
                not self.requirements or not self.checks or
                len(self.checks) != len(checks) or
                len({req.id for req in self.requirements}) != len(self.requirements) or
                any(not req.id or not isinstance(req.source, str) or not req.source.strip() or
                    not req.checks or any(check not in self.checks for check in req.checks)
                    for req in self.requirements)):
            raise AcceptanceError("Every distinct requirement needs at least one declared check")
        if any(not check.watch or any(not pattern or pattern.startswith("/") or ".." in Path(pattern).parts
                                       for pattern in check.watch) for check in checks):
            raise AcceptanceError("Every check needs a bounded workspace watch pattern")
        for req in self.requirements:
            if req.source_file is None:
                continue
            path = self.workspace / req.source_file
            if (Path(req.source_file).is_absolute() or ".." in Path(req.source_file).parts or
                    not path.resolve().is_relative_to(self.workspace) or not path.is_file() or
                    path.read_text() != req.source):
                raise AcceptanceError("Requirement source file differs from admitted text: " + req.id)

    def admission_text(self, prompt):
        """Admit only distinct task obligations, never check commands or oracles."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise AcceptanceError("Managed task needs the original user request")
        additional = [req for req in self.requirements if req.source.strip() not in prompt]
        if not additional:
            return prompt
        return prompt.rstrip() + "\n\nCurrent acceptance requirements:\n" + "\n".join(
            f"[{req.id}] {req.source.strip()}" for req in additional)

    def request(self, method, path, body=None):
        return self.server.request(method, path, body, timeout=5)

    def save(self, report):
        self.report_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile("w", dir=self.report_path.parent, prefix=".acceptance-",
                                         delete=False) as output:
            temp = Path(output.name)
            try:
                os.fchmod(output.fileno(), 0o600)
                json.dump(report, output, indent=2)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            except BaseException:
                temp.unlink(missing_ok=True)
                raise
        temp.replace(self.report_path)

    def latest_messages(self):
        sid = quote(self.session_id, safe="")
        return self.request("GET", f"/api/session/{sid}/message?limit=100&order=desc")["data"]

    def wait_for_idle(self, previous):
        sid = quote(self.session_id, safe="")
        deadline = time.monotonic() + self.turn_timeout
        while time.monotonic() < deadline:
            if self.cancelled():
                self.request("POST", f"/api/session/{sid}/interrupt", {})
                raise AcceptanceError("Resource guard stopped the managed Agent turn")
            messages = self.latest_messages()
            idle = next((m for m in messages if m.get("type") == "idle" and m.get("id") not in previous), None)
            active = self.request("GET", "/api/session/active")["data"]
            inbox = self.request("GET", f"/api/session/{sid}/inbox")["data"]
            if idle is not None and not active and not inbox:
                return idle
            if self.request("GET", f"/api/session/{sid}/permission")["data"] or \
                    self.request("GET", f"/api/session/{sid}/form")["data"]:
                raise AcceptanceError("Agent is waiting for a permission or form response")
            time.sleep(self.poll_interval)
        self.request("POST", f"/api/session/{sid}/interrupt", {})
        raise AcceptanceError("Native Agent turn exceeded the managed timeout")

    def send(self, text, *, repair=False):
        sid = quote(self.session_id, safe="")
        previous = {m["id"] for m in self.latest_messages() if m.get("type") == "idle"}
        endpoint = "synthetic" if repair else "prompt"
        body = ({"text": text, "description": "KRYN observed verification failure", "resume": True}
                if repair else {"text": text})
        admitted = self.request("POST", f"/api/session/{sid}/{endpoint}", body)["data"]
        idle = self.wait_for_idle(previous)
        if idle.get("outcome") != "succeeded":
            raise AcceptanceError("Native Agent turn ended " + str(idle.get("outcome")))
        return admitted["id"], idle["id"]

    def verify(self, previous_state=None, previous_outcomes=None):
        before = self.revision(self.workspace)
        current = self.source_state(self.workspace)
        previous_outcomes = previous_outcomes or {}
        changed = (set(current["paths"]) | set(previous_state["paths"])) if previous_state else set(current["paths"])
        if previous_state:
            changed = {path for path in changed if current["paths"].get(path) != previous_state["paths"].get(path)}
        full_invalidation = (previous_state is None or current["head"] != previous_state["head"] or
                             any(not any(check.affected_by(path) for check in self.checks.values())
                                 for path in changed))
        altered_sources = [req.source_file for req in self.requirements if req.source_file and
                           (not (self.workspace / req.source_file).is_file() or
                            (self.workspace / req.source_file).read_text() != req.source)]
        outcomes = {}
        for name, check in self.checks.items():
            if self.cancelled():
                raise AcceptanceError("Resource guard stopped managed verification")
            previous = previous_outcomes.get(name)
            if altered_sources:
                result = {"status": "failed", "detail": "Restore requirement source: " + ", ".join(altered_sources)}
            elif (not full_invalidation and previous and previous["status"] == "passed" and
                  not any(check.affected_by(path) for path in changed)):
                result = {**previous, "reused": True}
            else:
                result = check.run(self.workspace)
                result["evidence_revision"] = before
                result["reused"] = False
            if result.get("status") not in {"passed", "failed", "blocked"}:
                raise AcceptanceError("Check returned no authoritative status: " + name)
            outcomes[name] = result
        if self.cancelled():
            raise AcceptanceError("Resource guard stopped managed verification")
        after = self.revision(self.workspace)
        final_state = self.source_state(self.workspace)
        if after != before or final_state != current:
            for result in outcomes.values():
                result["status"] = "stale"
                result["detail"] = "Project source changed during verification"
        return after, final_state, sorted(changed), outcomes

    def run(self, prompt, *, initial=None, admitted_prompt=None):
        expected_admission = self.admission_text(prompt)
        if initial is not None and admitted_prompt != expected_admission:
            raise AcceptanceError("Native first turn did not use the admitted requirements")
        info = self.request("GET", "/api/session/" + quote(self.session_id, safe=""))["data"]
        if info.get("id") != self.session_id or \
                Path(info.get("location", {}).get("directory", "")).resolve() != self.workspace or \
                info.get("agent") not in {"agent", "build"}:
            raise AcceptanceError("Managed session identity, workspace or Agent role changed")
        report = {"session_id": self.session_id, "workspace": str(self.workspace),
                  "request_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                  "admitted_sha256": hashlib.sha256(expected_admission.encode()).hexdigest(),
                  "state": "working", "accepted": False, "rounds": [],
                  "requirements": [{"id": req.id, "source": req.source, "source_file": req.source_file,
                                    "capability": req.capability, "checks": list(req.checks),
                                    "status": "unrun", "evidence": {}} for req in self.requirements]}
        self.save(report)
        feedback = expected_admission
        prior_state = prior_outcomes = None
        try:
            for cycle in range(self.max_repairs + 1):
                turn_started = time.monotonic()
                admission, idle = initial if cycle == 0 and initial is not None else \
                    self.send(feedback, repair=cycle > 0)
                turn_seconds = (None if cycle == 0 and initial is not None else
                                round(time.monotonic() - turn_started, 3))
                if self.cancelled():
                    raise AcceptanceError("Resource guard stopped managed verification")
                report["state"] = "verifying"
                self.save(report)
                verify_started = time.monotonic()
                revision, prior_state, changed, outcomes = self.verify(prior_state, prior_outcomes)
                verify_seconds = round(time.monotonic() - verify_started, 3)
                prior_outcomes = outcomes
                for record in report["requirements"]:
                    states = [outcomes[key]["status"] for key in record["checks"]]
                    record["status"] = "passed" if all(s == "passed" for s in states) else \
                        "stale" if "stale" in states else "blocked" if "blocked" in states else "failed"
                    record["evidence"] = {key: {"status": outcomes[key]["status"],
                                                 "revision": outcomes[key].get("evidence_revision"),
                                                 "reused": outcomes[key].get("reused", False)}
                                          for key in record["checks"]}
                report["rounds"].append({"cycle": cycle, "admission_id": admission,
                                         "idle_id": idle, "source_revision": revision,
                                         "turn_seconds": turn_seconds, "verify_seconds": verify_seconds,
                                         "changed_paths": changed, "checks": outcomes})
                if all(r["status"] == "passed" for r in report["requirements"]):
                    if self.revision(self.workspace) != revision or self.source_state(self.workspace) != prior_state:
                        raise AcceptanceError("Project source changed before acceptance")
                    report["state"], report["accepted"] = "accepted", True
                    self.save(report)
                    return report
                if cycle == self.max_repairs:
                    break
                report["state"] = "repair_required"
                self.save(report)
                failed = [f"{name} ({item['status']}): {item.get('detail', '')[:900]}"
                          for name, item in outcomes.items() if item["status"] != "passed"]
                obligations = [f"{record['id']} [{record['status']}]: " + ", ".join(
                    key for key in record["checks"] if outcomes[key]["status"] != "passed")
                    for record in report["requirements"] if record["status"] != "passed"]
                feedback = ("Independent verification is incomplete at source revision " + revision + ".\n" +
                            "Requirements: " + "; ".join(obligations) + "\nObserved failures:\n" +
                            "\n".join(failed) + "\nChanged paths: " + ", ".join(changed))
        except Exception as error:
            report["error"] = type(error).__name__ + ": " + str(error)
        report["state"] = "blocked"
        self.save(report)
        return report
