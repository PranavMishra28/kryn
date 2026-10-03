#!/usr/bin/env python3
"""Public one-turn compatibility screen with an encrypted hidden oracle mounted.

This is not a protected holdout task or a harness-quality score. The pinned
external adapter owns the real OpenCode loop and resource guard.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import secrets
import signal
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from native_client import background_boundary
from run_external_patch import run as run_external
from check_holdout_boundary import probe


def command(args, *, input=None, timeout=30):
    return subprocess.run(args, input=input, capture_output=True, text=True,
                          timeout=timeout, close_fds=True)


def _bound_output():
    resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))


def grade(workspace, private, oracle, source=None):
    cases = json.loads(oracle.read_text())
    python = Path(sys.executable).resolve()
    dependencies = [python, Path(sys.base_prefix).resolve()]
    if source is not None:
        dependencies.append(source.resolve())  # Exact reference file, for reference preflight only.
    prefix = background_boundary(workspace, private, dependencies, None)
    results = []
    for case in cases:
        with tempfile.TemporaryFile() as output:
            process = subprocess.Popen(prefix + [str(python), "-I", "-B",
                str(source or workspace / "solve.py")], cwd=workspace, stdin=subprocess.PIPE,
                stdout=output, stderr=subprocess.DEVNULL, close_fds=True,
                start_new_session=True, preexec_fn=_bound_output)
            timed_out = False
            try:
                try:
                    process.communicate(input=json.dumps(case["input"]).encode(), timeout=10)
                except subprocess.TimeoutExpired:
                    timed_out = True
            finally:
                # A child holding stdout cannot prevent cleanup or retain the mount.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                if process.poll() is None:
                    process.wait(timeout=2)
            output.seek(0)
            payload = output.read(65537)
        try:
            actual = json.loads(payload)
        except json.JSONDecodeError:
            actual = None
        results.append(not timed_out and len(payload) <= 65536
                       and process.returncode == 0 and actual == case["expected"])
    return all(results)


def model_check_succeeded(path):
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        part = entry.get("part", {})
        if part.get("type") != "tool" or part.get("tool") != "shell":
            continue
        state = part.get("state", {})
        command = state.get("input", {}).get("command", "")
        exit_code = state.get("output", {}).get("metadata", {}).get("metadata", {}).get("exit")
        if (state.get("status") == "completed" and exit_code == 0 and
                "python" in command and ("solve.py" in command or "import solve" in command)):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="new private /private/tmp directory")
    args = parser.parse_args()
    root = args.root.absolute()
    if not root.is_relative_to(Path("/private/tmp")) or root.exists() or root.is_symlink():
        parser.error("Choose a new canonical /private/tmp run directory")
    root.mkdir(mode=0o700)
    workspace, private, mount = (root / name for name in ("workspace", "private", "grader"))
    for directory in (workspace, private, mount):
        directory.mkdir(mode=0o700)
    (workspace / "solve.py").write_text(
        "import json,sys\n"
        "def total(values):\n    return len(values)\n"
        "if __name__ == '__main__':\n    print(json.dumps(total(json.load(sys.stdin))))\n")
    (workspace / "visible.txt").write_text("candidate-visible")
    prompt = root / "prompt.txt"
    prompt.write_text("Fix solve.py so total(values) sums signed integers, "
                      "including an empty list. Preserve JSON stdin/stdout. "
                      "Read the source and run a check. Do not create new files.\n")
    commands = (["/usr/bin/git", "init", "-q", str(workspace)],
                ["/usr/bin/git", "-C", str(workspace), "add", "solve.py", "visible.txt"],
                ["/usr/bin/git", "-C", str(workspace), "-c", "user.name=Research",
                 "-c", "user.email=research@example.invalid", "commit", "-qm", "seed"])
    for argv in commands:
        subprocess.run(argv, check=True, capture_output=True, timeout=20)
    base = command(["/usr/bin/git", "-C", str(workspace), "rev-parse", "HEAD"]).stdout.strip()
    image = root / "oracle.dmg"
    key = secrets.token_hex(32) + "\n"
    mounted = False
    result = {"schema": 1, "kind": "public_boundary_compatibility", "base_commit": base,
              "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest()}
    try:
        created = command(["hdiutil", "create", "-size", "16m", "-fs", "APFS",
                           "-volname", "KRYNPublicCanary", "-encryption", "AES-256",
                           "-stdinpass", str(image)], input=key)
        if created.returncode:
            raise RuntimeError("Encrypted image creation failed")
        info = command(["hdiutil", "imageinfo", "-stdinpass", str(image)], input=key)
        if info.returncode or "Encrypted: true" not in info.stdout:
            raise RuntimeError("Encrypted image identity was not verified")
        attached = command(["hdiutil", "attach", "-nobrowse", "-noverify",
                            "-stdinpass", "-mountpoint", str(mount), str(image)], input=key)
        if attached.returncode:
            raise RuntimeError("Encrypted image could not mount")
        mounted = True
        devices = re.findall(r"/dev/disk\d+(?:s\d+)?", attached.stdout)
        oracle = mount / "oracle.json"
        oracle.write_text(json.dumps([
            {"input": [2, -1, 4], "expected": 5},
            {"input": [], "expected": 0},
            {"input": [-3, -2], "expected": -5},
        ]))
        result["oracle_sha256"] = hashlib.sha256(oracle.read_bytes()).hexdigest()
        result["boundary"] = probe(workspace, private, oracle, image,
                                   devices[-1] if devices else None)
        for alias in (workspace / "oracle-symlink", workspace / "oracle-hardlink"):
            alias.unlink(missing_ok=True)
        if not all(result["boundary"].values()):
            raise RuntimeError("Encrypted boundary preflight failed")
        result["broken_seed_rejected"] = not grade(workspace, private, oracle)
        reference = mount / "reference.py"
        reference.write_text(
            "import json,sys\n"
            "def total(values):\n    return sum(values)\n"
            "if __name__ == '__main__':\n    print(json.dumps(total(json.load(sys.stdin))))\n")
        candidate_prefix = background_boundary(workspace, private,
            [Path(sys.executable).resolve(), Path(sys.base_prefix).resolve()], None)
        hidden = command(candidate_prefix + ["/bin/cat", str(reference)], timeout=5)
        result["reference_hidden_from_candidate"] = hidden.returncode != 0
        if not result["reference_hidden_from_candidate"]:
            raise RuntimeError("Candidate grader can read the reference")
        result["reference_passed"] = grade(workspace, private, oracle, reference)
        if not (result["broken_seed_rejected"] and result["reference_passed"]):
            raise RuntimeError("Public fixture seed/reference preflight failed")
        trial = run_external(argparse.Namespace(workspace=workspace, base_commit=base,
            task_id="boundary-public-sum-20261003", prompt=prompt,
            evidence=root / "evidence", arm="kryn", tool_venv=None, timeout=300))
        result["driver_completed"] = trial["completed"]
        result["intervention"] = trial.get("intervention")
        result["wall_seconds"] = trial.get("wall_seconds")
        result["independent_grade_passed"] = grade(workspace, private, oracle)
        result["model_check_succeeded"] = model_check_succeeded(root / "evidence/events.jsonl")
        result["patch_sha256"] = trial.get("patch_sha256")
        result["resource_guard_reason"] = trial.get("resources", {}).get("guard_reason")
        result["passed"] = bool(result["driver_completed"] and result["independent_grade_passed"]
                                and result["model_check_succeeded"])
    except Exception as failure:
        result["error"] = type(failure).__name__ + ": " + str(failure)
    finally:
        if mounted:
            try:
                detached = command(["hdiutil", "detach", str(mount)])
                result["oracle_detached"] = detached.returncode == 0
            except Exception:
                result["oracle_detached"] = False
        result["passed"] = bool(result.get("passed") and result.get("oracle_detached"))
        (root / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
