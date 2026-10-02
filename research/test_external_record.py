import json
from pathlib import Path
import tempfile
import unittest

import record_external


class ExternalRecordTest(unittest.TestCase):
    def test_official_result_and_interruption(self):
        task = json.loads(record_external.ROSTER.read_text())["tasks"][0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "candidate"
            evidence.mkdir()
            driver = {"task_id": task["instance_id"], "arm": "kryn",
                      "base_commit": task["base_commit"],
                      "prompt_sha256": task["prompt_sha256"], "timeout_seconds": 900,
                      "completed": True, "requests": [],
                      "resources": {"telemetry_complete": True,
                                    "warning_or_critical_observed": False,
                                    "swap_peak_growth_bytes": 0}}
            (evidence / "driver.json").write_text(json.dumps(driver))
            patch = "diff --git a/example b/example\n"
            (evidence / "model.patch").write_text(patch)
            prediction = root / "prediction.json"
            prediction.write_text(json.dumps([{"instance_id": task["instance_id"],
                                               "model_patch": patch}]))
            run = root / "run-1"
            grade = run / "model" / task["instance_id"]
            grade.mkdir(parents=True)
            official_patch = grade / "patch.diff"
            official_patch.write_text(patch)
            (grade / "report.json").write_text(json.dumps({task["instance_id"]: {"resolved": True}}))
            official = run / "results.json"
            official.write_text(json.dumps({"submitted_ids": [task["instance_id"]],
                                            "resolved_ids": [task["instance_id"]]}))
            row = record_external.receipt(evidence, official, prediction, official_patch, "run-1")
            self.assertTrue(row["accepted"])
            self.assertNotIn(str(root), json.dumps(row))
            self.assertEqual(record_external.edited_tests(
                "diff --git a/tests/test_api.py b/tests/test_api.py\n"), ["tests/test_api.py"])
            self.assertEqual(record_external.edited_tests(
                "diff --git a/tests/test_new.py b/tests/test_new.py\n"
                "new file mode 100644\n--- /dev/null\n+++ b/tests/test_new.py\n"
                "@@ -0,0 +1 @@\n+new test\n"), [])
            forbidden = "diff --git a/tests/test_api.py b/tests/test_api.py\n"
            (evidence / "model.patch").write_text(forbidden)
            official_patch.write_text(forbidden)
            prediction.write_text(json.dumps([{"instance_id": task["instance_id"],
                                               "model_patch": forbidden}]))
            self.assertFalse(record_external.receipt(
                evidence, official, prediction, official_patch, "run-1")["accepted"])
            (evidence / "model.patch").write_text(patch)
            official_patch.write_text(patch)
            prediction.write_text(json.dumps([{"instance_id": task["instance_id"],
                                               "model_patch": patch}]))
            official_patch.write_text("wrong")
            with self.assertRaisesRegex(ValueError, "evaluator patch differs"):
                record_external.receipt(evidence, official, prediction, official_patch, "run-1")
            official_patch.write_text(patch)
            with self.assertRaisesRegex(ValueError, "declared evaluator run"):
                record_external.receipt(evidence, official, prediction, official_patch, "run-2")
            (grade / "report.json").write_text(json.dumps({task["instance_id"]: {"resolved": False}}))
            with self.assertRaisesRegex(ValueError, "per-task report"):
                record_external.receipt(evidence, official, prediction, official_patch, "run-1")
            (grade / "report.json").write_text(json.dumps({task["instance_id"]: {"resolved": True}}))
            database = root / "history.jsonl"
            record_external.append(database, row)
            with self.assertRaisesRegex(ValueError, "already recorded"):
                record_external.append(database, row)
            with self.assertRaisesRegex(ValueError, "exception name"):
                record_external.append(database, {**row, "error": "failed at /home/person/secret"})
            with self.assertRaisesRegex(ValueError, "unsafe test path"):
                record_external.append(database, {**row, "edited_test_paths": ["/tmp/secret"]})
            with self.assertRaisesRegex(ValueError, "unsafe test path"):
                record_external.append(database, {**row, "edited_test_paths": ["../secret/test_a.py"]})
            driver["intervention"] = "resource_guard"
            (evidence / "driver.json").write_text(json.dumps(driver))
            self.assertFalse(record_external.receipt(
                evidence, official, prediction, official_patch, "run-1")["accepted"])
            driver["prompt_sha256"] = "wrong"
            (evidence / "driver.json").write_text(json.dumps(driver))
            with self.assertRaisesRegex(ValueError, "frozen task"):
                record_external.receipt(evidence, official, prediction, official_patch, "run-1")


if __name__ == "__main__":
    unittest.main()
