import unittest

import summarize_external


class ExternalSummaryTest(unittest.TestCase):
    def test_preflight_excluded_and_pairs_required(self):
        tasks = [{"instance_id": "one"}, {"instance_id": "two"}]
        rows = [{"task_id": task, "arm": arm, "official_run_id": "graded",
                 "accepted": task == "one" and arm == "native", "wall_seconds": 60}
                for task in ("one", "two") for arm in ("kryn", "native")]
        rows.append({"task_id": "one", "arm": "native", "official_run_id": None,
                     "accepted": False, "wall_seconds": 10})
        result = summarize_external.summarize(tasks, rows, resamples=100)
        self.assertEqual(result["paired_deltas"], [-1, 0])
        self.assertEqual(result["arms"]["native"]["accepted"], 1)
        self.assertEqual(result["arms"]["native"]["generation_wall_seconds"], 120)
        with self.assertRaisesRegex(ValueError, "one graded"):
            summarize_external.summarize(tasks, rows[:-2])


if __name__ == "__main__":
    unittest.main()
