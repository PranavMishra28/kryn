#!/usr/bin/env python3
"""No-model Agent→Browse→read-only-capture→fresh-grader canary for both arms.

This verifies the native wire and containment mechanics, never agent quality.
"""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
from threading import Lock, Thread
from unittest.mock import patch

RESEARCH = Path(__file__).resolve().parents[1]
ROOT = RESEARCH.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(RESEARCH))
import learning  # noqa: E402
from agent_grade_barrier import run_candidate_to_grader  # noqa: E402
from ui_gateway.synthetic_dispatch import FakeInference, URL  # noqa: E402


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def trial(seed, tool_venv, image, hidden, marker, arm):
    sequence = [
        ("write", {"path": "index.html", "content":
                   "<!doctype html><title>Public canary</title><p>" + marker + "</p>"}),
        ("subagent", {"agent": "browse", "description": "Inspect the public page",
                      "prompt": "Open " + URL + " and report the visible " + marker + " text."}),
        ("browser_browser_navigate", {"url": URL}),
        ("browser_browser_snapshot", {}),
    ]

    class CannedRelay:
        def __init__(self, *_args, **_kwargs):
            self.server = FakeInference(sequence)
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
            self.thread.join(timeout=2)

    receipt = Path("/private/tmp") / ("kryn-ui-barrier-" + secrets.token_hex(8))
    prompt = hidden.parent / "prompt.txt"

    def grade(workspace, _private, _evidence):
        page = (workspace / "index.html").read_text()
        return {"accepted": marker in page and "SYNTHETIC-HIDDEN-CANARY" not in page}

    try:
        with patch.object(learning, "InferenceRelay", CannedRelay):
            result = run_candidate_to_grader(
                seed=seed, prompt=prompt, task_id="canned-ui-" + arm, arm=arm,
                tool_venv=tool_venv, receipt=receipt, hidden_paths=[hidden],
                grade=grade, timeout=120, browser_image=image)
    except BaseException as error:
        return {"arm": arm, "receipt": str(receipt),
                "error": type(error).__name__ + ": " + str(error), "passed": False}

    agent = result["agent"]
    exported = []
    for path in sorted((receipt / "agent-evidence").glob("ses_*.export.json")):
        exported.append(json.loads(path.read_text())["data"])
    roots = [item for item in exported if item["info"].get("parentID") is None]
    children = [item for item in exported if item["info"].get("parentID") is not None]
    tools = [part for item in children for message in item["messages"]
             for part in message.get("content", []) if part.get("type") == "tool"]
    browser = [(part.get("name"), part.get("state", {}).get("status"),
                str(part.get("state", {}).get("content", []))) for part in tools]
    role_and_browser = (len(roots) == len(children) == 1 and
        children[0]["info"].get("parentID") == roots[0]["info"]["id"] and
        children[0]["info"].get("agent") == "browse" and
        [(name, status) for name, status, _ in browser] == [
            ("browser_browser_navigate", "completed"),
            ("browser_browser_snapshot", "completed")] and
        all(marker in text and "SYNTHETIC-HIDDEN-CANARY" not in text
            for _, _, text in browser))
    catalogs = [request["tools"] for request in agent["requests"]]
    expected_roles = (len(catalogs) == 6 and
        catalogs[0] == catalogs[1] == catalogs[5] and
        catalogs[2] == catalogs[3] == catalogs[4] and
        "subagent" in catalogs[0] and "browser_browser_navigate" not in catalogs[0] and
        "browser_browser_navigate" in catalogs[2] and "write" not in catalogs[2])
    passed = bool(result["graded"] and result["grader_result"]["accepted"] and
        result["candidate_detached"] and result["capture_detached"] and
        result["grader_detached"] and agent["completed"] and
        agent["browser_mcp_connected"] and agent["browser_settled"] and
        agent["inference_relay_settled"] and
        not agent["resources"]["warning_or_critical_observed"] and
        role_and_browser and expected_roles)
    return {"arm": arm, "receipt": str(receipt), "passed": passed,
            "graded": result["graded"], "fresh_grader_accepted": result["grader_result"]["accepted"],
            "candidate_detached": result["candidate_detached"],
            "capture_detached": result["capture_detached"],
            "grader_detached": result["grader_detached"],
            "broker_settled": agent["browser_settled"],
            "inference_relay_settled": agent["inference_relay_settled"],
            "role_and_browser_evidence": role_and_browser,
            "role_catalog_shape": expected_roles, "catalogs": catalogs,
            "swap_growth_bytes": agent["resources"]["swap_peak_growth_bytes"],
            "warning_or_critical": agent["resources"]["warning_or_critical_observed"],
            "wall_seconds": agent["wall_seconds"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--tool-venv", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    if output.parent != Path("/private/tmp") or output.exists():
        parser.error("Use a fresh direct /private/tmp output path")
    output.mkdir(mode=0o700)
    marker = "PUBLIC-CANARY-" + secrets.token_hex(6)
    hidden = output / "hidden.txt"
    hidden.write_text("SYNTHETIC-HIDDEN-CANARY\n")
    (output / "prompt.txt").write_text("Edit index.html and verify the public page with Browse.\n")
    results = [trial(args.seed.absolute(), args.tool_venv.absolute(), args.image,
                     hidden, marker, arm) for arm in ("native", "kryn")]
    equal = (all(result.get("passed") for result in results) and
             results[0]["catalogs"] == results[1]["catalogs"])
    report = {"kind": "zero_model_agent_browse_barrier_canary", "schema": 1,
              "source_commit": subprocess.check_output(
                  ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
              "source_dirty": bool(subprocess.check_output(
                  ["git", "-C", str(ROOT), "status", "--porcelain"], text=True)),
              "script_sha256": digest(__file__), "seed_head": subprocess.check_output(
                  ["git", "-C", str(args.seed), "rev-parse", "HEAD"], text=True).strip(),
              "image": args.image, "tool_venv": str(args.tool_venv.absolute()),
              "real_model_requests": 0, "protected_score": False,
              "paired_catalogs_equal": equal, "passed": equal, "results": results}
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(output), "passed": equal,
                      "arms": [{"arm": item["arm"], "passed": item["passed"]} for item in results]}))
    return 0 if equal else 1


if __name__ == "__main__":
    raise SystemExit(main())
