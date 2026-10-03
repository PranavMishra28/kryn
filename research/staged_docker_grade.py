"""Grade the public staged fixture in a fresh Docker-visible clone."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import tempfile

from agent_grade_barrier import clean_clone
from run_external_patch import drive
from ui_gateway.preflight import prove_container_absent

IMAGE = "python@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0"
MAX_SOURCE = 1024 * 1024


def source_bytes(workspace, name):
    root = Path(workspace)
    fd = os.open(root / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_dev != root.stat().st_dev or
                info.st_size > MAX_SOURCE):
            raise RuntimeError("Staged source is not a bounded same-device regular file")
        data = b""
        while len(data) <= MAX_SOURCE:
            chunk = os.read(fd, min(65536, MAX_SOURCE + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) != info.st_size:
            raise RuntimeError("Staged source changed during copy")
        return data
    finally:
        os.close(fd)


def grade(workspace, seed, base_commit, oracle, stage_root, *, source_override=None,
          cancelled=lambda: False):
    cases = json.loads(Path(oracle).read_text())
    if not isinstance(cases, list) or not cases:
        raise ValueError("Frozen stage oracle is empty")
    stage_root = Path(stage_root)
    stage_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    expected = {name: source_bytes(workspace, name) for name in ("solve.py", "rules.json")}
    if source_override is not None:
        expected["solve.py"] = Path(source_override).read_bytes()
    results = []
    with tempfile.TemporaryDirectory(prefix="stage-", dir=stage_root) as temporary:
        staged = Path(temporary) / "workspace"
        clean_clone(seed, staged, base_commit)
        for name, data in expected.items():
            (staged / name).write_bytes(data)
            (staged / name).chmod(0o644)
        staged.chmod(0o755)
        staged_hashes = {name: hashlib.sha256((staged / name).read_bytes()).hexdigest()
                         for name in expected}
        for case in cases:
            if cancelled():
                raise RuntimeError("Resource guard stopped staged Docker grading")
            container = "kryn-stage-" + secrets.token_hex(12)
            command = ["docker", "run", "--rm", "--name", container, "--interactive",
                       "--network", "none", "--read-only", "--cap-drop", "ALL",
                       "--security-opt", "no-new-privileges", "--pids-limit", "32",
                       "--memory", "256m", "--cpus", "1", "--user", "65534:65534",
                       "--workdir", "/workspace", "--mount",
                       f"type=bind,src={staged},dst=/workspace,readonly", IMAGE,
                       "python", "-I", "-B", "/workspace/solve.py"]
            child = subprocess.Popen(command, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     start_new_session=True)
            try:
                cause, output, errors = drive(child, json.dumps(case["input"]).encode(),
                                              20, cancelled)
                exit_code = child.wait(timeout=2) if cause is None else None
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=2)
                for pipe in (child.stdin, child.stdout, child.stderr):
                    if pipe and not pipe.closed:
                        pipe.close()
                subprocess.run(["docker", "rm", "-f", container],
                               capture_output=True, timeout=5, check=False)
                prove_container_absent(container)
            try:
                actual = json.loads(output) if cause is None and exit_code == 0 else None
            except json.JSONDecodeError:
                actual = None
            valid_json = actual is not None
            results.append({"passed": cause is None and exit_code == 0 and
                            actual == case["expected"], "valid_json": valid_json,
                            "exit": exit_code,
                            "cause": cause, "stderr_sha256": hashlib.sha256(errors).hexdigest(),
                            "output_bytes": len(output)})
        current = {name: hashlib.sha256(source_bytes(workspace, name)).hexdigest()
                   for name in expected}
        source_unchanged = source_override is not None or current == staged_hashes
    return {"passed": bool(all(item["passed"] for item in results) and source_unchanged),
            "cases": results, "staged_sha256": staged_hashes,
            "candidate_source_unchanged": source_unchanged, "image": IMAGE,
            "container_absent": True}
