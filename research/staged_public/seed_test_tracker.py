import unittest

from tracker import Tracker


class TrackerTest(unittest.TestCase):
    def test_add_and_list(self):
        tracker = Tracker()
        self.assertEqual(tracker.add(" first "), 1)
        self.assertEqual(tracker.add("second"), 2)
        self.assertEqual(tracker.list_items(), [
            {"id": 1, "title": "first", "done": False},
            {"id": 2, "title": "second", "done": False},
        ])


if __name__ == "__main__":
    unittest.main()
