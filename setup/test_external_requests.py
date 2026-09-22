"""Offline regressions for the optional evaluator's Git and import boundaries."""
import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


class ExternalRequestsTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "external_requests_test_adapter",
            Path(__file__).resolve().parents[1] / "evals/external_requests.py")
        self.adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.adapter)
        self.temporary = tempfile.TemporaryDirectory(prefix="kryn-external-eval-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.adapter.configure(self.root / "state")

    @unittest.skipUnless(os.name == "posix" and shutil.which("git"), "Requires POSIX Git")
    def test_prepare_ignores_hostile_git_hooks_and_redirects(self):
        m = self.adapter
        m.UPSTREAM.mkdir(parents=True)
        (m.UPSTREAM / "source.txt").write_text("original source\n")
        m.ORACLE.mkdir()
        (m.ORACLE / "problem.txt").write_text("Exact task\n")
        home, hooks, foreign = [self.root / name for name in ("home", "hooks", "foreign")]
        for folder in (home, hooks, foreign):
            folder.mkdir()
        (foreign / "untouched").write_text("original\n")
        marker = self.root / "hook-executed"
        hook = hooks / "pre-commit"
        hook.write_text("#!/bin/sh\ntouch " + shlex.quote(str(marker)) + "\ntouch HOOK_INJECTION\n")
        hook.chmod(0o700)
        config = home / ".gitconfig"
        config.write_text('[core]\n\thooksPath = "' + str(hooks) + '"\n')
        hostile = {"HOME": str(home), "GIT_CONFIG_GLOBAL": str(config),
            "GIT_DIR": str(foreign / ".git"), "GIT_WORK_TREE": str(foreign),
            "GIT_INDEX_FILE": str(foreign / "index"), "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": str(hooks),
            "GIT_CONFIG_PARAMETERS": "'core.hooksPath=" + str(hooks) + "'"}
        # This boundary test needs no dataset, evaluator venv or downloads.
        with patch.dict(os.environ, hostile), patch.object(m, "verify_inputs"):
            workspace = m.prepare("hostile-git")
        self.assertFalse(marker.exists(), "An inherited hook must never execute")
        self.assertEqual(list(foreign.iterdir()), [foreign / "untouched"])
        self.assertEqual((foreign / "untouched").read_text(), "original\n")
        self.assertEqual({str(p.relative_to(workspace)): p.read_text() for p in workspace.rglob("*")
                          if p.is_file() and ".git" not in p.relative_to(workspace).parts},
                         {"source.txt": "original source\n", "TASK.md": "Exact task\n"})
        independent_env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": str(home),
                           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=workspace, env=independent_env, text=True, capture_output=True, check=True, timeout=10)
        self.assertEqual(status.stdout, "")

    def test_stalled_candidate_import_times_out_before_pytest(self):
        target = self.root / "candidate"
        requests = target / "requests"
        requests.mkdir(parents=True)
        (requests / "__init__.py").write_text("import time\ntime.sleep(60)\n")
        out = self.root / "grade"
        out.mkdir()
        self.adapter.PYTHON = Path(sys.executable)
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.adapter.run_checks(target, out)
        elapsed = time.monotonic() - started
        self.assertEqual(caught.exception.timeout, 15)
        self.assertGreaterEqual(elapsed, 14)
        self.assertLess(elapsed, 30, "Import timeout should kill and reap the stalled child")
        self.assertEqual(list(out.iterdir()), [], "Pytest must not run after a stalled import")


if __name__ == "__main__":
    unittest.main()
