#!/usr/bin/env python3
"""Run frozen checks and retain source-bound evaluator observations outside the candidate workspace."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

from bench import ROOT, run_path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def optional_hash(file):
    if file.is_symlink():
        raise RuntimeError(f"Refusing linked evaluator input: {file}")
    return digest(file.read_bytes()) if file.is_file() else None


def source_state(workspace):
    """Fingerprint Git-visible project files, including untracked non-ignored source."""
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=workspace, capture_output=True, check=True, timeout=10,
    )
    files = {}
    for raw in sorted(set(result.stdout.split(b"\0")) - {b""}):
        name = os.fsdecode(raw)
        file = workspace / name
        if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(workspace.resolve()):
            raise RuntimeError(f"Unsafe or missing project file: {name}")
        files[name] = digest(file.read_bytes())
    return {"sha256": digest(json.dumps(files, sort_keys=True).encode()), "files": files}


def paths(run_id):
    run = run_path(run_id)
    workspace, evidence = run / "workspace", run / "evidence"
    if not (run.is_dir() and workspace.is_dir() and evidence.is_dir()) or any(
        p.is_symlink() for p in (run, workspace, evidence)
    ):
        raise RuntimeError("Expected an existing non-symlink frozen run")
    return run, workspace, evidence


def observation(kind, report, returncode):
    if report is None:
        return {"status": "ERROR", "failures": [{"check": kind + " infrastructure", "error": f"exit {returncode}; no fresh report"}]}
    if kind == "grade":
        automatic = report.get("automatic", {})
        try:
            tests_run = json.loads(automatic.get("stdout", "").splitlines()[-1])["tests_run"]
            if type(tests_run) is not int or tests_run < 0:
                tests_run = None
        except (IndexError, ValueError, KeyError, TypeError):
            tests_run = None
        failures = []
        if not automatic.get("passed"):
            failures.append({"check": "automatic", "error": automatic.get("stderr", "")[:4000]})
        failures.extend({"check": key, "error": status} for key, status in report.get("manual", {}).items()
                        if status == "FAIL")
        grade_status = report.get("status", "ERROR")
        if (grade_status == "PASS") != (returncode == 0):
            grade_status = "ERROR"
            failures.append({"check": "grade process", "error": "Exit status disagreed with grade report"})
        return {"status": grade_status, "automatic": automatic.get("passed"),
                "automatic_tests_run": tests_run,
                "manual": report.get("manual", {}), "failures": failures}
    checks = [{"name": c.get("name"), "pass": c.get("pass")} for c in report.get("checks", [])]
    failures = [{"check": c.get("name"), "error": str(c.get("error", "unknown failure"))[:1000]}
                for c in report.get("checks", []) if c.get("pass") is False]
    if report.get("error") and not failures:
        failures.append({"check": "browser setup", "error": report["error"].splitlines()[0]})
    return {"status": "PASS" if report.get("pass") and returncode == 0 else "FAIL",
            "checks": checks, "failures": failures}


def record(run_id, kind, *, url=None, db=None, flags=()):
    run, workspace, evidence = paths(run_id)
    task = json.loads((run / "run.json").read_text())["task"]
    scope = task if kind == "grade" else task + ":" + ("+".join(sorted(flags)) or "base")
    before = source_state(workspace)
    review_before = optional_hash(run / "review.json") if kind == "grade" else None
    started_ns = time.time_ns()
    if kind == "grade":
        command = [sys.executable, "-B", str(ROOT / "bench.py"), "grade", run_id]
        report_path = run / "grade.json"
        timeout = 180
    else:
        output = evidence / ("browser-" + uuid4().hex)
        command = ["node", str(ROOT.parent / "tools/browser_check.mjs"), "--task", task,
                   "--url", url, "--db", str(db), "--output", str(output), *flags]
        report_path = output / "browser-report.json"
        timeout = 180
    try:
        process = subprocess.run(command, cwd=ROOT.parent, capture_output=True, text=True, timeout=timeout)
        returncode, runner_error = process.returncode, None
    except (OSError, subprocess.TimeoutExpired) as error:
        returncode, runner_error = None, str(error)
    after = source_state(workspace)
    review_after = optional_hash(run / "review.json") if kind == "grade" else None
    fresh = report_path.is_file() and not report_path.is_symlink() and report_path.stat().st_mtime_ns >= started_ns
    try:
        report = json.loads(report_path.read_text()) if fresh else None
    except (OSError, ValueError) as error:
        report = None
        runner_error = "Invalid fresh report: " + str(error)
    result = observation(kind, report, returncode)
    if report is not None and report.get("task") != task:
        result = {"status": "ERROR", "failures": [{"check": "report identity", "error": "Reported task differs from frozen run"}]}
    if runner_error:
        result = {"status": "ERROR", "failures": [{"check": "runner", "error": runner_error[:1000]}]}
    if before["sha256"] != after["sha256"]:
        result["status"] = "INVALIDATED"
        result.setdefault("failures", []).append({"check": "source stability", "error": "Project files changed during check"})
    if review_before != review_after:
        result["status"] = "INVALIDATED"
        result.setdefault("failures", []).append({"check": "review stability", "error": "Manual review changed during grade"})
    folder = evidence / "observations"
    folder.mkdir(mode=0o700, exist_ok=True)
    if folder.is_symlink():
        raise RuntimeError("Observation directory is a symlink")
    target = folder / f"{started_ns}-{uuid4().hex}.json"
    archived = target.with_suffix(".report.json") if fresh and kind == "grade" else report_path if fresh else None
    if fresh and kind == "grade":
        with archived.open("xb") as stream:
            stream.write(report_path.read_bytes())
            stream.flush()
            os.fsync(stream.fileno())
    item = {"schema": 1, "run": run_id, "kind": kind, "scope": scope, "observed_ns": started_ns,
            "source_before": before, "source_after": after, "review_sha256": review_after, "result": result,
            "report": str(archived.relative_to(run)) if archived else None,
            "report_sha256": digest(archived.read_bytes()) if archived else None}
    temporary = target.with_suffix(".tmp")
    with temporary.open("x") as stream:
        json.dump(item, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, target)
    temporary.unlink()
    return item, target


def status(run_id):
    run, workspace, evidence = paths(run_id)
    task = json.loads((run / "run.json").read_text())["task"]
    current = source_state(workspace)["sha256"]
    current_review = optional_hash(run / "review.json")
    folder = evidence / "observations"
    history = []
    if folder.exists():
        if folder.is_symlink():
            raise RuntimeError("Observation directory is a symlink")
        for file in sorted(folder.glob("*.json")):
            if file.name.endswith(".report.json"):
                continue
            if file.is_symlink():
                raise RuntimeError("Observation file is a symlink")
            item = json.loads(file.read_text())
            report = run / item["report"] if item.get("report") else None
            intact = bool(report and report.is_file() and not report.is_symlink() and
                          report.resolve().is_relative_to(evidence.resolve()) and
                          digest(report.read_bytes()) == item["report_sha256"])
            history.append({"kind": item["kind"], "scope": item.get("scope", "unknown"),
                            "status": item["result"]["status"],
                            "source_sha256": item["source_after"]["sha256"],
                            "current_source": item["source_after"]["sha256"] == current,
                            "current_review": item["kind"] != "grade" or item.get("review_sha256") == current_review,
                            "report_intact": intact, "failures": item["result"].get("failures", []),
                            "checks": item["result"].get("checks", []),
                            "manual": item["result"].get("manual", {}),
                            "automatic_passed": item["result"].get("automatic"),
                            "automatic_tests_run": item["result"].get("automatic_tests_run"),
                            "manual_review_record_present": item.get("review_sha256") is not None,
                            "record": str(file)})
    required = {"grade:" + task}
    if task in ("06", "08", "12"):
        required.add("browser:" + task + ":base")
    keys = sorted(required | {h["kind"] + ":" + h["scope"] for h in history if h["scope"] != "unknown"})
    latest = {key: next((h for h in reversed(history) if h["kind"] + ":" + h["scope"] == key and
                         h["current_source"] and h["current_review"] and h["report_intact"]), None)
              for key in keys}
    return {"run": run_id, "current_source_sha256": current, "latest_current": latest, "history": history,
            "note": "Historical failures remain recorded. An earlier failure is not a current action when a later source-bound check passes. This same-account record is not an access boundary."}


def compact_status(run_id):
    full = status(run_id)
    evidence_id = lambda item: Path(item["record"]).stem
    def bounded_failures(item):
        if item["kind"] == "grade":
            return [{"check": failure["check"], "error": "Frozen grader detail withheld from candidate handoff"
                     if failure["check"] == "automatic" else failure["error"]}
                    for failure in item["failures"]]
        return item["failures"]
    current = {}
    for key, item in full["latest_current"].items():
        if item is None:
            current[key] = None
            continue
        detail = {
            "status": item["status"], "failures": bounded_failures(item), "manual": item["manual"],
            "passed_checks": [c["name"] for c in item["checks"] if c["pass"] is True],
            "evidence_id": evidence_id(item)}
        if item["kind"] == "grade":
            detail.update(automatic_passed=item["automatic_passed"],
                          automatic_tests_run=item["automatic_tests_run"],
                          manual_review_record_present=item["manual_review_record_present"])
        current[key] = detail
    active_records = {item["record"] for item in full["latest_current"].values() if item is not None}
    def older_same_scope(item):
        latest = full["latest_current"].get(item["kind"] + ":" + item["scope"])
        return bool(latest and latest["record"] != item["record"] and
                    latest["source_sha256"] == item["source_sha256"])
    failed = [dict(kind=h["kind"], scope=h["scope"], status=h["status"], current_source=h["current_source"],
                   failures=bounded_failures(h), evidence_id=evidence_id(h))
              for h in full["history"] if h["failures"] and h["report_intact"] and
              h["record"] not in active_records and not older_same_scope(h)]
    infrastructure = [dict(kind=h["kind"], failures=h["failures"], evidence_id=evidence_id(h))
                      for h in full["history"] if h["status"] == "ERROR" and not h["report_intact"]]
    return {"run": run_id, "current_source_sha256": full["current_source_sha256"],
            "current": current, "historical_failures": failed[-6:],
            "older_failures_omitted": max(0, len(failed) - 6), "total_observations": len(full["history"]),
            "older_same_source_scope_failures_omitted": sum(bool(h["failures"] and h["report_intact"] and older_same_scope(h))
                                                            for h in full["history"]),
            "damaged_reports": sum(not h["report_intact"] for h in full["history"]),
            "infrastructure_errors": infrastructure[-3:],
            "note": "Use the latest intact source-matched observation by exact scope for next actions; a weaker pass does not settle a stricter failure. Older same-source/scope failure details remain in full history, not this prompt; changed checker coverage is not inferred. Source matching does not prove unchanged runtime/data. Same-account records do not isolate the grader from candidate shell access."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    grade = sub.add_parser("grade")
    grade.add_argument("run")
    browser = sub.add_parser("browser")
    browser.add_argument("run")
    browser.add_argument("--url", required=True)
    browser.add_argument("--db", required=True, type=Path)
    browser.add_argument("--stored-html", action="store_true")
    browser.add_argument("--visible-controls", action="store_true")
    show = sub.add_parser("status")
    show.add_argument("run")
    show.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    if args.command == "status":
        print(json.dumps(compact_status(args.run) if args.compact else status(args.run), indent=2, ensure_ascii=False))
        return
    flags = ["--" + name for name in ("stored-html", "visible-controls") if getattr(args, name.replace("-", "_"), False)] if args.command == "browser" else []
    item, target = record(args.run, args.command, url=getattr(args, "url", None), db=getattr(args, "db", None), flags=flags)
    print(json.dumps({"record": str(target), "source_sha256": item["source_after"]["sha256"], "result": item["result"]}, ensure_ascii=False))
    raise SystemExit(0 if item["result"]["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
