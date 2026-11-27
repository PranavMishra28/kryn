import unittest
from taskboard_lite.report import summarize
from datetime import date

class TestSummarize(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {'date': '2026-09-01', 'project': 'Project A', 'minutes': 60},
            {'date': '2026-09-01', 'project': 'Project B', 'minutes': 30},
            {'date': '2026-09-02', 'project': 'Project A', 'minutes': 45},
            {'date': '2026-09-02', 'project': 'Project B', 'minutes': 90},
            {'date': '2026-09-03', 'project': 'Project A', 'minutes': 120},
        ]
    
    def test_summarize_all(self):
        result = summarize(self.rows)
        self.assertEqual(result['count'], 5)
        self.assertEqual(result['minutes'], 345)
    
    def test_summarize_project_a(self):
        result = summarize(self.rows, project='Project A')
        self.assertEqual(result['count'], 3)
        self.assertEqual(result['minutes'], 225)
    
    def test_summarize_project_b(self):
        result = summarize(self.rows, project='Project B')
        self.assertEqual(result['count'], 2)
        self.assertEqual(result['minutes'], 120)
    
    def test_summarize_date_range(self):
        result = summarize(self.rows, start=date(2026, 9, 1), end=date(2026, 9, 2))
        self.assertEqual(result['count'], 4)
        self.assertEqual(result['minutes'], 225)

if __name__ == '__main__':
    unittest.main()