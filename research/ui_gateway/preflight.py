#!/usr/bin/env python3
"""No-model UI 01 browser and OpenCode MCP boundary preflight on a candidate volume."""
import argparse
import base64
import errno
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import select
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
from threading import Thread
import time

RESEARCH = Path(__file__).resolve().parents[1]
ROOT = RESEARCH.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(Path(__file__).parent))
from native_client import NativeServer, background_boundary  # noqa: E402
from run_external_patch import configuration  # noqa: E402
from trial_config import TOOLS, with_ui_gateway  # noqa: E402

URL = "http://candidate.invalid/index.html"
ADAPTER = Path(__file__).with_name("adapter.py").resolve()
PYTHON = Path(sys.executable).resolve()


def command(argv, **kwargs):
    return subprocess.run(argv, capture_output=True, text=True, timeout=20, **kwargs)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def broker_start(image):
    child = subprocess.Popen([str(PYTHON), "-B", str(Path(__file__).with_name("broker.py")),
                              "--image", image, "--lifetime", "300"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True)
    if not select.select([child.stdout], [], [], 20)[0]:
        raise RuntimeError("UI broker did not start")
    line = child.stdout.readline()
    if not line:
        raise RuntimeError("UI broker exited: " + child.stderr.read(500).decode(errors="replace"))
    return child, json.loads(line)


def mcp(prefix, repo, broker, calls):
    argv = [*prefix, str(PYTHON), "-B", str(ADAPTER), "--repo", str(repo),
            "--port", str(broker["port"]), "--token", broker["token"]]
    payload = "".join(json.dumps({"jsonrpc": "2.0", "id": index,
                                   "method": method, "params": params}) + "\n"
                      for index, (method, params) in enumerate(calls, 1))
    done = subprocess.run(argv, input=payload, capture_output=True, text=True,
                          cwd=repo, timeout=25)
    if done.returncode or len(done.stdout) > 3_500_000:
        raise RuntimeError("sandboxed MCP adapter failed: " + done.stderr[-300:])
    results = [json.loads(line) for line in done.stdout.splitlines()]
    if len(results) != len(calls):
        raise RuntimeError("sandboxed MCP adapter lost a response")
    return [item.get("result", item.get("error")) for item in results]


def tool(name, arguments=None):
    return "tools/call", {"name": name, "arguments": arguments if arguments is not None else {}}


def text(result):
    return result.get("content", [{}])[0].get("text", "")


def broker_request(info, message):
    with socket.create_connection(("127.0.0.1", info["port"]), timeout=3) as connection:
        connection.settimeout(3)
        connection.sendall((json.dumps(message) + "\n").encode())
        output = b""
        while b"\n" not in output:
            output += connection.recv(65536)
        return json.loads(output.split(b"\n", 1)[0])


def native_catalog(workspace, private, broker, report):
    catalogs = {}
    configurations = {}
    for arm in ("native", "kryn"):
        state = workspace / ".git" / ("ui-preflight-" + arm)
        state.mkdir(mode=0o700, exist_ok=True)
        config, _, dependencies = configuration(
            workspace, state, arm, "http://127.0.0.1:" + str(broker["port"]) + "/v1")
        config = with_ui_gateway(config, python=PYTHON, adapter=ADAPTER, repo=workspace,
                                 port=broker["port"], token=broker["token"])
        if set(config["mcp"]["servers"]) != {"browser"}:
            raise RuntimeError("source MCP survived UI trial configuration")
        dependencies += [PYTHON, Path(sys.base_prefix).resolve(), ADAPTER]
        configurations[arm] = {key: config[key] for key in ("mcp", "permissions")}
        with NativeServer(workspace, config, workspace.parent.parent / (arm + "-native.log"),
                          background={"dependencies": dependencies,
                                      "inference_port": broker["port"],
                                      "private_parent": private}) as server:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                items = server.request("GET", "/api/mcp", timeout=5).get("data", [])
                if any(item.get("name") == "browser" and
                       item.get("status", {}).get("status") == "connected" for item in items):
                    break
                time.sleep(.3)
            else:
                raise RuntimeError(arm + " OpenCode browser MCP did not connect")
            catalogs[arm] = sorted((item["name"], item["status"]["status"])
                                   for item in items)
    report["paired_mcp_and_permissions_equal"] = configurations["native"] == configurations["kryn"]
    report["paired_mcp_status_equal"] = catalogs["native"] == catalogs["kryn"]
    report["mcp_status"] = catalogs
    report["opencode_tool_catalog_unverified"] = True
    return report["paired_mcp_and_permissions_equal"] and report["paired_mcp_status_equal"]


def main(draft, image, output):
    output = Path(output).absolute()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    mount = output / "mount"
    mount.mkdir(mode=0o700)
    disk = output / "candidate.sparseimage"
    report = {"schema": 1, "scope": "no-model UI 01 gateway preflight",
              "protected_eligible": False, "model_gateway_qualified": False,
              "port_substitution": "broker occupied the inference-only port for this no-model startup probe",
              "browser_image": image, "adapter_sha256": digest(ADAPTER),
              "broker_sha256": digest(Path(__file__).with_name("broker.py")),
              "worker_sha256": digest(Path(__file__).with_name("worker.js")),
              "checks": {}, "passed": False}
    mounted = False
    broker_child = None
    broker = None
    try:
        created = command(["hdiutil", "create", "-size", "128m", "-type", "SPARSE",
                           "-fs", "APFS", "-volname", "KRYNUICandidate", str(disk)])
        if created.returncode:
            raise RuntimeError("candidate image create failed: " + created.stderr[-300:])
        attached = command(["hdiutil", "attach", "-nobrowse", "-noverify",
                            "-mountpoint", str(mount), str(disk)])
        if attached.returncode or mount.stat().st_dev == output.stat().st_dev:
            raise RuntimeError("candidate volume attach failed: " + attached.stderr[-300:])
        mounted = True
        workspace = mount / "workspace"
        private = mount / "private"
        private.mkdir(mode=0o700)
        seed = Path(draft).resolve() / "bundles/01-harbor-tabs/repo"
        cloned = command(["git", "clone", "--no-hardlinks", "-q", str(seed), str(workspace)])
        if cloned.returncode:
            raise RuntimeError("seed clone failed: " + cloned.stderr[-300:])
        command(["git", "-C", str(workspace), "remote", "remove", "origin"])
        hidden = output / "hidden-canary.txt"
        marker = "KRYN-UI-HIDDEN-" + os.urandom(12).hex()
        hidden.write_text(marker)
        report["checks"]["different_device"] = workspace.stat().st_dev != hidden.stat().st_dev
        try:
            os.link(hidden, workspace / "answer-hardlink")
            report["checks"]["hardlink_impossible"] = False
        except OSError as error:
            report["checks"]["hardlink_impossible"] = error.errno == errno.EXDEV
        (workspace / "answer-link").symlink_to(hidden)
        broker_child, broker = broker_start(image)
        report["container"] = broker["container"]
        report["container_boundary"] = broker["boundary"]
        prefix = background_boundary(workspace, private,
            [PYTHON, Path(sys.base_prefix).resolve(), ADAPTER], broker["port"])
        for label, argv in (("hidden_read_denied", ["/bin/cat", str(hidden)]),
                            ("hidden_stat_denied", ["/usr/bin/stat", str(hidden)]),
                            ("symlink_read_denied", ["/bin/cat", str(workspace / "answer-link")])):
            attempt = command(prefix + argv)
            report["checks"][label] = attempt.returncode != 0 and marker not in attempt.stdout + attempt.stderr
        calls = [("initialize", {}), ("tools/list", {}), tool("browser_navigate", {"url": URL}),
                 tool("browser_click", {"selector": '[data-tab="activity"]'}),
                 tool("browser_snapshot"), tool("browser_take_screenshot")]
        result = mcp(prefix, workspace, broker, calls)
        listed = [item["name"] for item in result[1]["tools"]]
        report["checks"]["catalog_exact"] = listed == list(TOOLS)
        report["checks"]["public_page_visible"] = "Harbor accounts" in text(result[2]) and "Recent activity: 3 items" in text(result[3])
        report["checks"]["screenshot_bounded"] = (result[5].get("content", [{}])[0].get("type") == "image" and
            len(result[5]["content"][0]["data"]) < 2_800_000)
        report["checks"]["hidden_absent_in_browser"] = marker not in json.dumps(result)
        denied = mcp(prefix, workspace, broker,
                     [tool("browser_navigate", {"url": hidden.as_uri()}),
                      tool("browser_navigate", {"url": "http://127.0.0.1:1/"}),
                      tool("browser_run_code_unsafe", {"code": "1+1"})])
        report["checks"]["url_and_code_denied"] = all(item.get("isError") is True for item in denied)
        report["checks"]["direct_broker_denied"] = (
            broker_request(broker, {"token": "0" * 48, "op": "snapshot"}).get("error") == "DENIED" and
            broker_request(broker, {"token": broker["token"], "op": "open", "path": str(hidden)}).get("error") == "DENIED")
        original = (workspace / "index.html").read_bytes()
        hits = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                self.send_response(204)
                self.end_headers()
            def log_message(self, *_args):
                pass
        listener = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        listener_thread = Thread(target=listener.serve_forever, daemon=True)
        listener_thread.start()
        try:
            attempted_url = "http://127.0.0.1:" + str(listener.server_address[1]) + "/attempt"
            page = ("<!doctype html><title>boundary canary</title><p>public only</p><script>"
                    "fetch(" + json.dumps(hidden.as_uri()) + ").then(r=>r.text()).then(x=>document.body.append(x)).catch(()=>{});"
                    "fetch(" + json.dumps(attempted_url) + ").catch(()=>{});"
                    "const f=document.createElement('iframe');f.src=" + json.dumps(hidden.as_uri()) + ";document.body.append(f);"
                    "window.open(" + json.dumps(hidden.as_uri()) + ");</script>")
            (workspace / "index.html").write_text(page)
            adversarial = mcp(prefix, workspace, broker, [tool("browser_navigate", {"url": URL}),
                                                         tool("browser_snapshot")])
            time.sleep(.5)
            report["checks"]["page_file_and_network_denied"] = (
                marker not in json.dumps(adversarial) and not any(path.startswith("/attempt") for path in hits))
            from urllib.request import urlopen
            with urlopen(attempted_url.replace("/attempt", "/control"), timeout=3) as response:
                report["checks"]["egress_listener_live"] = response.status == 204 and "/control" in hits
        finally:
            listener.shutdown()
            listener.server_close()
            listener_thread.join(timeout=3)
        (workspace / "index.html").write_bytes(original)
        mcp(prefix, workspace, broker, [tool("browser_navigate", {"url": URL}),
                                      tool("browser_click", {"selector": '[data-tab="activity"]'})])
        (workspace / "index.html").unlink()
        (workspace / "index.html").symlink_to(hidden)
        swapped = mcp(prefix, workspace, broker, [tool("browser_navigate", {"url": URL}), tool("browser_snapshot")])
        report["checks"]["symlink_swap_rejected"] = swapped[0].get("isError") is True and marker not in json.dumps(swapped) and "Recent activity" in text(swapped[1])
        (workspace / "index.html").unlink()
        fifo = workspace / "index.html"
        os.mkfifo(fifo)
        start = time.monotonic()
        rejected = mcp(prefix, workspace, broker, [tool("browser_navigate", {"url": URL})])
        report["checks"]["fifo_rejected_fast"] = rejected[0].get("isError") is True and time.monotonic() - start < 5
        fifo.unlink()
        (workspace / "index.html").write_bytes(b"x" * (1024 * 1024 + 1))
        rejected = mcp(prefix, workspace, broker, [tool("browser_navigate", {"url": URL})])
        report["checks"]["oversize_rejected"] = rejected[0].get("isError") is True
        (workspace / "index.html").write_bytes(original)
        reference = Path(draft).resolve() / "validation/01-harbor-tabs/reference/index.html"
        (workspace / "index.html").write_bytes(reference.read_bytes())
        verified = mcp(prefix, workspace, broker, [tool("browser_navigate", {"url": URL}),
            tool("browser_click", {"selector": '#tab-overview'}), tool("browser_press_key", {"key": "ArrowRight"})])
        report["checks"]["reference_keyboard_browser"] = 'tab "Activity" [selected]' in text(verified[2])
        report["checks"]["paired_opencode_mcp"] = native_catalog(workspace, private, broker, report)
        report["passed"] = all(report["checks"].values())
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if broker_child is not None:
            try:
                if broker_child.poll() is None:
                    os.killpg(broker_child.pid, signal.SIGTERM)
                broker_child.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(broker_child.pid, signal.SIGKILL)
                    broker_child.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            try:
                report["checks"]["container_cleaned"] = (broker is not None and command(
                    ["docker", "ps", "-a", "--filter", "name=" + broker["container"],
                     "--format", "{{.Names}}"]).stdout.strip() == "")
            except (OSError, subprocess.TimeoutExpired):
                report["checks"]["container_cleaned"] = False
        if mounted:
            try:
                detached = command(["hdiutil", "detach", str(mount)])
                report["checks"]["volume_detached"] = (detached.returncode == 0 and
                    mount.stat().st_dev == output.stat().st_dev)
            except (OSError, subprocess.TimeoutExpired):
                report["checks"]["volume_detached"] = False
        report["passed"] = report["passed"] and all(report["checks"].values())
        (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.draft, args.image, args.output))
