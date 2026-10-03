#!/usr/bin/env python3
"""Public zero-model Agent→detached patch→Docker grader handoff canary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from threading import Lock, Thread
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "research"))
import learning  # noqa: E402
from agent_grade_barrier import clean_clone, run_candidate_to_grader  # noqa: E402
from ui_gateway.synthetic_dispatch import FakeInference  # noqa: E402

PYTHON_IMAGE = "python@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0"
FIXED = "def answer():\n    return 42\n"
BROKEN = "def answer():\n    return 0\n"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(argv, *, env=None, cwd=None, timeout=20):
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True,
                            text=True, timeout=timeout, close_fds=True)
    if result.returncode:
        raise RuntimeError("Command failed: " + str(argv[:3]) + " " + result.stderr[-250:])
    return result.stdout


def fixture(output):
    seed = output / "seed"
    seed.mkdir(mode=0o700)
    checked(["git", "init", "--initial-branch=main", "-q", str(seed)])
    (seed / "answer.py").write_text(BROKEN)
    checked(["git", "-C", str(seed), "add", "answer.py"])
    env = os.environ.copy()
    env.update(GIT_AUTHOR_NAME="KRYN public canary", GIT_AUTHOR_EMAIL="canary@example.invalid",
               GIT_COMMITTER_NAME="KRYN public canary", GIT_COMMITTER_EMAIL="canary@example.invalid",
               GIT_AUTHOR_DATE="2026-10-03T00:00:00+0000",
               GIT_COMMITTER_DATE="2026-10-03T00:00:00+0000")
    checked(["git", "-C", str(seed), "commit", "-qm", "broken public fixture"], env=env)
    prompt = output / "prompt.txt"
    prompt.write_text("Change answer.py so answer() returns 42.\n")
    hidden = output / "hidden.txt"
    hidden.write_text("PUBLIC-HIDDEN-" + secrets.token_hex(12) + "\n")
    return seed, prompt, hidden


def trial(seed, prompt, hidden, tool_venv, grade_root, arm):
    sequence = [("write", {"path": "answer.py", "content": FIXED})]

    class CannedRelay:
        def __init__(self, *_args, **_kwargs):
            self.server = FakeInference(sequence, final_text="Canned edit complete.")
            self.port = self.server.server_address[1]
            self.records = self.server.calls
            self.connections = set()
            self.gate = Lock()

        def __enter__(self):
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            return self

        def cancel(self):
            pass

        def __exit__(self, *_args):
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=3)

    # The barrier accepts only a new direct /private/tmp receipt; use a sibling
    # rather than a child of the public fixture output directory.
    receipt = Path("/private/tmp") / ("kryn-docker-handoff-" + arm + "-" + secrets.token_hex(8))
    base = checked(["git", "-C", str(seed), "rev-parse", "HEAD"]).strip()

    def grade(apfs_workspace, _private, _evidence):
        patch_file = receipt / "agent-evidence" / "model.patch"
        if not patch_file.is_file() or patch_file.stat().st_size > 1024 * 1024:
            raise RuntimeError("Captured patch is missing or too large for the public canary")
        apfs_file = apfs_workspace / "answer.py"
        if (apfs_file.is_symlink() or not apfs_file.is_file() or
                apfs_file.stat().st_dev != apfs_workspace.stat().st_dev):
            raise RuntimeError("APFS grading file identity changed")
        with tempfile.TemporaryDirectory(prefix="kryn-docker-handoff-", dir=grade_root) as temporary:
            staged = Path(temporary) / "workspace"
            clean_clone(seed, staged, base)
            checked(["git", "-C", str(staged), "apply", "--check", str(patch_file)])
            checked(["git", "-C", str(staged), "apply", str(patch_file)])
            staged_file = staged / "answer.py"
            same = (not staged_file.is_symlink() and staged_file.is_file()
                    and staged_file.read_bytes() == apfs_file.read_bytes()
                    and staged_file.read_text() == FIXED)
            if not same:
                raise RuntimeError("Docker staging differs from the barrier's APFS grade")
            container = "kryn-handoff-" + secrets.token_hex(12)
            command = ["docker", "run", "--rm", "--name", container,
                       "--network", "none", "--read-only", "--cap-drop", "ALL",
                       "--security-opt", "no-new-privileges", "--pids-limit", "32",
                       "--memory", "256m", "--cpus", "1", "--user", "65534:65534",
                       "--mount", f"type=bind,src={staged},dst=/workspace,readonly",
                       PYTHON_IMAGE, "python", "-I", "-c",
                       "from pathlib import Path; s=Path('/workspace/answer.py').read_text(); "
                       "assert s=='def answer():\\n    return 42\\n'; print('PUBLIC PASS')"]
            try:
                docker = subprocess.run(command, capture_output=True, text=True,
                                        timeout=30, close_fds=True)
            except BaseException:
                subprocess.run(["docker", "rm", "-f", container], capture_output=True,
                               timeout=5, check=False)
                raise
            remaining = checked(["docker", "ps", "-a", "--filter", "name=" + container,
                                 "--format", "{{.Names}}"])
            return {"docker_exit": docker.returncode,
                    "docker_stdout": docker.stdout[:100],
                    "docker_stderr": docker.stderr[-300:],
                    "container_absent": not remaining.strip(),
                    "staged_equals_apfs": same,
                    "patch_sha256": sha(patch_file),
                    "staged_sha256": sha(staged_file),
                    "image": PYTHON_IMAGE}

    try:
        with patch.object(learning, "InferenceRelay", CannedRelay):
            result = run_candidate_to_grader(
                seed=seed, prompt=prompt, task_id="public-docker-handoff-" + arm,
                arm=arm, tool_venv=tool_venv, receipt=receipt,
                hidden_paths=[hidden], grade=grade, timeout=120)
    except BaseException as error:
        return {"arm": arm, "receipt": str(receipt), "passed": False,
                "error": type(error).__name__ + ": " + str(error)}
    agent = result["agent"]
    catalogs = [request["tools"] for request in agent["requests"]]
    graded = result["grader_result"]
    passed = bool(result["graded"] and agent["completed"] and
                  agent["inference_relay_settled"] and
                  result["candidate_detached"] and result["capture_detached"] and
                  result["grader_detached"] and graded["docker_exit"] == 0 and
                  graded["docker_stdout"] == "PUBLIC PASS\n" and
                  graded["container_absent"] and graded["staged_equals_apfs"] and
                  graded["patch_sha256"] == result["capture"]["patch_sha256"] and
                  len(catalogs) >= 2 and all(catalog == catalogs[0] for catalog in catalogs)
                  and "write" in catalogs[0] and
                  agent["resources"]["telemetry_complete"] and
                  not agent["resources"]["warning_or_critical_observed"] and
                  result["capture_guard"]["resources"]["telemetry_complete"] and
                  not result["capture_guard"]["cancelled"])
    return {"arm": arm, "receipt": str(receipt), "passed": passed,
            "catalogs": catalogs, "grader": graded,
            "candidate_detached": result["candidate_detached"],
            "capture_detached": result["capture_detached"],
            "grader_detached": result["grader_detached"],
            "wall_seconds": result["wall_seconds"],
            "swap_growth_bytes": agent["resources"]["swap_peak_growth_bytes"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tool-venv", required=True, type=Path)
    parser.add_argument("--grade-root", required=True, type=Path)
    args = parser.parse_args()
    output, grade_root = args.output.absolute(), args.grade_root.absolute()
    if (output.parent != Path("/private/tmp") or output.exists() or
            grade_root != grade_root.resolve() or not grade_root.is_dir() or
            grade_root.stat().st_uid != os.geteuid() or grade_root.stat().st_mode & 0o077):
        parser.error("Use a fresh /private/tmp output and an owned private Docker-shared root")
    output.mkdir(mode=0o700)
    image_id = checked(["docker", "image", "inspect", PYTHON_IMAGE,
                        "--format", "{{.Id}}"], timeout=10).strip()
    seed, prompt, hidden = fixture(output)
    runs = [trial(seed, prompt, hidden, args.tool_venv.absolute(), grade_root,
                  arm) for arm in ("native", "kryn")]
    equal = (all(run.get("passed") for run in runs) and
             runs[0]["catalogs"] == runs[1]["catalogs"] and
             runs[0]["grader"]["patch_sha256"] == runs[1]["grader"]["patch_sha256"])
    report = {"schema": 1, "kind": "public_zero_model_docker_grade_handoff",
              "source_commit": checked(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).strip(),
              "source_dirty": bool(checked(["git", "-C", str(ROOT), "status", "--porcelain"])),
              "script_sha256": sha(Path(__file__)), "seed_commit": checked(
                  ["git", "-C", str(seed), "rev-parse", "HEAD"]).strip(),
              "prompt_sha256": sha(prompt), "real_model_requests": 0,
              "protected_score": False, "image": PYTHON_IMAGE,
              "image_id": image_id, "tool_venv": str(args.tool_venv.absolute()),
              "paired_catalogs_equal": equal, "passed": equal, "runs": runs}
    report["passed"] = bool(report["passed"] and not report["source_dirty"])
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(output), "passed": report["passed"],
                      "arms": [{"arm": item["arm"], "passed": item["passed"]} for item in runs]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
