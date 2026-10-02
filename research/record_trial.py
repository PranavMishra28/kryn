#!/usr/bin/env python3
"""Append a fail-closed, machine-readable receipt for one completed development trial."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "research/history/development.jsonl"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    return digest(path.read_bytes()) if path.is_file() else None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def model_provenance(profile, model_id, profile_hash, invocation_hash):
    """Never label a replacement model with the installed champion's revision."""
    champion_id = profile.get("repository", "").rsplit("/", 1)[-1]
    if model_id != champion_id:
        return {"repository": None, "revision": None, "manifest_sha256": None,
                "verified": False}
    return {"repository": profile.get("repository"), "revision": profile.get("revision"),
            "manifest_sha256": profile_hash,
            "verified": bool(invocation_hash and invocation_hash == profile_hash
                             and profile.get("revision"))}


def receipt(run, stage):
    run = Path(run).resolve()
    if not run.is_relative_to(ROOT / "evals/runs") or not stage or "/" in stage or stage.startswith("."):
        raise ValueError("Expected a prepared development run and a simple stage name")
    verified = subprocess.run([sys.executable, "-B", str(ROOT / "evals/bench.py"), "verify"],
                              cwd=ROOT, capture_output=True, text=True, timeout=20)
    if verified.returncode:
        raise ValueError("Frozen development suite no longer matches its manifest")
    evidence = run / "evidence" / stage
    meta = json.loads((run / "run.json").read_text())
    driver_file, grade_file = evidence / "driver.json", run / "grade.json"
    driver, grade = json.loads(driver_file.read_text()), json.loads(grade_file.read_text())
    config = json.loads((evidence / "requested-config.json").read_text())
    if (meta.get("task") != grade.get("task") or grade.get("run") != run.name
            or meta.get("suite") != grade.get("suite")
            or file_hash(ROOT / "evals/frozen.sha256.json") != meta.get("suite_manifest_sha256")
            or file_hash(evidence / "requested-config.json") != driver.get("config_sha256")):
        raise ValueError("Trial, config, suite and grader identities do not match")
    if driver.get("arm") not in {"native", "kryn"} or type(driver.get("completed")) is not bool:
        raise ValueError("Driver has no verified arm/completion state")
    controls = {key: config.get(key) for key in ("model", "providers", "permissions", "mcp",
                                                   "skills", "compaction", "tool_output")}
    tools = evidence / "tool-catalog.json"
    runtime = json.loads((evidence / "guard-idle-before.response.json").read_text()).get("json", {})
    profile_path = ROOT / "setup/accepted-profile.json"
    if (driver.get("model_profile_sha256") and
            driver["model_profile_sha256"] != file_hash(profile_path)):
        raise ValueError("Model profile changed since trial invocation")
    profile = json.loads(profile_path.read_text())
    provenance = model_provenance(profile, driver.get("expected_model_id"),
                                  file_hash(profile_path), driver.get("model_profile_sha256"))
    guard = driver.get("resource_guard", {})
    supplemental = None
    supplemental_checks = {"02": ROOT / "evals/supervised_task02.py",
                           "03": ROOT / "research/check_task03.py"}
    if meta["task"] in supplemental_checks:
        check = supplemental_checks[meta["task"]]
        result = subprocess.run([sys.executable, "-B", str(check), str(run / "workspace")],
                                cwd=ROOT, capture_output=True, text=True, timeout=20)
        supplemental = {"check": str(check.relative_to(ROOT)), "source_sha256": file_hash(check),
                        "exit_code": result.returncode, "stdout_sha256": digest(result.stdout.encode()),
                        "stderr_sha256": digest(result.stderr.encode()),
                        "passed": result.returncode == 0}
    accepted = (driver["completed"] and grade.get("status") == "PASS"
                and (supplemental is None or supplemental["passed"])
                and driver.get("interventions") == 0 and driver.get("routing_verified") is True
                and driver.get("resources", {}).get("telemetry_complete") is True
                and not guard.get("reason"))
    token_rows = list((driver.get("native_session_tokens") or {}).values())
    def total(*keys):
        values = [row for row in token_rows]
        for key in keys:
            values = [row.get(key) if isinstance(row, dict) else None for row in values]
        return sum(values) if values and all(type(value) is int for value in values) else None
    tokens = {"input": total("input"), "output": total("output"),
              "reasoning": total("reasoning"), "cache_read": total("cache", "read"),
              "cache_write": total("cache", "write")}
    tool_errors = driver.get("tool_errors") or []
    return {
        "schema": 1, "split": "development", "run": run.name, "stage": stage,
        "arm": driver["arm"], "task": meta["task"], "suite": meta["suite"],
        "production_control": "v1.0.0@4038a77ebea5f421b08b055c9aa768dcf12a890b",
        "research_git_sha_at_recording": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "runner_sha256_at_invocation": driver.get("driver_source_sha256"),
        "recorder_source_sha256": file_hash(Path(__file__)),
        "suite_manifest_sha256": meta["suite_manifest_sha256"],
        "driver_sha256": file_hash(driver_file), "grader_result_sha256": file_hash(grade_file),
        "grader_source_sha256": file_hash(ROOT / "evals/checks.py"),
        "grader_runner_sha256": file_hash(ROOT / "evals/bench.py"),
        "audit_plugin_sha256": driver.get("audit_plugin_sha256"),
        "trial_input_sha256": driver.get("trial_input_sha256"),
        "prompt_sha256": driver.get("prompt_sha256"), "config_sha256": driver["config_sha256"],
        "matched_controls_sha256": digest(canonical(controls)),
        "effective_permissions_sha256": digest(canonical({"global": config.get("permissions"),
            "agent": config.get("agents", {}).get(driver.get("agent"), {}).get("permissions")})),
        "tool_catalog_sha256": file_hash(tools),
        "model_id": driver.get("expected_model_id"),
        "model_repository": provenance["repository"], "model_revision": provenance["revision"],
        "model_manifest_sha256": provenance["manifest_sha256"],
        "model_provenance_verified": provenance["verified"],
        "model_profile_sha256_at_invocation": driver.get("model_profile_sha256"),
        "opencode_version": driver.get("opencode_version", "2.0.10"),
        "opencode_binary_sha256_at_invocation": driver.get("opencode_binary_sha256"),
        "runtime_version": runtime.get("version"),
        "runtime_memory_ceiling_bytes": runtime.get("model_memory_max"),
        "variant": driver.get("variant"), "thinking_budget_override": driver.get("thinking_budget_override"),
        "turn_timeout_seconds": driver.get("turn_timeout_seconds"),
        "driver_completed": driver["completed"], "grader_status": grade.get("status"),
        "accepted": bool(accepted), "grader_assertions": grade.get("assertions"),
        "manual_review": grade.get("manual"), "supplemental": supplemental,
        "wall_seconds": driver.get("wall_seconds"),
        "tool_calls": driver.get("tool_calls"), "tool_error_count": len(tool_errors),
        "tool_error_tools": sorted(str(item.get("tool")) for item in tool_errors),
        "native_session_count": len(token_rows), "tokens": tokens,
        "compactions": driver.get("generation_completion", {}).get("compactions"),
        "interventions": driver.get("interventions"), "resources": driver.get("resources"),
        "guard": guard, "evidence_path": str(evidence.relative_to(ROOT)),
        "limitations": ["public development fixture", "same-account grader is not a protected holdout",
                        *([] if driver.get("driver_source_sha256") else
                          ["runner source hash was not captured at invocation"]),
                        *([] if driver.get("opencode_binary_sha256") else
                          ["OpenCode binary hash was not captured at invocation"]),
                        *([] if driver.get("turn_timeout_seconds") else
                          ["turn timeout was not captured at invocation"]),
                        *([] if provenance["verified"] else
                          ["model revision provenance is unverified for this trial"])],
    }


def append(database, row):
    serialized = canonical(row).decode()
    if any(marker in serialized for marker in ("/Users/", "/private/tmp/", "/var/folders/")):
        raise ValueError("Public receipt contains a local absolute path")
    database.parent.mkdir(parents=True, exist_ok=True)
    with database.open("a+", encoding="utf-8") as out:
        fcntl.flock(out, fcntl.LOCK_EX)
        out.seek(0)
        for line in out:
            existing = json.loads(line)
            if (existing.get("run"), existing.get("stage")) == (row["run"], row["stage"]):
                raise ValueError("Trial stage already recorded; receipts are append-only")
        out.write(serialized + "\n")
        out.flush()
        os.fsync(out.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--stage", default="attempt1")
    parser.add_argument("--database", type=Path, default=DATABASE)
    args = parser.parse_args()
    row = receipt(args.run, args.stage)
    append(args.database, row)
    print(json.dumps({"run": row["run"], "arm": row["arm"], "accepted": row["accepted"],
                      "grader_status": row["grader_status"], "database": str(args.database)}))


if __name__ == "__main__":
    main()
