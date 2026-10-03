#!/usr/bin/env python3
"""No-model read-only official-source channel canary on a candidate APFS volume."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from agent_grade_barrier import clean_clone, create_volume, detach, image_entry
from check_holdout_boundary import probe, server_probe
from run_external_patch import configuration

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COMMIT = "2bd66de8cea336061c9ea060c9b37385136e6ab3"
EXPECTED_SOURCE_SHA = "418bdf281d74a89c7dabedc4af53a6f7b286f2416e7670d9cc71453db08d8640"
EXPECTED_SOURCE_BYTES = 10088


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(argv, *, env=None):
    return subprocess.run(argv, env=env, capture_output=True, text=True,
                          timeout=20, close_fds=True)


def fixture(output):
    seed = output / "seed"
    seed.mkdir(mode=0o700)
    if command(["git", "init", "--initial-branch=main", "-q", str(seed)]).returncode:
        raise RuntimeError("Public seed Git init failed")
    (seed / "visible.txt").write_text("candidate-visible")
    if command(["git", "-C", str(seed), "add", "visible.txt"]).returncode:
        raise RuntimeError("Public seed Git add failed")
    env = os.environ.copy()
    env.update(GIT_AUTHOR_NAME="KRYN public source canary", GIT_AUTHOR_EMAIL="canary@example.invalid",
               GIT_COMMITTER_NAME="KRYN public source canary", GIT_COMMITTER_EMAIL="canary@example.invalid",
               GIT_AUTHOR_DATE="2026-10-03T00:00:00+0000",
               GIT_COMMITTER_DATE="2026-10-03T00:00:00+0000")
    if command(["git", "-C", str(seed), "commit", "-qm", "public source seed"], env=env).returncode:
        raise RuntimeError("Public seed Git commit failed")
    return seed


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tool-venv", required=True, type=Path)
    args = parser.parse_args()
    source_dir, output = args.source_dir.absolute(), args.output.absolute()
    if (source_dir != source_dir.resolve() or not source_dir.is_dir() or
            source_dir.stat().st_uid != os.geteuid() or source_dir.stat().st_mode & 0o077 or
            output.parent != Path("/private/tmp") or output.exists()):
        parser.error("Use the canonical owner-only source snapshot and a fresh /private/tmp output")
    source, hidden = source_dir / "github-pagination.md", source_dir / "SOURCE.json"
    manifest = json.loads(hidden.read_text())
    if (not source.is_file() or source != source.resolve() or
            not hidden.is_file() or hidden != hidden.resolve() or
            len(source.read_bytes()) != EXPECTED_SOURCE_BYTES or
            sha(source) != EXPECTED_SOURCE_SHA or
            manifest.get("source_commit") != EXPECTED_COMMIT or
            manifest.get("sha256") != EXPECTED_SOURCE_SHA or
            manifest.get("bytes") != EXPECTED_SOURCE_BYTES):
        parser.error("Official source snapshot identity changed")
    output.mkdir(mode=0o700)
    source_head = command(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    source_status = command(["git", "-C", str(ROOT), "status", "--porcelain"])
    report = {"schema": 1, "kind": "official_source_no_model_gateway_preflight",
              "research_source_commit": source_head.stdout.strip(),
              "research_tree_dirty": bool(source_status.stdout),
              "runner_sha256": sha(Path(__file__)),
              "snapshot_sha256": EXPECTED_SOURCE_SHA,
              "snapshot_provenance_sha256": sha(hidden),
              "model_requests": 0, "protected_status": False, "passed": False}
    volume = None
    try:
        if source_head.returncode or source_status.returncode or report["research_tree_dirty"]:
            raise RuntimeError("Research source must be a clean commit")
        seed = fixture(output)
        base = command(["git", "-C", str(seed), "rev-parse", "HEAD"])
        if base.returncode:
            raise RuntimeError("Public seed commit missing")
        report["seed_commit"] = base.stdout.strip()
        volume = create_volume(output, "source-candidate")
        workspace, private = volume.mount / "workspace", volume.mount / "private"
        private.mkdir(mode=0o700)
        clean_clone(seed, workspace, report["seed_commit"])
        from native_client import background_boundary
        baseline = command(background_boundary(workspace, private, [], None) +
                           ["/bin/cat", str(source)])
        report["baseline_source_read_denied"] = (
            baseline.returncode != 0 and baseline.stdout == "")
        prefix = background_boundary(workspace, private, [source], None)
        visible = command(prefix + ["/bin/cat", str(source)])
        blocked_write = command(prefix + ["/bin/sh", "-c", "printf tampered >> \"$1\"",
                                          "sh", str(source)])
        hidden_read = command(prefix + ["/bin/cat", str(hidden)])
        hidden_list = command(prefix + ["/bin/ls", "-a", str(source_dir)])
        report["source_direct_exact_read"] = (visible.returncode == 0 and
                                              visible.stdout.encode() == source.read_bytes())
        report["source_direct_write_denied"] = blocked_write.returncode != 0
        report["source_direct_sibling_denied"] = (hidden_read.returncode != 0 and
                                                   hidden_read.stdout == "")
        report["source_direct_parent_listing_denied"] = (
            hidden_list.returncode != 0 and hidden_list.stdout == "")
        report["source_and_hidden_separate_device"] = (
            all(path.stat().st_dev != workspace.stat().st_dev for path in (source, hidden)))
        report["source_hardlink_impossible"] = False
        try:
            os.link(source, workspace / "source-hardlink")
        except OSError as error:
            report["source_hardlink_impossible"] = error.errno == errno.EXDEV
        devices = [item.get("dev-entry") for item in
                   image_entry(volume.image).get("system-entities", [])]
        device = next((item for item in reversed(devices)
                       if item and Path(item).exists()), None)
        report["hidden_boundary"] = probe(workspace, private, hidden,
                                          volume.image, device, output)
        configurations = {}
        report["server_boundary"] = {}
        for arm in ("native", "kryn"):
            config, _, _ = configuration(workspace, workspace / ".git" / arm, arm,
                                         "http://127.0.0.1:19876/v1")
            configurations[arm] = {"mcp": config["mcp"],
                                   "permissions": config["permissions"],
                                   "agent_permissions": {name: agent.get("permissions", [])
                                       for name, agent in config.get("agents", {}).items()}}
            report["server_boundary"][arm] = server_probe(
                workspace, output / (arm + "-server.log"), hidden,
                hidden.read_text(), private, arm=arm, tool_venv=args.tool_venv,
                source_file=source)
        report["paired_tool_permission_config_equal"] = (
            configurations["native"] == configurations["kryn"])
        for name in ("oracle-symlink", "oracle-hardlink", "candidate-hardlink",
                     "source-hardlink", "copied"):
            (workspace / name).unlink(missing_ok=True)
        status = command(["git", "-C", str(workspace), "status", "--porcelain=v1",
                          "--untracked-files=all", "--ignored"])
        report["candidate_clean_after_probe"] = status.returncode == 0 and not status.stdout
        report["source_unchanged"] = sha(source) == EXPECTED_SOURCE_SHA
        report["provenance_unchanged"] = sha(hidden) == report["snapshot_provenance_sha256"]
        required = (
                    "baseline_source_read_denied", "source_direct_exact_read",
                    "source_direct_write_denied", "source_direct_sibling_denied",
                    "source_direct_parent_listing_denied", "source_and_hidden_separate_device",
                    "source_hardlink_impossible", "paired_tool_permission_config_equal",
                    "candidate_clean_after_probe", "source_unchanged", "provenance_unchanged")
        if not (all(report.get(key) for key in required)
                and all(report["hidden_boundary"].values())
                and all(all(checks.values()) for checks in report["server_boundary"].values())):
            raise RuntimeError("Read-only source gateway canary failed")
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if volume is not None:
            try:
                detach(volume)
                report["detached"] = True
            except BaseException as error:
                report["detached"] = False
                report["detach_error"] = type(error).__name__ + ": " + str(error)
        report["wall_seconds"] = round(time.monotonic() - started, 3)
        report["passed"] = bool(report.get("detached") and "error" not in report)
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(output), "passed": report["passed"],
                      "detached": report.get("detached"), "error": report.get("error")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
