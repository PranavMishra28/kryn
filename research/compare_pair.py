#!/usr/bin/env python3
"""Verify the matched controls before describing a KRYN/native development pair."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from record_trial import receipt

MATCHED = ("task", "suite", "prompt_sha256", "matched_controls_sha256",
           "effective_permissions_sha256", "tool_catalog_sha256", "model_id",
           "runtime_version", "runtime_memory_ceiling_bytes", "variant",
           "turn_timeout_seconds", "audit_plugin_sha256")
GUARD = ("allowed_preflight_pressure", "sample_interval_seconds", "warning_samples_to_abort",
         "max_swap_growth_bytes", "any_warning_fails_acceptance", "missing_telemetry_aborts")


def effective_permissions(run, folder):
    config_root = folder / "candidate-inputs/config"
    if not config_root.exists():
        config_root = run / "trial-inputs/frozen/config"
    inventory = json.loads((folder / "agent-inventory.json").read_text())
    normalized = {}
    for agent in inventory["data"]:
        value = json.dumps(agent.get("permissions"), sort_keys=True)
        value = value.replace(str(config_root), "<CONFIG>").replace(str(run / "workspace"), "<WORKSPACE>")
        value = re.sub(r"\.localai-tmp-[a-z0-9_]+", "<TMP>", value)
        normalized[agent["id"]] = json.loads(value)
    return hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def compare(native_run, kryn_run, stage):
    a, b = receipt(native_run, stage), receipt(kryn_run, stage)
    if a["arm"] != "native" or b["arm"] != "kryn":
        raise ValueError("Expected native control first and KRYN candidate second")
    unequal = [key for key in MATCHED if a.get(key) != b.get(key)]
    unverified = [key for key in ("runner_sha256_at_invocation", "opencode_binary_sha256_at_invocation",
                                "model_profile_sha256_at_invocation", "turn_timeout_seconds")
                  if not a.get(key) or not b.get(key)]
    for key in ("runner_sha256_at_invocation", "opencode_binary_sha256_at_invocation",
                "model_profile_sha256_at_invocation"):
        if a.get(key) and b.get(key) and a[key] != b[key]:
            unequal.append(key)
    unequal += ["guard." + key for key in GUARD if a["guard"].get(key) != b["guard"].get(key)]
    if not a["tool_catalog_sha256"] or not b["tool_catalog_sha256"]:
        unequal.append("missing tool catalog")
    power = [sorted(row["resources"].get("power_sources_observed", [])) for row in (a, b)]
    if power[0] != power[1] or power[0] != ["AC Power"]:
        unequal.append("power source")
    roots = [Path(p) / "evidence" / stage for p in (native_run, kryn_run)]
    effective = [effective_permissions(Path(run), folder)
                 for run, folder in zip((native_run, kryn_run), roots)]
    if effective[0] != effective[1]:
        unequal.append("runtime effective permissions")
    wires = []
    for folder in roots:
        events = [json.loads(line) for line in (folder / "inference.jsonl").read_text().splitlines() if line.strip()]
        wire = next((event for event in events if event.get("event") == "wire.options"
                     and event.get("kind") == "primary"), None)
        if wire is None:
            unequal.append("missing first primary wire request")
            wire = {}
        wires.append(wire)
    for key in ("requestModelID", "numeric", "thinking", "toolCount", "tools"):
        if wires[0].get(key) != wires[1].get(key):
            unequal.append("wire." + key)
    normalized = [wire.get("workspaceNormalizedToolsSha256") for wire in wires]
    if all(normalized):
        if normalized[0] != normalized[1]:
            unequal.append("wire.workspace-normalized tool schemas")
    elif wires[0].get("toolsSha256") != wires[1].get("toolsSha256"):
        unequal.append("wire.tool schemas (normalization evidence unavailable)")
    runtime = [json.loads((folder / "guard-idle-before.response.json").read_text()).get("json", {})
               for folder in roots]
    loaded = [row.get("default_model") in row.get("loaded_models", []) for row in runtime]
    if loaded[0] != loaded[1]:
        unequal.append("cold/warm model state")
    configs = [json.loads((folder / "requested-config.json").read_text()) for folder in roots]
    products = [[p for p in cfg.get("plugins", []) if isinstance(p, dict)
                 and "profileId" in p.get("options", {})] for cfg in configs]
    if products[0] or len(products[1]) != 1:
        unequal.append("treatment plugin delta")
    return {"matched": not unequal and not unverified, "observed_controls_matched": not unequal,
            "unequal_controls": unequal, "unverified_controls": unverified, "split": "development",
            "task": a["task"], "model_loaded_before": loaded,
            "wire_tool_schema_sha256": [wire.get("toolsSha256") for wire in wires],
            "wire_workspace_normalized_schema_sha256": normalized,
            "effective_permissions_sha256": effective,
            "native": {"run": a["run"], "accepted": a["accepted"], "seconds": a["wall_seconds"],
                       "grader_status": a["grader_status"], "supplemental": a["supplemental"]},
            "kryn": {"run": b["run"], "accepted": b["accepted"], "seconds": b["wall_seconds"],
                     "grader_status": b["grader_status"], "supplemental": b["supplemental"]},
            "caveat": "Public development task; serial same-task cache may favor the second arm. No uplift inference from one pair."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_run", type=Path)
    parser.add_argument("kryn_run", type=Path)
    parser.add_argument("--stage", default="attempt1")
    args = parser.parse_args()
    result = compare(args.native_run, args.kryn_run, args.stage)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["matched"] else 1)


if __name__ == "__main__":
    main()
