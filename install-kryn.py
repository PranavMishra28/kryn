#!/usr/bin/env python3
"""Install a checksum-verified GitHub release for the authorized owner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

REPO = "PranavMishra28/kryn"
UV_URL = "https://github.com/astral-sh/uv/releases/download/0.11.16/uv-aarch64-apple-darwin.tar.gz"
UV_SHA = "2b25be1af546be330b340b0a76b99f989daa6d92678fdffb87438e661e9d88fb"


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def run(args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def safe(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RuntimeError("Linked installer destinations are refused")
    existing = next(p for p in (path, *path.parents) if p.exists())
    if existing.stat().st_uid not in (0, os.geteuid()) or existing.stat().st_mode & 0o022:
        raise RuntimeError("Installer destination is not owned and protected")
    return path


def secure_owner(gh):
    """Bootstrap equivalent of the packaged auth boundary; never disclose subprocess output."""
    hosts = Path(os.environ.get("GH_CONFIG_DIR", str(Path.home() / ".config/gh"))) / "hosts.yml"
    if hosts.is_file() and re.search(r"^\s*oauth_token:\s*\S+", hosts.read_text(), re.M):
        raise RuntimeError("Plaintext GitHub token storage is refused; use gh's OS credential store")
    def read(arguments):
        try:
            result = subprocess.run([gh, *arguments], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            raise RuntimeError("Secure GitHub identity check failed; check network and gh authentication") from None
        if result.returncode: raise RuntimeError("Secure GitHub identity check failed; check network and gh authentication")
        try:
            value = json.loads(result.stdout)
            if not isinstance(value, dict): raise ValueError()
            return value
        except ValueError: raise RuntimeError("Unexpected GitHub identity response") from None
    status = read(["auth", "status", "--active", "--hostname", "github.com", "--json", "hosts"])
    hosts = status.get("hosts")
    accounts = hosts.get("github.com") if isinstance(hosts, dict) else None
    if (not isinstance(accounts, list) or len(accounts) != 1 or not isinstance(accounts[0], dict) or accounts[0].get("active") is not True or
            accounts[0].get("state") != "success" or accounts[0].get("tokenSource") != "keyring"):
        raise RuntimeError("Secure GitHub login required: gh auth login --hostname github.com --web")
    user = read(["api", "--hostname", "github.com", "user"])
    if type(user.get("id")) is not int or user["id"] != 90290458 or user.get("type") != "User":
        raise RuntimeError("This release authorizes only the verified repository owner")
    # Repository visibility is independent of the owner's installation policy.
    # Release access is checked by the subsequent authenticated download.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", args.tag):
        raise RuntimeError("Use an exact release tag")
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("This installer supports native Apple Silicon macOS")
    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError("Install GitHub CLI and use gh auth login --hostname github.com --web first")
    if any(os.environ.get(k) for k in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")):
        raise RuntimeError("Use GitHub CLI's OS credential store instead of token environment variables")
    secure_owner(gh)
    # The verified package renews the bounded offline owner session before activation.
    os.umask(0o077)
    root = safe(Path.home() / "Library/Application Support/LocalAI")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix=".private-release-", dir=root) as work:
        work = Path(work)
        run([gh, "release", "download", args.tag, "--repo", REPO, "--pattern", "*.whl", "--pattern", "SHA256SUMS", "--dir", work])
        wheels = list(work.glob("*.whl"))
        if len(wheels) != 1: raise RuntimeError("Expected one wheel in this release")
        wheel = wheels[0]
        sums = {}
        for line in (work / "SHA256SUMS").read_text().splitlines():
            if line.strip():
                value, name = line.split(maxsplit=1)
                name = name.lstrip(" *")
                if not re.fullmatch(r"[a-f0-9]{64}", value) or name in sums: raise RuntimeError("Invalid release checksums")
                sums[name] = value
        expected = sums.get(wheel.name)
        if expected is None or sha(wheel) != expected: raise RuntimeError("Release wheel checksum failed")
        # Reject path traversal, links, and non-package data before pip touches the wheel.
        with zipfile.ZipFile(wheel) as bundle:
            names = bundle.namelist()
            if len(names) != len(set(names)): raise RuntimeError("Duplicate wheel entries")
            for item in bundle.infolist():
                file = Path(item.filename)
                if file.is_absolute() or ".." in file.parts or (item.external_attr >> 16) & 0o170000 == 0o120000:
                    raise RuntimeError("Unsafe wheel entry")
                if not (item.filename.startswith("kryn/") or re.match(r"kryn-[^/]+\.dist-info/", item.filename)):
                    raise RuntimeError("Unexpected wheel top-level contents")
        uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
        env = os.environ.copy()
        env["UV_CACHE_DIR"] = str(root / "uv-cache")
        if not Path(uv).is_file():
            target = safe(root / "dependencies/uv-0.11.16/uv")
            receipt_file = safe(target.parent / "uv.json")
            if target.exists():
                receipt = json.loads(receipt_file.read_text())
                if receipt != {"archive_sha256": UV_SHA, "binary_sha256": sha(target)}:
                    raise RuntimeError("Preserving changed private uv installation")
            else:
                archive = work / "uv.tar.gz"
                with urllib.request.urlopen(UV_URL, timeout=60) as response, archive.open("wb") as stream:
                    shutil.copyfileobj(response, stream)
                if sha(archive) != UV_SHA: raise RuntimeError("Original-publisher uv checksum failed")
                with tarfile.open(archive) as bundle:
                    member = bundle.getmember("uv-aarch64-apple-darwin/uv")
                    if not member.isfile() or member.size > 100 * 1024**2: raise RuntimeError("Unexpected uv binary")
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    with target.open("xb") as stream: shutil.copyfileobj(bundle.extractfile(member), stream)
                    target.chmod(0o700)
                    receipt_file.write_text(json.dumps({"archive_sha256": UV_SHA, "binary_sha256": sha(target)}) + "\n")
            uv = str(target)
        env["PATH"] = str(Path(uv).parent) + os.pathsep + env.get("PATH", "")
        directory = safe(root / "packages" / expected)
        venv = directory / "venv"
        staging_receipt = {"schema": 1, "wheel": wheel.name, "sha256": expected, "tag": args.tag}
        stage_record = directory / "staging.json"
        complete_record = directory / "package.json"
        if directory.exists() and not complete_record.exists():
            if (not stage_record.is_file() or json.loads(stage_record.read_text()) != staging_receipt or
                    {p.name for p in directory.iterdir()} - {"staging.json", wheel.name, "venv"}):
                raise RuntimeError("Preserving unowned partial package installation")
            if (directory / wheel.name).exists() and sha(directory / wheel.name) != expected:
                raise RuntimeError("Preserving changed staged wheel")
            if venv.is_symlink(): raise RuntimeError("Linked partial environment is refused")
            if venv.exists(): shutil.rmtree(venv)
        if not complete_record.exists():
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            stage_record.write_text(json.dumps(staging_receipt) + "\n")
            cached = directory / wheel.name
            shutil.copyfile(wheel, cached)
            # Reuse an existing compatible managed Python where possible.
            found = subprocess.run([uv, "python", "find", "3.13", "--managed-python"], capture_output=True, text=True, env=env)
            python = found.stdout.strip() if found.returncode == 0 else "3.13.13"
            if found.returncode: env["UV_PYTHON_INSTALL_DIR"] = str(root / "python")
            run([uv, "venv", "--python", python, venv], env=env)
            run([uv, "pip", "install", "--python", venv / "bin/python", "--no-index", "--no-deps", cached], env=env)
            run([venv / "bin/python", "-E", "-B", "-m", "kryn", "--package-check"], env=env)
            complete_record.write_text(json.dumps(staging_receipt) + "\n")
            stage_record.unlink()
        else:
            receipt = json.loads((directory / "package.json").read_text())
            if receipt != {"schema": 1, "wheel": wheel.name, "sha256": expected, "tag": args.tag} or sha(directory / wheel.name) != expected:
                raise RuntimeError("Preserving changed or incomplete package installation")
            run([venv / "bin/python", "-E", "-B", "-m", "kryn", "--package-check"], env=env)
        run([venv / "bin/python", "-E", "-B", "-m", "kryn", "install"], env=env)


if __name__ == "__main__":
    try: main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit("STOP: " + str(error))
