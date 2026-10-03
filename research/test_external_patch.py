"""The external adapter refuses dirty or ambiguous benchmark workspaces."""
from pathlib import Path
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

from unittest.mock import patch

from run_external_patch import (PatchBudgetExceeded, benchmark_tools, collect_patch,
                                drive, prepare, stop_browser_broker)


class ExternalPreflightTest(unittest.TestCase):
    def test_browser_cleanup_requires_exact_container_absence_and_closed_listener(self):
        child = SimpleNamespace(poll=lambda: None)
        broker = {"container": "kryn-ui-test-exact", "port": 65431}
        absent = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        unknown = subprocess.CompletedProcess([], 1, stdout="", stderr="daemon unavailable")
        with patch("ui_gateway.preflight.stop_group", return_value=True), patch(
                "run_external_patch.subprocess.run", return_value=absent) as docker:
            self.assertTrue(stop_browser_broker(child, broker))
            self.assertEqual(docker.call_args.args[0][4], "name=" + broker["container"])
        with patch("ui_gateway.preflight.stop_group", return_value=True), patch(
                "run_external_patch.subprocess.run", return_value=unknown), patch(
                "run_external_patch.time.sleep"):
            with self.assertRaisesRegex(RuntimeError, "absence could not be proved"):
                stop_browser_broker(child, broker)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            broker["port"] = listener.getsockname()[1]
            with patch("ui_gateway.preflight.stop_group", return_value=True), patch(
                    "run_external_patch.subprocess.run", return_value=absent):
                with self.assertRaisesRegex(RuntimeError, "listener remains reachable"):
                    stop_browser_broker(child, broker)
        with patch("ui_gateway.preflight.stop_group", return_value=False), patch(
                "run_external_patch.subprocess.run", return_value=absent):
            self.assertFalse(stop_browser_broker(child, broker))

    def test_patch_includes_new_files_without_mutating_candidate_index(self):
        with tempfile.TemporaryDirectory(prefix="kryn-external-test-", dir="/private/tmp") as tmp:
            root = Path(tmp).resolve()
            workspace = root / "workspace"
            workspace.mkdir()
            subprocess.run(["git", "init", "-q", str(workspace)], check=True)
            (workspace / "source.py").write_text("print(1)\n")
            subprocess.run(["git", "-C", str(workspace), "add", "source.py"], check=True)
            subprocess.run(["git", "-C", str(workspace), "-c", "user.name=Research",
                            "-c", "user.email=research@example.invalid", "commit", "-qm", "seed"], check=True)
            base = subprocess.check_output(["git", "-C", str(workspace), "rev-parse", "HEAD"],
                                           text=True).strip()
            before = hashlib.sha256((workspace / ".git/index").read_bytes()).digest()
            (workspace / "source.py").write_text("print(2)\n")
            (workspace / "new test.py").write_text("assert True\n")
            evidence = root / "evidence"; evidence.mkdir()
            private = root / "private"; private.mkdir()
            with patch("run_external_patch.background_boundary", return_value=[]):
                patch_file, names, size, digest = collect_patch(
                    workspace, base, evidence, private=private, dependencies=[],
                    git_binary=Path(shutil.which("git")), tool_path=None,
                    cancelled=lambda: False)
            patch_bytes = patch_file.read_bytes()
            self.assertEqual(names, ["new test.py"])
            self.assertEqual(size, len(patch_bytes))
            self.assertEqual(digest, hashlib.sha256(patch_bytes).hexdigest())
            self.assertIn(b"new file mode", patch_bytes)
            self.assertIn(b"+assert True", patch_bytes)
            self.assertIn(b"+print(2)", patch_bytes)
            self.assertEqual(before, hashlib.sha256((workspace / ".git/index").read_bytes()).digest())
            self.assertFalse(list(private.glob("patch-index-*")))

    def test_patch_rehashes_same_size_tracked_edit_with_stale_index_stat(self):
        with tempfile.TemporaryDirectory(prefix="kryn-external-test-", dir="/private/tmp") as tmp:
            root = Path(tmp).resolve()
            workspace = root / "workspace"; workspace.mkdir()
            subprocess.run(["git", "init", "-q", str(workspace)], check=True)
            source = workspace / "source.py"
            source.write_text("value = 1\n")
            subprocess.run(["git", "-C", str(workspace), "config", "core.trustctime",
                            "false"], check=True)
            subprocess.run(["git", "-C", str(workspace), "add", "source.py"], check=True)
            subprocess.run(["git", "-C", str(workspace), "-c", "user.name=Research",
                            "-c", "user.email=research@example.invalid", "commit", "-qm",
                            "seed"], check=True)
            base = subprocess.check_output(["git", "-C", str(workspace), "rev-parse",
                                            "HEAD"], text=True).strip()
            before = source.stat()
            source.write_text("value = 2\n")
            # Recreate the equal-size/equal-mtime cache collision that can
            # occur immediately after cloning a task checkout.
            os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
            staged_new = workspace / "new_test.py"
            staged_new.write_text("assert True\n")
            # A candidate index can explicitly suppress that same-size edit;
            # the private capture index must still describe the worktree.
            subprocess.run(["git", "-C", str(workspace), "update-index",
                            "--assume-unchanged", "source.py"], check=True)
            self.assertNotIn("source.py", subprocess.check_output(
                ["git", "-C", str(workspace), "diff", "--name-only", base], text=True))
            subprocess.run(["git", "-C", str(workspace), "add", "-N", "new_test.py"],
                           check=True)
            evidence = root / "evidence"; evidence.mkdir()
            private = root / "private"; private.mkdir()
            with patch("run_external_patch.background_boundary", return_value=[]):
                patch_file, _, _, _ = collect_patch(
                    workspace, base, evidence, private=private, dependencies=[],
                    git_binary=Path(shutil.which("git")), tool_path=None,
                    cancelled=lambda: False)
            payload = patch_file.read_text()
            self.assertIn("+value = 2", payload)
            self.assertIn("+assert True", payload)

    def test_patch_budget_fails_closed_and_removes_partial_output(self):
        with tempfile.TemporaryDirectory(prefix="kryn-external-test-", dir="/private/tmp") as tmp:
            root = Path(tmp).resolve()
            workspace = root / "workspace"; workspace.mkdir()
            subprocess.run(["git", "init", "-q", str(workspace)], check=True)
            (workspace / "source.py").write_text("print(1)\n")
            subprocess.run(["git", "-C", str(workspace), "add", "source.py"], check=True)
            subprocess.run(["git", "-C", str(workspace), "-c", "user.name=Research",
                            "-c", "user.email=research@example.invalid", "commit", "-qm", "seed"], check=True)
            base = subprocess.check_output(["git", "-C", str(workspace), "rev-parse", "HEAD"],
                                           text=True).strip()
            (workspace / "large-new.py").write_bytes(b"x" * 4096)
            evidence = root / "evidence"; evidence.mkdir()
            private = root / "private"; private.mkdir()
            before = hashlib.sha256((workspace / ".git/index").read_bytes()).digest()
            with patch("run_external_patch.background_boundary", return_value=[]), patch(
                    "run_external_patch.PATCH_BUDGET", 1024):
                with self.assertRaises(PatchBudgetExceeded):
                    collect_patch(workspace, base, evidence, private=private, dependencies=[],
                                  git_binary=Path(shutil.which("git")), tool_path=None,
                                  cancelled=lambda: False)
            self.assertFalse((evidence / "model.patch").exists())
            self.assertFalse(list(private.glob("patch-index-*")))
            self.assertEqual(before, hashlib.sha256((workspace / ".git/index").read_bytes()).digest())

    @unittest.skipUnless(sys.platform == "darwin" and Path(
        "/Library/Developer/CommandLineTools/usr/bin/git").is_file(),
        "Requires the macOS research boundary and Command Line Tools")
    def test_candidate_git_filter_cannot_read_host_oracle_during_capture(self):
        with tempfile.TemporaryDirectory(prefix="kryn-external-test-", dir="/private/tmp") as tmp:
            root = Path(tmp).resolve()
            workspace = root / "workspace"; workspace.mkdir(mode=0o700)
            evidence = root / "evidence"; evidence.mkdir(mode=0o700)
            private = root / "private"; private.mkdir(mode=0o700)
            oracle = root / "oracle.txt"; oracle.write_text("synthetic-hidden-oracle-7736\n")
            git = ["/usr/bin/git", "-C", str(workspace)]
            subprocess.run(["/usr/bin/git", "init", "-q", str(workspace)], check=True)
            (workspace / "source.py").write_text("print(1)\n")
            subprocess.run(git + ["add", "source.py"], check=True)
            subprocess.run(git + ["-c", "user.name=Research", "-c",
                                  "user.email=research@example.invalid", "commit", "-qm", "seed"], check=True)
            base = subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()
            hook = workspace / "clean-filter.sh"
            hook.write_text("#!/bin/sh\nprintf fired > '" + str(workspace / "filter-fired") +
                            "'\n/bin/cat '" + str(oracle) + "' > '" + str(workspace / "leak") +
                            "' 2>/dev/null || :\n/bin/cat\n")
            hook.chmod(0o700)
            (workspace / ".gitattributes").write_text("source.py filter=probe\n")
            subprocess.run(git + ["config", "filter.probe.clean", str(hook)], check=True)
            (workspace / "source.py").write_text("print(2)\n")
            patch_file, _, _, _ = collect_patch(
                workspace, base, evidence, private=private, dependencies=[],
                git_binary=Path("/Library/Developer/CommandLineTools/usr/bin/git"),
                tool_path=None, cancelled=lambda: False)
            self.assertTrue((workspace / "filter-fired").is_file())
            self.assertEqual((workspace / "leak").read_bytes(), b"")
            self.assertTrue(patch_file.is_file())
            (workspace / "filter-fired").unlink()
            (workspace / "leak").unlink()
            prompt = root / "prompt.txt"; prompt.write_text("Change source.py")
            with self.assertRaisesRegex(ValueError, "clean base"):
                prepare(workspace, prompt, root / "new-evidence", base)
            self.assertTrue((workspace / "filter-fired").is_file())
            self.assertEqual((workspace / "leak").read_bytes(), b"")

    def test_finished_cli_cannot_silently_truncate_events(self):
        child = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdout.write('x' * 3000000)"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        try:
            cause, output, errors = drive(child, b"task", 30, lambda: False)
            self.assertEqual(cause, "output_budget")
            self.assertLessEqual(len(output), 2 * 1024**2 + 1)
            self.assertEqual(errors, b"")
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()
            child.stdout.close(); child.stderr.close()

    def test_benchmark_tool_dependencies_are_explicit(self):
        self.assertEqual(benchmark_tools(None), (None, [], None))
        with tempfile.TemporaryDirectory(prefix="kryn-external-test-", dir="/private/tmp") as tmp:
            venv = Path(tmp) / "venv"
            (venv / "bin").mkdir(parents=True)
            for name in ("pyvenv.cfg", "bin/python3", "bin/rg", "bin/git"):
                (venv / name).touch()
            with patch("run_external_patch.subprocess.check_output", side_effect=[
                "/private/tmp/python-base\n", "/private/tmp/venv/bin/rg:\n"
                "    /usr/local/opt/pcre2/lib/libpcre2-8.0.dylib (compatibility version 1.0.0)\n"
                "    /usr/lib/libSystem.B.dylib (compatibility version 1.0.0)\n",
                "[[\"pytest\", \"8.3.3\"]]\n"]), patch(
                    "run_external_patch.subprocess.run", return_value=subprocess.CompletedProcess(
                        [], 0, "pytest 8.3.3\n", "")):
                bin_path, dependencies, manifest = benchmark_tools(venv)
            self.assertEqual(bin_path, venv / "bin")
            self.assertEqual(dependencies[:2], [venv, Path("/private/tmp/python-base")])
            self.assertEqual(len(dependencies), 4)
            self.assertEqual(dependencies[2], venv / "bin/git")
            self.assertEqual(manifest["pytest_version"], "pytest 8.3.3")
            self.assertEqual(manifest["packages"], [["pytest", "8.3.3"]])
            with patch("run_external_patch.subprocess.run", return_value=subprocess.CompletedProcess(
                    [], 1, "", "No module named pytest")):
                with self.assertRaisesRegex(RuntimeError, "lacks runnable pytest"):
                    benchmark_tools(venv)
            (venv / "bin/python3").unlink()
            (venv / "bin/python3").symlink_to("/usr/bin/python3")
            with self.assertRaisesRegex(ValueError, "Python, rg and Git"):
                benchmark_tools(venv)

    def test_exact_clean_base_and_separate_oracle(self):
        with tempfile.TemporaryDirectory(prefix="kryn-external-test-", dir="/private/tmp") as tmp:
            root = Path(tmp).resolve()
            workspace = root / "workspace"
            workspace.mkdir(mode=0o700)
            subprocess.run(["git", "init", "-q", str(workspace)], check=True)
            (workspace / "source.py").write_text("print(1)\n")
            subprocess.run(["git", "-C", str(workspace), "add", "source.py"], check=True)
            subprocess.run(["git", "-C", str(workspace), "-c", "user.name=Research",
                            "-c", "user.email=research@example.invalid", "commit", "-qm", "seed"], check=True)
            base = subprocess.check_output(["git", "-C", str(workspace), "rev-parse", "HEAD"], text=True).strip()
            prompt = root / "prompt.txt"
            prompt.write_text("Fix source.py")
            evidence = root / "evidence"
            got = prepare(workspace, prompt, evidence, base)
            self.assertEqual(got[:3], (workspace, prompt, evidence))
            self.assertTrue(got[3].is_dir())
            self.assertTrue(got[3].is_relative_to(workspace / ".git"))
            self.assertEqual(evidence.stat().st_mode & 0o777, 0o700)
            with self.assertRaisesRegex(ValueError, "separate fresh"):
                prepare(workspace, prompt, evidence, base)
            (workspace / "source.py").write_text("print(2)\n")
            with self.assertRaisesRegex(ValueError, "clean base"):
                prepare(workspace, prompt, root / "later", base)


if __name__ == "__main__":
    unittest.main()
