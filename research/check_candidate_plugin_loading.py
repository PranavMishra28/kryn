#!/usr/bin/env python3
"""No-model real OpenCode check for disposable candidate-plugin loading."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from native_client import NativeServer  # noqa: E402
from run_native_trial import plugin_active, plugin_absent  # noqa: E402
from agent_grade_barrier import create_volume, detach, image_entry  # noqa: E402
from run_external_patch import candidate_plugin_package, configuration  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def shell(server, workspace, command):
    response = server.request("POST", "/api/shell", {"command": command,
        "cwd": str(workspace), "timeout": 10000}, timeout=15)
    job = response.get("data", {})
    job_id = job.get("id")
    if not isinstance(job_id, str) or not job_id.startswith("sh_"):
        raise RuntimeError("OpenCode did not return a native shell job")
    endpoint = "/api/shell/" + urllib.parse.quote(job_id, safe="")
    try:
        deadline = time.monotonic() + 12
        while job.get("status") == "running" and time.monotonic() < deadline:
            time.sleep(.1)
            job = server.request("GET", endpoint, timeout=5).get("data", {})
        if job.get("status") != "exited" or type(job.get("exit")) is not int:
            raise RuntimeError("Native shell job did not settle")
        output = server.request("GET", endpoint + "/output?cursor=0&limit=4096",
                                timeout=5).get("data", {}).get("output", "")
        return job["exit"], output
    finally:
        server.request("DELETE", endpoint, timeout=5)


def arm_probe(arm, workspace, private, package, hidden, report):
    state = workspace / ".git" / ("candidate-loader-" + arm)
    state.mkdir(mode=0o700)
    config, products, dependencies = configuration(
        workspace, state, arm, "http://127.0.0.1:19876/v1",
        candidate_package=package if arm == "kryn" else None)
    server = NativeServer(workspace, config, report / (arm + "-server.log"),
                          background={"dependencies": dependencies,
                                      "inference_port": None,
                                      "private_parent": private})
    server.env["GIT_CONFIG_NOSYSTEM"] = "1"
    with server:
        server.inventory()
        for _ in range(75):
            inventory = server.request("GET", "/api/plugin", timeout=5)
            ready = (plugin_active(inventory, "kryn.product", package) if arm == "kryn"
                     else plugin_absent(inventory, "kryn.product"))
            if ready or any(item.get("state", {}).get("status") in {"failed", "error"}
                            for item in inventory.get("data", [])):
                break
            time.sleep(.2)
        visible = shell(server, workspace, "/bin/cat " + shlex.quote(str(workspace / "visible.txt")))
        secret = shell(server, workspace, "/bin/cat " + shlex.quote(str(hidden)))
        package_write = shell(server, workspace, "/usr/bin/touch " +
                              shlex.quote(str(package / "server.js"))) if arm == "kryn" else None
        return {"active": ready, "inventory_path": next(
                    (item.get("source", {}).get("path") for item in inventory.get("data", [])
                     if item.get("id") == "kryn.product"), None),
                "visible_read": visible == (0, "candidate-visible"),
                "hidden_read_denied": secret[0] != 0 and "hidden-marker" not in secret[1],
                "package_write_denied": package_write is None or package_write[0] != 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_source", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    source, root = args.candidate_source.resolve(), args.receipt.absolute()
    if (root.parent != Path("/private/tmp") or root.exists() or source != args.candidate_source or
            not source.is_dir()):
        parser.error("Use a canonical candidate source and fresh direct /private/tmp receipt")
    root.mkdir(mode=0o700)
    # Identify the installed product by its profileId, not by list position.
    config = json.loads((Path.home() / "Library/Application Support/LocalAI/xdg/config/opencode/opencode.json").read_text())
    installed = Path(next(item["package"] for item in config["plugins"]
                          if isinstance(item, dict) and "profileId" in item.get("options", {})))
    installed_before = sha(installed / "server.js")
    package, hashes = candidate_plugin_package(source, root)
    hidden = root / "hidden.txt"
    hidden.write_text("hidden-marker")
    hidden.chmod(0o600)
    volume = None
    result = {"schema": 1, "kind": "candidate_plugin_loader_no_model",
              "candidate_source_commit": subprocess.check_output(
                  ["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip(),
              "candidate_hashes": hashes, "installed_server_sha256": installed_before,
              "arms": {}, "detached": False, "passed": False}
    try:
        volume = create_volume(root, "candidate")
        workspace, private = volume.mount / "workspace", volume.mount / "private"
        workspace.mkdir(mode=0o700)
        private.mkdir(mode=0o700)
        (workspace / "visible.txt").write_text("candidate-visible")
        subprocess.run(["/Library/Developer/CommandLineTools/usr/bin/git", "init", "-q",
                        str(workspace)], check=True)
        for arm in ("kryn", "native"):
            result["arms"][arm] = arm_probe(arm, workspace, private, package, hidden, root)
    except BaseException as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if volume is not None:
            try:
                detach(volume)
                result["detached"] = image_entry(volume.image) is None
            except BaseException as error:
                result["detach_error"] = type(error).__name__ + ": " + str(error)
        result["installed_unchanged"] = sha(installed / "server.js") == installed_before
        result["candidate_unchanged"] = all(sha(package / name) == digest
                                            for name, digest in hashes.items())
        result["passed"] = (result["detached"] and result["installed_unchanged"] and
                            result["candidate_unchanged"] and
                            all(all(value for key, value in checks.items() if key != "inventory_path")
                                for checks in result["arms"].values()) and
                            set(result["arms"]) == {"kryn", "native"} and
                            result["arms"]["kryn"]["inventory_path"] == str(package / "server.js"))
        (root / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "arms": result["arms"],
                      "detached": result["detached"], "error": result.get("error")}, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
