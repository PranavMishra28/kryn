#!/usr/bin/env python3
"""Run one public development check for a managed repair round.

The full independent acceptance script remains the final authority. This
wrapper only lets the controller report distinct requirement evidence.
"""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4

from development_acceptance import ROOT, browser, command


CHECKS = ("source_and_api", "existing_tests", "js_syntax", "diff_hygiene",
          "task06_browser", "cancel_edit_browser")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=CHECKS)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    workspace, base = args.workspace.resolve(), args.evidence.resolve()
    if not (workspace / ".git").is_dir() or base.is_relative_to(workspace):
        parser.error("Use a Git fixture and private evidence outside the Agent workspace")
    evidence = base / uuid4().hex
    evidence.mkdir(parents=True, mode=0o700)
    if args.check == "source_and_api":
        result = command([sys.executable, "-B", str(ROOT / "evals/checks.py"), "06", str(workspace)], workspace, 60)
    elif args.check == "existing_tests":
        result = command([sys.executable, "-B", "-m", "unittest", "-v", "test_existing"], workspace, 45)
    elif args.check == "js_syntax":
        result = command(["node", "--check", "web/app.js"], workspace, 20)
    elif args.check == "diff_hygiene":
        result = command(["git", "diff", "--check"], workspace, 20)
    else:
        result = browser(workspace, evidence, "task06" if args.check == "task06_browser" else "cancel")
    summary = {"check": args.check, "pass": result["pass"], "observed": result.get("observed"),
               "output": result.get("output", "")[-1200:] if not result["pass"] else "",
               "evidence": str(evidence)}
    (evidence / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
