#!/usr/bin/env python3
"""One guarded public three-turn coding screen with two compactions/restarts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from native_client import BINARY, MODEL_ID, NativeServer  # noqa: E402
import learning  # noqa: E402
from context_probe import summarize_resources  # noqa: E402
from run_native_trial import NativeResourceGuard, runtime_is_idle  # noqa: E402
from agent_grade_barrier import create_volume, detach, image_entry  # noqa: E402
from check_candidate_plugin_loading import shell  # noqa: E402
from run_external_patch import benchmark_tools, configuration  # noqa: E402
from staged_lifecycle_canned import (check_session, compact, export, restart,
                                     turn, wait_arm_ready)  # noqa: E402

FIXTURE = ROOT / "research/staged_public"
GIT = Path("/Library/Developer/CommandLineTools/usr/bin/git")
FILES = ("seed_tracker.py", "seed_test_tracker.py", "stage1.txt", "stage2.txt",
         "stage3.txt", "inject_legacy.py", "inject_test_legacy.py", "oracle.py",
         "reference_tracker.py", "reference_legacy.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=20, check=True).stdout.strip()


def test(workspace, name, python):
    result = subprocess.run([str(python), "-B", "-m", "unittest", "-q", name],
                            cwd=workspace, capture_output=True, text=True, timeout=20)
    return {"exit": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
            "stderr_tail": result.stderr[-600:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--tool-venv", type=Path,
                        default=Path("/private/tmp/kryn-python-tools-v2-20261003"))
    args = parser.parse_args()
    receipt = args.receipt.absolute()
    if receipt.parent != Path("/private/tmp") or receipt != receipt.resolve() or receipt.exists():
        parser.error("Use a fresh canonical direct /private/tmp receipt")
    if command("git", "-C", str(ROOT), "status", "--porcelain"):
        parser.error("Research source must be a clean commit")
    source_commit = command("git", "-C", str(ROOT), "rev-parse", "HEAD")
    fixture_hashes = {name: sha(FIXTURE / name) for name in FILES}
    tool_path, tool_dependencies, tool_manifest = benchmark_tools(args.tool_venv)
    receipt.mkdir(mode=0o700)
    report = {"schema": 1, "kind": "public_staged_real_model_development",
              "protected_status": False, "source_commit": source_commit,
              "runner_sha256": sha(Path(__file__)), "fixture_sha256": fixture_hashes,
              "opencode_binary_sha256": sha(BINARY), "model_id": MODEL_ID,
              "model_profile_sha256": sha(ROOT / "setup/accepted-profile.json"),
              "tool_manifest": tool_manifest, "guard_reason": None, "passed": False,
              "turns": [], "compactions": [], "restarts": [], "candidate_detached": False}
    started = time.monotonic()
    volume = None
    guard = None
    relay = None
    samples = []
    try:
        volume = create_volume(receipt, "candidate")
        workspace, private = volume.mount / "workspace", volume.mount / "private"
        workspace.mkdir(mode=0o700)
        private.mkdir(mode=0o700)
        shutil.copy2(FIXTURE / "seed_tracker.py", workspace / "tracker.py")
        shutil.copy2(FIXTURE / "seed_test_tracker.py", workspace / "test_tracker.py")
        command(str(GIT), "init", "-q", str(workspace))
        command(str(GIT), "-C", str(workspace), "add", "tracker.py", "test_tracker.py")
        command(str(GIT), "-C", str(workspace), "-c", "user.name=KRYN Research",
                "-c", "user.email=research@localhost", "commit", "-qm", "public staged seed")
        report["seed_commit"] = command(str(GIT), "-C", str(workspace), "rev-parse", "HEAD")
        state = workspace / ".git" / "staged-real-state"
        state.mkdir(mode=0o700)
        relay = learning.InferenceRelay(MODEL_ID, 8192, 360)
        with relay:
            config, products, dependencies = configuration(
                workspace, state, "kryn", f"http://127.0.0.1:{relay.port}/v1")
            dependencies += tool_dependencies
            report["config_sha256"] = hashlib.sha256(
                json.dumps(config, sort_keys=True).encode()).hexdigest()
            if not runtime_is_idle(receipt, "runtime-before", model_id=MODEL_ID, guard_gib=22):
                raise RuntimeError("Guarded model runtime was not idle before stage 1")
            guard = NativeResourceGuard(receipt, samples)
            guard.start()
            if guard.cancel.is_set():
                raise RuntimeError("Resource guard refused stage 1 startup")
            background = {"dependencies": dependencies, "inference_port": relay.port,
                          "private_parent": private, "cancel": guard.cancel.is_set,
                          "tool_path": str(tool_path)}
            with NativeServer(workspace, config, receipt / "native.log",
                              background=background) as server:
                server.env["GIT_CONFIG_NOSYSTEM"] = "1"
                wait_arm_ready(server, "kryn", products)
                denied = shell(server, workspace, "/bin/cat " + str(FIXTURE / "oracle.py"))
                report["oracle_read_denied"] = denied[0] != 0 and "staged_public_oracle_passed" not in denied[1]
                if not report["oracle_read_denied"]:
                    raise RuntimeError("Candidate can read trusted oracle")
                created = server.request("POST", "/api/session", {
                    "title": "public-staged-model-20261003", "agent": "agent",
                    "model": {"providerID": "local", "id": "qwen", "variant": "default"},
                    "location": {"directory": str(workspace)}}, timeout=5)["data"]
                sid = created["id"]
                report["session_id"] = sid
                prompts = [(FIXTURE / f"stage{i}.txt").read_text() for i in (1, 2, 3)]
                report["prompt_sha256"] = [hashlib.sha256(p.encode()).hexdigest() for p in prompts]
                for index, prompt in enumerate(prompts, 1):
                    stage = receipt / f"stage{index}"
                    stage.mkdir(mode=0o700)
                    check_session(server, sid, workspace)
                    report["turns"].append(turn(server, sid, workspace, stage, prompt, guard, timeout=360))
                    if index < 3:
                        report["compactions"].append(compact(
                            server, sid, workspace, stage, guard, timeout=180))
                        report["restarts"].append(restart(server, guard))
                        wait_arm_ready(server, "kryn", products)
                        check_session(server, sid, workspace)
                    if index == 2:
                        shutil.copy2(FIXTURE / "inject_legacy.py", workspace / "legacy.py")
                        shutil.copy2(FIXTURE / "inject_test_legacy.py", workspace / "test_legacy.py")
                        command(str(GIT), "-C", str(workspace), "add", "legacy.py", "test_legacy.py")
                        command(str(GIT), "-C", str(workspace), "-c", "user.name=KRYN Research",
                                "-c", "user.email=research@localhost", "commit", "-qm", "injected legacy check")
                        report["injection_commit"] = command(str(GIT), "-C", str(workspace), "rev-parse", "HEAD")
                        report["injected_before_stage3"] = test(
                            workspace, "test_legacy", args.tool_venv / "bin/python3")
                        if report["injected_before_stage3"]["exit"] == 0:
                            raise RuntimeError("Frozen injected test did not fail before stage 3")
                history = export(server, sid)
                (receipt / "final-export.json").write_text(json.dumps(history, indent=2) + "\n")
                stored = [m.get("text", "") for m in history["messages"] if m.get("type") == "user"]
                report["stored_prompts"] = [p.strip() in "\n".join(stored) for p in prompts]
                report["stored_compactions"] = [m["id"] for m in history["messages"]
                    if m.get("type") == "compaction" and m.get("status") == "completed"]
                report["tokens"] = history["info"].get("tokens")
                tools = [p for m in history["messages"] if m.get("type") == "assistant"
                         for p in m.get("content", []) if p.get("type") == "tool"]
                report["tool_calls"] = len(tools)
                report["tool_errors"] = sum(p.get("state", {}).get("status") == "error" for p in tools)
            report["server_shutdown_proved"] = server.process.poll() is not None and not server.forced_shutdown
            oracle = subprocess.run([sys.executable, "-B", str(FIXTURE / "oracle.py"), str(workspace)],
                                    capture_output=True, text=True, timeout=20)
            report["oracle_passed"] = oracle.returncode == 0 and "staged_public_oracle_passed" in oracle.stdout
            report["oracle_exit"] = oracle.returncode
            report["visible_tracker_test"] = test(workspace, "test_tracker", args.tool_venv / "bin/python3")
            report["visible_legacy_test"] = test(workspace, "test_legacy", args.tool_venv / "bin/python3")
            report["tracked_tests_preserved"] = (
                sha(workspace / "test_tracker.py") == fixture_hashes["seed_test_tracker.py"] and
                sha(workspace / "test_legacy.py") == fixture_hashes["inject_test_legacy.py"])
            report["model_requests"] = len(relay.records)
            report["wire_tool_schema_sha256"] = [r["tool_schema_sha256"] for r in relay.records]
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        if relay is not None:
            relay.cancel()
    finally:
        if guard is not None:
            try:
                guard.close()
                report["guard_reason"] = guard.guard.reason
                report["resources"] = summarize_resources(samples)
            except BaseException as error:
                report["guard_cleanup_error"] = type(error).__name__ + ": " + str(error)
        if volume is not None:
            try:
                detach(volume)
                report["candidate_detached"] = image_entry(volume.image) is None
            except BaseException as error:
                report["detach_error"] = type(error).__name__ + ": " + str(error)
        report["passed"] = bool(
            "error" not in report and len(report["turns"]) == 3 and
            len(report["compactions"]) == 2 and len(report["restarts"]) == 2 and
            "injected_before_stage3" in report and
            report["injected_before_stage3"]["exit"] != 0 and
            all(report.get("stored_prompts", [])) and
            report.get("stored_compactions") == report["compactions"] and
            report.get("oracle_passed") and report.get("tracked_tests_preserved") and
            report.get("visible_tracker_test", {}).get("exit") == 0 and
            report.get("visible_legacy_test", {}).get("exit") == 0 and
            report.get("oracle_read_denied") and report.get("server_shutdown_proved") and
            report["candidate_detached"] and report.get("guard_reason") is None and
            report.get("resources", {}).get("telemetry_complete"))
        report["wall_seconds"] = round(time.monotonic() - started, 3)
        (receipt / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report.get(key) for key in
                      ("passed", "error", "wall_seconds", "model_requests", "candidate_detached")},
                     sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
