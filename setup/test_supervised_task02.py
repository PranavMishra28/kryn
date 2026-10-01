"""The supplemental Task02 oracle must catch the gap in the frozen grader."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "evals/supervised_task02.py"
SOURCE = ROOT / "evals/fixture/taskboard_lite"


class SupervisedTask02Check(unittest.TestCase):
    def test_reference_passes_and_compact_date_regression_fails(self):
        good = subprocess.run([sys.executable, "-B", str(CHECK), str(SOURCE.parent)],
                              capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(good.stdout)["passed"])
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "taskboard_lite"
            shutil.copytree(SOURCE, candidate)
            report = candidate / "report.py"
            original = '            if datetime.date.fromisoformat(boundary).isoformat() != boundary:\n                raise ValueError("invalid date")'
            self.assertIn(original, report.read_text())
            report.write_text(report.read_text().replace(original,
                              '            datetime.date.fromisoformat(boundary)'))
            bad = subprocess.run([sys.executable, "-B", str(CHECK), temporary],
                                 capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1)
            self.assertIn("20260901", json.loads(bad.stdout)["error"])
