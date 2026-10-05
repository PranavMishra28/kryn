"""Durable sequencing for one frozen local container development pair.

Native OpenCode owns generation; the official evaluator owns tests. Existing
stage markers are never executed twice. Recovery only preserves interrupted
source and settles owned resources, and cannot upgrade an interrupted result.
"""

import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid
import urllib.error

from research.campaign_supervisor import (Waiting, power, power_problem, memory_pressure,
    size, event, save, digest, live_commands, stop_pid, MIN_FREE, MAX_RAW, MEMORY_COOLDOWN_SECONDS)
from research.container_admission import ROOT
from research.container_generation import frozen
from research.container_worker import HostGuard
from research import local_only
from research.local_campaign import controlled_env


def read(path):
    return json.loads(Path(path).read_text())


def once(path, value):
    """A deterministic preparation may resume; an existing receipt may not change."""
    path = Path(path)
    if path.exists():
        if read(path) != value:
            raise RuntimeError("Immutable receipt changed: " + str(path))
    else:
        save(path, value)


def pin(path):
    path = Path(path)
    return {"path": str(path.resolve()), "sha256": digest(path)} if path.is_file() else None


def problem(campaign):
    import shutil
    issue = power_problem(power(), True)
    if memory_pressure() != 1:
        issue = "host_memory_not_green"
    if shutil.disk_usage(campaign).free < MIN_FREE or size(campaign) > MAX_RAW:
        issue = "disk_or_raw_data_limit"
    return issue


def runtime_ready(manifest):
    if manifest["kind"] == "swe_container_generation_canary":
        return True
    local_only.localai.ensure_runtime()
    local_only.localai.runtime_identity()
    value = local_only.localai.runtime_metadata()
    if (value.get("healthy") is not True or value.get("model") != local_only.MODEL
            or value.get("max_model_len") != 98304 or value.get("model_memory_max") != 22 * 1024**3):
        raise RuntimeError("Owned local runtime identity, context or ceiling drift")
    if value.get("active_requests") != 0 or value.get("waiting_requests") != 0:
        return False
    return True


def wait_ready(campaign, manifest, stopping):
    state = campaign / "state"
    stable = 0
    previous = None
    while not stopping[0]:
        frozen(campaign)
        try:
            issue = problem(campaign)
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
            issue = "safety_telemetry: " + str(error)
        cooldown = state / "cooldown.json"
        if cooldown.exists() and read(cooldown)["until_unix"] > time.time():
            issue = issue or "guard_cooldown"
        stable = stable + 1 if issue is None else 0
        if stable >= 3:
            try:
                if runtime_ready(manifest) and not problem(campaign):
                    return True
                issue = "owned_runtime_busy"
            except (OSError, urllib.error.URLError, subprocess.TimeoutExpired) as error:
                issue = "runtime_service_unavailable: " + str(error)
            except subprocess.CalledProcessError as error:
                if (error.returncode != 1 or error.cmd !=
                        ['/usr/sbin/lsof', '-nP', '-a', '-iTCP:8000', '-sTCP:LISTEN', '-Fpu']):
                    raise
                issue = "owned_runtime_absent"
            stable = 0
        reason = issue or "safe_admission_stabilizing"
        if reason != previous:
            event(state, "waiting", reason=reason)
            previous = reason
        time.sleep(15)
    return False


def argv_for(campaign, arm, phase):
    from research.swebench_local import EVALUATOR_PYTHON
    target = campaign if phase == "generation" else campaign / "grading" / arm
    return [str(EVALUATOR_PYTHON), "-B", "-m", "research.container_" + phase,
            str(target), *([arm] if phase == "generation" else [])]


def stop_stage(argv):
    # The module plus exact canonical campaign/arm identifies only this child.
    expected = " ".join(argv[3:])
    for pid, command in live_commands().items():
        if command.endswith(expected):
            stop_pid(pid, [expected])


def stage(campaign, manifest, arm, phase, stopping):
    state = campaign / "state"
    prefix = state / (arm + "." + phase)
    started = prefix.with_name(prefix.name + "-start.json")
    finished = prefix.with_name(prefix.name + "-exit.json")
    argv = argv_for(campaign, arm, phase)
    if started.exists() and (read(started)["argv"] != argv
            or read(started)["manifest_sha256"] != digest(campaign / "manifest.json")):
        raise RuntimeError("Stage command or manifest drift")
    if finished.exists():
        if not started.exists():
            raise RuntimeError("Stage result has no launch receipt")
        return read(finished)
    if started.exists():
        stop_stage(argv)
        value = {"returncode": None, "reason": "controller_interrupted", "finished_unix": time.time()}
        once(finished, value)
        return value
    if not wait_ready(campaign, manifest, stopping):
        raise Waiting("supervisor_exit")
    directory = prefix.with_name(prefix.name + "-guard-" + uuid.uuid4().hex)
    directory.mkdir()
    child = None
    reason = None
    code = None
    try:
        with HostGuard(directory) as guard:
            # No arm is spent by an earlier unsafe/busy runtime admission.
            frozen(campaign)
            if not runtime_ready(manifest) or problem(campaign):
                raise Waiting("runtime_or_safety_changed_before_launch")
            once(started, {"arm": arm, "phase": phase, "argv": argv,
                          "manifest_sha256": digest(campaign / "manifest.json"), "started_unix": time.time()})
            with prefix.with_suffix(prefix.suffix + ".log").open("xb") as output:
                child = subprocess.Popen(argv, cwd=ROOT, env=controlled_env(), stdin=subprocess.DEVNULL,
                                         stdout=output, stderr=subprocess.STDOUT)
                event(state, "running", arm=arm, phase=phase, pid=child.pid)
                deadline = time.monotonic() + (manifest["wall_seconds"] + 300 if phase == "generation" else 2400)
                next_size_check = 0
                try:
                    while child.poll() is None:
                        guard.check()
                        if stopping[0]:
                            raise Waiting("supervisor_exit")
                        if time.monotonic() >= deadline:
                            raise RuntimeError("stage_deadline")
                        if time.monotonic() >= next_size_check:
                            if size(campaign) > MAX_RAW:
                                raise RuntimeError("raw_data_limit")
                            next_size_check = time.monotonic() + 5
                        time.sleep(1)
                    code = child.returncode
                finally:
                    if child.poll() is None:
                        stop_stage(argv)
                        child.wait(timeout=15)
            guard.check()
    except Exception as error:
        if not started.exists():
            # HostGuard re-admission can race a transient power/memory switch.
            raise Waiting(str(error)) from error
        reason = str(error)
        save(state / "cooldown.json", {"until_unix": time.time() + MEMORY_COOLDOWN_SECONDS, "reason": reason})
    finally:
        if child is not None and child.poll() is None:
            stop_stage(argv)
            child.wait(timeout=15)
    value = {"returncode": code, "reason": reason, "finished_unix": time.time()}
    once(finished, value)
    return value


def prepare_grade(campaign, manifest, arm):
    from research.swebench_controller import source_lock
    template = campaign / "grader-template.json"
    if digest(template) != manifest["grader_template_sha256"]:
        raise RuntimeError("Frozen grader template drift")
    directory = campaign / "grading" / arm
    directory.mkdir(parents=True, exist_ok=True)
    generation = campaign / arm
    patch = (generation / "model.patch").read_bytes()
    target = directory / "model.patch"
    if target.exists() and target.read_bytes() != patch:
        raise RuntimeError("Candidate patch preparation changed")
    if not target.exists():
        with target.open("xb") as output:
            output.write(patch)
            output.flush(); os.fsync(output.fileno())
    value = read(template)
    value.update(kind="swe_container_development_grade", patch_role="candidate", expected_resolved=None,
        source_sha256=manifest["source_sha256"], synthetic_inference=manifest["kind"] == "swe_container_generation_canary",
        task=manifest["task"], arm=arm, generation_root=str(generation), patch_sha256=digest(target),
        generation_manifest_sha256=digest(campaign / "manifest.json"),
        generation_sha256={name: digest(generation / name) for name in ("driver.json", "ownership.json", "model.patch")})
    once(directory / "manifest.json", value)
    seal = directory / "manifest.sha256"
    if seal.exists() and seal.read_text().strip() != digest(directory / "manifest.json"):
        raise RuntimeError("Candidate grade seal drift")
    if not seal.exists():
        seal.write_text(digest(directory / "manifest.json") + "\n")
    source_lock(value, directory)
    return directory


def eligible(driver):
    return bool(driver and driver.get("cleanup_settled") is True and driver.get("worker_exported") is True
        and driver.get("inference_relay_settled") is True and driver.get("intervention") in (None, "timeout")
        and (driver.get("completed") is True or driver.get("intervention") == "timeout")
        and not driver.get("guard_reason") and not driver.get("error") and not driver.get("edited_test_paths")
        and driver.get("wire", {}).get("matches_frozen") is True)


def terminal_arm(campaign, manifest, arm, stopping):
    from research.container_recovery import recover, settle_recorded
    terminal = campaign / "state" / (arm + ".json")
    if terminal.exists():
        return read(terminal)
    result = stage(campaign, manifest, arm, "generation", stopping)
    folder = campaign / arm
    driver_path = folder / "driver.json"
    driver = read(driver_path) if driver_path.is_file() else None
    recovery = None
    grade_path = None
    reason = result["reason"]
    if reason or not driver or not driver.get("cleanup_settled") or not driver.get("worker_exported"):
        recovery = recover(campaign, arm, admit=lambda: wait_ready(campaign, manifest, stopping))
        if recovery.get("waiting"):
            raise Waiting("deferred_export_waiting")
        recovery = pin(folder / "recovery" / "result.json")
        if recovery is None:
            raise RuntimeError("Recovery did not produce a pinned result")
    elif eligible(driver):
        if (folder / "model.patch").stat().st_size == 0:
            reason = "no_change"
        else:
            grade = prepare_grade(campaign, manifest, arm)
            outcome = stage(campaign, manifest, arm, "grader", stopping)
            grade_path = grade / "grade" / "result.json"
            if outcome["reason"] or not grade_path.is_file() or not read(grade_path).get("cleanup_settled"):
                receipt = settle_recorded(grade / "grade", manifest["official_image_id"], grade / "recovery")
                if receipt.get("waiting"):
                    raise Waiting("grader_cleanup_waiting")
                recovery = pin(grade / "recovery" / "result.json")
                if recovery is None:
                    raise RuntimeError("Grader recovery has no receipt")
                reason = outcome["reason"] or "grader_interrupted"
    value = {"status": "terminal", "manifest_sha256": digest(campaign / "manifest.json"),
        "generation": pin(driver_path), "grade": pin(grade_path) if grade_path else None,
        "recovery": recovery, "reason": reason, "terminal_unix": time.time(),
        "controller": {key: pin(campaign / "state" / (arm + ".generation-" + name + ".json"))
                       for key, name in (("start", "start"), ("finish", "exit"))}}
    once(terminal, value)
    return value


def validate_protocol(campaign):
    from research.swebench_controller import source_lock
    from research.container_grader import wheel_paths
    from research.swebench_local import image_identity
    manifest = frozen(campaign)
    if (digest(campaign / "grader-template.json") != manifest["grader_template_sha256"]
            or digest(ROOT / "research/container_adjudication.py") != manifest["adjudicator_sha256"]
            or not (campaign / "execution-lock.json").is_file()):
        raise RuntimeError("Controller/grader/adjudicator protocol is not sealed")
    lock = source_lock(manifest, campaign)
    if lock["evaluator_package_sha256"] != manifest["evaluator_package_sha256"]:
        raise RuntimeError("Frozen official evaluator changed")
    template = read(campaign / "grader-template.json")
    for key in ("task", "evaluator_archive_sha256", "evaluator_commit", "evaluator_package_sha256",
                "official_image_digest", "official_image_id", "wheelhouse", "wheel_sha256", "datasets"):
        if template[key] != manifest[key]:
            raise RuntimeError("Generation and grading protocol differ: " + key)
    wheel_paths(manifest)
    if image_identity({"image_tag": manifest["official_image_digest"]})["Id"] != manifest["official_image_id"]:
        raise RuntimeError("Frozen official image changed")
    return manifest


def supervise(campaign):
    manifest = validate_protocol(campaign)
    state = campaign / "state"
    state.mkdir(mode=0o700, exist_ok=True)
    stopping = [False]
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopping.__setitem__(0, True))
    with (state / ".controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (state / "status.json").is_file() and read(state / "status.json")["kind"] == "needs_action":
            return
        try:
            for arm in manifest["arm_order"]:
                while not stopping[0]:
                    frozen(campaign)
                    try:
                        terminal_arm(campaign, manifest, arm, stopping)
                        break
                    except Waiting as error:
                        event(state, "waiting", arm=arm, reason=str(error))
                        time.sleep(15)
                if stopping[0]:
                    return
            frozen(campaign)
            if manifest["kind"] == "swe_container_generation_canary":
                # Synthetic transport controls never enter real-model scoring.
                once(campaign / "canary-controller.json", {"kind": "container_controller_no_model",
                    "finished": True, "manifest_sha256": digest(campaign / "manifest.json"),
                    "terminal_sha256": {arm: digest(state / (arm + ".json")) for arm in manifest["arm_order"]}})
                event(state, "canary_complete", release_qualified=False)
            else:
                from research.container_adjudication import adjudicate
                if not (campaign / "adjudication.json").exists():
                    adjudicate(campaign)
                event(state, "adjudicated", result_sha256=digest(campaign / "adjudication.json"), release_qualified=False)
        except Exception as error:
            event(state, "needs_action", error=str(error))
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    args = parser.parse_args()
    supervise(args.campaign.resolve(strict=True))
