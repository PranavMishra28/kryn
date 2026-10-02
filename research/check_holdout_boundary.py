#!/usr/bin/env python3
"""Preflight the macOS read boundary before any protected local-model trial."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from native_client import background_boundary


def main():
    with tempfile.TemporaryDirectory(prefix="kryn-holdout-boundary-", dir="/private/tmp") as tmp:
        root = Path(tmp).resolve()
        workspace, private, grader = (root / name for name in ("workspace", "private", "grader"))
        for folder in (workspace, private, grader):
            folder.mkdir(mode=0o700)
        visible = workspace / "visible.txt"
        hidden = grader / "oracle.txt"
        visible.write_text("candidate input")
        hidden.write_text("hidden oracle")
        alias = workspace / "oracle-alias.txt"
        alias.symlink_to(hidden)
        prefix = background_boundary(workspace, private, [], None)

        def read(path):
            return subprocess.run(prefix + ["/bin/cat", str(path)], cwd=workspace,
                                  capture_output=True, text=True, timeout=5)

        allowed, blocked, indirect = (read(path) for path in (visible, hidden, alias))
        passed = (allowed.returncode == 0 and allowed.stdout == "candidate input"
                  and blocked.returncode != 0 and indirect.returncode != 0)
        print(json.dumps({"boundary_preflight_passed": passed,
                          "workspace_read": allowed.returncode,
                          "grader_read": blocked.returncode,
                          "grader_symlink_read": indirect.returncode}))
        raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
