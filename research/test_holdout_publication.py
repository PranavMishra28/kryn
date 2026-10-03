"""The local publication gate rejects task identity leaks before a PR is pushed."""
import hashlib
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
        subprocess.run(["git", "-C", str(self.repo), "branch", "-M", "main"], check=True)
        remote = self.root / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", str(remote)],
                       check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "-u", "origin", "main"],
                       check=True)
        self.base = subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "HEAD"],
                                            text=True).strip()
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

    def check(self, *extra):
        result = subprocess.run([
            sys.executable, "-B", str(SCRIPT), str(self.roster),
            "--repo", str(self.repo),
            "--roster-sha256", hashlib.sha256(self.roster.read_bytes()).hexdigest(),
            "--pr-text", str(self.pr_text), *extra,
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

    def test_deleted_commit_blob_and_path_name_still_disclose(self):
        leaked = self.repo / (self.task_id + ".txt")
        leaked.write_text("Visible " + self.task_id + "\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "Add draft"], check=True)
        leaked.unlink()
        subprocess.run(["git", "-C", str(self.repo), "add", "-u"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "Remove draft"], check=True)
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertGreater(result["historical_matching_paths"], 0)
        self.assertGreater(result["historical_matching_path_names"], 0)
        self.assertEqual(result["tracked_matching_paths"], 0)

    def test_binary_blob_is_scanned(self):
        (self.repo / "sample.bin").write_bytes(b"\0" + self.task_id.encode() + b"\0")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertGreater(result["staged_matching_paths"], 0)

    def test_private_report_is_mode_0600(self):
        report = self.root / "receipt.json"
        code, result = self.check("--report", str(report))
        self.assertEqual(code, 0)
        self.assertTrue(result["passed"])
        self.assertEqual(report.stat().st_mode & 0o777, 0o600)
        self.assertTrue(json.loads(report.read_text())["passed"])

    def test_missing_identity_fails_closed(self):
        data = json.loads(self.roster.read_text())
        del data["tasks"][0]["grader_sha256"]
        self.roster.write_text(json.dumps(data))
        result = subprocess.run([
            sys.executable, "-B", str(SCRIPT), str(self.roster),
            "--repo", str(self.repo),
            "--roster-sha256", hashlib.sha256(self.roster.read_bytes()).hexdigest(),
            "--pr-text", str(self.pr_text),
        ], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("grader_sha256", result.stderr)

    def test_stale_roster_digest_fails_closed(self):
        result = subprocess.run([
            sys.executable, "-B", str(SCRIPT), str(self.roster),
            "--repo", str(self.repo), "--roster-sha256", "0" * 64,
            "--pr-text", str(self.pr_text),
        ], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("differs", result.stderr)

    def test_public_base_must_match_remote(self):
        (self.repo / "README.md").write_text("Another public change.\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "Advance main"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "push", "-q", "origin", "main"],
                       check=True)
        subprocess.run(["git", "-C", str(self.repo), "update-ref", "refs/remotes/origin/main",
                        self.base], check=True)
        result = subprocess.run([
            sys.executable, "-B", str(SCRIPT), str(self.roster),
            "--repo", str(self.repo),
            "--roster-sha256", hashlib.sha256(self.roster.read_bytes()).hexdigest(),
            "--pr-text", str(self.pr_text),
        ], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("differs from public main", result.stderr)


if __name__ == "__main__":
    unittest.main()
