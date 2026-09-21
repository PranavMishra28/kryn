#!/usr/bin/env python3
"""Build a private wheel from a curated stage, never from ignored personal state."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

FILES = ["LICENSE", "THIRD_PARTY_NOTICES.md", "install-kryn.py",
    "setup/setup.py", "setup/deploy_client.py", "setup/AGENTS.md", "setup/accepted-profile.json",
    "setup/model-sha256.json", "setup/opencode.template.json", "setup/browser-package-lock.json",
    "tools/localai.py", "tools/native_client.py", "tools/context_probe.py", "tools/protocol_probe.py",
    "tools/improvement.py", "tools/learning.py", "tools/owner_auth.py", "tools/native-shell",
    "tools/kryn_plugin.mjs", "tools/kryn_tui.tsx", "tools/permission_display.mjs", "tools/session_report.py", "tools/run_native_trial.py", "tools/browser_check.mjs",
    "tools/native_lifecycle_probe.py", "tools/inference-audit/server.js", "tools/inference-audit/package.json",
    "evals/README.md", "evals/bench.py", "evals/checks.py", "evals/tasks.json", "evals/frozen.sha256.json"]


def source_files(root):
    frozen = json.loads((root / "evals/frozen.sha256.json").read_text())
    fixtures = ["evals/" + name for name in frozen if name.startswith(("fixture/", "references/"))]
    paths = FILES + fixtures
    for name in fixtures:
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != frozen[name.removeprefix("evals/")]:
            raise RuntimeError("Frozen evaluation payload changed: " + name)
    for relative in paths:
        file = root / relative
        if not file.is_file() or file.is_symlink() or file.stat().st_size > 5 * 1024**2:
            raise RuntimeError("Unshippable payload file: " + relative)
    return sorted(set(paths))


def stage(root, destination, revision, dirty=False):
    for file in (root / "src/kryn").glob("*.py"):
        target = destination / "src/kryn" / file.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, target)
    shutil.copyfile(root / "pyproject.toml", destination / "pyproject.toml")
    files = {}
    for name in source_files(root):
        target = destination / "src/kryn/payload" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
        files[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = {"schema": 1, "version": "0.1.6", "source_revision": revision, "source_dirty": dirty, "files": files}
    (destination / "src/kryn/manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("dist"))
    parser.add_argument("--candidate", action="store_true", help="Allow a truthfully marked dirty-tree candidate; never a published final release")
    parser.add_argument("--uv", default=shutil.which("uv"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if not args.uv: raise RuntimeError("uv is required to build the pinned hatchling wheel")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip())
    if dirty and not args.candidate: raise RuntimeError("Commit the intended source before final build, or pass --candidate")
    output = args.out_dir.absolute()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kryn-package-stage-") as work:
        work = Path(work)
        manifest = stage(root, work, revision, dirty)
        subprocess.run([args.uv, "build", "--wheel", "--out-dir", output, work], check=True)
    wheel = output / "kryn-0.1.6-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as bundle:
        names = bundle.namelist()
        required = {"kryn/payload/" + name for name in manifest["files"]} | {"kryn/manifest.json", "kryn/cli.py", "kryn/installer.py"}
        if not required <= set(names) or any("/runs/" in name or "node_modules" in name or name.endswith(".safetensors") for name in names):
            raise RuntimeError("Wheel contents failed curation check")
    shutil.copyfile(root / "install-kryn.py", output / "install-kryn.py")
    sums = [hashlib.sha256((output / name).read_bytes()).hexdigest() + "  " + name for name in (wheel.name, "install-kryn.py")]
    (output / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(json.dumps({"wheel": str(wheel), "source_revision": revision, "source_dirty": dirty,
                      "payload_files": len(manifest["files"]), "sha256": sums[0].split()[0]}))


if __name__ == "__main__":
    main()
