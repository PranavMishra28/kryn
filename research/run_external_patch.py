#!/usr/bin/env python3
"""Run one pinned external task through native OpenCode; emit a patch for its official grader.

The benchmark oracle remains outside the whole-process candidate boundary. This
adapter owns lifecycle and evidence only; OpenCode remains the agent loop.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import learning
from native_client import BINARY, MODEL_ID, NativeServer, background_boundary, owned_config
from context_probe import summarize_resources
from run_native_trial import (NativeResourceGuard, export_owned_sessions,
                              generation_completion, native_control_config,
                              plugin_active, plugin_absent, runtime_is_idle,
                              settle_owned_sessions)

ROOT = Path(__file__).resolve().parents[1]
PATCH_BUDGET = 16 * 1024**2
UNTRACKED_LIST_BUDGET = 256 * 1024
UNTRACKED_COUNT_BUDGET = 1024


class PatchBudgetExceeded(RuntimeError):
    """The candidate produced more source evidence than this trial can retain."""


class CaptureCancelled(RuntimeError):
    """The host resource guard interrupted patch capture."""


class CandidateGitConfigChanged(RuntimeError):
    """The patch would no longer use the checkout's preregistered Git rules."""


def git(workspace, *args):
    return subprocess.check_output(["git", "-C", str(workspace), *args], text=True,
                                   stderr=subprocess.STDOUT, timeout=20).strip()


def kill_group(child):
    # The leader has not yet been reaped. Its process-group ID cannot have been
    # reused, even when a Git filter has forked descendants holding stdout.
    failure = None
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        # macOS can return EPERM for an already exited sandbox-exec leader
        # whose group has vanished; it permits the same kill while live.
        if os.waitid(os.P_PID, child.pid,
                     os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
            child.kill()
            failure = RuntimeError("Could not terminate live Git process group")
    status = child.wait()
    if failure is not None:
        raise failure
    return status


def bounded_output(command, destination, limit, *, env, cwd, cancelled, timeout=20):
    """Stream a command to disk, stopping before it can exceed its byte budget."""
    digest = hashlib.sha256()
    total = 0
    deadline = time.monotonic() + timeout
    child = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, env=env, start_new_session=True)
    try:
        with destination.open("wb") as output, selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            while True:
                if cancelled():
                    raise CaptureCancelled("Resource guard interrupted patch capture")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                if not selector.select(min(remaining, .25)):
                    continue
                chunk = os.read(child.stdout.fileno(), min(64 * 1024, limit + 1 - total))
                if not chunk:
                    break
                if total + len(chunk) > limit:
                    raise PatchBudgetExceeded(f"Git output exceeded {limit} bytes")
                output.write(chunk)
                digest.update(chunk)
                total += len(chunk)
        while os.waitid(os.P_PID, child.pid,
                        os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
            if cancelled():
                raise CaptureCancelled("Resource guard interrupted patch capture")
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(command, timeout)
            time.sleep(.05)
    except BaseException:
        try:
            kill_group(child)
        finally:
            child.stdout.close()
        raise
    try:
        status = kill_group(child)
    finally:
        child.stdout.close()
    if status:
        raise subprocess.CalledProcessError(status, command)
    return total, digest.hexdigest()


def quiet_command(command, *, env, cwd, cancelled, timeout=20):
    child = subprocess.Popen(command, cwd=cwd, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, env=env, start_new_session=True)
    deadline = time.monotonic() + timeout
    try:
        while os.waitid(os.P_PID, child.pid,
                        os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
            if cancelled():
                raise CaptureCancelled("Resource guard interrupted patch capture")
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(command, timeout)
            time.sleep(.1)
    except BaseException:
        kill_group(child)
        raise
    status = kill_group(child)
    if status:
        raise subprocess.CalledProcessError(status, command)


def candidate_file_size(root_fd, name, device, *, missing_ok=False):
    """Stat a candidate path without following a swapped directory or file link."""
    path = Path(name)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise PatchBudgetExceeded("Candidate path leaves the workspace")
    current = os.dup(root_fd)
    try:
        for component in path.parts[:-1]:
            try:
                following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                    dir_fd=current)
            except FileNotFoundError:
                if missing_ok:
                    return 0
                raise
            os.close(current)
            current = following
            if os.fstat(current).st_dev != device:
                raise PatchBudgetExceeded("Candidate path crosses a device boundary")
        try:
            info = os.stat(path.parts[-1], dir_fd=current, follow_symlinks=False)
        except FileNotFoundError:
            if missing_ok:
                return 0
            raise
        if info.st_dev != device or not (stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)):
            raise PatchBudgetExceeded("Candidate path is not a regular file or link")
        return info.st_size
    finally:
        os.close(current)


def git_config_sha256(workspace):
    """Pin candidate Git configuration without following model-created links."""
    root = os.open(workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        device = os.fstat(root).st_dev
        directory = os.open(".git", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=root)
        try:
            if os.fstat(directory).st_dev != device:
                raise PatchBudgetExceeded("Candidate Git directory crosses a device boundary")
            config = os.open("config", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            try:
                info = os.fstat(config)
                if not stat.S_ISREG(info.st_mode) or info.st_dev != device or info.st_size > 1024**2:
                    raise PatchBudgetExceeded("Candidate Git config exceeds a safe bound")
                with os.fdopen(config, "rb", closefd=False) as source:
                    payload = source.read(1024**2 + 1)
                if len(payload) > 1024**2:
                    raise PatchBudgetExceeded("Candidate Git config grew beyond a safe bound")
                return hashlib.sha256(payload).hexdigest()
            finally:
                os.close(config)
        finally:
            os.close(directory)
    finally:
        os.close(root)


def isolated_git(workspace, private, dependencies, git_binary, tool_path):
    """Build the same networkless Git boundary for preflight and patch capture."""
    for name in ("tmpdir", "tmp", "temp", "xdg_config_home"):
        (private / name).mkdir(mode=0o700, exist_ok=True)
    # Git reads candidate-controlled config/attributes and can execute their
    # fsmonitor or filter commands. Run every Git child under a networkless
    # whole-process read boundary; the host only receives bounded pipe output.
    toolchain = Path("/Library/Developer/CommandLineTools")
    capture_dependencies = [*dependencies]
    if toolchain.is_dir():
        capture_dependencies.append(toolchain.resolve())
    prefix = background_boundary(workspace, private, capture_dependencies, None)
    capture_env = {
        "PATH": str(tool_path) + ":/usr/bin:/bin" if tool_path else "/usr/bin:/bin",
        "HOME": str(private), "TMPDIR": str(private / "tmpdir"),
        "TMP": str(private / "tmp"), "TEMP": str(private / "temp"),
        "XDG_CONFIG_HOME": str(private / "xdg_config_home"),
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null", "LANG": "C",
    }
    git_command = prefix + [str(git_binary), "-C", str(workspace),
                            "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null"]
    return git_command, capture_env


def collect_patch(workspace, base_commit, evidence, *, private, dependencies,
                  git_binary, tool_path, cancelled):
    """Include new source files in a bounded patch without changing the agent index."""
    workspace, evidence, private = Path(workspace), Path(evidence), Path(private)
    git_command, capture_env = isolated_git(
        workspace, private, dependencies, git_binary, tool_path)
    names_file = evidence / "untracked.paths"
    changed_file = evidence / "changed.paths"
    temporary_index = None
    workspace_fd = os.open(workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    device = os.fstat(workspace_fd).st_dev
    patch_file = evidence / "model.patch"
    try:
        bounded_output(git_command + ["ls-files", "--others", "--exclude-standard", "-z"],
                       names_file, UNTRACKED_LIST_BUDGET, env=capture_env,
                       cwd=workspace, cancelled=cancelled)
        names = [os.fsdecode(name) for name in names_file.read_bytes().split(b"\0") if name]
        if len(names) > UNTRACKED_COUNT_BUDGET:
            raise PatchBudgetExceeded("Too many untracked candidate files")
        if sum(candidate_file_size(workspace_fd, name, device) for name in names) > PATCH_BUDGET:
            raise PatchBudgetExceeded("Untracked candidate files exceed patch budget")
        bounded_output(git_command + ["diff", "--name-only", "-z", base_commit, "--"],
                       changed_file, UNTRACKED_LIST_BUDGET, env=capture_env,
                       cwd=workspace, cancelled=cancelled)
        changed = [os.fsdecode(name) for name in changed_file.read_bytes().split(b"\0") if name]
        if len(changed) > UNTRACKED_COUNT_BUDGET:
            raise PatchBudgetExceeded("Too many changed candidate files")
        if sum(candidate_file_size(workspace_fd, name, device, missing_ok=True)
               for name in changed) > PATCH_BUDGET:
            raise PatchBudgetExceeded("Changed candidate files exceed patch budget")
        git_dir_fd = os.open(".git", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                             dir_fd=workspace_fd)
        try:
            if os.fstat(git_dir_fd).st_dev != device:
                raise PatchBudgetExceeded("Candidate Git directory crosses a device boundary")
            index_fd = os.open("index", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=git_dir_fd)
            try:
                info = os.fstat(index_fd)
                if (not stat.S_ISREG(info.st_mode) or
                        info.st_dev != device or info.st_size > PATCH_BUDGET):
                    raise PatchBudgetExceeded("Candidate Git index exceeds patch budget")
                with tempfile.NamedTemporaryFile(prefix="patch-index-", dir=private,
                                                 delete=False) as temporary:
                    temporary_index = Path(temporary.name)
                    with os.fdopen(index_fd, "rb", closefd=False) as source:
                        copied = 0
                        while chunk := source.read(64 * 1024):
                            copied += len(chunk)
                            if copied > PATCH_BUDGET:
                                raise PatchBudgetExceeded("Candidate Git index grew beyond patch budget")
                            temporary.write(chunk)
            finally:
                os.close(index_fd)
        finally:
            os.close(git_dir_fd)
        capture_env["GIT_INDEX_FILE"] = str(temporary_index)
        if names:
            quiet_command(git_command + ["add", "-N", "--", *names], env=capture_env,
                          cwd=workspace, cancelled=cancelled)
        size, sha = bounded_output(git_command + ["diff", "--binary", "--no-ext-diff",
                                    "--no-textconv", base_commit, "--"],
                                   patch_file, PATCH_BUDGET, env=capture_env,
                                   cwd=workspace, cancelled=cancelled)
        return patch_file, names, size, sha
    except BaseException:
        patch_file.unlink(missing_ok=True)
        raise
    finally:
        names_file.unlink(missing_ok=True)
        changed_file.unlink(missing_ok=True)
        if temporary_index is not None:
            temporary_index.unlink(missing_ok=True)
        os.close(workspace_fd)


def prepare(workspace, prompt_file, evidence, base_commit, *, private_parent=None):
    paths = [Path(p).absolute() for p in (workspace, prompt_file, evidence)]
    if any(path != path.resolve() or any(parent.is_symlink() for parent in path.parents)
           for path in paths):
        raise ValueError("External task paths must be canonical and without symlinks")
    workspace, prompt_file, evidence = paths
    if (not workspace.is_relative_to(Path("/private/tmp")) or not (workspace / ".git").is_dir()
            or prompt_file.is_relative_to(workspace) or evidence.is_relative_to(workspace)
            or workspace.is_relative_to(evidence) or evidence.exists()):
        raise ValueError("Use a clean disposable /private/tmp Git checkout and separate fresh inputs/evidence")
    parent = Path(private_parent or "/private/tmp")
    if private_parent is not None and (parent != parent.resolve() or
            parent.parent != workspace.parent or parent.stat().st_dev != workspace.stat().st_dev or
            parent.stat().st_dev == Path("/private/tmp").stat().st_dev):
        raise ValueError("Protected task private parent must be a sibling on the candidate volume")
    with tempfile.TemporaryDirectory(prefix="kryn-preflight-", dir=parent) as temporary:
        private = Path(temporary)
        command, env = isolated_git(
            workspace, private, [],
            Path("/Library/Developer/CommandLineTools/usr/bin/git"), None)
        head = private / "head.txt"
        status = private / "status.txt"
        bounded_output(command + ["rev-parse", "HEAD"], head, 128,
                       env=env, cwd=workspace, cancelled=lambda: False)
        bounded_output(command + ["status", "--porcelain=v1", "--untracked-files=all",
                                  "--ignored"], status,
                       UNTRACKED_LIST_BUDGET, env=env, cwd=workspace, cancelled=lambda: False)
        if head.read_text().strip() != base_commit or status.stat().st_size:
            raise ValueError("External task checkout differs from its declared clean base commit")
    if not prompt_file.is_file() or not prompt_file.read_bytes().strip():
        raise ValueError("External task prompt is missing")
    config_sha = git_config_sha256(workspace)
    evidence.mkdir(mode=0o700)
    # Keep plugin state fresh across failed startup attempts in the same checkout.
    state_dir = workspace / (".git/kryn-external-" + hashlib.sha256(str(evidence).encode()).hexdigest()[:16])
    state_dir.mkdir(mode=0o700)
    return workspace, prompt_file, evidence, state_dir, config_sha


def configuration(workspace, state_dir, arm, relay_url):
    config = copy.deepcopy(owned_config())
    if arm == "native":
        config = native_control_config(config)
    products = [p for p in config.get("plugins", []) if isinstance(p, dict)
                and "profileId" in p.get("options", {})]
    if len(products) != (0 if arm == "native" else 1):
        raise RuntimeError("Unexpected product plugin count")
    dependencies = [BINARY.parent.parent.resolve(), *learning.python_dependencies()]
    if products:
        products[0]["options"]["stateDir"] = str(state_dir)
        products[0]["options"]["observe"] = True
        products[0]["options"]["inferenceBaseURL"] = relay_url
        dependencies.append(Path(products[0]["package"]).resolve())
        node_binary = products[0]["options"].get("nodeBinary")
        if node_binary:
            dependencies.append(Path(node_binary).resolve())
    config["mcp"] = {"servers": {}}
    config["skills"] = []
    config["permissions"] += [
        {"action": "shell", "resource": "*", "effect": "allow"},
        {"action": "external_directory", "resource": "*", "effect": "deny"},
    ]
    provider = config["providers"]["local"]
    provider["settings"]["baseURL"] = relay_url
    model = provider["models"]["qwen"]
    model.setdefault("settings", {})["baseURL"] = relay_url
    for variant in model.get("variants", []):
        variant.setdefault("settings", {})["baseURL"] = relay_url
    return config, products, dependencies


def benchmark_tools(venv):
    if venv is None:
        return None, [], None
    venv = Path(venv).absolute()
    if (venv != venv.resolve() or not venv.is_relative_to(Path("/private/tmp")) or
            not (venv / "pyvenv.cfg").is_file() or not (venv / "bin/python3").is_file() or
            (venv / "bin/python3").is_symlink() or not (venv / "bin/rg").is_file() or
            (venv / "bin/rg").is_symlink() or not (venv / "bin/git").is_file()):
        raise ValueError("Benchmark tool venv needs Python, rg and Git inside /private/tmp")
    git_binary = (venv / "bin/git").resolve()
    if not (git_binary.is_relative_to(venv) or
            git_binary.is_relative_to(Path("/Library/Developer/CommandLineTools"))):
        raise ValueError("Benchmark Git must be copied or use the installed Command Line Tools")
    pytest = subprocess.run([str(venv / "bin/python3"), "-I", "-m", "pytest", "--version"],
                            capture_output=True, text=True, timeout=10)
    if pytest.returncode:
        raise RuntimeError("Benchmark tool venv lacks runnable pytest; no prompt sent")
    base = Path(subprocess.check_output([str(venv / "bin/python3"), "-I", "-c",
        "import sys; print(sys.base_prefix)"], text=True, timeout=5).strip()).resolve()
    linked = subprocess.check_output(["/usr/bin/otool", "-L", str(venv / "bin/rg")],
                                     text=True, timeout=5)
    libraries = []
    for line in linked.splitlines()[1:]:
        name = line.strip().split(" ", 1)[0]
        if name.startswith("/") and not name.startswith(("/usr/lib/", "/System/")):
            libraries.append(Path(name).resolve())
    package_listing = subprocess.check_output([str(venv / "bin/python3"), "-I", "-c",
        "import importlib.metadata as m,json; print(json.dumps(sorted((d.metadata['Name'], d.version) for d in m.distributions())))"],
        text=True, timeout=10)
    return venv / "bin", [venv, base, git_binary, *libraries], {
        "pytest_version": pytest.stdout.strip(),
        "python_sha256": hashlib.sha256((venv / "bin/python3").resolve().read_bytes()).hexdigest(),
        "rg_sha256": hashlib.sha256((venv / "bin/rg").read_bytes()).hexdigest(),
        "git_sha256": hashlib.sha256(git_binary.read_bytes()).hexdigest(),
        "packages": json.loads(package_listing),
    }


def drive(child, prompt, timeout, cancelled):
    deadline = time.monotonic() + timeout
    streams = {child.stdout: (bytearray(), 2 * 1024**2),
               child.stderr: (bytearray(), 64 * 1024)}
    pending = memoryview(prompt)
    with selectors.DefaultSelector() as selector:
        for stream in streams:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ)
        os.set_blocking(child.stdin.fileno(), False)
        selector.register(child.stdin, selectors.EVENT_WRITE)
        while selector.get_map():
            if cancelled():
                return "resource_guard", bytes(streams[child.stdout][0]), bytes(streams[child.stderr][0])
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return "timeout", bytes(streams[child.stdout][0]), bytes(streams[child.stderr][0])
            for key, _ in selector.select(min(.25, remaining)):
                stream = key.fileobj
                if stream is child.stdin:
                    try:
                        written = os.write(stream.fileno(), pending[:64 * 1024]) if pending else 0
                        pending = pending[written:]
                    except BrokenPipeError:
                        pending = memoryview(b"")
                    if not pending:
                        selector.unregister(stream)
                        stream.close()
                else:
                    buffer, limit = streams[stream]
                    try:
                        chunk = os.read(stream.fileno(), min(64 * 1024, limit + 1 - len(buffer)))
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(stream)
                    else:
                        buffer.extend(chunk)
                        if len(buffer) > limit:
                            return "output_budget", bytes(streams[child.stdout][0]), bytes(streams[child.stderr][0])
    return ("resource_guard" if cancelled() else None), bytes(streams[child.stdout][0]), bytes(streams[child.stderr][0])


def run(args):
    private_parent = getattr(args, "private_parent", None)
    workspace, prompt_file, evidence, state_dir, git_config_sha = prepare(
        args.workspace, args.prompt, args.evidence, args.base_commit,
        private_parent=private_parent)
    prompt = prompt_file.read_bytes()
    started = time.monotonic()
    profile_path = ROOT / "setup/accepted-profile.json"
    profile = json.loads(profile_path.read_text())
    if profile.get("repository", "").rsplit("/", 1)[-1] != MODEL_ID:
        raise RuntimeError("Installed champion profile does not identify the requested model")
    report = {"schema": 1, "task_id": args.task_id, "arm": args.arm,
              "base_commit": args.base_commit, "prompt_sha256": hashlib.sha256(prompt).hexdigest(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "source_commit": git(ROOT, "rev-parse", "HEAD"),
              "opencode_binary_sha256": hashlib.sha256(BINARY.read_bytes()).hexdigest(),
              "model_profile_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
              "model_repository": profile["repository"], "model_revision": profile["revision"],
              "model_id": MODEL_ID, "timeout_seconds": args.timeout, "completed": False,
              "initial_git_config_sha256": git_config_sha}
    report["candidate_private_parent"] = str(private_parent) if private_parent else None
    samples = []
    with learning.InferenceRelay(MODEL_ID, 8192, min(args.timeout, 360)) as relay:
        config, products, dependencies = configuration(
            workspace, state_dir, args.arm, f"http://127.0.0.1:{relay.port}/v1")
        monitor = NativeResourceGuard(evidence, samples)
        try:
            tool_path, tool_dependencies, tool_manifest = benchmark_tools(args.tool_venv)
            dependencies += tool_dependencies
            report["benchmark_tool_path"] = str(tool_path) if tool_path else None
            report["benchmark_tool_dependencies"] = [str(path) for path in tool_dependencies]
            report["benchmark_tool_manifest"] = tool_manifest
            report["config_sha256"] = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
            if not runtime_is_idle(evidence, "runtime-before", model_id=MODEL_ID, guard_gib=22):
                raise RuntimeError("Expected guarded model runtime is not idle")
            monitor.start()
            background = {"dependencies": dependencies, "inference_port": relay.port,
                          "cancel": monitor.cancel.is_set}
            if private_parent is not None:
                background["private_parent"] = private_parent
            if tool_path is not None:
                background["tool_path"] = str(tool_path)
            native_server = NativeServer(workspace, config, evidence / "native.log",
                                         background=background)
            native_server.env["GIT_CONFIG_NOSYSTEM"] = "1"
            with native_server as server:
                # /api/info can become ready before asynchronous plugin discovery.
                for _ in range(75):
                    inventory = server.request("GET", "/api/plugin")
                    entries = inventory.get("data", [])
                    policy_ready = any(p.get("id") == "opencode.config.policy" and
                                       p.get("state", {}).get("status") == "active" for p in entries)
                    active = policy_ready and (plugin_absent(inventory, "kryn.product") if args.arm == "native"
                              else plugin_active(inventory, "kryn.product", Path(products[0]["package"])))
                    if active or any(p.get("state", {}).get("status") in {"failed", "error"} for p in entries):
                        break
                    time.sleep(.2)
                (evidence / "plugin-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
                if not active:
                    raise RuntimeError("Requested OpenCode arm is not active")
                session = server.request("POST", "/api/session", {
                    "title": args.task_id, "agent": "agent",
                    "model": {"providerID": "local", "id": "qwen", "variant": "default"},
                    "location": {"directory": str(workspace)}}, timeout=5)["data"]
                sid = session["id"]
                command = server.background_prefix + [str(BINARY), "run", "--server", server.url,
                    "--session", sid, "--agent", "agent", "--model", "local/qwen",
                    "--format", "json", "--thinking"]
                child = subprocess.Popen(command, cwd=workspace, env=server.env,
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                try:
                    cause, output, errors = drive(child, prompt, args.timeout, monitor.cancel.is_set)
                    report["intervention"] = cause
                    report["settlement"] = learning.settle_background(
                        server, sid, workspace, relay, interrupt=cause is not None)
                finally:
                    if child.poll() is None:
                        child.terminate()
                        try: child.wait(timeout=2)
                        except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=2)
                    report["cli_exit_code"] = child.returncode
                (evidence / "events.jsonl").write_bytes(output[:2 * 1024**2])
                (evidence / "stderr.log").write_bytes(errors[:64 * 1024])
                owned = settle_owned_sessions(server, sid, workspace, evidence,
                                               model_id=MODEL_ID, guard_gib=22)
                report["owned_settlement"] = owned
                if not owned.get("idle"):
                    raise RuntimeError("Native descendants or runtime did not settle")
                exports, ownership = export_owned_sessions(
                    server, owned["verified_sessions"], sid, workspace, evidence)
                report["ownership"] = ownership
                report["generation"] = generation_completion(
                    exports, 0, sid, set(owned["verified_sessions"]))
                report["completed"] = bool(cause is None and child.returncode == 0
                    and ownership["verified"] and report["generation"]["verified"])
            try:
                post_git_config_sha = git_config_sha256(workspace)
                report["post_git_config_sha256"] = post_git_config_sha
                if post_git_config_sha != git_config_sha:
                    raise CandidateGitConfigChanged("Candidate Git config changed during the model turn")
                with tempfile.TemporaryDirectory(prefix="kryn-patch-",
                                                 dir=private_parent or "/private/tmp") as capture_private:
                    _, untracked, patch_size, patch_sha = collect_patch(
                        workspace, args.base_commit, evidence,
                        private=Path(capture_private), dependencies=dependencies,
                        git_binary=(tool_path / "git" if tool_path else
                                    Path("/Library/Developer/CommandLineTools/usr/bin/git")),
                        tool_path=tool_path, cancelled=monitor.cancel.is_set)
                report["untracked_files_included_in_patch"] = untracked
                report["patch_size_bytes"] = patch_size
                report["patch_sha256"] = patch_sha
            except PatchBudgetExceeded as error:
                report["intervention"] = "patch_budget"
                report["patch_error"] = str(error)
                report["completed"] = False
            except CandidateGitConfigChanged as error:
                report["intervention"] = "git_config_changed"
                report["patch_error"] = str(error)
                report["completed"] = False
            except CaptureCancelled as error:
                report["intervention"] = "resource_guard"
                report["patch_error"] = str(error)
                report["completed"] = False
        except BaseException as error:
            report["error"] = type(error).__name__ + ": " + str(error)
            report["completed"] = False
            raise
        finally:
            relay.cancel()
            monitor.close()
            report["requests"] = relay.records
            report["resources"] = summarize_resources(samples)
            report["wall_seconds"] = round(time.monotonic() - started, 3)
            report["completed"] = bool(report["completed"] and not monitor.guard.reason
                                       and report["resources"].get("telemetry_complete"))
            (evidence / "driver.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--arm", choices=("native", "kryn"), default="kryn")
    parser.add_argument("--tool-venv", type=Path, help="preflighted disposable benchmark Python/ripgrep venv")
    parser.add_argument("--private-parent", type=Path,
                        help="sibling private directory on the mounted candidate volume")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    if not 30 <= args.timeout <= 1800:
        parser.error("Timeout must be 30–1800 seconds")
    result = run(args)
    print(json.dumps({k: result.get(k) for k in ("task_id", "arm", "completed", "wall_seconds",
                                                 "patch_sha256", "intervention", "error")}))
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
