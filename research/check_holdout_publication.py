#!/usr/bin/env python3
"""Fail before publication if private task identifiers enter a public Git tree."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile


def git(repo, *args):
    result = subprocess.run(("git", "-C", str(repo), *args),
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git failed")
    return result.stdout


def grep_paths(repo, patterns, *, cached):
    with tempfile.NamedTemporaryFile(mode="w", prefix="kryn-private-patterns-",
                                     dir="/private/tmp", delete=True) as stream:
        stream.write("\n".join(patterns) + "\n")
        stream.flush()
        argv = ["git", "-C", str(repo), "grep", "-I", "-l", "-F", "-f", stream.name]
        if cached:
            argv.append("--cached")
        result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "git grep failed")
    return sorted(set(result.stdout.splitlines()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roster", type=Path, help="private roster JSON, outside the public repo")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pr-text", type=Path, required=True,
                        help="proposed PR title and body in a local text file")
    parser.add_argument("--report", type=Path,
                        help="optional new private JSON receipt with matching paths")
    args = parser.parse_args()
    repo = args.repo.resolve()
    roster_path = args.roster.resolve()
    if roster_path.is_relative_to(repo):
        parser.error("Private roster must live outside the public repository")
    if args.report and (args.report.resolve().is_relative_to(repo) or args.report.exists()):
        parser.error("Report must be a new file outside the public repository")
    if not args.pr_text.is_file():
        parser.error("PR title/body file is required")
    roster = json.loads(roster_path.read_text())
    rows = roster["tasks"]
    if not isinstance(rows, list) or not rows:
        parser.error("Roster must contain tasks")
    patterns = set()
    for row in rows:
        task_id = row["id"]
        if not isinstance(task_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{5,100}", task_id):
            parser.error("Each task needs a distinctive slug")
        patterns.add(task_id)
        for field in ("prompt_sha256", "grader_sha256", "seed_commit"):
            value = row.get(field)
            if value:
                if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40,64}", value):
                    parser.error("Invalid private identity hash")
                patterns.add(value)
    if len({row["id"] for row in rows}) != len(rows):
        parser.error("Task IDs must be unique")
    patterns = sorted(patterns)
    tracked = grep_paths(repo, patterns, cached=False)
    staged = grep_paths(repo, patterns, cached=True)
    tracked_names = [name for name in git(repo, "ls-files", "-z").split("\0") if name]
    path_names = [name for name in tracked_names
                  if any(pattern in name for pattern in patterns)]
    proposed_pr = args.pr_text.read_text()
    pr_hits = sum(pattern in proposed_pr for pattern in patterns)
    commit_text = git(repo, "log", "--format=%B", "--all")
    commit_hits = sum(pattern in commit_text for pattern in patterns)
    result = {
        "schema": 1,
        "kind": "private_holdout_publication_preflight",
        "task_count": len(rows),
        "tracked_matching_paths": tracked,
        "staged_matching_paths": staged,
        "matching_path_names": path_names,
        "pr_text_matching_patterns": pr_hits,
        "commit_message_matching_patterns": commit_hits,
        "passed": not (tracked or staged or path_names or pr_hits or commit_hits),
        "limitations": [
            "Exact task IDs and hashes only; paraphrases require human review",
            "Current tracked/index trees and commit messages, not all historical blobs or remote PR text",
        ],
    }
    if args.report:
        with args.report.open("x") as stream:
            stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        args.report.chmod(0o600)
    print(json.dumps({
        "task_count": len(rows),
        "passed": result["passed"],
        "tracked_matching_paths": len(tracked),
        "staged_matching_paths": len(staged),
        "matching_path_names": len(path_names),
        "pr_text_matching_patterns": pr_hits,
        "commit_message_matching_patterns": commit_hits,
    }, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
