#!/usr/bin/env python3
"""Trusted relay to one secretless, networkless browser container. No model calls."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import secrets
import select
import signal
import socket
import subprocess
import sys
import stat
import time

MAX_HTML = 1024 * 1024
MAX_REQUEST = 1_500_000
MAX_RESPONSE = 3_000_000
OPERATIONS = {"open", "snapshot", "click", "key", "resize", "screenshot"}


def line_from_fd(fd, buffer, limit, deadline):
    while b"\n" not in buffer:
        if len(buffer) > limit:
            raise RuntimeError("worker output limit")
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise TimeoutError("worker response deadline")
        chunk = os.read(fd, min(65536, limit + 1 - len(buffer)))
        if not chunk:
            raise RuntimeError("worker closed")
        buffer += chunk
    line, buffer = buffer.split(b"\n", 1)
    if len(line) > limit:
        raise RuntimeError("worker output limit")
    return line, buffer


def write_fd(fd, data, deadline):
    offset = 0
    while offset < len(data):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
            raise TimeoutError("worker input deadline")
        offset += os.write(fd, data[offset:offset + 65536])


def exact(message, keys):
    return isinstance(message, dict) and set(message) == set(keys)


def checked_page(root_fd, device):
    descriptor = os.open("index.html", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                         dir_fd=root_fd)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_dev != device or info.st_size > MAX_HTML:
            raise ValueError("candidate page is not a bounded regular file on the checkout device")
        value = bytearray()
        while len(value) <= MAX_HTML:
            chunk = os.read(descriptor, min(65536, MAX_HTML + 1 - len(value)))
            if not chunk:
                break
            value.extend(chunk)
        if len(value) > MAX_HTML:
            raise ValueError("candidate page exceeded 1 MiB")
        return bytes(value)
    finally:
        os.close(descriptor)


def valid_command(message):
    if not isinstance(message, dict) or message.get("op") not in OPERATIONS:
        return False
    op = message["op"]
    if op == "open":
        return exact(message, ("op",))
    if op == "click":
        return exact(message, ("op", "selector")) and isinstance(message["selector"], str) and len(message["selector"]) <= 128
    if op == "key":
        return (exact(message, ("op", "key")) and isinstance(message["key"], str) and
                message["key"] in {"ArrowLeft", "ArrowRight", "Home", "End", "Tab", "Enter", "Space"})
    if op == "resize":
        return (exact(message, ("op", "width", "height")) and
                type(message["width"]) is int and type(message["height"]) is int and
                320 <= message["width"] <= 1440 and 240 <= message["height"] <= 1200)
    return exact(message, ("op",))


def read_client(connection):
    connection.settimeout(10)
    data = b""
    while b"\n" not in data:
        chunk = connection.recv(min(65536, MAX_REQUEST + 1 - len(data)))
        if not chunk or len(data) + len(chunk) > MAX_REQUEST:
            raise ValueError("request limit")
        data += chunk
    line, remainder = data.split(b"\n", 1)
    if remainder:
        raise ValueError("one request per connection")
    return json.loads(line)


def inspect_container(name, image):
    result = subprocess.run(["docker", "inspect", name], capture_output=True,
                            text=True, timeout=5, check=True)
    return verify_boundary(json.loads(result.stdout)[0], image)


def verify_boundary(item, image):
    host = item["HostConfig"]
    if (item["Image"] != image or item["Mounts"] or host["NetworkMode"] != "none" or
            host["ReadonlyRootfs"] is not True or host["Privileged"] is not False or
            set(host["CapDrop"] or []) != {"ALL"} or
            set(host["SecurityOpt"] or []) != {"no-new-privileges"} or
            host["PidMode"] not in ("", "private") or host["IpcMode"] != "private" or
            host["CgroupnsMode"] != "private" or host["UsernsMode"] not in ("", "private") or
            host["Devices"] or host["DeviceCgroupRules"] or host["CapAdd"] or
            host["Binds"] or host.get("Mounts") or host["VolumesFrom"] or
            host["PortBindings"] or host["PublishAllPorts"] is not False or
            not 0 < host["PidsLimit"] <= 128 or not 0 < host["Memory"] <= 512 * 1024 * 1024 or
            item["Config"]["User"] != "10001:10001"):
        raise RuntimeError("browser container boundary differs")
    return {"image_id": item["Image"], "mounts": len(item["Mounts"]),
            "network": host["NetworkMode"], "read_only": host["ReadonlyRootfs"],
            "privileged": host["Privileged"], "cap_drop": host["CapDrop"],
            "pid_mode": host["PidMode"], "ipc_mode": host["IpcMode"],
            "cgroup_mode": host["CgroupnsMode"], "security_opt": host["SecurityOpt"],
            "pids_limit": host["PidsLimit"], "memory_limit": host["Memory"],
            "user": item["Config"]["User"]}


def run(image, lifetime, repo):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("browser image must be an exact local image ID")
    root = Path(repo).absolute()
    if root != root.resolve() or any(path.is_symlink() for path in (root, *root.parents)):
        raise ValueError("candidate checkout must be canonical")
    actual = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", image],
                            capture_output=True, text=True, timeout=5, check=True).stdout.strip()
    if actual != image:
        raise RuntimeError("browser image ID changed")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    device = os.fstat(root_fd).st_dev
    name = "kryn-ui-" + secrets.token_hex(8)
    command = ["docker", "run", "--rm", "-i", "--name", name, "--network", "none",
               "--read-only", "--user", "10001:10001", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges", "--pids-limit", "128",
               "--memory", "512m", "--cpus", "1", "--tmpfs", "/tmp:rw,nosuid,size=128m",
               "--shm-size", "128m", image]
    child = None
    server = None
    buffer = b""
    try:
        child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
        server = socket.socket()
        os.set_blocking(child.stdin.fileno(), False)
        os.set_blocking(child.stdout.fileno(), False)
        ready, buffer = line_from_fd(child.stdout.fileno(), buffer, 1024, time.monotonic() + 15)
        if json.loads(ready) != {"ready": True}:
            raise RuntimeError("browser worker did not become ready")
        boundary = inspect_container(name, image)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.settimeout(1)
        token = secrets.token_hex(24)
        print(json.dumps({"port": server.getsockname()[1], "token": token,
                          "image": image, "container": name, "boundary": boundary}), flush=True)
        deadline = time.monotonic() + lifetime
        while time.monotonic() < deadline:
            try:
                connection, _ = server.accept()
            except socket.timeout:
                if child.poll() is not None:
                    raise RuntimeError("browser worker exited")
                continue
            with connection:
                try:
                    message = read_client(connection)
                    if not isinstance(message, dict) or message.pop("token", None) != token or not valid_command(message):
                        response = {"ok": False, "error": "DENIED"}
                    else:
                        response = None
                        if message["op"] == "open":
                            try:
                                page = checked_page(root_fd, device)
                            except (OSError, ValueError):
                                response = {"ok": False, "error": "PAGE_REJECTED"}
                            else:
                                message = {"op": "open", "html_b64": base64.b64encode(page).decode()}
                        if response is None:
                            write_fd(child.stdin.fileno(), (json.dumps(message) + "\n").encode(), time.monotonic() + 10)
                            raw, buffer = line_from_fd(child.stdout.fileno(), buffer, MAX_RESPONSE, time.monotonic() + 10)
                            response = json.loads(raw)
                            if (not isinstance(response, dict) or type(response.get("ok")) is not bool or
                                    not set(response).issubset({"ok", "text", "image_b64", "error"})):
                                raise RuntimeError("browser worker response changed")
                except (OSError, ValueError, TimeoutError, RuntimeError, TypeError, KeyError, json.JSONDecodeError):
                    response = {"ok": False, "error": "BROKER_FAILURE"}
                try:
                    connection.sendall((json.dumps(response) + "\n").encode())
                except OSError:
                    pass
    finally:
        os.close(root_fd)
        if server is not None:
            server.close()
        cleanup_errors = []
        for action in (("kill", "rm") if child is not None else ()):
            argv = ["docker", action, name] if action == "kill" else ["docker", "rm", "-f", name]
            try:
                subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=5, check=False)
            except (OSError, subprocess.TimeoutExpired) as error:
                cleanup_errors.append(type(error).__name__)
        if child is not None:
            try:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired) as error:
                cleanup_errors.append(type(error).__name__)
            for _ in range(20):
                try:
                    present = subprocess.run(["docker", "inspect", name], stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL, timeout=2).returncode == 0
                except (OSError, subprocess.TimeoutExpired):
                    present = True
                if not present:
                    break
                time.sleep(.1)
        if (child is not None and present) or cleanup_errors:
            raise RuntimeError("browser container cleanup incomplete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--lifetime", type=int, default=300)
    args = parser.parse_args()
    if not 1 <= args.lifetime <= 3600:
        parser.error("lifetime must be 1..3600 seconds")
    def stop(_signal, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        run(args.image, args.lifetime, args.repo)
    except KeyboardInterrupt:
        pass
