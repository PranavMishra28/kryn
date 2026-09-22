"""Optional native macOS evaluator for one pinned SWE-bench Verified Requests task.

No model calls. State and test/reference material must remain outside this checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET

COMMIT = "0192aac24123735b3eaf9b08df46429bb770c283"
DATASET_REVISION = "c104f840cc67f8b6eec6f759ebc8b2693d585d4a"
INSTANCE = "psf__requests-6028"
SOURCE_SHA256 = "acf8041195a5fdd1177612ddb93b159424de40d95b7156567c162405864a3cb8"
INPUTS_SHA256 = "22f43a3293a6d6a1b99da3816195518a6d7f84e76f230fd21a0e83c1cfa85246"
CASES_SHA256 = "392840d14a4578a3e7ffe58ee470e14535efb360927307f7418b1c7660733f0b"
FIELDS = {
    "problem_statement": ("problem.txt", "1d82b6998adb429d6d13a59c0c321de5ea24889a19843d4de7ea4dff06739cc0"),
    "patch": ("reference.patch", "9cd3e2a2c10cc8b9555156f0e9cda00c67aa4e08f40ebd125f417bbeb41b2fb3"),
    "test_patch": ("test.patch", "cc4b0007afd140c1737b08e14d0cbb9dbccfbee483146d5112971dd7b9bcb142"),
}
REQUIREMENTS = """attrs==26.1.0
certifi==2021.10.8
charset-normalizer==2.0.12
idna==3.3
iniconfig==2.3.0
packaging==26.3
pluggy==1.6.0
py==1.11.0
pytest==6.2.5
pytest-mock==2.0.0
toml==0.10.2
urllib3==1.26.7
"""
ROOT = UPSTREAM = ORACLE = PYTHON = None


def configure(state):
    global ROOT, UPSTREAM, ORACLE, PYTHON
    state = Path(state).expanduser()
    checkout = Path(__file__).resolve().parents[1]
    ROOT = state.resolve()
    if state.is_symlink() or ROOT.is_relative_to(checkout) or checkout.is_relative_to(ROOT):
        raise ValueError("Choose a dedicated state directory outside the repository")
    UPSTREAM, ORACLE, PYTHON = ROOT / "upstream", ROOT / "oracle", ROOT / "venv/bin/python"


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def protected():
    return [*sorted((UPSTREAM / "tests").rglob("*")), *[UPSTREAM / name for name in
        ("pytest.ini", "setup.cfg", "setup.py", "requirements-dev.txt", "tox.ini")]]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args, cwd, **kwargs):
    args = [str(x) for x in args]
    if Path(args[0]).name == "git":
        env = {key: value for key, value in kwargs.pop("env", os.environ).items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
        kwargs["env"] = env
        args[1:1] = ["-c", "core.hooksPath=/dev/null"]
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True, **kwargs)


def verify_inputs():
    manifest = json.loads((ORACLE / "input-hashes.json").read_text())
    if canonical(manifest) != INPUTS_SHA256:
        raise RuntimeError("Fixture input manifest differs from the frozen definition")
    if {str(p.relative_to(UPSTREAM)) for p in UPSTREAM.rglob("*") if p.is_file() or p.is_symlink()} != {name.removeprefix("upstream/") for name in manifest if name.startswith("upstream/")}:
        raise RuntimeError("Upstream file inventory changed")
    for name, expected in manifest.items():
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise RuntimeError(f"Fixture input changed: {name}")
    verify_environment()


def verify_environment():
    script = "import sys,json,importlib.metadata as m; print(json.dumps([list(sys.version_info[:3]), {n:m.version(n) for n in sys.argv[1:]}]))"
    expected = dict(line.split("==") for line in REQUIREMENTS.splitlines())
    actual = json.loads(command([PYTHON, "-I", "-c", script, *expected], ROOT, timeout=15).stdout)
    if actual != [[3, 10, 16], expected]:
        raise RuntimeError("Fixture requires Python 3.10.16 and its exact dependency versions")


def prepare(label):
    verify_inputs()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", label):
        raise ValueError("Unsafe fixture label")
    workspace = ROOT / "workspaces" / label
    if workspace.exists():
        raise FileExistsError(workspace)
    shutil.copytree(UPSTREAM, workspace)
    shutil.copyfile(ORACLE / "problem.txt", workspace / "TASK.md")
    command(["git", "init", "-q", "--initial-branch=main"], workspace)
    command(["git", "add", "."], workspace)
    command(["git", "-c", "commit.gpgsign=false", "-c", "user.name=KRYN Evaluation", "-c", "user.email=eval@localhost", "commit", "-qm", f"Frozen upstream Requests fixture {COMMIT}"], workspace)
    if command(["git", "status", "--porcelain", "--untracked-files=all"], workspace).stdout:
        raise RuntimeError("Prepared fixture Git workspace is not clean")
    return workspace


def grade(workspace):
    verify_inputs()
    workspace = Path(workspace)
    if workspace.is_symlink() or not workspace.is_dir():
        raise ValueError("Workspace must be a directory")
    workspace = workspace.resolve()
    out = Path(tempfile.mkdtemp(prefix="grade-", dir=ROOT / "grades"))
    protected_changes = []
    for source in protected():
        if not source.is_file():
            continue
        rel = source.relative_to(UPSTREAM)
        candidate = workspace / rel
        if candidate.is_symlink() or not candidate.is_file() or digest(candidate) != digest(source):
            protected_changes.append(str(rel))
    original_conftests = {p.relative_to(UPSTREAM) for p in UPSTREAM.rglob("conftest.py")}
    for p in workspace.rglob("conftest.py"):
        if ".git" not in p.relative_to(workspace).parts and p.relative_to(workspace) not in original_conftests:
            protected_changes.append(str(p.relative_to(workspace)))
    symlinks = [str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_symlink() and ".git" not in p.relative_to(workspace).parts]
    result = {"instance_id": "psf__requests-6028", "base_commit": COMMIT, "protected_files_preserved": not protected_changes, "protected_changes": sorted(set(protected_changes)), "symlinks": symlinks, "checks": {}, "passed": False}
    if protected_changes or symlinks:
        (out / "grade.json").write_text(json.dumps(result, indent=2) + "\n")
        return result | {"evidence": str(out)}

    target = out / "workspace"
    shutil.copytree(workspace, target, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".kryn", ".opencode"))
    command(["git", "apply", "--check", ORACLE / "test.patch"], target)
    command(["git", "apply", ORACLE / "test.patch"], target)
    result["checks"], observed = run_checks(target, out)
    expected = json.loads((ORACLE / "expected-cases.json").read_text())
    for name, check in result["checks"].items():
        check["exact_case_and_skip_set"] = observed[name] == expected[name]
    result["passed"] = all(v["exit_code"] == 0 and not v["failures"] and v["exact_case_and_skip_set"] for v in result["checks"].values())
    (out / "grade.json").write_text(json.dumps(result, indent=2) + "\n")
    return result | {"evidence": str(out)}



def run_checks(target, out):
    checks, observed_cases = {}, {}
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_PLUGINS", None)
    env.pop("PYTHONPATH", None)
    check_import = command([PYTHON, "-E", "-B", "-c", "import requests; print(requests.__file__)"], target, env=env, timeout=15)
    if Path(check_import.stdout.strip()).resolve() != target / "requests/__init__.py":
        raise RuntimeError("Tests would import a different Requests checkout")
    for name, extra in [("focused", ["-k", "prepend_scheme_if_needed"]), ("adjacent_module", [])]:
        args = [str(PYTHON), "-I", "-B", "-m", "pytest", "-p", "pytest_mock", "-q", "tests/test_utils.py", "--junitxml", str(out / f"{name}.xml"), *extra]
        started = time.monotonic()
        proc = subprocess.run(args, cwd=target, env=env, text=True, capture_output=True, timeout=120)
        (out / f"{name}.stdout").write_text(proc.stdout)
        (out / f"{name}.stderr").write_text(proc.stderr)
        suites = ET.parse(out / f"{name}.xml").getroot()
        cases = list(suites.iter("testcase"))
        failures = [c.attrib.get("name") for c in cases if c.find("failure") is not None or c.find("error") is not None]
        # Upstream parametrizes absolute workspace paths and pytest.__file__.
        # Normalize only these owned prefixes; every case and skip must match.
        observed = sorted((c.attrib.get("classname", ""), c.attrib["name"].replace(str(target), "<workspace>").replace(str(ROOT / "venv"), "<venv>"), c.find("skipped") is not None) for c in cases)
        observed_cases[name] = [list(x) for x in observed]
        checks[name] = {"exit_code": proc.returncode, "seconds": round(time.monotonic() - started, 3), "cases": len(cases), "failures": failures, "skipped": sum(c.find("skipped") is not None for c in cases)}
    return checks, observed_cases


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as reply:
        data = reply.read(16 * 1024**2 + 1)
    if len(data) > 16 * 1024**2:
        raise RuntimeError("Fixture download exceeds the bounded expected size")
    return data


def initialize(source_archive=None, instance_json=None):
    if ROOT.exists() and any(ROOT.iterdir()):
        raise FileExistsError("Initialization requires a new or empty state directory")
    ROOT.mkdir(parents=True, mode=0o700, exist_ok=True)
    for name in ("oracle", "grades", "workspaces"):
        (ROOT / name).mkdir(mode=0o700)
    archive = Path(source_archive).read_bytes() if source_archive else fetch(
        f"https://codeload.github.com/psf/requests/tar.gz/{COMMIT}")
    if hashlib.sha256(archive).hexdigest() != SOURCE_SHA256:
        raise RuntimeError("Source archive differs from the pinned upstream commit")
    (ROOT / "source.tar.gz").write_bytes(archive)
    UPSTREAM.mkdir()
    with tarfile.open(ROOT / "source.tar.gz") as source:
        prefix = "requests-" + COMMIT
        for member in source.getmembers():
            parts = Path(member.name).parts
            if not parts or parts[0] != prefix or ".." in parts or not (member.isfile() or member.isdir()):
                raise RuntimeError("Unexpected archive entry")
            target = UPSTREAM.joinpath(*parts[1:])
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as stream:
                    target.write_bytes(stream.read())
                target.chmod(member.mode & 0o777)
    if instance_json:
        instance = json.loads(Path(instance_json).read_text())
    else:
        # The rows service is not revision-addressable. Exact field hashes below
        # enforce the frozen instance even if the dataset's current head changes.
        rows = json.loads(fetch("https://datasets-server.huggingface.co/rows?dataset=princeton-nlp%2FSWE-bench_Verified&config=default&split=test&offset=297&length=1"))
        instance = rows["rows"][0]["row"]
    if (instance.get("instance_id"), instance.get("repo"), instance.get("base_commit"),
            instance.get("environment_setup_commit")) != (INSTANCE, "psf/requests", COMMIT, COMMIT):
        raise RuntimeError("Unexpected dataset instance")
    for field, (name, expected) in FIELDS.items():
        data = instance[field].encode()
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError("Frozen dataset field changed: " + field)
        (ORACLE / name).write_bytes(data)
    (ROOT / "requirements.lock.txt").write_text(REQUIREMENTS)
    command(["uv", "--no-config", "venv", "--managed-python", "--python", "3.10.16", ROOT / "venv"], ROOT, timeout=180)
    command(["uv", "--no-config", "pip", "install", "--python", PYTHON, "--only-binary", ":all:",
             "-r", ROOT / "requirements.lock.txt"], ROOT, timeout=180)
    verify_environment()
    reference = ORACLE / "calibration"
    shutil.copytree(UPSTREAM, reference)
    for patch in ("reference.patch", "test.patch"):
        command(["git", "apply", ORACLE / patch], reference)
    checks, cases = run_checks(reference, ORACLE)
    if canonical(cases) != CASES_SHA256 or any(check["exit_code"] or check["failures"] for check in checks.values()):
        raise RuntimeError("Reference validation or frozen case/skip identities differ; do not recalibrate the oracle")
    save(ORACLE / "expected-cases.json", cases)
    inputs = [*UPSTREAM.rglob("*"), ROOT / "requirements.lock.txt", ORACLE / "expected-cases.json",
              *[ORACLE / name for name, _ in FIELDS.values()]]
    manifest = {str(p.relative_to(ROOT)): digest(p) for p in sorted(inputs) if p.is_file()}
    if canonical(manifest) != INPUTS_SHA256:
        raise RuntimeError("Reconstructed fixture differs from the original 102 pinned inputs")
    save(ORACLE / "input-hashes.json", manifest)
    save(ORACLE / "provenance.json", {"instance_id": INSTANCE, "base_commit": COMMIT,
        "dataset": "princeton-nlp/SWE-bench_Verified", "dataset_revision": DATASET_REVISION,
        "source_sha256": SOURCE_SHA256, "input_manifest_sha256": INPUTS_SHA256,
        "case_identity_normalization": "Only owned grader workspace and evaluator venv prefixes become <workspace> and <venv>. No assertion, case or skip changes.",
        "scope": "Native macOS single-task adaptation, not the official Docker benchmark. Public task may be training-contaminated."})
    verify_inputs()
    return {"initialized": True, "state": str(ROOT), "reference_checks": checks}


def selftest():
    verify_inputs()
    run = Path(tempfile.mkdtemp(prefix="selftest-", dir=ORACLE))
    base = run / "base"
    shutil.copytree(UPSTREAM, base)
    broken = grade(base)
    good = run / "reference"
    shutil.copytree(UPSTREAM, good)
    command(["git", "apply", ORACLE / "reference.patch"], good)
    reference = grade(good)
    with (good / "tests/test_utils.py").open("a") as stream:
        stream.write("\n# Deliberate protected-test mutation for evaluator self-test.\n")
    tampered = grade(good)
    expected_failures = {
        "test_prepend_scheme_if_needed[http://user:pass@example.com/path?query-http://user:pass@example.com/path?query]",
        "test_prepend_scheme_if_needed[http://user@example.com/path?query-http://user@example.com/path?query]",
    }
    passed = (not broken["passed"] and reference["passed"] and not tampered["passed"] and
        tampered["protected_changes"] == ["tests/test_utils.py"] and not tampered["checks"] and
        all(set(check["failures"]) == expected_failures and check["exact_case_and_skip_set"] for check in broken["checks"].values()))
    result = {"passed": passed, "scope": "Evaluator validation only; no model run", "base": broken,
              "reference": reference, "changed_test": tampered}
    save(run / "validation.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True, help="Dedicated evaluator state outside the repository")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--source-archive", type=Path, help="Optional cached pinned source archive")
    init.add_argument("--instance-json", type=Path, help="Optional cached official dataset row object")
    commands.add_parser("prepare").add_argument("label")
    commands.add_parser("grade").add_argument("workspace", type=Path)
    commands.add_parser("selftest")
    args = parser.parse_args()
    configure(args.state)
    if args.command == "init":
        result = initialize(args.source_archive, args.instance_json)
    elif args.command == "prepare":
        print(prepare(args.label))
        return 0
    elif args.command == "grade":
        result = grade(args.workspace)
    else:
        result = selftest()
    print(json.dumps(result, indent=2))
    return 0 if result.get("passed", result.get("initialized", False)) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError, ET.ParseError) as error:
        print(json.dumps({"setup_error": str(error)}), file=sys.stderr)
        raise SystemExit(2)
