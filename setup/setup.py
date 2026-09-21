#!/usr/bin/env python3
"""Reviewed setup recipe, not an agent harness. Default: read-only preflight.

Python 3.13+, macOS 26/27 ARM64, at least 48 GiB RAM. See README.md.
No sudo, shell startup edits, service launches or automatic removal of existing files.
Core --apply copies only the verified user-space app and deploys the daily client.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
MODEL = "Qwen3.8-27B-oQ6e-mtp"
REVISION = "f7ec1f012451c7a76e775e2fdefdd5f0a51f11f7"
GIB = 1024 ** 3
DMG_URL = "https://github.com/jundot/omlx/releases/download/v0.6.4/oMLX-0.6.4-macos26-27.dmg"
DMG_SHA = "53f1506c2385e8920a67198b72d1fe09351c1b3538be9c6bdeb78e5277d06d93"
CLI_URL = "https://registry.npmjs.org/@opencode/cli-darwin-arm64/-/cli-darwin-arm64-2.0.10.tgz"
CLI_SHA = "acb2f84e60c47a2437d6316c173250fa0a3f6af6ac9e55dadf7538996f49d84d6f3763222c639e690ce5398438804ef605b92ba763e5fc9531d4924288ada5dd"
DOC_PACKAGES = ["python-docx==1.2.0", "python-pptx==1.0.2", "openpyxl==3.1.5",
                "matplotlib==3.11.2", "pypdf==6.19.0", "pypdfium2==5.13.0",
                "reportlab==5.0.1", "Pillow==12.3.0"]


def load_profile(path=None):
    profile = (json.loads(Path(path).read_text()) if path else {
        "repository": "Jundot/" + MODEL, "revision": REVISION,
        "memory_gib": 36, "files": json.loads((HERE / "model-sha256.json").read_text())})
    if not isinstance(profile, dict) or set(profile) - {"repository", "revision", "memory_gib", "files", "model_parent"}:
        raise RuntimeError("Profile must contain repository, revision, memory_gib, files and optional model_parent")
    profile = {**profile, "model_parent": profile.get("model_parent", "models")}
    def relative(value):
        return (isinstance(value, str) and value and not Path(value).is_absolute()
                and not value.startswith("-") and "\x00" not in value
                and all(part not in ("", ".", "..") for part in value.split("/")) and "\\" not in value)
    if (not isinstance(profile.get("repository"), str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", profile["repository"])
            or any(part in (".", "..") for part in profile["repository"].split("/"))
            or not isinstance(profile.get("revision"), str)
            or not re.fullmatch(r"[a-f0-9]{40}", profile["revision"])
            or type(profile.get("memory_gib")) not in (int, float)
            or not 0 < profile["memory_gib"] <= 128 or not relative(profile["model_parent"])):
        raise RuntimeError("Invalid exact model pin, memory ceiling or relative model_parent")
    files = profile.get("files")
    if (not isinstance(files, dict) or not files or not any(isinstance(name, str) and name.endswith(".safetensors") for name in files)
            or any(not relative(name) or not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value)
                   for name, value in files.items())):
        raise RuntimeError("Profile files must map safe relative paths to exact SHA256 hashes")
    return profile


def model_id(profile):
    return profile["repository"].split("/")[1]


def model_destination(root, profile=None):
    profile = profile or load_profile()
    destination = root / profile["model_parent"] / model_id(profile)
    marker = destination / ".localai-download.json"
    identity = encode({key: profile[key] for key in ("repository", "revision")})
    check_destination(marker, identity)
    if destination.exists():
        if not marker.is_file():
            raise RuntimeError(f"Preserving existing unowned model directory: {destination}")
        if any(path.is_symlink() for path in destination.rglob("*")):
            raise RuntimeError(f"Refusing symlinks within model directory: {destination}")
    return destination, marker, identity


def require_space(free, phase):
    # Conservative even on reruns: unrelated files never reduce the reserve.
    required = (140 if phase == "core" else 104) * GIB
    if free < required:
        raise RuntimeError(f"Need at least {required // GIB} GiB free for this phase, including the 100 GiB reserve")


def encode(value):
    return json.dumps(value, indent=2) + "\n"


def check_destination(path, text):
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise RuntimeError(f"Refusing symlink destination: {parent}")
    if path.exists() and (not path.is_file() or path.read_text() != text):
        raise RuntimeError(f"Preserving existing/changed file; review manually: {path}")


def write_same(path, text, executable=False):
    check_destination(path, text)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as target:
            target.write(text)
    if executable:
        path.chmod(0o700)


def digest(path, algorithm):
    result = hashlib.new(algorithm)
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def download(url, path, algorithm, expected):
    for part in [path, *path.parents, path.with_suffix(path.suffix + ".partial")]:
        if part.is_symlink():
            raise RuntimeError(f"Refusing symlink download: {part}")
    if path.exists():
        if digest(path, algorithm) != expected:
            raise RuntimeError(f"Existing download fails integrity check: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    print(f"Downloading {url}", flush=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        if not response.url.startswith("https://"):
            raise RuntimeError("Refusing non-HTTPS redirect")
        with partial.open("wb") as target:
            shutil.copyfileobj(response, target, length=1024 * 1024)
    if digest(partial, algorithm) != expected:
        raise RuntimeError(f"Checksum mismatch; partial retained for inspection: {partial}")
    partial.replace(path)


def extract_cli(archive, destination):
    # Read only the two known files; never extract archive paths, links or modes.
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        allowed = {"package/bin/opencode", "package/package.json"}
        files = [m for m in members if not m.isdir()]
        if {m.name for m in files} != allowed or len(files) != 2:
            raise RuntimeError("Unexpected CLI archive contents")
        if any(not m.isfile() or m.size > 200 * 1024 ** 2 for m in files):
            raise RuntimeError("Unexpected CLI archive member type/size")
        for member in files:
            target = destination / member.name
            for part in [target, *target.parents]:
                if part.is_symlink():
                    raise RuntimeError(f"Refusing symlink extraction: {part}")
            data = bundle.extractfile(member).read()
            if target.exists():
                if target.read_bytes() != data:
                    raise RuntimeError(f"Preserving changed executable/package: {target}")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    output.write(data)
            if member.name.endswith("/opencode"):
                target.chmod(0o700)


def plugin_files():
    return {"server.js": (HERE.parent / "tools/kryn_plugin.mjs").read_bytes(),
            "package.json": b'{"private":true,"type":"module"}\n'}


def plugin_directory(root):
    return root / "plugins" / hashlib.sha256(plugin_files()["server.js"]).hexdigest()[:16]


def render(root, node, profile=None):
    profile = profile or load_profile()
    def substitute(value):
        if isinstance(value, str):
            return (value.replace("__ROOT__", str(root)).replace("__NODE__", str(node))
                    .replace("__KRYN_PLUGIN__", str(plugin_directory(root)))
                    .replace("__KRYN_STATE__", str(root / "state/improvement"))
                    .replace("__PROFILE_ID__", hashlib.sha256(encode(profile).encode()).hexdigest()))
        if isinstance(value, list):
            return [substitute(item) for item in value]
        if isinstance(value, dict):
            return {key: substitute(item) for key, item in value.items()}
        return value
    cfg = substitute(json.loads((HERE / "opencode.template.json").read_text()))
    selected = model_id(profile)
    cfg["providers"]["local"]["models"]["qwen"].update(modelID=selected, name=selected)
    for item in cfg["plugins"]:
        if isinstance(item, dict):
            item["options"]["modelID"] = selected
    return cfg


def desktop_config(cfg, root):
    expanded = copy.deepcopy(cfg)
    expanded["mcp"]["servers"]["peekaboo"] = {
        "type": "local", "command": [str(root / "peekaboo/node_modules/.bin/peekaboo"),
        "mcp", "serve", "--allow-foreground"], "environment": {"PEEKABOO_AI_PROVIDERS": "",
        "PEEKABOO_ALLOW_TOOLS": "see,app,window,click,type,press,scroll,set_value,action,menu,move,drag,sleep,permissions",
        "PEEKABOO_DISABLE_TOOLS": "image,analyze,agent,shell,browser"}}
    return expanded


def runtime_settings(root, profile=None):
    profile = profile or load_profile()
    return {"version": "1.0", "server": {"host": "127.0.0.1", "port": 8000,
            "auto_start_on_launch": False,
            "cors_origins": ["http://127.0.0.1:8000", "http://localhost:8000"]},
            "model": {"model_dirs": [str(root / profile["model_parent"])],
            "model_fallback": False}, "scheduler": {"max_concurrent_requests": 1},
            "memory": {"prefill_memory_guard": True, "memory_guard_tier": "custom",
            "memory_guard_custom_ceiling_gb": profile["memory_gib"], "soft_threshold": 0.85, "hard_threshold": 0.95},
            "idle_timeout": {"idle_timeout_seconds": 300},
            "cache": {"enabled": True, "hot_cache_only": False,
            "ssd_cache_max_size": "8GB", "hot_cache_max_size": "0",
            "ssd_cache_dir": str(root / "cache" / profile["revision"])},
            "huggingface": {"hf_cache_enabled": False}}


def model_settings(profile=None):
    return {"version": 1, "models": {model_id(profile or load_profile()): {"max_context_window": 16384, "max_tokens": 4096,
            "enable_thinking": True, "mtp_enabled": False,
            "mtp_num_draft_tokens": 3, "vlm_mtp_enabled": False, "dflash_enabled": False,
            "specprefill_enabled": False, "turboquant_kv_enabled": False,
            "qwen35_ane_prefill_enabled": False, "is_pinned": False, "is_default": True}}}


def launcher(root):
    # Historical bytes are retained only to recognize the earlier owned launcher during migration.
    return """#!/bin/zsh
set -eu
localai_root=%s
exec env -u OPENCODE_CONFIG -u OPENCODE_CONFIG_CONTENT -u OPENCODE_CONFIG_DIR \\
  -u OPENCODE_DB -u OPENCODE_TEST_HOME -u OPENCODE_SIMULATE \\
  NO_PROXY='127.0.0.1,localhost,::1' no_proxy='127.0.0.1,localhost,::1' \\
  XDG_CONFIG_HOME="$localai_root/xdg/config" XDG_DATA_HOME="$localai_root/xdg/data" \\
  XDG_CACHE_HOME="$localai_root/xdg/cache" XDG_STATE_HOME="$localai_root/xdg/state" \\
  OPENCODE_CLI_CONFIG_CONTENT='{"session":{"permissions":"prompt"}}' \\
  "$localai_root/opencode/2.0.10/package/bin/opencode" --standalone "$@"
""" % shlex.quote(str(root))


def run(args, env, timeout=None):
    print("Running:", shlex.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), env=env, check=True, timeout=timeout)


def bundle_digest(app):
    digest_value = hashlib.sha256()
    for path in sorted(app.rglob("*")):
        if path.is_symlink():
            item = [str(path.relative_to(app)), "link", os.readlink(path)]
        elif path.is_file():
            item = [str(path.relative_to(app)), "file", digest(path, "sha256")]
        elif path.is_dir():
            continue
        else:
            raise RuntimeError(f"Unexpected app member: {path}")
        digest_value.update((json.dumps(item) + "\n").encode())
    return digest_value.hexdigest()


def install_app(root, env):
    destination = Path.home() / "Applications/oMLX.app"
    receipt = root / "app-install.json"
    temporary = destination.with_name("oMLX.app.localai-new")
    for path in (destination, receipt, temporary):
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise RuntimeError(f"Refusing symlink app destination: {path}")
    reuse = destination.exists()
    if reuse and receipt.is_file():
        expected = {"path": str(destination), "dmg_sha256": DMG_SHA,
                    "bundle_sha256": bundle_digest(destination)}
        check_destination(receipt, encode(expected))
        run(["/usr/bin/codesign", "--verify", "--deep", "--strict", destination], env)
        return
    if temporary.exists() or receipt.exists():
        raise RuntimeError("Preserving unfinished app installation; inspect its files before retrying")
    dmg = (root / "downloads/oMLX-0.6.4-macos26-27.dmg").resolve()
    before = plistlib.loads(subprocess.check_output(["/usr/bin/hdiutil", "info", "-plist"], env=env, timeout=15))
    images = before["images"]
    for item in images:
        prior = Path(item["image-path"])
        if prior.resolve() == dmg or (prior.exists() and os.path.samefile(prior, dmg)):
            raise RuntimeError("Preserving already-attached oMLX image; detach it yourself before retrying")
    existing_devices = {item["dev-entry"] for image in images for item in image.get("system-entities", [])
                        if item.get("dev-entry")}
    mount = Path(tempfile.mkdtemp(prefix=".omlx-mount-", dir=root))
    owned_device = None
    try:
        result = subprocess.check_output(["/usr/bin/hdiutil", "attach", "-readonly", "-nobrowse", "-plist",
            "-mountpoint", str(mount), str(dmg)], env=env, timeout=60)
        entities = plistlib.loads(result)["system-entities"]
        devices = {item["dev-entry"] for item in entities if item.get("dev-entry")}
        whole = {device for device in devices if re.fullmatch(r"/dev/disk[0-9]+", device)}
        physical = {item["dev-entry"] for item in entities
                    if item.get("content-hint") == "GUID_partition_scheme" and item.get("dev-entry") in whole}
        owners = physical or whole
        mounted = [Path(item["mount-point"]) for item in entities if item.get("mount-point")]
        if len(owners) != 1 or devices & existing_devices or mounted != [mount]:
            raise RuntimeError("Could not prove a new private app-image attachment; leaving returned devices untouched")
        owned_device = owners.pop()  # APFS also returns a synthesized whole-disk device.
        app = mount / "oMLX.app"
        info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
        if (info.get("CFBundleIdentifier"), info.get("CFBundleShortVersionString")) != ("app.omlx", "0.6.4"):
            raise RuntimeError("Unexpected app identity/version")
        run(["/usr/bin/codesign", "--verify", "--deep", "--strict", app], env)
        expected_hash = bundle_digest(app)
        if reuse:
            if not destination.is_dir() or bundle_digest(destination) != expected_hash:
                raise RuntimeError("Preserving existing app that differs from the verified publisher artifact")
            run(["/usr/bin/codesign", "--verify", "--deep", "--strict", destination], env)
            write_same(receipt, encode({"path": str(destination), "dmg_sha256": DMG_SHA,
                                       "bundle_sha256": expected_hash}))
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        run(["/usr/bin/ditto", "--rsrc", "--extattr", app, temporary], env)
        if bundle_digest(temporary) != expected_hash or destination.exists():
            raise RuntimeError("App copy mismatch or destination appeared; preserving temporary copy")
        run(["/usr/bin/codesign", "--verify", "--deep", "--strict", temporary], env)
        temporary.rename(destination)
        write_same(receipt, encode({"path": str(destination), "dmg_sha256": DMG_SHA,
                                   "bundle_sha256": expected_hash}))
    finally:
        primary_error = sys.exception()
        try:
            if owned_device:
                run(["/usr/bin/hdiutil", "detach", owned_device], env, timeout=30)
            if mount.exists() and not os.path.ismount(mount):
                mount.rmdir()  # Only our now-empty private directory; never recursive cleanup.
        except Exception as cleanup_error:
            if primary_error is not None:
                raise RuntimeError(f"{primary_error}; attachment cleanup also failed: {cleanup_error}") from primary_error
            raise


def npm_install(root, node, folder, package, env):
    tree = root / folder / "node_modules"
    if tree.exists() or tree.is_symlink():
        raise RuntimeError(f"Preserving existing dependency tree; review it before reinstalling: {tree}")
    manifest = root / folder / "package.json"
    name, version = package.rsplit("@", 1)
    write_same(manifest, encode({"private": True, "dependencies": {name: version}}))
    if folder == "browser":
        write_same(manifest.parent / "package-lock.json", (HERE / "browser-package-lock.json").read_text())
    operation = "ci" if (manifest.parent / "package-lock.json").exists() else "install"
    run([node.parent / "npm", "--prefix", manifest.parent, "--cache", root / "npm-cache",
         operation, "--registry=https://registry.npmjs.org", "--ignore-scripts", "--no-audit", "--no-fund"], env)


def download_model(uv, model_dir, profile, env):
    missing = []
    for name, expected in profile["files"].items():
        path = model_dir / name
        if path.exists() or path.is_symlink():
            if not path.is_file() or path.is_symlink() or digest(path, "sha256") != expected:
                raise RuntimeError(f"Preserving changed model file: {name}")
        else:
            missing.append(name)
    for name in missing:
        # One filename selects hf_hub_download; multi-file snapshot_download omitted a pinned dotfile.
        run([uv, "tool", "run", "--from", "huggingface-hub==1.32.0", "hf", "download",
             profile["repository"], name, "--revision", profile["revision"], "--local-dir", model_dir], env)
    for name, expected in profile["files"].items():
        if digest(model_dir / name, "sha256") != expected:
            raise RuntimeError(f"Model file integrity mismatch: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Perform selected installation phase")
    parser.add_argument("--phase", choices=["core", "documents", "desktop"], default="core")
    parser.add_argument("--profile", type=Path, help="Accepted exact model/revision/hash/memory profile; required with --apply")
    parser.add_argument("--uv", type=Path, default=shutil.which("uv"), help="Existing uv executable")
    parser.add_argument("--node", type=Path, default=shutil.which("node"), help="Existing native Node 22.23.1 executable")
    args = parser.parse_args()
    if args.apply and args.profile is None:
        raise RuntimeError("Choose the accepted profile explicitly with --profile; the built-in example is not acceptance")
    profile = load_profile(args.profile)
    if args.apply:
        os.umask(0o077)
    home = Path.home()
    root = home / "Library/Application Support/LocalAI"
    uv = (args.uv or home / ".local/bin/uv").expanduser().resolve()
    node = (args.node or home / ".nvm/versions/node/v22.23.1/bin/node").expanduser().resolve()
    python = Path(sys.executable).resolve()
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("This profile requires native Apple Silicon macOS")
    if sys.version_info < (3, 13) or int(platform.mac_ver()[0].split(".")[0]) not in (26, 27):
        raise RuntimeError("Use Python 3.13+ on macOS 26/27 for this pinned profile")
    memory = int(subprocess.check_output(["/usr/sbin/sysctl", "-n", "hw.memsize"]))
    if memory < 48 * GIB:
        raise RuntimeError("This model profile requires at least 48 GiB RAM")
    if profile["memory_gib"] > memory / GIB - 8:
        raise RuntimeError("Accepted memory ceiling must leave at least 8 GiB outside oMLX")
    for required in (uv, node, node.parent / "npm", Path("/Applications/Google Chrome.app")):
        if not required.exists():
            raise RuntimeError(f"Required existing dependency missing: {required}; install prerequisites or pass --uv/--node")
    node_info = subprocess.check_output([str(node), "-p", "process.arch + ' ' + process.versions.node"], text=True).strip()
    node_match = re.fullmatch(r"arm64 22\.(\d+)\.(\d+)", node_info)
    if not node_match or int(node_match[1]) < 23:
        raise RuntimeError("Use native ARM64 Node 22.23 or later in the 22.x compatibility line")
    for part in [root, *root.parents]:
        if part.is_symlink():
            raise RuntimeError(f"Refusing symlink install root: {part}")
    free = shutil.disk_usage(home).free
    require_space(free, args.phase)
    cfg_path = root / "xdg/config/opencode/opencode.json"
    cfg = render(root, node, profile)
    guidance = (HERE / "AGENTS.md").read_text() + f"\nIf installed, use {root}/artifacts/.venv/bin/python for document/data tasks.\n"
    files = {cfg_path: encode(cfg), root / "xdg/config/opencode/AGENTS.md": guidance,
             root / "install-profile.json": encode(profile),
             home / ".omlx/settings.json": encode(runtime_settings(root, profile)),
             home / ".omlx/model_settings.json": encode(model_settings(profile))}
    if args.phase == "core":
        model_dir, model_marker, model_identity = model_destination(root, profile)
        tree = root / "browser/node_modules"
        if tree.exists() or tree.is_symlink():
            raise RuntimeError(f"Preserving existing dependency tree; review it before reinstalling: {tree}")
        app = home / "Applications/oMLX.app"
        if app.exists() and not (root / "app-install.json").is_file():
            raise RuntimeError("Preserving existing app without this installer's receipt; review its ownership first")
        if app.with_name("oMLX.app.localai-new").exists():
            raise RuntimeError("Preserving unfinished app copy; inspect before retrying")
        if "OMLX_BASE_PATH" in os.environ or (home / "Library/Application Support/oMLX/base-path").exists():
            raise RuntimeError("Existing oMLX base-path override: review its active configuration first")
        if subprocess.run(["/usr/bin/pgrep", "-x", "oMLX"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0:
            raise RuntimeError("oMLX is running; quit it before preparing runtime configuration")
        with socket.socket() as probe:
            probe.settimeout(0.5)
            if probe.connect_ex(("127.0.0.1", 8000)) == 0:
                raise RuntimeError("Port 8000 is occupied; review before configuring a runtime")
        for path, text in files.items():
            check_destination(path, text)
    elif not cfg_path.is_file():
        raise RuntimeError("Complete the core phase before installing an optional module")
    if args.phase == "documents":
        venv = root / "artifacts/.venv"
        resolved = root / "artifacts/resolved-requirements.txt"
        for part in [venv, resolved, *venv.parents]:
            if part.is_symlink():
                raise RuntimeError(f"Refusing symlink environment: {part}")
    if args.phase == "desktop":
        expanded = desktop_config(cfg, root)
        if cfg_path.is_symlink() or json.loads(cfg_path.read_text()) not in (cfg, expanded):
            raise RuntimeError("OpenCode config was customized; preserve it and add Peekaboo manually")
    print(f"Profile: macOS ARM64, {memory // GIB} GiB RAM; {free / GIB:.1f} GiB free")
    print(f"Phase: {args.phase}; destination: {root}")
    print(f"Model: {profile['repository']}@{profile['revision']}; guard {profile['memory_gib']} GiB")
    if not args.apply:
        print("READ-ONLY preflight passed. No downloads, writes or installations performed.")
        print("With --apply and --profile: core verifies/downloads the selected model, installs the user app and daily client.")
        print("Documents/desktop phases install only their named optional packages. Read README.md first.")
        return
    env = os.environ.copy()
    env.update({"PATH": str(node.parent) + os.pathsep + env.get("PATH", ""),
                "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1", "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
                "HF_HUB_DISABLE_XET": "1", "UV_CACHE_DIR": str(root / "uv-cache")})
    if args.phase == "core":
        download(DMG_URL, root / "downloads/oMLX-0.6.4-macos26-27.dmg", "sha256", DMG_SHA)
        archive = root / "downloads/opencode-2.0.10.tgz"
        download(CLI_URL, archive, "sha512", CLI_SHA)
        extract_cli(archive, root / "opencode/2.0.10")
        npm_install(root, node, "browser", "@playwright/mcp@0.0.82", env)
        write_same(model_marker, model_identity)
        download_model(uv, model_dir, profile, env)
        for path, text in files.items():
            write_same(path, text, executable=path.name == "localai")
        install_app(root, env)
        run([python, "-B", HERE / "deploy_client.py", "--profile", root / "install-profile.json", "--apply"], env)
        print("Installed; no app or model server was started. First launch may require normal macOS approval.")
        print(f"Daily command: {home}/.local/bin/localai /path/to/project")
    elif args.phase == "documents":
        if not venv.exists():
            run([uv, "venv", "--python", python, venv], env)
        requirements = ["-r", resolved] if resolved.exists() else DOC_PACKAGES
        run([uv, "pip", "install", "--python", venv / "bin/python", *requirements], env)
        frozen = subprocess.check_output([str(uv), "pip", "freeze", "--python", str(venv / "bin/python")], env=env, text=True)
        write_same(resolved, frozen)
        print("Documents installed; resolved versions saved in artifacts/resolved-requirements.txt.")
    else:
        npm_install(root, node, "peekaboo", "@steipete/peekaboo@4.4.0", env)
        (root / "peekaboo/node_modules/@steipete/peekaboo/peekaboo").chmod(0o700)
        if json.loads(cfg_path.read_text()) == cfg:
            write_same(cfg_path.with_suffix(".pre-desktop.json"), cfg_path.read_text())
            temporary = cfg_path.with_suffix(".desktop-new.json")
            write_same(temporary, encode(expanded))
            temporary.replace(cfg_path)
        print("Restart the assistant to expose Peekaboo. Grant macOS permissions only when prompted.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError, ValueError) as error:
        sys.exit(f"STOP: {error}")
