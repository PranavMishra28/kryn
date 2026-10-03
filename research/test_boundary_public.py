"""Security regression checks for the disposable public boundary grader."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from run_boundary_public import grade


@unittest.skipUnless(sys.platform == "darwin", "Seatbelt is macOS-only")
class PublicGraderBoundaryTest(unittest.TestCase):
    def test_reference_is_hidden_and_output_is_bounded(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            root = Path(temporary)
            workspace, private, grader = (root / name for name in
                                           ("workspace", "private", "grader"))
            for directory in (workspace, private, grader):
                directory.mkdir()
            oracle = grader / "oracle.json"
            oracle.write_text(json.dumps([{"input": [1, 2], "expected": 3}]))
            reference = grader / "reference.py"
            reference.write_text("import json,sys\nprint(sum(json.load(sys.stdin)))\n")
            candidate = workspace / "solve.py"
            candidate.write_text(reference.read_text())
            self.assertTrue(grade(workspace, private, oracle))
            self.assertTrue(grade(workspace, private, oracle, reference))

            candidate.write_text("exec(open(" + repr(str(reference)) + ").read())\n")
            self.assertFalse(grade(workspace, private, oracle))
            candidate.write_text('print("x" * 1000000)\n')
            self.assertFalse(grade(workspace, private, oracle))

            candidate.write_text(
                "import json,sys,subprocess,pathlib\n"
                "child=subprocess.Popen(['/bin/sleep','30'])\n"
                "pathlib.Path('child.pid').write_text(str(child.pid))\n"
                "print(sum(json.load(sys.stdin)))\n")
            self.assertTrue(grade(workspace, private, oracle))
            child_pid = int((workspace / "child.pid").read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)


if __name__ == "__main__":
    unittest.main()
