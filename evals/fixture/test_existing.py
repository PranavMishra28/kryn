import unittest
from pathlib import Path
from taskboard_lite.parse import parse_rows
from taskboard_lite.report import summarize


class Existing(unittest.TestCase):
    def test_original_rows(self):
        rows = parse_rows(Path("data/entries.csv").read_text())
        self.assertEqual(len(rows), 3)
        self.assertEqual(summarize(rows), {"count": 3, "minutes": 75})

    def test_bad_minutes(self):
        with self.assertRaises(ValueError):
            parse_rows("id,project,minutes,date\nbad,alpha,-1,2026-09-01\n")


if __name__ == "__main__":
    unittest.main()
