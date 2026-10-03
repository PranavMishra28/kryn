"""No-model APFS integration checks for the research Agent-to-grader barrier."""
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import agent_grade_barrier as barrier
from run_external_patch import git_config_sha256, stop_browser_broker
from ui_gateway.preflight import broker_request, broker_start


@unittest.skipUnless(sys.platform == "darwin" and barrier.GIT.is_file(),
                     "Requires macOS disk images and Command Line Tools Git")
class AgentGradeBarrierTest(unittest.TestCase):
    def run_trial(self, uncertain_detach=False, cancel_capture=False, unsettled_browser=False,
                  live_browser_image=None):
        with tempfile.TemporaryDirectory(prefix="kryn-barrier-test-seed-", dir="/private/tmp") as temp:
            root = Path(temp)
            seed = root / "seed"
            seed.mkdir()
            subprocess.run([str(barrier.GIT), "init", "-q", str(seed)], check=True)
            (seed / "source.py").write_text("value = 1\n")
            if live_browser_image:
                (seed / "index.html").write_text("<!doctype html><title>Seed</title>")
            subprocess.run([str(barrier.GIT), "-C", str(seed), "add", "-A"], check=True)
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
                expected_image = live_browser_image or ("sha256:" + "a" * 64 if unsettled_browser else None)
                self.assertEqual(args.ui_image, expected_image)
                args.evidence.mkdir(mode=0o700)
                config = git_config_sha256(args.workspace)
                (args.workspace / "source.py").write_text("value = 2\n")
                (args.workspace / "new_test.py").write_text("assert 2 == 2\n")
                browser_settled = not unsettled_browser
                if live_browser_image:
                    (args.workspace / "index.html").write_text(
                        "<!doctype html><title>Candidate nonce</title><p>PUBLIC-17</p>")
                    child, broker = broker_start(live_browser_image, args.workspace)
                    try:
                        opened = broker_request(broker, {"token": broker["token"], "op": "open"})
                        self.assertTrue(opened["ok"])
                        self.assertIn("PUBLIC-17", opened["text"])
                        self.assertNotIn("synthetic oracle", opened["text"])
                    finally:
                        browser_settled = stop_browser_broker(child, broker)
                return {"completed": True, "patch_deferred": True,
                        "inference_relay_settled": True,
                        "browser_settled": browser_settled,
                        "initial_git_config_sha256": config,
                        "benchmark_tool_manifest": {"canary": True}}

            def fake_grade(workspace, private, evidence):
                graded.append(True)
                self.assertEqual((workspace / "source.py").read_text(), "value = 2\n")
                self.assertEqual((workspace / "new_test.py").read_text(), "assert 2 == 2\n")
                if live_browser_image:
                    self.assertIn("PUBLIC-17", (workspace / "index.html").read_text())
                self.assertIsNone(barrier.image_entry(receipt / "candidate.sparseimage"))
                return {"pass": True}

            original_detach = barrier.detach
            original_collect = barrier.collect_patch
            monitors = []

            class FakeGuard:
                def __init__(self, folder, samples):
                    self.samples = samples
                    self.cancel = threading.Event()
                    self.guard = SimpleNamespace(reason=None, max_swap_growth=512 * 1024**2,
                                                 warning_samples=2)
                    self.preflight_passed = False
                    monitors.append(self)

                def sample(self):
                    self.samples.append({"swap_used_bytes": 0, "pressure_level": 1,
                                         "power_source": "AC", "listener_processes": [
                                             {"pid": 123, "rss_bytes": 1024}]})

                def start(self):
                    self.preflight_passed = True
                    self.sample()

                def close(self):
                    self.sample()

            def maybe_cancel_collect(*args, **kwargs):
                if cancel_capture:
                    monitors[-1].guard.reason = "synthetic capture resource abort"
                    monitors[-1].cancel.set()
                return original_collect(*args, **kwargs)

            def detach_then_doubt(volume):
                original_detach(volume)
                if uncertain_detach and volume.image.name == "candidate.sparseimage":
                    raise barrier.BarrierError("detachment uncertain")

            with patch.object(barrier, "run", fake_agent), patch.object(
                    barrier, "benchmark_tools", return_value=(barrier.GIT.parent, [],
                                                                 {"canary": True})), patch.object(
                    barrier, "configuration", return_value=({}, [], [])), patch.object(
                    barrier, "detach", detach_then_doubt), patch.object(
                    barrier, "NativeResourceGuard", FakeGuard), patch.object(
                    barrier, "runtime_is_idle", return_value=True), patch.object(
                    barrier, "collect_patch", maybe_cancel_collect):
                image = live_browser_image or ("sha256:" + "a" * 64 if unsettled_browser else None)
                if uncertain_detach:
                    with self.assertRaisesRegex(barrier.BarrierError, "detachment uncertain"):
                        barrier.run_candidate_to_grader(
                            seed=seed, prompt=prompt, task_id="canary", arm="native",
                            tool_venv=tool_venv, receipt=receipt,
                            hidden_paths=[hidden], grade=fake_grade,
                            browser_image=image)
                elif cancel_capture:
                    with self.assertRaisesRegex(barrier.CaptureCancelled, "Resource guard"):
                        barrier.run_candidate_to_grader(
                            seed=seed, prompt=prompt, task_id="canary", arm="native",
                            tool_venv=tool_venv, receipt=receipt,
                            hidden_paths=[hidden], grade=fake_grade,
                            browser_image=image)
                elif unsettled_browser:
                    with self.assertRaisesRegex(barrier.BarrierError, "did not complete"):
                        barrier.run_candidate_to_grader(
                            seed=seed, prompt=prompt, task_id="canary", arm="native",
                            tool_venv=tool_venv, receipt=receipt,
                            hidden_paths=[hidden], grade=fake_grade,
                            browser_image=image)
                else:
                    result = barrier.run_candidate_to_grader(
                        seed=seed, prompt=prompt, task_id="canary", arm="native",
                        tool_venv=tool_venv, receipt=receipt,
                        hidden_paths=[hidden], grade=fake_grade,
                        browser_image=image)
                    self.assertTrue(result["graded"])
                    self.assertTrue(result["candidate_detached"])
                    self.assertTrue(result["capture_detached"])
                    self.assertTrue(result["grader_detached"])
                    self.assertEqual(result["capture"]["untracked_files_included_in_patch"],
                                     ["new_test.py"])
                    self.assertEqual(result["grader_result"], {"pass": True})
                    self.assertTrue(result["capture_guard"]["resources"]["telemetry_complete"])
                    self.assertEqual(result["capture_guard"]["warning_samples_to_abort"], 2)
                    self.assertEqual(result["capture_guard"]["max_swap_growth_bytes"],
                                     512 * 1024**2)
            self.assertEqual(bool(graded), not (uncertain_detach or cancel_capture or unsettled_browser))
            recorded = json.loads((receipt / "barrier.json").read_text())
            self.assertEqual(recorded["graded"], not (uncertain_detach or cancel_capture or unsettled_browser))
            self.assertIsNone(barrier.image_entry(receipt / "candidate.sparseimage"))
            if cancel_capture:
                self.assertTrue(recorded["capture_detached"])
                self.assertTrue(recorded["capture_guard"]["cancelled"])
                self.assertEqual(recorded["capture_guard"]["reason"],
                                 "synthetic capture resource abort")
                self.assertFalse((receipt / "grader.sparseimage").exists())
            if not uncertain_detach and not cancel_capture:
                self.assertIsNone(barrier.image_entry(receipt / "grader.sparseimage"))
            shutil.rmtree(receipt)

    def test_read_only_capture_then_fresh_grade(self):
        self.run_trial()

    def test_uncertain_detach_prevents_grading(self):
        self.run_trial(uncertain_detach=True)

    def test_capture_resource_abort_prevents_grading(self):
        self.run_trial(cancel_capture=True)

    def test_browser_cleanup_uncertainty_prevents_grading(self):
        self.run_trial(unsettled_browser=True)

    @unittest.skipUnless(os.environ.get("KRYN_UI_IMAGE"), "Requires a pinned local browser image")
    def test_real_browser_settles_before_capture_and_grade(self):
        self.run_trial(live_browser_image=os.environ["KRYN_UI_IMAGE"])


if __name__ == "__main__":
    unittest.main()
