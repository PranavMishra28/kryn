"""Owned, guarded Docker plumbing for prospective SWE development screens.

This is not a model loop or a replacement for Harbor. OpenCode owns agent work;
the caller supplies an already pinned, offline-ready image and inference port.
No host directory or Docker socket is mounted in either container.
"""

import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import threading
import time
import uuid

from research.campaign_supervisor import memory_pressure, power, power_problem
from research.local_campaign import atomic
from research.run_external_patch import bounded_output
from tools.run_native_trial import NativeResourceGuard

LABEL = "kryn.container-worker.owner"
SIDECAR_IMAGE = "alpine/socat@sha256:3d9e7966201dd3a065df591020a09fd3c70845de7e7086e3531ea69db774406b"
DISK_FLOOR = 12 * 1024**3
ARCHIVE_LIMIT = 512 * 1024**2


def pinned_image(value):
    if not re.fullmatch(r"(?:[a-zA-Z0-9._/:-]+@)?sha256:[0-9a-f]{64}", value):
        raise ValueError("Worker images must be pinned by digest or local image ID")
    return value


def validate_worker(info, image_id, network, *, grader=False):
    if grader and network != "none":
        raise RuntimeError("Official grading must have no network")
    host, config = info["HostConfig"], info["Config"]
    if grader and not {"PIP_NO_INDEX=1", "PIP_FIND_LINKS=/opt/kryn-wheels"}.issubset(config.get("Env") or []):
        raise RuntimeError("Official grader offline dependency route drifted")
    if (info["Image"] != image_id or info.get("Mounts") or host.get("Binds")
            or config.get("User") != ("root" if grader else "10001:10001") or host.get("Privileged")
            or host.get("CapAdd") or host.get("CapDrop") != ["ALL"]
            or host.get("Devices") or host.get("DeviceRequests")
            or host.get("DeviceCgroupRules") or host.get("UTSMode")
            or host.get("PidMode") or host.get("IpcMode") != "private"
            or host.get("PortBindings") or host.get("ExtraHosts")
            or host.get("Dns") != ["127.0.0.1"]
            or set(host.get("SecurityOpt") or []) != {"no-new-privileges"}
            or host.get("Memory") != 2 * 1024**3
            or host.get("MemorySwap") != 2 * 1024**3
            or host.get("NanoCpus") != 2 * 10**9
            or host.get("PidsLimit") != 256
            or host.get("NetworkMode") not in {network, info["NetworkSettings"]["Networks"].get(network, {}).get("NetworkID")}
            or set(info["NetworkSettings"]["Networks"]) != {network}):
        raise RuntimeError("Worker isolation or resource controls drifted")


class HostGuard:
    """Existing memory guard plus independent pressure/power/disk admission."""

    def __init__(self, evidence):
        self.evidence = Path(evidence)
        self.samples = []
        self.memory = NativeResourceGuard(self.evidence, self.samples)
        self.stop = threading.Event()
        self.reason = None
        self.threads = []
        self.awake = None

    def check(self):
        if self.reason or self.memory.cancel.is_set():
            raise RuntimeError(self.reason or self.memory.guard.reason or "resource_guard")

    def _watch(self, probe, interval):
        while not self.stop.is_set():
            try:
                issue = probe()
            except Exception as error:
                issue = "guard_telemetry: " + str(error)
            if issue:
                self.reason = issue
                return
            self.stop.wait(interval)

    def __enter__(self):
        try:
            issue = power_problem(power(), True)
            if issue or memory_pressure() != 1 or shutil.disk_usage(self.evidence).free < DISK_FLOOR:
                raise RuntimeError(issue or "host_memory_or_disk_admission")
            self.memory.start()
            self.awake = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())])
            def slow():
                return (power_problem(power(), False) or
                        ("disk_floor" if shutil.disk_usage(self.evidence).free < DISK_FLOOR else None))
            for probe, interval in ((lambda: "host_memory_pressure" if memory_pressure() != 1 else None, .5),
                                    (slow, 2)):
                thread = threading.Thread(target=self._watch, args=(probe, interval), daemon=True)
                self.threads.append(thread)
                thread.start()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        self.stop.set()
        for thread in self.threads:
            thread.join(timeout=25)
        try:
            self.memory.close()
        finally:
            if self.awake:
                self.awake.terminate()
                self.awake.wait(timeout=5)


class DockerWorker:
    """Own resources by both immutable ID and a random owner label; never adopt."""

    def __init__(self, evidence, guard):
        self.evidence = Path(evidence)
        self.guard = guard
        self.owner = "kryn-worker-" + uuid.uuid4().hex[:16]
        self.containers = []
        self.networks = []
        self.expected = {"container": {}, "network": {}}
        self.sequence = 0
        self.cleanup_errors = []
        self.last_usage_check = 0
        self.last_command = None
        self.retained = []

    def save(self):
        atomic(self.evidence / "ownership.json", {
            "owner": self.owner, "containers": self.containers,
            "networks": self.networks, "expected_names": self.expected,
            "retained_containers": self.retained,
            "retained_networks": self.networks if self.retained else [],
            "cleanup_errors": self.cleanup_errors})

    def command(self, *args, timeout=60, cleanup=False, stdin=None):
        if not cleanup:
            self.guard.check()
        if stdin is not None and len(stdin) > 4096:
            raise ValueError("Controller stdin exceeds its bounded control-message limit")
        self.sequence += 1
        log = self.evidence / f"docker-{self.sequence:03d}.log"
        # All command arguments here are supplied by the controller, not model output.
        stderr = log.with_suffix(".stderr")
        with log.open("xb") as output, stderr.open("xb") as errors, selectors.DefaultSelector() as selector:
            child = subprocess.Popen(["docker", *args], stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                selector.register(child.stdout, selectors.EVENT_READ, output)
                selector.register(child.stderr, selectors.EVENT_READ, errors)
                if stdin is not None:
                    child.stdin.write(stdin)
                    child.stdin.close()
                deadline = time.monotonic() + timeout
                size = 0
                while selector.get_map() or child.poll() is None:
                    if not cleanup:
                        self.guard.check()
                        if time.monotonic() - self.last_usage_check >= 5:
                            self.check_usage()
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Docker command deadline exceeded")
                    for key, _ in selector.select(.1):
                        data = os.read(key.fileobj.fileno(), min(64 * 1024, 8 * 1024**2 - size + 1))
                        if not data:
                            selector.unregister(key.fileobj)
                            continue
                        size += len(data)
                        if size > 8 * 1024**2:
                            raise RuntimeError("Docker command output exceeded admission budget")
                        key.data.write(data)
                errors.flush()
                if child.returncode:
                    raise RuntimeError(f"Docker exit {child.returncode}: {stderr.read_text(errors='replace')[-1200:]}")
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
                child.stdout.close()
                child.stderr.close()
                self.last_command = {"returncode": child.returncode, "stdout": str(log), "stderr": str(stderr)}
                atomic(log.with_suffix(".result.json"), self.last_command)
        return log.read_text()

    def check_usage(self):
        self.last_usage_check = time.monotonic()
        raw_bytes = sum(p.stat().st_size for p in self.evidence.rglob("*") if p.is_file() and not p.is_symlink())
        if raw_bytes > 8 * 1024**3:
            raise RuntimeError("Raw evidence exceeds 8 GiB cap")
        for identity in self.containers:
            value = subprocess.run(["docker", "container", "inspect", "--size", identity],
                                   capture_output=True, text=True, timeout=5, check=True)
            info = json.loads(value.stdout)[0]
            if (info["Config"]["Labels"].get(LABEL) != self.owner
                    or type(info.get("SizeRw")) is not int or info["SizeRw"] > 4 * 1024**3):
                raise RuntimeError("Owned container identity or 4 GiB work cap failed")

    def inspect(self, kind, identity, *, cleanup=False):
        return json.loads(self.command(kind, "inspect", identity, cleanup=cleanup))[0]

    def network(self):
        self.expected["network"][self.owner] = None
        self.save()
        identity = self.command("network", "create", "--internal", "--label", LABEL + "=" + self.owner,
                                self.owner).strip()
        if not re.fullmatch(r"[0-9a-f]{64}", identity):
            raise RuntimeError("Docker network identity is not a full ID")
        self.networks.append(identity)
        self.expected["network"][self.owner] = identity
        self.save()
        return identity

    def create(self, label, image, arguments, *, network="none", worker=False, grader=False):
        if grader and (worker or network != "none"):
            raise ValueError("Grader must be separate from the worker and have no network")
        pinned_image(image)
        name = self.owner + "-" + label
        self.expected["container"][name] = None
        self.save()
        flags = ["--label", LABEL + "=" + self.owner, "--name", name,
                 "--network", network, "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                 "--memory", "2g" if worker or grader else "64m", "--memory-swap", "2g" if worker or grader else "64m",
                 "--cpus", "2" if worker or grader else "1", "--pids-limit", "256" if worker or grader else "64"]
        if worker or grader:
            flags += ["--platform", "linux/amd64", "--user", "root" if grader else "10001:10001",
                      "--dns", "127.0.0.1", "--ipc", "private"]
            if grader:
                flags += ["--env", "PIP_NO_INDEX=1", "--env", "PIP_FIND_LINKS=/opt/kryn-wheels"]
        else:
            flags += ["--read-only"]
        identity = self.command("create", *flags, image, *arguments).strip()
        if not re.fullmatch(r"[0-9a-f]{64}", identity):
            raise RuntimeError("Docker container identity is not a full ID")
        self.containers.append(identity)
        self.expected["container"][name] = identity
        self.save()
        self.command("start", identity)
        return identity

    def route(self, port):
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("Invalid bounded loopback endpoint")
        network = self.network()
        sidecar = self.create("relay", SIDECAR_IMAGE,
                              ["TCP-LISTEN:18766,reuseaddr,fork", "TCP:host.docker.internal:" + str(port)],
                              network="bridge")
        self.command("network", "connect", network, sidecar)
        info = self.inspect("container", sidecar)
        return network, sidecar, info["NetworkSettings"]["Networks"][self.owner]["IPAddress"]

    def settle(self, identity):
        info = self.inspect("container", identity, cleanup=True)
        if identity not in self.containers or info["Config"]["Labels"].get(LABEL) != self.owner:
            raise RuntimeError("Container ownership changed")
        self.command("stop", "--timeout", "2", identity, cleanup=True)
        info = self.inspect("container", identity, cleanup=True)
        if info["State"]["Running"] or info["State"]["Pid"]:
            raise RuntimeError("Container did not settle")

    def export(self, identity, destination):
        info = self.inspect("container", identity)
        if (identity not in self.containers or info["Config"]["Labels"].get(LABEL) != self.owner
                or info["State"]["Running"] or info["State"]["Pid"]):
            raise RuntimeError("Export requires an owned, stopped container")
        return bounded_output(["docker", "cp", identity + ":/testbed/.", "-"],
                              Path(destination), ARCHIVE_LIMIT, env=os.environ.copy(),
                              cwd=self.evidence, cancelled=lambda: bool(self.guard.reason or self.guard.memory.cancel.is_set()),
                              timeout=120)

    def close(self, *, retain=()):
        if any(identity not in self.containers for identity in retain):
            raise RuntimeError("Can retain only an owned, stopped worker for later safe export")
        self.retained = list(retain)
        for identity in retain:
            try:
                info = self.inspect("container", identity, cleanup=True)
                if info["Config"]["Labels"].get(LABEL) != self.owner:
                    raise RuntimeError("Retained worker ownership changed")
                if info["State"]["Running"] or info["State"]["Pid"]:
                    self.settle(identity)
                    raise RuntimeError("Retained worker was not already owned, stopped")
            except Exception as error:
                # Preserve the exact candidate identity, but continue settling
                # other owned resources. Uncertain retention cannot pass cleanup.
                self.cleanup_errors.append(str(error))
        for kind, identities in (("container", self.containers), ("network", self.networks)):
            # A cancelled create can succeed on the daemon before the CLI yields
            # an ID. Names were durably reserved first, so reconcile the exact
            # random owner and name before removing anything.
            if self.expected[kind]:
                try:
                    found = self.command(kind, "ls", *(["-a"] if kind == "container" else []),
                                         "--no-trunc", "-q", "--filter", "label=" + LABEL + "=" + self.owner,
                                         cleanup=True).split()
                    observed = set()
                    for identity in found:
                        info = self.inspect(kind, identity, cleanup=True)
                        name = info["Name"].lstrip("/")
                        labels = info["Config"]["Labels"] if kind == "container" else info["Labels"]
                        if labels.get(LABEL) != self.owner or name not in self.expected[kind]:
                            raise RuntimeError("Discovered resource does not match reserved owner/name")
                        prior = self.expected[kind][name]
                        if prior is not None and prior != identity:
                            raise RuntimeError("Reserved resource identity changed")
                        observed.add(name)
                        self.expected[kind][name] = identity
                        if identity not in identities:
                            identities.append(identity)
                    if any(identity is None and name not in observed for name, identity in self.expected[kind].items()):
                        raise RuntimeError("Interrupted create has no settled identity; ownership audit required")
                except Exception as error:
                    self.cleanup_errors.append(str(error))
            for identity in reversed(identities):
                if kind == "container" and identity in self.retained:
                    continue
                if kind == "network" and self.retained:
                    continue
                try:
                    info = self.inspect(kind, identity, cleanup=True)
                    labels = info["Config"]["Labels"] if kind == "container" else info["Labels"]
                    if labels.get(LABEL) != self.owner:
                        raise RuntimeError("Resource ownership changed")
                    self.command(kind, "rm", *(["-f"] if kind == "container" else []), identity, cleanup=True)
                except Exception as error:
                    self.cleanup_errors.append(str(error))
        self.save()
        if self.cleanup_errors:
            raise RuntimeError("Owned Docker cleanup failed: " + "; ".join(self.cleanup_errors))
