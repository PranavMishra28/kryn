#!/usr/bin/env python3
"""Resume a preregistered, single-worker local Harbor campaign without Codex turns.

Raw task material and logs stay in the private campaign directory. This process
never selects a model: each worker must pass research.local_only before inference.
"""

import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import tomllib

ROOT = Path(__file__).resolve().parents[1]
HARBOR_COMMIT = "fd1521a1da6250d9ed8fc7505caa0b7a72f36c4b"
TASKS_COMMIT = "69671fbaac6d67a7ef0dfec016cc38a64ef7a77c"
EXCLUDED = {"regex-log", "log-summary-date-ranges", "raman-fitting",
            "nginx-request-logging", "sqlite-with-gcov"}
MIN_FREE = 12 * 1024**3
MAX_RAW = 8 * 1024**3
MAX_ATTEMPTS = 32
MAX_WORKER_SECONDS = 2700
MIN_START_BATTERY = 40
STOP_BATTERY = 25
PINNED_FILES = ("research/local_campaign.py", "research/local_only.py",
                "research/run_harbor_calibration.py", "research/harbor_kryn_agent.py",
                "setup/opencode.template.json", "tools/learning.py",
                "tools/native_client.py")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def plugin_hashes():
    sys.path.insert(0, str(ROOT))
    from tools.native_client import product_plugin_files
    return {name: sha(payload) for name, payload in
            sorted(product_plugin_files(ROOT).items())}


def atomic(path, value):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as out:
        json.dump(value, out, sort_keys=True, indent=2)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())
    os.replace(temporary, path)


def call(command, *, timeout=30, cwd=None):
    return subprocess.check_output(command, text=True, timeout=timeout, cwd=cwd).strip()


def source_commit(source):
    return call(["git", "-C", str(source), "rev-parse", "HEAD"])


def task_bytes(source, name, filename):
    return subprocess.check_output(["git", "-C", str(source), "show",
                                    "HEAD:" + name + "/" + filename], timeout=30)


def freeze_harbor(source, output, count, seed, harbor_python):
    if not 4 <= count <= 16:
        raise ValueError("The Harbor baseline must contain 4–16 tasks")
    if source_commit(source) != TASKS_COMMIT:
        raise RuntimeError("Official Terminal-Bench task source commit changed")
    harbor_checkout = harbor_python.parent.parent.parent
    if source_commit(harbor_checkout) != HARBOR_COMMIT:
        raise RuntimeError("Harbor evaluator commit changed")
    if call([str(harbor_python), "-c", "import harbor; print(harbor.__version__)"],
            timeout=10) != "0.23.0":
        raise RuntimeError("Pinned Harbor 0.23.0 is unavailable")
    names = call(["git", "-C", str(source), "ls-tree", "-d", "--name-only", "HEAD"])
    eligible = [name for name in names.splitlines() if name not in EXCLUDED]
    selected = sorted(eligible, key=lambda name: sha((seed + "\0" + name).encode()))[:count]
    tasks = []
    for index, name in enumerate(selected):
        raw = task_bytes(source, name, "task.toml")
        image = tomllib.loads(raw.decode())["environment"]["docker_image"]
        if not re.fullmatch(r"[a-zA-Z0-9_./-]+:[a-zA-Z0-9_.-]+", image):
            raise RuntimeError("Task image is not a registry tag")
        tasks.append({"name": name, "task_toml_sha256": sha(raw),
                      "image_tag": image,
                      "arm_order": ["kryn", "native"] if index % 2 == 0
                      else ["native", "kryn"]})
    manifest = {"schema": 1, "kind": "harbor_local_baseline", "seed": seed,
                "selection": "first SHA256(seed + NUL + task name), excluding prior exposed tasks",
                "eligible_count": len(eligible), "source_commit": TASKS_COMMIT,
                "harbor_commit": HARBOR_COMMIT, "model": "Qwen3.5-9B-6bit",
                "arms": ["kryn", "native"], "attempts_per_arm": 1,
                "max_agent_seconds": 900, "max_worker_seconds": MAX_WORKER_SECONDS,
                "min_free_bytes": MIN_FREE, "max_raw_bytes": MAX_RAW,
                "min_start_battery_percent": MIN_START_BATTERY,
                "stop_battery_percent": STOP_BATTERY,
                "product_source_sha256": {name: file_sha(ROOT / name)
                                          for name in PINNED_FILES},
                "product_plugin_sha256": plugin_hashes(),
                "tasks": tasks}
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    path = output / "manifest.json"
    atomic(path, manifest)
    (output / "manifest.sha256").write_text(sha(path.read_bytes()) + "\n")
    return path


def battery():
    value = call(["pmset", "-g", "batt"], timeout=10)
    match = re.search(r"(\d+)%", value)
    if not match:
        raise RuntimeError("Battery telemetry unavailable")
    return "AC Power" in value, int(match.group(1))


def bytes_under(path):
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except FileNotFoundError:
            continue
    return total


def room(campaign, *, starting):
    if shutil.disk_usage(campaign).free < MIN_FREE or bytes_under(campaign) > MAX_RAW:
        return "disk_or_raw_data_limit"
    plugged, percent = battery()
    if not plugged and percent < (MIN_START_BATTERY if starting else STOP_BATTERY):
        return "battery_below_campaign_limit"
    return None


def owned_resources(name):
    project = name + "__env"
    return {
        "containers": call(["docker", "ps", "-aq", "--filter",
                            "label=com.docker.compose.project=" + project], timeout=15),
        "networks": call(["docker", "network", "ls", "-q", "--filter",
                          "label=com.docker.compose.project=" + project], timeout=15),
        "volumes": call(["docker", "volume", "ls", "-q", "--filter",
                         "label=com.docker.compose.project=" + project], timeout=15),
    }


def settle_resources(name):
    owned = owned_resources(name)
    for kind, command in (("containers", ["docker", "rm", "-f"]),
                          ("networks", ["docker", "network", "rm"]),
                          ("volumes", ["docker", "volume", "rm"])):
        if owned[kind]:
            subprocess.run(command + owned[kind].splitlines(), check=True,
                           stdout=subprocess.DEVNULL, timeout=60)
    return not any(owned_resources(name).values())


def runtime_idle():
    sys.path.insert(0, str(ROOT / "tools"))
    import localai
    try:
        localai.runtime_identity()
        data = localai.runtime_metadata()
        return (data.get("healthy") is True and
                data.get("model") == "Qwen3.5-9B-6bit" and
                data.get("model_memory_max") == 22 * 1024**3 and
                data.get("active_requests") == 0 and
                data.get("waiting_requests") == 0)
    except (OSError, RuntimeError, ValueError):
        return False


def controlled_env():
    # Harbor itself needs the owner's Docker context; the OpenCode child uses
    # env -i and cannot inherit this process's account or provider credentials.
    allowed = {"HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "DOCKER_HOST",
               "DOCKER_CONFIG", "XDG_RUNTIME_DIR"}
    env = {key: value for key, value in os.environ.items() if key in allowed}
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_child(command, name, attempts, campaign, *, wall=MAX_WORKER_SECONDS):
    log = attempts / (name + ".stdout.log")
    marker = attempts / (name + ".running.json")
    if log.exists() or marker.exists():
        raise RuntimeError("Attempt already started: " + name)
    power_start = battery()
    with log.open("wb") as out:
        child = subprocess.Popen(command, stdout=out, stderr=subprocess.STDOUT,
                                 env=controlled_env(), start_new_session=True)
        atomic(marker, {"pid": child.pid, "command_sha256": sha("\0".join(command).encode()),
                        "started_unix": time.time()})
        started = time.monotonic()
        stop = None
        while child.poll() is None:
            if time.monotonic() - started > wall:
                stop = "outer_wall_limit"
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
    power_end = battery()
    return {"returncode": child.returncode, "stop_reason": stop,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "stdout_sha256": file_sha(log), "runner_exited": child.poll() is not None,
            "ac_power_start": power_start[0], "ac_power_end": power_end[0],
            "battery_percent_start": power_start[1],
            "battery_percent_end": power_end[1]}


def stop_orphan(marker, name, expected):
    """A crashed controller never replays an arm or leaves its worker running."""
    pid = json.loads(marker.read_text())["pid"]
    command = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    if command and name in command and expected in command:
        os.killpg(pid, signal.SIGTERM)
        time.sleep(2)
        if subprocess.run(["ps", "-p", str(pid)], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=10).returncode == 0:
            os.killpg(pid, signal.SIGKILL)


def prepare_task(source, task, work):
    name = task["name"]
    parent = work / "tasks"
    parent.mkdir(exist_ok=True)
    destination = parent / name
    receipt = parent / (name + ".prepared.json")
    if receipt.exists():
        pinned = json.loads(receipt.read_text())
        if not destination.is_dir() or not (destination / "task.toml").is_file():
            raise RuntimeError("Prepared task disappeared")
        if tree_sha(destination) != pinned["prepared_tree_sha256"]:
            raise RuntimeError("Prepared task source changed")
        return destination, pinned
    if destination.exists():
        raise RuntimeError("Partial task preparation requires manual audit")
    if sha(task_bytes(source, name, "task.toml")) != task["task_toml_sha256"]:
        raise RuntimeError("Frozen task TOML changed")
    # Pull and pin the image before any candidate generation. This may pause
    # the campaign on disk pressure; the image is never silently substituted.
    image = task["image_tag"]
    prior_ids = set(call(["docker", "image", "ls", "-a", "-q", "--no-trunc"], timeout=30).splitlines())
    if subprocess.run(["docker", "image", "inspect", image], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL, timeout=15).returncode:
        subprocess.run(["docker", "pull", "--platform", "linux/amd64", image],
                       check=True, stdout=subprocess.DEVNULL, timeout=900)
    details = json.loads(call(["docker", "image", "inspect", image], timeout=20))[0]
    if details.get("Architecture") != "amd64" or details.get("Os") != "linux":
        raise RuntimeError("Official task image is not linux/amd64")
    repository = image.rsplit(":", 1)[0]
    pinned = next((value for value in details.get("RepoDigests", [])
                   if value.startswith(repository + "@sha256:")), None)
    if pinned is None:
        raise RuntimeError("Docker did not expose an immutable image digest")
    archive = subprocess.check_output(["git", "-C", str(source), "archive",
                                       TASKS_COMMIT, name], timeout=60)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(parent, filter="data")
    toml_path = destination / "task.toml"
    original = toml_path.read_text()
    if original.count(image) != 1:
        raise RuntimeError("Cannot pin official task image unambiguously")
    toml_path.write_text(original.replace(image, pinned))
    prepared = {"source_commit": TASKS_COMMIT, "original_toml_sha256":
                task["task_toml_sha256"], "image_tag": image,
                "image_digest": pinned, "pinned_toml_sha256": sha(toml_path.read_bytes()),
                "source_tree_sha256": sha(archive),
                "image_id": details["Id"], "image_owned": details["Id"] not in prior_ids,
                "prepared_tree_sha256": tree_sha(destination)}
    atomic(receipt, prepared)
    return destination, prepared


def tree_sha(directory):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            digest.update(str(path.relative_to(directory)).encode() + b"\0L")
            digest.update(os.readlink(path).encode())
        elif path.is_file():
            digest.update(str(path.relative_to(directory)).encode() + b"\0F")
            digest.update(bytes.fromhex(file_sha(path)))
    return digest.hexdigest()


def release_owned_image(campaign, task):
    prepared = campaign / "tasks" / (task["name"] + ".prepared.json")
    receipt = campaign / "tasks" / (task["name"] + ".image-release.json")
    if not prepared.is_file() or receipt.exists():
        return
    info = json.loads(prepared.read_text())
    if info["image_owned"]:
        # Never use --force. Docker refuses removal if another workload adopted it.
        subprocess.run(["docker", "image", "rm", info["image_tag"]],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        subprocess.run(["docker", "image", "rm", info["image_digest"]],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    still_present = subprocess.run(["docker", "image", "inspect", info["image_id"]],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=15).returncode == 0
    atomic(receipt, {"image_owned": info["image_owned"],
                     "image_removed": info["image_owned"] and not still_present,
                     "preserved_preexisting_image": not info["image_owned"]})


def write_progress(campaign, manifest):
    attempts = sorted((campaign / "attempts").glob("*.final.json"))
    rows = [json.loads(path.read_text()) for path in attempts]
    summary = {"schema": 1, "manifest_sha256": sha((campaign / "manifest.json").read_bytes()),
               "planned_tasks": len(manifest["tasks"]),
               "planned_arms": 2 * len(manifest["tasks"]),
               "finished_arms": len(rows),
               "strict_kryn": sum(row.get("strict_accepted") is True
                                  for row in rows if row.get("arm") == "kryn"),
               "strict_native": sum(row.get("strict_accepted") is True
                                    for row in rows if row.get("arm") == "native"),
               "invalid_or_ungraded": sum(row.get("official_reward") is None for row in rows),
               "last_attempt": rows[-1]["name"] if rows else None,
               "updated_unix": time.time()}
    summary["paired"] = paired_summary(campaign, manifest, rows)
    atomic(campaign / "progress.json", summary)
    return summary


def main_wire(campaign, name):
    path = campaign / "trials" / name / "host-guard" / "inference.json"
    if not path.is_file():
        return None
    for row in json.loads(path.read_text()):
        if row.get("tool_count", 0) > 0:
            return {key: row.get(key) for key in
                    ("model", "max_tokens", "numeric", "thinking", "tool_count",
                     "tool_schema_sha256")}
    return None


def paired_summary(campaign, manifest, rows):
    by_name = {row["name"]: row for row in rows}
    paired = []
    for index, task in enumerate(manifest["tasks"], start=1):
        keys = {arm: f"h{index:02d}-{arm}" for arm in ("kryn", "native")}
        if any(name not in by_name for name in keys.values()):
            continue
        arms = {arm: by_name[name] for arm, name in keys.items()}
        wires = {arm: main_wire(campaign, name) for arm, name in keys.items()}
        powers = {arm: arms[arm].get("worker", {}) for arm in ("kryn", "native")}
        power_matched = (all(row.get("ac_power_start") == row.get("ac_power_end")
                             for row in powers.values()) and
                         powers["kryn"].get("ac_power_start") is not None and
                         powers["kryn"].get("ac_power_start") ==
                         powers["native"].get("ac_power_start"))
        comparable = bool(all(row["status"] == "graded" and
                              (row.get("local_only") or {}).get("generation_proven") is True
                              for row in arms.values()) and power_matched and wires["kryn"] and
                          wires["kryn"] == wires["native"])
        paired.append({"task": task["name"], "scoreable": comparable,
                       "kryn": arms["kryn"]["strict_accepted"],
                       "native": arms["native"]["strict_accepted"],
                       "power_matched": power_matched,
                       "wire_matched": bool(wires["kryn"] and wires["kryn"] == wires["native"])})
    scoreable = [row for row in paired if row["scoreable"]]
    counts = {"kryn_only": sum(row["kryn"] and not row["native"] for row in scoreable),
              "native_only": sum(row["native"] and not row["kryn"] for row in scoreable),
              "both": sum(row["kryn"] and row["native"] for row in scoreable),
              "neither": sum(not row["kryn"] and not row["native"] for row in scoreable)}
    deltas = [int(row["kryn"]) - int(row["native"]) for row in scoreable]
    interval = None
    if deltas:
        rng = random.Random(20261003)
        values = sorted(sum(rng.choice(deltas) for _ in deltas) / len(deltas)
                        for _ in range(10000))
        interval = [values[249], values[9749]]
    return {"completed_pairs": len(paired), "scoreable_pairs": len(scoreable),
            "attrition_pairs": len(paired) - len(scoreable), "win_loss_tie": counts,
            "strict_success_delta": sum(deltas) / len(deltas) if deltas else None,
            "bootstrap_95_percentile": interval, "bootstrap_resamples": 10000,
            "pairs": paired}


def gold_preflight(campaign, task_dir, index, harbor_python):
    name = f"gold-h{index:02d}"
    receipt = campaign / (name + ".final.json")
    if receipt.exists():
        return json.loads(receipt.read_text())["passed"]
    marker = campaign / "attempts" / (name + ".running.json")
    log = campaign / "attempts" / (name + ".stdout.log")
    if marker.exists() or log.exists():
        # Even the no-model oracle gets one attempt. An interrupted oracle
        # invalidates this task, rather than silently changing the roster.
        if marker.exists():
            stop_orphan(marker, name, "harbor trials start")
        result = {"passed": False, "reason": "oracle_interrupted",
                  "owned_resources_settled": settle_resources(name)}
    else:
        command = [str(harbor_python.parent / "harbor"), "trials", "start", "-p",
                   str(task_dir), "-a", "oracle", "--trial-name", name,
                   "--trials-dir", str(campaign / "oracle")]
        raw = run_child(command, name, campaign / "attempts", campaign, wall=1800)
        output = campaign / "oracle" / name / "result.json"
        grade = json.loads(output.read_text()) if output.is_file() else {}
        reward = (grade.get("verifier_result") or {}).get("rewards", {}).get("reward")
        result = {"passed": raw["returncode"] == 0 and raw["stop_reason"] is None
                  and reward == 1 and grade.get("exception_info") is None,
                  "reward": reward, "worker": raw,
                  "result_sha256": sha(output.read_bytes()) if output.is_file() else None,
                  "owned_resources_settled": settle_resources(name)}
    atomic(receipt, result)
    if not result.get("owned_resources_settled", True):
        raise RuntimeError("Oracle Docker resources failed to settle")
    return result["passed"]


def run_campaign(campaign, source, harbor_python, expected_sha):
    manifest_path = campaign / "manifest.json"
    if sha(manifest_path.read_bytes()) != expected_sha or \
            (campaign / "manifest.sha256").read_text().strip() != expected_sha:
        raise RuntimeError("Campaign manifest changed after preregistration")
    manifest = json.loads(manifest_path.read_text())
    if manifest["schema"] != 1 or manifest["kind"] != "harbor_local_baseline" or \
            manifest["source_commit"] != source_commit(source) or \
            manifest["harbor_commit"] != HARBOR_COMMIT or \
            source_commit(harbor_python.parent.parent.parent) != HARBOR_COMMIT or \
            manifest["product_source_sha256"] != {name: file_sha(ROOT / name)
                                                  for name in PINNED_FILES} or \
            manifest["product_plugin_sha256"] != plugin_hashes() or \
            len(manifest["tasks"]) * 2 > MAX_ATTEMPTS:
        raise RuntimeError("Campaign source, suite, or attempt ceiling changed")
    (campaign / "attempts").mkdir(exist_ok=True)
    lock = (campaign / ".runner.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for index, task in enumerate(manifest["tasks"], start=1):
        task_name = task["name"]
        task_dir = None
        oracle_passed = None
        setup_failed = campaign / "tasks" / (task_name + ".setup-failed.json")
        if setup_failed.is_file():
            oracle_passed = False
        for arm in task["arm_order"]:
            name = f"h{index:02d}-{arm}"
            final = campaign / "attempts" / (name + ".final.json")
            if final.exists():
                continue
            if (manifest["product_source_sha256"] !=
                    {item: file_sha(ROOT / item) for item in PINNED_FILES} or
                    manifest["product_plugin_sha256"] != plugin_hashes()):
                raise RuntimeError("Frozen worker or product payload changed between arms")
            while problem := room(campaign, starting=True):
                atomic(campaign / "pause.json", {"reason": problem, "next": name,
                                                  "updated_unix": time.time()})
                time.sleep(60)
            while not runtime_idle():
                atomic(campaign / "pause.json", {"reason": "owned_runtime_not_idle",
                                                  "next": name, "updated_unix": time.time()})
                time.sleep(60)
            if task_dir is None and oracle_passed is None:
                try:
                    task_dir, prep = prepare_task(source, task, campaign)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                        tarfile.TarError) as error:
                    atomic(setup_failed, {"error_type": type(error).__name__,
                                          "task": task_name, "before_generation": True})
                    oracle_passed = False
                if task_dir is not None:
                    while problem := room(campaign, starting=True):
                        atomic(campaign / "pause.json", {"reason": problem, "next": name,
                                                          "updated_unix": time.time()})
                        time.sleep(60)
                    oracle_passed = gold_preflight(campaign, task_dir, index, harbor_python)
            if task_dir is not None and tree_sha(task_dir) != prep["prepared_tree_sha256"]:
                raise RuntimeError("Task source changed between paired arms")
            while problem := room(campaign, starting=True):
                atomic(campaign / "pause.json", {"reason": problem, "next": name,
                                                  "updated_unix": time.time()})
                time.sleep(60)
            marker = campaign / "attempts" / (name + ".running.json")
            log = campaign / "attempts" / (name + ".stdout.log")
            if not marker.exists() and not log.exists() and any(owned_resources(name).values()):
                raise RuntimeError("Owned Harbor resources exist before attempt")
            if not oracle_passed:
                outcome = {"name": name, "arm": arm, "task": task_name,
                           "status": "oracle_failed", "strict_accepted": False,
                           "official_reward": None, "owned_resources_settled": True,
                           "runtime_idle_after": runtime_idle()}
            elif marker.exists() or log.exists():
                # Crash recovery never replays a possibly generated attempt.
                if marker.exists():
                    stop_orphan(marker, name, "run_harbor_calibration.py")
                settled = settle_resources(name)
                outcome = {"name": name, "arm": arm, "task": task_name,
                           "status": "interrupted_before_receipt", "strict_accepted": False,
                           "official_reward": None, "owned_resources_settled": settled,
                           "runtime_idle_after": runtime_idle()}
            else:
                command = [str(harbor_python), "-B", str(ROOT / "research/run_harbor_calibration.py"),
                           str(task_dir), str(campaign / "trials"), name, "--arm", arm]
                raw = run_child(command, name, campaign / "attempts", campaign)
                summary_file = campaign / "trials" / name / "host-guard" / "summary.json"
                summary = json.loads(summary_file.read_text()) if summary_file.is_file() else {}
                settled = settle_resources(name)
                outcome = {"name": name, "arm": arm, "task": task_name,
                           "status": "graded" if summary.get("reward") is not None else "ungraded",
                           "official_reward": summary.get("reward"),
                           "strict_accepted": summary.get("strict_accepted") is True and
                           raw["returncode"] == 0 and raw["stop_reason"] is None,
                           "worker": raw, "summary_sha256": sha(summary_file.read_bytes())
                           if summary else None,
                           "image_digest": prep["image_digest"],
                           "local_only": summary.get("local_only"),
                           "owned_resources_settled": settled,
                           "runtime_idle_after": runtime_idle()}
            atomic(final, outcome)
            write_progress(campaign, manifest)
            if not outcome["owned_resources_settled"] or not outcome["runtime_idle_after"]:
                raise RuntimeError("Trial failed to settle; campaign stopped safely")
        release_owned_image(campaign, task)
    report = write_progress(campaign, manifest)
    report["finished"] = report["finished_arms"] == report["planned_arms"]
    atomic(campaign / "final-report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze-harbor")
    freeze.add_argument("source", type=Path)
    freeze.add_argument("output", type=Path)
    freeze.add_argument("--count", type=int, default=12)
    freeze.add_argument("--seed", default="kryn-harbor-campaign-20261003-v1")
    freeze.add_argument("--harbor-python", type=Path,
                        default=Path("/private/tmp/kryn-harbor-fd1521/.venv/bin/python"))
    run = sub.add_parser("run")
    run.add_argument("campaign", type=Path)
    run.add_argument("source", type=Path)
    run.add_argument("--expected-sha256", required=True)
    run.add_argument("--harbor-python", type=Path,
                     default=Path("/private/tmp/kryn-harbor-fd1521/.venv/bin/python"))
    args = parser.parse_args()
    if args.command == "freeze-harbor":
        path = freeze_harbor(args.source.resolve(), args.output.resolve(), args.count,
                             args.seed, args.harbor_python.absolute())
        print(json.dumps({"manifest": str(path), "sha256": sha(path.read_bytes())}))
    else:
        print(json.dumps(run_campaign(args.campaign.resolve(), args.source.resolve(),
                                      args.harbor_python.absolute(), args.expected_sha256)))


if __name__ == "__main__":
    main()
