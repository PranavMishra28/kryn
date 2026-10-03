#!/usr/bin/env python3
"""No-model OpenCode shell canaries for the research Agent-to-grader volume barrier.

No session or inference endpoint is invoked. Retain the receipt on failure.
"""
import errno
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from native_client import NativeServer

from agent_grade_barrier import BarrierError, attach, create_volume, detach, image_entry
from run_external_patch import configuration
from run_native_trial import plugin_absent


def policy_ready(server):
    for _ in range(75):
        inventory = server.request("GET", "/api/plugin", timeout=5)
        entries = inventory.get("data", [])
        policy = any(item.get("id") == "opencode.config.policy" and
                     item.get("state", {}).get("status") == "active" for item in entries)
        if policy and plugin_absent(inventory, "kryn.product"):
            return
        if any(item.get("state", {}).get("status") in {"failed", "error"}
               for item in entries):
            break
        time.sleep(.2)
    raise RuntimeError("No-model OpenCode policy/native arm did not become ready")


def shell_child(server, workspace, source, *args):
    launch = ("import subprocess,sys; p=subprocess.Popen("
              "[sys.argv[1],'-c',sys.argv[2],*sys.argv[3:]],"
              "cwd='/',stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
              "stderr=subprocess.DEVNULL,close_fds=True,start_new_session=True);"
              "print(p.pid,flush=True)")
    command = shlex.join(["python3", "-c", launch, str(Path(sys.executable).resolve()),
                           source, *map(str, args)])
    response = server.request("POST", "/api/shell", {
        "command": command, "cwd": str(workspace), "timeout": 10000}, timeout=15)
    info = response.get("data", {})
    identity = info.get("id")
    if not isinstance(identity, str) or not identity.startswith("sh_"):
        raise RuntimeError("OpenCode shell child has no owned identity")
    endpoint = "/api/shell/" + urllib.parse.quote(identity, safe="")
    try:
        deadline = time.monotonic() + 15
        while info.get("status") == "running" and time.monotonic() < deadline:
            time.sleep(.1)
            info = server.request("GET", endpoint, timeout=5).get("data", {})
        if info.get("status") != "exited" or info.get("exit") != 0:
            output = server.request("GET", endpoint + "/output?cursor=0&limit=4096",
                                    timeout=5).get("data", {})
            raise RuntimeError("OpenCode shell launcher did not exit cleanly: " +
                               repr((info.get("status"), info.get("exit"), output.get("output"))))
        while time.monotonic() < deadline:
            output = server.request("GET", endpoint + "/output?cursor=0&limit=128",
                                    timeout=5).get("data", {})
            data = output.get("output", "")
            if data.endswith("\n") and data[:-1].isdigit():
                return int(data[:-1])
            time.sleep(.1)
        raise RuntimeError("OpenCode shell launcher did not report the child PID")
    finally:
        server.request("DELETE", endpoint, timeout=5)


def server_for(volume, receipt, inference_port):
    workspace = volume.mount / "workspace"
    workspace.mkdir(mode=0o700)
    private = volume.mount / "private"
    private.mkdir(mode=0o700)
    subprocess.run(["/Library/Developer/CommandLineTools/usr/bin/git", "init", "-q",
                    str(workspace)], check=True, timeout=15)
    state = workspace / ".git/kryn-barrier-canary"
    state.mkdir(mode=0o700)
    config, products, dependencies = configuration(
        workspace, state, "native", f"http://127.0.0.1:{inference_port}/v1")
    if products:
        raise RuntimeError("No-model canary unexpectedly loaded a product plugin")
    server = NativeServer(workspace, config, log=receipt / "native.log",
                          background={"dependencies": dependencies,
                                      "inference_port": inference_port,
                                      "private_parent": private})
    server.env["GIT_CONFIG_NOSYSTEM"] = "1"
    return server, workspace


def wait_gone(pid):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(.1)
    raise RuntimeError(f"Detached canary child {pid} did not exit")


def run_canaries(receipt):
    checks = {}
    busy = free = read_only = grade = None
    busy_pid = free_pid = None
    connection = stream = None
    try:
        busy = create_volume(receipt, "busy", size="128m")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            server, workspace = server_for(busy, receipt, listener.getsockname()[1])
            payload = workspace / "hold.txt"
            payload.write_text("hold open\n")
            ready = workspace / "held-ready"
            child = ("import pathlib,sys,time; held=open(sys.argv[1],'rb'); "
                     "pathlib.Path(sys.argv[2]).write_text('ready'); time.sleep(90)")
            with server:
                policy_ready(server)
                busy_pid = shell_child(server, workspace, child, payload, ready)
                deadline = time.monotonic() + 5
                while not ready.is_file() and time.monotonic() < deadline:
                    time.sleep(.05)
                if not ready.is_file():
                    raise RuntimeError("Detached child did not open the candidate file")
            try:
                detach(busy)
            except BarrierError:
                checks["open_fd_prevents_normal_detach"] = image_entry(busy.image) is not None
            else:
                checks["open_fd_prevents_normal_detach"] = False
            os.kill(busy_pid, signal.SIGTERM)
            wait_gone(busy_pid)
            detach(busy)
            busy_pid = None
            checks["busy_volume_detached_after_child_exit"] = image_entry(busy.image) is None
            busy = None

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(15)
            free = create_volume(receipt, "free", size="128m")
            server, workspace = server_for(free, receipt, listener.getsockname()[1])
            child = """import errno,json,os,socket,sys
s=socket.create_connection(('127.0.0.1',int(sys.argv[1])),timeout=20)
s.sendall(json.dumps({'pid':os.getpid(),'sid':os.getsid(0)}).encode()+b'\\n')
stream=s.makefile('rb')
paths=json.loads(stream.readline())
result={}
for name,path in paths.items():
    try:
        with open(path,'wb' if name=='grade_write' else 'rb') as file:
            file.write(b'escape') if name=='grade_write' else file.read(16)
        result[name]='opened'
    except OSError as error:
        result[name]=error.errno
s.sendall(json.dumps(result).encode()+b'\\n')
"""
            with server:
                policy_ready(server)
                free_pid = shell_child(server, workspace, child, listener.getsockname()[1])
                connection, _ = listener.accept()
                connection.settimeout(20)
                stream = connection.makefile("rb")
                ready = json.loads(stream.readline())
                checks["detached_session_child_started"] = (
                    ready == {"pid": free_pid, "sid": free_pid})
                # The shell launcher and native server have settled here;
                # retain the live child connection across the detach.
            detach(free)
            checks["fd_free_child_allows_normal_detach"] = image_entry(free.image) is None
            free = None
            read_only = attach(receipt / "free.sparseimage", receipt, readonly=True)
            grade = create_volume(receipt, "grader", size="128m")
            secret = grade.mount / "secret.txt"
            secret.write_text("hidden canary\n")
            attempted_write = grade.mount / "escaped.txt"
            paths = {"old_candidate_new_mount": str(read_only.mount / "workspace/.git/config"),
                     "fresh_grader_read": str(secret),
                     "grade_write": str(attempted_write)}
            connection.sendall(json.dumps(paths).encode() + b"\n")
            result = json.loads(stream.readline())
            checks["old_sandbox_cannot_read_new_mount"] = result.get(
                "old_candidate_new_mount") in {errno.EPERM, errno.EACCES}
            checks["old_sandbox_cannot_read_grader"] = result.get(
                "fresh_grader_read") in {errno.EPERM, errno.EACCES}
            checks["old_sandbox_cannot_write_grader"] = (result.get("grade_write") in
                {errno.EPERM, errno.EACCES} and not attempted_write.exists())
            checks["grader_secret_intact"] = secret.read_text() == "hidden canary\n"
            stream.close()
            connection.close()
            stream = connection = None
            detach(read_only)
            read_only = None
            detach(grade)
            grade = None
            wait_gone(free_pid)
            free_pid = None
    finally:
        if stream is not None:
            stream.close()
        if connection is not None:
            connection.close()
        for pid in (busy_pid, free_pid):
            if pid is not None:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        for volume in (read_only, grade, free, busy):
            if volume is not None:
                try:
                    detach(volume)
                except BaseException:
                    pass  # Preserve a still-mounted receipt for inspection; never force-unmount.
    return checks


def main():
    receipt = Path(tempfile.mkdtemp(prefix="kryn-agent-grade-canary-", dir="/private/tmp"))
    report = {"kind": "research_agent_grade_barrier_canary", "receipt": str(receipt),
              "model_calls": 0, "checks": {},
              "canary_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "barrier_sha256": hashlib.sha256(Path(__file__).with_name(
                  "agent_grade_barrier.py").read_bytes()).hexdigest(),
              "runner_sha256": hashlib.sha256(Path(__file__).with_name(
                  "run_external_patch.py").read_bytes()).hexdigest()}
    try:
        report["checks"] = run_canaries(receipt)
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    report["passed"] = "error" not in report and bool(report["checks"]) and all(
        report["checks"].values())
    (receipt / "canary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
