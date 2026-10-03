#!/usr/bin/env python3
"""Offline admission preflight for one private Python task; no model requests.

The candidate checkout and its temporary directory live on a disposable APFS
volume. The oracle and reference patches stay on the host volume. This checks
the real task path and seed/reference/partial controls, but does not seal a
roster or score a protected trial.
"""
import argparse
import errno
import hashlib
import inspect
import json
import os
from pathlib import Path
import platform
import re
import resource
import signal
import subprocess
import sys
import tempfile

from check_holdout_boundary import background_boundary, mount_active, probe, server_probe
from run_external_patch import benchmark_tools, configuration


def command(argv, *, timeout=20):
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                          close_fds=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grade(oracle, workspace, private, boundary, draft, output):
    # The trusted oracle imports native_client, whose product ROOT derives from
    # HOME. Only the sandboxed candidate receives HOME=private (in harness.py).
    env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", str(Path.home())),
           "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONPATH": str(oracle.parent.parent),
           "KRYN_NATIVE_CLIENT": str(boundary),
           "CANDIDATE_PRIVATE": str(private)}
    def bound():
        # The oracle's own log is small; its sandboxed child needs a 1 MiB
        # hard ceiling for the harness's separate bounded temp files.
        resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 1024 * 1024))
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        child = subprocess.Popen([sys.executable, "-B", str(oracle), str(workspace)],
                                 cwd=workspace, env=env, stdout=stdout, stderr=stderr,
                                 close_fds=True, start_new_session=True, preexec_fn=bound)
        timed_out = False
        try:
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                timed_out = True
        finally:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if child.poll() is None:
                child.wait(timeout=2)
        stdout.seek(0); stderr.seek(0)
        out, err = stdout.read(65537), stderr.read(65537)
    output.write_bytes(out + b"\n--- stderr ---\n" + err)
    # The draft controls normalize only the disposable mount prefix. Keep the
    # actual bytes in the receipt, but compare stable failure signatures.
    normalized_out = out.decode("utf-8", errors="replace").rstrip("\n").replace(
        str(workspace.parent), "<CANDIDATE_VOLUME>/mount")
    normalized_err = err.decode("utf-8", errors="replace").rstrip("\n").replace(
        str(workspace.parent), "<CANDIDATE_VOLUME>/mount").replace(
        str(draft), "<DRAFT_ROOT>")
    return {"exit": child.returncode, "timed_out": timed_out,
            "output_bounded": len(out) <= 65536 and len(err) <= 65536,
            "stdout_sha256": hashlib.sha256(normalized_out.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(normalized_err.encode()).hexdigest(),
            "output_sha256": sha(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path, help="offline draft root with manifest.json")
    parser.add_argument("task_id")
    parser.add_argument("receipt", type=Path, help="new /private/tmp receipt directory")
    parser.add_argument("--tool-venv", required=True, type=Path,
                        help="pinned Python/ripgrep/Git environment used by both candidate arms")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,80}", args.task_id):
        parser.error("Task ID must be a simple slug")
    draft, receipt = args.draft.absolute(), args.receipt.absolute()
    if (draft != draft.resolve() or not draft.is_dir() or
            receipt.parent != Path("/private/tmp") or receipt.exists() or
            receipt.is_symlink()):
        parser.error("Use a canonical draft and a new direct /private/tmp receipt")
    if args.tool_venv.is_relative_to(draft) or args.tool_venv.is_relative_to(receipt):
        parser.error("Benchmark tools must not overlap the hidden draft or candidate receipt")
    receipt.mkdir(mode=0o700)
    mount = receipt / "mount"; mount.mkdir(mode=0o700)
    image = receipt / "candidate.sparseimage"
    manifest_file = draft / "manifest.json"
    research_root = Path(__file__).resolve().parents[1]
    source = command(["git", "-C", str(research_root), "rev-parse", "HEAD"])
    dirty = command(["git", "-C", str(research_root), "status", "--porcelain"])
    if source.returncode or dirty.returncode:
        raise RuntimeError("Could not identify the research source commit")
    report = {"schema": 1, "kind": "offline_protected_python_preflight",
              "task_id": args.task_id, "draft_manifest_sha256": sha(manifest_file),
              "source_commit": source.stdout.strip(),
              "source_tree_dirty": bool(dirty.stdout),
              "runner_sha256": sha(Path(__file__).resolve()),
              "model_requests": 0, "passed": False}
    try:
        entries = json.loads(manifest_file.read_text())
        matches = [item for item in entries if item["id"] == args.task_id]
        if len(matches) != 1:
            raise RuntimeError("Task ID missing or duplicated in manifest")
        entry = matches[0]
        report["retired_from_holdout"] = bool(entry.get("retirement_reason"))
        report["scientific_flags"] = entry.get("scientific_flags", [])
        grader_python = Path(sys.executable).resolve()
        report["grader_python_version"] = platform.python_version()
        report["grader_python_sha256"] = sha(grader_python)
        report["grader_interpreter_matches"] = (
            entry.get("grader_python_version") == report["grader_python_version"]
            and entry.get("grader_python_sha256") == report["grader_python_sha256"])
        if not report["grader_interpreter_matches"]:
            raise RuntimeError("Trusted grader interpreter differs from the frozen task validation")
        seed = draft / "tasks" / args.task_id / "seed"
        prompt = draft / "tasks" / args.task_id / "prompt.md"
        oracle = draft / "private" / "oracles" / (args.task_id + ".py")
        harness = draft / "private" / "harness.py"
        boundary = Path(inspect.getfile(background_boundary)).resolve()
        validation = draft / "private" / "validations" / (args.task_id + ".json")
        reference = draft / "private" / "solutions" / (args.task_id + ".patch")
        partial = draft / "private" / "partials" / (args.task_id + ".patch")
        paths = {"prompt_sha256": prompt, "oracle_sha256": oracle,
                 "harness_sha256": harness, "boundary_source_sha256": boundary,
                 "validation_output_sha256": validation,
                 "reference_sha256": reference, "partial_sha256": partial}
        report["input_hashes_match"] = (all(sha(path) == entry[key] for key, path in paths.items())
            and hashlib.sha256(oracle.read_bytes() + harness.read_bytes() + boundary.read_bytes()).hexdigest()
                == entry["grader_sha256"])
        report["executed_boundary_sha256"] = sha(boundary)
        expected_validation = json.loads(validation.read_text())
        original_oracle = re.search(r'File "([^"]+/private/oracles/[^"]+)"',
                                    expected_validation["seed"]["stderr"])
        if not original_oracle:
            raise RuntimeError("Frozen validation lacks its oracle path")
        original_draft = Path(original_oracle.group(1)).parents[2]
        report["validation_hashes_match"] = all(
            hashlib.sha256(expected_validation[name]["stderr"].encode()).hexdigest()
                == entry["validation"][name]["stderr_sha256"]
            and expected_validation[name]["stdout"] == entry["validation"][name]["stdout"]
            for name in ("seed", "reference", "partial"))
        head = command(["git", "-C", str(seed), "rev-parse", "HEAD"])
        status = command(["git", "-C", str(seed), "status", "--porcelain"])
        report["base_matches"] = (head.returncode == 0 and status.returncode == 0
                                  and head.stdout.strip() == entry["base_sha"]
                                  and status.stdout == "")
        report["seed_symlinks_absent"] = all(not path.is_symlink() for path in seed.rglob("*")
                                              if ".git" not in path.parts)
        if not all(report[key] for key in ("input_hashes_match", "validation_hashes_match",
                                       "base_matches", "seed_symlinks_absent")):
            raise RuntimeError("Task identity or seed preflight failed")
        created = command(["hdiutil", "create", "-size", "512m", "-type", "SPARSE",
                           "-fs", "APFS", "-volname", "KRYNPythonCandidate", str(image)])
        if created.returncode:
            raise RuntimeError("Candidate image creation failed: " + created.stderr[:200])
        attached = command(["hdiutil", "attach", "-nobrowse", "-noverify",
                            "-mountpoint", str(mount), str(image)])
        if attached.returncode or not mount_active(receipt, mount):
            raise RuntimeError("Candidate image attachment failed: " + attached.stderr[:200])
        devices = re.findall(r"/dev/disk\d+(?:s\d+)?", attached.stdout)
        private = mount / "private"; private.mkdir(mode=0o700)
        workspace = mount / "workspace"
        clone = command(["git", "clone", "--no-hardlinks", "-q", str(seed), str(workspace)])
        if clone.returncode:
            raise RuntimeError("Seed clone failed: " + clone.stderr[:200])
        if command(["git", "-C", str(workspace), "remote", "remove", "origin"]).returncode:
            raise RuntimeError("Could not remove source remote from candidate checkout")
        dependency_checks = {}
        tool_path, tool_dependencies, tool_manifest = benchmark_tools(args.tool_venv)
        report["benchmark_tool_path"] = str(tool_path) if tool_path else None
        report["benchmark_tool_manifest"] = tool_manifest
        for arm in ("native", "kryn"):
            _, _, dependencies = configuration(
                workspace, workspace / ".git" / "preflight-state", arm,
                "http://127.0.0.1:19876/v1")
            dependency_checks[arm] = all(
                not (draft == path or draft.is_relative_to(path) or path.is_relative_to(draft))
                for path in (Path(item).resolve() for item in dependencies + tool_dependencies))
        report["code_only_dependencies_exclude_draft"] = dependency_checks
        report["grader_dependencies_exclude_draft"] = all(
            not (draft == path or draft.is_relative_to(path) or path.is_relative_to(draft))
            for path in (Path(item).resolve() for item in
                         (sys.executable, sys.prefix, sys.base_prefix, boundary)))
        report["grader_device_separate"] = workspace.stat().st_dev != oracle.stat().st_dev
        report["reference_device_separate"] = workspace.stat().st_dev != reference.stat().st_dev
        draft_paths = list(draft.rglob("*"))
        report["draft_files_separate"] = (
            all(not path.is_symlink() for path in draft_paths) and
            all(path.stat().st_dev != workspace.stat().st_dev
                for path in draft_paths if path.is_file()))
        # A hidden file with one link cannot be aliased inside any readable
        # host-volume dependency, including the separately pinned tool venv.
        report["hidden_file_hardlinks_absent"] = all(
            path.stat().st_nlink == 1 for path in draft_paths
            if not path.is_symlink() and path.is_file())
        report["answer_aliases_impossible"] = {}
        for label, hidden in (("reference", reference), ("partial", partial),
                              ("validation", validation)):
            alias = workspace / ("hidden-" + label + "-hardlink")
            try:
                os.link(hidden, alias)
            except OSError as error:
                report["answer_aliases_impossible"][label] = error.errno == errno.EXDEV
            else:
                report["answer_aliases_impossible"][label] = False
                alias.unlink()
        (workspace / "visible.txt").write_text("candidate-visible")
        report["boundary"] = probe(workspace, private, oracle, image,
                                   devices[-1] if devices else None, receipt)
        if all(report["boundary"].values()):
            report["server_boundary"] = server_probe(
                workspace, receipt / "native-server.log", oracle, oracle.read_text(), private,
                tool_venv=args.tool_venv,
                extra_hidden=(("reference", reference), ("manifest", manifest_file)))
            report["server_boundary_native"] = server_probe(
                workspace, receipt / "native-control-server.log", oracle,
                oracle.read_text(), private, arm="native", tool_venv=args.tool_venv,
                extra_hidden=(("reference", reference), ("manifest", manifest_file)))
        for name in ("visible.txt", "oracle-symlink", "oracle-hardlink",
                     "candidate-hardlink", "copied"):
            (workspace / name).unlink(missing_ok=True)
        candidate_status = command(["git", "-C", str(workspace), "status", "--porcelain=v1",
                                    "--untracked-files=all", "--ignored"])
        report["candidate_clean_after_probe"] = (candidate_status.returncode == 0
                                                  and candidate_status.stdout == "")
        if not (report["grader_device_separate"] and report["reference_device_separate"]
                and report["draft_files_separate"]
                and report["hidden_file_hardlinks_absent"]
                and all(report["answer_aliases_impossible"].values())
                and all(report["code_only_dependencies_exclude_draft"].values())
                and report["grader_dependencies_exclude_draft"]
                and all(report["boundary"].values()) and report["candidate_clean_after_probe"]):
            raise RuntimeError("Real task boundary preflight failed")
        if not all(report.get("server_boundary", {}).values()):
            raise RuntimeError("Real task native OpenCode server boundary failed")
        if not all(report.get("server_boundary_native", {}).values()):
            raise RuntimeError("Real task native control server boundary failed")
        report["seed"] = grade(oracle, workspace, private, boundary, draft,
                               receipt / "seed-grader.log")
        if command(["git", "-C", str(workspace), "apply", str(reference)]).returncode:
            raise RuntimeError("Reference patch did not apply")
        report["reference"] = grade(oracle, workspace, private, boundary, draft,
                                    receipt / "reference-grader.log")
        if (command(["git", "-C", str(workspace), "reset", "--hard",
                     entry["base_sha"]]).returncode or
                command(["git", "-C", str(workspace), "clean", "-fd"]).returncode):
            raise RuntimeError("Could not reset reference checkout to the frozen seed")
        if command(["git", "-C", str(workspace), "apply", str(partial)]).returncode:
            raise RuntimeError("Partial patch did not apply")
        report["partial"] = grade(oracle, workspace, private, boundary, draft,
                                  receipt / "partial-grader.log")
        report["control_evidence_match"] = all(
            report[name]["exit"] == entry["validation"][name]["exit_code"]
            and report[name]["stdout_sha256"] == hashlib.sha256(
                entry["validation"][name]["stdout"].encode()).hexdigest()
            and report[name]["stderr_sha256"] == hashlib.sha256(
                expected_validation[name]["stderr"].replace(
                    str(original_draft), "<DRAFT_ROOT>").encode()).hexdigest()
            for name in ("seed", "reference", "partial"))
        report["controls_pass"] = (report["seed"]["exit"] != 0 and
                                   report["reference"]["exit"] == 0 and
                                   report["partial"]["exit"] != 0 and
                                   report["control_evidence_match"] and
                                   all(report[name]["output_bounded"] and
                                       not report[name]["timed_out"]
                                       for name in ("seed", "reference", "partial")))
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    finally:
        detach_ok = True
        if mount_active(receipt, mount):
            try:
                detach_ok = command(["hdiutil", "detach", str(mount)]).returncode == 0
            except Exception:
                detach_ok = False
        try:
            info = command(["hdiutil", "info"])
            image_absent = info.returncode == 0 and str(image) not in info.stdout
        except Exception:
            image_absent = False
        report["detached"] = detach_ok and not mount_active(receipt, mount) and image_absent
        if report["detached"] and image.exists():
            image.unlink()
        report["mechanics_passed"] = bool(not report["source_tree_dirty"] and
                                          report.get("controls_pass") and
                                          all(report.get("server_boundary", {}).values()) and
                                          report.get("server_boundary") and report["detached"]
                                          and all(report.get("server_boundary_native", {}).values())
                                          and report.get("server_boundary_native")
                                          and "error" not in report)
        report["passed"] = bool(report["mechanics_passed"] and
                                not report.get("retired_from_holdout") and
                                not report.get("scientific_flags"))
        if report["source_tree_dirty"]:
            report["admission_note"] = "Research source tree is dirty; controls are development-only"
        (receipt / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report.get(key) for key in ("task_id", "passed", "mechanics_passed",
                                                  "retired_from_holdout", "scientific_flags",
                                                  "controls_pass", "detached", "admission_note", "error")},
                     sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
