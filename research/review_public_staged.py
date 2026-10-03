#!/usr/bin/env python3
"""Re-evaluate an immutable public staged receipt after the quoted-prompt bug."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
from public_staged_fixture import PROMPTS, json_bytes  # noqa: E402
from run_public_staged_model import prompts_retained, read_before_edit  # noqa: E402


def digest(data):
    return hashlib.sha256(data).hexdigest()


def review(root):
    raw = (root / "result.json").read_bytes()
    trial = json.loads(raw)
    commit = trial["source_commit"]
    runner_at_trial = subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{commit}:research/run_public_staged_model.py"],
        timeout=10)
    fixture_at_trial = subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{commit}:research/public_staged_fixture.py"],
        timeout=10)
    if (digest(runner_at_trial) != trial["runner_sha256"] or
            digest(fixture_at_trial) != trial["fixture_sha256"] or
            trial["arm_order"] != ["kryn", "native"] or
            len(trial["results"]) != 2):
        raise RuntimeError("Raw trial provenance differs from its pinned commit")
    rows = []
    for old in trial["results"]:
        which = old["arm"]
        history_path = root / which / "final-export.json"
        history = json.loads(history_path.read_text())
        retained = prompts_retained(history, PROMPTS)
        stages = old["stages"]
        reread = [read_before_edit(root / which / f"stage{i}" / "events.jsonl", i)["passed"]
                  for i in (1, 2, 3)]
        accepted = (len(stages) == 3 and all(s["generation_verified"] and
            s["ownership_verified"] and reread[i] and
            s["independent_grade_passed"] for i, s in enumerate(stages)) and
            len(old["compactions"]) == len(old["restarts"]) == 2 and
            old["stored_compactions"] == old["compactions"] and all(retained) and
            old["server_shutdown_proved"] and old["relay_settled"] and
            old["rule_after_owner_edit_sha256"] == digest(json_bytes({"separator": "_"})) and
            old["volume_detached"] and old.get("guard_reason") is None and
            old["resources"]["telemetry_complete"])
        rows.append({"arm": which, "raw_reported_passed": old["passed"],
                     "corrected_stored_prompts": retained,
                     "corrected_read_before_edit": reread,
                     "stage_grades": [s["independent_grade_passed"] for s in stages],
                     "corrected_accepted": bool(accepted),
                     "export_sha256": digest(history_path.read_bytes())})
    return {"schema": 1, "kind": "public_staged_receipt_review",
            "raw_result_sha256": digest(raw), "source_commit": commit,
            "measurement_correction": "Read native user-message text directly; count shell reads only on zero exit before mutation",
            "matched_first_wire_schema": trial["matched_first_wire_schema"],
            "matched_permissions": trial["matched_permissions"],
            "results": rows,
            "matched_pair": bool(trial["matched_first_wire_schema"] and
                                 trial["matched_permissions"]),
            "both_accepted": all(row["corrected_accepted"] for row in rows),
            "protected_eligible": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.absolute()
    if root.parent != Path("/private/tmp"):
        parser.error("Expected direct /private/tmp research receipt")
    report = review(root)
    target = root / "corrected-review-v2.json"
    if target.exists():
        if json.loads(target.read_text()) != report:
            raise RuntimeError("Existing correction receipt differs from current review")
    else:
        target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
