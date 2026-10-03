#!/usr/bin/env python3
"""No-model alias canary for the actual whole-process research sandbox.

The same-volume control must fail; the two separate-volume cases must pass.
A passing canary is not a qualified protected holdout or a full agent run.
"""
import argparse
import errno
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from native_client import NativeServer, background_boundary
from run_native_trial import plugin_active, plugin_absent
from run_external_patch import benchmark_tools, configuration

ROOT = Path("/private/tmp")


def run(command, *, input=None):
    return subprocess.run(command, input=input, text=True, capture_output=True,
                          timeout=20, close_fds=True)


def mount_active(base, mount):
    try:
        return mount.stat().st_dev != base.stat().st_dev
    except OSError:
        return True  # Never recursively remove a base whose mount state is unknown.


def probe(workspace, private, oracle, image=None, device=None, run_root=None,
          same_volume_control=False):
    marker = oracle.read_text()
    alias = workspace / "oracle-symlink"
    alias.symlink_to(oracle)
    prefix = background_boundary(workspace, private, [], None)
    if "(deny file-read*)" not in prefix[2]:
        raise RuntimeError("Research sandbox does not deny file-read metadata")

    def denied(name, command):
        result = run(prefix + command)
        return name, result.returncode != 0 and result.stdout == "" and marker not in result.stderr

    def listing_denied(directory):
        result = run(prefix + ["/bin/ls", "-a", str(directory)])
        return result.returncode != 0 and result.stdout == ""

    visible_result = run(prefix + ["/bin/cat", str(workspace / "visible.txt")])
    checks = dict([
        denied("direct_read", ["/bin/cat", str(oracle)]),
        denied("symlink_read", ["/bin/cat", str(alias)]),
        denied("copy_read", ["/bin/cp", str(oracle), str(workspace / "copied")]),
        denied("metadata_read", ["/usr/bin/stat", str(oracle)]),
        denied("file_url_read", ["/usr/bin/curl", "-sS", "file://" + str(oracle)]),
    ])
    checks["ancestor_listing_denied"] = listing_denied(workspace.parent)
    if run_root is not None:
        checks["runroot_listing_denied"] = listing_denied(run_root)
    # The visible file is required to work; all hidden-file probes must fail.
    checks["workspace_read"] = (visible_result.returncode == 0
                                and visible_result.stdout == "candidate-visible")
    checks["different_filesystem"] = os.stat(workspace).st_dev != os.stat(oracle).st_dev

    hardlink = workspace / "oracle-hardlink"
    try:
        os.link(oracle, hardlink)  # Trusted parent simulates a pre-existing alias.
        checks["hardlink_impossible"] = False
        linked = run(prefix + ["/bin/cat", str(hardlink)])
        checks["hardlink_read_denied"] = linked.returncode != 0 and marker not in linked.stdout + linked.stderr
        if same_volume_control:
            checks["hardlink_marker_read"] = linked.returncode == 0 and linked.stdout == marker
    except OSError as error:
        checks["hardlink_impossible"] = error.errno == errno.EXDEV
        checks["hardlink_read_denied"] = True  # There is no alias to read.
        if same_volume_control:
            checks["hardlink_marker_read"] = False
    checks["candidate_link_denied"] = denied("candidate_link_denied",
        ["/bin/ln", str(oracle), str(workspace / "candidate-hardlink")])[1]
    if image is not None:
        checks["backing_image_read_denied"] = denied("backing_image_read_denied",
            ["/bin/cat", str(image)])[1]
        checks["raw_device_read_denied"] = bool(device and Path(device).exists() and
            denied("raw_device_read_denied",
                   ["/bin/dd", "if=" + device, "of=/dev/null", "bs=16", "count=1"])[1])
    return checks


def server_probe(workspace, log, oracle, marker, private_parent=None,
                 *, arm="kryn", tool_venv=None, extra_hidden=(), source_file=None):
    # Use the same product configuration and dependency builder as the external
    # candidate runner. API inventory initializes plugins without inference.
    subprocess.run(["/usr/bin/git", "init", "-q", str(workspace)], check=True,
                   capture_output=True, timeout=10)
    state = workspace / ".git" / ("kryn-boundary-canary-" + arm)
    state.mkdir(mode=0o700)
    config, products, dependencies = configuration(
        workspace, state, arm, "http://127.0.0.1:19876/v1")
    tool_path, tool_dependencies, _ = benchmark_tools(tool_venv)
    dependencies += tool_dependencies
    if source_file is not None:
        source_file = Path(source_file)
        if (not source_file.is_file() or source_file != source_file.resolve()
                or source_file.stat().st_dev == workspace.stat().st_dev):
            raise RuntimeError("Source allowance requires a canonical host-side file")
        dependencies.append(source_file)

    def shell(server, argv, *, output_limit=4096):
        command = " ".join(shlex.quote(str(value)) for value in argv)
        response = server.request("POST", "/api/shell", {
            "command": command, "cwd": str(workspace), "timeout": 10000}, timeout=15)
        info = response.get("data", {})
        shell_id = info.get("id")
        if not isinstance(shell_id, str) or not shell_id.startswith("sh_"):
            raise RuntimeError("Native shell canary did not return an owned job")
        endpoint = "/api/shell/" + urllib.parse.quote(shell_id, safe="")
        try:
            deadline = time.monotonic() + 12
            while info.get("status") == "running" and time.monotonic() < deadline:
                time.sleep(.1)
                info = server.request("GET", endpoint, timeout=5).get("data", {})
            if info.get("status") != "exited" or type(info.get("exit")) is not int:
                raise RuntimeError("Native shell canary did not exit with a verified status")
            output = server.request("GET", endpoint +
                                    f"/output?cursor=0&limit={output_limit}",
                                    timeout=5).get("data", {})
            return info.get("exit"), output.get("output", "")
        finally:
            server.request("DELETE", endpoint, timeout=5)

    background = {"dependencies": dependencies, "inference_port": 19876}
    if private_parent is not None:
        background["private_parent"] = private_parent
    if tool_path is not None:
        background["tool_path"] = str(tool_path)
    native_server = NativeServer(workspace, config, log=log, background=background)
    native_server.env["GIT_CONFIG_NOSYSTEM"] = "1"
    with socket.socket() as blocked_listener, native_server as server:
        blocked_listener.bind(("127.0.0.1", 0))
        blocked_listener.listen(1)
        server.inventory()
        for domain in ("config", "agent", "command", "skill"):
            server.request("GET", "/api/" + domain, timeout=5)
        for _ in range(75):
            inventory = server.request("GET", "/api/plugin", timeout=5)
            plugins = inventory.get("data", [])
            policy_ready = any(entry.get("id") == "opencode.config.policy" and
                               entry.get("state", {}).get("status") == "active"
                               for entry in plugins)
            arm_ready = ((len(products) == 1 and plugin_active(
                          inventory, "kryn.product", Path(products[0]["package"])))
                         if arm == "kryn" else len(products) == 0 and plugin_absent(
                          inventory, "kryn.product"))
            if (policy_ready and arm_ready) or any(
                    entry.get("state", {}).get("status") in {"failed", "error"}
                    for entry in plugins):
                break
            time.sleep(.2)
        raw = run(server.background_prefix + ["/bin/cat", str(oracle)])
        visible_exit, visible_output = shell(server, ["/bin/cat", workspace / "visible.txt"])
        hidden_exit, hidden_output = shell(server, ["/bin/cat", oracle])
        python_exit, python_output = shell(server, ["python3", "-c", "print('python-ready')"])
        checks = {
            "native_server_started": True,
            "requested_arm_active": policy_ready and arm_ready,
            "server_profile_oracle_read_denied": raw.returncode != 0
                and raw.stdout == "" and marker not in raw.stderr,
            "api_shell_workspace_read": visible_exit == 0
                and visible_output == "candidate-visible",
            "api_shell_oracle_read_denied": hidden_exit != 0
                and hidden_output == f"cat: {oracle}: Operation not permitted\n",
            "api_shell_python_ready": python_exit == 0
                and python_output == "python-ready\n",
        }
        for label, hidden_path in extra_hidden:
            raw_hidden = run(server.background_prefix + ["/bin/cat", str(hidden_path)])
            api_exit, api_output = shell(server, ["/bin/cat", hidden_path])
            checks[f"server_profile_{label}_read_denied"] = (
                raw_hidden.returncode != 0 and raw_hidden.stdout == "")
            checks[f"api_shell_{label}_read_denied"] = (
                api_exit != 0 and api_output ==
                f"cat: {hidden_path}: Operation not permitted\n")
        blocked_port = blocked_listener.getsockname()[1]
        connect_script = ("import socket; s=socket.socket(); "
                          f"print('DENIED:'+str(s.connect_ex(('127.0.0.1',{blocked_port}))))")
        connect_exit, connect_output = shell(server, ["python3", "-c", connect_script])
        checks["api_shell_unlisted_loopback_denied"] = (
            connect_exit == 0 and connect_output in ("DENIED:1\n", "DENIED:13\n"))
        if tool_venv is not None:
            rg_exit, rg_output = shell(server, ["rg", "candidate-visible", workspace / "visible.txt"])
            pytest_exit, pytest_output = shell(server, ["python3", "-I", "-m", "pytest", "--version"])
            git_exit, git_output = shell(server, ["git", "-C", workspace,
                                                  "rev-parse", "--is-inside-work-tree"])
            checks["api_shell_rg_ready"] = rg_exit == 0 and rg_output == "candidate-visible\n"
            checks["api_shell_pytest_ready"] = pytest_exit == 0 and pytest_output.startswith("pytest ")
            checks["api_shell_git_ready"] = git_exit == 0 and git_output == "true\n"
        if source_file is not None:
            before = source_file.read_bytes()
            source_exit, source_output = shell(server, ["/bin/cat", source_file],
                                               output_limit=16384)
            write_exit, _ = shell(server, ["python3", "-c",
                "from pathlib import Path; Path(" + repr(str(source_file)) +
                ").write_text('tampered')"])
            list_exit, _ = shell(server, ["/bin/ls", "-a", source_file.parent])
            checks["api_shell_source_exact_read"] = (
                source_exit == 0 and source_output.encode() == before)
            checks["api_shell_source_write_denied"] = (
                write_exit != 0 and source_file.read_bytes() == before)
            checks["api_shell_source_parent_listing_denied"] = list_exit != 0
        return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("same-volume", "encrypted-volume", "candidate-volume"),
                        help="same-volume is the expected failing hardlink control")
    args = parser.parse_args()
    ROOT.mkdir(mode=0o700, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="kryn-holdout-boundary-", dir=ROOT))
    mount = base / ("mount" if args.mode == "candidate-volume" else "grader")
    mount.mkdir(mode=0o700)
    workspace = (mount if args.mode == "candidate-volume" else base) / "workspace"
    private = (mount if args.mode == "candidate-volume" else base) / "private"
    grader = base / "grader"
    if args.mode != "candidate-volume":
        for directory in (workspace, private):
            directory.mkdir(mode=0o700)
    if args.mode != "encrypted-volume":
        grader.mkdir(mode=0o700, exist_ok=True)
    marker = "oracle-" + secrets.token_hex(16)
    mounted = False
    device = None
    image = base / ("candidate.sparseimage" if args.mode == "candidate-volume" else "oracle.dmg")
    oracle = grader / "oracle.txt"
    checks = {}
    error = None
    cleanup_ok = True
    try:
        if args.mode == "candidate-volume":
            created = run(["hdiutil", "create", "-size", "64m", "-type", "SPARSE",
                           "-fs", "APFS", "-volname", "KRYNCandidateCanary", str(image)])
            if created.returncode:
                raise RuntimeError("Candidate image creation failed: " + created.stderr[:200])
            attached = run(["hdiutil", "attach", "-nobrowse", "-noverify",
                            "-mountpoint", str(mount), str(image)])
            if attached.returncode:
                raise RuntimeError("Candidate image mount failed: " + attached.stderr[:200])
            mounted = True
            devices = re.findall(r"/dev/disk\d+(?:s\d+)?", attached.stdout)
            device = devices[-1] if devices else None
            for directory in (workspace, private):
                directory.mkdir(mode=0o700)
        elif args.mode == "encrypted-volume":
            key = secrets.token_hex(32) + "\n"  # Never write to disk/env/argv.
            created = run(["hdiutil", "create", "-size", "16m", "-fs", "APFS",
                           "-volname", "KRYNHoldoutCanary", "-encryption", "AES-256",
                           "-stdinpass", str(image)], input=key)
            if created.returncode:
                raise RuntimeError("Encrypted image creation failed: " + created.stderr[:200])
            info = run(["hdiutil", "imageinfo", "-stdinpass", str(image)], input=key)
            if info.returncode or "Encrypted: true" not in info.stdout:
                raise RuntimeError("Could not verify image encryption")
            attached = run(["hdiutil", "attach", "-nobrowse", "-noverify",
                            "-stdinpass", "-mountpoint", str(grader), str(image)], input=key)
            if attached.returncode:
                raise RuntimeError("Encrypted image mount failed: " + attached.stderr[:200])
            mounted = True
            devices = re.findall(r"/dev/disk\d+(?:s\d+)?", attached.stdout)
            device = devices[-1] if devices else None
        (workspace / "visible.txt").write_text("candidate-visible")
        oracle.write_text(marker)
        checks = probe(workspace, private, oracle, image if mounted else None, device,
                       base if args.mode == "candidate-volume" else None,
                       args.mode == "same-volume")
        if mounted and all(checks.values()):
            checks.update(server_probe(workspace, base / "native.log", oracle, marker,
                                       private if args.mode == "candidate-volume" else None))
    except Exception as failure:
        error = type(failure).__name__ + ": " + str(failure)
    finally:
        if mount_active(base, mount):
            try:
                run(["hdiutil", "detach", str(mount)])
                cleanup_ok = not mount_active(base, mount)
            except Exception:
                cleanup_ok = False
            if not cleanup_ok:
                print("Mounted image could not be detached; inspect " + str(base), file=sys.stderr)
        if cleanup_ok and not mount_active(base, mount):
            shutil.rmtree(base)
    checks["oracle_detached"] = cleanup_ok
    if args.mode == "same-volume":
        control_exposed = (error is None and cleanup_ok and
                           checks.get("direct_read") is True and
                           checks.get("symlink_read") is True and
                           checks.get("hardlink_impossible") is False and
                           checks.get("hardlink_marker_read") is True)
    else:
        control_exposed = None
    passed = error is None and bool(checks) and all(checks.values())
    print(json.dumps({"mode": args.mode, "passed": passed, "checks": checks,
                      "negative_control_exposed": control_exposed,
                      "error": error}, sort_keys=True))
    if args.mode == "same-volume":
        return 1 if control_exposed else 2  # Distinguish expected exposure from a broken control.
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
