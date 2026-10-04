#!/usr/bin/env python3
"""Finish the local baseline with an exposed long-horizon regression screen.

This process waits for the independent SWE-bench phase, then runs one paired
three-stage OpenCode trial with two native compactions and two real restarts.
Its public fixture is development evidence, never unseen validation.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.local_campaign import (atomic, file_sha, plugin_hashes, room,
                                     run_child, runtime_idle, sha, stop_orphan)

PINNED = ("research/post_baseline.py", "research/run_public_staged_model.py",
          "research/public_staged_fixture.py", "research/staged_lifecycle_canned.py",
          "research/staged_docker_grade.py", "research/local_only.py",
          "research/run_external_patch.py", "setup/opencode.template.json",
          "setup/accepted-profile.json", "tools/learning.py", "tools/native_client.py")
STAGED = Path("/private/tmp/kryn-staged-baseline-20261003-v1")


def source_hashes():
    return {name: file_sha(ROOT / name) for name in PINNED}


def freeze(output, harbor, swebench):
    if output.exists():
        raise FileExistsError(output)
    if STAGED.exists():
        raise RuntimeError("Frozen staged output path is already occupied")
    for source in (harbor, swebench):
        if not (source / "manifest.json").is_file():
            raise RuntimeError("A prerequisite campaign manifest is missing")
    output.mkdir(mode=0o700, parents=True)
    manifest = {"schema": 1, "kind": "local_baseline_followthrough",
                "harbor": str(harbor), "harbor_manifest_sha256": file_sha(harbor / "manifest.json"),
                "swebench": str(swebench),
                "swebench_manifest_sha256": file_sha(swebench / "manifest.json"),
                "staged_output": str(STAGED), "staged_fixture_status": "exposed_development",
                "source_sha256": source_hashes(), "product_plugin_sha256": plugin_hashes(),
                "max_staged_wall_seconds": 7200, "attempts": 1}
    atomic(output / "manifest.json", manifest)
    (output / "manifest.sha256").write_text(file_sha(output / "manifest.json") + "\n")
    return file_sha(output / "manifest.json")


def _live(pid, expected):
    result = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                            capture_output=True, text=True, timeout=10)
    return result.returncode == 0 and expected in result.stdout


def _wait(campaign, manifest):
    swebench = Path(manifest["swebench"])
    while True:
        final = swebench / "final-report.json"
        status_file = swebench / "chain-status.json"
        if final.is_file():
            report = json.loads(final.read_text())
            if not report.get("finished"):
                raise RuntimeError("SWE-bench final report is incomplete")
            return report
        status = json.loads(status_file.read_text()) if status_file.is_file() else {}
        chain_pid = int((swebench / "chain.pid").read_text().strip())
        if status.get("state") == "failed" or not _live(chain_pid, "campaign_chain.py"):
            raise RuntimeError("SWE-bench chain stopped before its final report")
        atomic(campaign / "status.json", {"state": "waiting_for_swebench",
                                          "updated_unix": time.time()})
        time.sleep(120)


def _safe(campaign):
    while True:
        problem = room(campaign, starting=True)
        if problem is None and not runtime_idle():
            problem = "owned_runtime_not_idle"
        if problem is None:
            return
        atomic(campaign / "status.json", {"state": "paused", "reason": problem,
                                          "updated_unix": time.time()})
        time.sleep(60)


def _staged(campaign, manifest):
    attempts = campaign / "attempts"
    attempts.mkdir(exist_ok=True)
    name = "baseline-staged"
    marker = attempts / (name + ".running.json")
    log = attempts / (name + ".stdout.log")
    receipt = attempts / (name + ".final.json")
    if receipt.is_file():
        return json.loads(receipt.read_text())
    if marker.exists() or log.exists() or STAGED.exists():
        if marker.exists():
            stop_orphan(marker, str(STAGED), "run_public_staged_model.py")
        result = {"passed": False, "status": "interrupted_or_partial",
                  "protected_eligible": False}
    else:
        command = [sys.executable, "-B", str(ROOT / "research/run_public_staged_model.py"),
                   str(STAGED)]
        worker = run_child(command, name, attempts, campaign, wall=7200)
        raw = STAGED / "result.json"
        report = json.loads(raw.read_text()) if raw.is_file() else {}
        local = all((row.get("local_only") or {}).get("generation_proven") is True
                    for row in report.get("results", [])) and len(report.get("results", [])) == 2
        result = {"passed": bool(report.get("passed") and local and
                                 worker["returncode"] == 0 and
                                 worker["stop_reason"] is None),
                  "status": "graded" if raw.is_file() else "ungraded",
                  "protected_eligible": False, "local_only_proven": local,
                  "result_sha256": file_sha(raw) if raw.is_file() else None,
                  "arm_passed": {row["arm"]: row.get("passed") for row in
                                 report.get("results", [])}, "worker": worker}
    atomic(receipt, result)
    return result


def run(campaign, expected_sha):
    path = campaign / "manifest.json"
    if (file_sha(path) != expected_sha or
            (campaign / "manifest.sha256").read_text().strip() != expected_sha):
        raise RuntimeError("Followthrough manifest changed after preregistration")
    manifest = json.loads(path.read_text())
    if (manifest.get("kind") != "local_baseline_followthrough" or
            manifest["source_sha256"] != source_hashes() or
            manifest["product_plugin_sha256"] != plugin_hashes()):
        raise RuntimeError("Frozen staged source or product payload changed")
    harbor = Path(manifest["harbor"])
    if file_sha(harbor / "manifest.json") != manifest["harbor_manifest_sha256"]:
        raise RuntimeError("Harbor baseline manifest drifted")
    if file_sha(Path(manifest["swebench"]) / "manifest.json") != manifest[
            "swebench_manifest_sha256"]:
        raise RuntimeError("SWE-bench baseline manifest drifted")
    swe = _wait(campaign, manifest)
    harbor_report = json.loads((harbor / "final-report.json").read_text())
    if not harbor_report.get("finished"):
        raise RuntimeError("Harbor baseline is not finished")
    _safe(campaign)
    staged = _staged(campaign, manifest)
    if manifest["source_sha256"] != source_hashes() or manifest[
            "product_plugin_sha256"] != plugin_hashes():
        raise RuntimeError("Frozen source changed during the staged trial")
    result = {"schema": 1, "kind": "local_baseline_summary",
              "harbor": {"planned_tasks": harbor_report["planned_tasks"],
                         "finished_arms": harbor_report["finished_arms"],
                         "paired": harbor_report["paired"],
                         "strict_kryn": harbor_report["strict_kryn"],
                         "strict_native": harbor_report["strict_native"]},
              "swebench": {key: swe.get(key) for key in
                           ("planned_tasks", "finished_arms", "matched_pairs",
                            "attrition_pairs", "kryn_strict", "native_strict",
                            "delta", "bootstrap_95_percentile", "pairs")},
              "long_horizon_exposed_development": staged,
              "frontier_adjacent_qualified": False,
              "candidate_validation_completed": False,
              "updated_unix": time.time()}
    atomic(campaign / "baseline-summary.json", result)
    atomic(campaign / "status.json", {"state": "baseline_checkpoint_ready",
                                      "updated_unix": time.time()})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("output", type=Path)
    f.add_argument("harbor", type=Path)
    f.add_argument("swebench", type=Path)
    r = sub.add_parser("run")
    r.add_argument("campaign", type=Path)
    r.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        digest = freeze(args.output.resolve(), args.harbor.resolve(), args.swebench.resolve())
        print(json.dumps({"manifest_sha256": digest}))
    else:
        report = run(args.campaign.resolve(), args.expected_sha256)
        print(json.dumps({"checkpoint_ready": True,
                          "staged_passed": report["long_horizon_exposed_development"]["passed"]}))


if __name__ == "__main__":
    main()
