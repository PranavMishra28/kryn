#!/usr/bin/env python3
"""Fail before publication if private task identifiers enter a public Git tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def git(repo, *args):
    result = subprocess.run(("git", "-C", str(repo), *args),
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git failed")
    return result.stdout


def grep_paths(repo, patterns, *, cached=False, revision=None):
    with tempfile.NamedTemporaryFile(mode="w", prefix="kryn-private-patterns-",
                                     dir="/private/tmp", delete=True) as stream:
        stream.write("\n".join(patterns) + "\n")
        stream.flush()
        argv = ["git", "-C", str(repo), "grep", "-a", "-l", "-F", "-f", stream.name]
        if cached:
            argv.append("--cached")
        if revision:
            argv.append(revision)
        argv.append("--")
        result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "git grep failed")
    return sorted(set(result.stdout.splitlines()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roster", type=Path, help="private roster JSON, outside the public repo")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--roster-sha256", required=True,
                        help="digest from the independently pinned private roster receipt")
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
    if not re.fullmatch(r"[0-9a-f]{64}", args.roster_sha256):
        parser.error("Expected a 64-character private roster digest")
    roster_bytes = roster_path.read_bytes()
    if hashlib.sha256(roster_bytes).hexdigest() != args.roster_sha256:
        parser.error("Private roster differs from its independently pinned digest")
    roster = json.loads(roster_bytes)
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
            length = 40 if field == "seed_commit" else 64
            if not isinstance(value, str) or not re.fullmatch(rf"[0-9a-f]{{{length}}}", value):
                parser.error(f"Each task needs a valid {field}")
            patterns.add(value)
    if len({row["id"] for row in rows}) != len(rows):
        parser.error("Task IDs must be unique")
    patterns = sorted(patterns)
    tracked = grep_paths(repo, patterns, cached=False)
    staged = grep_paths(repo, patterns, cached=True)
    tracked_names = [name for name in git(repo, "ls-files", "-z").split("\0") if name]
    path_names = [name for name in tracked_names
                  if any(pattern in name for pattern in patterns)]
    base = git(repo, "rev-parse", "--verify", "refs/remotes/origin/main^{commit}").strip()
    remote_main = git(repo, "ls-remote", "--exit-code", "origin", "refs/heads/main").splitlines()
    if len(remote_main) != 1 or remote_main[0].split() != [base, "refs/heads/main"]:
        parser.error("Local origin/main differs from public main; fetch before checking")
    ancestor = subprocess.run(("git", "-C", str(repo), "merge-base", "--is-ancestor",
                               base, "HEAD"), capture_output=True)
    if ancestor.returncode:
        parser.error("Public base must be an ancestor of HEAD")
    published_commits = git(repo, "rev-list", "--reverse", f"{base}..HEAD").splitlines()
    history_paths = []
    history_names = []
    for commit in published_commits:
        history_paths.extend(grep_paths(repo, patterns, revision=commit))
        history_names.extend(name for name in git(repo, "ls-tree", "-r", "--name-only", commit).splitlines()
                             if any(pattern in name for pattern in patterns))
    proposed_pr = args.pr_text.read_text()
    pr_hits = sum(pattern in proposed_pr for pattern in patterns)
    commit_text = git(repo, "log", "--format=%B", f"{base}..HEAD")
    commit_hits = sum(pattern in commit_text for pattern in patterns)
    result = {
        "schema": 1,
        "kind": "private_holdout_publication_preflight",
        "task_count": len(rows),
        "roster_sha256_verified": True,
        "public_base_verified": True,
        "tracked_matching_paths": tracked,
        "staged_matching_paths": staged,
        "matching_path_names": path_names,
        "historical_matching_paths": sorted(set(history_paths)),
        "historical_matching_path_names": sorted(set(history_names)),
        "pr_text_matching_patterns": pr_hits,
        "commit_message_matching_patterns": commit_hits,
        "passed": not (tracked or staged or path_names or history_paths or history_names
                       or pr_hits or commit_hits),
        "limitations": [
            "Exact task IDs and hashes only; paraphrases require human review",
            "A matching roster digest does not prove the pinned roster was complete",
            "New branch commits, current tracked/index trees and proposed PR text; not older public history or remote PR edits",
        ],
    }
    if args.report:
        with os.fdopen(os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
            stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "task_count": len(rows),
        "passed": result["passed"],
        "tracked_matching_paths": len(tracked),
        "staged_matching_paths": len(staged),
        "matching_path_names": len(path_names),
        "historical_matching_paths": len(history_paths),
        "historical_matching_path_names": len(history_names),
        "pr_text_matching_patterns": pr_hits,
        "commit_message_matching_patterns": commit_hits,
    }, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
