#!/usr/bin/env python3
"""Prepare disposable fixtures and grade evidence; never invoke a model."""
import argparse
import csv
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

ROOT = Path(__file__).resolve().parent
VERSION = "2026-09-19.2"
TASKS = json.loads((ROOT / "tasks.json").read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def static_hashes():
    items = [ROOT / name for name in ("bench.py", "checks.py", "tasks.json", "README.md")]
    for name in ("fixture", "references"):
        items.extend(p for p in (ROOT / name).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(items)}


def verify():
    expected = json.loads((ROOT / "frozen.sha256.json").read_text())
    if expected != static_hashes():
        raise RuntimeError("Frozen suite changed. Do not compare trials across suite versions.")


def project_hashes(path):
    return {str(p.relative_to(path)): sha(p) for p in path.rglob("*") if p.is_file() and not p.is_symlink() and ".git" not in p.relative_to(path).parts and "__pycache__" not in p.parts}


def replace(path, old, new):
    text = path.read_text()
    if old not in text:
        raise RuntimeError(f"Seed anchor missing: {path.name}")
    path.write_text(text.replace(old, new))


def populate(workspace, task, golden=False):
    shutil.copytree(ROOT / "fixture", workspace)
    (workspace / "data/bom.csv").write_text('\ufeffid,project,minutes,date\r\nu,"café, Ω",0,2026-09-01\r\n', encoding="utf-8")
    (workspace / "TASK.md").write_text(TASKS[task]["prompt"] + "\n")
    (workspace / ".gitignore").write_text("__pycache__/\n*.pyc\n*.db\n*.db-*\n*.fail-next\nartifacts/\n")
    if task == "09":
        (workspace / "data/endurance.csv").write_text("id,project,minutes,date\n")
    if task == "08":
        shutil.copy2(ROOT / "references/vision.png", workspace / "vision.png")
    if not golden:
        if task in ("02", "10"):
            replace(workspace / "taskboard_lite/report.py", 'r["date"] < end', 'r["date"] <= end')
        if task in ("03", "10"):
            replace(workspace / "taskboard_lite/report.py", '(project is None or r["project"] == project)', 'True')
            replace(workspace / "taskboard_lite/cli.py", 'parser.add_argument("--project")', '# --project support is missing')
            replace(workspace / "taskboard_lite/cli.py", 'args.start, args.end, args.project', 'args.start, args.end')
            replace(workspace / "taskboard_lite/server.py", ', query.get("project")', '')
        if task == "04":
            duplicate = (workspace / "taskboard_lite/parse.py").read_text()
            replace(workspace / "taskboard_lite/cli.py", 'from .parse import parse_rows', duplicate)
            replace(workspace / "taskboard_lite/server.py", 'from .parse import parse_rows, validate, FIELDS', duplicate)
        if task == "05":
            replace(workspace / "taskboard_lite/parse.py", 'text.lstrip("\\ufeff")', 'text')
        if task in ("06", "12"):
            (workspace / "web/app.js").write_text("fetch('/api/entries').then(r=>r.json()).then(rows=>{document.querySelector('#entries').textContent=JSON.stringify(rows);});\n")
        if task == "08":
            with (workspace / "web/style.css").open("a") as target:
                target.write("\n@media(max-width:500px){form{width:600px;flex-wrap:nowrap}main{overflow:hidden}}\n")
        if task == "12":
            replace(workspace / "taskboard_lite/server.py", 'if url.path == "/api/export":', 'if url.path == "/api/export-not-implemented":')
            replace(workspace / "taskboard_lite/server.py", 'if self.path == "/api/import":', 'if self.path == "/api/import-not-implemented":')
            replace(workspace / "taskboard_lite/server.py", 'def do_PATCH(self):', 'def unimplemented_PATCH(self):')
    if task == "05":
        result = subprocess.run([sys.executable, "-B", "-m", "taskboard_lite.cli", "validate", "data/bom.csv"], cwd=workspace, text=True, capture_output=True, timeout=10)
        (workspace / "failure.txt").write_text("Command: python3 -B -m taskboard_lite.cli validate data/bom.csv\n" + f"Exit: {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")


def run_path(run_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", run_id) or run_id in (".", ".."):
        raise ValueError("Use a simple unique run ID")
    path = ROOT / "runs" / run_id
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise RuntimeError("Refusing symlink run path")
    return path


def check_process(task, workspace):
    result = subprocess.run([sys.executable, "-B", str(ROOT / "checks.py"), task, str(workspace)], text=True, capture_output=True, timeout=120, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    return {"passed": result.returncode == 0, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def research_matches(path):
    try:
        answers = json.loads(path.read_text())
        expected = json.loads((ROOT / "references/research-oracle.json").read_text())
        actual = {a["project"]: a for a in answers}
        return bool(len(answers) == 2 and set(actual) == set(expected) and all(all(actual[key].get(field) == value[field] for field in ("version", "published_at", "source_url")) and actual[key].get("caveat") and actual[key].get("caveat_source", "").startswith("https://") for key, value in expected.items()))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def prepare(task, run_id):
    verify()
    run = run_path(run_id)
    run.mkdir(parents=True, exist_ok=False)
    workspace = run / "workspace"
    populate(workspace, task)
    (run / "evidence").mkdir()
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
    subprocess.run(["git", "-c", "init.defaultBranch=main", "init", "-q"], cwd=workspace, env=env, check=True)
    subprocess.run(["git", "add", "."], cwd=workspace, env=env, check=True)
    subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Frozen disposable task fixture"], cwd=workspace, env=env, check=True)
    write_json(run / "run.json", {"suite": VERSION, "task": task, "created_unix": time.time(), "initial_hashes": project_hashes(workspace), "suite_manifest_sha256": sha(ROOT / "frozen.sha256.json")})
    write_json(run / "review.template.json", {"reviewer": "", "checks": {key: {"status": "NOT_TESTED", "evidence": [], "note": ""} for key in TASKS[task]["manual"]}})
    print(json.dumps({"run": str(run), "workspace": str(workspace), "prompt": str(workspace / "TASK.md"), "task": task}))


def grade(run_id):
    verify()
    run = run_path(run_id)
    meta = json.loads((run / "run.json").read_text())
    workspace, task = run / "workspace", meta["task"]
    if meta["suite_manifest_sha256"] != sha(ROOT / "frozen.sha256.json"):
        raise RuntimeError("Run belongs to another frozen suite")
    outcome = check_process(task, workspace)
    extra = {}
    for name in ("test_existing.py", "data/entries.csv"):
        extra["preserved_" + name] = (workspace / name).is_file() and sha(workspace / name) == meta["initial_hashes"][name]
    if task == "01":
        current = project_hashes(workspace)
        extra["no_project_edits"] = all(current.get(k) == v for k, v in meta["initial_hashes"].items()) and not (set(current) - set(meta["initial_hashes"]) - {"answer.json"})
    if task == "07":
        extra["release_facts"] = research_matches(workspace / "research.json")
    if task == "09":
        checkpoints = sorted((run / "checkpoints").glob("*.json")) if (run / "checkpoints").exists() else []
        extra["ten_valid_checkpoints"] = len(checkpoints) == 10 and all(json.loads(p.read_text()).get("passed") is True for p in checkpoints)
        with (workspace / "data/endurance.csv").open() as source:
            rows = list(csv.DictReader(source))
        extra["final_endurance_rows"] = rows == endurance_rows(10)
    review = json.loads((run / "review.json").read_text()) if (run / "review.json").is_file() else {}
    manual = {}
    for name in TASKS[task]["manual"]:
        check = review.get("checks", {}).get(name, {})
        paths = [run / p for p in check.get("evidence", [])]
        valid = bool(review.get("reviewer")) and bool(paths) and all(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to((run / "evidence").resolve()) for p in paths)
        manual[name] = check.get("status") if valid and check.get("status") in ("PASS", "FAIL") else "NOT_TESTED"
    auto_pass = outcome["passed"] and all(extra.values())
    status = "FAIL" if not auto_pass or "FAIL" in manual.values() else ("PARTIAL" if "NOT_TESTED" in manual.values() else "PASS")
    report = {"suite": VERSION, "task": task, "run": run_id, "status": status, "automatic": outcome, "assertions": extra, "manual": manual, "note": "Manual checks require independent operator review of raw evidence; declarations are not automatic proof."}
    write_json(run / "grade.json", report)
    print(json.dumps(report, indent=2))
    return status


def endurance_rows(count):
    return [{"id": f"e{i:02}", "project": "endurance", "minutes": str(i), "date": "2026-09-03"} for i in range(1, count + 1)]


def checkpoint(run_id, number):
    verify()
    run = run_path(run_id)
    if json.loads((run / "run.json").read_text())["task"] != "09":
        raise ValueError("Checkpoints belong to task 09")
    dest = run / "checkpoints" / f"{number:02}.json"
    if dest.exists() or not 1 <= number <= 10:
        raise ValueError("Checkpoint must be new and numbered 1–10")
    if number > 1 and not dest.with_name(f"{number-1:02}.json").is_file():
        raise ValueError("Record checkpoints sequentially")
    with (run / "workspace/data/endurance.csv").open() as source:
        rows = list(csv.DictReader(source))
    result = check_process("09", run / "workspace")
    dest.parent.mkdir(exist_ok=True)
    write_json(dest, {"turn": number, "rows": rows, "passed": rows == endurance_rows(number) and result["passed"], "checks": result, "observed_unix": time.time()})
    print(dest)


def context(run_id, records):
    verify()
    run = run_path(run_id)
    if json.loads((run / "run.json").read_text())["task"] != "10" or not 10 <= records <= 20000:
        raise ValueError("Use task 10 and 10–20000 records")
    path = run / "workspace/context.txt"
    if path.exists():
        raise ValueError("Context already generated; use a fresh run for each tier")
    lines = ["Maintenance requirements: date ranges include start and exclude end. report_label = September review.\n"]
    for i in range(records):
        lines.append(f"Archived event {i:05}: project p{i%37:02}; work item {i*17%991:03}; minutes {i%59}; recorded successfully; historical data only.\n")
        if i == records // 2:
            lines.append("Requirement: preserve zero-minute entries and original public behavior. zero_minutes = include.\n")
    lines.append("Requirement: project filters match exactly, including case and Unicode, in report, CLI and HTTP. project_match = exact.\n")
    path.write_text("".join(lines))
    write_json(run / "context-manifest.json", {"records": records, "sha256": sha(path), "bytes": path.stat().st_size, "tokens": None, "note": "Measure with selected model tokenizer/runtime; bytes are not tokens."})
    print(path)


def selftest():
    verify()
    results = []
    (ROOT / ".validation").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as temporary:
        for task in ("01", "02", "03", "04", "05", "06", "08", "09", "10", "12"):
            workspace = Path(temporary) / (task + "-golden")
            populate(workspace, task, golden=True)
            if task == "01":
                write_json(workspace / "answer.json", json.loads((ROOT / "references/comprehension.json").read_text()))
            if task == "08":
                write_json(workspace / "vision-answer.json", {"status": "Offline", "pending": 7, "clipped_control": "Save"})
            if task == "10":
                write_json(workspace / "context-summary.json", {"report_label": "September review", "zero_minutes": "include", "project_match": "exact"})
            result = check_process(task, workspace)
            results.append({"task": task, "kind": "golden_automatic_only", "passed": result["passed"], "details": result})
        for task in ("02", "03", "04", "05", "10", "12"):
            workspace = Path(temporary) / (task + "-seed")
            populate(workspace, task)
            result = check_process(task, workspace)
            results.append({"task": task, "kind": "seed_rejected", "passed": not result["passed"], "details": result})
        expected = json.loads((ROOT / "references/research-oracle.json").read_text())
        answers = [dict(value, project=key, caveat="Reference-validation placeholder, not a researched caveat", caveat_source=value["source_url"]) for key, value in expected.items()]
        path = Path(temporary) / "research.json"
        write_json(path, answers)
        results.append({"task": "07", "kind": "golden_release_facts_only", "passed": research_matches(path)})
        answers[0]["version"] = "incorrect-version"
        write_json(path, answers)
        results.append({"task": "07", "kind": "incorrect_release_rejected", "passed": not research_matches(path)})
    write_json(ROOT / ".validation/fixture-validation.json", {"kind": "fixture_validation_NOT_model_baseline", "results": results, "manual_checks_executed": False})
    print(json.dumps({"valid": all(r["passed"] for r in results), "cases": len(results), "report": str(ROOT / ".validation/fixture-validation.json"), "model_runs": 0}))
    return all(r["passed"] for r in results)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare"); prep.add_argument("task", choices=TASKS); prep.add_argument("run_id")
    grading = sub.add_parser("grade"); grading.add_argument("run_id")
    cp = sub.add_parser("checkpoint"); cp.add_argument("run_id"); cp.add_argument("number", type=int)
    ctx = sub.add_parser("context"); ctx.add_argument("run_id"); ctx.add_argument("--records", type=int, default=1500)
    sub.add_parser("selftest"); sub.add_parser("verify"); sub.add_parser("freeze")
    args = parser.parse_args()
    if args.command == "freeze":
        path = ROOT / "frozen.sha256.json"
        if path.exists(): verify()
        else: write_json(path, static_hashes())
        print(path)
    elif args.command == "prepare": prepare(args.task, args.run_id)
    elif args.command == "grade": raise SystemExit(0 if grade(args.run_id) == "PASS" else 1)
    elif args.command == "checkpoint": checkpoint(args.run_id, args.number)
    elif args.command == "context": context(args.run_id, args.records)
    elif args.command == "selftest": raise SystemExit(0 if selftest() else 1)
    else: verify(); print("Frozen suite verified")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Evaluation error: {exc}", file=sys.stderr)
        raise SystemExit(2)
