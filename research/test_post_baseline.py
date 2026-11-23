"""The unattended followthrough only summarizes completed, frozen phases."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research import post_baseline
from research.local_campaign import sha


class PostBaselineTests(unittest.TestCase):
    def test_completed_baselines_produce_explicitly_unqualified_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            harbor, swe, campaign = (root / name for name in ("harbor", "swe", "follow"))
            for path in (harbor, swe, campaign):
                path.mkdir()
            (harbor / "manifest.json").write_text("{}\n")
            (swe / "manifest.json").write_text("{}\n")
            (harbor / "final-report.json").write_text(json.dumps({
                "finished": True, "planned_tasks": 1, "finished_arms": 2,
                "paired": {"scoreable_pairs": 1}, "strict_kryn": 0,
                "strict_native": 1}))
            (swe / "final-report.json").write_text(json.dumps({
                "finished": True, "planned_tasks": 1, "finished_arms": 2,
                "matched_pairs": 1, "kryn_strict": 0, "native_strict": 0}))
            manifest = {"kind": "local_baseline_followthrough", "harbor": str(harbor),
                        "harbor_manifest_sha256": post_baseline.file_sha(harbor / "manifest.json"),
                        "swebench": str(swe),
                        "swebench_manifest_sha256": post_baseline.file_sha(swe / "manifest.json"),
                        "source_sha256": {"source": "hash"},
                        "product_plugin_sha256": {}}
            data = (json.dumps(manifest) + "\n").encode()
            (campaign / "manifest.json").write_bytes(data)
            (campaign / "manifest.sha256").write_text(sha(data) + "\n")
            with patch.object(post_baseline, "source_hashes", return_value={"source": "hash"}), \
                    patch.object(post_baseline, "plugin_hashes", return_value={}), \
                    patch.object(post_baseline, "_safe"), \
                    patch.object(post_baseline, "_staged", return_value={"passed": True,
                                "protected_eligible": False}):
                result = post_baseline.run(campaign, sha(data))
            self.assertFalse(result["frontier_adjacent_qualified"])
            self.assertFalse(result["candidate_validation_completed"])
            self.assertEqual(result["harbor"]["strict_native"], 1)
            self.assertEqual(json.loads((campaign / "status.json").read_text())[
                "state"], "baseline_checkpoint_ready")


if __name__ == "__main__":
    unittest.main()
