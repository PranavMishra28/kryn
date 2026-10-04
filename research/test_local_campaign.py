"""Campaign reporting controls for unmatched local benchmark arms."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from research import local_campaign
from research.local_campaign import controlled_env, paired_summary


class CampaignTests(unittest.TestCase):
    def test_campaign_battery_floor_applies_while_charging(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(local_campaign.shutil, "disk_usage", return_value=SimpleNamespace(
                    free=local_campaign.MIN_FREE + 1)), patch.object(
                    local_campaign, "bytes_under", return_value=0):
                with patch.object(local_campaign, "battery", return_value=(True, 39)):
                    self.assertEqual(local_campaign.room(root, starting=True),
                                     "battery_below_campaign_limit")
                    self.assertIsNone(local_campaign.room(root, starting=False))
                with patch.object(local_campaign, "battery", return_value=(True, 24)):
                    self.assertEqual(local_campaign.room(root, starting=False),
                                     "battery_below_campaign_limit")
                with patch.object(local_campaign, "battery", return_value=(True, 40)):
                    self.assertIsNone(local_campaign.room(root, starting=True))
                with patch.object(local_campaign, "battery", return_value=(False, 24)):
                    self.assertEqual(local_campaign.room(root, starting=False),
                                     "battery_below_campaign_limit")

    def test_unmatched_wire_cannot_be_scored_as_uplift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = {"tasks": [{"name": "one"}, {"name": "two"}]}
            rows = []
            for number, model in ((1, "Qwen3.5-9B-6bit"), (2, "other")):
                for arm in ("kryn", "native"):
                    name = f"h{number:02d}-{arm}"
                    folder = root / "trials" / name / "host-guard"
                    folder.mkdir(parents=True)
                    wire = {"model": model if arm == "native" else "Qwen3.5-9B-6bit",
                            "max_tokens": 8192, "numeric": {}, "thinking": {},
                            "tool_count": 10, "tool_schema_sha256": "same"}
                    (folder / "inference.json").write_text(json.dumps([wire]))
                    rows.append({"name": name, "status": "graded", "arm": arm,
                                 "strict_accepted": arm == "kryn",
                                 "worker": {"ac_power_start": False,
                                            "ac_power_end": False},
                                 "local_only": {"generation_proven": True}})
            result = paired_summary(root, manifest, rows)
            self.assertEqual(result["scoreable_pairs"], 1)
            self.assertEqual(result["attrition_pairs"], 1)
            self.assertEqual(result["win_loss_tie"]["kryn_only"], 1)

    def test_later_tool_wire_drift_invalidates_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rows = []
            for arm in ("kryn", "native"):
                name = f"h01-{arm}"
                folder = root / "trials" / name / "host-guard"
                folder.mkdir(parents=True)
                wire = {"model": "Qwen3.5-9B-6bit", "max_tokens": 8192,
                        "numeric": {}, "thinking": {}, "tool_count": 10,
                        "tool_schema_sha256": "same"}
                later = dict(wire, tool_schema_sha256="changed" if arm == "kryn"
                             else "same")
                (folder / "inference.json").write_text(json.dumps([wire, later]))
                rows.append({"name": name, "status": "graded", "arm": arm,
                             "strict_accepted": arm == "kryn",
                             "worker": {"ac_power_start": True,
                                        "ac_power_end": True},
                             "local_only": {"generation_proven": True}})
            result = paired_summary(root, {"tasks": [{"name": "one"}]}, rows)
            self.assertEqual(result["scoreable_pairs"], 0)
            self.assertEqual(result["attrition_pairs"], 1)
            self.assertEqual(result["win_loss_tie"]["kryn_only"], 0)

    def test_owned_image_cleanup_failure_blocks_finish_and_can_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tasks = root / "tasks"
            tasks.mkdir()
            task = {"name": "one"}
            (tasks / "one.prepared.json").write_text(json.dumps({
                "image_owned": True, "image_tag": "repo:tag",
                "image_digest": "repo@sha256:abc", "image_id": "sha256:id"}))
            remaining = True

            def image_id(_):
                return "sha256:id" if remaining else None

            def remove(*_, **__):
                nonlocal remaining
                if allow_removal:
                    remaining = False
                return subprocess.CompletedProcess([], 0 if allow_removal else 1)

            allow_removal = False
            with patch.object(local_campaign, "docker_image_id", side_effect=image_id), patch.object(
                    local_campaign.subprocess, "run", side_effect=remove):
                with self.assertRaisesRegex(RuntimeError, "remained after cleanup"):
                    local_campaign.release_owned_image(root, task)
                self.assertFalse(json.loads((tasks / "one.image-release.json").read_text())[
                    "image_removed"])
                allow_removal = True
                local_campaign.release_owned_image(root, task)
            self.assertTrue(json.loads((tasks / "one.image-release.json").read_text())[
                "image_removed"])

    def test_owned_image_tag_drift_blocks_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tasks = root / "tasks"
            tasks.mkdir()
            (tasks / "one.prepared.json").write_text(json.dumps({
                "image_owned": True, "image_tag": "repo:tag",
                "image_digest": "repo@sha256:abc", "image_id": "sha256:id"}))
            with patch.object(local_campaign, "docker_image_id", return_value="sha256:other"), patch.object(
                    local_campaign.subprocess, "run") as run:
                with self.assertRaisesRegex(RuntimeError, "reference changed"):
                    local_campaign.release_owned_image(root, {"name": "one"})
                run.assert_not_called()

    def test_docker_inspect_failure_is_not_image_absence(self):
        with patch.object(local_campaign.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 1, stdout="",
                                                      stderr="Cannot connect to Docker daemon")):
            with self.assertRaisesRegex(RuntimeError, "Cannot verify Docker image absence"):
                local_campaign.docker_image_id("repo:tag")
        with patch.object(local_campaign.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 1, stdout="",
                                                      stderr="Error: No such image: repo:tag")):
            self.assertIsNone(local_campaign.docker_image_id("repo:tag"))

    def test_host_worker_environment_has_no_provider_credentials(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sentinel",
                                     "OPENCODE_CONFIG_CONTENT": "remote",
                                     "ANTHROPIC_AUTH_TOKEN": "sentinel"}):
            env = controlled_env()
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("OPENCODE_CONFIG_CONTENT", env)
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", env)

    def test_telemetry_exception_reaps_model_worker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real_popen = subprocess.Popen

            class FinishedAwake:
                def poll(self):
                    return 0

                def wait(self, timeout=None):
                    return 0

            def launch(command, **kwargs):
                if command[0] == "/usr/bin/caffeinate":
                    return FinishedAwake()
                return real_popen(command, **kwargs)

            with patch.object(local_campaign, "battery", return_value=(True, 100)), patch.object(
                    local_campaign, "room", side_effect=RuntimeError("telemetry unavailable")), patch.object(
                    local_campaign.subprocess, "Popen", side_effect=launch):
                with self.assertRaisesRegex(RuntimeError, "telemetry unavailable"):
                    local_campaign.run_child(["/bin/sleep", "30"], "attempt", root, root)
            pid = json.loads((root / "attempt.running.json").read_text())["pid"]
            self.assertNotEqual(subprocess.run(["ps", "-p", str(pid)],
                                               stdout=subprocess.DEVNULL).returncode, 0)


if __name__ == "__main__":
    unittest.main()
