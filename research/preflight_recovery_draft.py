#!/usr/bin/env python3
"""No-model, real OpenCode/volume preflight for one owner-only recovery draft.

The owner-only bundle is input data, never installed with KRYN. A passing
receipt checks boundary mechanics and three grader controls; it does not seal
or score a protected holdout task.
"""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile

from agent_grade_barrier import clean_clone, create_volume, detach, image_entry
from check_holdout_boundary import probe, server_probe
from run_external_patch import benchmark_tools, configuration


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(argv, *, timeout=20):
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                          close_fds=True)


def grade(bundle, workspace, variant, receipt):
    """Run the trusted Docker oracle, keeping its bytes out of the candidate."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(Path.home()),
           "PYTHONDONTWRITEBYTECODE": "1", "CANDIDATE_REPO": str(workspace),
           "KRYN_TRUSTED_WORKSPACE": str(workspace),
           "KRYN_VALIDATION_ROOT": str(workspace.parent)}
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        child = subprocess.Popen([sys.executable, "-B", str(bundle / "hidden_grader" / "grade.py")],
                                 cwd=workspace, env=env, stdout=stdout, stderr=stderr,
                                 start_new_session=True, close_fds=True)
        timed_out = False
        try:
            child.wait(timeout=45)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if child.poll() is None:
                child.wait(timeout=5)
            # The trusted probe names each worker with its own PID. Reap even
            # when the parent was interrupted before the probe's finally block.
            listing = command(["docker", "ps", "-aq", "--filter",
                               f"name=kryn-probe-{child.pid}-"], timeout=5)
            if listing.returncode or listing.stdout.strip():
                for container in listing.stdout.splitlines():
                    command(["docker", "rm", "-f", container], timeout=5)
                raise RuntimeError("Trusted probe container did not self-reap")
        stdout.seek(0); stderr.seek(0)
        out, err = stdout.read(65537), stderr.read(65537)
    (receipt / (variant + ".log")).write_bytes(out + b"\n--- stderr ---\n" + err)
    return {"exit": child.returncode, "timed_out": timed_out,
            "output_bounded": len(out) <= 65536 and len(err) <= 65536,
            "stdout_sha256": hashlib.sha256(out).hexdigest(),
            "stderr_sha256": hashlib.sha256(err).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--tool-venv", required=True, type=Path)
    args = parser.parse_args()
    draft, receipt = args.draft.absolute(), args.receipt.absolute()
    if (draft != draft.resolve() or not draft.is_dir() or
            receipt.parent != Path("/private/tmp") or receipt.exists() or
            args.tool_venv.resolve().is_relative_to(draft)):
        parser.error("Use a canonical private draft and fresh direct /private/tmp receipt")
    bundles = list((draft / "bundles").iterdir())
    if len(bundles) != 1 or not bundles[0].is_dir():
        parser.error("Expected exactly one owner-only task bundle")
    bundle = bundles[0]
    manifest_file = bundle / "manifest.json"
    manifest = json.loads(manifest_file.read_text())
    archive = json.loads((draft / "ARCHIVE.json").read_text())
    validation = json.loads((draft / "VALIDATION.json").read_text())
    task_id = manifest["id"]
    if (not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,80}", task_id) or
            bundle.name != task_id or manifest["category"] != "error_recovery" or
            manifest["protected_status"] is not False or manifest["model_runs"] != 0 or
            validation["protected_status"] is not False or validation["model_runs"] != 0):
        parser.error("Only one unexposed error-recovery draft may be preflighted")
    receipt.mkdir(mode=0o700)
    source_root = Path(__file__).resolve().parents[1]
    source = command(["git", "-C", str(source_root), "rev-parse", "HEAD"])
    status = command(["git", "-C", str(source_root), "status", "--porcelain"])
    report = {"schema": 1, "kind": "recovery_draft_no_model_preflight",
              "task_id": task_id, "source_commit": source.stdout.strip(),
              "source_tree_dirty": bool(status.stdout), "model_requests": 0,
              "protected_status": False, "passed": False,
              "draft_archive_sha256": sha(draft / "ARCHIVE.json"),
              "manifest_sha256": sha(manifest_file),
              "runner_sha256": sha(Path(__file__))}
    volume = None
    detached = False
    try:
        if source.returncode or status.returncode or report["source_tree_dirty"]:
            raise RuntimeError("Research source must be a clean commit")
        archived = archive["files"]
        report["archived_hashes_match"] = bool(archived) and all(
            (draft / name).is_file() and sha(draft / name) == digest
            for name, digest in archived.items())
        checksums = json.loads((bundle / "SHA256SUMS.json").read_text())
        report["bundle_hashes_match"] = bool(checksums) and all(
            (bundle / name).is_file() and sha(bundle / name) == digest
            for name, digest in checksums.items())
        seed = bundle / "repo"
        oracle = draft / "trusted_grader.py"
        reference = bundle / "reference.patch"
        partial = bundle / "partial.patch"
        hidden = [oracle, manifest_file, reference, partial, draft / "VALIDATION.json"]
        report["frozen_identity_match"] = (
            manifest["oracle_sha256"] == sha(oracle)
            and manifest["validation_receipt_sha256"] == sha(draft / "VALIDATION.json")
            and validation["prompt_sha256"] == sha(bundle / "task.md")
            and validation["reference_patch_sha256"] == sha(reference)
            and validation["grader_sha256"] == sha(oracle))
        head = command(["git", "-C", str(seed), "rev-parse", "HEAD"])
        seed_status = command(["git", "-C", str(seed), "status", "--porcelain=v1",
                               "--untracked-files=all", "--ignored"])
        report["seed_clean"] = (head.returncode == 0 and seed_status.returncode == 0
                                and head.stdout.strip() == manifest["base_commit"]
                                and not seed_status.stdout)
        if not all(report[key] for key in ("archived_hashes_match", "bundle_hashes_match",
                                       "frozen_identity_match", "seed_clean")):
            raise RuntimeError("Owner-only task identity or seed changed")
        tool_path, tool_dependencies, tool_manifest = benchmark_tools(args.tool_venv)
        report["benchmark_tool_manifest"] = tool_manifest
        volume = create_volume(receipt, "candidate")
        workspace, private = volume.mount / "workspace", volume.mount / "private"
        private.mkdir(mode=0o700)
        clean_clone(seed, workspace, manifest["base_commit"])
        report["hidden_files_separate_device"] = all(
            path.stat().st_dev != workspace.stat().st_dev for path in hidden)
        report["hidden_hardlinks_impossible"] = {}
        for label, path in zip(("oracle", "manifest", "reference", "partial", "validation"), hidden):
            alias = workspace / ("hidden-" + label)
            try:
                os.link(path, alias)
            except OSError as error:
                report["hidden_hardlinks_impossible"][label] = error.errno == errno.EXDEV
            else:
                report["hidden_hardlinks_impossible"][label] = False
                alias.unlink()
        (workspace / "visible.txt").write_text("candidate-visible")
        devices = [item.get("dev-entry") for item in
                   image_entry(volume.image).get("system-entities", [])]
        device = next((item for item in reversed(devices)
                       if item and Path(item).exists()), None)
        report["boundary"] = probe(workspace, private, oracle, volume.image,
                                   device, receipt)
        # Probe already covers direct/symlink/copy/metadata aliases. The server
        # path exercises the actual native OpenCode shell in both trial arms.
        report["server_boundary"] = {}
        for arm in ("native", "kryn"):
            _, _, dependencies = configuration(
                workspace, workspace / ".git" / ("preflight-" + arm), arm,
                "http://127.0.0.1:19876/v1")
            report["server_boundary"][arm] = server_probe(
                workspace, receipt / (arm + "-server.log"), oracle,
                oracle.read_text(), private, arm=arm, tool_venv=args.tool_venv,
                extra_hidden=(("manifest", manifest_file), ("reference", reference),
                              ("partial", partial), ("validation", draft / "VALIDATION.json")))
            report["dependencies_exclude_draft_" + arm] = all(
                not Path(item).resolve().is_relative_to(draft)
                and not draft.is_relative_to(Path(item).resolve())
                for item in dependencies + tool_dependencies)
        for name in ("visible.txt", "oracle-symlink", "oracle-hardlink",
                     "candidate-hardlink", "copied"):
            (workspace / name).unlink(missing_ok=True)
        report["candidate_clean_after_probe"] = not command(
            ["git", "-C", str(workspace), "status", "--porcelain=v1",
             "--untracked-files=all", "--ignored"]).stdout
        if not (report["hidden_files_separate_device"] and
                all(report["hidden_hardlinks_impossible"].values()) and
                all(report["boundary"].values()) and
                all(all(checks.values()) for checks in report["server_boundary"].values()) and
                report["dependencies_exclude_draft_native"] and
                report["dependencies_exclude_draft_kryn"] and
                report["candidate_clean_after_probe"]):
            raise RuntimeError("Candidate-volume/OpenCode boundary failed")
        detach(volume)
        detached = True
        report["candidate_detached_before_grading"] = True
        # Docker Desktop cannot bind-mount this Mac's nested APFS candidate
        # image. The real barrier also detaches the candidate first, then
        # grades a fresh host-side checkout. /Users is Docker-shared here;
        # /private/tmp newly created checkouts appeared late to its VM.
        with tempfile.TemporaryDirectory(prefix="recovery-grader-", dir=draft.parent) as grading:
            grader_workspace = Path(grading) / "workspace"
            clean_clone(seed, grader_workspace, manifest["base_commit"])
            report["grader_workspace_fresh"] = (
                grader_workspace.stat().st_dev == oracle.stat().st_dev
                and grader_workspace != workspace)
            if not report["grader_workspace_fresh"]:
                raise RuntimeError("Fresh grading checkout identity failed")
            outcomes = {item["variant"]: item for item in validation["outcomes"]}
            for variant, patch in (("seed", None), ("reference", reference),
                                   ("partial", partial)):
                if patch is not None:
                    applied = command(["git", "-C", str(grader_workspace), "apply", str(patch)])
                    if applied.returncode:
                        raise RuntimeError("Frozen " + variant + " patch did not apply")
                report[variant] = grade(bundle, grader_workspace, variant, receipt)
                expected = outcomes[variant]
                if ((report[variant]["exit"] == 0) != expected["passed"] or
                        not report[variant]["output_bounded"] or report[variant]["timed_out"]
                        or report[variant]["stdout_sha256"] != expected["stdout_sha256"]
                        or report[variant]["stderr_sha256"] != expected["stderr_sha256"]):
                    raise RuntimeError("Fresh-checkout " + variant + " grader differed")
                if variant != "seed":
                    reset = command(["git", "-C", str(grader_workspace), "reset", "--hard",
                                     manifest["base_commit"]])
                    if reset.returncode:
                        raise RuntimeError("Could not reset fresh control checkout")
            report["controls_pass"] = (report["seed"]["exit"] != 0 and
                                       report["reference"]["exit"] == 0 and
                                       report["partial"]["exit"] != 0)
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if volume is not None and not detached:
            try:
                detach(volume)
                detached = True
            except BaseException as error:
                report["detach_error"] = type(error).__name__ + ": " + str(error)
        report["detached"] = detached
        report["mechanics_passed"] = bool(report.get("controls_pass") and
                                          report.get("detached") and "error" not in report)
        report["passed"] = False  # Unsealed task; never an H1 score or admission.
        (receipt / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report.get(key) for key in
                      ("task_id", "mechanics_passed", "controls_pass", "detached", "error")},
                     sort_keys=True))
    return 0 if report["mechanics_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
