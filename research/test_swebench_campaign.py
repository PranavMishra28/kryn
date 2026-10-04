"""Fail-closed paired scoring for the official SWE-bench campaign."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research import swebench_controller
from research.swebench_roster import EVALUATOR
from research.local_campaign import sha

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
                           "official": {"graded": True},
                           "worker": {"ac_power_start": True,
                                      "ac_power_end": True}}
                    (attempts / (row["name"] + ".final.json")).write_text(json.dumps(row))
            result = summarize(root, manifest)
            self.assertEqual(result["matched_pairs"], 1)
            self.assertEqual(result["attrition_pairs"], 1)
            self.assertEqual(result["kryn_strict"], 1)
            self.assertEqual(result["native_strict"], 0)

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
