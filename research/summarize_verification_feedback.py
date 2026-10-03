#!/usr/bin/env python3
"""Reproduce the stopped public verifier-feedback pair from compact receipts."""
import json
from pathlib import Path

HISTORY = Path(__file__).with_name("history") / "verification_feedback.jsonl"
MATCHED = ("model_id", "driver_sha256_at_invocation", "opencode_binary_sha256",
           "model_profile_sha256", "prompt_sha256", "normalized_managed_spec_sha256",
           "suite_manifest_sha256", "checker_sha256", "matched_controls_sha256",
           "runtime_effective_permissions_sha256", "tool_catalog_sha256",
           "product_bundle_sha256", "wire_tools_sha256", "wire_numeric_sha256",
           "wire_tool_count", "guard_policy", "variant", "turn_timeout_seconds")


def summarize(rows):
    by_arm = {row["arm"]: row for row in rows}
    if len(rows) != 2 or set(by_arm) != {"control", "candidate"} or any(
        row["run"] != f"feedback-v1-{arm}-a" or
        row["experiment"] != "verification-feedback-v1" or
        row["split"] != "public-development" for arm, row in by_arm.items()
    ):
        raise ValueError("Expected the frozen public V1 control/candidate pair")
    control, candidate = by_arm["control"], by_arm["candidate"]
    for key in MATCHED:
        if control[key] != candidate[key] or control[key] is None:
            raise ValueError(f"Unmatched or missing observed control: {key}")
    for row in rows:
        if row["accepted"] != bool(row["driver_completed"] and row["controller_accepted"]
                                   and row["guard_stop_reason"] is None):
            raise ValueError("Acceptance contradicts driver, controller or guard")
        if not row["raw_private_archive_manifest_sha256"] or not row["rounds"]:
            raise ValueError("Missing raw evidence or independent checks")
    if control["raw_private_archive_manifest_sha256"] != candidate["raw_private_archive_manifest_sha256"]:
        raise ValueError("Archived evidence manifests differ")
    if control["model_loaded_before"] == candidate["model_loaded_before"] or not candidate["guard_stop_reason"]:
        raise ValueError("Frozen cold/warm confound or candidate guard stop is missing")
    return {
        "public_development_only": True,
        "fully_matched": False,
        "matched_observed_controls": True,
        "unmatched_factors": ["cold/warm model state", "power-transition timing",
                              "occupied-host pressure trajectory"],
        "arms": {arm: {
            "accepted": row["accepted"],
            "controller_rounds": len(row["rounds"]),
            "repair_feedback_lengths": row["repair_feedback_lengths"],
            "wall_seconds": row["wall_seconds"],
            "tool_calls": row["tool_calls"],
            "tool_error_count": row["tool_error_count"],
            "new_input_tokens": row["tokens"]["input"],
            "swap_peak_growth_bytes": row["resources"]["swap_peak_growth_bytes"],
            "guard_stop_reason": row["guard_stop_reason"],
        } for arm, row in by_arm.items()},
        "candidate_promoted": False,
        "early_stop": "Candidate hit the unchanged swap guard; reverse-order pair was not run",
    }


if __name__ == "__main__":
    print(json.dumps(summarize([json.loads(line) for line in HISTORY.read_text().splitlines()]),
                     sort_keys=True))
