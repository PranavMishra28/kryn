#!/usr/bin/env python3
"""One public, guarded model-facing browser dispatch check; never a holdout score."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_external_patch import run as run_external
from ui_gateway.preflight import broker_start, command, stop_group


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="new /private/tmp public receipt directory")
    parser.add_argument("--image", required=True, help="exact local browser image ID")
    parser.add_argument("--arm", choices=("native", "kryn"), default="kryn")
    args = parser.parse_args()
    root = args.root.absolute()
    if (root != root.resolve() or not root.is_relative_to(Path("/private/tmp")) or
            root.exists() or root.is_symlink()):
        parser.error("Use a new canonical /private/tmp receipt directory")
    root.mkdir(mode=0o700)
    workspace = root / "workspace"
    workspace.mkdir(mode=0o700)
    (workspace / "index.html").write_text(
        '<!doctype html><title>Public browser dispatch</title>'
        '<button id="toggle" onclick="document.getElementById(\'state\').textContent=\'Activated\'">Activate</button>'
        '<p id="state">Waiting</p>\n', encoding="utf-8")
    for argv in (["git", "init", "-q", str(workspace)],
                 ["git", "-C", str(workspace), "add", "index.html"],
                 ["git", "-C", str(workspace), "-c", "user.name=Research", "-c",
                  "user.email=research@example.invalid", "commit", "-qm", "seed"]):
        subprocess.run(argv, check=True, capture_output=True, timeout=20)
    base = command(["git", "-C", str(workspace), "rev-parse", "HEAD"]).stdout.strip()
    prompt = root / "prompt.txt"
    prompt.write_text(
        "Use the browser tools on http://candidate.invalid/index.html. "
        "Click the Activate button, then take a browser snapshot and tell me the "
        "visible state. Do not change files.\n", encoding="utf-8")
    broker_child = None
    broker = None
    report = {"schema": 1, "kind": "public_ui_model_dispatch", "arm": args.arm,
              "source_commit": command(["git", "-C", str(Path(__file__).resolve().parents[2]),
                                        "rev-parse", "HEAD"]).stdout.strip(),
              "source_dirty": bool(command(["git", "-C", str(Path(__file__).resolve().parents[2]),
                                           "status", "--porcelain"]).stdout),
              "browser_image": args.image, "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
              "protected_score": False, "passed": False}
    try:
        broker_child, broker = broker_start(args.image, workspace, timeout=20)
        trial = run_external(argparse.Namespace(
            workspace=workspace, base_commit=base, task_id="public-ui-browser-dispatch",
            prompt=prompt, evidence=root / "evidence", arm=args.arm, tool_venv=None,
            private_parent=None, timeout=300, ui_gateway=broker, agent="browse"))
        report["driver_completed"] = trial.get("completed")
        report["intervention"] = trial.get("intervention")
        resource_file = root / "evidence/resources.jsonl"
        report["resource_guard_reason"] = next((entry.get("guard_reason")
            for entry in reversed([json.loads(line) for line in resource_file.read_text().splitlines()])
            if entry.get("guard_reason")), None) if resource_file.exists() else None
        events = root / "evidence/events.jsonl"
        calls = []
        if events.exists():
            for line in events.read_text().splitlines():
                try:
                    part = json.loads(line).get("part", {})
                except json.JSONDecodeError:
                    continue
                if part.get("type") == "tool" and str(part.get("tool", "")).startswith("browser_"):
                    calls.append({"tool": part["tool"], "status": part.get("state", {}).get("status")})
        report["browser_calls"] = calls
        report["passed"] = bool(trial.get("completed") and
                                any(c["tool"] == "browser_browser_navigate" and c["status"] == "completed"
                                    for c in calls) and
                                any(c["tool"] == "browser_browser_click" and c["status"] == "completed"
                                    for c in calls) and
                                any(c["tool"] == "browser_browser_snapshot" and c["status"] == "completed"
                                    for c in calls))
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if broker_child is not None:
            stop_group(broker_child)
            try:
                report["container_cleaned"] = (broker is not None and command(
                    ["docker", "ps", "-a", "--filter", "name=" + broker["container"],
                     "--format", "{{.Names}}"]).stdout.strip() == "")
            except (OSError, subprocess.TimeoutExpired):
                report["container_cleaned"] = False
        report["passed"] = report["passed"] and report.get("container_cleaned", False)
        (root / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
