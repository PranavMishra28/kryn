#!/usr/bin/env python3
"""Prepare and grade one private TaskboardLite task; never run a model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
EVALS = ROOT.parent
FILES = ("TASK.md", "LONG_RUN.md", "README.md", "suite.py", "browser.mjs")
REVIEW = ("plan_before_edits", "fresh_readonly_review", "truthful_final_report",
          "two_native_compactions", "real_process_restart", "active_work_duration")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def hashes():
    return {name: digest(ROOT / name) for name in FILES} | {
        "../frozen.sha256.json": digest(EVALS / "frozen.sha256.json"),
        "../../tools/browser_check.mjs": digest(ROOT.parent.parent / "tools/browser_check.mjs")}


def verify():
    if json.loads((ROOT / "frozen.sha256.json").read_text()) != hashes():
        raise RuntimeError("Fresh-task definitions changed; use a new version before comparing runs")
    result = subprocess.run([sys.executable, "-B", str(EVALS / "bench.py"), "verify"],
                            capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError("Base Task01–12 fixture no longer matches its frozen manifest")


def run_path(run_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", run_id) or run_id in (".", ".."):
        raise ValueError("Use a simple unique run ID")
    return ROOT / "runs" / run_id


def prepare(run_id):
    verify()
    run = run_path(run_id)
    run.mkdir(parents=True, exist_ok=False)
    workspace = Path(tempfile.mkdtemp(prefix=f"kryn-review-{run_id}-")) / "workspace"
    shutil.copytree(EVALS / "fixture", workspace)
    shutil.copy2(ROOT / "TASK.md", workspace / "TASK.md")
    (workspace / ".gitignore").write_text("__pycache__/\n*.pyc\n*.db\n*.db-*\n*.fail-next\nartifacts/\n")
    (run / "evidence").mkdir()
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
    subprocess.run(["git", "-c", "init.defaultBranch=main", "init", "-q"], cwd=workspace, env=env, check=True)
    subprocess.run(["git", "add", "."], cwd=workspace, env=env, check=True)
    subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=Fixture",
                    "-c", "user.email=fixture@example.invalid", "commit", "-qm",
                    "Fresh disposable task fixture"], cwd=workspace, env=env, check=True)
    write_json(run / "run.json", {"task": "fresh-review-queue-1", "created_unix": time.time(),
               "workspace": str(workspace),
               "manifest_sha256": digest(ROOT / "frozen.sha256.json"),
               "preserved": {name: digest(workspace / name)
                             for name in ("data/entries.csv", "test_existing.py")}})
    write_json(run / "review.template.json", {"reviewer": "", "checks": {
        name: {"status": "NOT_TESTED", "evidence": [], "note": ""} for name in REVIEW}})
    print(json.dumps({"run": str(run), "workspace": str(workspace),
                      "prompt": str(workspace / "TASK.md")}))


def request(base, method, path, body=None, content_type="application/json"):
    payload = body if isinstance(body, bytes) else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base + path, data=payload, method=method)
    if payload is not None:
        req.add_header("Content-Type", content_type)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        response = opener.open(req, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read().decode("utf-8")
        return response.status, json.loads(raw)


class CandidateServerError(RuntimeError):
    pass


class Server:
    def __init__(self, workspace, evidence, name, db=None):
        self.workspace, self.evidence, self.name = workspace, evidence, name
        self.db = db or evidence / f"{name}.db"
        self.port_file = evidence / f"{name}.port"
        self.proc = None

    def __enter__(self):
        self.log = (self.evidence / f"{self.name}.server.log").open("w")
        self.proc = subprocess.Popen([sys.executable, "-B", "-m", "taskboard_lite.server",
            "--db", str(self.db), "--seed", "data/entries.csv", "--port", "0",
            "--port-file", str(self.port_file)], cwd=self.workspace, stdout=self.log,
            stderr=self.log, start_new_session=True)
        deadline = time.monotonic() + 10
        while not self.port_file.exists() and self.proc.poll() is None and time.monotonic() < deadline:
            time.sleep(.05)
        if not self.port_file.exists():
            self.__exit__(None, None, None)
            raise CandidateServerError(f"Candidate server did not start; inspect {self.name}.server.log")
        self.base = "http://127.0.0.1:" + self.port_file.read_text().strip()
        return self

    def __exit__(self, *_):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.log.close()


def source_checks(workspace, meta):
    results = {}
    for name, original in meta["preserved"].items():
        results[f"preserved {name}"] = (workspace / name).is_file() and digest(workspace / name) == original
    app_file = workspace / "web/app.js"
    results["web/app.js exists"] = app_file.is_file()
    app = app_file.read_text() if app_file.is_file() else ""
    results["stored text avoids unsafe HTML/JS sinks"] = not re.search(
        r"\b(?:innerHTML|outerHTML|insertAdjacentHTML|eval)\b", app)
    result = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v", "test_existing"],
                            cwd=workspace, capture_output=True, text=True, timeout=30)
    results["original tests"] = result.returncode == 0
    return results, {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def api_checks(workspace, evidence):
    checks = []
    def check(name, condition, detail=None):
        checks.append({"name": name, "pass": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(name)

    with Server(workspace, evidence, "api") as server:
        base = server.base
        entries = request(base, "GET", "/api/entries")
        check("original entries API shape", entries[0] == 200 and
              entries[1] == [{"id": "t1", "project": "alpha", "minutes": 30, "date": "2026-09-01"},
                             {"id": "t2", "project": "beta", "minutes": 0, "date": "2026-09-01"},
                             {"id": "t3", "project": "alpha", "minutes": 45, "date": "2026-09-02"}], entries)
        pending = [{"id": key, "reviewed": False} for key in ("t1", "t2", "t3")]
        check("seed starts pending", request(base, "GET", "/api/review") == (200, pending))
        check("review persists and returns exact response", request(base, "POST", "/api/review",
              {"id": "t1", "reviewed": True}) == (200, {"id": "t1", "reviewed": True}))
        reviewed = [dict(row, reviewed=row["id"] == "t1") for row in pending]
        check("GET reflects persisted state", request(base, "GET", "/api/review") == (200, reviewed))
        for name, payload in (("unknown id", {"id": "missing", "reviewed": True}),
                              ("string boolean", {"id": "t2", "reviewed": "true"}),
                              ("missing field", {"id": "t2"}),
                              ("extra field", {"id": "t2", "reviewed": True, "extra": 1}),
                              ("malformed JSON", b"{")):
            code, body = request(base, "POST", "/api/review", payload)
            check(name + " rejects without write", code == 400 and isinstance(body.get("error"), str)
                  and request(base, "GET", "/api/review") == (200, reviewed), {"status": code, "body": body})
        server.db.with_suffix(".fail-next").touch()
        check("injected 503 precedes review write", request(base, "POST", "/api/review",
              {"id": "t2", "reviewed": True})[0] == 503 and
              request(base, "GET", "/api/review") == (200, reviewed))
        check("manual retry writes once", request(base, "POST", "/api/review",
              {"id": "t2", "reviewed": True}) == (200, {"id": "t2", "reviewed": True}))
        check("idempotent repeat", request(base, "POST", "/api/review",
              {"id": "t2", "reviewed": True}) == (200, {"id": "t2", "reviewed": True}))
        row = {"id": "n, Ω", "project": "R&D &quot; Ω", "minutes": 0, "date": "2026-09-03"}
        check("new entry starts pending", request(base, "POST", "/api/entries", row)[0] == 201 and
              {"id": row["id"], "reviewed": False} in request(base, "GET", "/api/review")[1])
        imported = b"id,project,minutes,date\nimported,Caseboard,3,2026-09-04\n"
        check("imported entry starts pending", request(base, "POST", "/api/import", imported,
              content_type="text/csv")[0] == 201 and
              {"id": "imported", "reviewed": False} in request(base, "GET", "/api/review")[1])
        expected = [{"id": key, "reviewed": key in ("t1", "t2")}
                    for key in ("imported", "n, Ω", "t1", "t2", "t3")]
        check("review rows remain in ID order after additions",
              request(base, "GET", "/api/review") == (200, expected))
        check("original entries remain unchanged", all(item in request(base, "GET", "/api/entries")[1]
              for item in entries[1]))
    # A real server process restart must read the same persisted database.
    with Server(workspace, evidence, "api-restart", db=evidence / "api.db") as restarted:
        persisted = request(restarted.base, "GET", "/api/review")
        check("server restart preserves ordered review state", persisted == (200, expected), persisted)
    return checks


def browser_check(workspace, evidence, name, script, args):
    with Server(workspace, evidence, name) as server:
        output = evidence / name
        command = ["node", str(script), "--url", server.base, "--db", str(server.db),
                   "--output", str(output), *args]
        result = subprocess.run(command, cwd=workspace, capture_output=True, text=True, timeout=180)
        (evidence / f"{name}.command.json").write_text(json.dumps({"command": command,
            "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}, indent=2))
        report = output / "browser-report.json"
        if result.returncode == 2:
            raise RuntimeError(f"Browser evaluation setup failed; inspect {name}.command.json")
        return {"pass": result.returncode == 0 and report.is_file() and
                json.loads(report.read_text()).get("pass") is True,
                "exit_code": result.returncode, "report": str(report) if report.is_file() else None,
                "stdout": result.stdout, "stderr": result.stderr}


def candidate_browser_check(workspace, evidence, name, script, args):
    try:
        return browser_check(workspace, evidence, name, script, args)
    except CandidateServerError as error:
        return {"pass": False, "error": str(error)}


def manual_review(run):
    path = run / "review.json"
    review = json.loads(path.read_text()) if path.is_file() else {}
    result = {}
    for name in REVIEW:
        item = review.get("checks", {}).get(name, {})
        paths = [run / p for p in item.get("evidence", [])]
        valid = bool(review.get("reviewer")) and bool(item.get("note")) and bool(paths) and all(
            p.is_file() and not p.is_symlink() and p.resolve().is_relative_to((run / "evidence").resolve())
            for p in paths)
        result[name] = item.get("status") if valid and item.get("status") in ("PASS", "FAIL") else "NOT_TESTED"
    return result


def grade(run_id):
    verify()
    run = run_path(run_id)
    meta = json.loads((run / "run.json").read_text())
    if meta["manifest_sha256"] != digest(ROOT / "frozen.sha256.json"):
        raise RuntimeError("Run belongs to another fresh-task version")
    workspace = Path(meta["workspace"])
    evidence = run / "evidence" / ("grade-" + uuid4().hex[:10])
    evidence.mkdir()
    try:
        source, tests = source_checks(workspace, meta)
    except (OSError, subprocess.SubprocessError) as error:
        source, tests = {"source checks runnable": False}, {"error": str(error)}
    write_json(evidence / "source-and-tests.json", {"checks": source, "tests": tests})
    try:
        api = api_checks(workspace, evidence)
        api_pass = True
    except (AssertionError, CandidateServerError, OSError, ValueError, KeyError, TypeError) as error:
        api = [{"name": "API acceptance", "pass": False, "error": str(error)}]
        api_pass = False
    write_json(evidence / "api.json", api)
    browser = candidate_browser_check(workspace, evidence, "review-browser", ROOT / "browser.mjs", [])
    write_json(evidence / "browser.json", browser)
    regression = candidate_browser_check(workspace, evidence, "task12-browser-regression",
                               ROOT.parent.parent / "tools/browser_check.mjs", ["--task", "12"])
    write_json(evidence / "task12-regression.json", regression)
    manual = manual_review(run)
    automatic = all(source.values()) and api_pass and browser["pass"] and regression["pass"]
    status = "FAIL" if not automatic or "FAIL" in manual.values() else (
        "PARTIAL" if "NOT_TESTED" in manual.values() else "PASS")
    report = {"task": "fresh-review-queue-1", "status": status, "automatic_pass": automatic,
              "source": source, "api": api, "browser": browser, "task12_browser_regression": regression,
              "manual": manual, "evidence": str(evidence),
              "note": "External browser/source checks and independent review are required; agent claims are not evidence."}
    write_json(run / "grade.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if status == "PASS" else 1


def selftest():
    verify()
    result = subprocess.run(["node", "--check", str(ROOT / "browser.mjs")], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    result = subprocess.run(["node", str(ROOT / "browser.mjs"), "--self-check"],
                            capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    result = subprocess.run(["node", str(ROOT.parent.parent / "tools/browser_check.mjs"),
                             "--self-check"], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    print("Fresh oracle syntax and offline self-check passed; no agent or live browser graded")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    sub.add_parser("selftest")
    sub.add_parser("freeze")
    sub.add_parser("prepare").add_argument("run_id")
    sub.add_parser("grade").add_argument("run_id")
    args = parser.parse_args()
    if args.command == "freeze":
        if (ROOT / "frozen.sha256.json").exists():
            verify()
        else:
            write_json(ROOT / "frozen.sha256.json", hashes())
    elif args.command == "verify":
        verify()
        print("Fresh and base suite definitions verified")
    elif args.command == "selftest":
        selftest()
    elif args.command == "prepare":
        prepare(args.run_id)
    else:
        return grade(args.run_id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Evaluation error: {exc}", file=sys.stderr)
        raise SystemExit(2)
