"""The external adapter refuses dirty or ambiguous benchmark workspaces."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from unittest.mock import patch

from run_external_patch import benchmark_tools, drive, prepare


class ExternalPreflightTest(unittest.TestCase):
    def test_finished_cli_cannot_silently_truncate_events(self):
        class Child:
            def communicate(self, **kwargs):
                return b"x" * (2 * 1024**2 + 1), b""
        cause, _, _ = drive(Child(), b"task", 30, lambda: False)
        self.assertEqual(cause, "output_budget")

    def test_benchmark_tool_dependencies_are_explicit(self):
        self.assertEqual(benchmark_tools(None), (None, [], None))
        with tempfile.TemporaryDirectory(prefix="kryn-external-test-", dir="/private/tmp") as tmp:
            venv = Path(tmp) / "venv"
            (venv / "bin").mkdir(parents=True)
            for name in ("pyvenv.cfg", "bin/python3", "bin/rg"):
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
            self.assertEqual(len(dependencies), 3)
            self.assertEqual(manifest["pytest_version"], "pytest 8.3.3")
            self.assertEqual(manifest["packages"], [["pytest", "8.3.3"]])
            with patch("run_external_patch.subprocess.run", return_value=subprocess.CompletedProcess(
                    [], 1, "", "No module named pytest")):
                with self.assertRaisesRegex(RuntimeError, "lacks runnable pytest"):
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
