#!/usr/bin/env python3
"""Reproduce the four-pair public C1 development result from compact receipts."""
import json
from pathlib import Path
from statistics import median

HISTORY = Path(__file__).with_name("history") / "cache_ablation.jsonl"
PAIRS = (("02", "a"), ("03", "a"), ("02", "b"), ("03", "b"))
CONTROLS = ("suite_manifest_sha256", "runner_sha256_at_invocation",
            "opencode_binary_sha256_at_invocation", "model_profile_sha256_at_invocation",
            "model_revision", "matched_controls_sha256", "effective_permissions_sha256",
            "tool_catalog_sha256", "turn_timeout_seconds", "guard")


def summarize(rows):
    expected = {f"cache-c1-{task}-{arm}-{repeat}"
                for task, repeat in PAIRS for arm in ("v1", "c1")}
    by_name = {row["run"]: row for row in rows}
    if len(rows) != 8 or set(by_name) != expected:
        raise ValueError("Expected exactly the four frozen V1/C1 development pairs")
    for task, repeat in PAIRS:
        v1 = by_name[f"cache-c1-{task}-v1-{repeat}"]
        c1 = by_name[f"cache-c1-{task}-c1-{repeat}"]
        if v1["comparison_arm"] != "v1" or c1["comparison_arm"] != "c1":
            raise ValueError("Arm labels do not match frozen run IDs")
        if v1["prompt_sha256"] != c1["prompt_sha256"]:
            raise ValueError("Paired prompts differ")
    for key in CONTROLS:
        if len({json.dumps(row[key], sort_keys=True) for row in rows}) != 1:
            raise ValueError(f"Non-matched control: {key}")
    for arm in ("v1", "c1"):
        if len({row["candidate_bundle_sha256"] for row in rows
                if row["comparison_arm"] == arm}) != 1:
            raise ValueError(f"{arm} product bundle changed between repeats")
    arms = {}
    for arm in ("v1", "c1"):
        selected = [by_name[f"cache-c1-{task}-{arm}-{repeat}"]
                    for task, repeat in PAIRS]
        accepted = sum(bool(row["accepted"]) for row in selected)
        wall = sum(row["wall_seconds"] for row in selected)
        arms[arm] = {
            "accepted": accepted,
            "false_completion": sum(bool(row["false_completion"]) for row in selected),
            "wall_seconds": round(wall, 3),
            "accepted_per_generation_hour": round(3600 * accepted / wall, 3),
            "new_input_tokens": sum(row["tokens"]["input"] for row in selected),
            "cache_read_tokens": sum(row["tokens"]["cache_read"] for row in selected),
            "output_tokens": sum(row["tokens"]["output"] for row in selected),
            "median_new_input_per_primary_request": round(median(
                row["tokens"]["input"] / row["wire_primary_requests"] for row in selected), 1),
            "primary_requests": sum(row["wire_primary_requests"] for row in selected),
            "system_prompt_changes": sum(row["system_prompt_changes"] for row in selected),
            "tool_calls": sum(row["tool_calls"] for row in selected),
            "tool_errors": sum(row["tool_error_count"] for row in selected),
            "guard_stops": sum(bool(row["guard"].get("reason")) for row in selected),
            "peak_swap_growth_bytes": max(row["resources"]["swap_peak_growth_bytes"]
                                          for row in selected),
        }
    return {"public_development_only": True, "task_count": 2, "pairs": 4,
            "paired_acceptance_deltas": [int(by_name[f"cache-c1-{task}-c1-{repeat}"]["accepted"])
                                         - int(by_name[f"cache-c1-{task}-v1-{repeat}"]["accepted"])
                                         for task, repeat in PAIRS],
            "arms": arms, "candidate_promoted": False}


if __name__ == "__main__":
    print(json.dumps(summarize([json.loads(line) for line in HISTORY.read_text().splitlines()]),
                     sort_keys=True))
