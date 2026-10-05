"""No-model OpenCode admission for a pinned, dependency-ready SWE worker image.

Uses canned local responses only. This deliberately cannot run benchmark prompts
or contact oMLX. Both arms must pass before a separate experiment is frozen.
"""

import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import shlex
import secrets
import subprocess
import tempfile
import threading

from research.container_config import LOCAL_URL, worker_environment
from research.container_worker import DockerWorker, HostGuard, validate_worker, pinned_image
from research.local_campaign import atomic
from research.local_only import check_environment
from research.run_external_patch import collect_patch
from research.ui_gateway.synthetic_dispatch import FakeInference
from tools.native_client import product_plugin_files
from tools.run_native_trial import plugin_active, plugin_absent

ROOT = Path(__file__).resolve().parents[1]
PYTHON = "/opt/miniconda3/envs/testbed/bin/python"
CANARY = "\nKRYN synthetic worker admission.\n"
CONTROL_IMAGE = "python@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0"
SERVER = "http://127.0.0.1:18767"


def source_inputs():
    # Freeze the local Python implementation, including transitive boundary and
    # resource helpers. A short hand-maintained import list silently missed them.
    paths = [p for directory in ("research", "tools", "src")
             for p in (ROOT / directory).rglob("*.py") if p.is_file()]
    paths.append(ROOT / "setup/opencode.template.json")
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def environment(native):
    env = worker_environment(native=native)
    env["PATH"] = "/opt/miniconda3/envs/testbed/bin:/usr/local/bin:/usr/bin:/bin"
    env["PWD"] = "/testbed"
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    config = json.loads(env["OPENCODE_CONFIG_CONTENT"])
    for plugin in config["plugins"]:
        if isinstance(plugin, dict):
            plugin["package"] = "/opt/kryn-plugin"
            plugin["options"].update(nodeBinary="/usr/local/bin/node",
                                     profileId="swe-container-development")
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
    check_environment(env, "/tmp/kryn", LOCAL_URL)
    return env


def baseline_links(baseline):
    """Only unchanged tracked links from the trusted pre-agent source are allowed."""
    def git(*args):
        return subprocess.check_output(["git", "-C", str(baseline), *args], timeout=20)
    if git("status", "--porcelain", "--untracked-files=all").strip():
        raise RuntimeError("Admission baseline is not clean")
    links = {}
    for entry in git("ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue
        fields, name = entry.split(b"\t", 1)
        mode, oid, stage = fields.split()
        if stage != b"0":
            raise RuntimeError("Baseline has an unmerged index")
        if mode == b"120000":
            links[name.decode()] = git("cat-file", "blob", oid.decode()).decode()
    actual = {p.relative_to(baseline).as_posix(): str(p.readlink())
              for p in baseline.rglob("*") if p.is_symlink()}
    if links != actual:
        raise RuntimeError("Baseline has untracked or changed symbolic links")
    return links


def unchanged(manifest, baseline):
    if source_inputs() != manifest["source_sha256"]:
        raise RuntimeError("Admission source drift")
    plugins = {name: hashlib.sha256(data).hexdigest() for name, data in product_plugin_files(ROOT).items()}
    if plugins != manifest["plugin_sha256"]:
        raise RuntimeError("Admission plugin drift")
    if (baseline_links(baseline) != manifest["baseline_symlinks"]
            or hashlib.sha256((baseline / ".git/config").read_bytes()).hexdigest() != manifest["git_config_sha256"]
            or subprocess.check_output(["git", "-C", str(baseline), "rev-parse", "HEAD"], text=True).strip() != manifest["base_commit"]):
        raise RuntimeError("Admission baseline drift")


def tool_acceptance(output):
    parts = []
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        part = event.get("part")
        if isinstance(part, dict) and part.get("type") == "tool":
            parts.append(part)
    names = [part.get("tool") for part in parts]
    completed = all(part.get("state", {}).get("status") == "completed" for part in parts)
    shell_exit = (parts[-1].get("state", {}).get("metadata", {}).get("metadata", {}).get("exit")
                  if parts and parts[-1].get("tool") == "shell" else None)
    return {"passed": names == ["read", "shell"] and completed and type(shell_exit) is int and shell_exit == 0,
            "tools": names, "all_completed": completed, "shell_exit": shell_exit}


def plugin_inventory(docker, worker, native, password):
    script = """import json,time,urllib.request
last='no response'
for attempt in range(100):
 try:
  req=urllib.request.Request('SERVER/api/plugin',headers=HEADERS)
  with urllib.request.urlopen(req,timeout=1) as r:inventory=json.load(r)
  assert isinstance(inventory.get('data'),list) and inventory.get('location',{}).get('directory')=='/testbed'
  rows=[p for p in inventory.get('data',[]) if p.get('id')=='kryn.product']
  if NATIVE or any(p.get('state',{}).get('status')=='active' for p in rows):break
 except OSError as error:last=str(error)
 time.sleep(.2)
else:raise RuntimeError('Native plugin inventory did not become ready: '+last)
print(json.dumps(inventory))
""".replace("SERVER", SERVER).replace("NATIVE", repr(native)).replace("HEADERS", repr({
        "Authorization": "Basic " + base64.b64encode(("opencode:" + password).encode()).decode(),
        "x-opencode-directory": "%2Ftestbed"}))
    inventory = json.loads(docker.command("exec", worker, PYTHON, "-I", "-c", script, timeout=45))
    passed = (plugin_absent(inventory, "kryn.product") if native else
              plugin_active(inventory, "kryn.product", Path("/opt/kryn-plugin")))
    if not passed:
        raise RuntimeError("KRYN/native plugin activation mismatch: " + json.dumps(inventory))
    return inventory


class Marker(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"kryn-private-host-marker")

    def log_message(self, *_):
        pass


def routes(docker, worker, sidecar, ip):
    """Negative checks have reachable positive controls in the bridge sidecar."""
    with ThreadingHTTPServer(("127.0.0.1", 0), Marker) as marker:
        threading.Thread(target=marker.serve_forever, daemon=True).start()
        try:
            port = marker.server_address[1]
            control = docker.create("route-control", CONTROL_IMAGE, ["sleep", "120"], network="bridge")
            positive = """import socket,http.client,json
ips=sorted({item[4][0] for item in socket.getaddrinfo('host.docker.internal',PORT,type=socket.SOCK_STREAM)})
controls={}
for ip in ips:
 try:
  c=http.client.HTTPConnection(ip,PORT,timeout=3);c.request('GET','/')
  controls[ip]=c.getresponse().read()==b'kryn-private-host-marker';c.close()
 except OSError as e:controls[ip]=str(e)
assert any(value is True and ':' not in ip for ip,value in controls.items())
with socket.create_connection(('1.1.1.1',443),timeout=3):pass
assert socket.getaddrinfo('example.com',443)
print(json.dumps(controls))
""".replace("PORT", str(port))
            controls = json.loads(docker.command("exec", control, "python", "-I", "-c", positive))
            host_ips = list(controls)
            docker.settle(control)
            networks = docker.inspect("container", sidecar)["NetworkSettings"]["Networks"]
            gateways = sorted({item["Gateway"] for n in networks.values()
                               for item in docker.inspect("network", n["NetworkID"])["IPAM"]["Config"]
                               if item.get("Gateway")})
            host_file = docker.evidence / "private-marker"
            host_file.write_text("Host-only canary, not benchmark evidence.\n")
            script = """import json,socket,urllib.request,pathlib
def connected(host,port):
 try:
  with socket.create_connection((host,port),timeout=2):return True
 except OSError:return False
r={'model_get':json.load(urllib.request.urlopen(URL,timeout=3))['data'][0]['id']}
r['host_denied']=all(not connected(h,p) for h in HOSTS for p in (PORT,8000))
r['external_denied']=not connected('1.1.1.1',443)
try:socket.getaddrinfo('example.com',443);r['dns_denied']=False
except OSError:r['dns_denied']=True
r['host_file_denied']=not pathlib.Path(HOST_FILE).exists()
r['docker_socket_denied']=not pathlib.Path('/var/run/docker.sock').exists()
print(json.dumps(r))
""".replace("URL", repr(f"http://{ip}:18766/v1/models")).replace("HOSTS", repr([*host_ips, *gateways])).replace(
                "PORT", str(port)).replace("HOST_FILE", repr(str(host_file)))
            observed = json.loads(docker.command("exec", worker, PYTHON, "-I", "-c", script, timeout=40))
            if observed.pop("model_get") != "Qwen3.5-9B-6bit" or not all(v is True for v in observed.values()):
                raise RuntimeError("Worker route isolation failed: " + json.dumps(observed))
            return {"passed": True, "positive_controls": True, "host_ips": host_ips,
                    "host_positive_results": controls, "gateways": gateways, "observed": observed}
        finally:
            marker.shutdown()


def arm(image, directory, native, baseline, baseline_symlinks):
    from research.container_export import extract_worktree
    directory.mkdir(mode=0o700)
    report = {"passed": False, "native": native, "synthetic_inference": True}
    # These commands prove transport, dependencies and export; they do not solve
    # the public issue. Existing tests are neither read nor altered by the stub.
    shell = ("python -c " + shlex.quote(
        "import pathlib,ssl,django,asgiref; "
        "p=pathlib.Path('README.rst'); original=p.read_text(); "
        f"p.write_text(original+{CANARY!r}); "
        "pathlib.Path('kryn-canary.txt').write_text('new source file\\n'); "
        "print('KRYN_READY',django.__version__,asgiref.__version__)"))
    sequence = [("read", {"path": "/testbed/README.rst"}),
                ("shell", {"command": shell, "description": "Synthetic dependency and export canary"})]
    fake = FakeInference(sequence, "Synthetic worker canary complete.")
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    try:
        with HostGuard(directory) as guard:
            docker = DockerWorker(directory, guard)
            worker = None
            def capture_server_log():
                if worker and docker.inspect("container", worker, cleanup=True)["State"]["Running"]:
                    script = ("import os,stat; fd=os.open('/tmp/kryn-server.log',os.O_RDONLY|os.O_NOFOLLOW); "
                              "s=os.fstat(fd); assert stat.S_ISREG(s.st_mode) and s.st_size<=1024*1024; "
                              "data=os.read(fd,1024*1024); os.close(fd); os.write(1,data)")
                    log = docker.command("exec", worker, PYTHON, "-I", "-c", script, cleanup=True)
                    (directory / "server.log").write_text(log)
            try:
                net, side, ip = docker.route(fake.server_address[1])
                worker = docker.create("candidate", image, ["/bin/sh", "-c", "sleep 600"], network=net, worker=True)
                info = docker.inspect("container", worker)
                validate_worker(info, image, docker.owner)
                atomic(directory / "worker-inspect.json", info)
                report["routes"] = routes(docker, worker, side, ip)
                # No configuration or credentials from the owner's environment.
                docker.command("exec", worker, "mkdir", "-p", "/tmp/kryn-state",
                               "/tmp/kryn/home", "/tmp/kryn/xdg/config", "/tmp/kryn/xdg/data",
                               "/tmp/kryn/xdg/cache", "/tmp/kryn/xdg/state")
                if not native:
                    with tempfile.TemporaryDirectory(prefix="kryn-plugin-") as temporary:
                        path = Path(temporary)
                        path.chmod(0o755)
                        for name, data in product_plugin_files(ROOT).items():
                            (path / name).write_bytes(data)
                            (path / name).chmod(0o644)
                        # The copied files retain a non-worker owner. The agent
                        # cannot replace policy bytes beneath unwritable /opt.
                        docker.command("cp", str(path), worker + ":/opt/kryn-plugin")
                    report["plugin_protection"] = json.loads(docker.command("exec", worker, PYTHON, "-I", "-c",
                        "import pathlib,os,json; p=pathlib.Path('/opt/kryn-plugin'); "
                        "v={'directory_owner':p.stat().st_uid,'agent_uid':os.geteuid(),"
                        "'parent_writable':os.access(p.parent,os.W_OK),'writable':os.access(p,os.W_OK),"
                        "'files_writable':any(os.access(f,os.W_OK) for f in p.iterdir())}; "
                        "print(json.dumps(v)); assert v['directory_owner']!=v['agent_uid'] and not v['parent_writable'] and not v['writable'] and not v['files_writable']"))
                docker.command("exec", "-d", worker, "socat",
                               "TCP-LISTEN:18765,bind=127.0.0.1,reuseaddr,fork", f"TCP:{ip}:18766")
                env = environment(native)
                env["OPENCODE_PASSWORD"] = secrets.token_urlsafe(24)
                atomic(directory / "environment.json", env)
                server_command = shlex.join(["/usr/bin/env", "-i", *[k + "=" + v for k, v in sorted(env.items())],
                                            "/usr/local/bin/opencode", "serve", "--hostname", "127.0.0.1", "--port", "18767"])
                docker.command("exec", "-d", "-w", "/testbed", worker, "/bin/sh", "-c",
                               "exec " + server_command + " > /tmp/kryn-server.log 2>&1")
                report["plugin_before"] = plugin_inventory(docker, worker, native, env["OPENCODE_PASSWORD"])
                output = docker.command("exec", "-w", "/testbed", worker, "/usr/bin/env", "-i",
                                        *[k + "=" + v for k, v in sorted(env.items())],
                                        "/usr/local/bin/opencode", "run", "--server", SERVER, "--model", "local/qwen",
                                        "--agent", "agent", "--format", "json", "--auto", "--title", "Synthetic worker admission", "--",
                                        "Run the synthetic worker admission canary.", timeout=180)
                (directory / "events.jsonl").write_text(output)
                report["plugin_after"] = plugin_inventory(docker, worker, native, env["OPENCODE_PASSWORD"])
                capture_server_log()
                docker.settle(worker)
                docker.settle(side)
                archive = directory / "worktree.tar"
                docker.export(worker, archive)
                capture = directory / "capture"
                report["export"] = extract_worktree(archive, capture,
                    expected_git_config_sha256=hashlib.sha256((baseline / ".git/config").read_bytes()).hexdigest(),
                    archive_root=".", baseline_symlinks=baseline_symlinks)
                shutil.copytree(baseline / ".git", capture / ".git")
                git_private = directory / "git-private"
                git_private.mkdir()
                base = subprocess.check_output(["git", "-C", str(baseline), "rev-parse", "HEAD"], text=True).strip()
                git_binary = Path(subprocess.check_output(["/usr/bin/xcrun", "--find", "git"], text=True).strip()).resolve()
                patch, names, size, sha = collect_patch(capture, base, directory, private=git_private,
                    dependencies=[], git_binary=git_binary, tool_path=None,
                    cancelled=lambda: bool(guard.reason or guard.memory.cancel.is_set()))
                expected_readme = (baseline / "README.rst").read_bytes() + CANARY.encode()
                exact_files = ((capture / "README.rst").read_bytes() == expected_readme
                               and (capture / "kryn-canary.txt").read_text() == "new source file\n")
                tool_gate = tool_acceptance(output)
                report.update(inference_calls=fake.calls, patch_sha256=sha, patch_bytes=size,
                              new_paths=names, tool_calls=tool_gate["tools"], tool_gate=tool_gate)
                headers = {line for line in patch.read_bytes().splitlines() if line.startswith(b"diff --git ")}
                report["passed"] = (exact_files and tool_gate["passed"]
                                    and sum(bool(c["tools"]) for c in fake.calls) == 3 and set(names) == {"kryn-canary.txt"}
                                    and headers == {b"diff --git a/README.rst b/README.rst",
                                                    b"diff --git a/kryn-canary.txt b/kryn-canary.txt"})
                guard.check()
            except Exception as error:
                report["error"] = str(error)
                try:
                    capture_server_log()
                except Exception as log_error:
                    report["server_log_error"] = str(log_error)
            finally:
                try:
                    docker.close()
                except Exception as error:
                    report.update(passed=False, cleanup_error=str(error))
                report["resources"] = guard.samples
                if guard.reason or guard.memory.cancel.is_set():
                    report.update(passed=False, guard_reason=guard.reason or guard.memory.guard.reason)
        guard.check()  # Include the final resource sample taken during __exit__.
    except Exception as error:
        report.update(passed=False, error=str(error))
    finally:
        report["inference_calls"] = fake.calls
        fake.shutdown()
        fake.server_close()
        atomic(directory / "result.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=pinned_image)
    parser.add_argument("--baseline", required=True, type=Path, help="Trusted, sealed image checkout captured before agent work")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not args.image.startswith("sha256:"):
        parser.error("Admission records the exact local worker image ID")
    args.out.mkdir(mode=0o700)
    baseline = args.baseline.resolve(strict=True)
    baseline_symlinks = baseline_links(baseline)
    manifest = {"kind": "swe_container_no_model_admission", "image": args.image,
                "base_commit": subprocess.check_output(["git", "-C", str(baseline), "rev-parse", "HEAD"], text=True).strip(),
                "git_config_sha256": hashlib.sha256((baseline / ".git/config").read_bytes()).hexdigest(),
                "baseline_symlinks": baseline_symlinks,
                "source_sha256": source_inputs(),
                "plugin_sha256": {name: hashlib.sha256(data).hexdigest()
                                  for name, data in product_plugin_files(ROOT).items()}}
    atomic(args.out / "manifest.json", manifest)
    for name in manifest["source_sha256"]:
        destination = args.out / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    results = []
    for name in ("native", "kryn"):
        unchanged(manifest, baseline)
        results.append(arm(args.image, args.out / name, name == "native", baseline, baseline_symlinks))
        if not results[-1]["passed"]:
            break
    unchanged(manifest, baseline)
    wire = [sorted({r["tool_schema_sha256"] for r in result.get("inference_calls", []) if r["tools"]}) for result in results]
    same_wire = len(wire) == 2 and len(wire[0]) == 1 and wire[0] == wire[1]
    report = {"passed": all(r["passed"] for r in results) and same_wire,
              "same_tool_wire": same_wire, "results": [r["passed"] for r in results]}
    atomic(args.out / "result.json", report)
    print(json.dumps(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
