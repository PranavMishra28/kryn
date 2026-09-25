"""Dispatch package operations or hand the user's project to the owned client."""
import json
import os
from pathlib import Path
import subprocess
import sys
from . import __version__
from .installer import install, rollback, uninstall, payload, verify_payload, safe_json, root_path


def main():
    args = sys.argv[1:]
    try:
        if args == ["--version"]:
            print("KRYN " + __version__)
            return
        if args == ["--package-check"]:
            value = verify_payload()
            print(json.dumps({"version": __version__, "payload_files": len(value["files"]),
                              "source_revision": value["source_revision"]}))
            return
        if args and args[0] == "install":
            if len(args) != 1:
                raise RuntimeError("Usage: kryn install")
            install()
            return
        if args and args[0] == "rollback":
            if len(args) != 1:
                raise RuntimeError("Usage: kryn rollback")
            rollback()
            return
        if args and args[0] == "uninstall":
            if len(args) != 1:
                raise RuntimeError("Usage: kryn uninstall (deactivates launchers; retains data)")
            uninstall()
            return
        if args and args[0] == "update":
            if len(args) != 2 or not args[1].startswith("v"):
                raise RuntimeError("Usage: kryn update vX.Y.Z")
            verify_payload()
            subprocess.run([sys.executable, "-E", "-B", str(payload() / "install-kryn.py"),
                            "--tag", args[1]], check=True)
            return
        root = root_path()
        deployment = safe_json(root / "client/deployment.json")
        directory = Path(deployment["directory"])
        if directory.parent != root / "client" or not directory.name.isalnum():
            raise RuntimeError("Invalid installed client identity; run the release installer")
        script = directory / "tools/localai.py"
        if not script.is_file() or script.is_symlink():
            raise RuntimeError("Installed client is missing; run the release installer")
        # Keep the venv's interpreter path: resolving its symlink would lose package context.
        os.execv(sys.executable, [sys.executable, "-E", "-B", str(script), *args])
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit("STOP: " + str(error))
