"""Negative controls for the public staged acceptance checks."""
import json
from pathlib import Path
import tempfile
import unittest

from run_public_staged_model import event_metrics, prompts_retained, read_before_edit


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


if __name__ == "__main__":
    unittest.main()
