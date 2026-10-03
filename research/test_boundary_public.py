"""Security regression checks for the disposable public boundary grader."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from run_boundary_public import grade, model_check_succeeded


@unittest.skipUnless(sys.platform == "darwin", "Seatbelt is macOS-only")
class PublicGraderBoundaryTest(unittest.TestCase):
    def test_model_check_reads_observed_shell_exit(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            events = Path(temporary) / "events.jsonl"
            def entry(command, exit_code):
                return {"part": {"type": "tool", "tool": "shell", "state": {
                    "status": "completed", "input": {"command": command},
                    "output": "0\n", "metadata": {"metadata": {"exit": exit_code}}}}}
            events.write_text(json.dumps(entry("python3 solve.py", 1)) + "\n")
            self.assertFalse(model_check_succeeded(events))
            with events.open("a") as stream:
                stream.write(json.dumps(entry("echo '[]' | python3 solve.py", 0)) + "\n")
            self.assertTrue(model_check_succeeded(events))

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
