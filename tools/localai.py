#!/usr/bin/env python3
"""Daily entry point for the owned local stack; delegates all agent work to OpenCode."""
import argparse
from contextlib import ExitStack, nullcontext
import copy
import ctypes
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from native_client import BINARY, MODEL_ID, PROJECT, ROOT, NativeServer, environment, owned_config
from context_probe import ResourceGuard, resources
import improvement
import learning
import owner_auth

RUNTIME = "http://127.0.0.1:8000"
BASE_URL = RUNTIME + "/v1"
PACKAGE = "@opencode/ai/providers/openai-compatible"
VARIANTS = {"fast", "medium", "high", "xhigh", "think"}
REVISION = '76fe4065e622cf34990d3c13ef80ec8531c9a0f7'
REPOSITORY = 'mlx-community/Qwen3.5-9B-6bit'
MODEL_PARENT = 'candidates/qwen35-9b/models'
SERVER_CONTEXT = 24576
MEMORY_GIB = 12
OMLX = Path.home() / "Applications/oMLX.app/Contents/MacOS/omlx-cli"
CONTROL = Path.home() / "Library/Application Support/oMLX/control.sock"
POLICY = [{"action": "provider.use", "resource": "*", "effect": "deny"},
          {"action": "provider.use", "resource": "local", "effect": "allow"}]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def local_reference(ref):
    if isinstance(ref, str):
        model, separator, variant = ref.partition("#")
        return model == "local/qwen" and (not separator or variant in VARIANTS)
    return (isinstance(ref, dict) and ref.get("providerID") == "local"
            and ref.get("id", ref.get("model")) == "qwen"
            and ref.get("variant") in VARIANTS | {None})


def expected_config():
    # The deployer copies the reviewed template and pins its selected model.
    config = json.loads((PROJECT / "setup/opencode.template.json").read_text())
    plugin = PROJECT / "plugin/server.js"
    if not plugin.is_file():
        plugin = PROJECT / "tools/kryn_plugin.mjs"
    identity = hashlib.sha256(plugin.read_bytes()).hexdigest()[:16]
    profile = PROJECT / "setup/install-profile.json"
    if not profile.is_file():
        profile = PROJECT / "setup/accepted-profile.json"
    profile_id = hashlib.sha256(profile.read_bytes()).hexdigest()
    for item in config["plugins"]:
        if isinstance(item, dict):
            item["package"] = str(ROOT / "plugins" / identity)
            item["options"].update(stateDir=str(ROOT / "state/improvement"), profileId=profile_id, modelID=MODEL_ID)
    return config


def reference_variant(ref):
    return (ref.partition("#")[2] or None) if isinstance(ref, str) else ref.get("variant")


def same_reference(left, right):
    return local_reference(left) and local_reference(right) and reference_variant(left) == reference_variant(right)


def validate_defaults(config, expected):
    require(same_reference(config.get("model"), expected.get("model")),
            "Expected release default model; review profile before launch")
    for key in ("default_agent", "compaction", "tool_output"):
        require(config.get(key) == expected.get(key), f"Expected release {key}; review profile before launch")


def validate_route(provider, model):
    for name, value in (("provider", provider), ("model", model)):
        require(value.get("package") == PACKAGE, f"Unexpected {name} package; refusing launch")
        require(value.get("settings", {}).get("baseURL") == BASE_URL,
                f"Unexpected {name} endpoint; refusing launch")
    require(model.get("modelID") == MODEL_ID, "Unexpected runtime model ID")
    variants = model.get("variants", [])
    require(len(variants) == len(VARIANTS) and {v.get("id") for v in variants} == VARIANTS,
            "Expected fast/medium/high/xhigh variants and the legacy think alias")
    require(all(v.get("settings", {}).get("baseURL") == BASE_URL for v in variants),
            "Every variant must explicitly use the local endpoint")
    expected = expected_config()["providers"]["local"]["models"]["qwen"]
    for key in ("limit", "body"):
        require(model.get(key) == expected.get(key), f"Unexpected model {key}; review profile before launch")
    require({v["id"]: v for v in variants} == {v["id"]: v for v in expected["variants"]},
            "Reasoning variant definitions differ from this release")


def validate_owned_config(config):
    expected_profile = expected_config()
    providers = config.get("providers", {})
    require(set(providers) == {"local"}, "Owned config must contain only provider local")
    models = providers["local"].get("models", {})
    require(set(models) == {"qwen"}, "Owned config must contain only model local/qwen")
    validate_route(providers["local"], models["qwen"])
    require(local_reference(config.get("model")), "Default model must be local/qwen")
    validate_defaults(config, expected_profile)
    rules = [p for p in config.get("experimental", {}).get("policies", [])
             if p.get("action") == "provider.use"]
    require(rules == POLICY, "Owned global config needs deny-all/allow-local provider policy")
    plugins = config.get("plugins", [])
    require(plugins == expected_profile["plugins"],
            "Owned plugin policy changed; review before launch")
    require(config.get("update") == "disable" and config.get("share") == "disabled",
            "Automatic updates/sharing must remain disabled")
    for section in ("agents", "commands"):
        for name, item in config.get(section, {}).items():
            require(local_reference(item.get("model")), f"Owned {section}/{name} must pin local/qwen")
        for name, item in expected_profile[section].items():
            require(same_reference(config.get(section, {}).get(name, {}).get("model"), item.get("model")),
                    f"Expected release model reference for {section}/{name}")
            if section == "commands":
                require(all(config[section][name].get(key) == item.get(key) for key in ("agent", "subagent")),
                        f"Expected release command routing for {name}")


def prerequisites(source_init=False):
    release = verify_release(current=not source_init)
    validate_runtime_files(Path(release["directory"]))
    model_integrity(source_init=source_init)
    config = owned_config()
    validate_owned_config(config)
    for path in (BINARY, OMLX):
        require(path.is_file() and os.access(path, os.X_OK), f"Missing executable: {path}")
    marker = ROOT / MODEL_PARENT / MODEL_ID / ".localai-download.json"
    identity = json.loads(marker.read_text())
    require(identity == {"repository": REPOSITORY, "revision": REVISION},
            "Model installation revision marker does not match")
    for name, item in config.get("mcp", {}).get("servers", {}).items():
        if item.get("type") == "local":
            command = item.get("command", [])
            require(command and Path(command[0]).is_file(), f"Missing MCP executable: {name}")
            if len(command) > 1 and command[1].endswith(".js"):
                require(Path(command[1]).is_file(), f"Missing MCP entry point: {name}")
    return config


def private_json(path):
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Refusing linked owned metadata")
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and info.st_nlink == 1
            and not info.st_mode & 0o022 and info.st_size <= 1024**2, "Owned metadata has unsafe ownership, size or permissions")
    return json.loads(path.read_text())


def verify_release(current=True):
    manifest = private_json(ROOT / "client/deployment.json")
    release = manifest.get("release")
    require(isinstance(release, str) and re.fullmatch(r"[a-f0-9]{16}", release), "Malformed installed release")
    directory = ROOT / "client" / release
    require(manifest.get("directory") == str(directory), "Installed release directory differs from its identity")
    require(not current or PROJECT.resolve() == directory.resolve(),
            "This is not the installed release; run the deployed kryn command (source-kit init/self-check remain available)")
    files = manifest.get("files")
    require(isinstance(files, dict) and {"tools/localai.py", "tools/native_client.py", "tools/native-shell",
            "tools/context_probe.py", "tools/improvement.py", "tools/learning.py", "tools/owner_auth.py", "tools/protocol_probe.py", "setup/opencode.template.json",
            "plugin/server.js", "plugin/package.json",
            "setup/install-profile.json", "setup/runtime-profile.json", "setup/AGENTS.md"} == set(files), "Unexpected installed release contents")
    require(hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:16] == release,
            "Installed release manifest identity changed")
    for name, digest in files.items():
        path = directory / name
        require(not any(p.is_symlink() for p in (path, *path.parents)), "Linked release file refused")
        require(path.is_file() and path.stat().st_size <= 2 * 1024**2 and hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                "Installed release file changed; restore its reviewed release")
    plugin_dir = ROOT / "plugins" / files["plugin/server.js"][:16]
    require(manifest.get("plugin_directory") == str(plugin_dir), "Native plugin path differs from its content identity")
    for name in ("server.js", "package.json"):
        path = plugin_dir / name
        require(not any(p.is_symlink() for p in (path, *path.parents))
                and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == files["plugin/" + name],
                "Installed native product plugin changed")
    return manifest


def validate_runtime_files(directory):
    expected = private_json(directory / "setup/runtime-profile.json")
    def subset(actual, wanted):
        if isinstance(wanted, dict):
            return isinstance(actual, dict) and all(key in actual and subset(actual[key], value) for key, value in wanted.items())
        if type(wanted) in (int, float):
            return type(actual) in (int, float) and actual == wanted
        return type(actual) is type(wanted) and actual == wanted
    for key, filename in (("global", "settings.json"), ("model", "model_settings.json")):
        # Only the generated public allowlist is compared. Extra secret settings
        # are neither returned nor logged.
        actual = private_json(Path.home() / ".omlx" / filename)
        require(subset(actual, expected[key]), "Installed oMLX " + key + " profile differs from this release")


def model_integrity(deep=False, source_init=False):
    release = verify_release(current=not source_init)
    profile = private_json(Path(release["directory"]) / "setup/install-profile.json")
    require((profile.get("repository"), profile.get("revision"), profile.get("model_parent"), profile.get("memory_gib"))
            == (REPOSITORY, REVISION, MODEL_PARENT, MEMORY_GIB), "Installed profile identity differs from the client")
    if not deep:
        return "Revision marker checked; model bytes not rehashed (use doctor --deep)."
    directory = ROOT / MODEL_PARENT / MODEL_ID
    for name, expected in profile["files"].items():
        relative = Path(name)
        require(not relative.is_absolute() and ".." not in relative.parts and relative.parts,
                "Invalid pinned model filename")
        path = directory / relative
        require(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(), "Pinned model file missing or linked")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(4 * 1024**2), b""):
                digest.update(block)
        require(digest.hexdigest() == expected, "Pinned model content changed; no inference allowed")
    return "Every pinned model file SHA256 verified."


def with_verified_skill(config, *, json_cli=False):
    """Snapshot approved data-only instructions for this native server's sessions."""
    result = copy.deepcopy(config)
    scope = "disposable_json_cli" if json_cli else None
    champion = learning.active_champion(ROOT / "state/improvement", scope=scope)
    for item in result.get("plugins", []):
        if isinstance(item, dict) and "champion" in item.get("options", {}):
            item["options"].update(champion=champion, workflowScope=scope)
    return result


def validate_runtime_metadata(results):
    models = [m for m in records(results.get("models", {})) if m.get("id") == MODEL_ID]
    require(len(models) == 1, "Local runtime must list the installed Qwen model exactly once; no fallback allowed")
    context = models[0].get("max_model_len")
    require(type(context) is int and context == SERVER_CONTEXT,
            "Runtime input ceiling differs from this release; review runtime settings")
    status = results.get("status", {})
    require(isinstance(status, dict), "Unexpected runtime status response")
    ceiling = status.get("model_memory_max")
    require(type(ceiling) in (int, float) and 0 < ceiling <= MEMORY_GIB * 1024**3,
            "Runtime effective memory ceiling is missing, disabled or above this release's limit")
    return {"max_model_len": context, "model_memory_max": ceiling}


def runtime_metadata():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    results = {}
    for name, path in (("health", "/health"), ("models", "/v1/models"), ("status", "/api/status")):
        with opener.open(RUNTIME + path, timeout=5) as reply:
            require(reply.status == 200, f"oMLX {name} check failed")
            results[name] = json.load(reply)
    checked = validate_runtime_metadata(results)
    require(results["status"].get("version") == "0.6.4", "Expected oMLX 0.6.4")
    require(results["status"].get("default_model") == MODEL_ID, "Unexpected default runtime model")
    return {"runtime": RUNTIME, "model": MODEL_ID, "healthy": True,
            **checked, "memory_limit_gib": MEMORY_GIB,
            **{k: results["status"].get(k) for k in ("active_requests", "waiting_requests", "version")},
            "note": "Profile metadata only; no generation. MTP and full runtime settings require adoption checks."}


def runtime_command(action):
    require(OMLX.is_file() and os.access(OMLX, os.X_OK), f"Missing owned oMLX CLI: {OMLX}")
    # Stopping the owned runtime must still work if its OpenCode config needs repair.
    env = environment({})
    env.pop("OMLX_BASE_PATH", None)
    command = [str(OMLX), action]
    if action == "start":
        command += ["--timeout", "60"]
    subprocess.run(command, env=env, check=True, timeout=75)


def runtime_identity():
    """The control socket and listener must identify this user's installed app."""
    require(not any(p.is_symlink() for p in (CONTROL, *CONTROL.parents)), "Linked runtime control socket refused")
    control = CONTROL.lstat()
    require(stat.S_ISSOCK(control.st_mode) and control.st_uid == os.getuid() and not control.st_mode & 0o022,
            "Runtime control socket ownership or permissions are unsafe")
    result = subprocess.run(["/usr/sbin/lsof", "-nP", "-a", "-iTCP:8000", "-sTCP:LISTEN", "-Fpu"],
                            capture_output=True, text=True, timeout=5, check=True)
    rows = []
    for line in result.stdout.splitlines():
        if line.startswith("p"):
            rows.append({"pid": int(line[1:])})
        elif line.startswith("u") and rows:
            rows[-1]["uid"] = int(line[1:])
    require(len(rows) == 1 and rows[0].get("uid") == os.getuid(), "Runtime listener ownership is uncertain")
    pid = rows[0]["pid"]
    lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    fn = lib.proc_pidpath
    fn.argtypes, fn.restype = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32], ctypes.c_int
    buf = ctypes.create_string_buffer(4096)
    require(fn(pid, buf, len(buf)) > 0 and Path(buf.value.decode()).resolve().is_relative_to(OMLX.parents[2].resolve()),
            "Runtime listener is outside the owned oMLX app")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(3)
        connection.connect(str(CONTROL))
        connection.sendall(b'{"command":"status"}\n')
        raw = b""
        while b"\n" not in raw and len(raw) < 16384:
            chunk = connection.recv(4096)
            if not chunk:
                break
            raw += chunk
    app = json.loads(raw.split(b"\n", 1)[0])
    require(app.get("ok") is True and app.get("state") == "running" and app.get("port") == 8000
            and type(app.get("pid")) is int and app["pid"] == pid, "Runtime control/listener identity mismatch")
    return pid


def ensure_runtime():
    try:
        return runtime_metadata()
    except (OSError, urllib.error.URLError):
        with socket.socket() as connection:
            connection.settimeout(1)
            require(connection.connect_ex(("127.0.0.1", 8000)) != 0,
                    "Port 8000 is occupied but runtime metadata failed; inspect it before starting oMLX")
    print("Starting the owned oMLX app…", flush=True)
    runtime_command("start")
    return runtime_metadata()


def records(response):
    require(isinstance(response, dict) and isinstance(response.get("data"), list),
            "Unexpected native inventory response")
    return response["data"]


def validate_inventory(inventory):
    expected_profile = expected_config()
    providers, models = records(inventory["providers"]), records(inventory["models"])
    require(len(providers) == 1 and providers[0].get("id") == "local",
            "Effective provider inventory is not exclusively local")
    require(len(models) == 1 and models[0].get("providerID") == "local"
            and models[0].get("id") == "qwen", "Effective model inventory is not exclusively local/qwen")
    validate_route(providers[0], models[0])
    for agent in records(inventory["agents"]):
        require(agent.get("model") is None or local_reference(agent["model"]),
                f"Agent {agent.get('id')} selects a nonlocal/unexpected model")
    agents = {item.get("id"): item for item in records(inventory["agents"])}
    for name, item in expected_profile["agents"].items():
        ref = agents.get(name, {}).get("model")
        require(same_reference(ref, item["model"]),
                f"Effective agent {name} differs from this release's default model reference")
    # The command API exposes names/descriptions, not model refs; fold authored config instead.
    commands = {}
    defaults = {}
    entries = inventory["config"]
    require(isinstance(entries, list), "Unexpected native config response")
    for entry in entries:
        if entry.get("type") == "document":
            info = entry.get("info", {})
            for key in ("model", "default_agent"):
                if key in info:
                    defaults[key] = info[key]
            # Native Config.latest selects the last whole tool_output block.
            if "tool_output" in info:
                defaults["tool_output"] = {"max_bytes": 50 * 1024, "max_lines": 2000,
                                           **info["tool_output"]}
            # Native compaction config updates these supplied fields independently.
            configured = info.get("compaction", {})
            compaction = defaults.setdefault("compaction", {})
            for key in ("auto", "buffer"):
                if key in configured:
                    compaction[key] = configured[key]
            if "tokens" in configured.get("keep", {}):
                compaction["keep"] = {"tokens": configured["keep"]["tokens"]}
            for name, item in info.get("commands", {}).items():
                commands[name] = item  # Native command registration replaces the whole definition.
    validate_defaults(defaults, expected_profile)
    for name, item in commands.items():
        require(item.get("model") is None or local_reference(item["model"]),
                f"Command {name} selects a nonlocal/unexpected model")
    for name, item in expected_profile["commands"].items():
        require(same_reference(commands.get(name, {}).get("model"), item.get("model")),
                f"Effective command {name} differs from this release's model reference")
        require(all(commands[name].get(key) == item.get(key) for key in ("agent", "subagent")),
                f"Effective command {name} differs from this release's routing")


def inventory(server, config):
    providers, models = server.inventory()
    deadline = time.monotonic() + 20
    while True:
        result = {"providers": providers, "models": models}
        for name, endpoint in (("agents", "/api/agent"), ("commands", "/api/command"), ("config", "/api/config")):
            result[name] = server.request("GET", endpoint)
        ready = (set(config["agents"]) <= {a.get("id") for a in records(result["agents"])}
                 and set(config["commands"]) <= {c.get("name") for c in records(result["commands"])})
        if ready:
            # Refresh after all configured domains have initialized.
            result["providers"] = server.request("GET", "/api/provider")
            result["models"] = server.request("GET", "/api/model")
            require(all(Path(result[k].get("location", {}).get("directory", "")).resolve() == server.directory
                        for k in ("providers", "models")), "Native inventory belongs to a different project")
            validate_inventory(result)
            return result
        require(time.monotonic() < deadline, "Configured agents/commands did not finish initializing")
        time.sleep(0.25)


def mcp_status(server, config):
    expected = {name for name, value in config.get("mcp", {}).get("servers", {}).items()
                if value.get("enabled", True)}
    deadline = time.monotonic() + 30
    while True:
        items = records(server.request("GET", "/api/mcp"))
        states = {item["name"]: item["status"] for item in items}
        if expected <= states.keys() and all(states[name].get("status") != "pending" for name in expected):
            return states
        if time.monotonic() >= deadline:
            return {name: states.get(name, {"status": "missing"}) for name in expected | states.keys()}
        time.sleep(0.5)


def dependency_report(config):
    """Read-only checks; these are compatibility checks, not model acceptance."""
    free = shutil.disk_usage(ROOT).free
    require(free >= 8 * 1024**3, "Less than 8 GiB disk headroom; free space before using KRYN")
    with (OMLX.parents[1] / "Info.plist").open("rb") as stream:
        app = plistlib.load(stream)
    require((app.get("CFBundleIdentifier"), app.get("CFBundleShortVersionString")) == ("app.omlx", "0.6.4"),
            "Installed oMLX app identity/version differs from this release")
    package = json.loads((BINARY.parents[1] / "package.json").read_text())
    require(package.get("version") == "2.0.10", "Expected OpenCode 2.0.10")
    chrome = Path("/Applications/Google Chrome.app/Contents/Info.plist")
    require(chrome.is_file(), "Google Chrome is missing; browser tools are unavailable")
    with chrome.open("rb") as stream:
        browser_version = plistlib.load(stream).get("CFBundleShortVersionString", "")
    require(re.fullmatch(r"153\.\d+\.\d+\.\d+", browser_version), "Chrome major differs from the tested compatibility line")
    browser = config.get("mcp", {}).get("servers", {}).get("browser", {})
    node = browser.get("command", [None])[0]
    require(node is not None, "Browser Node executable is not configured")
    node_version = subprocess.check_output([node, "-p", "process.arch + ' ' + process.versions.node"],
                                           text=True, timeout=10, env=environment({})).strip()
    matched = re.fullmatch(r"arm64 22\.(\d+)\.(\d+)", node_version)
    require(matched and int(matched[1]) >= 23, "Expected native ARM64 Node 22.23 or later in the 22.x line")
    mcp_package = json.loads((ROOT / "browser/node_modules/@playwright/mcp/package.json").read_text())
    require(mcp_package.get("version") == "0.0.82", "Expected Playwright MCP 0.0.82")
    return {"disk_free_bytes": free, "opencode": "2.0.10", "omlx": "0.6.4",
            "chrome": browser_version, "node": node_version, "playwright_mcp": "0.0.82"}


def interrupt_owned_sessions(server):
    deadline = time.monotonic() + 30
    def request(method, path, body=None):
        remaining = deadline - time.monotonic()
        require(remaining > 0, "Owned-session interruption exceeded 30 seconds")
        return server.request(method, path, body, timeout=min(3, remaining))
    active = request("GET", "/api/session/active").get("data")
    require(isinstance(active, dict) and len(active) <= 64, "Cannot safely inspect active native sessions")
    for sid in active:
        require(re.fullmatch(r"ses_[A-Za-z0-9]+", sid), "Unexpected active session identifier")
        info = request("GET", "/api/session/" + sid).get("data", {})
        require(info.get("id") == sid and Path(info.get("location", {}).get("directory", "")).resolve() == server.directory
                and local_reference(info.get("model")), "Refusing to interrupt an unrelated native session")
        response = request("POST", "/api/session/" + sid + "/interrupt", {})
        require(type(response.get("interrupted")) is bool, "Native session interruption was not acknowledged")


def stop_child(child):
    if child is None or child.poll() is not None:
        return
    for action in (lambda: child.send_signal(signal.SIGINT), child.terminate, child.kill):
        action()
        try:
            child.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue
    raise RuntimeError("Owned client did not exit; no other process was targeted")


class ResourceStop(RuntimeError):
    """A resource refusal whose owned runtime must be released after cancellation."""


def memory_status():
    try:
        value = resources(RUNTIME)
    except Exception:
        value = {}
    level = value.get("pressure_level")
    listeners = value.get("listener_processes", [])
    return {"pressure": {1: "normal", 2: "warning", 4: "critical", 6: "critical"}.get(level, "unknown"),
            "pressure_level": level, "swap_used_bytes": value.get("swap_used_bytes"),
            "runtime_footprint_bytes": listeners[0].get("phys_footprint_bytes") if len(listeners) == 1 else None}


def guarded_run(server, command, project, outcome, timeout=None):
    """Monitor the native client; OpenCode still owns every agent/tool decision."""
    guard = ResourceGuard(512 * 1024**2, 2)
    guard.pid = runtime_identity()
    child = None
    def sample():
        try:
            value = resources(RUNTIME)
        except Exception:
            value = {}
        reason = guard.check(value)
        level = value.get("pressure_level", 0)
        if type(level) is int and level in {1, 2, 4, 6}:
            outcome["last_pressure_level"] = level
        outcome["pressure_warning_samples"] = (outcome.get("pressure_warning_samples") or 0) + int(type(level) is int and bool(level & 6))
        footprints = [p.get("phys_footprint_bytes") for p in value.get("listener_processes", [])]
        for footprint in footprints:
            if type(footprint) is int and footprint > 0:
                outcome["max_runtime_footprint_bytes"] = max(outcome.get("max_runtime_footprint_bytes", 0), footprint)
        swap = value.get("swap_used_bytes")
        if type(swap) is int and guard.baseline_swap is not None:
            outcome["swap_growth_bytes"] = max(outcome.get("swap_growth_bytes") or 0, swap - guard.baseline_swap)
        if reason:
            outcome["failure_code"] = "resource"
            raise ResourceStop("Resource guard stopped KRYN: " + reason
                               + f" (pressure={level}, swap growth={outcome.get('swap_growth_bytes', 0)} bytes)."
                               + " Saved session and completed file writes are retained."
                               + " After pressure settles, run kryn --continue in this project to resume.")
        return value
    try:
        for index in range(3):
            if sample().get("pressure_level") != 1:
                raise ResourceStop("Resource preflight needs three consecutive green samples; no generation started."
                                   " Let memory pressure settle, then run kryn --continue.")
            if index < 2:
                time.sleep(2)
        started = time.monotonic()
        child = subprocess.Popen(command, cwd=project, env=server.env)
        while True:
            try:
                code = child.wait(timeout=2)
                sample()
                return code
            except subprocess.TimeoutExpired:
                sample()
                if timeout is not None and time.monotonic() - started >= timeout:
                    outcome["failure_code"] = "timeout"
                    raise RuntimeError("Owned client exceeded its declared time limit")
    finally:
        original = sys.exc_info()[1]
        if child is not None and child.poll() is None and (guard.reason or outcome.get("failure_code") == "timeout"):
            outcome["interventions"] = outcome.get("interventions", 0) + 1
        errors = []
        for cleanup in (lambda: interrupt_owned_sessions(server), lambda: stop_child(child)):
            try:
                cleanup()
            except BaseException as error:
                errors.append(error)
        if errors:
            if original is not None:
                original.add_note("Owned client/session cleanup could not be fully verified")
            else:
                raise RuntimeError("Owned client/session cleanup could not be fully verified") from errors[0]


def await_runtime_idle():
    deadline, quiet = time.monotonic() + 30, 0
    while time.monotonic() < deadline:
        state = runtime_metadata()
        good = all(type(state.get(k)) is int and state[k] == 0 for k in ("active_requests", "waiting_requests"))
        quiet = quiet + 1 if good else 0
        if quiet >= 2:
            return
        time.sleep(.5)
    raise RuntimeError("Owned native server closed, but runtime idle could not be verified; stop and inspect before another run")


def initialize(args):
    if (ROOT / "xdg/config/opencode/opencode.json").exists():
        cfg = prerequisites(source_init=True)
        print(json.dumps({"existing_installation": "preserved", "dependencies": dependency_report(cfg),
                          "scope": "Configuration/dependencies checked only. Run kryn doctor for live health; release acceptance is pending."}, indent=2))
        return 0
    setup_script = PROJECT / "setup/setup.py"
    require(setup_script.is_file(), "Run init from the complete KRYN source kit; installed releases do not contain the installer")
    profile = args.profile or PROJECT / "setup/accepted-profile.json"
    require(profile.is_file(), "An explicit pinned install profile is required")
    command = [sys.executable, "-E", "-B", str(setup_script), "--profile", str(profile)]
    for name in ("node", "uv"):
        value = getattr(args, name)
        if value:
            command += ["--" + name, str(value)]
    if args.apply:
        command += ["--apply"]
    result = subprocess.run(command, cwd=PROJECT, check=False)
    if result.returncode == 0:
        print("Bootstrap " + ("finished; run kryn doctor. Acceptance remains pending." if args.apply
                                else "preflight passed; repeat with --apply to install."))
    return result.returncode


def self_check():
    config = expected_config()
    validate_owned_config(config)
    for change in ("provider", "model", "variant", "policy", "reference", "global_skills", "desktop_browser"):
        altered = copy.deepcopy(config)
        provider = altered["providers"]["local"]
        model = provider["models"]["qwen"]
        if change == "provider":
            provider["settings"]["baseURL"] = "https://example.invalid/v1"
        elif change == "model":
            model["package"] = "untrusted-package"
        elif change == "variant":
            model["variants"][0]["settings"]["baseURL"] = "https://example.invalid/v1"
        elif change == "policy":
            altered["experimental"]["policies"].reverse()
        elif change == "reference":
            altered["agents"]["plan"]["model"] = "openai/remote"
        elif change == "global_skills":
            altered["plugins"].remove("-opencode.config.compatibility")
        else:
            altered["plugins"].remove("-opencode.browser")
        try:
            validate_owned_config(altered)
        except RuntimeError:
            continue
        raise AssertionError(f"Failed to reject {change} mutation")
    assert local_reference({"providerID": "local", "id": "qwen", "variant": "think"})
    assert not local_reference("local/qwen#unknown")
    provider = copy.deepcopy(config["providers"]["local"])
    model = provider.pop("models")["qwen"]
    example = {"providers": {"data": [{"id": "local", **provider}]},
               "models": {"data": [{"id": "qwen", "providerID": "local", **model}]},
               "agents": {"data": [{"id": name, "model": item["model"]}
                                    for name, item in config["agents"].items()]},
               "config": [{"type": "document", "info": config}]}
    validate_inventory(example)
    example["providers"]["data"].append({"id": "cloud"})
    try:
        validate_inventory(example)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Failed to reject extra effective provider")
    print("Offline self-check passed: local routing, variants, provider policy and model references.")


def run(args, outcome):
    command = args.command_or_project
    require(getattr(args, "auto", False) is not True or command not in {"init", "doctor", "status", "stop", "bench"},
            "--auto is supported only for an interactive coding launch")
    require(not args.json_cli or command not in {"init", "doctor", "status", "stop", "bench"},
            "--json-cli is a scoped coding launch; start a new native session to use its current guidance")
    require(not args.deep or command == "doctor", "--deep is supported only by kryn doctor")
    if command == "init":
        return initialize(args)
    require(not args.apply and args.profile is None and args.node is None and args.uv is None,
            "Bootstrap options are supported only by kryn init")
    if command == "stop":
        runtime_identity()
        state = runtime_metadata()
        require(state.get("active_requests") == 0 and state.get("waiting_requests") == 0,
                "Runtime is busy; finish or interrupt its work before stopping it")
        runtime_command("stop")
        print("Stopped the verified owned oMLX runtime. Existing Ollama was not targeted.")
        return 0
    if command == "status":
        try:
            health = runtime_metadata()
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            health = {"healthy": False, "state": "stopped_or_unavailable"}
        try:
            authorization = {"authorized": True, "expires_at": owner_auth.authorize()["expires_at"]}
        except owner_auth.AuthorizationError:
            authorization = {"authorized": False}
        print(json.dumps({**health, "owner_session": authorization,
                          "memory": memory_status(),
                          "improvement": learning.status(ROOT / "state/improvement")}, indent=2))
        return 0
    project = (Path(args.project or ".") if command == "launch" else
               Path.cwd() if command in {"doctor", "bench"} else Path(command)).expanduser().resolve()
    require(project.is_dir(), f"Project directory does not exist: {project}")
    if command not in {"doctor", "bench"}:
        require(project != Path.home().resolve(), "Enter a project directory first, then run kryn.")
    outcome["failure_code"] = "config"
    config = with_verified_skill(prerequisites(), json_cli=args.json_cli)
    dependencies = dependency_report(config)
    if command == "doctor":
        dependencies["model_integrity"] = model_integrity(args.deep)
        if args.deep:
            from kryn.installer import verify_browser
            verify_browser(ROOT, adopt=False)
            dependencies["browser_integrity"] = "all installed dependency files verified"
    outcome["failure_code"] = "runtime"
    if command == "doctor":
        try:
            health = runtime_metadata()
            runtime_identity()
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            health = {"healthy": False, "error": str(error)}
    else:
        health = ensure_runtime()
        require(all(type(health.get(k)) is int and health[k] == 0 for k in ("active_requests", "waiting_requests")),
                "Local runtime is busy; wait for its existing work before launching KRYN")
    invoked = False
    try:
        with ExitStack() as stack:
            if command in {"doctor", "bench"}:
                project = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="kryn-check-", dir="/private/tmp")))
            server = stack.enter_context(NativeServer(project, config=config))
            outcome["failure_code"] = "config"
            inventory(server, config)
            outcome["failure_code"] = "tools"
            mcp = mcp_status(server, config) if command != "bench" else {}
            if command == "doctor":
                memory = memory_status()
                print(json.dumps({"prerequisites": dependencies, "native_local_routing": "pass", "runtime": health,
                                  "memory": memory,
                                  "mcp": mcp, "scope": "Configuration and dependency checks; generation and browser interactions are not run."}, indent=2))
                return 0 if health["healthy"] and memory["pressure"] == "normal" and all(v.get("status") == "connected" for v in mcp.values()) else 1
            if command == "bench":
                print("Running guarded protocol smoke; this is not the full coding evaluation suite.", flush=True)
                executable = [sys.executable, "-E", "-B", str(PROJECT / "tools/protocol_probe.py"),
                              "--base-url", RUNTIME, "--model", MODEL_ID, "--runs-dir", str(ROOT / "runs"),
                              "--mode", "smoke", "--max-tokens", "1024", "--timeout", "180"]
            else:
                unavailable = sorted(name for name, state in mcp.items() if state.get("status") != "connected")
                if unavailable:
                    print("Local coding is available; unavailable tools: " + ", ".join(unavailable)
                          + ". Run kryn doctor for details.", file=sys.stderr, flush=True)
                executable = [str(BINARY), "--server", server.url, str(project)]
                if getattr(args, "auto", False) is True:
                    executable.append("--auto")
                if getattr(args, "continue_session", False) is True:
                    executable.append("--continue")
                if isinstance(getattr(args, "session", None), str):
                    selected = server.request("GET", "/api/session/" + args.session).get("data", {})
                    require(selected.get("id") == args.session and selected.get("location", {}).get("directory") == str(project)
                            and local_reference(selected.get("model")), "Resume session must belong to this local project")
                    executable.extend(["--session", args.session])
            outcome["failure_code"] = "resource"
            invoked = True
            code = guarded_run(server, executable, project, outcome, timeout=1500 if command == "bench" else None)
            outcome["failure_code"] = "none" if code == 0 else "verification" if command == "bench" else "unknown"
            return code
    finally:
        if invoked:
            original = sys.exc_info()[1]
            try:
                await_runtime_idle()
                if isinstance(original, ResourceStop):
                    runtime_identity()
                    runtime_command("stop")
                    print("Released the idle KRYN model server after the resource stop."
                          " Resume with kryn --continue; the server will start automatically.", file=sys.stderr)
            except BaseException as error:
                if original is not None:
                    original.add_note("Runtime idle could not be verified after owned native shutdown")
                    print("kryn: resource cleanup could not be verified; inspect kryn status before retrying.", file=sys.stderr)
                else:
                    raise error


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv in (["login"], ["logout"]):
        if argv[0] == "login":
            owner_auth.login()
            print("Owner verified with GitHub Keychain credentials. Offline session is valid for seven days.")
        else:
            owner_auth.logout()
            print("KRYN owner session removed. Existing GitHub CLI authentication was preserved.")
        return 0
    if argv and argv[0] == "improve":
        owner_auth.authorize()
        verify_release()
        require(len(argv) <= 2, "Usage: kryn improve [status|pause|resume|disable|enable]")
        action = argv[1] if len(argv) == 2 else "status"
        require(action in {"status", "pause", "resume", "disable", "enable"},
                "Use status, pause, resume, disable or enable; legacy manual promotion is not a product gate")
        result = (learning.status(ROOT / "state/improvement") if action == "status"
                  else learning.control(ROOT / "state/improvement", action))
        print(json.dumps(result, indent=2))
        return 0
    parser = argparse.ArgumentParser(prog="kryn", description=__doc__, epilog=(
        "Ordinary shell writes are restricted to the project and owned state/temp/log paths. "
        "Native/shell scratch uses a private project child; browser infrastructure uses separate private temp. "
        "Native file tools, browser/MCP, formatters and persistent PTY are outside this guard; reads and network are not isolated. "
        "Project configuration is trusted. Native explicit plan files use ~/.opencode/plan."))
    parser.add_argument("command_or_project", nargs="?", default=".", help="project directory, launch, init, status, doctor, bench, stop, or improve (--help)")
    parser.add_argument("project", nargs="?", help="project directory for launch")
    parser.add_argument("--apply", action="store_true", help="init only: explicitly apply the existing installer")
    parser.add_argument("--profile", type=Path, help="init only: pinned profile file")
    parser.add_argument("--node", type=Path, help="init only: native Node executable")
    parser.add_argument("--uv", type=Path, help="init only: uv executable")
    parser.add_argument("--self-check", action="store_true", help="offline validator checks; no services or inference")
    parser.add_argument("--deep", action="store_true", help="doctor only: rehash every pinned model file (slow; no inference)")
    parser.add_argument("--json-cli", action="store_true", help="apply validated workflow guidance for JSON command-line programs in new native sessions")
    parser.add_argument("--auto", action="store_true", help="this launch only: auto-approve native permission requests unless explicitly denied; includes browser/network actions, not just edits")
    resume = parser.add_mutually_exclusive_group()
    resume.add_argument("--continue", dest="continue_session", action="store_true", help="open the latest saved session in this project")
    resume.add_argument("--session", help="open a saved session ID belonging to this project")
    args = parser.parse_args(argv)
    require(args.session is None or re.fullmatch(r"ses_[A-Za-z0-9]+", args.session), "Invalid native session ID")
    require(not (args.continue_session or args.session) or args.command_or_project not in {"init", "doctor", "status", "stop", "bench"},
            "Session resume options are supported only for a coding launch")
    require(args.project is None or args.command_or_project == "launch", "Extra project argument requires launch")
    if args.self_check:
        self_check()
        return 0
    command = args.command_or_project if args.command_or_project in {"init", "doctor", "status", "stop", "bench"} else "run"
    if command not in {"status", "stop"}:
        owner_auth.authorize()
    outcome = {"command": command, "status": "failure", "wall_seconds": 0, "exit_code": None,
               "failure_code": "unknown", "interventions": 0, "pressure_warning_samples": None,
               "swap_growth_bytes": None, "release_id": PROJECT.name if re.fullmatch(r"[a-f0-9]{16}", PROJECT.name) else None,
               "profile_id": None}
    profile = PROJECT / "setup/install-profile.json"
    if profile.is_file():
        outcome["profile_id"] = hashlib.sha256(profile.read_bytes()).hexdigest()
    started = time.monotonic()
    try:
        with (learning.foreground(ROOT / "state/improvement") if command in {"run", "bench"} else nullcontext()):
            code = run(args, outcome)
        outcome.update(exit_code=code, status="success" if code == 0 else "failure")
        if code == 0:
            outcome["failure_code"] = "none"
            if command == "run":
                # A native TUI exit does not verify any task's acceptance criteria.
                outcome.update(status="incomplete", failure_code="unknown")
        return code
    except KeyboardInterrupt:
        outcome.update(status="interrupted", failure_code="interrupted", exit_code=130, interventions=1)
        raise
    finally:
        original = sys.exc_info()[1]
        outcome["wall_seconds"] = round(time.monotonic() - started, 3)
        try:
            improvement.record_outcome(ROOT / "state/improvement", outcome)
        except Exception as error:
            print("kryn: outcome recording failed (" + type(error).__name__ + "); no private task content was recorded", file=sys.stderr)
            if original is None:
                raise RuntimeError("KRYN outcome was not recorded; inspect the owned state directory") from error
        if command == "run" and original is None:
            try:
                learning.start_after_exit(ROOT / "state/improvement", with_verified_skill(owned_config()))
            except Exception as error:
                # Optional learning must not convert completed user work into a failed launch.
                print("kryn: background improvement deferred (" + type(error).__name__ + ")", file=sys.stderr)


if __name__ == "__main__":
    def interrupted(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"kryn: {error}", file=sys.stderr)
        sys.exit(1)
