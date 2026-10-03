#!/usr/bin/env python3
"""One preregistered, protected-ineligible Python development pair."""

import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from agent_grade_barrier import run_candidate_to_grader
from check_holdout_boundary import background_boundary
from preflight_protected_python import grade as grade_task
from run_external_patch import NativeResourceGuard, summarize_resources


TASK = "ledger-categories"
ROSTER_SHA = "6820b7298b0815dab9a30830cbb8fd5631d784e2ec3cf70e05b1ecd32ec1e172"
MANIFEST_SHA = "554ee191ebe626d314bf7b3c87052479854a6231c89c8c97f6913e4b5642b5b9"
ORDER = ("native", "kryn")  # Even first byte of SHA-256("ledger-categories-dev-20261003").
TIMEOUT = 900


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def status():
    return json.loads(subprocess.check_output(
        ["curl", "--fail-with-body", "--silent", "--show-error", "--max-time", "3",
         "http://127.0.0.1:8000/api/status"], text=True))


def warmup(folder):
    """Load the same model before each arm under the unchanged host guard."""
    folder.mkdir(mode=0o700)
    before = status()
    if before.get("default_model") != "Qwen3.5-9B-6bit" or before.get("active_requests") != 0:
        raise RuntimeError("Unexpected or occupied local runtime before setup warmup")
    request = {"model": "Qwen3.5-9B-6bit", "messages": [
        {"role": "user", "content": "Reply OK."}], "max_tokens": 1}
    dump(folder / "request.json", request)
    samples = []
    monitor = NativeResourceGuard(folder, samples)
    monitor.start()
    child = None
    try:
        with (folder / "response.json").open("wb") as output, (folder / "stderr.log").open("wb") as error:
            child = subprocess.Popen([
                "curl", "--fail-with-body", "--silent", "--show-error", "--max-time", "120",
                "-H", "Content-Type: application/json", "--data-binary",
                "@" + str(folder / "request.json"),
                "http://127.0.0.1:8000/v1/chat/completions"],
                stdout=output, stderr=error, close_fds=True)
            deadline = time.monotonic() + 125
            while child.poll() is None and not monitor.cancel.is_set() and time.monotonic() < deadline:
                time.sleep(.25)
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait(timeout=2)
    finally:
        monitor.close()
    after = status()
    result = {"before_loaded": before.get("loaded_models"),
              "after_loaded": after.get("loaded_models"),
              "exit": child.returncode if child else None,
              "guard_reason": monitor.guard.reason,
              "guard_cancelled": monitor.cancel.is_set(),
              "resources": summarize_resources(samples),
              "response_sha256": sha(folder / "response.json") if (folder / "response.json").exists() else None}
    dump(folder / "warmup.json", result)
    if (result["exit"] != 0 or result["guard_reason"] or result["guard_cancelled"] or
            not result["resources"]["telemetry_complete"] or
            "Qwen3.5-9B-6bit" not in (result["after_loaded"] or []) or
            after.get("active_requests") != 0 or after.get("waiting_requests") != 0):
        raise RuntimeError("Guarded setup warmup did not leave a loaded, idle model")
    return result


def permissions_digest(items, workspace, private):
    normalized = []
    count = 0
    for item in items:
        copy = dict(item)
        resource = copy.get("resource")
        if isinstance(resource, str):
            if resource == workspace or resource.startswith(workspace + "/"):
                resource = "<WORKSPACE>" + resource[len(workspace):]
            elif resource.startswith(private + "/"):
                relative = resource[len(private) + 1:]
                root, slash, suffix = relative.partition("/")
                if slash and re.fullmatch(r"kryn-isolated-[a-z0-9_]+", root):
                    resource = "<SERVER_PRIVATE>/" + suffix
                    count += 1
            copy["resource"] = resource
        normalized.append(copy)
    if not count:
        return None
    return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()


def permissions(receipt, barrier):
    inventory_file = receipt / "agent-evidence" / "agent-inventory.json"
    if not inventory_file.is_file():
        return None
    inventory = json.loads(inventory_file.read_text())
    agents = [item for item in inventory["data"] if item.get("id") == "agent"]
    if len(agents) != 1:
        raise RuntimeError("Expected one user-facing Agent permission inventory")
    agent = barrier["agent"]
    return permissions_digest(agents[0]["permissions"], agent["workspace"],
                              agent["candidate_private_parent"])


def main():
    if len(sys.argv) not in (5, 6) or (len(sys.argv) == 6 and sys.argv[5] != "--reverse"):
        raise SystemExit("usage: run_ledger_development_pair.py DRAFT ROSTER TOOL_VENV NEW_RECEIPT_ROOT [--reverse]")
    draft, roster, tool_venv, root = (Path(p).absolute() for p in sys.argv[1:5])
    order = ORDER[::-1] if len(sys.argv) == 6 else ORDER
    repo = Path(__file__).resolve().parents[1]
    if (root.parent != Path("/private/tmp") or root.exists() or
            any(p != p.resolve() for p in (draft, roster, tool_venv, root)) or
            git("-C", str(repo), "status", "--porcelain") or
            sha(roster) != ROSTER_SHA or sha(draft / "manifest.json") != MANIFEST_SHA):
        raise SystemExit("Requires fresh receipt, clean source and frozen draft/roster")
    rows = [row for row in json.loads(roster.read_text())["tasks"] if row["id"] == TASK]
    if (len(rows) != 1 or rows[0].get("protected_eligible") is not False or
            rows[0].get("admission") != "RETIRED_FOR_DEVELOPMENT_DIAGNOSTIC" or
            rows[0].get("recorded_model_runs") != 0):
        raise SystemExit("The task was not retired before generation")
    entry = next(item for item in json.loads((draft / "manifest.json").read_text())
                 if item["id"] == TASK)
    seed, prompt = draft / "tasks" / TASK / "seed", draft / "tasks" / TASK / "prompt.md"
    oracle = draft / "private" / "oracles" / (TASK + ".py")
    reference = draft / "private" / "solutions" / (TASK + ".patch")
    partial = draft / "private" / "partials" / (TASK + ".patch")
    if (entry.get("protected_status") is not False or rows[0]["seed_commit"] != entry["base_sha"] or
            git("-C", str(seed), "rev-parse", "HEAD") != entry["base_sha"] or
            any(sha(path) != entry[key] for path, key in
                ((prompt, "prompt_sha256"), (oracle, "oracle_sha256"),
                 (reference, "reference_sha256"), (partial, "partial_sha256")))):
        raise SystemExit("Frozen task identity mismatch")
    root.mkdir(mode=0o700)
    source = git("-C", str(repo), "rev-parse", "HEAD")
    preflight = root.with_name(root.name + "-preflight")
    if preflight.exists() or any(root.with_name(root.name + "-" + arm).exists() for arm in ORDER):
        raise RuntimeError("Development pair receipts already exist")
    result = subprocess.run([sys.executable, "-B", str(repo / "research/preflight_protected_python.py"),
                             str(draft), TASK, str(preflight), "--tool-venv", str(tool_venv)],
                            capture_output=True, text=True)
    (root / "preflight.stdout").write_text(result.stdout)
    (root / "preflight.stderr").write_text(result.stderr)
    if result.returncode or not json.loads((preflight / "report.json").read_text()).get("passed"):
        raise RuntimeError("No-model real-path preflight failed; no generation sent")
    boundary = Path(inspect.getfile(background_boundary)).resolve()
    summary = {"kind": "ledger_categories_development_pair", "protected_score": False,
               "source_commit": source, "task_id": TASK, "roster_sha256": ROSTER_SHA,
               "manifest_sha256": MANIFEST_SHA, "preflight_sha256": sha(preflight / "report.json"),
               "order": order, "arms": {}, "matched": False, "accepted": {}}
    for arm in order:
        folder = root.with_name(root.name + "-" + arm)
        setup = warmup(root / (arm + "-warmup"))
        def grade(workspace, private, evidence):
            return {"oracle": grade_task(oracle, workspace, private, boundary, draft,
                                         evidence / "trusted-grader.log")}
        error = None
        try:
            run_candidate_to_grader(
                seed=seed, prompt=prompt, task_id=TASK, arm=arm, tool_venv=tool_venv,
                receipt=folder, hidden_paths=[oracle, reference, partial, draft / "manifest.json"],
                grade=grade, timeout=TIMEOUT, candidate_product_source=arm == "kryn")
        except BaseException as exc:
            error = type(exc).__name__ + ": " + str(exc)
        barrier = json.loads((folder / "barrier.json").read_text()) if (folder / "barrier.json").exists() else {}
        agent, oracle_result = barrier.get("agent", {}), barrier.get("grader_result", {}).get("oracle", {})
        accepted = bool(not error and barrier.get("graded") and agent.get("completed") and
                        agent.get("intervention") is None and agent.get("requests") and
                        all(barrier.get(key) for key in
                            ("candidate_detached", "capture_detached", "grader_detached")) and
                        barrier.get("capture_guard", {}).get("resources", {}).get("telemetry_complete") and
                        not barrier.get("capture_guard", {}).get("cancelled") and
                        oracle_result.get("exit") == 0 and not oracle_result.get("timed_out") and
                        oracle_result.get("output_bounded"))
        summary["arms"][arm] = {"error": error, "warmup": setup,
                                "receipt": str(folder),
                                "barrier_sha256": sha(folder / "barrier.json") if barrier else None,
                                "agent": agent, "oracle": oracle_result,
                                "permissions_sha256": permissions(folder, barrier) if agent.get("workspace") else None}
        summary["accepted"][arm] = accepted
        dump(root / "pair.json", summary)
        if agent.get("intervention") == "resource_guard" or "resource_guard" in (error or ""):
            summary["stop_reason"] = "resource_guard; no same-condition second arm"
            break
    if len(summary["arms"]) == 2:
        native, kryn = summary["arms"]["native"], summary["arms"]["kryn"]
        a, b = native["agent"], kryn["agent"]
        first = [item["requests"][0] if item["requests"] else {} for item in (a, b)]
        controls = {
            "source": a.get("source_commit") == b.get("source_commit") == source,
            "task": a.get("prompt_sha256") == b.get("prompt_sha256") == entry["prompt_sha256"] and a.get("base_commit") == b.get("base_commit") == entry["base_sha"],
            "model": all(a.get(key) == b.get(key) for key in
                         ("model_id", "model_repository", "model_revision", "model_profile_sha256", "opencode_binary_sha256")),
            "tool_environment": a.get("benchmark_tool_manifest") == b.get("benchmark_tool_manifest"),
            "timeout": a.get("timeout_seconds") == b.get("timeout_seconds") == TIMEOUT,
            "wire": all(first[0].get(key) == first[1].get(key) for key in
                        ("model", "max_tokens", "numeric", "thinking", "tool_count", "tool_schema_sha256")) and bool(first[0].get("tool_schema_sha256")),
            "permissions": native["permissions_sha256"] == kryn["permissions_sha256"] and bool(native["permissions_sha256"]),
            "warm": all("Qwen3.5-9B-6bit" in (arm["warmup"]["after_loaded"] or []) for arm in (native, kryn)),
            "power": all(arm["agent"].get("resources", {}).get("power_sources_observed") == ["AC Power"] for arm in (native, kryn)),
            "clean_guard": all(arm["agent"].get("resources", {}).get("telemetry_complete") and
                               not arm["agent"].get("intervention") for arm in (native, kryn)),
        }
        summary["controls"] = controls
        summary["matched"] = all(controls.values())
    dump(root / "pair.json", summary)
    print(json.dumps({"matched": summary["matched"], "accepted": summary["accepted"],
                      "receipt": str(root / "pair.json")}, sort_keys=True))
    return 0 if summary["matched"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
