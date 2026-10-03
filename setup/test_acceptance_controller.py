"""Contracts for the managed acceptance boundary; no model or browser starts."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from acceptance_controller import AcceptanceController, AcceptanceError, Requirement, repair_detail, source_revision


class FakeServer:
    def __init__(self, workspace):
        self.workspace = workspace
        self.messages = [{"id": "msg_old", "type": "idle", "outcome": "succeeded"}]
        self.sent = []

    def request(self, method, path, body=None, timeout=5):
        if method == "GET" and path == "/api/session/ses_test":
            return {"data": {"id": "ses_test", "agent": "agent",
                             "location": {"directory": str(self.workspace)}}}
        if method == "GET" and path.startswith("/api/session/ses_test/message?"):
            return {"data": self.messages}
        if method == "GET" and path == "/api/session/active":
            return {"data": {}}
        if method == "GET" and path in {"/api/session/ses_test/inbox",
                                         "/api/session/ses_test/permission",
                                         "/api/session/ses_test/form"}:
            return {"data": []}
        if method == "POST" and path in {"/api/session/ses_test/prompt",
                                          "/api/session/ses_test/synthetic"}:
            self.sent.append((path, body))
            number = len(self.sent)
            self.messages = [{"id": f"msg_idle{number}", "type": "idle", "outcome": "succeeded"},
                             {"id": f"msg_answer{number}", "type": "assistant", "content": [
                                 {"type": "text", "text": "All tests passed"}]}, *self.messages]
            return {"data": {"id": f"msg_input{number}"}}
        raise AssertionError((method, path))


class SequenceCheck:
    def __init__(self, statuses, id="ui", watch=("*",), detail="Observed UI failure"):
        self.id, self.watch = id, watch
        self.statuses = iter(statuses)
        self.detail = detail

    def affected_by(self, path):
        from fnmatch import fnmatchcase
        return any(fnmatchcase(path, pattern) for pattern in self.watch)

    def run(self, _workspace):
        return {"status": next(self.statuses), "detail": self.detail}


class ControllerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "project"
        self.workspace.mkdir()
        self.report = self.root / "private" / "result.json"
        self.server = FakeServer(self.workspace)
        self.requirements = [Requirement("requested-ui", "Original user request", ("ui",))]

    def controller(self, check, **options):
        return AcceptanceController(self.server, "ses_test", self.workspace, self.report,
                                    self.requirements, [check], poll_interval=0,
                                    revision=lambda _: "source-v1",
                                    state=lambda _: {"head": "fixture", "paths": {}}, **options)

    def test_failed_check_repairs_same_session_then_accepts(self):
        report = self.controller(SequenceCheck(["failed", "passed"]), max_repairs=1).run("Build the UI")
        self.assertEqual(report["state"], "accepted")
        self.assertTrue(report["accepted"])
        self.assertEqual([r["checks"]["ui"]["status"] for r in report["rounds"]],
                         ["failed", "passed"])
        self.assertEqual([p for p, _ in self.server.sent],
                         ["/api/session/ses_test/prompt", "/api/session/ses_test/synthetic"])
        self.assertIn("Observed UI failure", self.server.sent[1][1]["text"])
        self.assertEqual(json.loads(self.report.read_text()), report)

    def test_combined_verifier_feedback_reaches_both_failed_browser_flows(self):
        combined = json.dumps({"pass": False, "checks": {
            "source_and_api": {"pass": True, "output": "passing-check-canary " * 55},
            "task06_browser": {"pass": False, "observed": {
                "failures": ["Stored probe row must render exactly once"]}},
            "cancel_edit_browser": {"pass": False, "observed": {
                "failures": "Cancel Edit did not clear the form"}},
        }})
        self.assertNotIn("cancel_edit_browser", combined[:900])
        report = self.controller(SequenceCheck(["failed", "passed"], detail=combined),
                                 max_repairs=1).run("Build the UI")
        feedback = self.server.sent[1][1]["text"]
        self.assertTrue(report["accepted"])
        self.assertIn("task06_browser", feedback)
        self.assertIn("cancel_edit_browser", feedback)
        self.assertIn("Cancel Edit did not clear the form", feedback)
        self.assertNotIn("passing-check-canary", feedback)
        self.assertLess(len(feedback), 2000)
        self.assertEqual(report["rounds"][0]["checks"]["ui"]["detail"], combined)

    def test_unstructured_verifier_failure_remains_bounded(self):
        self.assertEqual(repair_detail("not JSON" * 200), ("not JSON" * 200)[:900])

    def test_model_claim_cannot_accept_failing_check(self):
        report = self.controller(SequenceCheck(["failed"] * 3), max_repairs=2).run("Build the UI")
        self.assertEqual(report["state"], "blocked")
        self.assertFalse(report["accepted"])
        self.assertEqual(len(report["rounds"]), 3)
        self.assertEqual(report["requirements"][0]["status"], "failed")
        self.assertEqual(len(self.server.sent), 3)

    def test_missing_coverage_is_rejected_before_prompt(self):
        with self.assertRaisesRegex(AcceptanceError, "declared check"):
            AcceptanceController(self.server, "ses_test", self.workspace, self.report,
                                 self.requirements, [])
        self.assertEqual(self.server.sent, [])

    def test_source_change_during_check_stales_prior_pass(self):
        revisions = iter(["v1", "v2", "v2", "v2", "v2"])
        controller = AcceptanceController(self.server, "ses_test", self.workspace, self.report,
                                          self.requirements, [SequenceCheck(["passed", "passed"])],
                                          max_repairs=1, poll_interval=0, revision=lambda _: next(revisions),
                                          state=lambda _: {"head": "fixture", "paths": {}})
        report = controller.run("Build the UI")
        self.assertEqual([r["checks"]["ui"]["status"] for r in report["rounds"]],
                         ["stale", "passed"])
        self.assertTrue(report["accepted"])

    def test_report_cannot_be_in_agent_workspace(self):
        with self.assertRaisesRegex(AcceptanceError, "outside"):
            AcceptanceController(self.server, "ses_test", self.workspace,
                                 self.workspace / "result.json", self.requirements,
                                 [SequenceCheck(["passed"])])

    def test_repository_requirement_is_admitted_without_verifier_commands(self):
        (self.workspace / "TASK.md").write_text("Preserve the browser flow.\n")
        req = Requirement("repo-task", "Preserve the browser flow.\n", ("ui",),
                          "ui", "TASK.md")
        controller = AcceptanceController(self.server, "ses_test", self.workspace, self.report,
                                          [req], [SequenceCheck(["passed"])],
                                          revision=lambda _: "v1",
                                          state=lambda _: {"head": "fixture", "paths": {}})
        admitted = controller.admission_text("Add Cancel Edit")
        self.assertIn("Preserve the browser flow", admitted)
        self.assertNotIn("SequenceCheck", admitted)
        report = controller.run("Add Cancel Edit", initial=("native-cli", "msg_old"),
                                admitted_prompt=admitted)
        self.assertTrue(report["accepted"])
        with self.assertRaisesRegex(AcceptanceError, "did not use"):
            controller.run("Add Cancel Edit", initial=("native-cli", "msg_old"),
                           admitted_prompt="Add Cancel Edit")

    def test_only_affected_pass_is_rechecked_after_repair(self):
        states = iter([{"head": "fixture", "paths": {"web/app.js": "a"}}] * 2 +
                      [{"head": "fixture", "paths": {"web/app.js": "b"}}] * 3)
        api = SequenceCheck(["passed"], id="api", watch=("taskboard_lite/*",))
        ui = SequenceCheck(["failed", "passed"], id="ui", watch=("web/*",))
        controller = AcceptanceController(self.server, "ses_test", self.workspace, self.report,
                                          [Requirement("whole-task", "Original request", ("api", "ui"))],
                                          [api, ui], max_repairs=1, poll_interval=0,
                                          revision=lambda _: "v1", state=lambda _: next(states))
        report = controller.run("Build the UI")
        self.assertTrue(report["accepted"])
        self.assertTrue(report["rounds"][1]["checks"]["api"]["reused"])
        self.assertFalse(report["rounds"][1]["checks"]["ui"]["reused"])

    def test_ui_edit_rechecks_prior_browser_pass_and_catches_regression(self):
        states = iter([{"head": "fixture", "paths": {"web/app.js": "a"}}] * 2 +
                      [{"head": "fixture", "paths": {"web/app.js": "b"}}] * 3)
        stored = SequenceCheck(["passed", "passed"], id="stored", watch=("web/*",))
        cancel = SequenceCheck(["passed", "failed"], id="cancel", watch=("web/*",))
        repair = SequenceCheck(["failed", "passed"], id="repair", watch=("web/*",))
        controller = AcceptanceController(
            self.server, "ses_test", self.workspace, self.report,
            [Requirement("ui-task", "Original request", ("stored", "cancel", "repair"))],
            [stored, cancel, repair], max_repairs=1, poll_interval=0,
            revision=lambda _: "v1", state=lambda _: next(states))
        report = controller.run("Build the UI")
        self.assertEqual(report["state"], "blocked")
        self.assertEqual(report["rounds"][1]["checks"]["stored"]["status"], "passed")
        self.assertFalse(report["rounds"][1]["checks"]["stored"]["reused"])
        self.assertEqual(report["rounds"][1]["checks"]["cancel"]["status"], "failed")

    def test_api_edit_rechecks_stateful_browser_flow(self):
        states = iter([{"head": "fixture", "paths": {"taskboard_lite/server.py": "a"}}] * 2 +
                      [{"head": "fixture", "paths": {"taskboard_lite/server.py": "b"}}] * 3)
        api = SequenceCheck(["failed", "passed"], id="api", watch=("taskboard_lite/*",))
        browser = SequenceCheck(["passed", "failed"], id="browser", watch=("*",))
        controller = AcceptanceController(
            self.server, "ses_test", self.workspace, self.report,
            [Requirement("stateful-task", "Original request", ("api", "browser"))],
            [api, browser], max_repairs=1, poll_interval=0,
            revision=lambda _: "v1", state=lambda _: next(states))
        report = controller.run("Build the API and UI")
        self.assertEqual(report["state"], "blocked")
        self.assertFalse(report["rounds"][1]["checks"]["browser"]["reused"])
        self.assertEqual(report["rounds"][1]["checks"]["browser"]["status"], "failed")


class SourceRevisionTest(unittest.TestCase):
    def test_current_git_and_untracked_bytes_are_bound(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "source.txt").write_text("one")
            subprocess.run(["git", "add", "source.txt"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=f@example.invalid",
                            "commit", "-qm", "seed"], cwd=root, check=True)
            before = source_revision(root)
            (root / "source.txt").write_text("two")
            changed = source_revision(root)
            self.assertNotEqual(before, changed)
            (root / "extra.txt").write_text("new")
            self.assertNotEqual(changed, source_revision(root))
            (root / "extra.txt").write_text("newer")
            self.assertNotEqual(changed, source_revision(root))
            original = source_revision(root)
            (root / "source.txt").chmod(0o755)
            self.assertNotEqual(original, source_revision(root))


if __name__ == "__main__":
    unittest.main()
