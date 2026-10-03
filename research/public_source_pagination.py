#!/usr/bin/env python3
"""Public GitHub Docs coding calibration; never a protected holdout score."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile

from agent_grade_barrier import clean_clone, run_candidate_to_grader
from run_external_patch import configuration

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "418bdf281d74a89c7dabedc4af53a6f7b286f2416e7670d9cc71453db08d8640"
PROVENANCE_SHA = "bb4eecab83669283cddb071eedcbba496cabe60b4644171967237e6b91ac9f2a"
PYTHON_IMAGE = "python@sha256:399babc8b49529dabfd9c922f2b5eea81d611e4512e3ed250d75bd2e7683f4b0"
SEED = """def collect_pages(fetch, first_url):
    response = fetch(first_url)
    data = response.get('data')
    return data if isinstance(data, list) else []
"""
REFERENCE = """import re

_META = {'total_count', 'incomplete_results', 'repository_selection'}


def collect_pages(fetch, first_url):
    items = []
    visited = set()
    url = first_url
    while url and url not in visited:
        visited.add(url)
        response = fetch(url)
        data = response.get('data')
        if isinstance(data, list):
            items.extend(data)
        elif isinstance(data, dict):
            for key, value in data.items():
                if key not in _META and isinstance(value, list):
                    items.extend(value)
                    break
        headers = response.get('headers') or {}
        links = next((value for key, value in headers.items()
                      if key.lower() == 'link'), '')
        url = None
        for match in re.finditer(r'<([^<>]+)>\\s*;\\s*rel=\"([^\"]+)\"', links, re.I):
            if match.group(2).lower() == 'next':
                url = match.group(1)
                break
    return items
"""
PARTIAL = """def collect_pages(fetch, first_url):
    response = fetch(first_url)
    data = response.get('data')
    if not isinstance(data, list):
        return []
    return list(data)
"""
WORKER = """import json, sys
sys.path.insert(0, '/workspace')
from pager import collect_pages
cases = json.load(sys.stdin)
out = []
for case in cases:
    calls = []
    def fetch(url):
        calls.append(url)
        if len(calls) > 12:
            raise RuntimeError('unbounded pagination')
        return case['responses'][url]
    try:
        items = collect_pages(fetch, case['start'])
        out.append({'id': case['id'], 'items': items, 'calls': calls})
    except Exception as error:
        out.append({'id': case['id'], 'error': type(error).__name__, 'calls': calls})
print(json.dumps(out, separators=(',', ':')))
"""


def cases():
    return [
        {"id": "single", "start": "/single", "responses": {
            "/single": {"data": [1, 2], "headers": {}}},
         "expected": {"items": [1, 2], "calls": ["/single"]}},
        {"id": "mixed-opaque", "start": "/items?per_page=2", "responses": {
            "/items?per_page=2": {"data": ["a", "b"], "headers": {
                "link": '<https://api.github.com/items?after=opaque-A&per_page=2>; rel="next", <https://api.github.com/items?page=9>; rel="last"'}},
            "https://api.github.com/items?after=opaque-A&per_page=2": {"data": ["c"], "headers": {
                "link": '<https://api.github.com/items?page=1>; rel="first", <https://api.github.com/items?after=opaque-B>; rel="next"'}},
            "https://api.github.com/items?after=opaque-B": {"data": ["d"], "headers": {
                "link": '<https://api.github.com/items?page=1>; rel="first"'}}},
         "expected": {"items": ["a", "b", "c", "d"], "calls": [
             "/items?per_page=2", "https://api.github.com/items?after=opaque-A&per_page=2",
             "https://api.github.com/items?after=opaque-B"]}},
        {"id": "object-wrapper", "start": "/search", "responses": {
            "/search": {"data": {"total_count": 3, "incomplete_results": False,
                                   "items": [{"id": 1}, {"id": 2}]}, "headers": {
                "Link": '<https://api.github.com/search?page=2>; rel="next"'}},
            "https://api.github.com/search?page=2": {"data": {
                "total_count": 3, "items": [{"id": 3}]}, "headers": {}}},
         "expected": {"items": [{"id": 1}, {"id": 2}, {"id": 3}],
                      "calls": ["/search", "https://api.github.com/search?page=2"]}},
        {"id": "no-content", "start": "/empty", "responses": {
            "/empty": {"data": None, "headers": {"link": '<u2>; rel="next"'}},
            "u2": {"data": [7], "headers": {}}},
         "expected": {"items": [7], "calls": ["/empty", "u2"]}},
        {"id": "link-order", "start": "/page2", "responses": {
            "/page2": {"data": [2], "headers": {"LiNk":
                '<p1>; rel="prev", <p3>; rel="next", <p8>; rel="last"'}},
            "p3": {"data": [3], "headers": {"link": '<p2>; rel="prev"'}}},
         "expected": {"items": [2, 3], "calls": ["/page2", "p3"]}},
        {"id": "repeat-url", "start": "/loop", "responses": {
            "/loop": {"data": ["once"], "headers": {"link": '<' + "/loop" + '>; rel="next"'}}},
         "expected": {"items": ["once"], "calls": ["/loop"]}},
    ]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(argv, *, cwd=None, env=None, timeout=20):
    process = subprocess.run(argv, cwd=cwd, env=env, capture_output=True,
                             text=True, timeout=timeout, close_fds=True)
    if process.returncode:
        raise RuntimeError("Command failed: " + str(argv[:3]) + " " + process.stderr[-200:])
    return process.stdout.strip()


def make_patch(before, after, path):
    text = "".join(difflib.unified_diff(before.splitlines(keepends=True),
                after.splitlines(keepends=True), fromfile="a/pager.py", tofile="b/pager.py"))
    path.write_text(text)


def validate_source(source_dir):
    source_dir = Path(source_dir).absolute()
    source = source_dir / "github-pagination.md"
    provenance = source_dir / "SOURCE.json"
    if (source_dir != source_dir.resolve() or not source_dir.is_dir() or
            source_dir.stat().st_uid != os.geteuid() or source_dir.stat().st_mode & 0o077 or
            not source.is_file() or source.stat().st_size != 10088 or
            sha(source) != SOURCE_SHA or not provenance.is_file() or
            sha(provenance) != PROVENANCE_SHA):
        raise ValueError("Frozen official source or provenance changed")
    return source, provenance


def docker_grade(workspace):
    public_cases = [{k: value for k, value in case.items() if k != "expected"}
                    for case in cases()]
    expected = [{"id": case["id"], **case["expected"]} for case in cases()]
    container = "kryn-public-pagination-" + secrets.token_hex(10)
    argv = ["docker", "run", "-i", "--rm", "--name", container, "--network", "none",
            "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "32", "--memory", "256m", "--cpus", "1",
            "--user", "65534:65534", "--mount",
            f"type=bind,src={workspace},dst=/workspace,readonly", PYTHON_IMAGE,
            "python", "-B", "-I", "-c", WORKER]
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                 start_new_session=True, close_fds=True)
        timed_out = False
        try:
            child.communicate(input=json.dumps(public_cases).encode(), timeout=45)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        finally:
            subprocess.run(["docker", "rm", "-f", container], capture_output=True,
                           timeout=5, check=False)
        stdout.seek(0); stderr.seek(0)
        out, err = stdout.read(65537), stderr.read(65537)
    remaining = checked(["docker", "ps", "-a", "--filter", "name=" + container,
                         "--format", "{{.Names}}"])
    bounded = len(out) <= 65536 and len(err) <= 65536
    try:
        observed = json.loads(out) if child.returncode == 0 and bounded else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        observed = None
    checks = {case["id"]: observed[index] == item if isinstance(observed, list)
              and len(observed) == len(expected) else False
              for index, (case, item) in enumerate(zip(cases(), expected))}
    return {"accepted": bool(not timed_out and not remaining and bounded and
                              child.returncode == 0 and all(checks.values())),
            "cases": checks, "docker_exit": child.returncode,
            "timed_out": timed_out, "output_bounded": bounded,
            "container_absent": not remaining,
            "stdout_sha256": hashlib.sha256(out).hexdigest(),
            "stderr_sha256": hashlib.sha256(err).hexdigest()}


def grade_clone(seed, base, patch, grade_root):
    with tempfile.TemporaryDirectory(prefix="kryn-pagination-grade-", dir=grade_root) as temporary:
        staged = Path(temporary) / "workspace"
        clean_clone(seed, staged, base)
        if patch is not None:
            checked(["git", "-C", str(staged), "apply", "--check", str(patch)])
            checked(["git", "-C", str(staged), "apply", str(patch)])
        return docker_grade(staged)


def fixture(output, source):
    seed = output / "seed"
    seed.mkdir(mode=0o700)
    checked(["git", "init", "--initial-branch=main", "-q", str(seed)])
    (seed / "pager.py").write_text(SEED)
    checked(["git", "-C", str(seed), "add", "pager.py"])
    env = os.environ.copy()
    env.update(GIT_AUTHOR_NAME="KRYN public pagination", GIT_AUTHOR_EMAIL="task@example.invalid",
               GIT_COMMITTER_NAME="KRYN public pagination", GIT_COMMITTER_EMAIL="task@example.invalid",
               GIT_AUTHOR_DATE="2026-10-03T00:00:00+0000",
               GIT_COMMITTER_DATE="2026-10-03T00:00:00+0000")
    checked(["git", "-C", str(seed), "commit", "-qm", "broken public pagination seed"], env=env)
    prompt = output / "prompt.txt"
    prompt.write_text(
        "Implement collect_pages(fetch, first_url) in pager.py using the frozen official "
        "GitHub REST pagination guide at " + str(source) + ". Read the source rather "
        "than using live network data. fetch(url) returns a dict with data and headers. "
        "Return a flat list of items. Follow the link header's rel=next URL exactly; "
        "do not construct page numbers. Handle array, object-wrapped and no-content "
        "responses, and stop if a next URL repeats. Header key casing can vary. "
        "Native shell output for long files may be truncated, so use bounded line "
        "ranges or the saved output when needed. Run a local check before finishing.\n")
    reference, partial = output / "reference.patch", output / "partial.patch"
    make_patch(SEED, REFERENCE, reference)
    make_patch(SEED, PARTIAL, partial)
    return seed, prompt, reference, partial


def prepare(args, source, provenance):
    output = args.output
    if output.exists():
        raise ValueError("Use a fresh output for frozen public fixture")
    output.mkdir(mode=0o700)
    image_id = checked(["docker", "image", "inspect", PYTHON_IMAGE, "--format", "{{.Id}}"])
    seed, prompt, reference, partial = fixture(output, source)
    base = checked(["git", "-C", str(seed), "rev-parse", "HEAD"])
    controls = {name: grade_clone(seed, base, patch, args.grade_root)
                for name, patch in (("seed", None), ("reference", reference),
                                    ("partial", partial))}
    passed = (not controls["seed"]["accepted"] and controls["reference"]["accepted"]
              and not controls["partial"]["accepted"] and
              all(item["container_absent"] and item["output_bounded"] and
                  not item["timed_out"] for item in controls.values()))
    report = {"schema": 1, "kind": "public_official_source_pagination_fixture",
              "source_commit": checked(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
              "script_sha256": sha(Path(__file__)), "source_sha256": sha(source),
              "provenance_sha256": sha(provenance), "seed_commit": base,
              "prompt_sha256": sha(prompt), "reference_patch_sha256": sha(reference),
              "partial_patch_sha256": sha(partial), "docker_image": PYTHON_IMAGE,
              "docker_image_id": image_id, "model_requests": 0,
              "protected_status": False, "controls": controls, "controls_passed": passed}
    (output / "fixture.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"fixture": str(output), "controls_passed": passed}))
    return 0 if passed else 1


def source_calls(receipt, source):
    calls = []
    for export in (receipt / "agent-evidence").glob("ses_*.export.json"):
        for message in json.loads(export.read_text())["data"]["messages"]:
            for part in message.get("content", []):
                if part.get("type") != "tool":
                    continue
                state = part.get("state", {})
                if str(source) not in json.dumps(state.get("input", {})):
                    continue
                calls.append({"tool": part.get("name"),
                              "status": state.get("status"),
                              "exit": state.get("metadata", {}).get("exit"),
                              "truncated": state.get("metadata", {}).get("truncated")})
    return calls


def run_arm(args, fixture_report, source, provenance, arm):
    seed, prompt = args.output / "seed", args.output / "prompt.txt"
    reference, partial = args.output / "reference.patch", args.output / "partial.patch"
    receipt = Path("/private/tmp") / ("kryn-public-pagination-" + arm + "-" + secrets.token_hex(8))
    base = fixture_report["seed_commit"]

    def grade(apfs_workspace, _private, evidence):
        patch = evidence / "agent-evidence" / "model.patch"
        if not patch.is_file() or patch.stat().st_size > 1024 * 1024:
            raise RuntimeError("Candidate patch absent or over public task budget")
        with tempfile.TemporaryDirectory(prefix="kryn-pagination-grade-", dir=args.grade_root) as temporary:
            staged = Path(temporary) / "workspace"
            clean_clone(seed, staged, base)
            checked(["git", "-C", str(staged), "apply", "--check", str(patch)])
            checked(["git", "-C", str(staged), "apply", str(patch)])
            same = (sha(staged / "pager.py") == sha(apfs_workspace / "pager.py") and
                    not (staged / "pager.py").is_symlink())
            if not same:
                raise RuntimeError("Docker-visible clone differs from APFS grader checkout")
            result = docker_grade(staged)
            result["staged_equals_apfs"] = same
            result["patch_sha256"] = sha(patch)
            return result

    try:
        result = run_candidate_to_grader(
            seed=seed, prompt=prompt, task_id="public-github-pagination-" + arm,
            arm=arm, tool_venv=args.tool_venv, receipt=receipt,
            hidden_paths=[provenance, reference, partial, Path(__file__)],
            grade=grade, timeout=900, source_file=source)
    except BaseException as error:
        driver = receipt / "agent-evidence" / "driver.json"
        raw = json.loads(driver.read_text()) if driver.is_file() else {}
        resources = raw.get("resources") or {}
        guard_stopped = (raw.get("intervention") == "resource_guard" or
                         resources.get("warning_or_critical_observed") is True or
                         "Resource guard" in str(error))
        return {"arm": arm, "receipt": str(receipt), "accepted": False,
                "guard_stopped": guard_stopped,
                "error": type(error).__name__ + ": " + str(error)}
    agent = result["agent"]
    observed = source_calls(receipt, source)
    used = any(call["status"] == "completed" and
               (call["exit"] is None or call["exit"] == 0) for call in observed)
    graded = result["grader_result"]
    accepted = bool(result["graded"] and agent["completed"] and used and
                    graded["accepted"] and graded["staged_equals_apfs"] and
                    result["candidate_detached"] and result["capture_detached"] and
                    result["grader_detached"] and agent["resources"]["telemetry_complete"] and
                    not agent["resources"]["warning_or_critical_observed"])
    tools = [request.get("tools") for request in agent.get("requests", [])]
    return {"arm": arm, "receipt": str(receipt), "accepted": accepted,
            "guard_stopped": False,
            "native_completed": agent["completed"], "source_calls": observed,
            "source_used": used, "grade": graded, "tool_catalogs": tools,
            "request_count": len(agent.get("requests", [])),
            "wall_seconds": result["wall_seconds"], "resources": agent["resources"],
            "intervention": agent.get("intervention"),
            "candidate_detached": result["candidate_detached"],
            "capture_detached": result["capture_detached"],
            "grader_detached": result["grader_detached"]}


def pair(args, source, provenance):
    fixture_file = args.output / "fixture.json"
    if (not fixture_file.is_file() or (args.output / "pair.json").exists() or
            (args.output / "pair-progress.json").exists()):
        raise ValueError("Prepare exactly one fixture and run its pair once; inspect interrupted progress")
    frozen = json.loads(fixture_file.read_text())
    if (not frozen["controls_passed"] or frozen["script_sha256"] != sha(Path(__file__)) or
            frozen["source_commit"] != checked(["git", "-C", str(ROOT), "rev-parse", "HEAD"]) or
            frozen["source_sha256"] != sha(source) or
            frozen["provenance_sha256"] != sha(provenance) or
            frozen["seed_commit"] != checked(["git", "-C", str(args.output / "seed"), "rev-parse", "HEAD"]) or
            frozen["prompt_sha256"] != sha(args.output / "prompt.txt") or
            frozen["reference_patch_sha256"] != sha(args.output / "reference.patch") or
            frozen["partial_patch_sha256"] != sha(args.output / "partial.patch")):
        raise ValueError("Public fixture identity changed since controls")
    configs = [configuration(args.output / "seed", args.output / "seed" / ".git" / arm,
                             arm, "http://127.0.0.1:19876/v1")[0]
               for arm in ("native", "kryn")]
    permissions_equal = (configs[0]["permissions"] == configs[1]["permissions"] and
        {name: agent.get("permissions", []) for name, agent in configs[0].get("agents", {}).items()}
        == {name: agent.get("permissions", []) for name, agent in configs[1].get("agents", {}).items()})
    runs = [run_arm(args, frozen, source, provenance, "native")]
    (args.output / "pair-progress.json").write_text(json.dumps({
        "source_commit": frozen["source_commit"], "runs": runs}, indent=2) + "\n")
    if not runs[0]["guard_stopped"]:
        runs.append(run_arm(args, frozen, source, provenance, "kryn"))
    catalogs_equal = (len(runs) == 2 and all(run.get("tool_catalogs") for run in runs) and
        all(catalog == run["tool_catalogs"][0]
            for run in runs for catalog in run["tool_catalogs"]) and
        runs[0]["tool_catalogs"][0] == runs[1]["tool_catalogs"][0])
    report = {"schema": 1, "kind": "public_official_source_pagination_pair",
              "source_commit": frozen["source_commit"], "script_sha256": sha(Path(__file__)),
              "fixture_sha256": sha(fixture_file), "source_sha256": sha(source),
              "provenance_sha256": sha(provenance), "model_id": "Qwen3.5-9B-6bit",
              "protected_status": False, "order": ["native", "kryn"],
              "pair_completed": len(runs) == 2,
              "permissions_equal": permissions_equal,
              "tool_catalogs_equal": bool(catalogs_equal), "runs": runs}
    (args.output / "pair.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"pair": str(args.output / "pair.json"),
                      "permissions_equal": permissions_equal,
                      "tool_catalogs_equal": bool(catalogs_equal),
                      "pair_completed": len(runs) == 2,
                      "accepted": {run["arm"]: run["accepted"] for run in runs}}))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "pair"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--grade-root", required=True, type=Path)
    parser.add_argument("--tool-venv", required=True, type=Path)
    args = parser.parse_args()
    args.output = args.output.absolute()
    args.grade_root = args.grade_root.absolute()
    args.tool_venv = args.tool_venv.absolute()
    if (args.output.parent != Path("/private/tmp") or
            args.grade_root != args.grade_root.resolve() or
            not args.grade_root.is_dir() or
            args.grade_root.stat().st_uid != os.geteuid() or
            args.grade_root.stat().st_mode & 0o077 or
            not args.tool_venv.is_dir()):
        parser.error("Use a direct /private/tmp output and owned private grade root")
    source, provenance = validate_source(args.source_dir)
    if checked(["git", "-C", str(ROOT), "status", "--porcelain"]):
        parser.error("Research source must be a clean commit")
    if args.stage == "prepare":
        return prepare(args, source, provenance)
    return pair(args, source, provenance)


if __name__ == "__main__":
    raise SystemExit(main())
