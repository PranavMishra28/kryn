"""The external adapter refuses dirty or ambiguous benchmark workspaces."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from run_external_patch import prepare


class ExternalPreflightTest(unittest.TestCase):
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
