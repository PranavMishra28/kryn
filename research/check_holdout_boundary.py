#!/usr/bin/env python3
"""No-model alias canary for the actual whole-process research sandbox.

The same-volume control must fail; the encrypted-volume case must pass. A
passing canary is not a qualified protected holdout or a full agent run.
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
import subprocess
import sys
import tempfile
import time
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from native_client import NativeServer, background_boundary
from run_external_patch import configuration

ROOT = Path("/private/tmp")


def run(command, *, input=None):
    return subprocess.run(command, input=input, text=True, capture_output=True,
                          timeout=20, close_fds=True)


def probe(workspace, private, oracle, image=None, device=None):
    marker = oracle.read_text()
    alias = workspace / "oracle-symlink"
    alias.symlink_to(oracle)
    prefix = background_boundary(workspace, private, [], None)
    if "(deny file-read*)" not in prefix[2]:
        raise RuntimeError("Research sandbox does not deny file-read metadata")

    def denied(name, command):
        result = run(prefix + command)
        return name, result.returncode != 0 and marker not in result.stdout + result.stderr

    visible_result = run(prefix + ["/bin/cat", str(workspace / "visible.txt")])
    checks = dict([
        denied("direct_read", ["/bin/cat", str(oracle)]),
        denied("symlink_read", ["/bin/cat", str(alias)]),
        denied("copy_read", ["/bin/cp", str(oracle), str(workspace / "copied")]),
        denied("metadata_read", ["/usr/bin/stat", str(oracle)]),
        denied("file_url_read", ["/usr/bin/curl", "-sS", "file://" + str(oracle)]),
        denied("ancestor_listing_denied", ["/bin/ls", "-a", str(workspace.parent)]),
    ])
    # The visible file is required to work; all hidden-file probes must fail.
    checks["workspace_read"] = (visible_result.returncode == 0
                                and visible_result.stdout == "candidate-visible")
    checks["different_filesystem"] = os.stat(workspace).st_dev != os.stat(oracle).st_dev

    hardlink = workspace / "oracle-hardlink"
    try:
        os.link(oracle, hardlink)  # Trusted parent simulates a pre-existing alias.
        checks["hardlink_impossible"] = False
        checks["hardlink_read_denied"] = denied("hardlink_read_denied", ["/bin/cat", str(hardlink)])[1]
    except OSError as error:
        checks["hardlink_impossible"] = error.errno == errno.EXDEV
        checks["hardlink_read_denied"] = True  # There is no alias to read.
    checks["candidate_link_denied"] = denied("candidate_link_denied",
        ["/bin/ln", str(oracle), str(workspace / "candidate-hardlink")])[1]
    if image is not None:
        checks["backing_image_read_denied"] = denied("backing_image_read_denied",
            ["/bin/cat", str(image)])[1]
        checks["raw_device_read_denied"] = bool(device and Path(device).exists() and
            denied("raw_device_read_denied",
                   ["/bin/dd", "if=" + device, "of=/dev/null", "bs=16", "count=1"])[1])
    return checks


def server_probe(workspace, log, oracle, marker):
    # Use the same product configuration and dependency builder as the external
    # candidate runner. API inventory initializes plugins without inference.
    subprocess.run(["/usr/bin/git", "init", "-q", str(workspace)], check=True,
                   capture_output=True, timeout=10)
    state = workspace / ".git" / "kryn-boundary-canary"
    state.mkdir(mode=0o700)
    config, products, dependencies = configuration(
        workspace, state, "kryn", "http://127.0.0.1:19876/v1")

    def shell(server, argv):
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
            if info.get("status") == "running":
                raise RuntimeError("Native shell canary did not settle")
            output = server.request("GET", endpoint + "/output?cursor=0&limit=4096",
                                    timeout=5).get("data", {})
            return info.get("exit"), output.get("output", "")
        finally:
            server.request("DELETE", endpoint, timeout=5)

    with NativeServer(workspace, config, log=log,
                      background={"dependencies": dependencies,
                                  "inference_port": 19876}) as server:
        server.inventory()
        for domain in ("config", "agent", "command", "skill"):
            server.request("GET", "/api/" + domain, timeout=5)
        plugins = server.request("GET", "/api/plugin", timeout=5).get("data", [])
        product = [entry for entry in plugins if entry.get("id") == "kryn.product"]
        raw = run(server.background_prefix + ["/bin/cat", str(oracle)])
        visible_exit, visible_output = shell(server, ["/bin/cat", workspace / "visible.txt"])
        hidden_exit, hidden_output = shell(server, ["/bin/cat", oracle])
        python_exit, python_output = shell(server, ["python3", "-c", "print('python-ready')"])
        return {
            "native_server_started": True,
            "product_plugin_active": len(products) == 1 and len(product) == 1
                and product[0].get("state", {}).get("status") == "active",
            "server_profile_oracle_read_denied": raw.returncode != 0
                and marker not in raw.stdout + raw.stderr,
            "api_shell_workspace_read": visible_exit == 0
                and visible_output == "candidate-visible",
            "api_shell_oracle_read_denied": hidden_exit != 0
                and marker not in hidden_output,
            "api_shell_python_ready": python_exit == 0
                and python_output == "python-ready\n",
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("same-volume", "encrypted-volume"),
                        help="same-volume is the expected failing hardlink control")
    args = parser.parse_args()
    ROOT.mkdir(mode=0o700, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="kryn-holdout-boundary-", dir=ROOT))
    workspace, private, grader = (base / name for name in ("workspace", "private", "grader"))
    for directory in (workspace, private, grader):
        directory.mkdir(mode=0o700)
    (workspace / "visible.txt").write_text("candidate-visible")
    marker = "oracle-" + secrets.token_hex(16)
    mounted = False
    device = None
    image = base / "oracle.dmg"
    oracle = grader / "oracle.txt"
    checks = {}
    error = None
    cleanup_ok = True
    try:
        if args.mode == "encrypted-volume":
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
        oracle.write_text(marker)
        checks = probe(workspace, private, oracle, image if mounted else None, device)
        if mounted and all(checks.values()):
            checks.update(server_probe(workspace, base / "native.log", oracle, marker))
    except Exception as failure:
        error = type(failure).__name__ + ": " + str(failure)
    finally:
        if mounted:
            try:
                detached = run(["hdiutil", "detach", str(grader)])
                cleanup_ok = detached.returncode == 0
            except Exception:
                cleanup_ok = False
            if not cleanup_ok:
                print("Mounted image could not be detached; inspect " + str(base), file=sys.stderr)
        if cleanup_ok:
            shutil.rmtree(base)
    checks["oracle_detached"] = cleanup_ok
    passed = error is None and bool(checks) and all(checks.values())
    print(json.dumps({"mode": args.mode, "passed": passed, "checks": checks,
                      "error": error}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
