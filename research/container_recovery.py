"""Append-only settlement/export of an interrupted, never-replayed container arm.

The caller must first prove the generation/grader process has exited. Recovery
does not run an agent or grader and always leaves the interrupted arm unscored.
"""

import contextlib
import fcntl
import json
from pathlib import Path
import re
import shutil
import uuid

from research.campaign_supervisor import MAX_RAW, inventory, size
from research.container_admission import CONTROL_IMAGE
from research.container_export import MAX_WORKTREE_BYTES
from research.container_generation import export_source, frozen
from research.container_worker import ARCHIVE_LIMIT, DISK_FLOOR, DockerWorker, HostGuard, LABEL, SIDECAR_IMAGE, validate_worker
from research.local_campaign import atomic, file_sha
from research.run_external_patch import PATCH_BUDGET


def _read(path):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("Recovery requires a regular receipt: " + str(path))
    return json.loads(path.read_text())


def _seal(path, value):
    if path.exists():
        if _read(path) != value:
            raise RuntimeError("Recovery receipt changed: " + str(path))
    else:
        atomic(path, value)
    return value


@contextlib.contextmanager
def _session(directory, root, image):
    directory, root = Path(directory).absolute(), Path(root).absolute()
    if directory != directory.resolve() or root != root.resolve():
        raise RuntimeError("Linked recovery paths refused")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (root / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pins = {name: file_sha(directory / name) if (directory / name).is_file() else None
                for name in ("ownership.json", "driver.json", "result.json", "worktree.tar", "model.patch")}
        for name in pins:
            if (directory / name).is_symlink():
                raise RuntimeError("Linked original recovery evidence refused")
        _seal(root / "inputs.json", {"directory": str(directory), "image": image, "sha256": pins})
        journal = _read(directory / "ownership.json") if pins["ownership.json"] is not None else None
        attempt = root / ("attempt-" + uuid.uuid4().hex)
        attempt.mkdir(mode=0o700)
        docker = DockerWorker(attempt, None)
        yield docker, journal, attempt
        # Original success/failure/absence is immutable even after safe export.
        after = {name: file_sha(directory / name) if (directory / name).is_file() else None for name in pins}
        if after != pins:
            raise RuntimeError("Original arm evidence changed during recovery")


def _owned(docker, journal, image, root):
    """Validate the entire recorded set before issuing any stop/remove command."""
    owner = journal.get("owner", "")
    expected = journal.get("expected_names", {})
    if not re.fullmatch(r"kryn-worker-[0-9a-f]{16}", owner) or set(expected) != {"container", "network"}:
        raise RuntimeError("Invalid recorded Docker ownership")
    permitted = {"container": {owner + "-candidate", owner + "-relay", owner + "-grader", owner + "-route-control"}, "network": {owner}}
    observed = {"container": {}, "network": {}}
    for kind in observed:
        names = expected[kind]
        if not isinstance(names, dict) or not set(names) <= permitted[kind]:
            raise RuntimeError("Unrecognized reserved resource name")
        recorded = journal.get("containers" if kind == "container" else "networks")
        if not isinstance(recorded, list) or set(recorded) != {value for value in names.values() if value is not None}:
            raise RuntimeError("Recorded resource IDs disagree with reserved names")
        if any(not re.fullmatch(r"[0-9a-f]{64}", identity) for identity in recorded):
            raise RuntimeError("Recorded resource ID is not immutable")
        rows = docker.command(kind, "ls", *(["-a"] if kind == "container" else []), "--no-trunc",
                              "--format", "{{.ID}} {{.Names}}" if kind == "container" else "{{.ID}} {{.Name}}", cleanup=True)
        listed = dict(row.split(None, 1) for row in rows.splitlines() if row.strip())
        owned_ids = set(docker.command(kind, "ls", *(["-a"] if kind == "container" else []), "--no-trunc", "-q",
                                      "--filter", "label=" + LABEL + "=" + owner, cleanup=True).split())
        targets = owned_ids | (set(recorded) & set(listed)) | {identity for identity, name in listed.items() if name in names}
        for identity in targets:
            info = docker.inspect(kind, identity, cleanup=True)
            name = info["Name"].lstrip("/")
            labels = info["Config"].get("Labels") if kind == "container" else info.get("Labels")
            if info["Id"] != identity or not labels or labels.get(LABEL) != owner or name not in names:
                raise RuntimeError("Recorded resource ownership changed")
            prior = names[name]
            discovered = root / ("identity-" + name + ".json")
            if discovered.exists():
                prior = _read(discovered)["id"]
            if prior is not None and prior != identity:
                raise RuntimeError("Reserved resource identity changed")
            if kind == "container":
                if name.endswith("-candidate"):
                    validate_worker(info, image, owner)
                elif name.endswith("-grader"):
                    validate_worker(info, image, "none", grader=True)
                elif name.endswith("-route-control"):
                    if info["Config"].get("Image") != CONTROL_IMAGE:
                        raise RuntimeError("Recorded route-control image changed")
                elif info["Config"].get("Image") != SIDECAR_IMAGE:
                    raise RuntimeError("Recorded inference route image changed")
            elif info.get("Internal") is not True:
                raise RuntimeError("Recorded worker network isolation changed")
            observed[kind][identity] = info
        present_names = {info["Name"].lstrip("/") for info in observed[kind].values()}
        for name, identity in names.items():
            if identity is not None or name in present_names:
                continue
            discovered = root / ("identity-" + name + ".json")
            if not discovered.exists():
                # A daemon create may outlive the interrupted client RPC. An
                # empty listing cannot prove an unacknowledged create absent.
                raise RuntimeError("Interrupted create has no settled identity; ownership audit required")
            saved = _read(discovered)
            if saved.get("kind") != kind or not re.fullmatch(r"[0-9a-f]{64}", saved.get("id", "")):
                raise RuntimeError("Recovered resource identity receipt changed")
    for kind, items in observed.items():
        for identity, info in items.items():
            _seal(root / ("identity-" + info["Name"].lstrip("/") + ".json"), {"id": identity, "kind": kind})
    docker.owner = owner
    docker.containers = list(observed["container"])
    docker.networks = list(observed["network"])
    docker.expected = {kind: {info["Name"].lstrip("/"): identity for identity, info in items.items()}
                       for kind, items in observed.items()}
    return observed


def _stop(docker, observed):
    # Remove the inference route first; stopping is permitted during low power.
    for identity, info in sorted(observed["container"].items(), key=lambda item: not item[1]["Name"].endswith("-relay")):
        docker.settle(identity)


def _clear(docker, journal, image, root):
    observed = _owned(docker, journal, image, root)
    _stop(docker, observed)
    docker.close()
    if any(_owned(docker, journal, image, root).values()):
        raise RuntimeError("Recorded Docker resources remain after cleanup")


def settle_recorded(directory, expected_image, recovery_root):
    """Settle/remove a killed grader's exact recorded resources; never rerun it."""
    root = Path(recovery_root)
    with _session(directory, root, expected_image) as (docker, journal, _attempt):
        if journal is None:
            return _not_created(root)
        observed = _owned(docker, journal, expected_image, root)
        result = root / "result.json"
        if result.exists():
            if any(observed.values()):
                raise RuntimeError("Resources reappeared after completed recovery")
            return _read(result)
        _clear(docker, journal, expected_image, root)
        return _seal(result, {"recovery_complete": True, "cleanup_settled": True, "unscored": True,
                              "original_inputs_sha256": file_sha(root / "inputs.json")})


def _not_created(root):
    # DockerWorker durably reserves owner/name before every resource create.
    # The caller has already stopped the child; absent ownership proves that
    # this stage never reached a Docker create, not that it may be replayed.
    return _seal(root / "result.json", {"recovery_complete": True, "cleanup_settled": True,
        "worker_exported": False, "unscored": True, "reason": "ownership_never_created",
        "original_inputs_sha256": file_sha(root / "inputs.json")})


def _verified_export(root):
    path = root / "export.json"
    if not path.exists():
        return None
    receipt = _read(path)
    artifact = Path(receipt["directory"])
    if artifact.parent.parent != root or inventory(artifact) != receipt["files"]:
        raise RuntimeError("Retained recovery export changed")
    return receipt


def _original_handoff(campaign, arm, directory, root, journal):
    """Seal an already terminal handoff as unscored; do not import or regrade it."""
    path = directory / "driver.json"
    if not path.exists():
        return None
    driver = _read(path)
    if not all(driver.get(key) is True for key in
               ("worker_exported", "cleanup_settled", "inference_relay_settled")):
        return None
    if (driver.get("kind") != "swe_container_generation" or driver.get("arm") != arm
            or type(driver.get("completed")) is not bool
            or driver.get("manifest_sha256") != file_sha(campaign / "manifest.json")
            or journal.get("cleanup_errors") != [] or journal.get("retained_containers") != []
            or journal.get("retained_networks") != []
            or driver.get("patch_sha256") != file_sha(directory / "model.patch")
            or (driver.get("export") or {}).get("tar_sha256") != file_sha(directory / "worktree.tar")):
        raise RuntimeError("Original terminal handoff proof is incomplete or changed")
    _seal(root / "original-handoff.json", {"unscored": True,
        "sha256": {name: file_sha(directory / name) for name in
                   ("driver.json", "ownership.json", "worktree.tar", "model.patch")}})
    return _seal(root / "result.json", {"recovery_complete": True, "cleanup_settled": True,
        "worker_exported": True, "unscored": True, "reason": "original_terminal_handoff",
        "original_handoff_sha256": file_sha(root / "original-handoff.json"),
        "original_inputs_sha256": file_sha(root / "inputs.json")})


def recover(campaign, arm, *, admit=None):
    """Stop an interrupted arm, then export/clean it when safe. Always unscored.

    A waiting result retains the stopped worker; call again after safe admission.
    Original arm receipts are never changed or upgraded. No model/grader runs.
    Optional admit() runs after owned resources stop and before fresh HostGuard
    admission; it may wait for the controller's durable cooldown/green samples.
    """
    campaign = Path(campaign).absolute()
    manifest = frozen(campaign)
    if arm not in manifest["arm_order"]:
        raise ValueError("Unknown recovery arm")
    directory, root = campaign / arm, campaign / arm / "recovery"
    with _session(directory, root, manifest["image"]) as (docker, journal, attempt):
        if journal is None:
            return _not_created(root)
        observed = _owned(docker, journal, manifest["image"], root)
        result = root / "result.json"
        exported = _verified_export(root)
        candidate_name = journal["owner"] + "-candidate"
        if candidate_name not in journal["expected_names"]["container"]:
            if result.exists() and any(observed.values()):
                raise RuntimeError("Resources reappeared after completed recovery")
            _clear(docker, journal, manifest["image"], root)
            return _seal(result, {"recovery_complete": True, "cleanup_settled": True,
                "worker_exported": False, "unscored": True, "reason": "worker_never_created",
                "original_inputs_sha256": file_sha(root / "inputs.json")})
        if exported is None and not any(observed.values()):
            handoff = _original_handoff(campaign, arm, directory, root, journal)
            if handoff is not None:
                return handoff
        if result.exists():
            if any(observed.values()) or exported is None:
                raise RuntimeError("Completed recovery lost its export or resource absence")
            return _read(result)
        _stop(docker, observed)
        candidates = [identity for identity, info in observed["container"].items() if info["Name"].endswith("-candidate")]
        if exported is None:
            if len(candidates) != 1:
                raise RuntimeError("Interrupted worker absent before a verified recovery export")
            if admit is not None and admit() is False:
                return _seal(attempt / "waiting.json", {"waiting": True, "unscored": True,
                    "reason": "controller_admission_wait", "retained_worker": candidates[0]})
            # Recovery attempts share the arm's raw-data cap. Reserve the bounded
            # archive/import plus trusted Git data before allocating another copy.
            needed = ARCHIVE_LIMIT + MAX_WORKTREE_BYTES + 2 * size(Path(manifest["baseline"]) / ".git") + 4 * PATCH_BUDGET
            if size(directory) + needed > MAX_RAW or shutil.disk_usage(root).free < DISK_FLOOR + needed:
                return _seal(attempt / "waiting.json", {"waiting": True, "unscored": True,
                    "reason": "insufficient_recovery_export_headroom", "retained_worker": candidates[0]})
            guard_directory = attempt / "guard"
            guard_directory.mkdir(mode=0o700)
            guard = HostGuard(guard_directory, power_policy=manifest.get("power_policy", "ac-only"))
            try:
                guard.__enter__()
            except Exception as error:
                return _seal(attempt / "waiting.json", {"waiting": True, "unscored": True,
                    "reason": str(error), "retained_worker": candidates[0]})
            try:
                docker.guard = guard
                artifact = attempt / "export"
                artifact.mkdir(mode=0o700)
                # Reuse only a successfully exported archive; partial copies and
                # failed import/patch attempts remain preserved in their folders.
                archives = sorted(root.glob("attempt-*/archive.json"))
                if archives:
                    saved = _read(archives[0])
                    source = Path(saved["path"])
                    if source.parent.parent.parent != root or file_sha(source) != saved["sha256"]:
                        raise RuntimeError("Recovery archive changed")
                    docker.export = lambda _identity, destination: shutil.copyfile(source, destination)
                else:
                    original_export = docker.export
                    def capture(identity, destination):
                        value = original_export(identity, destination)
                        _seal(attempt / "archive.json", {"path": str(destination), "sha256": file_sha(destination)})
                        return value
                    docker.export = capture
                data = export_source(docker, candidates[0], Path(manifest["baseline"]), manifest, artifact, guard)
                guard.check()
            except Exception as error:
                if guard.reason or guard.memory.cancel.is_set():
                    return _seal(attempt / "waiting.json", {"waiting": True, "unscored": True,
                        "reason": str(error), "retained_worker": candidates[0]})
                raise
            finally:
                guard.__exit__(None, None, None)
            # Preserve partial exports, but never seal one after a final guard failure.
            try:
                guard.check()
            except Exception as error:
                return _seal(attempt / "waiting.json", {"waiting": True, "unscored": True,
                    "reason": str(error), "retained_worker": candidates[0]})
            exported = _seal(root / "export.json", {"directory": str(artifact), "files": inventory(artifact),
                                                     "evidence": data, "unscored": True})
        _clear(docker, journal, manifest["image"], root)
        return _seal(result, {"recovery_complete": True, "cleanup_settled": True, "unscored": True,
                              "export_sha256": file_sha(root / "export.json"),
                              "original_inputs_sha256": file_sha(root / "inputs.json")})
