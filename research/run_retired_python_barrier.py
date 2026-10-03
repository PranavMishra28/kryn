#!/usr/bin/env python3
"""Exercise the Agent-to-grader volume barrier on a retired development task."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys

from agent_grade_barrier import run_candidate_to_grader
from check_holdout_boundary import background_boundary
from preflight_protected_python import grade as grade_task


TASK = "linecfg-duplicate-key"
MANIFEST_SHA256 = "804278f90dac2d253d28b008b4150c449e361f0b4513ff41929968b1d025c314"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    parser.add_argument("preflight_report", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--tool-venv", required=True, type=Path)
    parser.add_argument("--candidate-product-source", action="store_true")
    args = parser.parse_args()
    draft, preflight, receipt = (path.absolute() for path in
                                 (args.draft, args.preflight_report, args.receipt))
    manifest_file = draft / "manifest.json"
    if sha(manifest_file) != MANIFEST_SHA256:
        parser.error("Retired draft manifest differs from the frozen pilot")
    entry = next((item for item in json.loads(manifest_file.read_text())
                  if item["id"] == TASK), None)
    if not entry or not entry.get("retirement_reason") or entry.get("protected_status"):
        parser.error("Pilot requires the retired, protected-ineligible task")
    prompt = draft / "tasks" / TASK / "prompt.md"
    seed = draft / "tasks" / TASK / "seed"
    oracle = draft / "private" / "oracles" / (TASK + ".py")
    reference = draft / "private" / "solutions" / (TASK + ".patch")
    partial = draft / "private" / "partials" / (TASK + ".patch")
    if any(sha(path) != entry[key] for path, key in
           ((prompt, "prompt_sha256"), (oracle, "oracle_sha256"),
            (reference, "reference_sha256"), (partial, "partial_sha256"))):
        parser.error("Retired task bytes differ from the frozen manifest")
    source_root = Path(__file__).resolve().parents[1]
    source_commit = subprocess.check_output(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(
        ["git", "-C", str(source_root), "status", "--porcelain"], text=True)
    gate = json.loads((preflight / "report.json").read_text())
    if (status or gate.get("source_commit") != source_commit or
            gate.get("draft_manifest_sha256") != MANIFEST_SHA256 or
            gate.get("task_id") != TASK or not gate.get("mechanics_passed") or
            not gate.get("controls_pass") or not gate.get("detached") or
            not gate.get("retired_from_holdout") or gate.get("passed") or
            Path(gate.get("benchmark_tool_path", "")).resolve() !=
                (args.tool_venv / "bin").resolve() or
            entry["grader_python_sha256"] != sha(Path(sys.executable).resolve())):
        parser.error("Current-source retired-task preflight or pinned grader is missing")
    boundary = Path(inspect.getfile(background_boundary)).resolve()

    def grade(workspace, private, evidence):
        result = grade_task(oracle, workspace, private, boundary, draft,
                            evidence / "trusted-grader.log")
        return {"oracle": result}

    error = None
    try:
        run_candidate_to_grader(
            seed=seed, prompt=prompt, task_id=TASK, arm="kryn",
            tool_venv=args.tool_venv, receipt=receipt,
            hidden_paths=[oracle, reference, partial, manifest_file],
            grade=grade, timeout=900,
            candidate_product_source=args.candidate_product_source)
    except BaseException as exc:
        error = type(exc).__name__ + ": " + str(exc)
    barrier = json.loads((receipt / "barrier.json").read_text()) if (receipt / "barrier.json").exists() else {}
    oracle_result = barrier.get("grader_result", {}).get("oracle", {})
    accepted = bool(not error and barrier.get("graded") and
                    all(barrier.get(key) for key in
                        ("candidate_detached", "capture_detached", "grader_detached")) and
                    barrier.get("agent", {}).get("completed") and
                    barrier.get("agent", {}).get("requests") and
                    barrier.get("capture_guard", {}).get("resources", {}).get("telemetry_complete") and
                    not barrier.get("capture_guard", {}).get("cancelled") and
                    oracle_result.get("exit") == 0 and
                    not oracle_result.get("timed_out") and
                    oracle_result.get("output_bounded"))
    summary = {"schema": 1, "kind": "retired_python_agent_grade_pilot",
               "source_commit": source_commit, "task_id": TASK,
               "draft_manifest_sha256": MANIFEST_SHA256,
               "candidate_product_source": args.candidate_product_source,
               "preflight_report_sha256": sha(preflight / "report.json"),
               "barrier_report_sha256": sha(receipt / "barrier.json") if barrier else None,
               "accepted": accepted, "protected_result": False, "error": error}
    if receipt.is_dir():
        (receipt / "pilot-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True))
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
