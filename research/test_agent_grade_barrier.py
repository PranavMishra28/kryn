"""No-model APFS integration checks for the research Agent-to-grader barrier."""
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import agent_grade_barrier as barrier
from run_external_patch import git_config_sha256


@unittest.skipUnless(sys.platform == "darwin" and barrier.GIT.is_file(),
                     "Requires macOS disk images and Command Line Tools Git")
class AgentGradeBarrierTest(unittest.TestCase):
    def run_trial(self, uncertain_detach=False):
        with tempfile.TemporaryDirectory(prefix="kryn-barrier-test-seed-", dir="/private/tmp") as temp:
            root = Path(temp)
            seed = root / "seed"
            seed.mkdir()
            subprocess.run([str(barrier.GIT), "init", "-q", str(seed)], check=True)
            (seed / "source.py").write_text("value = 1\n")
            subprocess.run([str(barrier.GIT), "-C", str(seed), "add", "source.py"], check=True)
            subprocess.run([str(barrier.GIT), "-C", str(seed), "-c", "user.name=Canary",
                            "-c", "user.email=canary@example.invalid", "commit", "-qm", "seed"], check=True)
            prompt = root / "prompt.txt"
            prompt.write_text("Change value and add a test\n")
            hidden = root / "hidden.txt"
            hidden.write_text("synthetic oracle\n")
            tool_venv = root / "unused"
            tool_venv.mkdir()
            receipt = Path("/private/tmp") / ("kryn-barrier-test-" + secrets.token_hex(8))
            graded = []

            def fake_agent(args, *, defer_patch):
                self.assertTrue(defer_patch)
                args.evidence.mkdir(mode=0o700)
                config = git_config_sha256(args.workspace)
                (args.workspace / "source.py").write_text("value = 2\n")
                (args.workspace / "new_test.py").write_text("assert 2 == 2\n")
                return {"completed": True, "patch_deferred": True,
                        "inference_relay_settled": True,
                        "initial_git_config_sha256": config,
                        "benchmark_tool_manifest": {"canary": True}}

            def fake_grade(workspace, private, evidence):
                graded.append(True)
                self.assertEqual((workspace / "source.py").read_text(), "value = 2\n")
                self.assertEqual((workspace / "new_test.py").read_text(), "assert 2 == 2\n")
                self.assertIsNone(barrier.image_entry(receipt / "candidate.sparseimage"))
                return {"pass": True}

            original_detach = barrier.detach

            def detach_then_doubt(volume):
                original_detach(volume)
                if uncertain_detach and volume.image.name == "candidate.sparseimage":
                    raise barrier.BarrierError("detachment uncertain")

            with patch.object(barrier, "run", fake_agent), patch.object(
                    barrier, "benchmark_tools", return_value=(barrier.GIT.parent, [],
                                                                 {"canary": True})), patch.object(
                    barrier, "detach", detach_then_doubt):
                if uncertain_detach:
                    with self.assertRaisesRegex(barrier.BarrierError, "detachment uncertain"):
                        barrier.run_candidate_to_grader(
                            seed=seed, prompt=prompt, task_id="canary", arm="native",
                            tool_venv=tool_venv, receipt=receipt,
                            hidden_paths=[hidden], grade=fake_grade)
                else:
                    result = barrier.run_candidate_to_grader(
                        seed=seed, prompt=prompt, task_id="canary", arm="native",
                        tool_venv=tool_venv, receipt=receipt,
                        hidden_paths=[hidden], grade=fake_grade)
                    self.assertTrue(result["graded"])
                    self.assertTrue(result["candidate_detached"])
                    self.assertTrue(result["capture_detached"])
                    self.assertTrue(result["grader_detached"])
                    self.assertEqual(result["capture"]["untracked_files_included_in_patch"],
                                     ["new_test.py"])
                    self.assertEqual(result["grader_result"], {"pass": True})
            self.assertEqual(bool(graded), not uncertain_detach)
            recorded = json.loads((receipt / "barrier.json").read_text())
            self.assertEqual(recorded["graded"], not uncertain_detach)
            self.assertIsNone(barrier.image_entry(receipt / "candidate.sparseimage"))
            if not uncertain_detach:
                self.assertIsNone(barrier.image_entry(receipt / "grader.sparseimage"))
            shutil.rmtree(receipt)

    def test_read_only_capture_then_fresh_grade(self):
        self.run_trial()

    def test_uncertain_detach_prevents_grading(self):
        self.run_trial(uncertain_detach=True)


if __name__ == "__main__":
    unittest.main()
