#!/usr/bin/env python3
"""Matched public three-stage local-model screen; never grades a protected task."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "research"))
from research import local_only  # noqa: E402
import learning  # noqa: E402
from native_client import BINARY, MODEL_ID, NativeServer  # noqa: E402
from context_probe import summarize_resources  # noqa: E402
from run_native_trial import (NativeResourceGuard, export_owned_sessions,
                              generation_completion, runtime_is_idle)  # noqa: E402
from run_external_patch import benchmark_tools, configuration  # noqa: E402
from run_boundary_public import grade  # noqa: E402
from staged_lifecycle_canned import (check_session, compact, create_volume, detach,
                                     export, image_entry, restart, turn, wait_arm_ready)  # noqa: E402
from public_staged_fixture import PROMPTS, REFERENCE, SEED, json_bytes, oracle  # noqa: E402
from staged_docker_grade import IMAGE, grade as docker_grade  # noqa: E402

SEED_TEXT = "kryn-public-staged-20261003-v1"
ORDER = ("kryn", "native")  # First byte of SHA-256(SEED_TEXT) is odd.
TOOL_VENV = Path("/private/tmp/kryn-python-tools-v2-20261003")
FIXTURE_SHA256 = "b7209bb5bac3ead98fa6b5f8d15e9346c803f520d6edc27af7e61125b1ad4630"
PROFILE_SHA256 = "05c4645f3b691ae09b239534c026a9da5fa929677e39cff3c0d867fe9e91fe52"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(*argv):
    return subprocess.check_output(argv, text=True, stderr=subprocess.STDOUT, timeout=20).strip()


def read_before_edit(path, stage):
    """Require successful source/rule reads before first mutating tool call."""
    reads = set()
    first_edit = None
    calls = []
    for line in path.read_text().splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = item.get("part", {})
        if part.get("type") != "tool":
            continue
        name = part.get("tool")
        state = part.get("state", {})
        arguments = state.get("input", {})
        if not isinstance(arguments, dict):
            continue
        status = state.get("status")
        calls.append({"tool": name, "status": status, "input": arguments})
        shell = str(arguments.get("command", "")) if name == "shell" else ""
        mutating = name in {"edit", "write", "patch"} or (name == "shell" and any(
            marker in shell for marker in
            ("apply_patch", "sed -i", "write_text(", "tee ", " > ", " >> ")))
        if mutating:
            first_edit = len(calls)
            break
        if name == "read" and status == "completed":
            target = str(arguments.get("path", ""))
            for filename in ("solve.py", "rules.json"):
                if target.endswith("/" + filename) or target == filename:
                    reads.add(filename)
        if (name == "shell" and status == "completed" and
                state.get("metadata", {}).get("metadata", {}).get("exit") == 0):
            if any(word in shell for word in ("cat ", "sed -n", "head ", "rg ")):
                for filename in ("solve.py", "rules.json"):
                    if filename in shell:
                        reads.add(filename)
    required = {"solve.py", "rules.json"} if stage == 1 else ({"rules.json"} if stage == 3 else {"solve.py"})
    return {"passed": bool(first_edit and required <= reads), "required": sorted(required),
            "read_before_first_edit": sorted(reads), "first_edit_tool_index": first_edit,
            "tool_calls_until_first_edit": calls}


def event_metrics(path):
    counters = {"tool_calls": 0, "tool_errors": 0, "model_steps": 0,
                "tokens": {"input": 0, "output": 0, "reasoning": 0,
                           "cache_read": 0, "cache_write": 0}}
    for line in path.read_text().splitlines():
        try:
            part = json.loads(line).get("part", {})
        except json.JSONDecodeError:
            continue
        if part.get("type") == "tool":
            counters["tool_calls"] += 1
            counters["tool_errors"] += part.get("state", {}).get("status") == "error"
        if part.get("type") == "step-finish":
            counters["model_steps"] += 1
            tokens = part.get("tokens", {})
            for key in ("input", "output", "reasoning"):
                counters["tokens"][key] += tokens.get(key, 0) or 0
            for key in ("read", "write"):
                counters["tokens"]["cache_" + key] += tokens.get("cache", {}).get(key, 0) or 0
    return counters


def prompts_retained(history, prompts):
    stored = [m.get("text") for m in history["messages"] if m.get("type") == "user"]
    return [stored.count(prompt) == 1 for prompt in prompts]


def functional_rejection(result):
    return (not result["passed"] and result["candidate_source_unchanged"] and
            any(not case["passed"] for case in result["cases"]) and
            all(case["exit"] == 0 and case["cause"] is None and case["valid_json"]
                for case in result["cases"]))


def effective_permission_hash(permissions, workspace, server_private):
    """Normalize only the two runtime-owned disposable paths."""
    normalized = []
    for item in permissions:
        copy = dict(item)
        resource = copy.get("resource")
        if isinstance(resource, str):
            for actual, marker in ((str(server_private), "<server_private>"),
                                   (str(workspace), "<workspace>")):
                if resource == actual or resource.startswith(actual + "/"):
                    resource = marker + resource[len(actual):]
                    break
            copy["resource"] = resource
        normalized.append(copy)
    return sha(json_bytes(normalized))


def seed_and_preflight(root):
    seed = root / "seed"
    seed.mkdir(mode=0o700)
    (seed / "solve.py").write_text(SEED)
    (seed / "rules.json").write_bytes(json_bytes({"separator": "-"}))
    grader = root / "grader"
    grader.mkdir(mode=0o700)
    (grader / "reference.py").write_text(REFERENCE)
    private = grader / "private"
    private.mkdir(mode=0o700)
    for stage in (1, 2, 3):
        (grader / f"stage{stage}.json").write_bytes(json_bytes(oracle(stage)))
    results = {"seed_fails_stage1": not grade(seed, private, grader / "stage1.json"),
               "reference": [], "stale_separator_fails_stage3": None}
    for stage in (1, 2):
        results["reference"].append(grade(seed, private, grader / f"stage{stage}.json",
                                          grader / "reference.py"))
    results["stale_separator_fails_stage3"] = not grade(
        seed, private, grader / "stage3.json", grader / "reference.py")
    (seed / "rules.json").write_bytes(json_bytes({"separator": "_"}))
    results["reference"].append(grade(seed, private, grader / "stage3.json",
                                      grader / "reference.py"))
    (seed / "rules.json").write_bytes(json_bytes({"separator": "-"}))
    if not (results["seed_fails_stage1"] and all(results["reference"]) and
            results["stale_separator_fails_stage3"]):
        raise RuntimeError("Frozen public seed/reference/stale-rule preflight failed: " + repr(results))
    command("git", "init", "-q", str(seed))
    command("git", "-C", str(seed), "add", "solve.py", "rules.json")
    command("git", "-C", str(seed), "-c", "user.name=PublicResearch", "-c",
            "user.email=public@example.invalid", "commit", "-qm", "seed")
    base = command("git", "-C", str(seed), "rev-parse", "HEAD")
    stage_root = root / "docker-preflight"
    docker = {"image_id": command("docker", "image", "inspect", IMAGE,
                                  "--format", "{{.Id}}"),
              "seed_fails_stage1": functional_rejection(docker_grade(
                  seed, seed, base, grader / "stage1.json", stage_root)),
              "reference": [], "stale_separator_fails_stage3": None}
    for stage in (1, 2):
        docker["reference"].append(docker_grade(
            seed, seed, base, grader / f"stage{stage}.json", stage_root,
            source_override=grader / "reference.py")["passed"])
    docker["stale_separator_fails_stage3"] = functional_rejection(docker_grade(
        seed, seed, base, grader / "stage3.json", stage_root,
        source_override=grader / "reference.py"))
    (seed / "rules.json").write_bytes(json_bytes({"separator": "_"}))
    docker["reference"].append(docker_grade(
        seed, seed, base, grader / "stage3.json", stage_root,
        source_override=grader / "reference.py")["passed"])
    (seed / "rules.json").write_bytes(json_bytes({"separator": "-"}))
    if not (docker["seed_fails_stage1"] and all(docker["reference"]) and
            docker["stale_separator_fails_stage3"]):
        raise RuntimeError("Frozen Docker-stage controls failed: " + repr(docker))
    return seed, grader, {"controls": results, "docker_controls": docker,
        "seed_commit": base, "reference_sha256": sha(REFERENCE.encode()),
        "oracle_sha256": [sha((grader / f"stage{n}.json").read_bytes()) for n in (1, 2, 3)]}


def arm(root, which, seed, grader, preflight, tools):
    started = time.monotonic()
    folder = root / which
    folder.mkdir(mode=0o700)
    result = {"arm": which, "passed": False, "stages": [], "compactions": [],
              "restarts": [], "volume_detached": False, "prompt_sha256": [sha(p.encode()) for p in PROMPTS],
              "seed_commit": preflight["seed_commit"]}
    volume = create_volume(folder, "candidate")
    guard = None
    relay = None
    samples = []
    try:
        workspace = volume.mount / "workspace"
        command("git", "clone", "--no-hardlinks", "-q", str(seed), str(workspace))
        command("git", "-C", str(workspace), "remote", "remove", "origin")
        if command("git", "-C", str(workspace), "rev-parse", "HEAD") != preflight["seed_commit"]:
            raise RuntimeError("Candidate clone differs from frozen seed")
        private = volume.mount / "private"
        private.mkdir(mode=0o700)
        state = workspace / ".git" / "research-staged-state"
        state.mkdir(mode=0o700)
        tool_path, tool_deps, tool_manifest = tools
        result["tool_manifest"] = tool_manifest
        with learning.InferenceRelay(MODEL_ID, 8192, 360) as relay:
            relay_url = f"http://127.0.0.1:{relay.port}/v1"
            config, products, dependencies = configuration(workspace, state, which,
                relay_url)
            result["local_config_sha256"] = local_only.check_config(config, relay_url)
            dependencies += tool_deps
            result["permissions_sha256"] = sha(json_bytes(config["permissions"]))
            result["config_sha256"] = sha(json_bytes(config))
            result["model_profile_sha256"] = sha((ROOT / "setup/accepted-profile.json").read_bytes())
            result["opencode_binary_sha256"] = sha(BINARY.read_bytes())
            guard = NativeResourceGuard(folder, samples)
            if not runtime_is_idle(folder, "runtime-before", model_id=MODEL_ID, guard_gib=22):
                raise RuntimeError("Pinned runtime was not idle before trial")
            guard.start()
            native_server = NativeServer(workspace, config, folder / "native.log", background={
                "dependencies": dependencies, "inference_port": relay.port,
                "private_parent": private, "tool_path": str(tool_path),
                "cancel": guard.cancel.is_set})
            native_server.env["GIT_CONFIG_NOSYSTEM"] = "1"
            with native_server as server:
                result["local_only"] = local_only.attest(
                    server.env, server.temporary.name, relay_url)
                wait_arm_ready(server, which, products)
                inventory = server.request("GET", "/api/agent", timeout=5)["data"]
                agent = next((item for item in inventory if item.get("id") == "agent"), None)
                if not agent or not isinstance(agent.get("permissions"), list):
                    raise RuntimeError("Effective Agent permissions are unavailable")
                result["effective_permissions_sha256"] = effective_permission_hash(
                    agent["permissions"], workspace, server.temporary.name)
                (folder / "agent-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
                sid = server.request("POST", "/api/session", {
                    "title": "public-staged-model", "agent": "agent",
                    "model": {"providerID": "local", "id": "qwen", "variant": "default"},
                    "location": {"directory": str(workspace)}}, timeout=5)["data"]["id"]
                result["session_id"] = sid
                for index, prompt in enumerate(PROMPTS, 1):
                    stage = folder / f"stage{index}"
                    stage.mkdir(mode=0o700)
                    check_session(server, sid, workspace)
                    start_ms = int(time.time() * 1000)
                    step = turn(server, sid, workspace, stage, prompt, guard, timeout=600)
                    exports, ownership = export_owned_sessions(
                        server, step["verified_sessions"], sid, workspace, stage)
                    generation = generation_completion(exports, start_ms, sid,
                                                       set(step["verified_sessions"]))
                    step["generation_verified"] = generation["verified"]
                    step["ownership_verified"] = ownership["verified"]
                    step["read_before_edit"] = read_before_edit(stage / "events.jsonl", index)
                    step["events"] = event_metrics(stage / "events.jsonl")
                    step["docker_grade"] = docker_grade(
                        workspace, seed, preflight["seed_commit"],
                        grader / f"stage{index}.json", folder / "docker-stages",
                        cancelled=guard.cancel.is_set)
                    step["independent_grade_passed"] = step["docker_grade"]["passed"]
                    step["rules_sha256"] = sha((workspace / "rules.json").read_bytes())
                    result["stages"].append(step)
                    (stage / "stage-result.json").write_text(json.dumps(step, indent=2) + "\n")
                    if index < 3:
                        result["compactions"].append(compact(
                            server, sid, workspace, stage, guard, timeout=240))
                        result["restarts"].append(restart(server, guard))
                        wait_arm_ready(server, which, products)
                        check_session(server, sid, workspace)
                        if index == 2:
                            result["rule_before_owner_edit_sha256"] = sha(
                                (workspace / "rules.json").read_bytes())
                            (workspace / "rules.json").write_bytes(json_bytes({"separator": "_"}))
                            result["rule_after_owner_edit_sha256"] = sha(
                                (workspace / "rules.json").read_bytes())
                final = export(server, sid)
                (folder / "final-export.json").write_text(json.dumps(final, indent=2) + "\n")
                result["stored_prompts"] = prompts_retained(final, PROMPTS)
                result["stored_compactions"] = [m["id"] for m in final["messages"]
                    if m.get("type") == "compaction" and m.get("status") == "completed"]
                result["server_pid_end"] = server.process.pid
            result["server_shutdown_proved"] = server.process.poll() is not None and not server.forced_shutdown
            result["requests"] = relay.records
            local_receipt = result["local_only"]
            local_receipt["runtime_same_after"] = local_only.same_runtime(local_receipt)
            local_receipt["observed_requests"] = len(relay.records)
            local_receipt["observed_local_model_only"] = bool(relay.records and all(
                item.get("model") == MODEL_ID for item in relay.records))
            local_receipt["generation_proven"] = bool(
                local_receipt["runtime_same_after"] and
                local_receipt["observed_local_model_only"])
            result["relay_settled"] = not relay.connections and not relay.gate.locked()
            result["wire_schema_stable"] = bool(relay.records and all(
                item["tool_schema_sha256"] == relay.records[0]["tool_schema_sha256"]
                for item in relay.records))
        result["passed"] = (len(result["stages"]) == 3 and
            all(s["generation_verified"] and s["ownership_verified"] and
                s["read_before_edit"]["passed"] and s["independent_grade_passed"]
                for s in result["stages"]) and
            len(result["compactions"]) == len(result["restarts"]) == 2 and
            result["stored_compactions"] == result["compactions"] and
            all(result["stored_prompts"]) and result["server_shutdown_proved"] and
            result["relay_settled"] and result["wire_schema_stable"] and
            result["local_only"]["generation_proven"] and
            result["rule_after_owner_edit_sha256"] ==
            sha(json_bytes({"separator": "_"})))
    except BaseException as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if relay is not None and "requests" not in result:
            result["requests"] = relay.records
        if guard is not None:
            try:
                guard.close()
                result["guard_reason"] = guard.guard.reason
                result["resources"] = summarize_resources(samples)
            except BaseException as error:
                result["guard_cleanup_error"] = type(error).__name__ + ": " + str(error)
        try:
            detach(volume)
            result["volume_detached"] = image_entry(volume.image) is None
        except BaseException as error:
            result["detach_error"] = type(error).__name__ + ": " + str(error)
        result["wall_seconds"] = round(time.monotonic() - started, 3)
        result["passed"] = bool(result["passed"] and result["volume_detached"] and
            result.get("guard_reason") is None and "guard_cleanup_error" not in result and
            result.get("resources", {}).get("telemetry_complete"))
        (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="fresh direct /private/tmp receipt directory")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    output = args.output.absolute()
    if output.parent != Path("/private/tmp") or output != output.resolve() or output.exists():
        parser.error("Choose a fresh direct /private/tmp receipt directory")
    if (sha((ROOT / "research/public_staged_fixture.py").read_bytes()) != FIXTURE_SHA256 or
            sha((ROOT / "setup/accepted-profile.json").read_bytes()) != PROFILE_SHA256):
        parser.error("Frozen public fixture or installed model profile changed")
    if not args.preflight_only and command("git", "-C", str(ROOT), "status", "--porcelain"):
        parser.error("Commit the frozen runner/fixture before any model request")
    output.mkdir(mode=0o700)
    seed, grader, preflight = seed_and_preflight(output)
    report = {"schema": 1, "kind": "public_staged_local_model_development",
              "source_commit": command("git", "-C", str(ROOT), "rev-parse", "HEAD"),
              "runner_sha256": sha(Path(__file__).read_bytes()),
              "fixture_sha256": sha((ROOT / "research/public_staged_fixture.py").read_bytes()),
              "order_seed_sha256": sha(SEED_TEXT.encode()), "arm_order": ORDER,
              "preflight": preflight, "protected_eligible": False, "results": []}
    if not args.preflight_only:
        tools = benchmark_tools(TOOL_VENV)
        for which in ORDER:
            report["results"].append(arm(output, which, seed, grader, preflight, tools))
        rows = report["results"]
        report["matched_first_wire_schema"] = (bool(rows[0].get("requests")) and
            bool(rows[1].get("requests")) and
            rows[0]["requests"][0]["tool_schema_sha256"] ==
            rows[1]["requests"][0]["tool_schema_sha256"])
        report["matched_permissions"] = (rows[0].get("permissions_sha256") ==
                                          rows[1].get("permissions_sha256"))
        report["matched_effective_permissions"] = (
            rows[0].get("effective_permissions_sha256") is not None and
            rows[0].get("effective_permissions_sha256") ==
            rows[1].get("effective_permissions_sha256"))
        report["passed"] = (all(row["passed"] for row in rows) and
                            report["matched_first_wire_schema"] and
                            report["matched_permissions"] and
                            report["matched_effective_permissions"])
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"preflight": preflight["controls"], "source_commit": report["source_commit"],
                      "results": [{"arm": row["arm"], "passed": row["passed"],
                                   "error": row.get("error")} for row in report["results"]],
                      "passed": report.get("passed")}))
    return 0 if args.preflight_only or report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
