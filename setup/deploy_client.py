#!/usr/bin/env python3
"""Deploy the small daily client into the already installed, owned LocalAI root.

No downloads, runtime changes, shell-profile edits or service launches. The release
is content-addressed; changed existing release files or launchers are preserved.
"""
import argparse
import ast
import hashlib
import json
import os
import re
from pathlib import Path
import shlex
import stat
import subprocess
import sys

import setup


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin_constant(data, name, value):
    text, count = re.subn(r"(?m)^" + re.escape(name) + r" = [^\n]+$",
                          lambda _: name + " = " + repr(value), data.decode())
    if count != 1:
        raise RuntimeError("Expected one reviewed client constant: " + name)
    ast.parse(text)
    return text.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--plan-json", action="store_true", help="Return the complete staged deployment manifest without writing")
    parser.add_argument("--profile", type=Path, help="Defaults to the installed profile; no profile is inferred from oMLX settings")
    parser.add_argument("--entry-python", type=Path, help="Installed package interpreter; launch its kryn console module")
    parser.add_argument("--smoke-check", action="store_true", help="Check staged client before activating owned entry points")
    args = parser.parse_args()
    if args.apply and args.plan_json:
        parser.error("--plan-json cannot be combined with --apply")
    os.umask(0o077)
    source = Path(__file__).resolve().parents[1]
    root = Path.home() / "Library/Application Support/LocalAI"
    config_path = root / "xdg/config/opencode/opencode.json"
    if not args.plan_json and not config_path.is_file():
        raise RuntimeError("Install and validate the owned core first")
    profile = setup.load_profile(args.profile or root / "install-profile.json")
    model = setup.model_id(profile)
    config = json.loads(config_path.read_text()) if config_path.is_file() else {}
    if not args.plan_json and config.get("providers", {}).get("local", {}).get("models", {}).get("qwen", {}).get("modelID") != model:
        raise RuntimeError("Owned OpenCode config disagrees with the chosen profile")
    marker = root / profile["model_parent"] / model / ".localai-download.json"
    setup.check_destination(marker, setup.encode({key: profile[key] for key in ("repository", "revision")}))
    if not marker.is_file():
        raise RuntimeError("Verified model installation marker is missing")
    names = ["tools/localai.py", "tools/session_report.py", "tools/native_client.py", "tools/protocol_probe.py", "tools/context_probe.py", "tools/improvement.py", "tools/learning.py", "tools/native-shell",
             "setup/opencode.template.json", "setup/AGENTS.md"]
    contents = {name: (source / name).read_bytes() for name in names}
    contents.update({"plugin/" + name: data for name, data in setup.plugin_files().items()})
    contents["tools/native_client.py"] = pin_constant(contents["tools/native_client.py"], "MODEL_ID", model)
    for name, value in (("REVISION", profile["revision"]), ("REPOSITORY", profile["repository"]),
                        ("MODEL_PARENT", profile["model_parent"]), ("MEMORY_GIB", profile["memory_gib"]),
                        ("SERVER_CONTEXT", setup.model_settings(profile)["models"][model]["max_context_window"])):
        contents["tools/localai.py"] = pin_constant(contents["tools/localai.py"], name, value)
    template = json.loads(contents["setup/opencode.template.json"])
    template["providers"]["local"]["models"]["qwen"].update(modelID=model, name=model)
    for item in template["plugins"]:
        if isinstance(item, dict):
            item["options"]["modelID"] = model
    contents["setup/opencode.template.json"] = setup.encode(template).encode()
    contents["setup/install-profile.json"] = setup.encode(profile).encode()
    contents["setup/runtime-profile.json"] = setup.encode({"global": setup.runtime_settings(root, profile),
                                                           "model": setup.model_settings(profile)}).encode()
    hashes = {name: sha(value) for name, value in contents.items()}
    release = sha(json.dumps(hashes, sort_keys=True).encode())[:16]
    destination = root / "client" / release
    python = args.entry_python.expanduser().absolute() if args.entry_python else Path(sys.executable).resolve()
    if not python.is_file() or not os.access(python, os.X_OK):
        raise RuntimeError("Package interpreter is missing or not executable")
    target = "-m kryn" if args.entry_python else shlex.quote(str(destination / "tools/localai.py"))
    script = "#!/bin/sh\nexec " + shlex.quote(str(python)) + " -E -B " + target + ' "$@"\n'
    manifest_path = root / "client/deployment.json"
    prior = json.loads(manifest_path.read_text()) if manifest_path.is_file() else None
    launchers = [root / "localai", Path.home() / ".local/bin/localai",
                 root / "kryn", Path.home() / ".local/bin/kryn"]
    for path in [destination, manifest_path, *launchers]:
        if any(p.is_symlink() for p in [path, *path.parents]):
            raise RuntimeError(f"Refusing symlink destination: {path}")
    for name, data in contents.items():
        path = destination / name
        if any(p.is_symlink() for p in [path, *path.parents]):
            raise RuntimeError(f"Refusing symlink release file: {path}")
        if path.exists() and (not path.is_file() or path.read_bytes() != data):
            raise RuntimeError(f"Preserving changed release file: {path}")
        if name == "tools/native-shell" and path.exists():
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid not in {0, os.geteuid()}
                    or info.st_nlink != 1 or info.st_mode & 0o022 or not os.access(path, os.X_OK)):
                raise RuntimeError(f"Preserving unsafe existing release shim: {path}")
    plugin_dir = setup.plugin_directory(root)
    for name, data in setup.plugin_files().items():
        path = plugin_dir / name
        if any(p.is_symlink() for p in (path, *path.parents)) or (path.exists() and path.read_bytes() != data):
            raise RuntimeError("Preserving changed or linked native product plugin")
    for path in launchers:
        if not path.exists():
            continue
        allowed = {script}
        if prior:
            allowed.add(prior["launcher"])
        elif path == root / "localai":
            allowed.add(setup.launcher(root))
        if not path.is_file() or path.read_bytes() not in {value.encode() for value in allowed}:
            raise RuntimeError(f"Preserving unowned/changed launcher: {path}")
    result = {"release": release, "directory": str(destination), "python": str(python),
              "plugin_directory": str(plugin_dir),
              "files": hashes, "launcher": script}
    manifest_text = json.dumps(result, indent=2) + "\n"
    setup.check_destination(manifest_path.with_suffix(".new.json"), manifest_text)
    backups = {}
    for index, path in enumerate(launchers):
        setup.check_destination(path.with_name(path.name + ".localai-new"), script)
        if path.exists() and path.read_bytes() != script.encode():
            previous = path.read_bytes()
            # The same client can be launched by multiple immutable package interpreters.
            backup = root / "backups" / ("client-" + release) / sha(previous) / (str(index) + "-localai")
            setup.check_destination(backup, previous.decode())
            if backup.exists() and backup.read_bytes() != previous:
                raise RuntimeError(f"Preserving changed launcher backup: {backup}")
            backups[path] = (backup, previous)
    if not args.apply:
        print(json.dumps(result if args.plan_json else {"read_only": True, "release": release, "launchers": list(map(str, launchers))}))
        return
    for name, data in contents.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("xb") as output:
                output.write(data)
            if name == "tools/native-shell":
                path.chmod(0o700)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    for name, data in setup.plugin_files().items():
        path = plugin_dir / name
        if not path.exists():
            with path.open("xb") as output:
                output.write(data)
    if args.smoke_check:
        subprocess.run([str(python), "-E", "-B", str(destination / "tools/localai.py"), "--self-check"], check=True)
    # Backup changed owned entry points before replacing them atomically.
    for path in launchers:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path in backups:
            backup, previous = backups[path]
            if path.read_bytes() != previous:
                raise RuntimeError(f"Preserving launcher changed after planning: {path}")
            setup.write_same(backup, previous.decode())
        temporary = path.with_name(path.name + ".localai-new")
        setup.write_same(temporary, script, executable=True)
        temporary.replace(path)
    temporary = manifest_path.with_suffix(".new.json")
    setup.write_same(temporary, manifest_text)
    temporary.replace(manifest_path)
    print(json.dumps({"deployed": True, "release": release, "command": str(launchers[3])}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        sys.exit("STOP: " + str(error))
