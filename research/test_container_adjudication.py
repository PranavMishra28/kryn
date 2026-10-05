"""Receipt adversaries for strict container development adjudication; no Docker or model."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research import container_adjudication as audit
from research.local_only import MODEL


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


class AdjudicationTests(unittest.TestCase):
    def terminal(self, campaign, arm, started, finished, terminal):
        state = campaign / "state"
        pin_start = write(state / f"{arm}.generation-start.json", {
            "arm": arm, "phase": "generation", "manifest_sha256": audit.digest_file(campaign / "manifest.json"),
            "argv": [str(audit.EVALUATOR), "-B", "-m", "research.container_generation",
                     str(campaign), arm], "started_unix": started})
        pin_finish = write(state / f"{arm}.generation-exit.json", {
            "finished_unix": finished, "returncode": 0, "reason": None})
        driver = write(campaign / arm / "driver.json", {"completed": True})
        write(state / f"{arm}.json", {
            "status": "terminal", "manifest_sha256": audit.digest_file(campaign / "manifest.json"),
            "generation": driver, "grade": None, "recovery": None, "reason": None,
            "terminal_unix": terminal, "controller": {"start": pin_start, "finish": pin_finish}})
        return driver

    def test_changed_terminal_pin_is_unscored_and_final_is_append_only(self):
        with tempfile.TemporaryDirectory() as folder:
            campaign = Path(folder).resolve()
            write(campaign / "manifest.json", {"kind": "test"})
            native = self.terminal(campaign, "native", 1, 2, 3)
            self.terminal(campaign, "kryn", 4, 5, 6)
            Path(native["path"]).write_text('{"completed":false}')
            with patch.object(audit, "campaign_manifest", return_value=({"arm_order": ["native", "kryn"]}, "frozen")), patch.object(
                    audit, "classify_arm", return_value={"category": "accepted", "accepted": True}) as classify:
                result = audit.adjudicate(campaign)
            self.assertEqual(result["arms"]["native"]["category"], "unscored")
            self.assertEqual(result["arms"]["kryn"]["category"], "accepted")
            self.assertFalse(result["pair_comparable"])
            classify.assert_called_once()
            with self.assertRaisesRegex(audit.InvalidEvidence, "already_final"):
                audit.adjudicate(campaign)

    def test_incomplete_arm_cannot_be_finalized(self):
        with tempfile.TemporaryDirectory() as folder:
            campaign = Path(folder).resolve()
            write(campaign / "manifest.json", {})
            self.terminal(campaign, "native", 1, 2, 3)
            with patch.object(audit, "campaign_manifest", return_value=({"arm_order": ["native", "kryn"]}, "frozen")):
                with self.assertRaises(OSError):
                    audit.adjudicate(campaign)
            self.assertFalse((campaign / "adjudication.json").exists())

    def test_campaign_order_contract_keeps_other_frozen_checks_required(self):
        manifest = {"kind": "swe_container_development", "wall_seconds": 900,
                    "request_seconds": 360, "task": {}, "source_sha256": {"changed": "source"}}
        for order in (["native", "kryn"], ["kryn", "native"], [], ["native"],
                      ["native", "native"], ["kryn", "kryn"], ["other", "kryn"],
                      ["native", "kryn", "native"], None, "native,kryn"):
            with self.subTest(order=order), patch.object(audit, "sealed",
                    return_value=({**manifest, "arm_order": order}, "frozen")), patch.object(
                    audit, "source_inputs", return_value={}) as source:
                valid = order in (["native", "kryn"], ["kryn", "native"])
                with self.assertRaisesRegex(audit.InvalidEvidence,
                        "frozen_source_drift" if valid else "campaign_contract"):
                    audit.campaign_manifest(Path("/unused"))
                self.assertEqual(source.call_count, 1 if valid else 0)

    def test_adjudication_uses_declared_order_and_unscored_actual_order_mismatch(self):
        for order in (["native", "kryn"], ["kryn", "native"]):
            for actual in (order, order[::-1]):
                with self.subTest(declared=order, actual=actual), tempfile.TemporaryDirectory() as folder:
                    campaign = Path(folder).resolve()
                    manifest = {"arm_order": order}
                    write(campaign / "manifest.json", manifest)
                    self.terminal(campaign, actual[0], 1, 2, 3)
                    self.terminal(campaign, actual[1], 4, 5, 6)
                    with patch.object(audit, "campaign_manifest", return_value=(manifest, "frozen")), patch.object(
                            audit, "classify_arm", return_value={"category": "accepted", "accepted": True}) as classify:
                        result = audit.adjudicate(campaign)
                    if actual == order:
                        self.assertTrue(result["pair_comparable"])
                        self.assertEqual([call.args[1] for call in classify.call_args_list], order)
                    else:
                        classify.assert_not_called()
                        self.assertFalse(result["pair_comparable"])
                        self.assertTrue(all(row == {"category": "unscored", "accepted": None,
                            "reason": "arm_order_invalid"} for row in result["arms"].values()))

    def test_false_session_completion_is_unscored(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sid = "ses_example"
            write(root / f"{sid}.export.json", {"data": {"info": {
                "id": sid, "parentID": None, "model": {"providerID": "local", "id": "qwen"},
                "location": {"directory": "/testbed"}, "outcome": "succeeded"},
                "messages": [{"type": "assistant", "finish": "tool-calls",
                              "model": {"providerID": "local", "id": "qwen"},
                              "time": {"created": 1, "completed": 2}, "content": []},
                             {"type": "idle", "outcome": "succeeded"}]}})
            driver = {"session_id": sid, "settlement": {"verified_sessions": [sid]},
                      "ownership": {"verified": True, "sessions": [{"session_id": sid, "owned": True}]},
                      "generation": {"verified": True, "sessions": [{"session_id": sid, "complete": True}]}}
            with self.assertRaisesRegex(audit.InvalidEvidence, "session_not_terminal_success"):
                audit.exports(root, driver, complete=True)

    def test_completed_compaction_without_end_timestamp_is_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            root, sid = Path(folder), "ses_example"
            model = {"providerID": "local", "id": "qwen"}
            write(root / f"{sid}.export.json", {"data": {"info": {
                "id": sid, "parentID": None, "model": model,
                "location": {"directory": "/testbed"}, "outcome": "succeeded",
                "time": {"idle": 4}}, "messages": [
                    {"type": "compaction", "status": "completed", "model": model,
                     "time": {"created": 1}},
                    {"type": "assistant", "finish": "stop", "model": model,
                     "time": {"created": 2, "completed": 3}, "content": []},
                    {"type": "idle", "outcome": "succeeded", "time": {"created": 4}}]}})
            driver = {"session_id": sid, "settlement": {"verified_sessions": [sid]},
                      "ownership": {"verified": True, "sessions": [{"session_id": sid, "owned": True}]},
                      "generation": {"verified": True, "sessions": [{"session_id": sid, "complete": True}]}}
            audit.exports(root, driver, complete=True)

    def test_full_wire_mismatch_and_relay_rejection_are_unscored(self):
        expected = {"body_controls_sha256": "a" * 64,
                    "tool_schema_sha256s": ["b" * 64, "c" * 64]}
        row = {"model": MODEL, "tool_count": 1,
               "body_controls_sha256": expected["body_controls_sha256"],
               "tool_schema_canonical_sha256": "b" * 64}
        driver = {"requests": [row], "wire": {"matches_frozen": True},
                  "relay_rejections": {"request_rejection": None, "wire_rejection": None}}
        audit.wire(driver, expected, complete=True)
        with self.assertRaisesRegex(audit.InvalidEvidence, "wire_mismatch"):
            audit.wire({**driver, "requests": [{**row, "body_controls_sha256": "d" * 64}]},
                       expected, complete=True)
        with self.assertRaisesRegex(audit.InvalidEvidence, "relay_rejected_request"):
            audit.wire({**driver, "relay_rejections": {"request_rejection": "blocked",
                                                       "wire_rejection": None}}, expected, complete=True)

    def test_clean_timeout_resolved_still_strict_failure(self):
        state = {"generation": {"path": "present"}, "grade": {"path": "present"},
                 "recovery": None, "_controller_finish": {"returncode": 1}}
        generation = {"driver": {}, "patch": b"nonempty", "timeout": True, "complete": False}
        with patch.object(audit, "generation", return_value=generation), patch.object(
                audit, "grade", return_value={"resolved": True}):
            result = audit.classify_arm(Path("/unused"), "native", {}, state)
        self.assertEqual(result["category"], "strict_failure")
        self.assertIs(result["accepted"], False)
        self.assertIs(result["official_resolved"], True)

    def test_invalid_test_edit_or_wire_is_unscored_not_strict_failure(self):
        patch_text = "diff --git a/tests/test_app.py b/tests/test_app.py\n--- a/tests/test_app.py\n+++ b/tests/test_app.py\n@@ -1 +1 @@\n-a\n+b\n"
        self.assertEqual(audit.test_edits(patch_text), ["tests/test_app.py"])
        state = {"generation": {"path": "present"}, "grade": None, "recovery": None,
                 "_controller_finish": {"returncode": 0}}
        for reason in ("existing_tests_changed", "wire_mismatch"):
            with self.subTest(reason=reason), patch.object(audit, "generation",
                    side_effect=audit.InvalidEvidence(reason)):
                result = audit.classify_arm(Path("/unused"), "native", {}, state)
            self.assertEqual(result["category"], "unscored")
            self.assertIsNone(result["accepted"])

    def test_no_change_is_strict_failure_only_with_clean_state(self):
        with tempfile.TemporaryDirectory() as folder:
            campaign = Path(folder)
            state = {"generation": {"path": "present"}, "grade": None, "recovery": None,
                     "reason": "no_change", "_controller_finish": {"returncode": 0}}
            generation = {"driver": {}, "patch": b"", "timeout": False, "complete": True}
            with patch.object(audit, "generation", return_value=generation):
                self.assertEqual(audit.classify_arm(campaign, "native", {}, state)["category"],
                                 "strict_failure")
                write(campaign / "state/native.grader-start.json", {})
                self.assertEqual(audit.classify_arm(campaign, "native", {}, state)["category"],
                                 "unscored")


if __name__ == "__main__":
    unittest.main()
