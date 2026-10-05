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
    def guard_evidence(self, root, source="Battery Power"):
        sample = {"pressure_level": 1, "power_source": source, "swap_used_bytes": 20,
                  "utc": "1970-01-01T00:00:01.100000+00:00"}
        power = {"unix": 1, "power_policy": "battery-capable", "ac": source == "AC Power",
                 "battery_percent": 40, "adapter_watts": 140 if source == "AC Power" else None,
                 "starting": True, "final": False, "reason": None}
        samples = [sample, {**sample, "utc": "1970-01-01T00:00:01.900000+00:00"}]
        powers = [power, {**power, "unix": 2, "starting": False, "final": True, "battery_percent": 26}]
        for name, rows in (("resources.jsonl", samples), ("power.jsonl", powers)):
            (root / name).write_text("".join(json.dumps(row) + "\n" for row in rows))
        summary = {"sample_count": 2, "telemetry_complete": True,
                   "warning_or_critical_observed": False, "swap_peak_growth_bytes": 0}
        return summary, samples, powers

    def test_battery_evidence_requires_explicit_policy_and_default_stays_ac_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            summary, _, _ = self.guard_evidence(root)
            audit.guard_samples(root, summary, power_policy="battery-capable")
            with self.assertRaisesRegex(audit.InvalidEvidence, "guard_pressure_or_power"):
                audit.guard_samples(root, summary)
            with self.assertRaisesRegex(audit.InvalidEvidence, "guard_power_policy"):
                audit.guard_samples(root, summary, power_policy="automatic")
            summary, _, _ = self.guard_evidence(root, "AC Power")
            audit.guard_samples(root, summary, power_policy="battery-capable")
            (root / "power.jsonl").unlink()
            audit.guard_samples(root, summary)  # Existing AC evidence needs no new receipt.
            with self.assertRaises(OSError):
                audit.guard_samples(root, summary, power_policy="battery-capable")

    def test_battery_power_receipts_reject_threshold_unknown_and_policy_drift(self):
        cases = [(0, {"battery_percent": 39}), (1, {"battery_percent": 25}),
                 (1, {"battery_percent": None}), (1, {"battery_percent": True}),
                 (1, {"ac": None}), (1, {"power_policy": "ac-only"}),
                 (1, {"reason": "battery_stop_floor"}), (1, {"starting": True}),
                 (0, {"unix": float("nan")}), (1, {"unix": float("inf")})]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for index, change in cases:
                with self.subTest(index=index, change=change):
                    summary, _, powers = self.guard_evidence(root)
                    powers[index].update(change)
                    (root / "power.jsonl").write_text("".join(json.dumps(row) + "\n" for row in powers))
                    with self.assertRaises(audit.InvalidEvidence):
                        audit.guard_samples(root, summary, power_policy="battery-capable")
            summary, _, powers = self.guard_evidence(root)
            del powers[1]["reason"]
            (root / "power.jsonl").write_text("".join(json.dumps(row) + "\n" for row in powers))
            with self.assertRaisesRegex(audit.InvalidEvidence, "guard_power_policy"):
                audit.guard_samples(root, summary, power_policy="battery-capable")

    def test_battery_policy_preserves_memory_and_final_guard_failures(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for change in ({"pressure_level": 2}, {"swap_used_bytes": 21},
                           {"power_source": None}, {"guard_reason": "listener changed"}):
                with self.subTest(change=change):
                    summary, samples, _ = self.guard_evidence(root)
                    samples[-1].update(change)
                    (root / "resources.jsonl").write_text("".join(json.dumps(row) + "\n" for row in samples))
                    with self.assertRaises(audit.InvalidEvidence):
                        audit.guard_samples(root, summary, power_policy="battery-capable")

    def test_power_receipt_must_end_and_cover_resource_samples(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for last_clock, final, expected in (
                    ("1970-01-01T00:00:01.900000+00:00", False, "guard_power_final"),
                    ("1970-01-01T00:00:06+00:00", True, "guard_power_coverage"),
                    ("1970-01-01T00:00:02", True, "guard_resource_clock"),
                    ("invalid", True, "guard_resource_clock")):
                with self.subTest(last_clock=last_clock, final=final):
                    summary, samples, powers = self.guard_evidence(root)
                    samples[-1]["utc"] = last_clock
                    powers[-1]["final"] = final
                    for name, rows in (("resources.jsonl", samples), ("power.jsonl", powers)):
                        (root / name).write_text("".join(json.dumps(row) + "\n" for row in rows))
                    with self.assertRaisesRegex(audit.InvalidEvidence, expected):
                        audit.guard_samples(root, summary, power_policy="battery-capable")
            summary, _, powers = self.guard_evidence(root)
            powers[0]["unix"], powers[1]["unix"] = 5, 6
            (root / "power.jsonl").write_text("".join(json.dumps(row) + "\n" for row in powers))
            with self.assertRaisesRegex(audit.InvalidEvidence, "guard_power_coverage"):
                audit.guard_samples(root, summary, power_policy="battery-capable")
            summary, samples, _ = self.guard_evidence(root)
            samples[-1]["utc"] = "1970-01-01T00:00:03.500000+00:00"
            (root / "resources.jsonl").write_text("".join(json.dumps(row) + "\n" for row in samples))
            audit.guard_samples(root, summary, power_policy="battery-capable")  # Bounded clock jitter.

    def test_manifest_power_policy_is_frozen_and_unknown_values_rejected(self):
        manifest = {"kind": "swe_container_development", "wall_seconds": 900,
                    "request_seconds": 360, "task": {}, "arm_order": ["native", "kryn"],
                    "source_sha256": {"changed": "source"}}
        for declared in ({}, {"power_policy": "ac-only"}, {"power_policy": "battery-capable"},
                         {"power_policy": None}, {"power_policy": "auto"}, {"power_policy": {}}):
            valid = not declared or declared["power_policy"] in ("ac-only", "battery-capable")
            with self.subTest(declared=declared), patch.object(audit, "sealed",
                    return_value=({**manifest, **declared}, "frozen")), patch.object(
                    audit, "source_inputs", return_value={}) as source:
                with self.assertRaisesRegex(audit.InvalidEvidence,
                        "frozen_source_drift" if valid else "campaign_power_policy"):
                    audit.campaign_manifest(Path("/unused"))
                self.assertEqual(source.call_count, 1 if valid else 0)

    def test_generation_cannot_relabel_ac_evidence_as_battery_capable(self):
        with tempfile.TemporaryDirectory() as folder:
            campaign = Path(folder)
            manifest = {"task": {"instance_id": "synthetic"}, "prompt_sha256": "frozen",
                        "power_policy": "battery-capable"}
            write(campaign / "manifest.json", manifest)
            write(campaign / "native/ownership.json", {})
            write(campaign / "native/driver.json", {"kind": "swe_container_generation", "arm": "native",
                "synthetic_inference": False, "manifest_sha256": audit.digest_file(campaign / "manifest.json"),
                "task_id": "synthetic", "prompt_sha256": "frozen"})
            with self.assertRaisesRegex(audit.InvalidEvidence, "generation_power_policy"):
                audit.generation(campaign, "native", manifest)

    def test_grader_manifest_must_use_generation_power_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            campaign = Path(folder)
            root = campaign / "grading/native"
            write(campaign / "state/native.grader-start.json", {"arm": "native", "phase": "grader",
                "manifest_sha256": "frozen", "started_unix": 3,
                "argv": [str(audit.EVALUATOR), "-B", "-m", "research.container_grader", str(root)]})
            write(campaign / "state/native.grader-exit.json", {
                "finished_unix": 4, "returncode": 0, "reason": None})
            state = {"manifest_sha256": "frozen", "terminal_unix": 5,
                     "_controller_finish": {"finished_unix": 2}}
            with patch.object(audit, "sealed", return_value=({}, "grade-manifest")):
                with self.assertRaisesRegex(audit.InvalidEvidence, "grade_power_policy"):
                    audit.grade(campaign, "native", {"power_policy": "battery-capable"}, {}, state)

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
