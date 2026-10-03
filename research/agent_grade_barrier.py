#!/usr/bin/env python3
"""Research-only volume barrier between a native Agent turn and trusted grading.

This does not qualify a protected roster or prove that every Agent descendant
exited. The caller owns task admission and supplies the trusted grader.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from types import SimpleNamespace

from run_external_patch import (CaptureCancelled, MODEL_ID, NativeResourceGuard,
                                benchmark_tools, collect_patch, configuration,
                                git_config_sha256, isolated_git, quiet_command, run,
                                runtime_is_idle, summarize_resources)

GIT = Path("/Library/Developer/CommandLineTools/usr/bin/git")


class BarrierError(RuntimeError):
    """A candidate artifact cannot safely advance to the next phase."""


@dataclass(frozen=True)
class Volume:
    image: Path
    mount: Path
    device: int


def command(argv, *, timeout=30):
    result = subprocess.run(argv, capture_output=True, timeout=timeout, close_fds=True)
    if result.returncode:
        raise BarrierError(f"{argv[0]} {argv[1]} failed: {result.stderr[:300]!r}")
    return result.stdout


def image_entry(image):
    listing = plistlib.loads(command(["hdiutil", "info", "-plist"], timeout=10))
    found = [entry for entry in listing.get("images", [])
             if entry.get("image-path") == str(image)]
    if len(found) > 1:
        raise BarrierError("Disk image appears more than once in hdiutil inventory")
    return found[0] if found else None


def attached_mount(entry):
    return [entity.get("mount-point") for entity in entry.get("system-entities", [])
            if entity.get("mount-point")]


def attach(image, root, *, readonly=False):
    if image_entry(image) is not None:
        raise BarrierError("Disk image was already attached")
    directory = Path(tempfile.mkdtemp(prefix="kryn-mount-", dir=root))
    mount = directory / "mount"
    mount.mkdir(mode=0o700)
    argv = ["hdiutil", "attach", "-nobrowse", "-noverify"]
    if readonly:
        argv.append("-readonly")
    argv += ["-mountpoint", str(mount), str(image)]
    try:
        command(argv)
        entry = image_entry(image)
        if (entry is None or attached_mount(entry) != [str(mount)] or
                mount.stat().st_dev == root.stat().st_dev):
            raise BarrierError("Disk image did not attach at its unique mount point")
        if readonly and (entry.get("writeable") is not False or
                         not (os.statvfs(mount).f_flag & os.ST_RDONLY)):
            raise BarrierError("Capture disk image is not read-only")
        return Volume(image, mount, mount.stat().st_dev)
    except BaseException:
        if image_entry(image) is not None:
            try:
                command(["hdiutil", "detach", str(mount)])
            except BaseException:
                pass  # Preserve the mounted image and original failure for inspection.
        raise


def create_volume(root, name, size="512m"):
    image = root / (name + ".sparseimage")
    if image.exists():
        raise BarrierError("Refusing to reuse a trial disk image")
    command(["hdiutil", "create", "-size", size, "-type", "SPARSE", "-fs", "APFS",
             "-volname", "KRYN" + name.title(), str(image)])
    return attach(image, root)


def detach(volume):
    entry = image_entry(volume.image)
    if entry is None or attached_mount(entry) != [str(volume.mount)]:
        raise BarrierError("Expected disk image mount is missing or changed")
    if volume.mount.stat().st_dev != volume.device:
        raise BarrierError("Disk image device changed before detachment")
    command(["hdiutil", "detach", str(volume.mount)])  # Never use -force.
    if (image_entry(volume.image) is not None or
            volume.mount.stat().st_dev != volume.mount.parent.stat().st_dev):
        raise BarrierError("Disk image detachment could not be proved")


def do_then_detach(volume, report, key, operation):
    original = None
    value = None
    try:
        value = operation()
    except BaseException as error:
        original = error
    try:
        detach(volume)
        report[key] = True
    except BaseException as error:
        report[key] = False
        if original is not None:
            error.add_note("Earlier phase failure: " + repr(original))
        raise
    if original is not None:
        raise original
    return value


def clean_clone(seed, workspace, base_commit):
    command([str(GIT), "clone", "--no-hardlinks", "-q", str(seed), str(workspace)])
    head = command([str(GIT), "-C", str(workspace), "rev-parse", "HEAD"]).decode().strip()
    if head != base_commit:
        raise BarrierError("Frozen seed changed between trial phases")
    command([str(GIT), "-C", str(workspace), "remote", "remove", "origin"])


def capture_readonly(volume, root, base_commit, agent, evidence, arm, tool_venv,
                     cancelled):
    old_mount = Path(agent["workspace"]).parent
    if volume.mount == old_mount or volume.mount.is_relative_to(old_mount):
        raise BarrierError("Read-only capture reused the Agent workspace path")
    workspace = volume.mount / "workspace"
    if git_config_sha256(workspace) != agent["initial_git_config_sha256"]:
        raise BarrierError("Candidate Git config changed before frozen patch capture")
    tool_path, tool_dependencies, tool_manifest = benchmark_tools(tool_venv)
    if tool_manifest != agent["benchmark_tool_manifest"]:
        raise BarrierError("Pinned benchmark tools changed during the Agent turn")
    _, _, dependencies = configuration(workspace, workspace / ".git", arm,
                                       "http://127.0.0.1:19876/v1")
    if cancelled():
        raise CaptureCancelled("Resource guard interrupted read-only patch capture")
    with tempfile.TemporaryDirectory(prefix="kryn-capture-private-", dir=root) as temporary:
        _, names, size, digest = collect_patch(
            workspace, base_commit, evidence, private=Path(temporary),
            dependencies=dependencies + tool_dependencies,
            git_binary=tool_path / "git", tool_path=tool_path,
            cancelled=cancelled, readonly_workspace=True)
    return {"patch_sha256": digest, "patch_size_bytes": size,
            "untracked_files_included_in_patch": names}


def apply_patch(workspace, private, patch):
    with tempfile.TemporaryDirectory(prefix="kryn-grade-git-", dir=private) as temporary:
        temporary = Path(temporary)
        source = temporary / "model.patch"
        shutil.copyfile(patch, source)
        git_command, env = isolated_git(workspace, temporary, [], GIT, None)
        for operation in ("--check", ""):
            argv = git_command + ["apply"] + ([operation] if operation else []) + [str(source)]
            quiet_command(argv, env=env, cwd=workspace, cancelled=lambda: False)


def run_candidate_to_grader(*, seed, prompt, task_id, arm, tool_venv, receipt,
                            hidden_paths, grade, timeout=900):
    """Run an admitted task; grade is a trusted callback(workspace, private, evidence).

    This function deliberately emits no protected pass/fail verdict. A study
    runner must first verify the frozen roster, oracle, and no-model controls.
    """
    seed, prompt, tool_venv, receipt = (Path(path).absolute() for path in
                                        (seed, prompt, tool_venv, receipt))
    hidden_paths = [Path(path).absolute() for path in hidden_paths]
    if arm not in {"native", "kryn"} or type(timeout) is not int or not 30 <= timeout <= 1800:
        raise ValueError("Use a known OpenCode arm and a 30–1800 second timeout")
    inputs = (seed, prompt, tool_venv, receipt, *hidden_paths)
    if any(path != path.resolve() or any(parent.is_symlink() for parent in path.parents)
           for path in inputs):
        raise ValueError("Trial paths must be canonical and without symlinks")
    if (receipt.parent != Path("/private/tmp") or receipt.exists() or
            not hidden_paths or not seed.is_dir() or not prompt.is_file() or
            not tool_venv.is_dir() or any(not path.exists() for path in hidden_paths) or
            any(path.is_relative_to(seed) or seed.is_relative_to(path) or
                path.is_relative_to(tool_venv) or tool_venv.is_relative_to(path)
                for path in hidden_paths)):
        raise ValueError("Use a fresh direct /private/tmp receipt and frozen task inputs")
    receipt.mkdir(mode=0o700)
    report = {"kind": "research_agent_grade_data_barrier", "task_id": task_id,
              "arm": arm, "protected_score": False, "graded": False,
              "barrier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    started = time.monotonic()
    try:
        base_commit = command([str(GIT), "-C", str(seed), "rev-parse", "HEAD"]).decode().strip()
        if command([str(GIT), "-C", str(seed), "status", "--porcelain=v1",
                    "--untracked-files=all", "--ignored"]):
            raise BarrierError("Frozen seed is dirty")
        candidate = create_volume(receipt, "candidate")
        def agent_phase():
            workspace = candidate.mount / "workspace"
            private = candidate.mount / "private"
            private.mkdir(mode=0o700)
            clean_clone(seed, workspace, base_commit)
            if any(workspace.stat().st_dev == path.stat().st_dev for path in hidden_paths):
                raise BarrierError("Candidate volume shares a hidden file device")
            args = SimpleNamespace(workspace=workspace, base_commit=base_commit,
                                   task_id=task_id, prompt=prompt,
                                   evidence=receipt / "agent-evidence", arm=arm,
                                   tool_venv=tool_venv, private_parent=private,
                                   timeout=timeout)
            result = run(args, defer_patch=True)
            report["agent"] = result
            report["agent"]["workspace"] = str(workspace)
            return result
        agent = do_then_detach(candidate, report, "candidate_detached", agent_phase)
        if (not agent["completed"] or not agent["patch_deferred"] or
                not agent.get("inference_relay_settled")):
            raise BarrierError("Agent did not complete an isolated deferred-patch turn")
        frozen = attach(candidate.image, receipt, readonly=True)
        def capture_phase():
            evidence = receipt / "capture-evidence"
            evidence.mkdir(mode=0o700)
            samples = []
            monitor = NativeResourceGuard(evidence, samples)
            before_idle = after_idle = False
            try:
                before_idle = runtime_is_idle(evidence, "runtime-before", model_id=MODEL_ID,
                                              guard_gib=22)
                if not before_idle:
                    raise BarrierError("Model runtime was not idle before patch capture")
                monitor.start()
                captured = capture_readonly(frozen, receipt, base_commit, agent,
                                            receipt / "agent-evidence", arm, tool_venv,
                                            monitor.cancel.is_set)
                report["capture"] = captured
                after_idle = runtime_is_idle(evidence, "runtime-after", model_id=MODEL_ID,
                                             guard_gib=22)
            finally:
                try:
                    monitor.close()
                finally:
                    report["capture_guard"] = {
                        "preflight_passed": monitor.preflight_passed,
                        "cancelled": monitor.cancel.is_set(),
                        "reason": monitor.guard.reason,
                        "max_swap_growth_bytes": monitor.guard.max_swap_growth,
                        "warning_samples_to_abort": monitor.guard.warning_samples,
                        "runtime_before_idle": before_idle,
                        "runtime_after_idle": after_idle,
                        "resources": summarize_resources(samples),
                    }
            guard = report["capture_guard"]
            if (guard["cancelled"] or guard["reason"] or
                    not guard["resources"]["telemetry_complete"] or not after_idle):
                raise BarrierError("Read-only patch capture resource or runtime settlement failed")
            return captured
        do_then_detach(frozen, report, "capture_detached", capture_phase)
        grader = create_volume(receipt, "grader")
        def grade_phase():
            workspace = grader.mount / "workspace"
            private = grader.mount / "private"
            private.mkdir(mode=0o700)
            clean_clone(seed, workspace, base_commit)
            if any(workspace.stat().st_dev == path.stat().st_dev for path in hidden_paths):
                raise BarrierError("Grading clone shares a hidden file device")
            if (workspace == Path(agent["workspace"]) or
                    workspace.is_relative_to(Path(agent["workspace"]))):
                raise BarrierError("Grading clone overlaps the Agent sandbox path")
            apply_patch(workspace, private, receipt / "agent-evidence/model.patch")
            return grade(workspace, private, receipt)
        result = do_then_detach(grader, report, "grader_detached", grade_phase)
        report["grader_result"] = result
        report["graded"] = True
        return report
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        report["wall_seconds"] = round(time.monotonic() - started, 3)
        (receipt / "barrier.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
