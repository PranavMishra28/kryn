"""The local handoff must respect the frozen phase boundary."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research import campaign_chain
from research.local_campaign import sha


class ChainTests(unittest.TestCase):
    def test_finished_harbor_starts_frozen_swebench_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            harbor, swebench, work = root / "harbor", root / "swebench", root / "work"
            harbor.mkdir()
            swebench.mkdir()
            (harbor / "final-report.json").write_text('{"finished": true}')
            manifest = b'{"kind": "swebench_local_baseline"}\n'
            (swebench / "manifest.json").write_bytes(manifest)
            (swebench / "manifest.sha256").write_text(sha(manifest) + "\n")
            with patch.object(campaign_chain, "runtime_idle", return_value=True), patch.object(
                    campaign_chain.subprocess, "run") as launch:
                launch.return_value.returncode = 0
                campaign_chain.run(harbor, swebench, work, sha(manifest), 123)
            self.assertEqual(launch.call_count, 1)
            self.assertIn("swebench_controller.py", " ".join(launch.call_args.args[0]))
            status = json.loads((swebench / "chain-status.json").read_text())
            self.assertEqual(status["state"], "finished")

    def test_incomplete_harbor_cannot_start_swebench(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            harbor, swebench = root / "harbor", root / "swebench"
            harbor.mkdir()
            swebench.mkdir()
            (harbor / "final-report.json").write_text('{"finished": false}')
            with patch.object(campaign_chain.subprocess, "run") as launch:
                with self.assertRaisesRegex(RuntimeError, "incomplete"):
                    campaign_chain.run(harbor, swebench, root / "work", "0" * 64, 123)
            launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
