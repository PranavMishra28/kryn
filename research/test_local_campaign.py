"""Campaign reporting controls for unmatched local benchmark arms."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.local_campaign import controlled_env, paired_summary


class CampaignTests(unittest.TestCase):
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

    def test_host_worker_environment_has_no_provider_credentials(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sentinel",
                                     "OPENCODE_CONFIG_CONTENT": "remote",
                                     "ANTHROPIC_AUTH_TOKEN": "sentinel"}):
            env = controlled_env()
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("OPENCODE_CONFIG_CONTENT", env)
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", env)


if __name__ == "__main__":
    unittest.main()
