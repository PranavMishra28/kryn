"""Independent, fail-closed adjudication of one frozen container SWE pair.

This reads settled generation and official grader evidence. It never runs an
agent, a benchmark test, or a container; Docker is queried only for absence of
owned resources. A clean timeout and a no-change patch are scoreable failures.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import subprocess
import sys
from urllib.parse import unquote, urlparse

from research.container_admission import source_inputs
from research.campaign_supervisor import power_problem
from research.container_policy import parse_log, policy_during_tools
from research.local_only import (FORWARD_TARGET, MODEL, check_environment)
from tools.native_client import product_plugin_files


LABEL = "kryn.container-worker.owner"
EVALUATOR = Path("/private/tmp/kryn-swebench-venv/bin/python")
DATASETS = Path("/private/tmp/kryn-swebench-datasets")
OWNER = re.compile(r"kryn-worker-[0-9a-f]{16}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class InvalidEvidence(RuntimeError):
    """Evidence cannot support a score, including unsafe interruptions."""


def require(condition, reason):
    if not condition:
        raise InvalidEvidence(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def data(path, limit=8 * 1024**2):
    path = Path(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and 0 <= info.st_size <= limit, "nonregular_or_oversized_evidence")
    raw = path.read_bytes()
    require(len(raw) == info.st_size, "evidence_changed_during_read")
    return raw


def digest_file(path, limit=1024**3):
    info = Path(path).lstat()
    require(stat.S_ISREG(info.st_mode) and 0 <= info.st_size <= limit, "nonregular_or_oversized_pin")
    value = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            value.update(block)
    require(size == info.st_size, "pin_changed_during_read")
    return value.hexdigest()


def load(path):
    return json.loads(data(path))


def sealed(root, *, prompt=False):
    raw = data(root / "manifest.json")
    require(sha(raw) == data(root / "manifest.sha256", 1024).decode().strip(), "manifest_seal")
    manifest = json.loads(raw)
    if prompt:
        require(sha(data(root / "prompt.txt", 1024 * 1024)) == manifest.get("prompt_sha256"), "prompt_seal")
    return manifest, sha(raw)


def exact_pin(pin, expected_path, *, optional=False):
    if pin is None and optional:
        return None
    require(isinstance(pin, dict) and set(pin) == {"path", "sha256"}, "terminal_pin_shape")
    path = Path(pin["path"])
    require(path.is_absolute() and path == expected_path and HEX64.fullmatch(pin["sha256"]), "terminal_pin_path")
    require(digest_file(path, 16 * 1024**2) == pin["sha256"], "terminal_pin_drift")
    return path


def owned_absent(owner, query=None):
    require(isinstance(owner, str) and OWNER.fullmatch(owner), "invalid_owner_label")
    if query is None:
        def query(kind, label):
            command = ["docker", kind, "ls", *(["-a"] if kind == "container" else []),
                       "-q", "--filter", f"label={LABEL}={label}"]
            return subprocess.check_output(command, text=True, timeout=20).strip()
    for kind in ("container", "network"):
        require(not query(kind, owner), "owned_resource_remains")


def guard_samples(folder, summary, *, power_policy="ac-only"):
    require(power_policy in ("ac-only", "battery-capable"), "guard_power_policy")
    lines = data(folder / "resources.jsonl").splitlines()
    samples = [json.loads(line) for line in lines if line]
    require(len(samples) >= 2 and summary.get("sample_count") == len(samples), "guard_samples_missing")
    sources = ("AC Power", "Battery Power") if power_policy == "battery-capable" else ("AC Power",)
    require(all(sample.get("pressure_level") == 1 and sample.get("power_source") in sources
                and not sample.get("guard_reason")
                for sample in samples), "guard_pressure_or_power")
    if power_policy == "battery-capable":
        power = [json.loads(line) for line in data(folder / "power.jsonl").splitlines() if line]
        require(len(power) >= 2 and power[0].get("starting") is True
                and all(row.get("starting") is False for row in power[1:]), "guard_power_admission")
        require(power[-1].get("final") is True and all(row.get("final") is False for row in power[:-1]),
                "guard_power_final")
        require(all(type(row.get("unix")) in (int, float) and math.isfinite(row["unix"])
                    and row["unix"] > 0 for row in power)
                and all(before["unix"] <= after["unix"] for before, after in zip(power, power[1:])),
                "guard_power_clock")
        try:
            clocks = [datetime.fromisoformat(sample["utc"]) for sample in samples]
            require(all(clock.tzinfo is not None and clock.utcoffset() is not None for clock in clocks),
                    "guard_resource_clock")
            observed = [clock.timestamp() for clock in clocks]
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            raise InvalidEvidence("guard_resource_clock") from error
        require(all(math.isfinite(value) and value > 0 for value in observed)
                and power[0]["unix"] <= min(observed) + 2
                and power[-1]["unix"] >= max(observed) - 2, "guard_power_coverage")
        try:
            valid = all({"unix", "power_policy", "ac", "battery_percent", "adapter_watts", "starting", "reason"}
                        <= row.keys() and row.get("power_policy") == power_policy and row.get("reason") is None
                        and power_problem(row, row["starting"], power_policy) is None for row in power)
        except (RuntimeError, ValueError, TypeError, KeyError) as error:
            raise InvalidEvidence("guard_power_telemetry") from error
        require(valid, "guard_power_policy")
    swaps = [sample.get("swap_used_bytes") for sample in samples]
    require(all(type(value) is int for value in swaps) and max(swaps) <= swaps[0], "guard_swap_growth")
    require(summary.get("telemetry_complete") is True
            and summary.get("warning_or_critical_observed") is False
            and summary.get("swap_peak_growth_bytes") == 0, "guard_summary")


def policy_log(folder, root, *, require_tool):
    before, after = load(folder / "policy-before.json"), load(folder / "policy-after.json")
    require(all(before["session"]["data"].get(key) == after["session"]["data"].get(key)
                for key in ("agent", "model", "permissions")), "policy_snapshot_drift")
    events = parse_log(data(folder / "policy-log.sse").decode(), root)
    require(not policy_during_tools(events, through_end=True), "policy_mutated_after_tool")
    require(not require_tool or any(event["type"] == "session.tool.input.started" for event in events),
            "completed_without_tool_wire")


def test_edits(patch):
    """Identify changes to existing test paths; new checks are allowed."""
    sections = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            sections.append([line])
        elif sections:
            sections[-1].append(line)
    changed = []
    seen = set()
    for section in sections:
        pair = shlex.split(section[0][len("diff --git "):])
        require(len(pair) == 2 and pair[0].startswith("a/") and pair[1].startswith("b/"),
                "patch_path_syntax")
        section_paths = []
        for prefixed in pair:
            raw = prefixed[2:]
            require(raw and "\\" not in raw and
                    not any(part in {"", ".", ".."} for part in raw.split("/")), "patch_path_escape")
            path = PurePosixPath(raw)
            require(not path.is_absolute(), "patch_path_escape")
            section_paths.append(path)
        header = section[1:next((i for i, line in enumerate(section)
                                 if line.startswith("@@ ")), len(section))]
        if any(line.startswith("new file mode ") or line == "--- /dev/null" for line in header):
            continue
        for path in section_paths:
            parts = {part.lower() for part in path.parts}
            name = path.name.lower()
            is_test = ({"test", "tests", "testing"} & parts or name.startswith("test_")
                       or name in {"test.py", "tests.py"}
                       or name.endswith(("_test.py", "_tests.py", ".test.js", ".spec.js",
                                         ".test.ts", ".spec.ts")))
            if is_test and path not in seen:
                changed.append(str(path))
                seen.add(path)
    return changed


def exports(folder, driver, *, complete):
    paths = list(folder.glob("ses_*.export.json"))
    require(paths and len(paths) <= 64, "session_exports_missing")
    sessions = {}
    for path in paths:
        row = load(path)["data"]
        sid = row["info"]["id"]
        require(path.name == sid + ".export.json" and sid not in sessions, "session_export_identity")
        sessions[sid] = row
    root = driver["session_id"]
    require(root in sessions and set(sessions) == set(driver["settlement"]["verified_sessions"]),
            "session_settlement_ids")
    require(sessions[root]["info"].get("parentID") in (None, ""), "root_session_parent")
    for sid, row in sessions.items():
        info = row["info"]
        require(info.get("location", {}).get("directory") == "/testbed"
                and info.get("model", {}).get("providerID") == "local"
                and info.get("model", {}).get("id") == "qwen"
                and (sid == root or info.get("parentID") in sessions), "foreign_session")
        # Ancestor walking rejects cycles and disconnected children.
        chain, current = set(), sid
        while current != root:
            require(current not in chain and current in sessions, "session_parent_cycle")
            chain.add(current)
            current = sessions[current]["info"].get("parentID")
        generations = [message for message in row["messages"]
                       if message.get("type") in {"assistant", "compaction"}]
        assistants = [message for message in generations if message["type"] == "assistant"]
        if complete:
            last_end = max((message.get("time", {}).get("completed") or
                            message.get("time", {}).get("created", 0) for message in generations), default=0)
            require(assistants and assistants[-1].get("finish") == "stop"
                    and info.get("outcome") == "succeeded"
                    and info.get("time", {}).get("idle", 0) >= last_end
                    and any(message.get("type") == "idle" and message.get("outcome") == "succeeded"
                            and message.get("time", {}).get("created", 0) >= last_end
                            for message in row["messages"]), "session_not_terminal_success")
        for message in generations:
            model, clock = message.get("model", {}), message.get("time", {})
            require(model.get("providerID") == "local" and model.get("id") == "qwen", "assistant_model")
            if complete:
                require(type(clock.get("created")) in (int, float) and not message.get("error"),
                        "generation_clock_or_error")
                if message["type"] == "assistant":
                    require(message.get("finish") in {"stop", "tool-calls"}
                            and type(clock.get("completed")) in (int, float)
                            and clock["completed"] >= clock["created"]
                            and all(part.get("state", {}).get("status") in {"completed", "error"}
                                    for part in message.get("content", []) if part.get("type") == "tool"),
                            "assistant_incomplete")
                else:
                    require(message.get("status") == "completed"
                            and (clock.get("completed") is None or
                                 (type(clock["completed"]) in (int, float)
                                  and clock["completed"] >= clock["created"])),
                            "compaction_incomplete")
    require(driver["ownership"]["verified"] is True
            and {row["session_id"] for row in driver["ownership"]["sessions"]} == set(sessions)
            and all(row["owned"] is True for row in driver["ownership"]["sessions"]), "session_ownership")
    if complete:
        require(driver["generation"]["verified"] is True
                and {row["session_id"] for row in driver["generation"]["sessions"]} == set(sessions)
                and all(row["complete"] is True for row in driver["generation"]["sessions"]),
                "generation_completion")


def wire(driver, expected, *, complete):
    require(set(expected) == {"body_controls_sha256", "tool_schema_sha256s"}
            and HEX64.fullmatch(expected["body_controls_sha256"])
            and 1 <= len(expected["tool_schema_sha256s"]) <= 2
            and len(set(expected["tool_schema_sha256s"])) == len(expected["tool_schema_sha256s"])
            and all(HEX64.fullmatch(item) for item in expected["tool_schema_sha256s"]), "wire_manifest")
    require(driver.get("relay_rejections") == {"request_rejection": None, "wire_rejection": None},
            "relay_rejected_request")
    requests = driver.get("requests")
    require(isinstance(requests, list) and all(row.get("model") == MODEL for row in requests), "request_model")
    primary = [row for row in requests if row.get("tool_count", len(row.get("tools", []))) > 0]
    if complete:
        require(primary, "no_primary_wire")
    for row in primary:
        require(row.get("body_controls_sha256") == expected["body_controls_sha256"]
                and row.get("tool_schema_canonical_sha256", row.get("tool_schema_sha256"))
                in expected["tool_schema_sha256s"], "wire_mismatch")
    if primary:
        require(driver.get("wire", {}).get("matches_frozen") is True, "wire_summary")


def generation(campaign, arm, manifest, *, owner_query=None):
    folder = campaign / arm
    driver = load(folder / "driver.json")
    ownership = load(folder / "ownership.json")
    require(driver.get("kind") == "swe_container_generation" and driver.get("arm") == arm
            and driver.get("synthetic_inference") is False
            and driver.get("manifest_sha256") == digest_file(campaign / "manifest.json")
            and driver.get("task_id") == manifest["task"]["instance_id"]
            and driver.get("prompt_sha256") == manifest["prompt_sha256"], "generation_identity")
    require(driver.get("power_policy", "ac-only") == manifest.get("power_policy", "ac-only"),
            "generation_power_policy")
    require(driver.get("cleanup_settled") is True and driver.get("inference_relay_settled") is True
            and driver.get("worker_exported") is True and not driver.get("settlement_errors")
            and driver.get("retained_for_safe_export") == []
            and not any(driver.get(key) for key in ("error", "guard_reason", "export_error", "cli_error")),
            "generation_settlement")
    require(ownership.get("cleanup_errors") == [] and ownership.get("retained_containers") == []
            and ownership.get("retained_networks") == [] and ownership.get("containers")
            and ownership.get("networks"), "generation_ownership")
    owned_absent(ownership.get("owner"), owner_query)
    info = load(folder / "worker-inspect.json")
    host = info["HostConfig"]
    require(info["Id"] in ownership["containers"] and info["Image"] == manifest["image"]
            and info["Config"]["Labels"].get(LABEL) == ownership["owner"]
            and info["Config"]["User"] == "10001:10001"
            and info["Mounts"] == [] and host.get("Binds") in (None, [])
            and host["NetworkMode"] in ownership["networks"]
            and host["CapDrop"] == ["ALL"] and host["Privileged"] is False,
            "generation_container_isolation")
    require(driver.get("routes", {}).get("passed") is True
            and driver["routes"].get("positive_controls") is True
            and set(driver["routes"]["observed"]) ==
            {"dns_denied", "docker_socket_denied", "external_denied", "host_denied", "host_file_denied"}
            and all(driver["routes"]["observed"].values()), "generation_routes")
    guard_samples(folder, driver["resources"], power_policy=manifest.get("power_policy", "ac-only"))
    policy_log(folder, driver["session_id"], require_tool=driver.get("completed") is True)
    require(driver.get("policy_restored") is True and driver.get("policy_mutations") == [], "policy_receipt")
    for before_after in ("plugin_before", "plugin_after"):
        rows = [row for row in driver[before_after]["data"] if row.get("id") == "kryn.product"]
        require(not rows if arm == "native" else
                len(rows) == 1 and rows[0].get("state", {}).get("status") == "active",
                "plugin_arm")
    if arm == "kryn":
        protection = driver["plugin_protection"]
        require(protection["directory_owner"] != protection["agent_uid"]
                and all(protection[key] is False for key in ("parent_writable", "writable", "files_writable")),
                "plugin_writable")
    local = driver.get("local_only")
    require(isinstance(local, dict) and local.get("passed") is True
            and local.get("provider") == "local" and local.get("model_id") == MODEL
            and local.get("forward_target") == FORWARD_TARGET
            and local.get("configured_loopback_url") == "http://127.0.0.1:18765/v1"
            and local.get("context_tokens") == 98304
            and local.get("memory_ceiling_bytes") == 22 * 1024**3
            and type(local.get("owned_runtime_pid")) is int
            and local.get("runtime_same_after") is True
            and local.get("relay_source_sha256") == manifest["source_sha256"]["tools/learning.py"],
            "local_attestation")
    env = load(folder / "environment.json")
    require(check_environment(env, "/tmp/kryn", "http://127.0.0.1:18765/v1")
            == local["effective_config_sha256"], "local_config_drift")
    complete = driver.get("completed") is True
    timeout = (driver.get("completed") is False and driver.get("intervention") == "timeout"
               and driver.get("cli_exit_code") is None)
    require(complete or timeout, "generation_not_clean_completion_or_timeout")
    if complete:
        require(driver.get("intervention") is None and driver.get("cli_exit_code") == 0
                and local.get("generation_proven") is True
                and local.get("observed_local_model_only") is True, "false_generation_completion")
    wire(driver, manifest["wire_controls"], complete=complete)
    cli = load(folder / "cli-process.json")
    require((cli.get("returncode") == 0 if complete else type(cli.get("returncode")) is int
             and cli["returncode"] < 0), "cli_process_exit")
    stdout, stderr = Path(cli["stdout"]), Path(cli["stderr"])
    require(stdout.parent == stderr.parent == folder
            and data(stdout) == data(folder / "events.jsonl")
            and data(stderr) == data(folder / "stderr.log"), "cli_stream_receipt")
    for line in data(folder / "events.jsonl").splitlines():
        if line.strip():
            json.loads(line)
    require(driver.get("settlement", {}).get("idle") is True
            and driver["settlement"].get("runtime_idle") is True, "native_not_idle")
    exports(folder, driver, complete=complete)
    patch = data(folder / "model.patch", 16 * 1024**2)
    require(driver.get("patch_sha256") == sha(patch) and driver.get("patch_bytes") == len(patch)
            and driver.get("edited_test_paths") == test_edits(patch.decode()), "patch_or_test_integrity")
    require(not test_edits(patch.decode()), "existing_tests_changed")
    return {"driver": driver, "patch": patch, "timeout": timeout, "complete": complete,
            "owner": ownership["owner"]}


OFFICIAL_PARSER = r'''import json,sys
import pyarrow.parquet as pq
from swebench.harness.utils import make_test_spec
from swebench.harness.grading import get_logs_eval
p=json.loads(sys.argv[1])
rows=[row for row in pq.read_table(p['parquet']).to_pylist() if row['instance_id']==p['instance']]
assert len(rows)==1
spec=make_test_spec(rows[0])
parsed,found=get_logs_eval(spec,p['test_output'])
report=json.load(open(p['report']))[p['instance']]
expected={'FAIL_TO_PASS':spec.FAIL_TO_PASS,'PASS_TO_PASS':spec.PASS_TO_PASS}
good=bool(found) and report.get('patch_successfully_applied') is True and bool(expected['FAIL_TO_PASS'])
for group,tests in expected.items():
 state=report['tests_status'][group]
 good &= set(tests).issubset(parsed) and sorted(state['success']+state['failure'])==sorted(tests)
 good &= not (set(state['success']) & set(state['failure']))
print(json.dumps({'coverage':bool(good),'f2p':len(expected['FAIL_TO_PASS']),'p2p':len(expected['PASS_TO_PASS'])}))
'''


def official_coverage(parquet, instance, report, output):
    payload = {"parquet": str(parquet), "instance": instance,
               "report": str(report), "test_output": str(output)}
    process = subprocess.run([str(EVALUATOR), "-I", "-B", "-c", OFFICIAL_PARSER, json.dumps(payload)],
                             env={"PATH": "/usr/bin:/bin", "HF_HUB_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1"},
                             capture_output=True, text=True, timeout=90, check=True)
    evidence = json.loads(process.stdout)
    require(evidence.get("coverage") is True and evidence.get("f2p", 0) > 0, "official_test_coverage")
    return evidence


def installed_evaluator(expected_archive, expected_package):
    """Rehash the installed official package and its pinned source archive."""
    require(Path(sys.prefix).resolve() == EVALUATOR.parent.parent.resolve(), "evaluator_interpreter")
    require(importlib.metadata.version("swebench") == "5.0.2", "evaluator_version")
    distribution = importlib.metadata.distribution("swebench")
    direct = json.loads(distribution.read_text("direct_url.json"))
    url = urlparse(direct["url"])
    require(url.scheme == "file" and not url.netloc, "evaluator_archive_url")
    require(digest_file(Path(unquote(url.path))) == expected_archive, "evaluator_archive_drift")
    package = Path(distribution.locate_file("swebench"))
    require(package.is_dir() and not package.is_symlink(), "evaluator_package_missing")
    observed = {str(path.relative_to(package)): digest_file(path)
                for path in sorted(package.rglob("*"))
                if path.is_file() and "__pycache__" not in path.parts}
    require(observed == expected_package, "evaluator_package_drift")


def grade(campaign, arm, manifest, generation_result, state, *, owner_query=None,
          coverage=official_coverage):
    root = campaign / "grading" / arm
    start_path = campaign / "state" / f"{arm}.grader-start.json"
    finish_path = campaign / "state" / f"{arm}.grader-exit.json"
    start, finish = load(start_path), load(finish_path)
    require(start.get("arm") == arm and start.get("phase") == "grader"
            and start.get("manifest_sha256") == state["manifest_sha256"]
            and start.get("argv") == [str(EVALUATOR), "-B", "-m", "research.container_grader", str(root)]
            and type(start.get("started_unix")) in (int, float)
            and type(finish.get("finished_unix")) in (int, float)
            and state["_controller_finish"]["finished_unix"] <= start["started_unix"]
            <= finish["finished_unix"] <= state["terminal_unix"]
            and finish.get("returncode") == 0 and finish.get("reason") is None,
            "controller_grader_provenance")
    gm, gm_sha = sealed(root)
    require(gm.get("power_policy", "ac-only") == manifest.get("power_policy", "ac-only"),
            "grade_power_policy")
    driver, patch = generation_result["driver"], generation_result["patch"]
    require(gm.get("kind") == "swe_container_development_grade"
            and gm.get("patch_role") == "candidate" and gm.get("expected_resolved", "missing") is None
            and gm.get("synthetic_inference") is False
            and gm.get("task") == manifest["task"]
            and gm.get("source_sha256") == manifest["source_sha256"]
            and gm.get("official_image_id") == manifest["official_image_id"]
            and gm.get("generation_root") == str(campaign / arm)
            and gm.get("generation_manifest_sha256") == digest_file(campaign / "manifest.json"),
            "grade_manifest_link")
    pins = gm.get("generation_sha256")
    require(isinstance(pins, dict) and set(pins) == {"driver.json", "ownership.json", "model.patch"},
            "generation_grade_pin_set")
    for name, expected in pins.items():
        require(digest_file(campaign / arm / name) == expected, "generation_grade_pin")
    require(data(root / "model.patch", 16 * 1024**2) == patch
            and gm.get("patch_sha256") == sha(patch), "grader_patch_identity")
    lock = load(root / "execution-lock.json")
    require(lock.get("manifest_sha256") == gm_sha
            and lock.get("evaluator_package_sha256") == gm.get("evaluator_package_sha256")
            and lock.get("evaluator_archive_sha256") == gm.get("evaluator_archive_sha256")
            and lock.get("evaluator_commit") == gm.get("evaluator_commit"), "evaluator_lock")
    require(gm.get("evaluator_package_sha256") == manifest.get("evaluator_package_sha256")
            and gm.get("evaluator_archive_sha256") == manifest.get("evaluator_archive_sha256")
            and gm.get("evaluator_commit") == manifest.get("evaluator_commit"), "evaluator_campaign_pin")
    # The grader is frozen to the same source, exact wheel bytes and dataset.
    parquet = DATASETS / gm["task"]["dataset"] / "data/test-00000-of-00001.parquet"
    require(digest_file(parquet) == gm["datasets"][gm["task"]["dataset"]]["test_sha256"], "dataset_pin")
    wheels = Path(gm["wheelhouse"])
    require(not wheels.is_symlink() and {p.name for p in wheels.iterdir()} == set(gm["wheel_sha256"]),
            "wheel_inventory")
    for name, expected in gm["wheel_sha256"].items():
        require(Path(name).name == name and name.endswith(".whl")
                and digest_file(wheels / name, 8 * 1024**2) == expected, "wheel_pin")
    result = load(root / "grade/result.json")
    require(result.get("kind") == gm["kind"] and result.get("grade_valid") is True
            and result.get("power_policy", "ac-only") == manifest.get("power_policy", "ac-only")
            and result.get("passed") is True and result.get("cleanup_settled") is True
            and result.get("synthetic_inference") is False
            and result.get("generation_completed") is driver["completed"]
            and result.get("generation_intervention") == driver["intervention"]
            and result.get("model_generation") is driver["completed"]
            and type(result.get("resolved")) is bool
            and result.get("patch_sha256") == sha(patch)
            and result.get("oom_killed") is False
            and "strict_accepted" not in result, "grade_result_integrity")
    official = result.get("official", {})
    require(official.get("graded") is True and official.get("resolved") is result["resolved"]
            and official.get("infra_failure_instances") == 0
            and official.get("error_instances") == 0, "official_grade_validity")
    folder = root / "grade"
    require(not (folder / "output-budget.json").exists()
            and load(folder / "official-child.json") == {"completed": True, "test_evidence": True},
            "official_child_or_output_budget")
    guard_samples(folder, result["resources"], power_policy=manifest.get("power_policy", "ac-only"))
    ownership, control = load(folder / "ownership.json"), load(folder / "control.json")
    require(ownership.get("owner") == control.get("owner")
            and ownership.get("cleanup_errors") == []
            and len(ownership.get("containers", [])) == 1
            and ownership.get("networks") == [], "grader_ownership")
    owned_absent(ownership["owner"], owner_query)
    for name in ("container-inspect.json", "container-after.json"):
        info = load(folder / name)
        host = info["HostConfig"]
        require(info["Id"] == control["container"]
                and info["Image"] == gm["official_image_id"] == control["image_id"]
                and info["Config"]["Labels"].get(LABEL) == ownership["owner"]
                and info["Mounts"] == [] and host.get("Binds") in (None, [])
                and host["NetworkMode"] == "none" and host["CapDrop"] == ["ALL"]
                and host["Privileged"] is False and host["Memory"] == host["MemorySwap"] == 2 * 1024**3,
                "grader_container_isolation")
    run = folder / "logs/evaluation" / control["run_id"]
    result_path = run / "results.json"
    report = load(result_path)
    instance = gm["task"]["instance_id"]
    require(report.get("submitted_ids") == [instance]
            and (instance in report.get("resolved_ids", [])) is result["resolved"]
            and report.get("infra_failure_instances") == report.get("error_instances") == 0
            and digest_file(result_path) == official.get("result_sha256"), "official_results_raw")
    task = run / "kryn-container-development" / instance
    require(data(task / "patch.diff", 16 * 1024**2) == patch, "official_applied_patch")
    data(task / "test_output.txt")
    data(task / "report.json")
    coverage(parquet, instance, task / "report.json", task / "test_output.txt")
    return result


def terminal_state(campaign, arm):
    state = load(campaign / "state" / f"{arm}.json")
    require(state.get("status") == "terminal" and set(state) ==
            {"status", "reason", "manifest_sha256", "generation", "grade", "recovery",
             "terminal_unix", "controller"},
            "arm_not_terminal")
    manifest_sha = digest_file(campaign / "manifest.json")
    require(state["manifest_sha256"] == manifest_sha
            and type(state["terminal_unix"]) in (int, float), "terminal_manifest_or_time_drift")
    exact_pin(state.get("generation"), campaign / arm / "driver.json", optional=True)
    exact_pin(state.get("grade"), campaign / "grading" / arm / "grade/result.json", optional=True)
    recovery = state.get("recovery")
    if recovery is not None:
        require(isinstance(recovery, dict) and set(recovery) == {"path", "sha256"}, "recovery_pin_shape")
        path = Path(recovery["path"])
        require(path.is_absolute() and path.is_relative_to(campaign)
                and path != campaign / arm / "driver.json"
                and digest_file(path) == recovery["sha256"], "recovery_pin_drift")
    pins = state["controller"]
    require(isinstance(pins, dict) and set(pins) == {"start", "finish"}, "controller_pin_set")
    start_path = campaign / "state" / f"{arm}.generation-start.json"
    finish_path = campaign / "state" / f"{arm}.generation-exit.json"
    exact_pin(pins["start"], start_path)
    exact_pin(pins["finish"], finish_path)
    start, finish = load(start_path), load(finish_path)
    require(start.get("arm") == arm and start.get("phase") == "generation"
            and start.get("manifest_sha256") == manifest_sha
            and start.get("argv") == [str(EVALUATOR), "-B", "-m", "research.container_generation",
                                       str(campaign), arm]
            and type(start.get("started_unix")) in (int, float)
            and type(finish.get("finished_unix")) in (int, float)
            and start["started_unix"] <= finish["finished_unix"] <= state["terminal_unix"],
            "controller_generation_provenance")
    if state["recovery"] is None:
        require(finish.get("reason") is None and type(finish.get("returncode")) is int,
                "controller_generation_interrupted")
    state["_controller_start"] = start
    state["_controller_finish"] = finish
    return state


def classify_arm(campaign, arm, manifest, state, *, owner_query=None, coverage=official_coverage):
    if state.get("recovery") is not None:
        return {"category": "unscored", "accepted": None, "reason": "recovery"}
    if state.get("generation") is None:
        return {"category": "unscored", "accepted": None, "reason": "missing_generation_receipt"}
    try:
        result = generation(campaign, arm, manifest, owner_query=owner_query)
        require(state["_controller_finish"]["returncode"] == (0 if result["complete"] else 1),
                "controller_driver_exit_mismatch")
        patch = result["patch"]
        if not patch:
            require(state.get("grade") is None and state.get("reason") == "no_change", "no_change_state")
            require(not (campaign / "state" / f"{arm}.grader-start.json").exists()
                    and not (campaign / "state" / f"{arm}.grader-exit.json").exists(),
                    "no_change_grader_started")
            return {"category": "strict_failure", "accepted": False, "reason": "no_change"}
        require(state.get("grade") is not None and state.get("reason") is None,
                "missing_official_grade_or_terminal_intervention")
        official = grade(campaign, arm, manifest, result, state,
                         owner_query=owner_query, coverage=coverage)
        if result["timeout"]:
            return {"category": "strict_failure", "accepted": False, "reason": "clean_timeout",
                    "official_resolved": official["resolved"]}
        accepted = official["resolved"] is True
        return {"category": "accepted" if accepted else "strict_failure", "accepted": accepted,
                "reason": "official_resolved" if accepted else "official_unresolved",
                "official_resolved": official["resolved"]}
    except (InvalidEvidence, OSError, KeyError, IndexError, AttributeError, TypeError,
            ValueError, UnicodeError, subprocess.SubprocessError) as error:
        return {"category": "unscored", "accepted": None, "reason": "evidence_invalid",
                "error_type": type(error).__name__}


def campaign_manifest(campaign):
    manifest, manifest_sha = sealed(campaign, prompt=True)
    require(manifest.get("power_policy", "ac-only") in ("ac-only", "battery-capable"),
            "campaign_power_policy")
    require(manifest.get("kind") == "swe_container_development"
            and manifest.get("arm_order") in (["native", "kryn"], ["kryn", "native"])
            and manifest.get("wall_seconds") == 900 and manifest.get("request_seconds") == 360
            and "sequence" not in manifest and isinstance(manifest.get("task"), dict),
            "campaign_contract")
    require(source_inputs() == manifest.get("source_sha256"), "frozen_source_drift")
    plugin_hashes = {name: sha(value) for name, value in product_plugin_files(Path(__file__).resolve().parents[1]).items()}
    require(plugin_hashes == manifest.get("plugin_sha256"), "frozen_plugin_drift")
    require(digest_file(campaign / "adjudicate.py") == manifest.get("adjudicator_sha256")
            and digest_file(Path(__file__)) == manifest.get("adjudicator_sha256"), "frozen_adjudicator_drift")
    template_path = campaign / "grader-template.json"
    require(digest_file(template_path) == manifest.get("grader_template_sha256")
            and isinstance(manifest.get("official_image_id"), str)
            and manifest["official_image_id"].startswith("sha256:"), "frozen_grader_template_or_image")
    template = load(template_path)
    require(template.get("power_policy", "ac-only") == manifest.get("power_policy", "ac-only"),
            "generation_grader_power_policy")
    for key in ("task", "evaluator_archive_sha256", "evaluator_commit", "evaluator_package_sha256",
                "official_image_digest", "official_image_id", "wheelhouse", "wheel_sha256", "datasets"):
        require(template.get(key) == manifest.get(key), "generation_grader_protocol_drift")
    lock = load(campaign / "execution-lock.json")
    require(lock.get("manifest_sha256") == manifest_sha
            and lock.get("evaluator_archive_sha256") == manifest.get("evaluator_archive_sha256")
            and lock.get("evaluator_package_sha256") == manifest.get("evaluator_package_sha256")
            and lock.get("evaluator_commit") == manifest.get("evaluator_commit"), "generation_evaluator_lock")
    installed_evaluator(manifest["evaluator_archive_sha256"], manifest["evaluator_package_sha256"])
    for key in ("image", "base_commit", "git_config_sha256"):
        require(isinstance(manifest.get(key), str) and manifest[key], "campaign_pin_missing")
    require(set(manifest.get("admission_sha256", {})) ==
            {"generation", "grader", "output", "policy", "image"}, "admission_pin_set")
    for item in manifest["admission_sha256"].values():
        require(isinstance(item, dict) and digest_file(Path(item["path"])) == item["sha256"]
                and load(Path(item["path"])).get("passed") is True, "admission_drift")
    require(manifest["image_preparation_sha256"] == manifest["admission_sha256"]["image"]["sha256"]
            and load(manifest["admission_sha256"]["image"]["path"]).get("image") == manifest["image"]
            and load(manifest["admission_sha256"]["generation"]["path"]).get("source_sha256")
            == manifest["source_sha256"], "admission_scope")
    return manifest, manifest_sha


def adjudicate(campaign, *, owner_query=None, coverage=official_coverage):
    campaign = Path(campaign).resolve(strict=True)
    require(not (campaign / "adjudication.json").exists(), "adjudication_already_final")
    manifest, manifest_sha = campaign_manifest(campaign)
    order = manifest["arm_order"]
    # Incomplete controller state is not a final campaign and must remain resumable.
    states, arms = {}, {}
    for arm in order:
        require(load(campaign / "state" / f"{arm}.json").get("status") == "terminal",
                "arm_not_terminal")
        try:
            states[arm] = terminal_state(campaign, arm)
        except (InvalidEvidence, OSError, KeyError, IndexError, AttributeError,
                TypeError, ValueError, UnicodeError) as error:
            arms[arm] = {"category": "unscored", "accepted": None,
                         "reason": "terminal_evidence_invalid", "error_type": type(error).__name__}
    if len(states) == 2 and states[order[0]]["terminal_unix"] > states[order[1]]["_controller_start"]["started_unix"]:
        for arm in order:
            arms[arm] = {"category": "unscored", "accepted": None, "reason": "arm_order_invalid"}
    else:
        for arm, state in states.items():
            arms[arm] = classify_arm(campaign, arm, manifest, state,
                                     owner_query=owner_query, coverage=coverage)
    comparable = all(arms[arm]["category"] != "unscored" for arm in order)
    receipt = {"kind": "swe_container_development_adjudication", "schema": 1,
               "manifest_sha256": manifest_sha, "created_utc": datetime.now(timezone.utc).isoformat(),
               "arms": arms, "pair_comparable": comparable,
               "scope": "Single frozen development pair; no protected-study or general uplift claim."}
    path = campaign / "adjudication.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump(receipt, output, sort_keys=True, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    args = parser.parse_args()
    result = adjudicate(args.campaign)
    print(json.dumps({"pair_comparable": result["pair_comparable"], "arms": result["arms"]}))


if __name__ == "__main__":
    main()
