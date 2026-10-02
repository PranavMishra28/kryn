"""Receipt ledger must preserve failed attempts without duplicate rewrites."""
import json
from pathlib import Path
import tempfile
import unittest

from record_trial import append, model_provenance


class LedgerTest(unittest.TestCase):
    def test_replacement_model_cannot_inherit_champion_revision(self):
        profile = {"repository": "mlx-community/Qwen3.5-9B-6bit", "revision": "pinned"}
        champion = model_provenance(profile, "Qwen3.5-9B-6bit", "hash", "hash")
        replacement = model_provenance(profile, "Different-14B", "hash", "hash")
        self.assertTrue(champion["verified"])
        self.assertFalse(replacement["verified"])
        self.assertIsNone(replacement["revision"])

    def test_append_only_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "development.jsonl"
            first = {"run": "attempt-a", "stage": "attempt1", "accepted": False}
            append(ledger, first)
            with self.assertRaisesRegex(ValueError, "already recorded"):
                append(ledger, {**first, "accepted": True})
            self.assertEqual([json.loads(line) for line in ledger.read_text().splitlines()], [first])

    def test_private_path_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "development.jsonl"
            with self.assertRaisesRegex(ValueError, "local absolute path"):
                append(ledger, {"run": "attempt-a", "stage": "attempt1",
                                "evidence_path": "/Users/example/private"})
            self.assertFalse(ledger.exists())


if __name__ == "__main__":
    unittest.main()
