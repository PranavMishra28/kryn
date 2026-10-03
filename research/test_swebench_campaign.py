"""Fail-closed paired scoring for the official SWE-bench campaign."""

import json
from pathlib import Path
import tempfile
import unittest

from research.swebench_controller import summarize


class SWEbenchCampaignTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
