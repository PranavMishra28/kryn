#!/usr/bin/env python3
"""Index one external trial without publishing its private prompt or trace."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "research/subsets/swebench-20261002.json"
DATABASE = ROOT / "research/history/external.jsonl"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def edited_tests(patch):
    paths = []
    seen = set()
    sections = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            sections.append([line])
        elif sections:
            sections[-1].append(line)
    for section in sections:
        pair = shlex.split(section[0][len("diff --git "):])
        if len(pair) != 2 or not pair[0].startswith("a/") or not pair[1].startswith("b/"):
            raise ValueError("Cannot audit patch paths")
        section_paths = []
        for prefixed in pair:
            raw = prefixed[2:]
            if not raw or "\\" in raw or any(part in {"", ".", ".."} for part in raw.split("/")):
                raise ValueError("Cannot audit patch paths")
            path = PurePosixPath(raw)
            if path.is_absolute():
                raise ValueError("Cannot audit patch paths")
            section_paths.append(path)
        header = section[1:next((i for i, line in enumerate(section)
                                  if line.startswith("@@ ")), len(section))]
        if any(line.startswith("new file mode ") or line == "--- /dev/null"
               for line in header):
            continue
        for path in section_paths:
            name = path.name.lower()
            is_test = ({"test", "tests", "testing"} & {part.lower() for part in path.parts} or
                       name.startswith("test_") or name in {"test.py", "tests.py"} or
                       name.endswith(("_test.py", "_tests.py", ".test.js", ".spec.js",
                                      ".test.ts", ".spec.ts")))
            if is_test and path not in seen:
                paths.append(str(path))
                seen.add(path)
    return paths


def receipt(evidence, official=None, prediction=None, official_patch=None,
            official_run_id=None):
    evidence = Path(evidence).resolve()
    driver_path = evidence / "driver.json"
    driver = json.loads(driver_path.read_text())
    task_id, arm = driver.get("task_id"), driver.get("arm")
    roster = json.loads(ROSTER.read_text())
    task = next((item for item in roster["tasks"] if item["instance_id"] == task_id), None)
    if not task or arm not in {"native", "kryn"}:
        raise ValueError("Trial is not an arm of the frozen external subset")
    if (driver.get("base_commit") != task["base_commit"] or
            driver.get("prompt_sha256") != task["prompt_sha256"] or
            driver.get("timeout_seconds") != roster["timeout_seconds"]):
        raise ValueError("Trial does not match the frozen task")
    model_patch = evidence / "model.patch"
    test_edits = edited_tests(model_patch.read_text()) if model_patch.is_file() else []
    if driver.get("patch_sha256") and driver["patch_sha256"] != sha(model_patch):
        raise ValueError("Driver patch hash does not match archived patch")
    results = None
    if official is not None:
        if not official_run_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", official_run_id):
            raise ValueError("Official grade needs its evaluator run ID")
        official = Path(official).resolve()
        if official.name != "results.json" or official.parent.name != official_run_id:
            raise ValueError("Official result is outside its declared evaluator run")
        results = json.loads(official.read_text())
        if results.get("submitted_ids") != [task_id]:
            raise ValueError("Official grade is for another task")
        if prediction is None or not model_patch.is_file():
            raise ValueError("Official grade needs its exact submitted patch")
        prediction = Path(prediction).resolve()
        submitted = json.loads(prediction.read_text())
        if (len(submitted) != 1 or submitted[0].get("instance_id") != task_id or
                submitted[0].get("model_patch") != model_patch.read_text()):
            raise ValueError("Submitted prediction differs from archived patch")
        if model_patch.stat().st_size:
            graded_patch = Path(official_patch).resolve() if official_patch else None
            if (graded_patch is None or graded_patch.name != "patch.diff" or
                    graded_patch.parent.name != task_id or
                    graded_patch.parent.parent.parent != official.parent or
                    sha(graded_patch) != sha(model_patch)):
                raise ValueError("Official evaluator patch differs from submitted patch")
            report_path = graded_patch.parent / "report.json"
            report = json.loads(report_path.read_text())
            if (report.get(task_id, {}).get("resolved") is not
                    (task_id in results.get("resolved_ids", []))):
                raise ValueError("Official per-task report differs from run result")
        elif task_id not in results.get("empty_patch_ids", []):
            raise ValueError("Empty patch does not match official result")
    elif prediction is not None or official_patch is not None or official_run_id is not None:
        raise ValueError("Prediction, official patch and run ID require official results")
    exports = list(evidence.glob("*.export.json"))
    if len(exports) > 1:
        raise ValueError("Ambiguous session exports")
    tokens = tool_calls = tool_errors = None
    if exports:
        session = json.loads(exports[0].read_text())["data"]
        tokens = session["info"].get("tokens")
        tools = [part for message in session["messages"]
                 for part in message.get("content", []) if part.get("type") == "tool"]
        tool_calls = len(tools)
        tool_errors = sum(part.get("state", {}).get("status") == "error" for part in tools)
    resources = driver.get("resources", {})
    clean_resources = (resources.get("telemetry_complete") is True and
                       resources.get("warning_or_critical_observed") is False and
                       resources.get("swap_peak_growth_bytes") == 0)
    accepted = bool(results and task_id in results.get("resolved_ids", []) and
                    driver.get("completed") is True and not driver.get("intervention") and
                    clean_resources and not test_edits)
    request_schemas = sorted({row["tool_schema_sha256"] for row in driver.get("requests", [])
                              if row.get("tool_schema_sha256")})
    error = driver.get("error")
    error_kind = error.split(":", 1)[0] if isinstance(error, str) else None
    if error_kind and not re.fullmatch(r"[A-Za-z_]\w*", error_kind):
        error_kind = "Error"
    return {
        "schema": 2, "split": "external-subset", "task_id": task_id,
        "dataset": task["dataset"], "arm": arm, "evidence_id": evidence.name,
        "source_commit": driver.get("source_commit"),
        "driver_sha256": sha(driver_path), "runner_sha256": driver.get("runner_sha256"),
        "roster_sha256": sha(ROSTER), "prompt_sha256": driver.get("prompt_sha256"),
        "base_commit": task["base_commit"], "image_digest": task["image_digest"],
        "model_repository": driver.get("model_repository"),
        "model_revision": driver.get("model_revision"),
        "model_profile_sha256": driver.get("model_profile_sha256"),
        "opencode_binary_sha256": driver.get("opencode_binary_sha256"),
        "evaluator_commit": roster["evaluator_commit"],
        "config_sha256": driver.get("config_sha256"),
        "tool_schema_sha256": request_schemas[0] if len(request_schemas) == 1 else None,
        "request_count": len(driver.get("requests", [])),
        "driver_completed": driver.get("completed"),
        "intervention": driver.get("intervention"),
        "error": error_kind,
        "official_results_sha256": sha(official) if official else None,
        "official_run_id": official_run_id,
        "prediction_sha256": sha(prediction) if prediction else None,
        "official_patch_sha256": sha(Path(official_patch).resolve()) if official_patch else None,
        "official_resolved": task_id in results.get("resolved_ids", []) if results else None,
        "official_empty_patch": task_id in results.get("empty_patch_ids", []) if results else None,
        "accepted": accepted, "wall_seconds": driver.get("wall_seconds"),
        "tokens": tokens, "tool_calls": tool_calls, "tool_errors": tool_errors,
        "resources": resources, "patch_sha256": sha(model_patch),
        "edited_test_paths": test_edits,
    }


def append(database, row):
    if row.get("error") is not None and not re.fullmatch(r"[A-Za-z_]\w*", row["error"]):
        raise ValueError("Public receipt error must contain only an exception name")
    for path in row.get("edited_test_paths", []):
        if not isinstance(path, str):
            raise ValueError("Public receipt contains an unsafe test path")
        parsed = PurePosixPath(path)
        if (parsed.is_absolute() or
                any(part == ".." for part in parsed.parts) or "\\" in path or
                any(ord(char) < 32 for char in path)):
            raise ValueError("Public receipt contains an unsafe test path")
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":"))
    if any(marker in encoded for marker in ("/Users/", "/private/tmp/", "/var/folders/")):
        raise ValueError("Public receipt contains a local absolute path")
    database.parent.mkdir(parents=True, exist_ok=True)
    with database.open("a+", encoding="utf-8") as out:
        fcntl.flock(out, fcntl.LOCK_EX)
        out.seek(0)
        for line in out:
            old = json.loads(line)
            if (old["task_id"], old["arm"], old["evidence_id"]) == (
                    row["task_id"], row["arm"], row["evidence_id"]):
                raise ValueError("External trial already recorded")
        out.write(encoded + "\n")
        out.flush()
        os.fsync(out.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--official-results", type=Path)
    parser.add_argument("--prediction", type=Path)
    parser.add_argument("--official-patch", type=Path)
    parser.add_argument("--official-run-id")
    parser.add_argument("--database", type=Path, default=DATABASE)
    args = parser.parse_args()
    row = receipt(args.evidence, args.official_results, args.prediction,
                  args.official_patch, args.official_run_id)
    append(args.database, row)
    print(json.dumps({"task_id": row["task_id"], "arm": row["arm"],
                      "accepted": row["accepted"], "evidence_id": row["evidence_id"]}))


if __name__ == "__main__":
    main()
