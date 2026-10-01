#!/usr/bin/env python3
"""Public development checks for Task06 seed plus the Cancel Edit request.

This script is outside the Agent workspace and is never the sealed holdout.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from fresh_review_queue.suite import Server


ROOT = Path(__file__).resolve().parents[1]


def command(argv, workspace, timeout):
    try:
        result = subprocess.run(argv, cwd=workspace, capture_output=True, text=True,
                                errors="replace", timeout=timeout)
        return {"pass": result.returncode == 0, "exit": result.returncode,
                "output": (result.stdout + "\n" + result.stderr).strip()[-1800:]}
    except subprocess.TimeoutExpired:
        return {"pass": False, "error": "timed out"}
    except OSError as error:
        return {"pass": False, "error": type(error).__name__ + ": " + str(error)}


def browser(workspace, evidence, name):
    with Server(workspace, evidence, name) as server:
        output = evidence / (name + "-browser")
        if name == "task06":
            argv = ["node", str(ROOT / "tools/browser_check.mjs"), "--task", "06",
                    "--stored-html", "--visible-controls", "--quoted-import",
                    "--url", server.base + "/", "--output", str(output), "--db", str(server.db)]
            report = output / "browser-report.json"
        else:
            argv = ["node", str(ROOT / "evals/development_cancel_edit.mjs"), server.base + "/", str(output)]
            report = output / "report.json"
        result = command(argv, workspace, 200)
        if report.is_file():
            data = json.loads(report.read_text())
            result["observed"] = {"pass": data.get("pass"),
                                  "failures": [str(row.get("name")) + ": " + str(row.get("error"))
                                               for row in data.get("checks", []) if not row.get("pass", False)]
                                  if name == "task06" else data.get("failure"),
                                  "page_errors": data.get("pageErrors") or data.get("errors")}
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    workspace, base = args.workspace.resolve(), args.evidence.resolve()
    if not (workspace / ".git").is_dir() or base.is_relative_to(workspace):
        parser.error("Use a Git fixture and private evidence outside the Agent workspace")
    evidence = base / uuid4().hex
    evidence.mkdir(parents=True, mode=0o700)
    results = {
        "source_and_api": command([sys.executable, "-B", str(ROOT / "evals/checks.py"), "06", str(workspace)], workspace, 60),
        "existing_tests": command([sys.executable, "-B", "-m", "unittest", "-v", "test_existing"], workspace, 45),
        "js_syntax": command(["node", "--check", "web/app.js"], workspace, 20),
        "diff_hygiene": command(["git", "diff", "--check"], workspace, 20),
    }
    results["task06_browser"] = browser(workspace, evidence, "task06")
    results["cancel_edit_browser"] = browser(workspace, evidence, "cancel")
    passed = all(item["pass"] for item in results.values())
    (evidence / "result.json").write_text(json.dumps({"pass": passed, "checks": results}, indent=2) + "\n")
    summary = {name: {"pass": item["pass"], "observed": item.get("observed"),
                      "output": item.get("output", "")[-450:] if not item["pass"] else ""}
               for name, item in results.items()}
    print(json.dumps({"pass": passed, "checks": summary, "evidence": str(evidence)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
