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
from preflight_source_gateway import EXPECTED_SOURCE_BYTES, EXPECTED_SOURCE_SHA  # noqa: E402
from run_external_patch import configuration  # noqa: E402
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


def trial(seed, prompt, hidden, tool_venv, grade_root, arm, source_file=None):
    sequence = []
    if source_file is not None:
        sequence += [("shell", {"command": "cat " + str(source_file)}),
                     ("shell", {"command": "cat " + str(source_file.parent / "SOURCE.json")}),
                     ("shell", {"command": "printf tampered >> " + str(source_file)})]
    sequence += [("shell", {"command": "cat " + str(hidden)}),
                 ("write", {"path": "answer.py", "content": FIXED})]

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
                hidden_paths=[hidden] + ([source_file.parent / "SOURCE.json"]
                                         if source_file is not None else []),
                grade=grade, timeout=120, source_file=source_file)
    except BaseException as error:
        return {"arm": arm, "receipt": str(receipt), "passed": False,
                "error": type(error).__name__ + ": " + str(error)}
    agent = result["agent"]
    catalogs = [request["tools"] for request in agent["requests"]]
    graded = result["grader_result"]
    shell_calls = []
    for export in (receipt / "agent-evidence").glob("ses_*.export.json"):
        data = json.loads(export.read_text())["data"]
        shell_calls.extend(part for message in data["messages"]
                           for part in message.get("content", [])
                           if part.get("type") == "tool" and part.get("name") == "shell")
    hidden_call = shell_calls[-1] if shell_calls else {}
    shell_exit = hidden_call.get("state", {}).get("metadata", {}).get("exit")
    hidden_denied = (type(shell_exit) is int and shell_exit != 0 and
                     hidden.read_text().strip() not in json.dumps(hidden_call))
    source_checks = {}
    if source_file is not None:
        source_checks = {
            "source_read_exact": (len(shell_calls) == 4 and
                shell_calls[0].get("state", {}).get("metadata", {}).get("exit") == 0 and
                shell_calls[0].get("state", {}).get("content", [{}])[0].get("text", "").encode()
                == source_file.read_bytes()),
            "source_sibling_denied": (len(shell_calls) == 4 and
                shell_calls[1].get("state", {}).get("metadata", {}).get("exit") != 0 and
                source_file.parent.joinpath("SOURCE.json").read_text() not in
                json.dumps(shell_calls[1])),
            "source_write_denied": (len(shell_calls) == 4 and
                shell_calls[2].get("state", {}).get("metadata", {}).get("exit") != 0 and
                sha(source_file) == EXPECTED_SOURCE_SHA),
        }
    else:
        source_checks = {"source_not_requested": len(shell_calls) == 1}
    passed = bool(result["graded"] and agent["completed"] and
                  agent["inference_relay_settled"] and
                  hidden_denied and all(source_checks.values()) and
                  result["candidate_detached"] and result["capture_detached"] and
                  result["grader_detached"] and graded["docker_exit"] == 0 and
                  graded["docker_stdout"] == "PUBLIC PASS\n" and
                  graded["container_absent"] and graded["staged_equals_apfs"] and
                  graded["patch_sha256"] == result["capture"]["patch_sha256"] and
                  len(catalogs) >= 3 and all(catalog == catalogs[0] for catalog in catalogs)
                  and "write" in catalogs[0] and "shell" in catalogs[0] and
                  agent["resources"]["telemetry_complete"] and
                  not agent["resources"]["warning_or_critical_observed"] and
                  result["capture_guard"]["resources"]["telemetry_complete"] and
                  not result["capture_guard"]["cancelled"])
    return {"arm": arm, "receipt": str(receipt), "passed": passed,
            "catalogs": catalogs, "grader": graded,
            "source_checks": source_checks,
            "hidden_shell_read_denied": hidden_denied,
            "candidate_detached": result["candidate_detached"],
            "capture_detached": result["capture_detached"],
            "grader_detached": result["grader_detached"],
            "wall_seconds": result["wall_seconds"],
            "synthetic_request_count": len(agent["requests"]),
            "source_unchanged": agent.get("source_unchanged"),
            "resources": agent["resources"],
            "swap_growth_bytes": agent["resources"]["swap_peak_growth_bytes"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tool-venv", required=True, type=Path)
    parser.add_argument("--grade-root", required=True, type=Path)
    parser.add_argument("--source-dir", type=Path,
                        help="Owner-only pinned GitHub Docs snapshot; enables source canary")
    args = parser.parse_args()
    output, grade_root = args.output.absolute(), args.grade_root.absolute()
    if (output.parent != Path("/private/tmp") or output.exists() or
            grade_root != grade_root.resolve() or not grade_root.is_dir() or
            grade_root.stat().st_uid != os.geteuid() or grade_root.stat().st_mode & 0o077):
        parser.error("Use a fresh /private/tmp output and an owned private Docker-shared root")
    source_file = None
    if args.source_dir is not None:
        source_dir = args.source_dir.absolute()
        source_file = source_dir / "github-pagination.md"
        if (source_dir != source_dir.resolve() or
                not source_dir.is_dir() or source_dir.stat().st_uid != os.geteuid() or
                source_dir.stat().st_mode & 0o077 or not source_file.is_file() or
                source_file.stat().st_size != EXPECTED_SOURCE_BYTES or
                sha(source_file) != EXPECTED_SOURCE_SHA or
                not (source_dir / "SOURCE.json").is_file()):
            parser.error("Pinned owner-only GitHub Docs source identity changed")
    output.mkdir(mode=0o700)
    image_id = checked(["docker", "image", "inspect", PYTHON_IMAGE,
                        "--format", "{{.Id}}"], timeout=10).strip()
    seed, prompt, hidden = fixture(output)
    runs = [trial(seed, prompt, hidden, args.tool_venv.absolute(), grade_root,
                  arm, source_file) for arm in ("native", "kryn")]
    configs = [configuration(seed, seed / ".git" / arm, arm,
                             "http://127.0.0.1:19876/v1")[0] for arm in ("native", "kryn")]
    permission_equal = (configs[0]["permissions"] == configs[1]["permissions"] and
        {name: agent.get("permissions", []) for name, agent in configs[0].get("agents", {}).items()}
        == {name: agent.get("permissions", []) for name, agent in configs[1].get("agents", {}).items()})
    equal = (all(run.get("passed") for run in runs) and
             runs[0]["catalogs"] == runs[1]["catalogs"] and
             runs[0]["grader"]["patch_sha256"] == runs[1]["grader"]["patch_sha256"] and
             permission_equal)
    report = {"schema": 1, "kind": ("public_zero_model_source_docker_handoff"
                                    if source_file else "public_zero_model_docker_grade_handoff"),
              "source_commit": checked(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).strip(),
              "source_dirty": bool(checked(["git", "-C", str(ROOT), "status", "--porcelain"])),
              "script_sha256": sha(Path(__file__)), "seed_commit": checked(
                  ["git", "-C", str(seed), "rev-parse", "HEAD"]).strip(),
              "prompt_sha256": sha(prompt), "real_model_requests": 0,
              "protected_score": False, "image": PYTHON_IMAGE,
              "source_sha256": EXPECTED_SOURCE_SHA if source_file else None,
              "source_unchanged": sha(source_file) == EXPECTED_SOURCE_SHA if source_file else True,
              "image_id": image_id, "tool_venv": str(args.tool_venv.absolute()),
              "paired_catalogs_equal": (runs[0].get("catalogs") is not None and
                                        runs[0].get("catalogs") == runs[1].get("catalogs")),
              "paired_permissions_equal": permission_equal,
              "passed": equal, "runs": runs}
    report["passed"] = bool(report["passed"] and not report["source_dirty"])
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(output), "passed": report["passed"],
                      "arms": [{"arm": item["arm"], "passed": item["passed"]} for item in runs]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
