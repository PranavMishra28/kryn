import unittest

from legacy import parse_legacy_id


class LegacyTest(unittest.TestCase):
    def test_hash_prefix(self):
        self.assertEqual(parse_legacy_id(" #12 "), 12)


if __name__ == "__main__":
    unittest.main()
