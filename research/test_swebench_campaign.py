"""Fail-closed paired scoring for the official SWE-bench campaign."""

import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from research import swebench_controller
from research import swebench_local
from research.swebench_roster import EVALUATOR
from research.local_campaign import file_sha, sha

summarize = swebench_controller.summarize


class SWEbenchCampaignTests(unittest.TestCase):
    def test_missing_driver_stops_after_first_arm_and_keeps_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign, work = root / "campaign", root / "work"
            campaign.mkdir()
            manifest = {"kind": "swebench_local_baseline", "evaluator_commit": EVALUATOR,
                        "tasks": [{"instance_id": "one", "arm_order": ["kryn", "native"],
                                   "base_commit": "frozen"}]}
            data = (json.dumps(manifest) + "\n").encode()
            (campaign / "manifest.json").write_bytes(data)
            (campaign / "manifest.sha256").write_text(sha(data) + "\n")

            def candidate(*_):
                path = work / "one" / "candidate"
                path.mkdir(parents=True)
                return path

            with patch.object(swebench_controller, "source_lock"), patch.object(
                    swebench_controller, "wait_for_safe"), patch.object(
                    swebench_controller.swebench_local, "prepare",
                    return_value=(work / "one/base", root / "prompt", {})), patch.object(
                    swebench_controller, "grade_once",
                    return_value={"clean_grade": True, "resolved": True}), patch.object(
                    swebench_controller.swebench_local, "fresh_candidate",
                    side_effect=candidate), patch.object(
                    swebench_controller, "run_child",
                    return_value={"returncode": 1, "stop_reason": None}) as worker:
                with self.assertRaisesRegex(RuntimeError, "no driver receipt"):
                    swebench_controller.run(campaign, work, sha(data))
            self.assertTrue((campaign / "attempts/s01-kryn.final.json").is_file())
            self.assertFalse((campaign / "attempts/s01-native.final.json").exists())
            worker.assert_called_once()
            self.assertEqual(worker.call_args.args[0][0],
                             str(swebench_controller.TOOL_VENV / "bin/python3"))

    def test_unmatched_tool_or_power_never_supports_uplift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attempts = root / "attempts"
            attempts.mkdir()
            manifest = {"tasks": [{"instance_id": "one"}, {"instance_id": "two"}]}
            for index in (1, 2):
                for arm in ("kryn", "native"):
                    row = {"name": f"s{index:02d}-{arm}", "accepted": arm == "kryn",
                           "main_wire": {"model": "Qwen3.5-9B-6bit",
                                         "tool_schema_sha256": "equal" if index == 1
                                         else arm},
                           "local_only": {"generation_proven": True},
                           "official": {"graded": True, "clean_grade": True},
                           "wire_stable": True,
                           "paired_controls": {"permissions": "same"},
                           "worker": {"ac_power_start": True,
                                      "ac_power_end": True}}
                    (attempts / (row["name"] + ".final.json")).write_text(json.dumps(row))
            result = summarize(root, manifest)
            self.assertEqual(result["matched_pairs"], 1)
            self.assertEqual(result["attrition_pairs"], 1)
            self.assertEqual(result["kryn_strict"], 1)
            self.assertEqual(result["native_strict"], 0)

    def test_different_effective_permissions_make_pair_unmatched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "attempts").mkdir()
            for arm in ("kryn", "native"):
                row = {"accepted": arm == "kryn", "main_wire": {"model": "same"},
                       "wire_stable": True,
                       "paired_controls": {"permissions": arm},
                       "local_only": {"generation_proven": True},
                       "official": {"clean_grade": True},
                       "worker": {"ac_power_start": True, "ac_power_end": True}}
                (root / "attempts" / f"s01-{arm}.final.json").write_text(json.dumps(row))
            result = summarize(root, {"tasks": [{"instance_id": "one"}]})
            self.assertEqual(result["matched_pairs"], 0)
            self.assertEqual(result["attrition_pairs"], 1)

    def test_permissions_normalize_only_isolated_runtime_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = []
            for name in ("a", "b"):
                evidence = root / name
                evidence.mkdir()
                permissions = [{"action": "shell", "effect": "allow", "resource": "*"},
                               {"action": "external_directory", "effect": "allow",
                                "resource": f"/private/tmp/kryn-isolated-{name}/tmpdir/opencode/*"}]
                (evidence / "agent-inventory.json").write_text(json.dumps(
                    {"data": [{"id": "agent", "permissions": permissions}]}))
                driver = {key: "same" for key in ("agent", "base_commit", "prompt_sha256",
                    "source_commit", "runner_sha256", "model_id", "model_repository",
                    "model_revision", "model_profile_sha256", "opencode_binary_sha256",
                    "benchmark_tool_manifest", "timeout_seconds")}
                hashes.append(swebench_controller.paired_controls(driver, evidence))
            self.assertEqual(hashes[0], hashes[1])
            inventory = root / "b/agent-inventory.json"
            changed = json.loads(inventory.read_text())
            changed["data"][0]["permissions"][0]["effect"] = "deny"
            inventory.write_text(json.dumps(changed))
            self.assertNotEqual(hashes[0], swebench_controller.paired_controls(driver, root / "b"))

    def test_unclean_gold_stops_before_candidate_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign, work = root / "campaign", root / "work"
            campaign.mkdir()
            manifest = {"kind": "swebench_local_baseline", "evaluator_commit": EVALUATOR,
                        "tasks": [{"instance_id": "one", "arm_order": ["kryn", "native"]}]}
            data = (json.dumps(manifest) + "\n").encode()
            (campaign / "manifest.json").write_bytes(data)
            (campaign / "manifest.sha256").write_text(sha(data) + "\n")
            with patch.object(swebench_controller, "source_lock"), patch.object(
                    swebench_controller, "wait_for_safe"), patch.object(
                    swebench_controller.swebench_local, "prepare",
                    return_value=(work / "one/base", root / "prompt", {})), patch.object(
                    swebench_controller, "grade_once",
                    return_value={"graded": False, "clean_grade": False, "reason": "resource_preflight"}), patch.object(
                    swebench_controller, "run_child") as worker:
                with self.assertRaisesRegex(RuntimeError, "Gold official grader failed"):
                    swebench_controller.run(campaign, work, sha(data))
            worker.assert_not_called()
            self.assertFalse(list((campaign / "attempts").glob("*.final.json")))

    def test_prepared_base_resume_refuses_modified_checkout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign, work = root / "campaign", root / "work"
            base = work / "one/base"
            base.mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(base)], check=True)
            subprocess.run(["git", "-C", str(base), "-c", "user.name=Test",
                            "-c", "user.email=test@example.invalid", "commit",
                            "--allow-empty", "-q", "-m", "base"], check=True)
            commit = subprocess.check_output(["git", "-C", str(base), "rev-parse", "HEAD"],
                                             text=True).strip()
            prepared = campaign / "prepared/one"
            prepared.mkdir(parents=True)
            prompt = prepared / "prompt.txt"
            prompt.write_text("prompt")
            (prepared / "receipt.json").write_text(json.dumps({
                "image_id": "pinned", "base_git_config_sha256": file_sha(base / ".git/config")}))
            (base / "unexpected.txt").write_text("drift")
            task = {"instance_id": "one", "base_commit": commit,
                    "prompt_sha256": file_sha(prompt), "image_tag": "unused"}
            with patch.object(swebench_local, "image_identity", return_value={"Id": "pinned"}):
                with self.assertRaisesRegex(RuntimeError, "Prepared SWE-bench task drifted"):
                    swebench_local.prepare({}, task, campaign, work)

    def test_grader_telemetry_exception_reaps_evaluator(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign = root / "campaign"
            prepared = campaign / "prepared/one"
            prepared.mkdir(parents=True)
            (prepared / "receipt.json").write_text('{"image_id":"pinned"}')
            (campaign / "manifest.json").write_text(
                '{"datasets":{"lite":{"test_sha256":"dataset"}}}')
            sys.path.insert(0, str(Path(swebench_controller.__file__).parents[1] / "tools"))
            import run_native_trial
            real_popen = subprocess.Popen
            children = []

            class FakeGuard:
                preflight_passed = True
                guard = None

                def __init__(self, *args, **kwargs):
                    self.cancel = self

                def is_set(self):
                    return False

                def start(self):
                    pass

                def close(self):
                    pass

            class FinishedAwake:
                def poll(self):
                    return 0

                def wait(self, timeout=None):
                    return 0

            def launch(command, **kwargs):
                if command[0] == "/usr/bin/caffeinate":
                    return FinishedAwake()
                child = real_popen(command, **kwargs)
                children.append(child)
                return child

            with patch.object(swebench_controller, "source_lock"), patch.object(
                    run_native_trial, "NativeResourceGuard", FakeGuard), patch.object(
                    swebench_controller, "file_sha", return_value="dataset"), patch.object(
                    swebench_controller, "runtime_idle", return_value=True), patch.object(
                    swebench_controller, "room", side_effect=[None, RuntimeError("telemetry unavailable")]), patch.object(
                    swebench_local, "image_identity", return_value={"Id": "pinned"}), patch.object(
                    swebench_local, "official_command", return_value=["/bin/sleep", "30"]), patch.object(
                    swebench_controller.subprocess, "check_output", return_value=""), patch.object(
                    swebench_controller.subprocess, "Popen", side_effect=launch):
                with self.assertRaisesRegex(RuntimeError, "telemetry unavailable"):
                    swebench_controller.grade_once(campaign, {"instance_id": "one", "dataset": "lite"},
                                                   "s01-kryn", "prediction")
            self.assertEqual(len(children), 1)
            self.assertIsNotNone(children[0].poll())

    def test_resume_after_both_arms_finishes_image_and_workspace_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign, work = root / "campaign", root / "work"
            (campaign / "attempts").mkdir(parents=True)
            prepared = campaign / "prepared" / "one"
            prepared.mkdir(parents=True)
            (prepared / "receipt.json").write_text('{"image_owned": true, "image_id": "id"}')
            checkout = work / "one"
            checkout.mkdir(parents=True)
            (checkout / "old-candidate").write_text("finished")
            manifest = {"kind": "swebench_local_baseline", "evaluator_commit": EVALUATOR,
                        "tasks": [{"instance_id": "one", "arm_order": ["kryn", "native"]}]}
            data = (json.dumps(manifest) + "\n").encode()
            (campaign / "manifest.json").write_bytes(data)
            (campaign / "manifest.sha256").write_text(sha(data) + "\n")
            for arm in ("kryn", "native"):
                (campaign / "attempts" / f"s01-{arm}.final.json").write_text(
                    json.dumps({"accepted": False, "instance_id": "one"}))
            with patch.object(swebench_controller, "source_lock"), patch.object(
                    swebench_controller.swebench_local, "release_image",
                    return_value={"removed": True}) as release:
                report = swebench_controller.run(campaign, work, sha(data))
            self.assertTrue(report["finished"])
            self.assertFalse(checkout.exists())
            self.assertTrue((prepared / "image-release.json").is_file())
            release.assert_called_once()

    def test_interrupted_arm_archives_partial_checkout_before_reusing_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            campaign, work = root / "campaign", root / "work"
            attempts = campaign / "attempts"
            attempts.mkdir(parents=True)
            candidate = work / "one/candidate"
            candidate.mkdir(parents=True)
            (candidate / "partial.txt").write_text("unfinished model edit")
            (attempts / "s01-kryn.running.json").write_text('{"pid": 123}')
            (attempts / "s01-kryn.stdout.log").write_text("interrupted")
            (attempts / "s01-native.final.json").write_text(
                json.dumps({"accepted": False, "instance_id": "one"}))
            manifest = {"kind": "swebench_local_baseline", "evaluator_commit": EVALUATOR,
                        "tasks": [{"instance_id": "one", "arm_order": ["kryn", "native"]}]}
            data = (json.dumps(manifest) + "\n").encode()
            (campaign / "manifest.json").write_bytes(data)
            (campaign / "manifest.sha256").write_text(sha(data) + "\n")
            with patch.object(swebench_controller, "source_lock"), patch.object(
                    swebench_controller, "wait_for_safe"), patch.object(
                    swebench_controller, "stop_orphan"), patch.object(
                    swebench_controller.swebench_local, "prepare",
                    return_value=(work / "one/base", root / "prompt", {})), patch.object(
                    swebench_controller, "grade_once",
                    return_value={"clean_grade": True, "resolved": True}), patch.object(
                    swebench_controller, "run_child") as worker:
                report = swebench_controller.run(campaign, work, sha(data))
            worker.assert_not_called()
            self.assertTrue(report["finished"])
            self.assertEqual(json.loads((attempts / "s01-kryn.final.json").read_text())
                             ["status"], "interrupted_before_receipt")
            archive = campaign / "interruptions/s01-kryn/candidate.tar.gz"
            receipt = json.loads((archive.parent / "receipt.json").read_text())
            self.assertEqual(receipt["archive_sha256"], file_sha(archive))
            with tarfile.open(archive) as bundle:
                self.assertEqual(bundle.extractfile("candidate/partial.txt").read(),
                                 b"unfinished model edit")
            self.assertFalse(candidate.exists())

    def test_image_cleanup_refuses_repointed_tag_or_retained_image(self):
        info = {"image_owned": True, "image_tag": "official:tag",
                "image_digest": "official@sha256:abc", "image_id": "sha256:expected"}
        with patch.object(swebench_controller.swebench_local, "image_identity",
                          return_value={"Id": "sha256:different"}), patch.object(
                              swebench_controller.swebench_local.subprocess, "run") as docker:
            with self.assertRaisesRegex(RuntimeError, "tag changed"):
                swebench_controller.swebench_local.release_image(info)
            docker.assert_not_called()
        with patch.object(swebench_controller.swebench_local, "image_identity",
                          return_value={"Id": "sha256:expected"}), patch.object(
                              swebench_controller.swebench_local.subprocess, "run") as docker:
            docker.return_value.returncode = 0
            with self.assertRaisesRegex(RuntimeError, "remained"):
                swebench_controller.swebench_local.release_image(info)


if __name__ == "__main__":
    unittest.main()
