"""Durable power supervision around an unchanged frozen SWE-bench controller.

Run from a private, hash-pinned copy under a per-user launchd job. The supervisor
owns lifecycle only: interrupted work is retained and unscored, never replayed.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import uuid

MIN_WATTS = 120
START_BATTERY = 40
STOP_BATTERY = 25
MIN_FREE = 12 * 1024**3
MAX_RAW = 8 * 1024**3
MAX_WORK = 4 * 1024**3
POLL_SECONDS = 15
MEMORY_POLL_SECONDS = 2
MEMORY_COOLDOWN_SECONDS = 60
MUTABLE = {".runner.lock", "progress.json", "pause.json"}


class Waiting(RuntimeError):
    """An unchanged safety limit or temporary service outage prevents work."""


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def command(argv, timeout=30, **kwargs):
    return subprocess.check_output(argv, text=True, timeout=timeout, **kwargs).strip()


def docker(*args, timeout=30):
    try:
        return command(["docker", *args], timeout=timeout)
    except (OSError, subprocess.SubprocessError) as error:
        raise Waiting("docker_unavailable: " + str(error)) from error


def inventory(root, *, exclude=()):
    result = {}
    for path in sorted(root.rglob("*")):
        name = str(path.relative_to(root))
        if name in exclude:
            continue
        if path.is_symlink():
            result[name] = "symlink:" + os.readlink(path)
        elif path.is_file():
            result[name] = digest(path)
    return result


def checkpoint(campaign, state, *, seal=True):
    """Previously retained evidence may grow, but cannot disappear or change."""
    path = state / "evidence-lock.json"
    prior = read(path) if path.exists() else {}
    current = inventory(campaign, exclude=MUTABLE)
    changed = [name for name, sha in prior.items() if current.get(name) != sha]
    if changed:
        raise RuntimeError("Retained evidence changed: " + ", ".join(changed[:5]))
    if seal:
        save(path, current)
    return current


def event(state, kind, **values):
    row = dict(kind=kind, unix=time.time(), **values)
    with (state / "events.jsonl").open("a") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    save(state / "status.json", row)


def power():
    battery = command(["/usr/bin/pmset", "-g", "batt"], timeout=10)
    details = command(["/usr/sbin/system_profiler", "SPPowerDataType"], timeout=20)
    percent = re.search(r"(\d+)%", battery)
    watts = re.search(r"Wattage \(W\):\s*(\d+)", details)
    ac, on_battery = "AC Power" in battery, "Battery Power" in battery
    if not percent or ac == on_battery or not 0 <= int(percent[1]) <= 100:
        raise RuntimeError("battery_telemetry_unavailable")
    return {"ac": ac, "battery_percent": int(percent[1]),
            "adapter_watts": int(watts[1]) if watts else None}


def power_problem(value, starting, power_policy="ac-only"):
    if type(power_policy) is not str or power_policy not in {"ac-only", "battery-capable"}:
        raise ValueError("unknown_power_policy")
    if (not isinstance(value, dict) or type(value.get("ac")) is not bool
            or type(value.get("battery_percent")) is not int
            or not 0 <= value["battery_percent"] <= 100
            or (value.get("adapter_watts") is not None
                and (type(value["adapter_watts"]) is not int or value["adapter_watts"] < 0))):
        raise RuntimeError("battery_telemetry_unavailable")
    if power_policy == "ac-only" and not value["ac"]:
        return "battery_power"
    if power_policy == "ac-only" and (value["adapter_watts"] is None or value["adapter_watts"] < MIN_WATTS):
        return "adapter_below_120w"
    below_floor = value["battery_percent"] < START_BATTERY if starting else value["battery_percent"] <= STOP_BATTERY
    if below_floor:
        return "battery_below_resume_floor" if starting else "battery_stop_floor"
    return None


def memory_pressure():
    level = int(command(["/usr/sbin/sysctl", "-n", "kern.memorystatus_vm_pressure_level"], timeout=2))
    if level not in (1, 2, 4, 6):
        raise RuntimeError("memory_pressure_telemetry_unavailable")
    return level


def size(root):
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        except FileNotFoundError:
            pass
    return total


def safety(config, starting):
    try:
        value = power()
        problem = power_problem(value, starting)
        if starting:
            value["pressure_level"] = memory_pressure()
            if value["pressure_level"] != 1:
                problem = "host_memory_not_green"
        campaign, state, work = (Path(config[key]) for key in ("campaign", "state", "work"))
        if shutil.disk_usage(campaign).free < MIN_FREE or size(campaign) + size(state) > MAX_RAW:
            problem = "disk_or_raw_data_limit"
        if size(work) > MAX_WORK:
            problem = "candidate_workspace_byte_limit"
        return problem, value
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        return "safety_telemetry_unavailable", {"error": str(error)}


def controller_command(config):
    return [config["python"], "-B", str(Path(config["source"]) / "research/swebench_controller.py"),
            config["campaign"], config["work"], "--expected-sha256", config["manifest_sha256"]]


def live_commands():
    rows = command(["ps", "-axo", "pid=,command="]).splitlines()
    return {int(row.strip().split(None, 1)[0]): row.strip().split(None, 1)[1]
            for row in rows if len(row.strip().split(None, 1)) == 2}


def descendants(pid):
    rows = command(["ps", "-axo", "pid=,ppid=,command="]).splitlines()
    processes = {}
    for row in rows:
        parts = row.strip().split(None, 2)
        if len(parts) == 3:
            processes[int(parts[0])] = (int(parts[1]), parts[2])
    owned = {pid}
    while True:
        children = {child for child, (parent, _) in processes.items() if parent in owned}
        if children <= owned:
            break
        owned |= children
    return {child: processes[child][1] for child in owned if child != pid and child in processes}


def stop_pid(pid, expected, started_unix=None):
    """Signal only a process whose current argv contains the owned identity."""
    if not all(part in live_commands().get(pid, "") for part in expected):
        return
    if started_unix is not None:
        born = subprocess.run(["ps", "-p", str(pid), "-o", "lstart="], timeout=10,
                              capture_output=True, text=True).stdout.strip()
        if not born or abs(datetime.strptime(born, "%a %b %d %H:%M:%S %Y").timestamp() - started_unix) > 5:
            return
    children = descendants(pid)
    child_birth = {}
    for child in children:
        born = subprocess.run(["ps", "-p", str(child), "-o", "lstart="], timeout=10,
                              capture_output=True, text=True).stdout.strip()
        if born:
            child_birth[child] = datetime.strptime(born, "%a %b %d %H:%M:%S %Y").timestamp()
    for sig, seconds in ((signal.SIGINT, 90), (signal.SIGTERM, 15), (signal.SIGKILL, 15)):
        current = live_commands().get(pid, "")
        if not all(part in current for part in expected):
            break
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            break
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            current = live_commands().get(pid, "")
            if not all(part in current for part in expected):
                break
            time.sleep(1)
    if all(part in live_commands().get(pid, "") for part in expected):
        raise RuntimeError(f"Owned process did not stop: {pid}")
    for child, birth in child_birth.items():
        stop_pid(child, [children[child]], birth)


def settle(config):
    """Also works after a supervisor crash, without trusting a stale PID alone."""
    campaign = Path(config["campaign"])
    expected = [str(Path(config["source"]) / "research/swebench_controller.py"), str(campaign)]
    for pid, argv in live_commands().items():
        if all(part in argv for part in expected):
            stop_pid(pid, expected)
    # Popen occurs before the frozen running marker is atomically written.
    # Discover those crash-window workers by their exact evidence path too.
    for pid, argv in live_commands().items():
        if "research/run_external_patch.py" in argv and str(campaign / "evidence") + "/" in argv:
            stop_pid(pid, ["research/run_external_patch.py", str(campaign / "evidence") + "/"])
        elif "swebench.harness.run_evaluation" in argv:
            cwd = subprocess.run(["/usr/sbin/lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
                                 capture_output=True, text=True, timeout=15).stdout.splitlines()
            if "n" + str(campaign / "grade-root") in cwd:
                stop_pid(pid, [argv])
    for marker in list((campaign / "attempts").glob("*.running.json")) + list(
            (campaign / "grader").glob("*/running.json")):
        row = read(marker)
        name = marker.name.removesuffix(".running.json") if marker.parent.name == "attempts" else marker.parent.name
        if marker.parent.name == "attempts":
            expected = ["research/run_external_patch.py", str(campaign / "evidence" / name)]
        else:
            expected = ["swebench.harness.run_evaluation", "--run_id " + name]
        stop_pid(row["pid"], expected, row["started_unix"])
    # Only clean containers created during this supervisor's recorded launch,
    # with exact task/run identity and the prepared immutable image.
    containers = docker("ps", "-a", "--format", "{{.Names}}", timeout=15).splitlines()
    tasks = read(campaign / "manifest.json")["tasks"]
    owned = {"kryn-sweprep-" + hashlib.sha256(task["instance_id"].encode()).hexdigest()[:16] for task in tasks}
    for index, task in enumerate(tasks, 1):
        for run in (f"gold-s{index:02d}", f"s{index:02d}-kryn", f"s{index:02d}-native"):
            owned.add("sweb.eval." + task["instance_id"].lower() + "." + run)
    state = Path(config["state"])
    baseline = state / "containers-before.json"
    for name in containers:
        if name not in owned and not any(name.startswith(base + ".") and name[len(base) + 1:].isdigit() for base in owned):
            continue
        info = json.loads(docker("inspect", name))[0]
        if not baseline.exists() or info["Id"] in read(baseline):
            raise RuntimeError("Pre-existing benchmark container requires ownership audit: " + name)
        task = next(task for task in tasks if name == "kryn-sweprep-" + hashlib.sha256(
            task["instance_id"].encode()).hexdigest()[:16] or name.startswith("sweb.eval." + task["instance_id"].lower() + "."))
        prepared = campaign / "prepared" / task["instance_id"] / "receipt.json"
        prep_owned = name.startswith("kryn-sweprep-") and (
            info.get("Config", {}).get("Labels") or {}).get("kryn.swebench.prep") == task["instance_id"]
        if not prep_owned and (not prepared.exists() or info["Image"] != read(prepared)["image_id"]):
            raise RuntimeError("Benchmark container image ownership changed: " + name)
        event(state, "interrupted_container_cleanup", container_id=info["Id"], name=name, image=info["Image"])
        docker("rm", "-f", info["Id"], timeout=60)


def archive_inventory(archive):
    result = {}
    with tarfile.open(archive) as bundle:
        for member in bundle:
            if member.isdir():
                continue
            key = str(Path(member.name).relative_to("candidate"))
            if member.issym():
                result[key] = "symlink:" + member.linkname
            elif member.isfile() or member.islnk():
                value = hashlib.sha256()
                with bundle.extractfile(member) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        value.update(chunk)
                result[key] = value.hexdigest()
            else:
                raise RuntimeError("Unsupported interrupted candidate file type")
    return result


def archive_candidate(candidate, state, name, campaign):
    receipt = state / "interruptions" / (name + ".json")
    if receipt.exists():
        record = read(receipt)
        if record.get("complete"):
            if digest(record["archive"]) != record["sha256"]:
                raise RuntimeError("Interrupted archive changed: " + name)
            return
    else:
        if not candidate.exists():
            return
        receipt.parent.mkdir(exist_ok=True)
        record = {"archive": str(receipt.parent / (name + ".tar.gz")), "name": name,
                  "files": inventory(candidate), "complete": False}
        save(receipt, record)
    archive = Path(record["archive"])
    if archive.exists():
        try:
            complete = archive_inventory(archive) == record["files"]
        except (tarfile.TarError, EOFError, OSError):
            complete = False
        if complete:
            save(receipt, {**record, "complete": True, "sha256": digest(archive)})
            return
        if not candidate.exists() or inventory(candidate) != record["files"]:
            raise RuntimeError("Interrupted archive and source cannot be reconciled: " + name)
        # This is an incomplete packaging copy, never the raw candidate. Keep
        # its checksum/size and the exact source; avoid accumulating duplicates.
        event(state, "discard_incomplete_archive_copy", name=name,
              sha256=digest(archive), bytes=archive.stat().st_size)
        archive.unlink()
    if not candidate.exists():
        raise RuntimeError("Interrupted candidate missing before archival: " + name)
    needed = size(candidate)
    if (shutil.disk_usage(state).free < MIN_FREE + needed or
            size(campaign) + size(state) + needed > MAX_RAW):
        raise Waiting("Insufficient disk headroom to archive interrupted candidate")
    with tarfile.open(archive, "w:gz", dereference=False) as bundle:
        bundle.add(candidate, arcname="candidate")
    if archive_inventory(archive) != record["files"] or inventory(candidate) != record["files"]:
        raise RuntimeError("Interrupted candidate changed during archival: " + name)
    save(receipt, {**record, "complete": True, "sha256": digest(archive)})


def relocate(state, sources):
    """Journal exact same-volume renames so a crash between moves is resumable."""
    destination = state / "relocations" / uuid.uuid4().hex
    destination.mkdir(parents=True)
    entries = []
    for index, source in enumerate(sources):
        if source.stat().st_dev != destination.stat().st_dev:
            raise RuntimeError("Recovery relocation requires the same filesystem")
        entries.append({"source": str(source), "target": str(index), "directory": source.is_dir(),
                        "files": inventory(source) if source.is_dir() else {"": digest(source)}})
    save(destination / "receipt.json", {"complete": False, "entries": entries})
    finish_relocations(state)


def finish_relocations(state):
    for receipt in (state / "relocations").glob("*/receipt.json"):
        row = read(receipt)
        for item in row["entries"]:
            target, source = receipt.parent / item["target"], Path(item["source"])
            if not row["complete"] and not target.exists():
                if not source.exists():
                    raise RuntimeError("Recovery relocation lost both paths: " + str(source))
                os.rename(source, target)
            actual = inventory(target) if item["directory"] else {"": digest(target)}
            if actual != item["files"]:
                raise RuntimeError("Retained relocation changed: " + str(target))
        if not row["complete"]:
            save(receipt, {**row, "complete": True})


def recover(config):
    """Retain interrupted work; append explicit unscored oracle outcomes only."""
    campaign, state, work = (Path(config[key]) for key in ("campaign", "state", "work"))
    finish_relocations(state)
    partial_writes = [path for path in campaign.rglob("*.tmp") if path.is_file()]
    if partial_writes:
        relocate(state, partial_writes)
    for receipt in (state / "interruptions").glob("*.json"):
        item = read(receipt)
        if item.get("complete") and digest(item["archive"]) != item["sha256"]:
            raise RuntimeError("Retained candidate archive changed: " + str(receipt))
    manifest = read(campaign / "manifest.json")
    for index, task in enumerate(manifest["tasks"], 1):
        prefix = f"s{index:02d}"
        for arm in task["arm_order"]:
            name = prefix + "-" + arm
            final = campaign / "attempts" / (name + ".final.json")
            started = any((campaign / "attempts" / (name + suffix)).exists()
                          for suffix in (".running.json", ".stdout.log"))
            if started and not final.exists():
                archive_candidate(work / task["instance_id"] / "candidate", state, name, campaign)
        gold = campaign / "grader" / ("gold-" + prefix)
        gold_final = gold / "final.json"
        existing_gold = read(gold_final) if gold_final.exists() else {}
        interrupted_gold = existing_gold.get("reason") in ("supervisor_interrupted_gold", "resource_preflight") or (
            existing_gold.get("stop_reason") in ("resource_guard", "battery_below_campaign_limit", "disk_or_raw_data_limit"))
        if gold.exists() and (not gold_final.exists() or interrupted_gold):
            # A gold attempt is single-use too. Its incomplete raw evidence stays
            # intact. Retire the affected pair, not the rest of the campaign.
            result = existing_gold or {"graded": False, "resolved": None, "clean_grade": False,
                                       "reason": "supervisor_interrupted_gold", "supervisor_state": str(state)}
            if not gold_final.exists():
                save(gold_final, result)
            changed = False
            for arm in task["arm_order"]:
                name = prefix + "-" + arm
                final = campaign / "attempts" / (name + ".final.json")
                if not final.exists():
                    save(final, {"name": name, "arm": arm, "instance_id": task["instance_id"],
                                 "accepted": False, "status": "oracle_interrupted", "official": result})
                    changed = True
            if changed:
                event(state, "oracle_interrupted_unscored", task=prefix)
        prepared = campaign / "prepared" / task["instance_id"]
        task_work = work / task["instance_id"]
        if not (prepared / "receipt.json").exists() and (prepared.exists() or task_work.exists()):
            if gold.exists() or any((campaign / "attempts" / (prefix + "-" + arm + ".running.json")).exists()
                                   for arm in task["arm_order"]):
                raise RuntimeError("Preparation missing after execution started: " + prefix)
            relocate(state, [path for path in (prepared, task_work) if path.exists()])
            event(state, "preparation_preserved_before_retry", task=prefix)


def preflight(config, *, start_runtime=False):
    source, campaign = Path(config["source"]), Path(config["campaign"])
    if (digest(campaign / "manifest.json") != config["manifest_sha256"] or
            (campaign / "manifest.sha256").read_text().strip() != config["manifest_sha256"]):
        raise RuntimeError("Frozen manifest changed")
    if command(["git", "-C", str(source), "rev-parse", "HEAD"]) != config["source_commit"] or command(
            ["git", "-C", str(source), "status", "--porcelain"]):
        raise RuntimeError("Frozen source worktree changed")
    if digest(config["auditor"]) != config["auditor_sha256"]:
        raise RuntimeError("Predeclared independent auditor changed")
    for filename, expected in config.get("retained_sha256", {}).items():
        if digest(filename) != expected:
            raise RuntimeError("Retained checkpoint input changed: " + filename)
    script = """import json,sys,subprocess,urllib.error
from pathlib import Path
from research.swebench_controller import source_lock
c=Path(sys.argv[1])
source_lock(json.loads((c/'manifest.json').read_text()),c)
sys.path.insert(0, str(Path.cwd()/'tools'))
import localai
try:
    if sys.argv[2] == 'start':
        localai.ensure_runtime()
    localai.runtime_identity()
    data = localai.runtime_metadata()
    if (data.get('healthy') is not True or data.get('model') != 'Qwen3.5-9B-6bit'
            or data.get('model_memory_max') != 22 * 1024**3):
        raise RuntimeError('Frozen runtime model or ceiling changed')
    ready = data.get('active_requests') == 0 and data.get('waiting_requests') == 0
except subprocess.CalledProcessError as error:
    if error.returncode != 1 or error.cmd != ['/usr/sbin/lsof', '-nP', '-a', '-iTCP:8000', '-sTCP:LISTEN', '-Fpu']:
        raise
    ready = False
except (FileNotFoundError, ConnectionRefusedError, TimeoutError, urllib.error.URLError, subprocess.TimeoutExpired):
    ready = False
raise SystemExit(0 if ready else 75)
"""
    result = subprocess.run([config["python"], "-B", "-c", script, str(campaign),
                             "start" if start_runtime else "check"],
                            cwd=source, env={**os.environ, "PYTHONPATH": str(source)},
                            capture_output=True, text=True, timeout=120)
    if result.returncode not in (0, 75):
        raise RuntimeError("Frozen runtime/source preflight failed: " + result.stderr[-1500:])
    return result.returncode == 0


def monitor(child, config, stopping):
    awake = None
    reason = None
    next_safety = 0
    telemetry = {}
    observation = None
    observer = ThreadPoolExecutor(max_workers=1)
    try:
        awake = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-s", "-w", str(child.pid)],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while child.poll() is None:
            problem = None
            # Slow power/disk inspection must not block the pressure cadence.
            if observation is None and time.monotonic() >= next_safety:
                observation = observer.submit(safety, config, starting=False)
            if observation is not None and observation.done():
                problem, telemetry = observation.result()
                observation = None
                next_safety = time.monotonic() + POLL_SECONDS
            try:
                level = memory_pressure()
                memory = {"pressure_level": level}
                # Conservative outer admission also protects the next arm's
                # immediate preflight. The frozen worker guard is unchanged.
                if level != 1:
                    problem = "host_memory_guard"
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                memory = {"error": str(error)}
                problem = "memory_pressure_telemetry_unavailable"
            if stopping[0] or problem:
                reason = "supervisor_exit" if stopping[0] else problem
                if problem in ("host_memory_guard", "memory_pressure_telemetry_unavailable"):
                    save(Path(config["state"]) / "memory-cooldown.json",
                         {"until_unix": time.time() + MEMORY_COOLDOWN_SECONDS,
                          "reason": problem, "memory": memory})
                event(Path(config["state"]), "pausing", reason=reason, power=telemetry, memory=memory)
                stop_pid(child.pid, [str(Path(config["source"]) / "research/swebench_controller.py"), config["campaign"]])
                child.wait(timeout=15)
                break
            try:
                child.wait(timeout=MEMORY_POLL_SECONDS)
            except subprocess.TimeoutExpired:
                pass
    finally:
        if child.poll() is None:
            stop_pid(child.pid, [str(Path(config["source"]) / "research/swebench_controller.py"), config["campaign"]])
            child.wait(timeout=15)
        if awake is not None:
            if awake.poll() is None:
                awake.terminate()
            awake.wait(timeout=15)
        observer.shutdown(wait=True)
    return reason


def adjudicate(config):
    campaign, state = Path(config["campaign"]), Path(config["state"])
    final = read(campaign / "final-report.json")
    expected = len(read(campaign / "manifest.json")["tasks"]) * 2
    if not final.get("finished") or final.get("finished_arms") != expected:
        raise RuntimeError("Controller final report is incomplete")
    target = campaign / "independent-audit.json"
    if not target.exists():
        if (state / "audit-started.json").exists():
            raise RuntimeError("Independent auditor interrupted; inspect its log before replay")
        save(state / "audit-started.json", {"unix": time.time(), "sha256": config["auditor_sha256"]})
        with (state / "audit.log").open("xb") as output:
            subprocess.run([config["python"], "-B", config["auditor"]], check=True,
                           stdout=output, stderr=subprocess.STDOUT, timeout=120)
    result = read(target)
    if result.get("manifest_sha256") != config["manifest_sha256"] or result.get("planned_pairs") * 2 != expected:
        raise RuntimeError("Independent audit identity mismatch")
    event(state, "adjudicated", audit_sha256=digest(target), report_sha256=digest(campaign / "final-report.json"),
          scoreable_pairs=result["scoreable_pairs"], attrition_pairs=result["attrition_pairs"],
          release_qualified=False)


def supervise(config):
    state, campaign = Path(config["state"]), Path(config["campaign"])
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state / ".supervisor.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config_lock = state / "config-lock.json"
        if config_lock.exists() and read(config_lock) != config:
            raise RuntimeError("Supervisor configuration changed")
        save(config_lock, config)
        if (state / "status.json").exists() and read(state / "status.json")["kind"] in ("adjudicated", "needs_action"):
            return
        stopping = [False]
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: stopping.__setitem__(0, True))
        try:
            stable = 0
            last_wait = None
            while not stopping[0]:
                try:
                    settle(config)
                    checkpoint(campaign, state, seal=False)
                except Waiting as error:
                    stable = 0
                    if last_wait != str(error):
                        event(state, "waiting", reason=str(error))
                        last_wait = str(error)
                    time.sleep(POLL_SECONDS)
                    continue
                problem, telemetry = safety(config, starting=True)
                cooldown = state / "memory-cooldown.json"
                if cooldown.exists() and time.time() < read(cooldown)["until_unix"]:
                    problem = problem or "memory_guard_cooldown"
                if problem:
                    stable = 0
                    if last_wait != problem:
                        event(state, "waiting", reason=problem, power=telemetry)
                        last_wait = problem
                    time.sleep(POLL_SECONDS)
                    continue
                stable += 1
                if stable < 3:
                    if last_wait != "power_stabilizing":
                        event(state, "waiting", reason="power_stabilizing", power=telemetry)
                        last_wait = "power_stabilizing"
                    time.sleep(POLL_SECONDS)
                    continue
                if not preflight(config, start_runtime=True):
                    if last_wait != "runtime_not_idle":
                        event(state, "waiting", reason="runtime_not_idle")
                        last_wait = "runtime_not_idle"
                    time.sleep(POLL_SECONDS)
                    continue
                try:
                    recover(config)
                except Waiting as error:
                    if last_wait != str(error):
                        event(state, "waiting", reason=str(error))
                        last_wait = str(error)
                    time.sleep(POLL_SECONDS)
                    continue
                checkpoint(campaign, state)
                if (campaign / "final-report.json").exists():
                    adjudicate(config)
                    checkpoint(campaign, state)
                    return
                prior = sorted(p.name for p in (campaign / "attempts").glob("*.final.json"))
                run_id = uuid.uuid4().hex
                try:
                    before = docker("ps", "-aq", "--no-trunc").splitlines()
                except Waiting as error:
                    event(state, "waiting", reason=str(error))
                    stable = 0
                    time.sleep(POLL_SECONDS)
                    continue
                save(state / "containers-before.json", before)
                # Startup and recovery can take time; stale safe observations
                # cannot authorize a launch after power or memory has changed.
                problem, telemetry = safety(config, starting=True)
                if problem:
                    event(state, "waiting", reason=problem, power=telemetry)
                    stable, last_wait = 0, problem
                    time.sleep(POLL_SECONDS)
                    continue
                with (state / ("controller-" + run_id + ".log")).open("xb") as output:
                    child = subprocess.Popen(controller_command(config), cwd=config["source"],
                                             stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
                    try:
                        event(state, "running", pid=child.pid, run_id=run_id, power=telemetry)
                        reason = monitor(child, config, stopping)
                    finally:
                        if child.poll() is None:
                            stop_pid(child.pid, [str(Path(config["source"]) / "research/swebench_controller.py"), config["campaign"]])
                            child.wait(timeout=15)
                event(state, "controller_exited", returncode=child.returncode, reason=reason, run_id=run_id)
                after = sorted(p.name for p in (campaign / "attempts").glob("*.final.json"))
                retry = state / "exit-retry.json"
                previous = read(retry) if retry.exists() else {}
                count = previous.get("count", 0) + 1 if previous.get("finals") == after else 1
                save(retry, {"finals": after, "count": count if not reason and prior == after else 0})
                if not reason and prior == after and count >= 2 and not (campaign / "final-report.json").exists():
                    raise RuntimeError("Controller exited twice without progress; inspect controller-" + run_id + ".log")
                stable, last_wait = 0, None
            event(state, "waiting", reason="supervisor_exit")
        except Exception as error:
            event(state, "needs_action", error=str(error))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    config = read(args.config)
    if config["supervisor_sha256"] != digest(__file__):
        raise RuntimeError("Supervisor source changed")
    if args.check:
        print(json.dumps({"runtime_idle": preflight(config), "safety": safety(config, True)}))
    else:
        supervise(config)


if __name__ == "__main__":
    main()
