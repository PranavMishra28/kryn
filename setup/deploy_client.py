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
    parser.add_argument("--profile", type=Path, help="Defaults to the installed profile; no profile is inferred from oMLX settings")
    args = parser.parse_args()
    os.umask(0o077)
    source = Path(__file__).resolve().parents[1]
    root = Path.home() / "Library/Application Support/LocalAI"
    if not (root / "xdg/config/opencode/opencode.json").is_file():
        raise RuntimeError("Install and validate the owned core first")
    profile = setup.load_profile(args.profile or root / "install-profile.json")
    model = setup.model_id(profile)
    config = json.loads((root / "xdg/config/opencode/opencode.json").read_text())
    if config.get("providers", {}).get("local", {}).get("models", {}).get("qwen", {}).get("modelID") != model:
        raise RuntimeError("Owned OpenCode config disagrees with the chosen profile")
    marker = root / profile["model_parent"] / model / ".localai-download.json"
    setup.check_destination(marker, setup.encode({key: profile[key] for key in ("repository", "revision")}))
    if not marker.is_file():
        raise RuntimeError("Verified model installation marker is missing")
    names = ["tools/localai.py", "tools/native_client.py", "tools/protocol_probe.py", "tools/context_probe.py", "tools/improvement.py", "tools/native-shell",
             "setup/opencode.template.json"]
    contents = {name: (source / name).read_bytes() for name in names}
    contents["tools/native_client.py"] = pin_constant(contents["tools/native_client.py"], "MODEL_ID", model)
    for name, value in (("REVISION", profile["revision"]), ("REPOSITORY", profile["repository"]),
                        ("MODEL_PARENT", profile["model_parent"]), ("MEMORY_GIB", profile["memory_gib"]),
                        ("SERVER_CONTEXT", setup.model_settings(profile)["models"][model]["max_context_window"])):
        contents["tools/localai.py"] = pin_constant(contents["tools/localai.py"], name, value)
    template = json.loads(contents["setup/opencode.template.json"])
    template["providers"]["local"]["models"]["qwen"].update(modelID=model, name=model)
    contents["setup/opencode.template.json"] = setup.encode(template).encode()
    contents["setup/install-profile.json"] = setup.encode(profile).encode()
    contents["setup/runtime-profile.json"] = setup.encode({"global": setup.runtime_settings(root, profile),
                                                           "model": setup.model_settings(profile)}).encode()
    hashes = {name: sha(value) for name, value in contents.items()}
    release = sha(json.dumps(hashes, sort_keys=True).encode())[:16]
    destination = root / "client" / release
    python = Path(sys.executable).resolve()
    script = "#!/bin/sh\nexec " + shlex.quote(str(python)) + " -E -B " + shlex.quote(
        str(destination / "tools/localai.py")) + ' "$@"\n'
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
    for path in launchers:
        if not path.exists():
            continue
        allowed = {script}
        if prior:
            allowed.add(prior["launcher"])
        elif path == root / "localai":
            allowed.add(setup.launcher(root))
        if not path.is_file() or path.read_text() not in allowed:
            raise RuntimeError(f"Preserving unowned/changed launcher: {path}")
    result = {"release": release, "directory": str(destination), "python": str(python),
              "files": hashes, "launcher": script}
    manifest_text = json.dumps(result, indent=2) + "\n"
    setup.check_destination(manifest_path.with_suffix(".new.json"), manifest_text)
    for index, path in enumerate(launchers):
        setup.check_destination(path.with_name(path.name + ".localai-new"), script)
        if path.exists() and path.read_text() != script:
            setup.check_destination(root / "backups" / ("client-" + release) / (str(index) + "-localai"), path.read_text())
    if not args.apply:
        print(json.dumps({"read_only": True, "release": release, "launchers": list(map(str, launchers))}))
        return
    for name, data in contents.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("xb") as output:
                output.write(data)
            if name == "tools/native-shell":
                path.chmod(0o700)
    # Backup changed owned entry points before replacing them atomically.
    for index, path in enumerate(launchers):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text() != script:
            backup = root / "backups" / ("client-" + release) / (str(index) + "-localai")
            setup.write_same(backup, path.read_text())
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
