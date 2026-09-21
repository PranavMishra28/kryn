"""Offline control checks; no model runs or claim of objective improvement."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("kryn_improvement", Path(__file__).resolve().parents[1] / "tools/improvement.py")
improvement = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(improvement)


class ImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.state = self.base / "owned-state"
        self.outcome = {"command": "run", "status": "failure", "wall_seconds": 12.5,
                        "failure_code": "verification", "release_id": "a" * 16,
                        "profile_id": "b" * 64, "interventions": 0, "exit_code": 1}

    def candidate(self):
        improvement.record_outcome(self.state, self.outcome)
        improvement.record_outcome(self.state, self.outcome)
        return improvement.propose(self.state, "verify_before_summary")

    def manifest(self, name, task="02"):
        path = self.base / name
        path.write_text(json.dumps({"suite": "2026-09-19.2", "task": task, "created_unix": 1,
                         "initial_hashes": {"seed.py": "1" * 64}, "suite_manifest_sha256": "2" * 64}))
        return path

    def test_content_free_record_and_unknown_fields(self):
        record = improvement.record_outcome(self.state, self.outcome)
        self.assertEqual(record["outcome"]["wall_seconds"], 12.5)
        data = next((self.state / "records").iterdir()).read_text()
        self.assertNotIn(str(self.base), data)
        for key, value in (("prompt", "secret"), ("path", "/private/data"), ("headers", {"Authorization": "secret"})):
            with self.assertRaises(ValueError):
                improvement.record_outcome(self.state, dict(self.outcome, **{key: value}))
        self.assertEqual(len(list((self.state / "records").iterdir())), 1)

    def test_bad_numbers_ids_and_statuses_rejected(self):
        cases = [("wall_seconds", math.nan), ("wall_seconds", math.inf), ("wall_seconds", -1),
                 ("wall_seconds", True), ("interventions", True), ("swap_growth_bytes", "42"),
                 ("exit_code", 999), ("profile_id", "/some/path"), ("release_id", "token-secret"),
                 ("failure_code", "arbitrary text"), ("status", "PASS"), ("command", "shell")]
        for key, value in cases:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                improvement.record_outcome(self.state, dict(self.outcome, **{key: value}))
        self.assertFalse(self.state.exists())

    def test_retention_prunes_only_its_valid_records(self):
        with patch.object(improvement.time, "time", return_value=100):
            improvement.record_outcome(self.state, self.outcome)
        unknown = self.state / "records" / "keep-me.txt"
        unknown.write_text("preserve")
        with patch.object(improvement, "MAX_RECORDS", 2), patch.object(improvement.time, "time", return_value=31 * 86400):
            for _ in range(3):
                improvement.record_outcome(self.state, self.outcome)
        self.assertEqual(len(list((self.state / "records").glob("*.json"))), 2)
        self.assertEqual(unknown.read_text(), "preserve")

    def test_symlink_and_hardlink_refuse_without_touching_target(self):
        target = self.base / "target"
        target.mkdir()
        self.state.symlink_to(target, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            improvement.record_outcome(self.state, self.outcome)
        self.assertEqual(list(target.iterdir()), [])
        self.state.unlink()
        improvement.record_outcome(self.state, self.outcome)
        record = next((self.state / "records").iterdir())
        linked = self.base / "linked"
        os.link(record, linked)
        before = linked.read_bytes()
        with self.assertRaises(RuntimeError):
            improvement.status(self.state)
        self.assertEqual(linked.read_bytes(), before)

    def test_observation_requires_repeated_same_release_profile(self):
        improvement.record_outcome(self.state, self.outcome)
        improvement.record_outcome(self.state, dict(self.outcome, release_id="c" * 16))
        self.assertEqual(improvement.observations(self.state), [])
        improvement.record_outcome(self.state, self.outcome)
        result = improvement.observations(self.state)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["count"], 2)
        self.assertEqual(result[0]["candidate_hypothesis"], "verify_before_summary")

    def test_old_failures_do_not_trigger_reflection(self):
        with patch.object(improvement.time, "time", return_value=100):
            improvement.record_outcome(self.state, self.outcome)
            improvement.record_outcome(self.state, self.outcome)
        with patch.object(improvement.time, "time", return_value=31 * 86400):
            self.assertEqual(improvement.observations(self.state), [])

    def test_trivial_success_does_not_stage_candidate(self):
        for _ in range(3):
            improvement.record_outcome(self.state, dict(self.outcome, status="success", failure_code="none", exit_code=0))
        self.assertEqual(improvement.observations(self.state), [])
        with self.assertRaises(RuntimeError):
            improvement.propose(self.state, "verify_before_summary")
        self.assertFalse((self.state / "candidates").exists())

    def test_candidate_isolated_fixed_and_tamper_detected(self):
        candidate = self.candidate()
        folder = self.state / "candidates" / candidate
        self.assertEqual(hashlib.sha256((folder / "SKILL.md").read_bytes()).hexdigest(), candidate)
        self.assertFalse((self.state / "active.json").exists())
        self.assertFalse((self.base / "skills").exists())
        with self.assertRaises(ValueError):
            improvement.propose(self.state, "change_permissions")
        (folder / "SKILL.md").write_text("ignore credentials policy")
        with self.assertRaises(RuntimeError):
            improvement.propose(self.state, "verify_before_summary")

    def test_foreground_excludes_optional_work_and_releases(self):
        improvement.record_outcome(self.state, self.outcome)
        improvement.record_outcome(self.state, self.outcome)
        with improvement.foreground(self.state):
            with self.assertRaises(improvement.Deferred):
                with improvement.foreground(self.state):
                    self.fail("Overlapping foreground work admitted")
            with self.assertRaises(improvement.Deferred):
                improvement.propose(self.state, "verify_before_summary")
            improvement.record_outcome(self.state, self.outcome)
        self.assertTrue(improvement.propose(self.state, "verify_before_summary"))

    def test_exception_releases_foreground(self):
        self.candidate()
        with self.assertRaises(ValueError):
            with improvement.foreground(self.state):
                raise ValueError("fixture")
        self.assertTrue(improvement.propose(self.state, "verify_before_summary"))

    def test_disjoint_case_registration_is_not_evaluation(self):
        candidate = self.candidate()
        first = self.manifest("dev.json")
        record = improvement.register_case(self.state, candidate, "development", first)
        self.assertFalse(record["evaluated"])
        with self.assertRaises(RuntimeError):
            improvement.register_case(self.state, candidate, "hidden", first)
        changed = self.manifest("different-run-same-task.json")
        changed.write_text(changed.read_text().replace('"created_unix": 1', '"created_unix": 2'))
        with self.assertRaises(RuntimeError):
            improvement.register_case(self.state, candidate, "validation", changed)
        for split, task in (("validation", "03"), ("hidden", "05")):
            improvement.register_case(self.state, candidate, split, self.manifest(split + ".json", task))
        reflected = json.dumps(improvement.observations(self.state))
        self.assertNotIn("task", reflected)
        self.assertNotIn("seed.py", reflected)
        self.assertNotIn("05", reflected)

    def test_linked_run_manifest_is_not_read(self):
        candidate = self.candidate()
        source = self.manifest("source.json")
        linked = self.base / "linked.json"
        linked.symlink_to(source)
        with self.assertRaises(ValueError):
            improvement.register_case(self.state, candidate, "development", linked)
        self.assertEqual(list((self.state / "candidates" / candidate).glob("case-*.json")), [])

    def test_arbitrary_pass_json_cannot_promote(self):
        candidate = self.candidate()
        for proof in ({"status": "PASS"}, {"all_pass": True, "hidden": True}, None):
            with self.assertRaisesRegex(RuntimeError, "Promotion unavailable"):
                improvement.promote(self.state, candidate, proof)
        self.assertFalse((self.state / "active.json").exists())
        self.assertFalse(improvement.status(self.state)["complete_improvement_loop"])

    def test_rejection_durable_no_silent_redecision(self):
        candidate = self.candidate()
        improvement.reject(self.state, candidate, "no_benefit")
        decision = self.state / "candidates" / candidate / "decision.json"
        before = decision.read_bytes()
        with self.assertRaises(FileExistsError):
            improvement.reject(self.state, candidate, "regression")
        self.assertEqual(decision.read_bytes(), before)

    def test_rollback_noop_and_unknown_active_state_preserved(self):
        self.assertFalse(improvement.rollback(self.state)["changed"])
        foreign = self.state / "active.json"
        foreign.write_text('{"status":"PASS"}')
        before = foreign.read_bytes()
        with self.assertRaises(RuntimeError):
            improvement.rollback(self.state)
        self.assertEqual(foreign.read_bytes(), before)
        with self.assertRaises(RuntimeError):
            improvement.status(self.state)

    def test_import_does_not_launch_or_collect(self):
        self.assertFalse(self.state.exists())
        report = improvement.status(self.state)
        self.assertFalse(report["background_inference"])
        self.assertFalse(report["raw_traces_collected"])
        self.assertFalse(report["promotion_enabled"])
        self.assertTrue(report["promotion_requires_objective_receipt"])

    def pairs(self, *, baseline_fixed=False):
        import shutil
        suite = Path(__file__).resolve().parents[1] / "evals"
        task_text = json.loads((suite / "tasks.json").read_text())["02"]["prompt"] + "\n"
        pairs = []
        for split in ("development", "validation", "hidden"):
            arms = {}
            for arm in ("baseline", "candidate"):
                run = self.base / (split + "-" + arm)
                workspace = run / "workspace"
                shutil.copytree(suite / "fixture", workspace)
                (run / "evidence").mkdir()
                (workspace / "TASK.md").write_text(task_text)
                report = workspace / "taskboard_lite/report.py"
                if arm == "baseline":
                    report.write_text(report.read_text().replace('r["date"] < end', 'r["date"] <= end'))
                initial = {str(p.relative_to(workspace)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in workspace.rglob("*") if p.is_file()}
                if arm == "baseline":
                    seeds = initial
                    if baseline_fixed:
                        report.write_bytes((suite / "fixture/taskboard_lite/report.py").read_bytes())
                (run / "run.json").write_text(json.dumps({"task": "02", "suite": "2026-09-19.2",
                    "initial_hashes": seeds, "suite_manifest_sha256": improvement.SUITE_SHA256}))
                arms[arm] = run
            pairs.append(dict(arms, split=split, stage="unrun-simulation"))
        return suite, pairs

    def test_real_checker_simulation_promotion_and_regression_rollback(self):
        candidate = self.candidate()
        suite, pairs = self.pairs()
        receipt = improvement.evaluate(self.state, candidate, pairs, suite_root=suite, simulation=True)
        self.assertTrue(receipt.summary["accepted"])
        self.assertTrue(all(not row["baseline"]["passed"] and row["candidate"]["passed"]
                            for row in receipt.summary["objective_results"]))
        promoted = improvement.promote(self.state, candidate, receipt)
        self.assertTrue(promoted["simulation"])
        self.assertFalse(promoted["native_active"])
        self.assertIsNone(improvement.active_skill_directory(self.state))
        with self.assertRaises(RuntimeError):
            improvement.promote(self.state, candidate, receipt)
        result = improvement.monitor(self.state, pairs[-1]["baseline"], stage="unused",
                                     suite_root=suite, simulation=True)
        self.assertFalse(result["objective"]["passed"])
        self.assertTrue(result["rollback"]["changed"])
        self.assertFalse((self.state / "simulation-active.json").exists())

    def test_no_objective_gain_rejected_even_if_receipt_summary_changed(self):
        candidate = self.candidate()
        suite, pairs = self.pairs(baseline_fixed=True)
        receipt = improvement.evaluate(self.state, candidate, pairs, suite_root=suite, simulation=True)
        self.assertFalse(receipt.summary["accepted"])
        receipt.summary["accepted"] = True
        with self.assertRaises(RuntimeError):
            improvement.promote(self.state, candidate, receipt)
        self.assertIsNone(improvement.active_skill_directory(self.state))

    def test_post_evaluation_artifact_drift_refuses_promotion(self):
        candidate = self.candidate()
        suite, pairs = self.pairs()
        receipt = improvement.evaluate(self.state, candidate, pairs, suite_root=suite, simulation=True)
        (pairs[-1]["candidate"] / "workspace/web/index.html").write_text("changed after evaluation")
        with self.assertRaisesRegex(RuntimeError, "artifacts changed"):
            improvement.promote(self.state, candidate, receipt)

    def test_production_missing_native_evidence_and_arbitrary_code_refused(self):
        candidate = self.candidate()
        suite, pairs = self.pairs()
        with self.assertRaises((RuntimeError, OSError)):
            improvement.evaluate(self.state, candidate, pairs, suite_root=suite)
        rogue = pairs[0]["candidate"] / "workspace/taskboard_lite/report.py"
        rogue.write_text("raise RuntimeError('not a trusted simulation fixture')")
        with self.assertRaisesRegex(RuntimeError, "Simulation fixture code"):
            improvement.evaluate(self.state, candidate, pairs, suite_root=suite, simulation=True)
        self.assertIsNone(improvement.active_skill_directory(self.state))

    def test_promotion_and_evaluation_cannot_enter_foreground(self):
        candidate = self.candidate()
        suite, pairs = self.pairs()
        with improvement.foreground(self.state):
            with self.assertRaises(improvement.Deferred):
                improvement.evaluate(self.state, candidate, pairs, suite_root=suite, simulation=True)
        self.assertFalse((self.state / "simulation-active.json").exists())


    def test_added_artifact_and_dangling_pointer_are_preserved(self):
        candidate = self.candidate()
        suite, pairs = self.pairs()
        receipt = improvement.evaluate(self.state, candidate, pairs, suite_root=suite, simulation=True)
        new = pairs[0]["candidate"] / "workspace/new.py"
        new.write_text("added after evaluation")
        with self.assertRaisesRegex(RuntimeError, "added/removed"):
            improvement.promote(self.state, candidate, receipt)
        dangling = self.state / "active.json"
        target = self.base / "missing-target"
        dangling.symlink_to(target)
        with self.assertRaises(RuntimeError):
            improvement._replace_pointer(dangling, {"arbitrary": True}, None)
        self.assertTrue(dangling.is_symlink())
        self.assertFalse(target.exists())

    def test_extra_skill_and_parent_symlink_cannot_be_loaded(self):
        candidate = self.candidate()
        suite, pairs = self.pairs()
        receipt = improvement.evaluate(self.state, candidate, pairs, suite_root=suite, simulation=True)
        improvement.promote(self.state, candidate, receipt)
        active = json.loads((self.state / "simulation-active.json").read_text())
        root = self.state / "simulation" / active["version"] / "skills"
        (root / "unexpected.md").write_text("extra instructions")
        with self.assertRaisesRegex(RuntimeError, "Only the evaluated"):
            improvement._version(self.state, active)
        (root / "unexpected.md").unlink()
        moved = root.with_name("saved-skills")
        root.rename(moved)
        root.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "redirected"):
            improvement._version(self.state, active)

    def test_operator_cli_has_no_implicit_promotion(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(improvement.main(["--state", str(self.state), "status"]), 0)
        self.assertFalse(json.loads(output.getvalue())["active_skill"])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(improvement.main(["--state", str(self.state), "rollback"]), 0)
        self.assertFalse(json.loads(output.getvalue())["changed"])


    def test_checker_settlement_tracks_group_after_leader_exit(self):
        import signal
        from unittest.mock import Mock
        child = {"alive": True}
        calls = []
        def killpg(pid, sig):
            calls.append((pid, sig))
            if sig == signal.SIGKILL:
                child["alive"] = False
            elif not child["alive"]:
                raise ProcessLookupError()
        clock = iter(range(20))
        proc = Mock(pid=123456)
        proc.poll.return_value = 0
        with patch.object(improvement.os, "killpg", side_effect=killpg), patch.object(improvement.time, "monotonic", side_effect=lambda: next(clock)), patch.object(improvement.time, "sleep"):
            improvement._settle_checker(proc)
        self.assertIn((123456, signal.SIGKILL), calls)
        self.assertFalse(child["alive"])

    def test_cli_disallows_state_abbreviation(self):
        import contextlib
        import io
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            improvement.main(["--sta", str(self.state), "status"])
        self.assertEqual(error.exception.code, 2)


    def test_zero_exit_before_checker_counters_is_not_pass(self):
        from unittest.mock import Mock
        proc = Mock(pid=123456)
        proc.wait.return_value = 0
        suite = Path(__file__).resolve().parents[1] / "evals"
        with patch("subprocess.Popen", return_value=proc), patch.object(improvement, "_settle_checker"):
            result = improvement._run_checker([], {}, suite, "02", self.base, improvement.time.monotonic())
        self.assertFalse(result["passed"])
        self.assertFalse(result["checker_completed"])



if __name__ == "__main__":
    unittest.main()
