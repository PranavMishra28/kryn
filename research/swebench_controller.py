"""Resume the preregistered local SWE-bench phase without Codex task turns.

The official evaluator owns grading; this module owns sequencing, safety and
receipts. Launch only after the Harbor phase has finished and settled.
"""

import argparse
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research import swebench_local
from research.swebench_roster import EVALUATOR
from research.local_campaign import (atomic, controlled_env, file_sha,
                                     plugin_hashes, room, run_child, runtime_idle,
                                     sha, stop_orphan)

ROOT = Path(__file__).resolve().parents[1]
TOOL_VENV = Path("/private/tmp/kryn-python-tools-v2-20261003")
PINNED = ("research/swebench_controller.py", "research/swebench_local.py",
          "research/swebench_roster.py", "research/run_external_patch.py",
          "research/record_external.py", "research/local_only.py",
          "research/local_campaign.py", "tools/learning.py",
          "tools/native_client.py", "tools/run_native_trial.py",
          "tools/context_probe.py", "setup/opencode.template.json")
MAX_WORK_BYTES = 4 * 1024**3


def source_lock(manifest, campaign):
    """Freeze worker, grader and product bytes before the first local turn."""
    if importlib.metadata.version("swebench") != "5.0.2":
        raise RuntimeError("Official SWE-bench evaluator package version changed")
    direct = json.loads(importlib.metadata.distribution("swebench").read_text("direct_url.json"))
    source_url = urlparse(direct["url"])
    if source_url.scheme != "file" or not manifest.get("evaluator_archive_sha256"):
        raise RuntimeError("SWE-bench source archive is not pinned in the manifest")
    archive = Path(unquote(source_url.path))
    if file_sha(archive) != manifest["evaluator_archive_sha256"]:
        raise RuntimeError("Pinned SWE-bench source archive changed")
    import swebench.harness.run_evaluation as evaluator
    import swebench.harness.utils as evaluator_utils
    lock_file = campaign / "execution-lock.json"
    source = {name: file_sha(ROOT / name) for name in PINNED}
    sys.path.insert(0, str(ROOT / "research"))
    from run_external_patch import benchmark_tools
    _, _, tool = benchmark_tools(TOOL_VENV)
    worker_python = TOOL_VENV / "bin/python3"
    if subprocess.run([str(worker_python), "-c",
                       "import sys; raise SystemExit(sys.version_info < (3, 13))"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                      timeout=10).returncode:
        raise RuntimeError("KRYN worker requires Python 3.13 or newer")
    value = {"schema": 1, "manifest_sha256": file_sha(campaign / "manifest.json"),
             "source_sha256": source, "product_plugin_sha256": plugin_hashes(),
             "tool_venv": str(TOOL_VENV), "tool_manifest": tool,
             "worker_python": str(worker_python),
             "evaluator_package": "swebench==5.0.2",
             "evaluator_archive_sha256": file_sha(archive),
             "evaluator_source_sha256": {"run_evaluation": file_sha(evaluator.__file__),
                                         "utils": file_sha(evaluator_utils.__file__)},
             "evaluator_package_sha256": {
                 str(path.relative_to(Path(evaluator.__file__).parent.parent)): file_sha(path)
                 for path in sorted(Path(evaluator.__file__).parent.parent.rglob("*"))
                 if path.is_file() and "__pycache__" not in path.parts},
             "evaluator_commit": manifest["evaluator_commit"],
             "local_provider": "local/qwen", "model_id": "Qwen3.5-9B-6bit"}
    if lock_file.exists():
        if json.loads(lock_file.read_text()) != value:
            raise RuntimeError("SWE-bench execution source or environment changed")
    else:
        atomic(lock_file, value)
    return value


def work_bytes(work):
    total = 0
    if work.exists():
        for path in work.rglob("*"):
            try:
                if path.is_file():
                    total += path.stat().st_size
            except FileNotFoundError:
                pass
    return total


def wait_for_safe(campaign, work, next_name):
    while True:
        problem = room(campaign, starting=True)
        if problem is None and work_bytes(work) > MAX_WORK_BYTES:
            problem = "candidate_workspace_byte_limit"
        if problem is None and not runtime_idle():
            problem = "owned_runtime_not_idle"
        if problem is None:
            return
        atomic(campaign / "pause.json", {"reason": problem, "next": next_name,
                                          "updated_unix": time.time()})
        time.sleep(60)


def grade_once(campaign, task, run_id, prediction_path):
    """Run the pinned official Docker grader with a separate host monitor."""
    sys.path.insert(0, str(ROOT / "tools"))
    from run_native_trial import NativeResourceGuard
    from context_probe import summarize_resources

    evidence = campaign / "grader" / run_id
    marker = evidence / "running.json"
    final = evidence / "final.json"
    if final.exists():
        return json.loads(final.read_text())
    if evidence.exists():
        # A previous grader may have created partial output or seen a signal.
        # Never silently replay the same official attempt.
        if marker.exists():
            stop_orphan(marker, run_id, "swebench.harness.run_evaluation")
        return {"graded": False, "resolved": None, "reason": "interrupted_grader"}
    while problem := room(campaign, starting=True):
        atomic(campaign / "pause.json", {"reason": problem, "next": run_id,
                                          "updated_unix": time.time()})
        time.sleep(60)
    if not runtime_idle():
        raise RuntimeError("Owned model runtime did not settle before official grading")
    pinned = json.loads((campaign / "manifest.json").read_text())
    source_lock(pinned, campaign)
    parquet = swebench_local.DATASET_ROOT / task["dataset"] / "data/test-00000-of-00001.parquet"
    dataset_sha = pinned["datasets"][task["dataset"]]["test_sha256"]
    prepared = json.loads((campaign / "prepared" / task["instance_id"] / "receipt.json").read_text())
    if file_sha(parquet) != dataset_sha or swebench_local.image_identity(task)["Id"] != prepared["image_id"]:
        raise RuntimeError("Official grader dataset or image changed before grading")
    evidence.mkdir(mode=0o700, parents=True)
    grade_root = campaign / "grade-root"
    grade_root.mkdir(exist_ok=True)
    command = swebench_local.official_command(task, run_id, prediction_path)
    before_containers = set(subprocess.check_output(["docker", "ps", "-aq"],
                                                    text=True, timeout=15).splitlines())
    log = evidence / "stdout.log"
    samples = []
    monitor = NativeResourceGuard(evidence, samples, warning_samples=None)
    try:
        monitor.start()
    except RuntimeError as error:
        monitor.close()
        result = {"graded": False, "resolved": None,
                  "reason": "resource_preflight", "guard_reason": str(error)}
        atomic(final, result)
        return result
    start = time.monotonic()
    child = None
    awake = None
    stop = None
    try:
        with log.open("wb") as out:
            child = subprocess.Popen(command, cwd=grade_root, env=controlled_env(),
                                     stdin=subprocess.DEVNULL, stdout=out,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            atomic(marker, {"pid": child.pid, "started_unix": time.time(),
                            "command_sha256": sha("\0".join(command).encode())})
            awake = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(child.pid)],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
            while child.poll() is None:
                if monitor.cancel.is_set():
                    stop = "resource_guard"
                elif time.monotonic() - start > 2400:
                    stop = "grader_wall_limit"
                else:
                    stop = room(campaign, starting=False)
                if stop:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait(timeout=10)
                    break
                time.sleep(5)
            try:
                awake.wait(timeout=10)
            except subprocess.TimeoutExpired:
                awake.terminate()
                awake.wait(timeout=10)
    finally:
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=10)
        if awake is not None and awake.poll() is None:
            awake.terminate()
            awake.wait(timeout=10)
        monitor.close()
    if file_sha(parquet) != dataset_sha or swebench_local.image_identity(task)["Id"] != prepared["image_id"]:
        raise RuntimeError("Official grader dataset or image changed during grading")
    source_lock(pinned, campaign)
    official = swebench_local.official_result(grade_root, task, run_id)
    after_containers = set(subprocess.check_output(["docker", "ps", "-aq"],
                                                   text=True, timeout=15).splitlines())
    leaked_containers = sorted(after_containers - before_containers)
    result = dict(official, returncode=child.returncode if child else None,
                  stop_reason=stop, guard_reason=monitor.guard.reason,
                  new_containers_after_grader=leaked_containers,
                  guard_preflight_passed=monitor.preflight_passed,
                  resources=summarize_resources(samples),
                  wall_seconds=round(time.monotonic() - start, 3),
                  stdout_sha256=file_sha(log) if log.is_file() else None)
    result["clean_grade"] = bool(result["graded"] and result["returncode"] == 0
                                 and result["stop_reason"] is None and
                                 result["guard_reason"] is None and
                                 not leaked_containers and
                                 result.get("infra_failure_instances") == 0 and
                                 result.get("error_instances") == 0 and
                                 result["resources"].get("telemetry_complete") is True
                                 and result["resources"].get("warning_or_critical_observed") is False
                                 and result["resources"].get("swap_peak_growth_bytes") == 0)
    atomic(final, result)
    if leaked_containers:
        raise RuntimeError("Official evaluator left Docker containers; campaign stopped")
    return result


def summarize(campaign, manifest):
    rows = {path.stem.removesuffix(".final"): json.loads(path.read_text())
            for path in (campaign / "attempts").glob("*.final.json")}
    pairs = []
    for index, task in enumerate(manifest["tasks"], 1):
        names = {arm: f"s{index:02d}-{arm}" for arm in ("kryn", "native")}
        if any(name not in rows for name in names.values()):
            continue
        k, n = rows[names["kryn"]], rows[names["native"]]
        k_wire = k.get("main_wire")
        n_wire = n.get("main_wire")
        power = (k.get("worker", {}).get("ac_power_start") ==
                 k.get("worker", {}).get("ac_power_end") ==
                 n.get("worker", {}).get("ac_power_start") ==
                 n.get("worker", {}).get("ac_power_end") and
                 k.get("worker", {}).get("ac_power_start") is not None)
        controls = k.get("paired_controls")
        matched = bool(k_wire and k_wire == n_wire and power and controls and
                       controls == n.get("paired_controls") and
                       k.get("wire_stable") is True and n.get("wire_stable") is True and
                       k.get("local_only") and n.get("local_only") and
                       k["local_only"].get("generation_proven") and
                       n["local_only"].get("generation_proven") and
                       k.get("official", {}).get("clean_grade") is True and
                       n.get("official", {}).get("clean_grade") is True)
        pairs.append({"instance_id": task["instance_id"], "matched": matched,
                      "tool_wire_match": bool(k_wire and k_wire == n_wire),
                      "power_match": power, "kryn": bool(k.get("accepted")),
                      "native": bool(n.get("accepted"))})
    valid = [pair for pair in pairs if pair["matched"]]
    deltas = [int(pair["kryn"]) - int(pair["native"]) for pair in valid]
    interval = None
    if deltas:
        rng = random.Random(20261003)
        values = sorted(sum(rng.choice(deltas) for _ in deltas) / len(deltas)
                        for _ in range(10000))
        interval = [values[249], values[9749]]
    return {"schema": 1, "planned_tasks": len(manifest["tasks"]),
            "finished_arms": len(rows), "planned_arms": len(manifest["tasks"]) * 2,
            "matched_pairs": len(valid), "attrition_pairs": len(pairs) - len(valid),
            "kryn_strict": sum(pair["kryn"] for pair in valid),
            "native_strict": sum(pair["native"] for pair in valid),
            "delta": sum(deltas) / len(deltas) if deltas else None,
            "bootstrap_95_percentile": interval, "pairs": pairs,
            "updated_unix": time.time()}


def paired_controls(driver, evidence):
    """Normalize only OpenCode's random isolated root in effective permissions."""
    inventory = evidence / "agent-inventory.json"
    if not inventory.is_file():
        return None
    agents = [item for item in json.loads(inventory.read_text()).get("data", [])
              if item.get("id") == "agent"]
    if len(agents) != 1 or not isinstance(agents[0].get("permissions"), list):
        return None
    permissions = re.sub(r"/private/tmp/kryn-isolated-[^/]+", "<ISOLATED>",
                         json.dumps(agents[0]["permissions"], sort_keys=True))
    keys = ("agent", "base_commit", "prompt_sha256", "source_commit", "runner_sha256",
            "model_id", "model_repository", "model_revision", "model_profile_sha256",
            "opencode_binary_sha256", "benchmark_tool_manifest", "timeout_seconds")
    controls = {key: driver.get(key) for key in keys}
    if any(value is None for value in controls.values()):
        return None
    controls["effective_permissions_sha256"] = sha(permissions.encode())
    return controls


def run(campaign, work, expected_sha):
    manifest_file = campaign / "manifest.json"
    if (file_sha(manifest_file) != expected_sha or
            (campaign / "manifest.sha256").read_text().strip() != expected_sha):
        raise RuntimeError("SWE-bench roster changed after preregistration")
    manifest = json.loads(manifest_file.read_text())
    if (manifest.get("kind") != "swebench_local_baseline" or
            manifest.get("evaluator_commit") != EVALUATOR or
            len(manifest["tasks"]) > 16 or
            len({item["instance_id"] for item in manifest["tasks"]}) != len(manifest["tasks"])):
        raise RuntimeError("Invalid or over-budget SWE-bench roster")
    source_lock(manifest, campaign)
    (campaign / "attempts").mkdir(exist_ok=True)
    work.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (campaign / ".runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for index, task in enumerate(manifest["tasks"], 1):
            ident = task["instance_id"]
            if not all((campaign / "attempts" / f"s{index:02d}-{arm}.final.json").is_file()
                       for arm in task["arm_order"]):
                wait_for_safe(campaign, work, f"s{index:02d}")
                base, prompt, image = swebench_local.prepare(manifest, task, campaign, work)
                if work_bytes(work) > MAX_WORK_BYTES:
                    raise RuntimeError("Prepared workspace exceeded 4-GiB campaign cap")
                wait_for_safe(campaign, work, f"gold-s{index:02d}")
                gold_id = f"gold-s{index:02d}"
                gold = grade_once(campaign, task, gold_id, "gold")
                if gold.get("clean_grade") is not True:
                    raise RuntimeError("Gold official grader failed infrastructure checks")
                gold_passed = gold.get("clean_grade") and gold.get("resolved") is True
            else:
                gold_passed = None
                base = prompt = image = None
            for arm in task["arm_order"]:
                name = f"s{index:02d}-{arm}"
                final = campaign / "attempts" / (name + ".final.json")
                if final.exists():
                    continue
                source_lock(manifest, campaign)
                marker = campaign / "attempts" / (name + ".running.json")
                log = campaign / "attempts" / (name + ".stdout.log")
                if marker.exists():
                    stop_orphan(marker, name, "run_external_patch.py")
                wait_for_safe(campaign, work, name)
                if not gold_passed:
                    row = {"name": name, "arm": arm, "instance_id": ident,
                           "accepted": False, "status": "oracle_failed",
                           "official": gold}
                elif marker.exists() or log.exists():
                    candidate = work / ident / "candidate"
                    if candidate.exists():
                        shutil.rmtree(candidate)
                    row = {"name": name, "arm": arm, "instance_id": ident,
                           "accepted": False, "status": "interrupted_before_receipt"}
                else:
                    candidate = swebench_local.fresh_candidate(base, work, task)
                    if work_bytes(work) > MAX_WORK_BYTES:
                        shutil.rmtree(candidate)
                        raise RuntimeError("Paired candidate exceeds 4-GiB workspace cap")
                    evidence = campaign / "evidence" / name
                    evidence.parent.mkdir(exist_ok=True)
                    command = [str(TOOL_VENV / "bin/python3"), "-B",
                               str(ROOT / "research/run_external_patch.py"),
                               str(candidate), "--base-commit", task["base_commit"],
                               "--task-id", ident, "--prompt", str(prompt),
                               "--evidence", str(evidence), "--arm", arm,
                               "--tool-venv", str(TOOL_VENV), "--timeout", "900"]
                    if arm == "kryn":
                        command.append("--candidate-product-source")
                    worker = run_child(command, name, campaign / "attempts", campaign)
                    driver_path = evidence / "driver.json"
                    driver = json.loads(driver_path.read_text()) if driver_path.is_file() else {}
                    official = {"graded": False, "resolved": None}
                    patch = evidence / "model.patch"
                    if patch.is_file():
                        prediction = campaign / "attempts" / (name + ".prediction.json")
                        swebench_local.prediction(evidence, task, arm, prediction)
                        official = grade_once(campaign, task, name, prediction)
                        if official.get("graded") and patch.stat().st_size:
                            swebench_local.official_result(campaign / "grade-root", task, name,
                                                           model_patch=patch)
                    tool_rows = [item for item in driver.get("requests", [])
                                 if item.get("tool_count", 0) > 0]
                    main_wire = ({key: tool_rows[0].get(key) for key in
                                  ("model", "max_tokens", "numeric", "thinking",
                                   "tool_count", "tool_schema_sha256")}
                                 if tool_rows else None)
                    wire_stable = bool(main_wire and all(
                        {key: item.get(key) for key in main_wire} == main_wire
                        for item in tool_rows))
                    local = driver.get("local_only")
                    clean = driver.get("resources") or {}
                    sys.path.insert(0, str(ROOT / "research"))
                    from record_external import edited_tests
                    test_edits = edited_tests(patch.read_text()) if patch.is_file() else []
                    row = {"name": name, "arm": arm, "instance_id": ident,
                           "status": "graded" if official.get("graded") else "ungraded",
                           "accepted": bool(driver.get("completed") is True and
                                            worker["returncode"] == 0 and
                                            worker["stop_reason"] is None and
                                            local and local.get("generation_proven") is True and
                                            clean.get("telemetry_complete") is True and
                                            clean.get("warning_or_critical_observed") is False and
                                            clean.get("swap_peak_growth_bytes") == 0 and
                                            not test_edits and
                                            official.get("clean_grade") is True and
                                            official.get("resolved") is True),
                           "driver_sha256": file_sha(driver_path) if driver_path.is_file() else None,
                           "patch_sha256": file_sha(patch) if patch.is_file() else None,
                           "edited_test_paths": test_edits,
                           "local_only": local, "main_wire": main_wire,
                           "wire_stable": wire_stable,
                           "paired_controls": paired_controls(driver, evidence),
                           "official": official, "worker": worker}
                    shutil.rmtree(candidate)
                atomic(final, row)
                atomic(campaign / "progress.json", summarize(campaign, manifest))
                if row["status"] == "ungraded" and row["driver_sha256"] is None:
                    raise RuntimeError("External worker wrote no driver receipt; stop the campaign")
            prepared = campaign / "prepared" / ident / "receipt.json"
            released = campaign / "prepared" / ident / "image-release.json"
            if prepared.is_file() and not released.exists():
                release = swebench_local.release_image(json.loads(prepared.read_text()))
                atomic(released, release)
            if released.exists() and (work / ident).exists():
                shutil.rmtree(work / ident)
        report = summarize(campaign, manifest)
        report["finished"] = report["finished_arms"] == report["planned_arms"]
        atomic(campaign / "final-report.json", report)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    report = run(args.campaign.resolve(), args.work.resolve(), args.expected_sha256)
    print(json.dumps({"finished": report["finished"],
                      "matched_pairs": report["matched_pairs"],
                      "kryn_strict": report["kryn_strict"],
                      "native_strict": report["native_strict"]}))


if __name__ == "__main__":
    main()
