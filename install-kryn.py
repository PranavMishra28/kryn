#!/usr/bin/env python3
"""Install a checksum-verified public GitHub release."""
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
import urllib.parse
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


class HTTPSReleaseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if target.scheme != "https" or target.hostname not in {
                "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}:
            raise RuntimeError("Release redirect left trusted HTTPS hosts")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def download_public(url, destination, limit):
    """Fetch public release bytes without GitHub CLI, account config or auth headers."""
    request = urllib.request.Request(url, headers={"User-Agent": "KRYN-installer"})
    opener = urllib.request.build_opener(HTTPSReleaseRedirect())
    with opener.open(request, timeout=60) as response, destination.open("xb") as stream:
        size = 0
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                raise RuntimeError("Release asset exceeds its download limit")
            stream.write(chunk)


def public_release(tag, work):
    base = f"https://github.com/{REPO}/releases/download/{tag}/"
    checksum = work / "SHA256SUMS"
    download_public(base + "SHA256SUMS", checksum, 65536)
    wheel_name = f"kryn-{tag[1:]}-py3-none-any.whl"
    sums = {}
    for line in checksum.read_text().splitlines():
        if line.strip():
            value, name = line.split(maxsplit=1)
            name = name.lstrip(" *")
            if not re.fullmatch(r"[a-f0-9]{64}", value) or name in sums:
                raise RuntimeError("Invalid release checksums")
            sums[name] = value
    if set(sums) != {wheel_name, "install-kryn.py"}:
        raise RuntimeError("Release checksums do not match the requested version")
    wheel = work / wheel_name
    download_public(base + wheel_name, wheel, 50 * 1024**2)
    if sha(wheel) != sums[wheel_name]:
        raise RuntimeError("Release wheel checksum failed")
    return wheel, sums[wheel_name]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", args.tag):
        raise RuntimeError("Use an exact release tag")
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("This installer supports native Apple Silicon macOS")
    os.umask(0o077)
    root = safe(Path.home() / "Library/Application Support/LocalAI")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix=".kryn-release-", dir=root) as work:
        work = Path(work)
        wheel, expected = public_release(args.tag, work)
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
        env = {key: value for key, value in os.environ.items()
               if not any(part in key.upper() for part in ("TOKEN", "API_KEY", "SECRET"))}
        uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
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
