#!/usr/bin/env python3
"""Run one pinned external task through native OpenCode; emit a patch for its official grader.

The benchmark oracle remains outside the whole-process candidate boundary. This
adapter owns lifecycle and evidence only; OpenCode remains the agent loop.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import learning
from native_client import BINARY, MODEL_ID, NativeServer, owned_config
from context_probe import summarize_resources
from run_native_trial import (NativeResourceGuard, export_owned_sessions,
                              generation_completion, native_control_config,
                              plugin_active, plugin_absent, runtime_is_idle,
                              settle_owned_sessions)

ROOT = Path(__file__).resolve().parents[1]


def git(workspace, *args):
    return subprocess.check_output(["git", "-C", str(workspace), *args], text=True,
                                   stderr=subprocess.STDOUT, timeout=20).strip()


def prepare(workspace, prompt_file, evidence, base_commit):
    paths = [Path(p).absolute() for p in (workspace, prompt_file, evidence)]
    if any(path != path.resolve() or any(parent.is_symlink() for parent in path.parents)
           for path in paths):
        raise ValueError("External task paths must be canonical and without symlinks")
    workspace, prompt_file, evidence = paths
    if (not workspace.is_relative_to(Path("/private/tmp")) or not (workspace / ".git").is_dir()
            or prompt_file.is_relative_to(workspace) or evidence.is_relative_to(workspace)
            or workspace.is_relative_to(evidence) or evidence.exists()):
        raise ValueError("Use a clean disposable /private/tmp Git checkout and separate fresh inputs/evidence")
    if git(workspace, "rev-parse", "HEAD") != base_commit or git(workspace, "status", "--porcelain"):
        raise ValueError("External task checkout differs from its declared clean base commit")
    if not prompt_file.is_file() or not prompt_file.read_bytes().strip():
        raise ValueError("External task prompt is missing")
    evidence.mkdir(mode=0o700)
    # Keep plugin state fresh across failed startup attempts in the same checkout.
    state_dir = workspace / (".git/kryn-external-" + hashlib.sha256(str(evidence).encode()).hexdigest()[:16])
    state_dir.mkdir(mode=0o700)
    return workspace, prompt_file, evidence, state_dir


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
            not (venv / "bin/rg").is_file()):
        raise ValueError("Benchmark tool venv must be a real disposable /private/tmp Python venv with rg")
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
    return venv / "bin", [venv, base, *libraries], {
        "pytest_version": pytest.stdout.strip(),
        "python_sha256": hashlib.sha256((venv / "bin/python3").resolve().read_bytes()).hexdigest(),
        "rg_sha256": hashlib.sha256((venv / "bin/rg").read_bytes()).hexdigest(),
        "packages": json.loads(package_listing),
    }


def drive(child, prompt, timeout, cancelled):
    deadline, first = time.monotonic() + timeout, True
    output = errors = b""
    while True:
        if cancelled():
            return "resource_guard", output, errors
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return "timeout", output, errors
        try:
            output, errors = child.communicate(input=prompt if first else None,
                                               timeout=min(.5, remaining))
            if len(output) > 2 * 1024**2 or len(errors) > 64 * 1024:
                return "output_budget", output, errors
            return ("resource_guard" if cancelled() else None), output, errors
        except subprocess.TimeoutExpired as error:
            first = False
            output, errors = error.output or b"", error.stderr or b""
            if len(output) > 2 * 1024**2 or len(errors) > 64 * 1024:
                return "output_budget", output, errors


def run(args):
    workspace, prompt_file, evidence, state_dir = prepare(
        args.workspace, args.prompt, args.evidence, args.base_commit)
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
              "model_id": MODEL_ID, "timeout_seconds": args.timeout, "completed": False}
    private_parent = getattr(args, "private_parent", None)
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
            with NativeServer(workspace, config, evidence / "native.log", background=background) as server:
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
        except BaseException as error:
            report["error"] = type(error).__name__ + ": " + str(error)
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
    patch = subprocess.check_output(["git", "-C", str(workspace), "diff", "--binary",
                                     args.base_commit, "--"], timeout=20)
    (evidence / "model.patch").write_bytes(patch)
    untracked = git(workspace, "ls-files", "--others", "--exclude-standard").splitlines()
    if untracked:
        report["untracked_files_omitted_from_patch"] = untracked
        report["completed"] = False
    report["patch_sha256"] = hashlib.sha256(patch).hexdigest()
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
