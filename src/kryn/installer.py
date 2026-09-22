"""Receipt-checked installation, owned-file transaction and exact rollback.

Dependencies/models are additive and verified by the existing setup primitives.
Only configuration, profile, deployment receipt and owned launchers are activated.
"""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import urllib.parse
from . import __version__

NODE_URL = "https://nodejs.org/dist/v22.23.1/node-v22.23.1-darwin-arm64.tar.gz"
NODE_SHA = "ef28d8fab2c0e4314522d4bb1b7173270aa3937e93b92cb7de79c112ac1fa953"


def root_path():
    return Path.home() / "Library/Application Support/LocalAI"


def payload():
    return Path(__file__).parent / "payload"


def digest(file):
    result = hashlib.sha256()
    with Path(file).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def safe_path(file):
    file = Path(file).absolute()
    if any(p.is_symlink() for p in (file, *file.parents)):
        raise RuntimeError("Linked installation paths are refused")
    existing = next(p for p in (file, *file.parents) if p.exists())
    if existing.stat().st_uid not in (0, os.geteuid()) or existing.stat().st_mode & 0o022:
        raise RuntimeError("Installation path is not owned and protected")
    return file


def safe_json(file):
    file = safe_path(file)
    with file.open() as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1024 * 1024:
            raise RuntimeError("Unsafe installation receipt")
        return json.load(stream)


def verify_payload(base=None, manifest=None):
    base = Path(base or payload())
    manifest = manifest or json.loads((Path(__file__).parent / "manifest.json").read_text())
    if manifest.get("schema") != 1 or manifest.get("version") != __version__:
        raise RuntimeError("Package identity mismatch")
    for relative, expected in manifest["files"].items():
        name = Path(relative)
        if name.is_absolute() or ".." in name.parts or not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise RuntimeError("Invalid package payload manifest")
        file = base / name
        if not file.is_file() or any(p.is_symlink() for p in (file, *file.parents)) or digest(file) != expected:
            raise RuntimeError("Package payload failed integrity: " + relative)
    actual = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != set(manifest["files"]):
        raise RuntimeError("Package has unexpected or missing payload files")
    return manifest


def module(name):
    directory = payload() / ("setup" if name == "setup" else "tools")
    for folder in (payload() / "tools", payload() / "setup"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location("kryn_payload_" + name, directory / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def atomic_write(file, data, mode=0o600):
    file = safe_path(file)
    file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".kryn-activate-", dir=file.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, file)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Transaction:
    def __init__(self, folder, paths, planned=None):
        self.folder = safe_path(folder)
        self.folder.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.rows = []
        for index, file in enumerate(paths):
            file = safe_path(file)
            if file.exists():
                info = file.stat()
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid():
                    raise RuntimeError("Preserving unowned activation file: " + str(file))
                data = file.read_bytes()
                backup = self.folder / str(index)
                backup.write_bytes(data)
                backup.chmod(0o600)
                before = {"sha256": digest(backup), "mode": stat.S_IMODE(info.st_mode), "backup": str(index)}
            else:
                before = None
            row = {"path": str(file), "before": before}
            if planned is not None:
                row["planned"] = hashlib.sha256(planned[file]).hexdigest() if planned.get(file) is not None else None
            self.rows.append(row)
        self.save("prepared")

    def save(self, status):
        atomic_write(self.folder / "transaction.json", json.dumps({"schema": 1, "status": status,
                     "files": self.rows}, indent=2).encode())

    def finish(self):
        for row in self.rows:
            file = safe_path(row["path"])
            row["after"] = digest(file) if file.exists() else None
        self.save("committed")

    def restore(self, require_after=False, require_planned=False, resume_rollback=False):
        # Validate every destination and backup before the first restoration write.
        for row in self.rows:
            file = safe_path(row["path"])
            if require_after and (digest(file) if file.exists() else None) != row.get("after"):
                raise RuntimeError("Preserving changed file during rollback: " + str(file))
            if resume_rollback:
                before = row["before"]["sha256"] if row["before"] else None
                if (digest(file) if file.exists() else None) not in {before, row["after"]}:
                    raise RuntimeError("Preserving changed file during interrupted rollback: " + str(file))
            if require_planned:
                before = row["before"]["sha256"] if row["before"] else None
                if "planned" not in row or (digest(file) if file.exists() else None) not in {before, row["planned"]}:
                    raise RuntimeError("Preserving unknown change during interrupted installation recovery: " + str(file))
            if row["before"] and digest(safe_path(self.folder / row["before"]["backup"])) != row["before"]["sha256"]:
                raise RuntimeError("Rollback backup failed integrity")
        if require_after:
            # active.json is restored first. Persist intent before it can point
            # at an older transaction, so a retry resumes this one exactly once.
            self.save("rolling_back")
        for row in reversed(self.rows):
            file = Path(row["path"])
            if row["before"]:
                atomic_write(file, (self.folder / row["before"]["backup"]).read_bytes(), row["before"]["mode"])
            elif file.exists():
                file.unlink()
        self.save("rolled_back")


def platform_check(profile):
    if platform.system() != "Darwin" or platform.machine() != "arm64" or sys.version_info < (3, 13):
        raise RuntimeError("KRYN requires native Apple Silicon macOS with Python 3.13+")
    if int(platform.mac_ver()[0].split(".")[0]) not in (26, 27):
        raise RuntimeError("Upstream supports this runtime on macOS 26/27; KRYN measurements cover the recorded Mac only")
    memory = int(subprocess.check_output(["/usr/sbin/sysctl", "-n", "hw.memsize"]))
    if memory < 48 * 1024**3 or profile["memory_gib"] > memory / 1024**3 - 8:
        raise RuntimeError("This profile requires 48 GiB RAM and at least 8 GiB outside the model ceiling")


def selected_node(root, setup, env):
    candidates = [shutil.which("node"), str(root / "dependencies/node-v22.23.1-darwin-arm64/bin/node")]
    candidates += [str(p) for p in sorted((Path.home() / ".nvm/versions/node").glob("v22.*/bin/node"), reverse=True)]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        result = subprocess.run([candidate, "-p", "process.arch + ' ' + process.versions.node"], capture_output=True, text=True, timeout=10)
        match = re.fullmatch(r"arm64 22\.(\d+)\.(\d+)", result.stdout.strip())
        if result.returncode == 0 and match and tuple(map(int, match.groups())) >= (23, 1) and Path(candidate).with_name("npm").exists():
            return Path(candidate).resolve()
    archive = root / "downloads/node-v22.23.1-darwin-arm64.tar.gz"
    setup.download(NODE_URL, archive, "sha256", NODE_SHA)
    destination = safe_path(root / "dependencies/node-v22.23.1-darwin-arm64")
    if destination.exists():
        raise RuntimeError("Preserving incomplete private Node installation")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    stage = Path(tempfile.mkdtemp(prefix=".node-stage-", dir=destination.parent))
    try:
        with tarfile.open(archive) as bundle:
            bundle.extractall(stage, filter="data")
        source = stage / destination.name
        if not (source / "bin/node").is_file():
            raise RuntimeError("Private Node archive missing executable")
        source.rename(destination)
    finally:
        shutil.rmtree(stage)
    return destination / "bin/node"


def browser_inventory(tree):
    tree = safe_path(tree)
    if not tree.is_dir(): raise RuntimeError("Browser dependency tree is missing")
    result = {}
    for file in sorted(tree.rglob("*")):
        info = file.lstat()
        if info.st_uid != os.geteuid() or info.st_mode & 0o022 and not file.is_symlink():
            raise RuntimeError("Browser dependency ownership or permissions changed")
        if file.is_symlink():
            target = os.readlink(file)
            if Path(target).is_absolute() or not file.resolve().is_relative_to(tree):
                raise RuntimeError("Browser dependency link leaves the owned tree")
            item = ["link", target]
        elif stat.S_ISREG(info.st_mode): item = ["file", digest(file), bool(info.st_mode & 0o111)]
        elif stat.S_ISDIR(info.st_mode): continue
        else: raise RuntimeError("Unexpected browser dependency file type")
        result[file.relative_to(tree).as_posix()] = item
    return result


def verify_browser(root, setup=None, node=None, env=None, *, adopt=True):
    directory = root / "browser"
    tree, receipt = directory / "node_modules", directory / "integrity.json"
    if not adopt and not receipt.is_file():
        raise RuntimeError("Existing browser integrity receipt is required; rerun the private installer")
    fresh = not tree.exists() and not tree.is_symlink()
    if fresh:
        if not adopt:
            raise RuntimeError("Browser dependency tree is missing; read-only verification cannot reinstall it")
        setup.npm_install(root, node, "browser", "@playwright/mcp@0.0.82", env)
    lock_hash = digest(payload() / "setup/browser-package-lock.json")
    if (safe_json(tree / "@playwright/mcp/package.json").get("version") != "0.0.82" or
            digest(safe_path(directory / "package-lock.json")) != lock_hash):
        raise RuntimeError("Preserving incompatible or changed browser dependencies")
    current = browser_inventory(tree)
    expected = {"schema": 1, "package": "@playwright/mcp@0.0.82", "lock_sha256": lock_hash, "files": current}
    if receipt.exists():
        if safe_json(receipt) != expected:
            raise RuntimeError("Preserving changed browser dependency bytes; integrity receipt differs")
    else:
        if not adopt:
            raise RuntimeError("Browser integrity receipt disappeared during read-only verification")
        if not fresh:
            # Reconstruct the original-publisher baseline, never bless an existing
            # tree merely because its package version and lockfile match.
            with tempfile.TemporaryDirectory(prefix=".browser-verify-", dir=root) as temporary:
                stage = Path(temporary)
                setup.npm_install(stage, node, "browser", "@playwright/mcp@0.0.82", env)
                if browser_inventory(stage / "browser/node_modules") != current:
                    raise RuntimeError("Preserving changed browser dependencies; original-publisher comparison failed")
        atomic_write(receipt, json.dumps(expected, sort_keys=True, indent=2).encode() + b"\n")
    return receipt


def installed_client(root):
    receipt_path = root / "client/deployment.json"
    if not receipt_path.exists():
        return None
    receipt = safe_json(receipt_path)
    directory = Path(receipt["directory"])
    if directory.parent != root / "client" or not re.fullmatch(r"[a-f0-9]{16}", directory.name):
        raise RuntimeError("Invalid owned client directory")
    for name, expected in receipt["files"].items():
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise RuntimeError("Invalid owned client manifest path")
        file = safe_path(directory / name)
        if not file.is_file() or digest(file) != expected:
            raise RuntimeError("Preserving changed installed client: " + name)
    return receipt


def guard_runtime(root, stop=False):
    with socket.socket() as connection:
        connection.settimeout(1)
        if connection.connect_ex(("127.0.0.1", 8000)) != 0:
            return
    receipt = installed_client(root)
    if receipt is None:
        raise RuntimeError("Preserving occupied runtime without an owned client receipt")
    # Use the active client's pinned model, not the new package's upgrade profile.
    # A separate interpreter also prevents previously imported new native_client
    # globals from replacing the installed release's identity checks.
    program = """import sys
sys.path.insert(0, sys.argv[1])
import localai
localai.runtime_identity()
state = localai.runtime_metadata()
if not all(type(state.get(k)) is int and state[k] == 0 for k in ('active_requests', 'waiting_requests')):
    raise RuntimeError('Runtime is busy or its idle state is unknown; installation cannot stop it')
if sys.argv[2] == 'stop':
    localai.runtime_command('stop')
"""
    subprocess.run([sys.executable, "-I", "-B", "-c", program,
                    str(Path(receipt["directory"]) / "tools"), "stop" if stop else "check"], check=True)
    if stop:
        deadline = time.monotonic() + 15
        while True:
            with socket.socket() as connection:
                connection.settimeout(0.5)
                if connection.connect_ex(("127.0.0.1", 8000)) != 0:
                    return
            if time.monotonic() >= deadline:
                raise RuntimeError("Runtime acknowledged stop but port 8000 remains occupied; configuration preserved")
            time.sleep(0.1)


def check_existing(root, setup):
    receipt = installed_client(root)
    if receipt is None:
        for file in (root / "xdg/config/opencode/opencode.json", root / "install-profile.json",
                     Path.home() / ".omlx/settings.json", Path.home() / ".omlx/model_settings.json"):
            if file.exists():
                raise RuntimeError("Preserving installation without ownership receipt: " + str(file))
        return None
    directory = Path(receipt["directory"])
    for file in aliases(root):
        if file.exists() and (file.is_symlink() or file.read_text() != receipt["launcher"]):
            raise RuntimeError("Preserving changed or unowned launcher: " + str(file))
    # The native owned config must still equal its installed template after original setup substitutions.
    config_path = root / "xdg/config/opencode/opencode.json"
    config = safe_json(config_path)
    template = safe_json(directory / "setup/opencode.template.json")
    command = config.get("mcp", {}).get("servers", {}).get("browser", {}).get("command", [])
    node = command[0] if command else ""
    def replace(value):
        if isinstance(value, str):
            return (value.replace("__ROOT__", str(root)).replace("__NODE__", node)
                    .replace("__KRYN_PLUGIN__", receipt.get("plugin_directory", "__KRYN_PLUGIN__"))
                    .replace("__KRYN_STATE__", str(root / "state/improvement"))
                    .replace("__PROFILE_ID__", hashlib.sha256(setup.encode(safe_json(directory / "setup/install-profile.json")).encode()).hexdigest()))
        if isinstance(value, list): return [replace(v) for v in value]
        if isinstance(value, dict): return {k: replace(v) for k, v in value.items()}
        return value
    expected = replace(template)
    # New releases already materialize the trusted plugin object in their installed template.
    if config != expected:
        raise RuntimeError("Owned OpenCode configuration was customized; preserve it before updating")
    runtime = safe_json(directory / "setup/runtime-profile.json")
    for file, expected_part in ((Path.home() / ".omlx/settings.json", runtime["global"]),
                                (Path.home() / ".omlx/model_settings.json", runtime["model"])):
        if not contains_settings(safe_json(file), expected_part):
            raise RuntimeError("Owned runtime profile was customized; preserve it before updating")
    guidance = root / "xdg/config/opencode/AGENTS.md"
    prior_guidance = directory / "setup/AGENTS.md"
    expected_guidance = (prior_guidance if prior_guidance.exists() else payload() / "setup/AGENTS.md").read_text() + f"\nIf installed, use {root}/artifacts/.venv/bin/python for document/data tasks.\n"
    if guidance.exists() and guidance.read_text() != expected_guidance:
        raise RuntimeError("Preserving customized installation guidance")
    return receipt


def merge_settings(current, changes):
    result = dict(current)
    for key, value in changes.items():
        result[key] = merge_settings(result.get(key, {}), value) if isinstance(value, dict) else value
    return result


def contains_settings(actual, expected):
    return isinstance(actual, dict) and all(
        contains_settings(actual.get(key), value) if isinstance(value, dict) else actual.get(key) == value
        for key, value in expected.items())


def aliases(root):
    return [root / "kryn", root / "localai", Path.home() / ".local/bin/kryn", Path.home() / ".local/bin/localai"]


def activation_paths(root):
    return [root / "xdg/config/opencode/opencode.json", root / "install-profile.json",
        root / "xdg/config/opencode/AGENTS.md", Path.home() / ".omlx/settings.json",
        Path.home() / ".omlx/model_settings.json", root / "client/deployment.json", *aliases(root), root / "packages/active.json"]


def load_transaction(root, folder):
    folder = safe_path(folder)
    if folder.parent != root / "packages/transactions": raise RuntimeError("Invalid rollback transaction")
    data = safe_json(folder / "transaction.json")
    transaction = object.__new__(Transaction)
    transaction.folder, transaction.rows = folder, data["files"]
    allowed = {str(p) for p in activation_paths(root)}
    if data.get("schema") != 1 or len(transaction.rows) != len(allowed) or {row["path"] for row in transaction.rows} != allowed:
        raise RuntimeError("Rollback contains unexpected activation targets")
    for row in transaction.rows:
        if row["before"] and not re.fullmatch(r"[0-9]+", row["before"]["backup"]):
            raise RuntimeError("Invalid rollback backup name")
    return transaction, data["status"]


def recover(root):
    restored_transaction = False
    for file in sorted((root / "packages/transactions").glob("*/transaction.json"), reverse=True):
        transaction, status = load_transaction(root, file.parent)
        if status in {"prepared", "rolling_back"}:
            # A prior crash may have been followed by a separately restarted app.
            # Never restore runtime settings beneath busy or unidentifiable work.
            guard_runtime(root, stop=True)
            if status == "rolling_back":
                transaction.restore(resume_rollback=True)
            else:
                transaction.restore(require_planned=True)
            restored_transaction = True
    return restored_transaction


def install():
    os.umask(0o077)
    manifest = verify_payload()
    setup, auth, learning = module("setup"), module("owner_auth"), module("learning")
    profile = setup.load_profile(payload() / "setup/accepted-profile.json")
    platform_check(profile)
    root = safe_path(root_path())
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try: auth.authorize()
    except auth.AuthorizationError: auth.login()
    uv = shutil.which("uv") or str(root / "dependencies/uv-0.11.16/uv")
    if not Path(uv).is_file(): uv = str(Path.home() / ".local/bin/uv")
    if not Path(uv).is_file():
        raise RuntimeError("The private installer must provide uv")
    if not Path("/Applications/Google Chrome.app").is_dir():
        raise RuntimeError("Install Google Chrome for this qualified browser profile, then rerun the installer")
    state = root / "state/improvement"
    with learning.foreground(state):
        recover(root)
        check_existing(root, setup)
        current = root / "packages/active.json"
        same_package = (current.exists()
                        and safe_json(current).get("payload_manifest_sha256") == digest(Path(__file__).parent / "manifest.json")
                        and not safe_json(current).get("deactivated")
                        and all(file.is_file() for file in activation_paths(root)))
        env = {k: v for k, v in os.environ.items() if not any(x in k.upper() for x in ("TOKEN", "API_KEY", "SECRET"))}
        env.update(PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD="1", HF_HUB_DISABLE_IMPLICIT_TOKEN="1", HF_HUB_DISABLE_XET="1",
                   UV_CACHE_DIR=str(root / "uv-cache"))
        node = selected_node(root, setup, env)
        env["PATH"] = str(node.parent) + os.pathsep + env.get("PATH", "")
        model_dir, model_marker, model_identity = setup.model_destination(root, profile)
        missing = [n for n in profile["files"] if not (model_dir / n).exists()]
        if missing:
            total = 0
            for name in missing:
                url = "https://huggingface.co/" + profile["repository"] + "/resolve/" + profile["revision"] + "/" + urllib.parse.quote(name, safe="/")
                with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as response:
                    size = response.headers.get("Content-Length")
                    if not size or not size.isdigit(): raise RuntimeError("Cannot establish download disk budget")
                    total += int(size)
            if shutil.disk_usage(root).free < total + 40 * 1024**3:
                raise RuntimeError("Model download would leave less than 40 GiB disk reserve")
        setup.download_omlx(root / "downloads/oMLX-0.6.4-macos26-27.dmg")
        archive = root / "downloads/opencode-2.0.10.tgz"
        setup.download(setup.CLI_URL, archive, "sha512", setup.CLI_SHA)
        setup.extract_cli(archive, root / "opencode/2.0.10")
        verify_browser(root, setup, node, env)
        setup.write_same(model_marker, model_identity)
        setup.download_model(uv, model_dir, profile, env)
        setup.install_app(root, env)
        for name, data in setup.plugin_files().items():
            setup.write_same(setup.plugin_directory(root) / name, data.decode() if isinstance(data, bytes) else data)
        if same_package:
            print("KRYN " + __version__ + " is already active; package, model and app integrity checked.")
            return
        files = {root / "xdg/config/opencode/opencode.json": setup.encode(setup.render(root, node, profile)),
                 root / "install-profile.json": setup.encode(profile),
                 root / "xdg/config/opencode/AGENTS.md": (payload() / "setup/AGENTS.md").read_text() +
                    f"\nIf installed, use {root}/artifacts/.venv/bin/python for document/data tasks.\n",
                 # Match oMLX's float values and no trailing newline: app startup
                 # must not invalidate the rollback transaction's exact hashes.
                 Path.home() / ".omlx/settings.json": json.dumps(merge_settings(
                    safe_json(Path.home() / ".omlx/settings.json") if (Path.home() / ".omlx/settings.json").exists() else {},
                    setup.runtime_settings(root, profile)), indent=2)}
        model_settings_path = Path.home() / ".omlx/model_settings.json"
        models = safe_json(model_settings_path) if model_settings_path.exists() else {"version": 1, "models": {}}
        for value in models.get("models", {}).values(): value["is_default"] = False
        models.setdefault("models", {}).update(setup.model_settings(profile)["models"])
        files[model_settings_path] = setup.encode(models)
        # Stop only an identity-verified owned runtime, and only when its settings change.
        changes_runtime = any(p.exists() and p.read_text() != text for p, text in files.items() if p.parent.name == ".omlx")
        guard_runtime(root, stop=changes_runtime)
        active = root / "packages/active.json"
        folder = root / "packages/transactions" / (str(time.time_ns()) + "-" + __version__)
        deployment_command = [sys.executable, "-E", "-B", str(payload() / "setup/deploy_client.py"),
            "--profile", str(payload() / "setup/accepted-profile.json"), "--entry-python", sys.executable]
        plan = json.loads(subprocess.check_output([*deployment_command, "--plan-json"], env=env, text=True))
        active_bytes = json.dumps({"schema": 1, "version": __version__, "python": sys.executable,
            "source_revision": manifest["source_revision"], "payload_manifest_sha256": digest(Path(__file__).parent / "manifest.json"),
            "transaction": str(folder)}, indent=2).encode()
        planned = {file: text.encode() for file, text in files.items()}
        planned[root / "client/deployment.json"] = (json.dumps(plan, indent=2) + "\n").encode()
        planned.update({file: plan["launcher"].encode() for file in aliases(root)})
        planned[active] = active_bytes
        transaction = Transaction(folder, activation_paths(root), planned)
        try:
            for file, text in files.items(): atomic_write(file, text.encode())
            subprocess.run([*deployment_command, "--apply", "--smoke-check"], check=True, env=env)
            atomic_write(active, active_bytes)
            transaction.finish()
        except BaseException:
            transaction.restore(require_planned=True)
            raise
    print("KRYN " + __version__ + " installed. Enter a project directory and run kryn.")


def rollback():
    verify_payload()
    auth, learning = module("owner_auth"), module("learning")
    auth.authorize()
    root = root_path()
    with learning.foreground(root / "state/improvement"):
        if not recover(root):
            active = safe_json(root / "packages/active.json")
            transaction, status = load_transaction(root, active["transaction"])
            if status != "committed": raise RuntimeError("No committed rollback transaction")
            guard_runtime(root, stop=True)
            transaction.restore(require_after=True)
    print("Previous owned configuration and launchers restored; retained dependencies/models remain available.")


def uninstall():
    """Deactivate owned entry points; retain all data and installed dependencies."""
    verify_payload()
    setup, auth, learning = module("setup"), module("owner_auth"), module("learning")
    auth.authorize()
    root = root_path()
    with learning.foreground(root / "state/improvement"):
        recover(root)
        active = root / "packages/active.json"
        if not active.exists():
            if any(path.exists() or path.is_symlink() for path in aliases(root)):
                raise RuntimeError("Preserving launchers without an active package receipt")
            print("KRYN is already deactivated; retained data was not changed.")
            return
        if check_existing(root, setup) is None:
            raise RuntimeError("An owned client receipt is required to deactivate KRYN")
        current = safe_json(active)
        if current.get("deactivated") is True and not any(path.exists() for path in aliases(root)):
            print("KRYN is already deactivated; retained data was not changed.")
            return
        guard_runtime(root, stop=True)
        paths = activation_paths(root)
        planned = {path: path.read_bytes() for path in paths if path.exists()}
        planned.update({path: None for path in aliases(root)})
        folder = root / "packages/transactions" / (str(time.time_ns()) + "-deactivate")
        planned[active] = json.dumps({**current, "deactivated": True, "transaction": str(folder)}, indent=2).encode()
        transaction = Transaction(folder, paths, planned)
        try:
            for path in aliases(root):
                if path.exists(): path.unlink()
            atomic_write(active, planned[active])
            transaction.finish()
        except BaseException:
            transaction.restore(require_planned=True)
            raise
    print("KRYN deactivated. Models, sessions, caches, settings and packages are retained. "
          "Rerun the verified release installer to reactivate.")
