#!/usr/bin/env python3
"""Public GitHub rate-limit coding calibration, never a protected score."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import tempfile

from agent_grade_barrier import clean_clone, run_candidate_to_grader
from public_source_pagination import (PYTHON_IMAGE, checked, sha, source_calls,
                                      wire_contracts)
from run_external_patch import configuration

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "3815984e337dad4da3ceb1a60da044da5c05db5df969719c40e10dd9a0d490ac"
PROVENANCE_SHA = "a119247a97d8212e2923f00159cd365a042553b309de833d5a76274ebd7dcbde"
SEED = """def request_with_backoff(fetch, sleep, now, max_retries=2):
    return fetch()
"""
REFERENCE = """def request_with_backoff(fetch, sleep, now, max_retries=2):
    secondary_count = 0
    for attempt in range(max_retries + 1):
        response = fetch()
        if response.get('status') not in (403, 429):
            return response
        headers = {str(key).lower(): value for key, value in
                   (response.get('headers') or {}).items()}
        body = response.get('body') or {}
        message = body.get('message', '') if isinstance(body, dict) else ''
        secondary = 'secondary rate limit' in str(message).lower()
        primary = (str(headers.get('x-ratelimit-remaining', '')) == '0' and
                   headers.get('x-ratelimit-reset') is not None)
        if not secondary and not primary:
            return response
        if attempt == max_retries:
            raise RuntimeError('rate limit persisted')
        reset = headers.get('x-ratelimit-reset')
        if secondary:
            delay = None
            retry_after = headers.get('retry-after')
            if retry_after is not None:
                try:
                    delay = max(0.0, float(retry_after))
                except (TypeError, ValueError):
                    pass
            if delay is None and primary:
                delay = max(1.0, float(reset) - float(now()) + 1.0)
            if delay is None:
                delay = 60.0
            delay *= 2 ** secondary_count
            secondary_count += 1
        else:
            delay = max(1.0, float(reset) - float(now()) + 1.0)
            secondary_count = 0
        sleep(delay)
    raise RuntimeError('unreachable retry state')
"""
PARTIAL = """def request_with_backoff(fetch, sleep, now, max_retries=2):
    response = fetch()
    if response.get('status') == 429 and max_retries:
        sleep(1)
        return fetch()
    return response
"""
WORKER = """import copy, json, sys
sys.path.insert(0, '/workspace')
from backoff import request_with_backoff
cases = json.load(sys.stdin)
results = []
for case in cases:
    calls, sleeps = [], []
    def fetch():
        if len(calls) >= len(case['responses']):
            raise AssertionError('unexpected extra fetch')
        response = copy.deepcopy(case['responses'][len(calls)])
        calls.append(response['status'])
        return response
    def sleep(seconds):
        sleeps.append(seconds)
    def now():
        return case['now']
    try:
        response = request_with_backoff(fetch, sleep, now, case['max_retries'])
        results.append({'id': case['id'], 'response': response,
                        'calls': calls, 'sleeps': sleeps})
    except Exception as error:
        results.append({'id': case['id'], 'error': type(error).__name__,
                        'calls': calls, 'sleeps': sleeps})
print(json.dumps(results, separators=(',', ':')))
"""


def cases():
    ok = {"status": 200, "headers": {}, "body": {"data": [1]}}
    forbidden = {"status": 403, "headers": {}, "body": {"message": "access denied"}}
    secondary = {"status": 429, "headers": {},
                 "body": {"message": "You have exceeded a secondary rate limit"}}
    primary = {"status": 403, "headers": {"x-ratelimit-remaining": "0",
                                           "x-ratelimit-reset": "105"},
               "body": {"message": "API rate limit exceeded"}}
    return [
        {"id": "success", "responses": [ok], "now": 100, "max_retries": 2,
         "expected": {"response": ok, "calls": [200], "sleeps": []}},
        {"id": "unrelated-403", "responses": [forbidden], "now": 100,
         "max_retries": 2,
         "expected": {"response": forbidden, "calls": [403], "sleeps": []}},
        {"id": "primary-reset", "responses": [primary, ok], "now": 100,
         "max_retries": 2,
         "expected": {"response": ok, "calls": [403, 200], "sleeps": [6.0]}},
        {"id": "secondary-retry-after", "responses": [
            {**secondary, "headers": {"retry-after": "7"}}, ok],
         "now": 100, "max_retries": 2,
         "expected": {"response": ok, "calls": [429, 200], "sleeps": [7.0]}},
        {"id": "secondary-fallback", "responses": [secondary, ok],
         "now": 100, "max_retries": 2,
         "expected": {"response": ok, "calls": [429, 200], "sleeps": [60.0]}},
        {"id": "mixed-case-primary", "responses": [
            {"status": 429, "headers": {"X-RateLimit-Remaining": "0",
                                         "X-RateLimit-Reset": "110"},
             "body": {"message": "API rate limit exceeded"}}, ok],
         "now": 100, "max_retries": 2,
         "expected": {"response": ok, "calls": [429, 200], "sleeps": [11.0]}},
        {"id": "secondary-exponential", "responses": [secondary, secondary, ok],
         "now": 100, "max_retries": 2,
         "expected": {"response": ok, "calls": [429, 429, 200],
                      "sleeps": [60.0, 120.0]}},
        {"id": "retry-exhausted", "responses": [secondary, secondary],
         "now": 100, "max_retries": 1,
         "expected": {"error": "RuntimeError", "calls": [429, 429],
                      "sleeps": [60.0]}},
    ]


def validate_source(source_dir):
    source_dir = Path(source_dir).absolute()
    source = source_dir / "github-rest-rate-limits.md"
    provenance = source_dir / "SOURCE.json"
    if (source_dir != source_dir.resolve() or not source_dir.is_dir() or
            source_dir.stat().st_uid != os.geteuid() or source_dir.stat().st_mode & 0o077 or
            not source.is_file() or source.stat().st_size != 9870 or
            source.stat().st_mode & 0o077 or sha(source) != SOURCE_SHA or
            not provenance.is_file() or provenance.stat().st_mode & 0o077 or
            sha(provenance) != PROVENANCE_SHA):
        raise ValueError("Frozen rate-limit source or provenance changed")
    return source, provenance


def docker_grade(workspace):
    public_cases = [{key: value for key, value in case.items() if key != "expected"}
                    for case in cases()]
    expected = [{"id": case["id"], **case["expected"]} for case in cases()]
    container = "kryn-public-rate-limit-" + secrets.token_hex(10)
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
        stdout.seek(0)
        stderr.seek(0)
        out, err = stdout.read(65537), stderr.read(65537)
    remaining = checked(["docker", "ps", "-a", "--filter", "name=" + container,
                         "--format", "{{.Names}}"])
    bounded = len(out) <= 65536 and len(err) <= 65536
    try:
        observed = json.loads(out) if child.returncode == 0 and bounded else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        observed = None
    checks = {item["id"]: observed[index] == item if isinstance(observed, list)
              and len(observed) == len(expected) else False
              for index, item in enumerate(expected)}
    return {"accepted": bool(not timed_out and not remaining and bounded and
                              child.returncode == 0 and all(checks.values())),
            "cases": checks, "docker_exit": child.returncode,
            "timed_out": timed_out, "output_bounded": bounded,
            "container_absent": not remaining,
            "stdout_sha256": hashlib.sha256(out).hexdigest(),
            "stderr_sha256": hashlib.sha256(err).hexdigest()}


def grade_clone(seed, base, patch, grade_root):
    with tempfile.TemporaryDirectory(prefix="kryn-rate-limit-grade-", dir=grade_root) as temporary:
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
    (seed / "backoff.py").write_text(SEED)
    checked(["git", "-C", str(seed), "add", "backoff.py"])
    env = os.environ.copy()
    env.update(GIT_AUTHOR_NAME="KRYN public rate limit", GIT_AUTHOR_EMAIL="task@example.invalid",
               GIT_COMMITTER_NAME="KRYN public rate limit", GIT_COMMITTER_EMAIL="task@example.invalid",
               GIT_AUTHOR_DATE="2026-10-03T00:00:00+0000",
               GIT_COMMITTER_DATE="2026-10-03T00:00:00+0000")
    checked(["git", "-C", str(seed), "commit", "-qm", "broken public rate-limit seed"], env=env)
    prompt = output / "prompt.txt"
    prompt.write_text(
        "Implement request_with_backoff(fetch, sleep, now, max_retries=2) in backoff.py "
        "using the pinned official GitHub REST rate-limit guide at " + str(source) + ". "
        "Read the source rather than live network data. fetch() returns a dict with "
        "integer status, headers, and a body dict with message. Return ordinary and "
        "unrelated-error responses unchanged. Retry recognized primary 403/429 when "
        "x-ratelimit-remaining is 0 and reset is present, waiting max(1, reset-now()+1) "
        "seconds. Retry secondary 403/429 when body.message contains 'secondary rate "
        "limit' (case-insensitive): use numeric retry-after seconds if valid, otherwise "
        "reset timing when remaining is 0, otherwise 60 seconds. Repeated consecutive "
        "secondary failures double that base delay each time. Header keys may have "
        "any casing. An invalid retry-after uses the other secondary fallback. "
        "max_retries bounds additional fetch calls; if a recognized limit persists "
        "after that budget, raise RuntimeError without another sleep. Injected sleep "
        "and now mean no real network or waiting is needed. Run a local check.\n")
    reference, partial = output / "reference.patch", output / "partial.patch"
    for after, target in ((REFERENCE, reference), (PARTIAL, partial)):
        target.write_text("".join(difflib.unified_diff(SEED.splitlines(keepends=True),
            after.splitlines(keepends=True), fromfile="a/backoff.py", tofile="b/backoff.py")))
    return seed, prompt, reference, partial


def prepare(args, source, provenance):
    if args.output.exists():
        raise ValueError("Use a fresh output for frozen public fixture")
    args.output.mkdir(mode=0o700)
    image_id = checked(["docker", "image", "inspect", PYTHON_IMAGE,
                        "--format", "{{.Id}}"])
    seed, prompt, reference, partial = fixture(args.output, source)
    base = checked(["git", "-C", str(seed), "rev-parse", "HEAD"])
    controls = {name: grade_clone(seed, base, patch, args.grade_root)
                for name, patch in (("seed", None), ("reference", reference),
                                    ("partial", partial))}
    passed = (not controls["seed"]["accepted"] and controls["reference"]["accepted"]
              and not controls["partial"]["accepted"] and
              all(item["container_absent"] and item["output_bounded"] and
                  not item["timed_out"] for item in controls.values()))
    report = {"schema": 1, "kind": "public_official_source_rate_limit_fixture",
              "source_commit": checked(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
              "script_sha256": sha(Path(__file__)), "source_sha256": sha(source),
              "provenance_sha256": sha(provenance), "seed_commit": base,
              "prompt_sha256": sha(prompt), "reference_patch_sha256": sha(reference),
              "partial_patch_sha256": sha(partial), "docker_image": PYTHON_IMAGE,
              "docker_image_id": image_id, "model_requests": 0,
              "protected_status": False, "controls": controls, "controls_passed": passed}
    (args.output / "fixture.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"fixture": str(args.output), "controls_passed": passed}))
    return 0 if passed else 1


def run_arm(args, fixture_report, source, provenance, arm):
    seed, prompt = args.output / "seed", args.output / "prompt.txt"
    receipt = Path("/private/tmp") / ("kryn-public-rate-limit-" + arm + "-" + secrets.token_hex(8))

    def grade(apfs_workspace, _private, evidence):
        patch = evidence / "agent-evidence" / "model.patch"
        if not patch.is_file() or patch.stat().st_size > 1024 * 1024:
            raise RuntimeError("Candidate patch absent or over public task budget")
        with tempfile.TemporaryDirectory(prefix="kryn-rate-limit-grade-", dir=args.grade_root) as temporary:
            staged = Path(temporary) / "workspace"
            clean_clone(seed, staged, fixture_report["seed_commit"])
            checked(["git", "-C", str(staged), "apply", "--check", str(patch)])
            checked(["git", "-C", str(staged), "apply", str(patch)])
            same = (not (staged / "backoff.py").is_symlink() and
                    not (apfs_workspace / "backoff.py").is_symlink() and
                    sha(staged / "backoff.py") == sha(apfs_workspace / "backoff.py"))
            if not same:
                raise RuntimeError("Docker-visible clone differs from APFS grader checkout")
            result = docker_grade(staged)
            result["staged_equals_apfs"] = same
            result["patch_sha256"] = sha(patch)
            return result

    try:
        result = run_candidate_to_grader(
            seed=seed, prompt=prompt, task_id="public-github-rate-limit-" + arm,
            arm=arm, tool_venv=args.tool_venv, receipt=receipt,
            hidden_paths=[provenance, args.output / "reference.patch",
                          args.output / "partial.patch", Path(__file__)],
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
                "wire_contracts": wire_contracts(raw.get("requests", [])),
                "request_count": len(raw.get("requests", [])),
                "resources": resources,
                "source_calls": source_calls(receipt, source),
                "error": type(error).__name__ + ": " + str(error)}
    agent = result["agent"]
    observed = source_calls(receipt, source)
    used = any(call["tool"] == "read" and call["status"] == "completed" and
               call["truncated"] is False for call in observed)
    graded = result["grader_result"]
    accepted = bool(result["graded"] and agent["completed"] and used and
                    graded["accepted"] and graded["staged_equals_apfs"] and
                    result["candidate_detached"] and result["capture_detached"] and
                    result["grader_detached"] and agent["resources"]["telemetry_complete"] and
                    not agent["resources"]["warning_or_critical_observed"])
    return {"arm": arm, "receipt": str(receipt), "accepted": accepted,
            "guard_stopped": False, "native_completed": agent["completed"],
            "source_calls": observed, "source_used": used, "grade": graded,
            "wire_contracts": wire_contracts(agent.get("requests", [])),
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
        raise ValueError("Prepare exactly one fixture and run its pair once")
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
                             arm, "http://127.0.0.1:19876/v1", source_file=source)[0]
               for arm in ("native", "kryn")]
    permissions_equal = (configs[0]["permissions"] == configs[1]["permissions"] and
        {name: agent.get("permissions", []) for name, agent in configs[0].get("agents", {}).items()}
        == {name: agent.get("permissions", []) for name, agent in configs[1].get("agents", {}).items()})
    runs = [run_arm(args, frozen, source, provenance, "native")]
    (args.output / "pair-progress.json").write_text(json.dumps({
        "source_commit": frozen["source_commit"], "runs": runs}, indent=2) + "\n")
    if not runs[0]["guard_stopped"]:
        runs.append(run_arm(args, frozen, source, provenance, "kryn"))
    contracts_equal = (len(runs) == 2 and all(run.get("wire_contracts") for run in runs) and
        all(contract == run["wire_contracts"][0]
            for run in runs for contract in run["wire_contracts"]) and
        runs[0]["wire_contracts"][0] == runs[1]["wire_contracts"][0])
    report = {"schema": 1, "kind": "public_official_source_rate_limit_pair",
              "source_commit": frozen["source_commit"], "script_sha256": sha(Path(__file__)),
              "fixture_sha256": sha(fixture_file), "source_sha256": sha(source),
              "provenance_sha256": sha(provenance), "model_id": "Qwen3.5-9B-6bit",
              "protected_status": False, "order": ["native", "kryn"],
              "pair_completed": len(runs) == 2,
              "permissions_equal": permissions_equal,
              "wire_contract_equal": bool(contracts_equal), "runs": runs}
    (args.output / "pair.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"pair": str(args.output / "pair.json"),
                      "permissions_equal": permissions_equal,
                      "wire_contract_equal": bool(contracts_equal),
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
    return prepare(args, source, provenance) if args.stage == "prepare" else pair(args, source, provenance)


if __name__ == "__main__":
    raise SystemExit(main())
