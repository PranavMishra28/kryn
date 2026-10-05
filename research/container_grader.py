"""No-model exported-patch admission through isolated official SWE-bench grading.

The official evaluator owns patch application, tests and scoring. Only container
creation and cleanup are supplied by our guarded parent; no upstream files change.
This screen cannot generate model responses or qualify accepted engineering work.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from research.container_admission import source_inputs
from research.container_worker import DockerWorker, HostGuard, LABEL, validate_worker
from research.local_campaign import atomic, controlled_env, file_sha
from research.run_external_patch import bounded_output
from research.swebench_controller import source_lock
from research import swebench_local
from tools.context_probe import summarize_resources


def wheel_paths(manifest):
    root = Path(manifest["wheelhouse"])
    pins = manifest["wheel_sha256"]
    if not 1 <= len(pins) <= 8 or root.is_symlink() or {p.name for p in root.iterdir()} != set(pins):
        raise RuntimeError("Offline wheel inventory differs from the frozen manifest")
    paths = []
    for name, digest in pins.items():
        path = root / name
        if (Path(name).name != name or not name.endswith(".whl") or path.is_symlink()
                or not path.is_file() or not 0 < path.stat().st_size <= 8 * 1024**2
                or file_sha(path) != digest):
            raise RuntimeError("Offline wheel identity drift")
        paths.append(path)
    if sum(p.stat().st_size for p in paths) > 16 * 1024**2:
        raise RuntimeError("Offline wheel byte budget exceeded")
    return paths


def worker_settled(manifest):
    admission = Path(manifest["admission_root"])
    required = {"manifest.json", "result.json", "native/result.json", "kryn/result.json",
                "native/ownership.json", "kryn/ownership.json", "kryn/model.patch"}
    if required != set(manifest["admission_sha256"]):
        raise RuntimeError("Worker admission receipts are not completely pinned")
    for name, digest in manifest["admission_sha256"].items():
        if file_sha(admission / name) != digest:
            raise RuntimeError("Worker admission evidence drift")
    if json.loads((admission / "result.json").read_text()).get("passed") is not True:
        raise RuntimeError("Worker admission did not pass")
    for arm in ("native", "kryn"):
        result = json.loads((admission / arm / "result.json").read_text())
        if result.get("passed") is not True or result.get("cleanup_error") or result.get("guard_reason"):
            raise RuntimeError("Worker arm admission or cleanup did not pass")
        ownership = json.loads((admission / arm / "ownership.json").read_text())
        if ownership.get("cleanup_errors"):
            raise RuntimeError("Worker cleanup did not settle")
        for kind in ("container", "network"):
            found = subprocess.check_output(
                ["docker", kind, "ls", *(["-a"] if kind == "container" else []),
                 "-q", "--filter", "label=" + LABEL + "=" + ownership["owner"]],
                timeout=15, text=True)
            if found.strip():
                raise RuntimeError("Worker or inference relay remains before grading")


def frozen(campaign, manifest):
    if (file_sha(campaign / "manifest.json") != (campaign / "manifest.sha256").read_text().strip()
            or manifest["kind"] != "swe_container_grader_no_model_admission"
            or source_inputs() != manifest["source_sha256"]):
        raise RuntimeError("Grader admission source or manifest drift")
    if not (campaign / "execution-lock.json").is_file():
        raise RuntimeError("Official evaluator lock must be sealed before grading")
    locked = source_lock(manifest, campaign)
    if locked["evaluator_package_sha256"] != manifest["evaluator_package_sha256"]:
        raise RuntimeError("Installed evaluator differs from the independently pinned package")
    parquet = swebench_local.DATASET_ROOT / manifest["task"]["dataset"] / "data/test-00000-of-00001.parquet"
    if file_sha(parquet) != manifest["datasets"][manifest["task"]["dataset"]]["test_sha256"]:
        raise RuntimeError("Official dataset drift")
    if swebench_local.image_identity({"image_tag": manifest["official_image_digest"]})["Id"] != manifest["official_image_id"]:
        raise RuntimeError("Official image drift")
    patch = campaign / "model.patch"
    if patch.is_symlink() or not patch.is_file() or not 0 < patch.stat().st_size <= 16 * 1024**2:
        raise RuntimeError("Grader patch is not a bounded regular file")
    if file_sha(patch) != manifest["patch_sha256"]:
        raise RuntimeError("Exported patch drift")
    wheel_paths(manifest)
    worker_settled(manifest)


def require_owned(info, control):
    if (info["Id"] != control["container"]
            or info["Config"]["Labels"].get(LABEL) != control["owner"]):
        raise RuntimeError("Official grader container ownership drift")
    validate_worker(info, control["image_id"], "none", grader=True)


def require_test_evidence(report, expected_tests, parsed):
    if report.get("patch_successfully_applied") is not True:
        raise RuntimeError("Official grader found no parseable test output")
    statuses = report.get("tests_status", {})
    for group, expected in expected_tests.items():
        if not set(expected).issubset(parsed):
            raise RuntimeError("Official grader did not observe every expected test")
        observed = statuses.get(group, {})
        success, failure = observed.get("success"), observed.get("failure")
        if (not isinstance(success, list) or not isinstance(failure, list)
                or sorted(success + failure) != sorted(expected) or set(success) & set(failure)):
            raise RuntimeError("Official grader test coverage differs from the frozen task")
    if not expected_tests["FAIL_TO_PASS"]:
        raise RuntimeError("Grader admission requires nonempty fail-to-pass checks")


def official_child(campaign):
    # This process runs only the pinned official evaluator after the worker and
    # inference relay have settled. Parent retains cleanup ownership on any exit.
    import docker
    import swebench.harness.run_evaluation as evaluator

    manifest = json.loads((campaign / "manifest.json").read_text())
    frozen(campaign, manifest)
    control = json.loads((campaign / "grade/control.json").read_text())
    row, _ = swebench_local.row_for(manifest, manifest["task"])
    if manifest["patch_role"] == "exported_canary":
        expected = (Path(manifest["admission_root"]) / "kryn/model.patch").read_bytes()
        expected_resolved = False
    elif manifest["patch_role"] == "official_gold_control":
        expected = row["patch"].encode()
        expected_resolved = True
    else:
        raise RuntimeError("Unknown no-model admission patch role")
    if (expected != (campaign / "model.patch").read_bytes()
            or manifest["expected_resolved"] is not expected_resolved):
        raise RuntimeError("No-model grader control patch or expected outcome drift")
    spec = evaluator.make_test_spec(row)
    if spec.image_assets:
        raise RuntimeError("Offline grader screen does not admit asset downloads")
    client = docker.from_env(timeout=30)
    owned = client.containers.get(control["container"])
    owned.reload()
    require_owned(owned.attrs, control)

    def create(test_spec, _client, run_id, _logger):
        if (test_spec.instance_id != manifest["task"]["instance_id"]
                or test_spec.image != manifest["task"]["image_tag"]
                or run_id != control["run_id"]):
            raise RuntimeError("Official grader requested different frozen task")
        owned.reload()
        require_owned(owned.attrs, control)
        return owned

    def cleanup(_client, container, _logger):
        if container is not None and container.id != owned.id:
            raise RuntimeError("Official grader cleanup requested another container")

    evaluator.create_container = create
    evaluator.cleanup_container = cleanup
    prediction = {"instance_id": spec.instance_id, "model_name_or_path": "kryn-no-model-admission",
                  "model_patch": (campaign / "model.patch").read_text()}
    result = evaluator.run_instance(spec, prediction, client, control["run_id"], timeout=1800)
    if not result or result[0] != spec.instance_id:
        raise RuntimeError("Official grader did not produce an instance report")
    expected_tests = {"FAIL_TO_PASS": spec.FAIL_TO_PASS, "PASS_TO_PASS": spec.PASS_TO_PASS}
    from swebench.harness.grading import get_logs_eval
    log = (evaluator.RUN_EVALUATION_LOG_DIR / control["run_id"] /
           prediction["model_name_or_path"] / spec.instance_id / evaluator.LOG_TEST_OUTPUT)
    parsed, found = get_logs_eval(spec, log)
    if not found:
        raise RuntimeError("Official grader found no parsed test run")
    require_test_evidence(result[1][spec.instance_id], expected_tests, parsed)
    evaluator.make_run_report({spec.instance_id: prediction}, [row], control["run_id"], client)
    frozen(campaign, manifest)
    atomic(campaign / "grade/official-child.json", {"completed": True, "test_evidence": True})
    client.close()


def grade(campaign):
    campaign = campaign.resolve(strict=True)
    manifest = json.loads((campaign / "manifest.json").read_text())
    frozen(campaign, manifest)
    evidence = campaign / "grade"
    evidence.mkdir(mode=0o700)  # An interrupted or failed attempt is never replayed.
    report = {"passed": False, "kind": manifest["kind"], "model_generation": False}
    start = time.monotonic()
    try:
        with HostGuard(evidence) as guard:
            docker = DockerWorker(evidence, guard)
            try:
                identity = docker.create("grader", manifest["official_image_id"],
                                         ["tail", "-f", "/dev/null"], grader=True)
                docker.command("exec", identity, "mkdir", "/opt/kryn-wheels")
                for wheel in wheel_paths(manifest):
                    target = "/opt/kryn-wheels/" + wheel.name
                    docker.command("cp", str(wheel), identity + ":" + target)
                    observed = docker.command("exec", identity, "sha256sum", target).split()[0]
                    if observed != manifest["wheel_sha256"][wheel.name]:
                        raise RuntimeError("Offline wheel changed during container copy")
                control = {"container": identity, "owner": docker.owner,
                           "image_id": manifest["official_image_id"], "run_id": docker.owner}
                info = docker.inspect("container", identity)
                require_owned(info, control)
                atomic(evidence / "container-inspect.json", info)
                atomic(evidence / "control.json", control)
                env = controlled_env()
                env.update(HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1")

                def cancelled():
                    guard.check()
                    if time.monotonic() - docker.last_usage_check >= 5:
                        docker.check_usage()
                    return False

                bounded_output([str(swebench_local.EVALUATOR_PYTHON), "-B", "-m",
                                "research.container_grader", "--child", str(campaign)],
                               evidence / "official.log", 8 * 1024**2, env=env, cwd=evidence,
                               cancelled=cancelled, timeout=2100)
                frozen(campaign, manifest)
                official = swebench_local.official_result(
                    evidence, manifest["task"], control["run_id"], model_patch=campaign / "model.patch")
                info = docker.inspect("container", identity)
                require_owned(info, control)
                atomic(evidence / "container-after.json", info)
                report.update(official=official, patch_sha256=file_sha(campaign / "model.patch"),
                              oom_killed=info["State"]["OOMKilled"])
                report["passed"] = (official.get("graded") is True
                                    and official.get("resolved") is manifest["expected_resolved"]
                                    and official.get("infra_failure_instances") == 0
                                    and official.get("error_instances") == 0
                                    and not info["State"]["OOMKilled"])
                guard.check()
            finally:
                docker.close()
                report["cleanup_settled"] = True
        guard.check()  # Include final resource samples taken by __exit__.
        resources = summarize_resources(guard.samples)
        report["resources"] = resources
        report["passed"] = (report["passed"] and resources.get("telemetry_complete") is True
                            and resources.get("warning_or_critical_observed") is False
                            and resources.get("swap_peak_growth_bytes") == 0)
    except Exception as error:
        report.update(passed=False, error=str(error))
    report["wall_seconds"] = round(time.monotonic() - start, 3)
    atomic(evidence / "result.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("campaign", type=Path)
    args = parser.parse_args()
    if args.child:
        sys.stderr = sys.stdout
        official_child(args.campaign)
    else:
        result = grade(args.campaign)
        print(json.dumps(result))
        raise SystemExit(0 if result["passed"] else 1)
