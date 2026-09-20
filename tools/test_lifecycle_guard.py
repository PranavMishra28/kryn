"""Offline guard behavior; no process, HTTP, runtime, browser or inference calls."""
import contextlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("lifecycle_proposal", HERE / "native_lifecycle_probe.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def sample(pid=101, pressure=1, swap=100):
    return {"utc": "offline", "swap_used_bytes": swap, "pressure_level": pressure,
            "listener_processes": [] if pid is None else [{"pid": pid, "rss_bytes": 1000,
                "phys_footprint_bytes": 2000, "lifetime_max_phys_footprint_bytes": 3000}]}


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=HERE)
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    @contextlib.contextmanager
    def guard(self, values, *, pid=101, baseline=100, host=False):
        rows = iter(values)
        latest = values[-1]
        def observation(*_):
            return next(rows, latest).copy()
        guard = m.LifecycleResourceGuard(self.folder, [], baseline, pid, host, lambda why: None)
        with patch.object(m, "resources", observation), patch("run_native_trial.resources", observation):
            try:
                yield guard
            finally:
                if not guard.log.closed:
                    guard.disarm()
                    guard.close()

    def test_full_green_and_expected_pid(self):
        with self.guard([sample()]) as guard:
            guard.sample()
            self.assertTrue(guard.finish()["clean"])

    def test_expected_outage_does_not_fabricate_process_telemetry(self):
        with self.guard([sample(pid=None)], pid=None, host=True) as guard:
            guard.sample()
            result = guard.finish()
            self.assertTrue(result["clean"])
            self.assertTrue(result["required_telemetry_complete"])
            self.assertFalse(result["telemetry_complete"])
            self.assertEqual(guard.samples[0]["listener_processes"], [])

    def test_positive_missing_listener_fails(self):
        with self.guard([sample(pid=None)]) as guard:
            guard.sample()
            self.assertTrue(guard.cancel.is_set())
            self.assertFalse(guard.finish()["clean"])

    def test_unexpected_listener_in_stable_outage_fails(self):
        with self.guard([sample()], host=True) as guard:
            guard.expect_absent = True
            guard.sample()
            self.assertIn("returned", guard.guard.reason)
            self.assertTrue(guard.cancel.is_set())

    def test_positive_pid_change_fails(self):
        with self.guard([sample(pid=202)]) as guard:
            guard.sample()
            self.assertIn("changed", guard.guard.reason)

    def test_verified_recovery_new_pid_passes(self):
        with self.guard([sample(pid=202)], pid=202) as guard:
            guard.sample()
            self.assertTrue(guard.finish()["clean"])

    def test_recovery_retains_original_swap_baseline(self):
        with self.guard([sample(pid=202, swap=100 + 512 * 1024**2 + 1)], pid=202) as guard:
            guard.sample()
            self.assertIn("swap", guard.guard.reason)
            self.assertFalse(guard.finish()["clean"])

    def test_missing_host_metadata_in_outage_fails(self):
        with self.guard([{"listener_processes": []}], host=True) as guard:
            guard.sample()
            self.assertTrue(guard.cancel.is_set())

    def test_outage_warns_and_signals_only_own_pid_once(self):
        with self.guard([sample(None, 2)] * 4, host=True) as guard, patch.object(m.os, "kill") as kill:
            guard.arm()
            guard.sample()
            self.assertFalse(guard.cancel.is_set())
            guard.sample()
            guard.sample()
            guard.finish()
            kill.assert_called_once_with(m.os.getpid(), m.signal.SIGTERM)

    def test_single_warning_fails_grading_without_cancel(self):
        with self.guard([sample(None, 2), sample(None, 1)], host=True) as guard:
            guard.sample()
            result = guard.finish()
            self.assertFalse(result["clean"])
            self.assertFalse(guard.cancel.is_set())

    def test_cleanup_guard_never_sends_signal(self):
        with self.guard([sample(None, 4)], host=True) as guard, patch.object(m.os, "kill") as kill:
            guard.sample()
            self.assertFalse(guard.finish()["clean"])
            kill.assert_not_called()

    def test_disarm_waits_for_pending_send_then_cleanup_is_signal_free(self):
        entered, release, disarming, disarmed = (threading.Event() for _ in range(4))
        order = []
        with self.guard([sample()]) as guard, patch.object(m.os, "kill", side_effect=lambda *_: order.append("signal")) as kill:
            def paused_abort(_):
                entered.set()
                if not release.wait(2): raise AssertionError("offline interleaving timed out")
            guard.on_abort = paused_abort
            guard.arm()
            guard.cancel.set()
            sender = threading.Thread(target=guard.signal_if_cancelled)
            def cleanup():
                disarming.set()
                guard.disarm()
                order.append("cleanup")
                disarmed.set()
            closer = threading.Thread(target=cleanup)
            sender.start()
            try:
                self.assertTrue(entered.wait(1))
                closer.start()
                self.assertTrue(disarming.wait(1))
                self.assertFalse(disarmed.wait(.05), "cleanup passed a pending signal")
            finally:
                release.set()
                sender.join(2)
                if closer.ident is not None: closer.join(2)
            self.assertFalse(sender.is_alive())
            self.assertFalse(closer.is_alive())
            self.assertEqual(order, ["signal", "cleanup"])
            guard.signal_if_cancelled()
            kill.assert_called_once_with(m.os.getpid(), m.signal.SIGTERM)

    def test_disarm_before_cancel_prevents_send(self):
        with self.guard([sample()]) as guard, patch.object(m.os, "kill") as kill:
            guard.arm()
            guard.disarm()
            guard.cancel.set()
            guard.signal_if_cancelled()
            kill.assert_not_called()

    def test_synchronous_generate_interrupt_reaches_owned_cleanup(self):
        report = {}
        probe = m.Probe(SimpleNamespace(run=self.folder), self.folder, report)
        server = SimpleNamespace()
        server.process = SimpleNamespace(poll=lambda: None if not getattr(server, "closed", False) else 0)
        server.close = lambda: setattr(server, "closed", True)
        class Context:
            process = server.process
            def __enter__(self): return self
            def __exit__(self, *_): server.close()
            def close(self): server.close()
            def request(self, *_): guard.sample()
        with self.guard([sample(pressure=4)]) as guard, patch.object(m.os, "kill", side_effect=KeyboardInterrupt), patch.object(probe, "cancel_owned", return_value=True) as cancel:
            probe.before_cleanup = guard.disarm
            guard.arm()
            with self.assertRaises(KeyboardInterrupt):
                with probe.managed(Context(), "main") as native:
                    probe.api(native, "POST", "/api/session/owned/generate", {}, timeout=900)
            cancel.assert_called_once()
            self.assertFalse(guard.armed)
            self.assertTrue(report["native_process_exited"]["main"])


class MainGates(unittest.TestCase):
    """Mock the existing native/lifecycle boundaries; test new sequencing only."""
    def scenario(self, *, fault=None, native_stuck=False, interrupt_finish=None):
        with tempfile.TemporaryDirectory(dir=HERE) as raw, contextlib.ExitStack() as stack:
            folder = Path(raw)
            run = folder / "fixture"
            (run / "workspace/.git").mkdir(parents=True)
            (run / "run.json").write_text(json.dumps({"task": "11", "initial_hashes": {}}))
            tools = folder / "tools"
            (tools / "inference-audit").mkdir(parents=True)
            for name in ("native_client.py", "localai.py", "run_native_trial.py", "context_probe.py", "inference-audit/server.js", "inference-audit/package.json"):
                (tools / name).write_text("offline fixture")
            calls, guards = [], []
            class FakeGuard:
                def __init__(self, target, samples, baseline, pid, host, on_abort):
                    self.label = target.name.removeprefix("resources-")
                    self.guard = SimpleNamespace(baseline_swap=100 if baseline is None else baseline, reason=None)
                    self.cancel = threading.Event()
                    self.failed = fault == self.label
                    self.closed, self.finishes = False, 0
                    guards.append((self.label, baseline, pid, host))
                def start(self):
                    if self.failed and self.label in {"positive", "restore"}:
                        self.guard.reason = "offline preflight failure"
                        self.cancel.set()
                        raise RuntimeError(self.guard.reason)
                def arm(self): pass
                def disarm(self): pass
                def is_closed(self): return self.closed
                def finish(self):
                    self.finishes += 1
                    calls.append("finish-" + self.label)
                    if self.label == interrupt_finish and self.finishes == 1:
                        raise KeyboardInterrupt("offline interrupted sampler close")
                    if self.failed:
                        self.guard.reason = "offline resource failure"
                        self.cancel.set()
                    self.closed = True
                    return {"clean": not self.failed}
            class FakeServer:
                def __init__(self, *_):
                    self.closed = False
                    self.process = SimpleNamespace(poll=lambda: None if native_stuck or not self.closed else 0)
            class FakeProbe:
                def __init__(self, args, evidence, report):
                    self.folder, self.report = evidence, report
                    self.audit_path = evidence / "inference.jsonl"
                @contextlib.contextmanager
                def managed(self, native, label):
                    rows = [{"event": "ready"}, {"event": "http.request", "kind": "primary", "ok": True,
                        "model": {"providerID": "local", "id": "qwen"}, "destination": "http://127.0.0.1:8000/v1/chat/completions"}]
                    self.audit_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
                    try: yield native
                    finally:
                        calls.append("cleanup-" + label)
                        native.closed = True
                        self.report.setdefault("native_process_exited", {})[label] = not native_stuck
                        with self.audit_path.open("a") as stream: stream.write('{"event":"closed"}\n')
                def api(self, _, method, path, *args):
                    if path == "/api/plugin":
                        return {"data": [{"id": "localai.inference-audit", "state": {"status": "active"},
                            "source": {"type": "file", "path": str(self.folder / "audit-plugin/server.js")}}]}
                    return {"data": {}}
                def audit(self): return [{"event": "ready"}]
                def positive(self, _):
                    calls.append("positive")
                    for name in ("first-turn", "second-turn", "title", "compaction", "retention", "generate", "review-parent", "one-reviewer", "review-child"):
                        self.record(name)
                    return "owned", "child"
                def idle(self, _): pass
                def outage(self, *_):
                    calls.append("outage")
                    for name in ("outage-primary", "outage-existing-child", "outage-compaction", "outage-generate"):
                        self.record(name)
                    if fault == "outage": raise KeyboardInterrupt
                def create(self, *_ , **kwargs): return "recovery"
                def turn(self, *_):
                    calls.append("recovery-prompt")
                    self.record("recovery")
                    return {}, True
                def record(self, name, *_):
                    self.report["cases"][name] = {"status": "PASS"}
                    return True
            def cli(command, **kwargs):
                calls.append("cli-" + command[1])
                return SimpleNamespace(returncode=0)
            identity = lambda expected=None: {"pid": expected or 202}
            replacements = {"TOOLS": tools, "owned_config": lambda: {"plugins": []},
                "validate_owned_config": lambda _: None, "fixture_hashes": lambda _: {},
                "runtime_identity": identity, "NativeServer": FakeServer, "Probe": FakeProbe,
                "LifecycleResourceGuard": FakeGuard, "port_open": lambda: False,
                "wait_runtime_idle": lambda: {}, "inventory": lambda *_: {"providers": {"data": []}, "models": {"data": []}}}
            for name, value in replacements.items(): stack.enter_context(patch.object(m, name, value))
            stack.enter_context(patch.object(m.subprocess, "run", cli))
            stack.enter_context(patch.object(m.time, "sleep", lambda _: None))
            stack.enter_context(patch.object(sys, "argv", ["probe", str(run), "--runtime-pid", "101", "--guard-resources"]))
            m.main()
            report = json.loads((run / "evidence/lifecycle1/metrics.json").read_text())
            return calls, guards, report

    def test_preflight_refusal_prevents_generation_and_stop(self):
        calls, _, report = self.scenario(fault="positive")
        self.assertNotIn("positive", calls)
        self.assertNotIn("cli-stop", calls)
        self.assertNotIn("recovery-prompt", calls)
        self.assertFalse(report["resource_guard"]["clean"])

    def test_outage_resource_failure_restores_but_never_infers(self):
        calls, _, report = self.scenario(fault="outage")
        self.assertIn("cli-stop", calls)
        self.assertIn("cli-start", calls)
        self.assertNotIn("recovery-prompt", calls)
        self.assertTrue(report["resource_aborted"])
        self.assertNotEqual(report["status"], "PASS")

    def test_recovery_uses_new_verified_pid_and_original_baseline(self):
        calls, guards, report = self.scenario()
        self.assertIn("recovery-prompt", calls)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(guards, [("positive", None, 101, False), ("outage", 100, None, True),
                                  ("restore", 100, None, True), ("recovery", 100, 202, False)])

    def test_restore_preflight_refuses_unsafe_start(self):
        calls, _, report = self.scenario(fault="restore")
        self.assertIn("cli-stop", calls)
        self.assertNotIn("cli-start", calls)
        self.assertNotIn("recovery-prompt", calls)
        self.assertNotEqual(report["status"], "PASS")

    def test_resource_failure_cannot_pass_even_with_all_task_cases_pass(self):
        calls, _, report = self.scenario(fault="recovery")
        self.assertIn("recovery-prompt", calls)
        self.assertTrue(all(case["status"] == "PASS" for case in report["cases"].values()))
        self.assertFalse(report["resource_guard"]["clean"])
        self.assertNotEqual(report["status"], "PASS")

    def test_live_native_prevents_restart(self):
        calls, _, report = self.scenario(native_stuck=True)
        self.assertIn("cli-stop", calls)
        self.assertNotIn("cli-start", calls)
        self.assertNotIn("recovery-prompt", calls)
        self.assertFalse(report["restore_gate_native_exited"])

    def test_interrupted_close_retains_original_handle_for_cleanup(self):
        calls, guards, report = self.scenario(interrupt_finish="outage")
        self.assertEqual(calls.count("finish-outage"), 2)
        self.assertNotIn("cli-start", calls)
        self.assertNotIn("recovery-prompt", calls)
        self.assertEqual([label for label, *_ in guards], ["positive", "outage"])
        self.assertTrue(report.get("cleanup_failures"))
        self.assertNotEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
