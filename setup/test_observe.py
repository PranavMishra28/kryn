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
    def test_browser_observation_keeps_only_bounded_post_statuses(self):
        report = {"pass": False, "manualRetryStarted": False,
                  "checks": [{"name": "retry", "pass": False, "error": "form cleared"}],
                  "network": [{"method": "POST", "url": "http://127.0.0.1:8765/api/entries?private=1", "status": 503},
                              {"method": "POST", "url": "http://127.0.0.1:8765/api/entries", "status": 201},
                              {"method": "GET", "url": "http://127.0.0.1:8765/api/entries", "status": 200}]}
        result = observe.observation("browser", report, 1)
        self.assertEqual(result["entry_post_statuses"], [503, 201])
        self.assertIs(result["manual_retry_started"], False)
        self.assertNotIn("private", json.dumps(result))
        report["network"] *= 5
        result = observe.observation("browser", report, 1)
        self.assertEqual(len(result["entry_post_statuses"]), 8)
        self.assertEqual(result["older_entry_posts_omitted"], 2)
        report["manualRetryStarted"] = "false"
        self.assertIsNone(observe.observation("browser", report, 1)["manual_retry_started"])

    def test_browser_evaluator_change_invalidates_fingerprint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "evals").mkdir()
            (root / "tools").mkdir()
            checker = root / "tools/browser_check.mjs"
            checker.write_text("first\n")
            with patch.object(observe, "ROOT", root / "evals"):
                before = observe.evaluator_sha256("browser")
                checker.write_text("second\n")
                self.assertNotEqual(before, observe.evaluator_sha256("browser"))

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

            def add(number, source, outcome, failure=None, kind="browser", scope="06:base", automatic=None, posts=(), retry=None):
                report = folder / f"{number}.report.json"
                report.write_text(json.dumps({"outcome": outcome}))
                record = {"kind": kind, "scope": scope, "source_after": source, "result": {
                    "status": outcome, "failures": failure or [], "checks": [],
                    "automatic": automatic,
                    "automatic_tests_run": 2 if kind == "grade" else None,
                    "entry_post_statuses": list(posts), "manual_retry_started": retry},
                    "evaluator_sha256": observe.evaluator_sha256(kind),
                    "report": str(report.relative_to(run)), "report_sha256": observe.digest(report.read_bytes())}
                (folder / f"{number}.json").write_text(json.dumps(record))
                return report

            failed_report = add(1, old, "FAIL", [{"check": "503", "error": "No POST was sent"}])
            (workspace / "app.js").write_text("fixed\n")
            current = observe.source_state(workspace)
            add(2, current, "PASS", posts=[201], retry=True)
            add(3, old, "FAIL", [{"check": "automatic", "error": "secret grader traceback"}], "grade", "06", False)
            add(4, current, "PARTIAL", kind="grade", scope="06", automatic=True)
            add(5, current, "FAIL", [{"check": "stored HTML", "error": "executed markup"}],
                scope="06:--stored-html")
            add(6, current, "FAIL", [{"check": "literal text", "error": "rendered text differs"}],
                scope="06:--stored-html")
            with patch.object(observe, "run_path", return_value=run):
                summary = observe.compact_status("trial")
                self.assertNotIn(str(run), json.dumps(summary))
                self.assertIn("evidence_id", summary["current"]["browser:06:base"])
                self.assertEqual(summary["current"]["browser:06:base"]["status"], "PASS")
                self.assertEqual(summary["current"]["browser:06:base"]["entry_post_statuses"], [201])
                self.assertIs(summary["current"]["browser:06:base"]["manual_retry_started"], True)
                self.assertNotIn("automatic_tests_run", summary["current"]["browser:06:base"])
                self.assertEqual(summary["current"]["browser:06:--stored-html"]["status"], "FAIL")
                self.assertEqual(summary["current"]["browser:06:--stored-html"]["failures"][0]["error"],
                                 "rendered text differs")
                self.assertTrue(summary["current"]["grade:06"]["automatic_passed"])
                self.assertEqual(summary["current"]["grade:06"]["automatic_tests_run"], 2)
                self.assertFalse(summary["current"]["grade:06"]["manual_review_record_present"])
                self.assertNotIn("stored HTML", json.dumps(summary["historical_failures"]))
                self.assertNotIn("executed markup", json.dumps(summary["historical_failures"]))
                self.assertEqual(summary["older_same_source_scope_failures_omitted"], 1)
                self.assertNotIn("secret grader traceback", json.dumps(summary))
                self.assertEqual(summary["historical_failures"][0]["failures"][0]["error"], "No POST was sent")
                self.assertFalse(summary["historical_failures"][0]["current_source"])
                self.assertEqual(summary["total_observations"], 6)
                original = {kind: observe.evaluator_sha256(kind) for kind in ("grade", "browser")}
                with patch.object(observe, "evaluator_sha256", side_effect=lambda kind: "0" * 64 if kind == "browser" else original[kind]):
                    changed = observe.compact_status("trial")
                    self.assertIsNone(changed["current"]["browser:06:base"])
                    self.assertIsNone(changed["current"]["browser:06:--stored-html"])
                    self.assertEqual(changed["current"]["grade:06"]["status"], "PARTIAL")
                    self.assertEqual(changed["stale_evaluator_records"], 3)
                    self.assertFalse(observe.status("trial")["history"][0]["current_evaluator"])
                legacy = folder / "4.json"
                item = json.loads(legacy.read_text())
                del item["evaluator_sha256"]
                legacy.write_text(json.dumps(item))
                changed = observe.compact_status("trial")
                self.assertIsNone(changed["current"]["grade:06"])
                self.assertEqual(changed["stale_evaluator_records"], 1)
                (run / "review.json").write_text("{}")
                self.assertIsNone(observe.compact_status("trial")["current"]["grade:06"])
                failed_report.write_text("tampered")
                self.assertFalse(observe.status("trial")["history"][0]["report_intact"])
                (workspace / "app.js").write_text("changed again\n")
                self.assertIsNone(observe.compact_status("trial")["current"]["browser:06:base"])


if __name__ == "__main__":
    unittest.main()
