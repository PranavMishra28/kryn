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
import traceback

RESEARCH = Path(__file__).resolve().parents[1]
ROOT = RESEARCH.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(Path(__file__).parent))
from native_client import NativeServer, background_boundary  # noqa: E402
from run_external_patch import configuration  # noqa: E402
from broker import verify_boundary  # noqa: E402
from trial_config import TOOLS, with_ui_gateway  # noqa: E402

URL = "http://candidate.invalid/index.html"
ADAPTER = Path(__file__).with_name("adapter.py").resolve()
PYTHON = Path(sys.executable).resolve()


def command(argv, **kwargs):
    return subprocess.run(argv, capture_output=True, text=True, timeout=20, **kwargs)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stop_group(child):
    try:
        if child.poll() is None:
            child.terminate()
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if child.poll() is None:
            try:
                child.kill()
            except ProcessLookupError:
                pass
        child.wait(timeout=5)


def broker_start(image, repo, script=None, timeout=20):
    child = subprocess.Popen([str(PYTHON), "-B", str(script or Path(__file__).with_name("broker.py")),
                              "--image", image, "--repo", str(repo), "--lifetime", "300"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True)
    try:
        fd = child.stdout.fileno()
        os.set_blocking(fd, False)
        deadline = time.monotonic() + timeout
        line = bytearray()
        while b"\n" not in line:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
                raise TimeoutError("UI broker startup deadline")
            chunk = os.read(fd, 4097 - len(line))
            if not chunk:
                raise RuntimeError("UI broker exited during startup")
            line.extend(chunk)
            if len(line) > 4096:
                raise RuntimeError("UI broker startup response limit")
        return child, json.loads(bytes(line).split(b"\n", 1)[0])
    except BaseException:
        stop_group(child)
        raise


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


def port_validation(workspace, private, inference_port, broker_port):
    malformed = ((0, 0, None), (True, 0, None), ("8000", 0, None),
                 (inference_port, None, None), (inference_port, True, None),
                 (inference_port, 0, 0), (inference_port, 0, True),
                 (inference_port, 0, "8000"),
                 (inference_port, 0, 65536),
                 (inference_port, inference_port, None),
                 (inference_port, 0, inference_port),
                 (inference_port, broker_port, broker_port))
    for inference, native, broker in malformed:
        try:
            background_boundary(workspace, private, [], inference, native, broker_port=broker)
        except RuntimeError:
            continue
        return False
    legacy = background_boundary(workspace, private, [], inference_port)[2]
    return (legacy.count("(allow network-outbound") == 1 and
            '(allow network-outbound (remote ip "localhost:' + str(inference_port) + '"))' in legacy)


def native_catalog(workspace, private, inference_port, broker, report):
    catalogs = {}
    configurations = {}
    profiles = {}
    for arm in ("native", "kryn"):
        state = workspace / ".git" / ("ui-preflight-" + arm)
        state.mkdir(mode=0o700, exist_ok=True)
        config, _, dependencies = configuration(
            workspace, state, arm, "http://127.0.0.1:" + str(inference_port) + "/v1")
        config = with_ui_gateway(config, python=PYTHON, adapter=ADAPTER, repo=workspace,
                                 port=broker["port"], token=broker["token"])
        if set(config["mcp"]["servers"]) != {"browser"}:
            raise RuntimeError("source MCP survived UI trial configuration")
        dependencies += [PYTHON, Path(sys.base_prefix).resolve(), ADAPTER]
        configurations[arm] = {
            **{key: config[key] for key in ("mcp", "permissions")},
            "agent_permissions": {name: agent.get("permissions", [])
                                  for name, agent in config.get("agents", {}).items()},
        }
        with NativeServer(workspace, config, workspace.parent.parent / (arm + "-native.log"),
                          background={"dependencies": dependencies,
                                      "inference_port": inference_port,
                                      "broker_port": broker["port"],
                                      "private_parent": private}) as server:
            profile = server.background_prefix[2]
            outbound = sorted(line.strip() for line in profile.splitlines()
                              if line.strip().startswith("(allow network-outbound "))
            expected = sorted('(allow network-outbound (remote ip "localhost:' + str(port) + '"))'
                              for port in (inference_port, server.port, broker["port"]))
            profiles[arm] = (outbound == expected and
                             '(allow network-inbound (local ip "localhost:' + str(server.port) + '"))' in profile)
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
    report["checks"]["three_port_profiles_exact"] = all(profiles.values())
    report["mcp_status"] = catalogs
    report["opencode_tool_catalog_unverified"] = True
    return (report["paired_mcp_and_permissions_equal"] and report["paired_mcp_status_equal"]
            and report["checks"]["three_port_profiles_exact"])


def main(draft, image, output):
    output = Path(output).absolute()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    mount = output / "mount"
    mount.mkdir(mode=0o700)
    disk = output / "candidate.sparseimage"
    report = {"schema": 1, "scope": "no-model UI 01 gateway preflight",
              "protected_eligible": False, "model_gateway_qualified": False,
              "port_substitution": "distinct dummy inference and live browser broker ports; no model calls",
              "browser_image": image, "adapter_sha256": digest(ADAPTER),
              "broker_sha256": digest(Path(__file__).with_name("broker.py")),
              "native_client_sha256": digest(ROOT / "tools/native_client.py"),
              "preflight_sha256": digest(__file__),
              "worker_sha256": digest(Path(__file__).with_name("worker.js")),
              "checks": {}, "passed": False}
    mounted = False
    broker_child = None
    broker = None
    inference_server = None
    inference_thread = None
    inference_hits = []
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
        original = (workspace / "index.html").read_bytes()
        class InferenceHandler(BaseHTTPRequestHandler):
            def respond(self):
                inference_hits.append((self.command, self.path))
                self.send_response(204 if (self.command, self.path) == ("GET", "/probe") else 503)
                self.end_headers()
            do_GET = respond
            do_POST = respond
            def log_message(self, *_args):
                pass
        inference_server = ThreadingHTTPServer(("127.0.0.1", 0), InferenceHandler)
        inference_thread = Thread(target=inference_server.serve_forever, daemon=True)
        inference_thread.start()
        inference_port = inference_server.server_address[1]
        broker_child, broker = broker_start(image, workspace)
        report["container"] = broker["container"]
        report["container_boundary"] = broker["boundary"]
        report["dummy_inference_port"] = inference_port
        report["broker_port"] = broker["port"]
        report["checks"]["distinct_inference_and_broker_ports"] = inference_port != broker["port"]
        report["checks"]["port_validation"] = port_validation(workspace, private, inference_port, broker["port"])
        seed_head = json.loads((Path(draft).resolve() / "bundles/01-harbor-tabs/manifest.json").read_text())["base_commit"]
        current_head = command(["git", "-C", str(workspace), "rev-parse", "HEAD"])
        current_status = command(["git", "-C", str(workspace), "status", "--porcelain"])
        report["checks"]["seed_state_at_opencode_start"] = (
            current_head.returncode == 0 and current_head.stdout.strip() == seed_head and
            current_status.returncode == 0 and current_status.stdout.strip() == "" and
            (workspace / "index.html").read_bytes() == original)
        if not report["checks"]["seed_state_at_opencode_start"]:
            raise RuntimeError("candidate checkout differs from clean seed at OpenCode startup")
        report["checks"]["paired_opencode_mcp"] = native_catalog(workspace, private, inference_port, broker, report)
        report["checks"]["browser_blank_after_opencode_start"] = (
            broker_request(broker, {"token": broker["token"], "op": "snapshot"}).get("error") == "PAGE_NOT_OPEN")
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
        actual_inspect = command(["docker", "inspect", broker["container"]])
        if actual_inspect.returncode:
            raise RuntimeError("UI browser container inspect failed")
        inspected = json.loads(actual_inspect.stdout)[0]
        report["checks"]["container_attestation"] = verify_boundary(inspected, image) == broker["boundary"]
        mutants_rejected = []
        for section, field, value in (("HostConfig", "PidsLimit", 0),
                                      ("HostConfig", "Memory", 0),
                                      ("Config", "User", "0:0")):
            mutant = json.loads(json.dumps(inspected))
            mutant[section][field] = value
            try:
                verify_boundary(mutant, image)
            except RuntimeError:
                mutants_rejected.append(True)
            else:
                mutants_rejected.append(False)
        report["checks"]["zero_limits_and_root_rejected"] = all(mutants_rejected)
        escape_mutants = []
        for field, value in (("PidMode", "host"), ("IpcMode", "host"),
                             ("CgroupnsMode", "host"), ("Devices", [{"PathOnHost": "/dev/disk0"}]),
                             ("DeviceRequests", [{"Driver": "nvidia"}]),
                             ("CapAdd", ["SYS_ADMIN"]), ("Binds", ["/:/host:ro"]),
                             ("SecurityOpt", ["no-new-privileges", "seccomp=unconfined"])):
            mutant = json.loads(json.dumps(inspected))
            mutant["HostConfig"][field] = value
            try:
                verify_boundary(mutant, image)
            except RuntimeError:
                escape_mutants.append(True)
            else:
                escape_mutants.append(False)
        report["checks"]["container_escape_mutants_rejected"] = all(escape_mutants)
        network_mutant = json.loads(json.dumps(inspected))
        network_mutant["NetworkSettings"]["Networks"] = {"bridge": {}}
        try:
            verify_boundary(network_mutant, image)
        except RuntimeError:
            report["checks"]["attached_network_rejected"] = True
        else:
            report["checks"]["attached_network_rejected"] = False
        stall = output / "stalled-broker.py"
        stall_pid = output / "stalled-broker.pid"
        stall.write_text("import os, time\n"
                         "open(" + repr(str(stall_pid)) + ", 'w').write(str(os.getpid()))\n"
                         "print('partial', end='', flush=True)\n"
                         "time.sleep(60)\n")
        try:
            broker_start(image, workspace, script=stall, timeout=.3)
            report["checks"]["startup_timeout_reaps_child"] = False
        except TimeoutError:
            pid = int(stall_pid.read_text())
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                report["checks"]["startup_timeout_reaps_child"] = True
            else:
                report["checks"]["startup_timeout_reaps_child"] = False
        prefix = background_boundary(workspace, private,
            [PYTHON, Path(sys.base_prefix).resolve(), ADAPTER], inference_port,
            broker_port=broker["port"])
        probe = ("import socket, sys\n"
                 "try:\n"
                 "    with socket.create_connection(('127.0.0.1', int(sys.argv[1])), timeout=3) as s:\n"
                 "        s.sendall(b'GET /probe HTTP/1.0\\r\\nHost: 127.0.0.1\\r\\n\\r\\n')\n"
                 "        print(s.recv(128).split(b'\\r\\n', 1)[0].decode())\n"
                 "except OSError as e:\n"
                 "    print(type(e).__name__)\n"
                 "    sys.exit(3)\n")
        allowed = command(prefix + [str(PYTHON), "-B", "-c", probe, str(inference_port)])
        report["dummy_probe_detail"] = {"exit": allowed.returncode, "stdout": allowed.stdout[:200],
                                        "stderr": allowed.stderr[:200]}
        report["checks"]["dummy_inference_port_reachable"] = (
            allowed.returncode == 0 and allowed.stdout.strip() == "HTTP/1.0 204 No Content" and
            ("GET", "/probe") in inference_hits)
        blocked_hits = []
        class BlockedHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                blocked_hits.append(self.path)
                self.send_response(204)
                self.end_headers()
            def log_message(self, *_args):
                pass
        blocked_server = ThreadingHTTPServer(("127.0.0.1", 0), BlockedHandler)
        blocked_thread = Thread(target=blocked_server.serve_forever, daemon=True)
        blocked_thread.start()
        try:
            blocked = command(prefix + [str(PYTHON), "-B", "-c", probe,
                                        str(blocked_server.server_address[1])])
            report["checks"]["unlisted_loopback_port_denied"] = (
                blocked.returncode == 3 and blocked.stdout.strip() == "PermissionError" and not blocked_hits)
        finally:
            blocked_server.shutdown()
            blocked_server.server_close()
            blocked_thread.join(timeout=3)
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
            broker_request(broker, {"token": broker["token"], "op": "open", "path": str(hidden)}).get("error") == "DENIED" and
            broker_request(broker, {"token": broker["token"], "op": "open",
                                    "html_b64": base64.b64encode(b"<p>forged answer</p>").decode()}).get("error") == "DENIED" and
            "Harbor accounts" in broker_request(broker, {"token": broker["token"], "op": "open"}).get("text", ""))
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
        (workspace / "index.html").write_bytes(original)
        (workspace / "answer-link").unlink()
        reset = mcp(prefix, workspace, broker, [tool("browser_navigate", {"url": URL})])
        current_head = command(["git", "-C", str(workspace), "rev-parse", "HEAD"])
        current_status = command(["git", "-C", str(workspace), "status", "--porcelain"])
        report["checks"]["seed_restored_after_reference"] = (
            current_head.returncode == 0 and current_head.stdout.strip() == seed_head and
            current_status.returncode == 0 and current_status.stdout.strip() == "" and
            (workspace / "index.html").read_bytes() == original and text(reset[0]) == text(result[2]))
        report["dummy_inference_hits"] = inference_hits
        report["checks"]["dummy_inference_probe_only"] = inference_hits == [("GET", "/probe")]
        report["passed"] = all(report["checks"].values())
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        report["error_traceback"] = traceback.format_exc(limit=6)
    finally:
        if inference_server is not None:
            inference_server.shutdown()
            inference_server.server_close()
            inference_thread.join(timeout=3)
        if broker_child is not None:
            stop_group(broker_child)
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
