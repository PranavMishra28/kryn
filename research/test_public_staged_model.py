"""Negative controls for the public staged acceptance checks."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from run_public_staged_model import (event_metrics, functional_rejection,
                                     prompts_retained, read_before_edit)
from staged_docker_grade import MAX_SOURCE, source_bytes


class StagedEvidenceTest(unittest.TestCase):
    def check(self, rows, stage):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "events.jsonl"
            path.write_text("".join(json.dumps({"part": row}) + "\n" for row in rows))
            return read_before_edit(path, stage), event_metrics(path)

    def test_requires_current_rules_read_before_edit(self):
        read = lambda path: {"type": "tool", "tool": "read", "state": {
            "status": "completed", "input": {"path": "/workspace/" + path}}}
        edit = {"type": "tool", "tool": "edit", "state": {"status": "completed",
                "input": {"path": "/workspace/solve.py"}}}
        self.assertTrue(self.check([read("solve.py"), read("rules.json"), edit], 1)[0]["passed"])
        self.assertFalse(self.check([read("solve.py"), edit, read("rules.json")], 3)[0]["passed"])
        failed = dict(read("rules.json"))
        failed["state"] = dict(failed["state"], status="error")
        self.assertFalse(self.check([failed, edit], 3)[0]["passed"])

    def test_token_and_error_counts(self):
        rows = [{"type": "tool", "tool": "shell", "state": {"status": "error", "input": {}}},
                {"type": "step-finish", "tokens": {"input": 10, "output": 3,
                    "reasoning": 2, "cache": {"read": 4, "write": 1}}}]
        _, metrics = self.check(rows, 2)
        self.assertEqual(metrics["tool_errors"], 1)
        self.assertEqual(metrics["tokens"], {"input": 10, "output": 3,
            "reasoning": 2, "cache_read": 4, "cache_write": 1})

    def test_failed_shell_read_and_shell_write_are_not_read_evidence(self):
        def shell(command, code):
            return {"type": "tool", "tool": "shell", "state": {
                "status": "completed", "input": {"command": command},
                "metadata": {"metadata": {"exit": code}}}}
        result, _ = self.check([shell("cat rules.json", 1),
                                shell("cat > solve.py", 0)], 3)
        self.assertFalse(result["passed"])

    def test_quoted_prompts_use_native_text_field(self):
        prompt = 'Return {"value":"ok"}.'
        history = {"messages": [{"type": "user", "text": prompt},
                                {"type": "assistant", "text": "done"}]}
        self.assertEqual(prompts_retained(history, [prompt]), [True])
        history["messages"].append({"type": "user", "text": prompt})
        self.assertEqual(prompts_retained(history, [prompt]), [False])

    def test_stage_source_rejects_link_fifo_and_oversize(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "solve.py").write_bytes(b"valid")
            self.assertEqual(source_bytes(root, "solve.py"), b"valid")
            (root / "link.py").symlink_to(root / "solve.py")
            with self.assertRaises(OSError):
                source_bytes(root, "link.py")
            os.mkfifo(root / "pipe.py")
            with self.assertRaises(RuntimeError):
                source_bytes(root, "pipe.py")
            (root / "large.py").write_bytes(b"x" * (MAX_SOURCE + 1))
            with self.assertRaises(RuntimeError):
                source_bytes(root, "large.py")

    def test_negative_control_requires_valid_execution(self):
        valid = {"passed": False, "candidate_source_unchanged": True,
                 "cases": [{"passed": False, "exit": 0, "cause": None,
                            "valid_json": True}]}
        self.assertTrue(functional_rejection(valid))
        for change in ({"exit": 1}, {"cause": "timeout"}, {"valid_json": False}):
            invalid = dict(valid, cases=[dict(valid["cases"][0], **change)])
            self.assertFalse(functional_rejection(invalid))


if __name__ == "__main__":
    unittest.main()
