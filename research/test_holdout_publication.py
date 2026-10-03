"""The local publication gate rejects task identity leaks before a PR is pushed."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid


SCRIPT = Path(__file__).with_name("check_holdout_publication.py")


class PublicationGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/private/tmp")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email",
                        "test@example.invalid"], check=True)
        (self.repo / "README.md").write_text("Public research notes.\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "Initial"], check=True)
        self.task_id = "private-fixture-" + uuid.uuid4().hex
        self.roster = self.root / "roster.json"
        self.roster.write_text(json.dumps({"tasks": [{
            "id": self.task_id,
            "prompt_sha256": "a" * 64,
            "grader_sha256": "b" * 64,
            "seed_commit": "c" * 40,
        }]}))
        self.pr_text = self.root / "pr.txt"
        self.pr_text.write_text("Aggregate research outcome only.\n")

    def check(self):
        result = subprocess.run([
            sys.executable, "-B", str(SCRIPT), str(self.roster),
            "--repo", str(self.repo), "--pr-text", str(self.pr_text),
        ], capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_clean_and_tracked_disclosure(self):
        code, result = self.check()
        self.assertEqual(code, 0)
        self.assertTrue(result["passed"])
        (self.repo / "README.md").write_text("Visible " + self.task_id + "\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertGreater(result["staged_matching_paths"], 0)

    def test_pr_text_and_commit_message_disclosure(self):
        self.pr_text.write_text("Includes " + self.task_id + "\n")
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(result["pr_text_matching_patterns"], 1)
        self.pr_text.write_text("Aggregate only.\n")
        subprocess.run(["git", "-C", str(self.repo), "commit", "--allow-empty", "-qm",
                        "Study " + self.task_id], check=True)
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(result["commit_message_matching_patterns"], 1)

    def test_path_name_disclosure(self):
        (self.repo / (self.task_id + ".txt")).write_text("Nothing sensitive inside.\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(result["matching_path_names"], 1)


if __name__ == "__main__":
    unittest.main()
