"""Read-only discovery of checksum-verified public KRYN releases."""
import hashlib
import importlib.util
import json
from pathlib import PurePosixPath, Path
import re
import tempfile
import unicodedata
import zipfile

from .installer import payload

RELEASES = "https://api.github.com/repos/PranavMishra28/kryn/releases?per_page=20"


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r"v?(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})", value):
        raise ValueError("Expected an exact release version")
    return tuple(map(int, value.removeprefix("v").split(".")))


def release_manifest(wheel, tag):
    """Inspect verified bytes without importing or extracting candidate code."""
    with zipfile.ZipFile(wheel) as bundle:
        items = bundle.infolist()
        names = [item.filename for item in items]
        if len(names) != len(set(names)) or sum(item.file_size for item in items) > 100 * 1024**2:
            raise ValueError("Invalid or oversized release wheel")
        for item in items:
            name = PurePosixPath(item.filename)
            if (name.is_absolute() or ".." in name.parts or "\\" in item.filename or
                    (item.external_attr >> 16) & 0o170000 == 0o120000 or
                    not item.filename.startswith(("kryn/", f"kryn-{tag[1:]}.dist-info/"))):
                raise ValueError("Unsafe release wheel entry")
        manifest = json.loads(bundle.read("kryn/manifest.json"))
        if (not isinstance(manifest, dict) or manifest.get("schema") != 1 or manifest.get("version") != tag[1:] or
                manifest.get("source_dirty") is not False or
                not re.fullmatch(r"[a-f0-9]{40}", manifest.get("source_revision", ""))):
            raise ValueError("Release is not a clean, versioned source build")
        files = manifest["files"]
        if not isinstance(files, dict) or not files:
            raise ValueError("Missing release payload")
        expected = {"kryn/payload/" + name for name in files}
        actual = {name for name in names if name.startswith("kryn/payload/") and not name.endswith("/")}
        if actual != expected:
            raise ValueError("Release payload inventory mismatch")
        for name, digest in files.items():
            if hashlib.sha256(bundle.read("kryn/payload/" + name)).hexdigest() != digest:
                raise ValueError("Release payload checksum mismatch")
        if not {"kryn/cli.py", "kryn/installer.py", "kryn/__init__.py",
                "kryn/payload/install-kryn.py"} <= set(names):
            raise ValueError("Missing KRYN updater")
        return manifest


def check_update(current):
    result = {"status": "unavailable", "installed_version": current["version"],
              "installed_revision": current["source_revision"]}
    try:
        installed = version(current["version"])
        spec = importlib.util.spec_from_file_location("kryn_release_download", payload() / "install-kryn.py")
        bootstrap = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bootstrap)
        with tempfile.TemporaryDirectory(prefix="kryn-update-check-") as temporary:
            work = Path(temporary)
            metadata = work / "releases.json"
            # The existing updater owns HTTPS redirect, byte-limit and checksum policy.
            # No GitHub CLI, account credentials or candidate code is executed.
            bootstrap.download_public(RELEASES, metadata, 2 * 1024**2)
            releases = json.loads(metadata.read_text())
            if not isinstance(releases, list):
                raise ValueError("Invalid release listing")
            candidates = []
            for release in releases:
                if not isinstance(release, dict) or release.get("draft") is not False or not release.get("published_at"):
                    continue
                tag = release.get("tag_name", "")
                try:
                    newer = tag.startswith("v") and version(tag) > installed
                except (ValueError, AttributeError):
                    continue
                if newer:
                    candidates.append(release)
            if not candidates:
                return {**result, "status": "current"}
            release = max(candidates, key=lambda item: version(item["tag_name"]))
            tag = release["tag_name"]
            required = {"SHA256SUMS", "install-kryn.py", f"kryn-{tag[1:]}-py3-none-any.whl"}
            assets = {asset["name"] for asset in release["assets"]
                      if isinstance(asset, dict) and asset.get("state") == "uploaded"}
            if not required <= assets:
                raise ValueError("Release assets are incomplete")
            wheel, digest = bootstrap.public_release(tag, work)
            manifest = release_manifest(wheel, tag)
            notes = release.get("body") or release.get("name") or "See release notes on GitHub."
            notes = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", notes)
            notes = " ".join("".join(c for c in notes if c in "\n\t" or
                                   not unicodedata.category(c).startswith("C")).split())
            summary = notes if len(notes) <= 240 else notes[:240].rsplit(" ", 1)[0] + "…"
            return {**result, "status": "available", "tag": tag,
                    "source_revision": manifest["source_revision"], "sha256": digest,
                    "prerelease": release.get("prerelease") is True,
                    "summary": summary,
                    "url": f"https://github.com/PranavMishra28/kryn/releases/tag/{tag}"}
    except (OSError, ValueError, KeyError, RuntimeError, TypeError, zipfile.BadZipFile):
        # A network/rate-limit/integrity failure is unknown, never "up to date".
        return result
