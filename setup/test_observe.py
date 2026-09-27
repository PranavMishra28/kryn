"""Evaluator observations must keep failed history without blessing changed source."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
import observe


class ObservationTests(unittest.TestCase):
    def test_source_change_failure_lineage_and_report_integrity(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "trial"
            workspace = run / "workspace"
            folder = run / "evidence" / "observations"
            workspace.mkdir(parents=True)
            folder.mkdir(parents=True)
            (run / "run.json").write_text('{"task":"06"}')
            (workspace / "app.js").write_text("broken\n")
            subprocess.run(["git", "init", "-q", str(workspace)], check=True)
            subprocess.run(["git", "add", "app.js"], cwd=workspace, check=True)
            old = observe.source_state(workspace)

            def add(number, source, outcome, failure=None, kind="browser", scope="06:base"):
                report = folder / f"{number}.report.json"
                report.write_text(json.dumps({"outcome": outcome}))
                record = {"kind": kind, "scope": scope, "source_after": source, "result": {
                    "status": outcome, "failures": failure or [], "checks": []},
                    "report": str(report.relative_to(run)), "report_sha256": observe.digest(report.read_bytes())}
                (folder / f"{number}.json").write_text(json.dumps(record))
                return report

            failed_report = add(1, old, "FAIL", [{"check": "503", "error": "No POST was sent"}])
            (workspace / "app.js").write_text("fixed\n")
            current = observe.source_state(workspace)
            add(2, current, "PASS")
            add(3, current, "FAIL", [{"check": "automatic", "error": "secret grader traceback"}], "grade", "06")
            add(4, current, "FAIL", [{"check": "stored HTML", "error": "executed markup"}],
                scope="06:--stored-html")
            with patch.object(observe, "run_path", return_value=run):
                summary = observe.compact_status("trial")
                self.assertEqual(summary["current"]["browser:06:base"]["status"], "PASS")
                self.assertEqual(summary["current"]["browser:06:--stored-html"]["status"], "FAIL")
                self.assertNotIn("stored HTML", json.dumps(summary["historical_failures"]))
                self.assertNotIn("secret grader traceback", json.dumps(summary))
                self.assertEqual(summary["historical_failures"][0]["failures"][0]["error"], "No POST was sent")
                self.assertFalse(summary["historical_failures"][0]["current_source"])
                self.assertEqual(summary["total_observations"], 4)
                (run / "review.json").write_text("{}")
                self.assertIsNone(observe.compact_status("trial")["current"]["grade:06"])
                failed_report.write_text("tampered")
                self.assertFalse(observe.status("trial")["history"][0]["report_intact"])
                (workspace / "app.js").write_text("changed again\n")
                self.assertIsNone(observe.compact_status("trial")["current"]["browser:06:base"])


if __name__ == "__main__":
    unittest.main()
