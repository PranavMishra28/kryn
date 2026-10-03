#!/usr/bin/env python3
"""Three-turn native OpenCode continuity canary with canned, non-model inference."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import socket
import subprocess
import sys
from threading import Thread
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "research"))
from native_client import BINARY, MODEL_ID, NativeServer  # noqa: E402
from context_probe import summarize_resources  # noqa: E402
from run_native_trial import NativeResourceGuard, plugin_absent, plugin_active, runtime_is_idle, settle_owned_sessions  # noqa: E402
from run_external_patch import configuration, drive  # noqa: E402
from agent_grade_barrier import create_volume, detach, image_entry  # noqa: E402
from ui_gateway.synthetic_dispatch import FakeInference  # noqa: E402

SUMMARY = """## Objective
- Complete the public staged lifecycle canary.

## Important Details
- Use the same native session and local model identity.

## Work State

### Completed
- A public turn completed.

### Active
- Continue the next public turn.

### Blocked
- (none)

## Next Move
1. Resume the next public turn.
2. (none)

## Relevant Files
- app.py: Public fixture file.
"""


def export(server, sid):
    data = server.request("GET", "/api/experimental/session/" + sid + "/export", timeout=5)["data"]
    if data.get("info", {}).get("id") != sid or not isinstance(data.get("messages"), list):
        raise RuntimeError("Native session export identity changed")
    return data


def check_session(server, sid, workspace):
    info = server.request("GET", "/api/session/" + sid, timeout=5)["data"]
    model = info.get("model", {})
    if (info.get("id") != sid or model.get("providerID") != "local" or
            model.get("id") != "qwen" or info.get("location", {}).get("directory") != str(workspace)):
        raise RuntimeError("Native session identity changed across restart")


def settle(server, sid, workspace, folder, guard):
    result = settle_owned_sessions(server, sid, workspace, folder, cancel=guard.cancel,
                                   model_id=MODEL_ID, guard_gib=22)
    if guard.cancel.is_set() or not result.get("idle"):
        raise RuntimeError("Owned native session or runtime did not settle")


def turn(server, sid, workspace, folder, prompt, guard):
    argv = server.background_prefix + [str(BINARY), "run", "--server", server.url,
        "--session", sid, "--agent", "agent", "--model", "local/qwen",
        "--format", "json", "--thinking"]
    child = subprocess.Popen(argv, cwd=workspace, env=server.env,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        cause, output, errors = drive(child, prompt.encode(), 45, guard.cancel.is_set)
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=2)
    (folder / "events.jsonl").write_bytes(output)
    (folder / "stderr.log").write_bytes(errors)
    if cause or child.returncode != 0:
        raise RuntimeError("Native turn failed: " + str(cause or child.returncode))
    settle(server, sid, workspace, folder, guard)
    return {"exit_code": child.returncode, "events_sha256": hashlib.sha256(output).hexdigest()}


def compact(server, sid, workspace, folder, guard):
    before = {m["id"] for m in export(server, sid)["messages"]
              if m.get("type") == "compaction" and m.get("status") == "completed"}
    response = server.request("POST", "/api/session/" + sid + "/compact", {}, timeout=10)
    if response is None or response.get("error"):
        raise RuntimeError("Native compaction request was not accepted")
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if guard.cancel.is_set():
            raise RuntimeError("Resource guard interrupted compaction")
        history = export(server, sid)
        fresh = [m for m in history["messages"] if m.get("type") == "compaction"
                 and m.get("id") not in before]
        if len(fresh) > 1 or any(m.get("status") in {"failed", "error"} for m in fresh):
            (folder / "compaction-export.json").write_text(json.dumps(history, indent=2) + "\n")
            raise RuntimeError("Native compaction produced unexpected records: " +
                               repr([(m.get("id"), m.get("status"), m.get("error")) for m in fresh]))
        if len(fresh) == 1 and fresh[0].get("status") == "completed":
            (folder / "compaction-export.json").write_text(json.dumps(history, indent=2) + "\n")
            settle(server, sid, workspace, folder, guard)
            return fresh[0]["id"]
        time.sleep(.2)
    (folder / "compaction-export.json").write_text(json.dumps(export(server, sid), indent=2) + "\n")
    raise TimeoutError("Native compaction did not complete")


def restart(server, guard):
    """Keep the owned private state, but replace the real OpenCode server process."""
    old = server.process
    if old is None or old.poll() is not None:
        raise RuntimeError("No live native server to restart")
    old_pid = old.pid
    old.terminate()
    try:
        code = old.wait(timeout=5)
    except subprocess.TimeoutExpired:
        old.kill()
        old.wait(timeout=2)
        raise RuntimeError("Native server did not stop gracefully")
    if code not in {0, 130}:
        raise RuntimeError("Native server stop was not clean: " + str(code))
    for _ in range(50):
        with socket.socket() as probe:
            probe.settimeout(.2)
            if probe.connect_ex(("127.0.0.1", server.port)) != 0:
                break
        time.sleep(.1)
    else:
        raise RuntimeError("Old native listener remains reachable")
    if guard.cancel.is_set():
        raise RuntimeError("Resource guard interrupted server restart")
    server.process = subprocess.Popen(server.background_prefix + [str(BINARY), "serve",
        "--hostname", "127.0.0.1", "--port", str(server.port)], cwd=server.directory,
        env=server.env, stdout=server.log_file, stderr=server.log_file)
    for _ in range(100):
        if guard.cancel.is_set() or server.process.poll() is not None:
            raise RuntimeError("Restarted native server stopped or hit resource guard")
        try:
            server.request("GET", "/api/info", timeout=1)
            return {"old_pid": old_pid, "new_pid": server.process.pid, "old_exit_code": code}
        except OSError:
            time.sleep(.2)
    raise TimeoutError("Restarted native server did not become ready")


def run_arm(root, arm):
    started = time.monotonic()
    folder = root / arm
    folder.mkdir(mode=0o700)
    volume = create_volume(folder, "candidate")
    result = {"arm": arm, "passed": False, "turns": [], "compactions": [],
              "restarts": [], "volume_detached": False, "real_model_requests": 0}
    fake = FakeInference([], final_text=SUMMARY)
    thread = Thread(target=fake.serve_forever, daemon=True)
    thread.start()
    guard = None
    samples = []
    try:
        workspace = volume.mount / "workspace"
        workspace.mkdir(mode=0o700)
        (workspace / "app.py").write_text("value = 1\n")
        for argv in (["git", "init", "-q", str(workspace)],
                     ["git", "-C", str(workspace), "add", "app.py"],
                     ["git", "-C", str(workspace), "-c", "user.name=Canary", "-c",
                      "user.email=canary@example.invalid", "commit", "-qm", "seed"]):
            subprocess.run(argv, check=True, capture_output=True, timeout=20)
        private = volume.mount / "private"
        private.mkdir(mode=0o700)
        state = workspace / ".git" / "staged-state"
        state.mkdir(mode=0o700)
        config, products, dependencies = configuration(workspace, state, arm,
            "http://127.0.0.1:" + str(fake.server_address[1]) + "/v1")
        result["config_sha256"] = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        guard = NativeResourceGuard(folder, samples)
        if not runtime_is_idle(folder, "runtime-before", model_id=MODEL_ID, guard_gib=22):
            raise RuntimeError("Owner model runtime is busy")
        guard.start()
        with NativeServer(workspace, config, folder / "native.log", background={
            "dependencies": dependencies, "inference_port": fake.server_address[1],
            "private_parent": private, "cancel": guard.cancel.is_set}) as server:
            for _ in range(75):
                inventory = server.request("GET", "/api/plugin", timeout=5)
                ready = (plugin_absent(inventory, "kryn.product") if arm == "native" else
                         plugin_active(inventory, "kryn.product", Path(products[0]["package"])))
                if ready:
                    break
                time.sleep(.2)
            else:
                raise RuntimeError("Requested OpenCode arm did not become active")
            session = server.request("POST", "/api/session", {"title": "public-staged-canary",
                "agent": "agent", "model": {"providerID": "local", "id": "qwen", "variant": "default"},
                "location": {"directory": str(workspace)}}, timeout=5)["data"]
            sid = session["id"]
            result["session_id"] = sid
            nonces = ["PUBLIC-STAGE-" + secrets.token_hex(8) for _ in range(3)]
            result["prompt_sha256"] = []
            for index, nonce in enumerate(nonces):
                stage = folder / ("stage" + str(index + 1))
                stage.mkdir(mode=0o700)
                prompt = "Public lifecycle turn " + str(index + 1) + ": " + nonce + ". Reply briefly.\n"
                result["prompt_sha256"].append(hashlib.sha256(prompt.encode()).hexdigest())
                check_session(server, sid, workspace)
                result["turns"].append(turn(server, sid, workspace, stage, prompt, guard))
                if index < 2:
                    result["compactions"].append(compact(server, sid, workspace, stage, guard))
                    result["restarts"].append(restart(server, guard))
                    check_session(server, sid, workspace)
            data = export(server, sid)
            (folder / "final-export.json").write_text(json.dumps(data, indent=2) + "\n")
            user_text = json.dumps([m for m in data["messages"] if m.get("type") == "user"], ensure_ascii=False)
            compactions = [m["id"] for m in data["messages"] if m.get("type") == "compaction"
                           and m.get("status") == "completed"]
            result["stored_user_nonces"] = [nonce in user_text for nonce in nonces]
            result["stored_compaction_ids"] = compactions
            result["raw_history_sha256"] = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
            result["passed"] = (all(result["stored_user_nonces"]) and compactions == result["compactions"]
                                and len(result["turns"]) == 3 and len(result["restarts"]) == 2)
        result["server_shutdown_proved"] = server.process.poll() is not None and not server.forced_shutdown
    except BaseException as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if guard is not None:
            try:
                guard.close()
                result["guard_reason"] = guard.guard.reason
                result["resources"] = summarize_resources(samples)
            except BaseException as error:
                result["guard_cleanup_error"] = type(error).__name__ + ": " + str(error)
        fake.shutdown()
        fake.server_close()
        thread.join(timeout=3)
        result["canned_inference_calls"] = len(fake.calls)
        result["all_requests_local_qwen"] = all(call.get("model") == MODEL_ID for call in fake.calls)
        result["wire_tool_schema_sha256"] = [call["tool_schema_sha256"] for call in fake.calls]
        result["first_wire_tool_catalog"] = fake.calls[0]["tools"] if fake.calls else []
        try:
            detach(volume)
            result["volume_detached"] = image_entry(volume.image) is None
        except BaseException as error:
            result["detach_error"] = type(error).__name__ + ": " + str(error)
        result["passed"] = bool(result["passed"] and result.get("server_shutdown_proved") and
                                result["volume_detached"] and result.get("guard_reason") is None and
                                "guard_cleanup_error" not in result and result["all_requests_local_qwen"] and
                                len(result["wire_tool_schema_sha256"]) >= 3)
        result["wall_seconds"] = round(time.monotonic() - started, 3)
        (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="fresh direct /private/tmp receipt directory")
    args = parser.parse_args()
    output = args.output.absolute()
    if output.parent != Path("/private/tmp") or output != output.resolve() or output.exists():
        parser.error("Choose a fresh direct /private/tmp receipt directory")
    output.mkdir(mode=0o700)
    rows = [run_arm(output, arm) for arm in ("native", "kryn")]
    report = {"schema": 1, "kind": "public_staged_continuity_no_model",
              "source_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
              "source_dirty": bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True)),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "real_model_requests": 0, "protected_eligible": False, "results": rows,
              "first_wire_tool_schema_equal": rows[0]["wire_tool_schema_sha256"][:1] ==
                                              rows[1]["wire_tool_schema_sha256"][:1],
              "passed": all(row["passed"] for row in rows) and
                        rows[0]["wire_tool_schema_sha256"][:1] ==
                        rows[1]["wire_tool_schema_sha256"][:1]}
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "source_dirty": report["source_dirty"],
                      "arms": [{"arm": row["arm"], "passed": row["passed"],
                                "error": row.get("error")} for row in rows]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
