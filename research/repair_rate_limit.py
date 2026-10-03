#!/usr/bin/env python3
"""One public, guarded repair screen on an already exposed failed patch."""
import argparse
import json
import os
from pathlib import Path
import secrets
import tempfile

from agent_grade_barrier import clean_clone, run_candidate_to_grader
from public_source_pagination import checked, sha, source_calls, wire_contracts
from public_source_rate_limit import docker_grade, validate_source


PAIR_SHA = "825e4f494e19e1420c636cb366d5c32e3c62d1b26d08cd244e4ccb3e5cb12b6c"
FIXTURE_SHA = "3ee47a1e1facc0b64da13aae66f1e4e22dc38279f80758461385d5b1f62ebc3d"
FAILED_PATCH_SHA = "04c74f195db46923a469620cb6730c3ea604ee57b8c0539ad402b8ee3768827c"
FAILURE = ("Independent verification of the current patch found one failing criterion. "
           "For max_retries=1 with two consecutive secondary-limit responses, "
           "expected RuntimeError, fetch statuses [429, 429], and sleep calls [60]. "
           "Observed RuntimeError, fetch statuses [429, 429], and sleep calls "
           "[60, 120]. The other seven independent cases passed. Repair the "
           "current implementation and run a local check that exercises this "
           "observable boundary. Do not claim that an independent grader passed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "source_dir", "grade_root", "tool_venv", "output"):
        parser.add_argument("--" + name.replace("_", "-"), required=True, type=Path)
    args = parser.parse_args()
    original, source_dir, grade_root, tool_venv, output = (
        getattr(args, name).absolute() for name in
        ("original", "source_dir", "grade_root", "tool_venv", "output"))
    if (output.parent != Path("/private/tmp") or output.exists() or
            grade_root != grade_root.resolve() or not grade_root.is_dir() or
            grade_root.stat().st_uid != os.geteuid() or
            grade_root.stat().st_mode & 0o077 or not tool_venv.is_dir()):
        parser.error("Use a fresh direct /private/tmp output and owned private grade root")
    source, provenance = validate_source(source_dir)
    pair_file, fixture_file = original / "pair.json", original / "fixture.json"
    pair = json.loads(pair_file.read_text())
    failed = next(run for run in pair["runs"] if run["arm"] == "kryn")
    patch = Path(failed["receipt"]) / "agent-evidence/model.patch"
    if (sha(pair_file) != PAIR_SHA or sha(fixture_file) != FIXTURE_SHA or
            sha(patch) != FAILED_PATCH_SHA or failed["accepted"] or
            failed["grade"]["cases"].get("retry-exhausted") is not False or
            sum(failed["grade"]["cases"].values()) != 7):
        raise ValueError("Frozen failed input changed")
    if checked(["git", "-C", str(Path(__file__).resolve().parents[1]),
                "status", "--porcelain"]):
        raise ValueError("Research source must be a clean commit before generation")
    output.mkdir(mode=0o700)
    seed = output / "repair-seed"
    base = checked(["git", "-C", str(original / "seed"), "rev-parse", "HEAD"])
    clean_clone(original / "seed", seed, base)
    checked(["git", "-C", str(seed), "apply", "--check", str(patch)])
    checked(["git", "-C", str(seed), "apply", str(patch)])
    checked(["git", "-C", str(seed), "add", "-A"])
    checked(["git", "-C", str(seed), "-c", "user.name=KRYN Research",
             "-c", "user.email=research@localhost", "commit", "-m", "Frozen failed patch"])
    seed_commit = checked(["git", "-C", str(seed), "rev-parse", "HEAD"])
    baseline = docker_grade(seed)
    if (baseline["accepted"] or sum(baseline["cases"].values()) != 7 or
            baseline["cases"].get("retry-exhausted") is not False):
        raise RuntimeError("Frozen baseline did not reproduce 7/8")
    prompt = output / "prompt.txt"
    prompt.write_text((original / "prompt.txt").read_text().rstrip() +
                      "\n\n" + FAILURE + "\n")
    receipt = Path("/private/tmp") / ("kryn-rate-limit-repair-" + secrets.token_hex(8))

    def grade(apfs_workspace, _private, evidence):
        with tempfile.TemporaryDirectory(prefix="kryn-rate-repair-grade-",
                                         dir=grade_root) as temporary:
            staged = Path(temporary) / "workspace"
            clean_clone(seed, staged, seed_commit)
            model_patch = evidence / "agent-evidence/model.patch"
            checked(["git", "-C", str(staged), "apply", "--check", str(model_patch)])
            checked(["git", "-C", str(staged), "apply", str(model_patch)])
            same = sha(staged / "backoff.py") == sha(apfs_workspace / "backoff.py")
            if not same:
                raise RuntimeError("Fresh Docker-visible clone differs from APFS grader")
            result = docker_grade(staged)
            return {**result, "staged_equals_apfs": same,
                    "repair_patch_sha256": sha(model_patch)}

    report = {"schema": 1, "kind": "public_exposed_rate_limit_repair_screen",
              "protected_status": False, "source_commit": checked([
                  "git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"]),
              "script_sha256": sha(Path(__file__)), "original_pair_sha256": sha(pair_file),
              "original_patch_sha256": sha(patch), "original_fixture_sha256": sha(fixture_file),
              "repair_seed_commit": seed_commit, "prompt_sha256": sha(prompt),
              "baseline": baseline, "receipt": str(receipt)}
    try:
        result = run_candidate_to_grader(
            seed=seed, prompt=prompt, task_id="public-rate-limit-repair", arm="kryn",
            tool_venv=tool_venv, receipt=receipt,
            hidden_paths=[provenance, original / "reference.patch",
                          original / "partial.patch", pair_file, Path(__file__)],
            grade=grade, timeout=900, source_file=source)
        agent, graded = result["agent"], result["grader_result"]
        reads = source_calls(receipt, source)
        used = any(call["tool"] == "read" and call["status"] == "completed" and
                   call["truncated"] is False for call in reads)
        report.update(native_completed=agent["completed"], grade=graded,
                      source_used=used, source_calls=reads,
                      wire_contracts=wire_contracts(agent.get("requests", [])),
                      request_count=len(agent.get("requests", [])),
                      resources=agent["resources"], wall_seconds=result["wall_seconds"],
                      candidate_detached=result["candidate_detached"],
                      capture_detached=result["capture_detached"],
                      grader_detached=result["grader_detached"])
        report["accepted"] = bool(result["graded"] and agent["completed"] and used and
                                  graded["accepted"] and graded["staged_equals_apfs"] and
                                  result["candidate_detached"] and
                                  result["capture_detached"] and
                                  result["grader_detached"] and
                                  agent["resources"]["telemetry_complete"] and
                                  not agent["resources"]["warning_or_critical_observed"])
    except BaseException as error:
        report["accepted"] = False
        report["error"] = type(error).__name__ + ": " + str(error)
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"result": str(output / "result.json"),
                      "accepted": report["accepted"], "error": report.get("error")}))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
