"""Offline listener diagnostics; unknown telemetry must still stop immediately."""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import context_probe as probe


class ListenerDiagnosticsTests(unittest.TestCase):
    def test_command_status_without_output_or_retries(self):
        for code in (0, 1):
            with self.subTest(code=code), patch.object(probe.subprocess, "run", return_value=
                    subprocess.CompletedProcess([], code, "123\n", "private-stderr")) as run:
                observation = {}
                self.assertEqual(probe.command(["lsof"], observation=observation), "123" if code == 0 else None)
                run.assert_called_once_with(["lsof"], capture_output=True, text=True, timeout=3)
                self.assertEqual(observation["status"], "ok" if code == 0 else "nonzero_exit")
                self.assertEqual(observation["returncode"], code)
                self.assertEqual((observation["stdout_bytes"], observation["stderr_bytes"]), (4, 14))
                self.assertGreaterEqual(observation["elapsed_seconds"], 0)
                self.assertNotIn("private-stderr", json.dumps(observation))

    def test_timeout_and_os_error_still_return_none_once(self):
        for error, status in ((subprocess.TimeoutExpired(["private-command"], 3, output=b"secret"), "timeout"),
                              (OSError(13, "private-path"), "os_error")):
            with self.subTest(status=status), patch.object(probe.subprocess, "run", side_effect=error) as run:
                observation = {}
                self.assertIsNone(probe.command(["lsof"], observation=observation))
                run.assert_called_once_with(["lsof"], capture_output=True, text=True, timeout=3)
                self.assertEqual(observation["status"], status)
                self.assertIsNone(observation["returncode"])
                self.assertNotIn("secret", json.dumps(observation))
                self.assertNotIn("private", json.dumps(observation))

    def sample(self, listener):
        def run(argv, **kwargs):
            if argv[0] == "/usr/sbin/lsof":
                if isinstance(listener, Exception):
                    raise listener
                code, stdout = listener
            else:
                code = 0
                stdout = {"vm.swapusage": "used = 0M", "kern.memorystatus_vm_pressure_level": "1",
                          "batt": "Now drawing from 'AC Power'", "123": "123 100 omlx"}[argv[-1]]
            return subprocess.CompletedProcess(argv, code, stdout, "")
        memory = SimpleNamespace(get_phys_footprint=lambda pid: 1234, get_lifetime_max_phys_footprint=lambda pid: 5678)
        with patch.object(probe.sys, "platform", "darwin"), patch.object(probe.subprocess, "run", side_effect=run), \
             patch.object(probe, "proc_memory_module", return_value=(memory, None)):
            return probe.resources("http://127.0.0.1:8000")

    def test_good_query_retains_telemetry(self):
        sample = self.sample((0, "123\n123\n"))
        self.assertTrue(probe.telemetry_ready(sample))
        self.assertEqual(set(sample["resource_queries"]), {"swap", "pressure", "power", "listener"})
        self.assertTrue(all(q["status"] == "ok" for q in sample["resource_queries"].values()))
        self.assertEqual(sample["resource_queries"]["listener"]["pid_count"], 1)
        self.assertEqual(sample["resource_queries"]["listener"]["invalid_token_count"], 0)
        self.assertIsNone(probe.ResourceGuard(0, 1).check(sample))

    def test_missing_listener_stops_and_latches_even_when_next_sample_is_good(self):
        for listener, status in (((0, ""), "ok"), ((0, "not-a-pid"), "ok"), ((1, ""), "nonzero_exit"),
                                 (subprocess.TimeoutExpired([], 3), "timeout"), (OSError(13, "denied"), "os_error")):
            with self.subTest(status=status, listener=str(listener)):
                sample = self.sample(listener)
                self.assertEqual(sample["resource_queries"]["listener"]["status"], status)
                self.assertFalse(probe.telemetry_ready(sample))
                guard = probe.ResourceGuard(0, 1)
                reason = "resource telemetry missing or listener identity ambiguous"
                self.assertEqual(guard.check(sample), reason)
                self.assertEqual(guard.check(self.sample((0, "123"))), reason)


if __name__ == "__main__":
    unittest.main()
