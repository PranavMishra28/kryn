"""Power loss and crash recovery must never replay or promote invalid work."""

from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from research import campaign_supervisor as supervisor


class SupervisorTests(unittest.TestCase):
    def fixture(self, root):
        campaign, state, work = (root / name for name in ("campaign", "state", "work"))
        for directory in (campaign, state, work, campaign / "attempts"):
            directory.mkdir()
        supervisor.save(campaign / "manifest.json", {"tasks": [
            {"instance_id": "task-one", "arm_order": ["kryn", "native"]}]})
        return {"campaign": str(campaign), "state": str(state), "work": str(work),
                "source": str(root), "python": sys.executable, "manifest_sha256": "frozen",
                "auditor": str(root / "audit.py"), "auditor_sha256": "auditor"}

    def test_power_hysteresis_and_missing_adapter(self):
        good = {"ac": True, "adapter_watts": 140, "battery_percent": 90}
        self.assertIsNone(supervisor.power_problem(good, True))
        for change in ({"ac": False}, {"adapter_watts": None}, {"adapter_watts": 65}, {"battery_percent": 39}):
            self.assertIsNotNone(supervisor.power_problem({**good, **change}, True))
        self.assertIsNone(supervisor.power_problem({**good, "battery_percent": 30}, False))
        self.assertIsNotNone(supervisor.power_problem({**good, "battery_percent": 25}, False))

    def test_runtime_absence_recovers_but_check_is_read_only_and_drift_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self.fixture(root)
            research, tools = root / "research", root / "tools"
            research.mkdir()
            tools.mkdir()
            (research / "__init__.py").write_text("")
            source_lock = research / "swebench_controller.py"
            source_lock.write_text("def source_lock(*args): pass\n")
            Path(config["auditor"]).write_text("# pinned auditor\n")
            config.update(source_commit="frozen", auditor_sha256=supervisor.digest(config["auditor"]),
                          manifest_sha256=supervisor.digest(Path(config["campaign"]) / "manifest.json"))
            (Path(config["campaign"]) / "manifest.sha256").write_text(config["manifest_sha256"])
            localai = tools / "localai.py"
            valid = ("from pathlib import Path\nimport subprocess\n"
                     "flag=Path(__file__).with_name('started')\n"
                     "def ensure_runtime(): flag.touch()\n"
                     "def runtime_identity():\n"
                     " if not flag.exists(): raise subprocess.CalledProcessError(1, "
                     "['/usr/sbin/lsof','-nP','-a','-iTCP:8000','-sTCP:LISTEN','-Fpu'])\n"
                     "def runtime_metadata(): return {'healthy':True,'model':'Qwen3.5-9B-6bit',"
                     "'model_memory_max':22*1024**3,'active_requests':0,'waiting_requests':0}\n")
            localai.write_text(valid)
            with patch.object(supervisor, "command", side_effect=lambda argv, **_: "frozen" if "rev-parse" in argv else ""):
                self.assertFalse(supervisor.preflight(config))
                self.assertFalse((tools / "started").exists())
                self.assertTrue(supervisor.preflight(config, start_runtime=True))
                self.assertTrue(supervisor.preflight(config))
                for broken in (valid.replace("22*1024**3", "24*1024**3"),
                               valid.replace("Qwen3.5-9B-6bit", "other-model"),
                               valid + "\ndef runtime_identity(): raise RuntimeError('wrong owner')\n"):
                    localai.write_text(broken)
                    with self.assertRaisesRegex(RuntimeError, "preflight failed"):
                        supervisor.preflight(config, start_runtime=True)
                localai.write_text(valid)
                source_lock.write_text("def source_lock(*args): raise RuntimeError('source drift')\n")
                with self.assertRaisesRegex(RuntimeError, "source drift"):
                    supervisor.preflight(config, start_runtime=True)

    def test_safety_requires_normal_memory_before_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            with patch.object(supervisor, "power", return_value={"ac": True, "adapter_watts": 140, "battery_percent": 90}), patch.object(
                    supervisor, "memory_pressure", return_value=2), patch.object(
                    supervisor.shutil, "disk_usage", return_value=Mock(free=30 * 1024**3)):
                self.assertEqual(supervisor.safety(config, True)[0], "host_memory_not_green")

    def test_memory_warning_pauses_controller_and_records_cooldown(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            child, awake = Mock(pid=987), Mock()
            child.poll.side_effect = [None, 0]
            child.wait.return_value = 0
            awake.poll.return_value = None
            with patch.object(supervisor, "memory_pressure", return_value=2), patch.object(
                    supervisor, "safety", return_value=(None, {})), patch.object(
                    supervisor, "stop_pid") as stop, patch.object(supervisor.subprocess, "Popen", return_value=awake):
                self.assertEqual(supervisor.monitor(child, config, [False]), "host_memory_guard")
                stop.assert_called_once()
            cooldown = supervisor.read(Path(config["state"]) / "memory-cooldown.json")
            self.assertGreater(cooldown["until_unix"], time.time())
            self.assertEqual(cooldown["memory"]["pressure_level"], 2)
            awake.terminate.assert_called_once()

    def test_slow_power_check_cannot_delay_memory_pause(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            child, awake = Mock(pid=987), Mock()
            child.poll.side_effect = [None, 0]
            awake.poll.return_value = None
            probing, stopped = threading.Event(), threading.Event()

            def slow_safety(*_a, **_k):
                probing.set()
                if not stopped.wait(3):
                    raise RuntimeError("power probe blocked memory pause")
                return None, {}

            def pressure():
                self.assertTrue(probing.wait(1))
                return 2

            with patch.object(supervisor, "memory_pressure", side_effect=pressure), patch.object(
                    supervisor, "safety", side_effect=slow_safety), patch.object(
                    supervisor, "stop_pid", side_effect=lambda *_: stopped.set()), patch.object(
                    supervisor.subprocess, "Popen", return_value=awake):
                self.assertEqual(supervisor.monitor(child, config, [False]), "host_memory_guard")
            self.assertTrue(stopped.is_set())

    def test_runtime_start_power_drift_and_persistent_pressure_prevent_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            good, bad = (None, {}), ("battery_power", {"ac": False})
            checks = [good, good, good, bad, ("host_memory_not_green", {}),
                      ("host_memory_not_green", {})]
            def safety(*_a, **_k):
                if checks:
                    return checks.pop(0)
                raise RuntimeError("test finished")
            with patch.object(supervisor, "safety", side_effect=safety), patch.object(
                    supervisor, "preflight", return_value=True) as preflight, patch.object(
                    supervisor, "settle"), patch.object(supervisor, "command", return_value=""), patch.object(
                    supervisor.time, "sleep"), patch.object(supervisor.signal, "signal"), patch.object(
                    supervisor.subprocess, "Popen") as launch:
                with self.assertRaisesRegex(RuntimeError, "test finished"):
                    supervisor.supervise(config)
                launch.assert_not_called()
                preflight.assert_called_once_with(config, start_runtime=True)
            events = (Path(config["state"]) / "events.jsonl").read_text()
            self.assertIn('"reason": "battery_power"', events)
            self.assertIn('"reason": "host_memory_not_green"', events)

    def test_completed_evidence_change_or_deletion_refuses_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            campaign, state = Path(config["campaign"]), Path(config["state"])
            final = campaign / "attempts/s01-native.final.json"
            final.write_text('{"accepted":false}')
            supervisor.checkpoint(campaign, state)
            final.write_text('{"accepted":true}')
            with self.assertRaisesRegex(RuntimeError, "evidence changed"):
                supervisor.checkpoint(campaign, state)
            final.unlink()
            with self.assertRaisesRegex(RuntimeError, "evidence changed"):
                supervisor.checkpoint(campaign, state)

    def test_interrupted_worker_keeps_markers_and_archives_candidate_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            campaign, state, work = (Path(config[key]) for key in ("campaign", "state", "work"))
            candidate = work / "task-one/candidate"
            candidate.mkdir(parents=True)
            (candidate / "change.py").write_text("unfinished = True\n")
            prepared = campaign / "prepared/task-one"
            prepared.mkdir(parents=True)
            supervisor.save(prepared / "receipt.json", {})
            marker = campaign / "attempts/s01-kryn.running.json"
            marker.write_text('{"pid":123}')
            supervisor.checkpoint(campaign, state)
            with patch.object(supervisor.shutil, "disk_usage", return_value=Mock(free=30 * 1024**3)):
                supervisor.recover(config)
                first = supervisor.read(state / "interruptions/s01-kryn.json")
                supervisor.recover(config)
            self.assertEqual(first, supervisor.read(state / "interruptions/s01-kryn.json"))
            self.assertEqual(marker.read_text(), '{"pid":123}')
            self.assertFalse((campaign / "attempts/s01-kryn.final.json").exists())
            self.assertTrue((candidate / "change.py").exists())
            supervisor.checkpoint(campaign, state)

    def test_interrupted_gold_retires_pair_without_overwriting_raw_or_replaying(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            campaign, state = Path(config["campaign"]), Path(config["state"])
            gold = campaign / "grader/gold-s01"
            gold.mkdir(parents=True)
            (gold / "stdout.log").write_text("incomplete grader\n")
            supervisor.checkpoint(campaign, state)
            supervisor.recover(config)
            before = supervisor.inventory(campaign)
            supervisor.recover(config)
            self.assertEqual(before, supervisor.inventory(campaign))
            self.assertFalse(supervisor.read(gold / "final.json")["clean_grade"])
            for arm in ("kryn", "native"):
                row = supervisor.read(campaign / f"attempts/s01-{arm}.final.json")
                self.assertFalse(row["accepted"])
                self.assertEqual(row["status"], "oracle_interrupted")
            self.assertEqual((gold / "stdout.log").read_text(), "incomplete grader\n")
            supervisor.checkpoint(campaign, state)

    def test_partial_preparation_relocated_with_exact_file_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            campaign, state, work = (Path(config[key]) for key in ("campaign", "state", "work"))
            supervisor.checkpoint(campaign, state)
            partial = campaign / "prepared/task-one"
            partial.mkdir(parents=True)
            (partial / "prompt.txt").write_text("frozen prompt")
            (work / "task-one").mkdir()
            supervisor.checkpoint(campaign, state, seal=False)
            supervisor.recover(config)
            supervisor.checkpoint(campaign, state)
            archives = list((state / "relocations").glob("*/receipt.json"))
            self.assertEqual(len(archives), 1)
            self.assertEqual((archives[0].parent / "0/prompt.txt").read_text(), "frozen prompt")
            self.assertFalse(partial.exists())
            supervisor.recover(config)
            (archives[0].parent / "0/prompt.txt").write_text("changed")
            with self.assertRaisesRegex(RuntimeError, "relocation changed"):
                supervisor.recover(config)

    def test_crash_between_gold_and_arm_receipts_is_reconciled(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            campaign = Path(config["campaign"])
            gold = campaign / "grader/gold-s01"
            gold.mkdir(parents=True)
            original = supervisor.save

            def interrupted(path, value):
                if Path(path).name == "s01-native.final.json":
                    raise OSError("simulated crash")
                original(path, value)

            with patch.object(supervisor, "save", side_effect=interrupted):
                with self.assertRaisesRegex(OSError, "simulated crash"):
                    supervisor.recover(config)
            prior = (gold / "final.json").read_bytes()
            supervisor.recover(config)
            self.assertEqual(prior, (gold / "final.json").read_bytes())
            self.assertFalse(supervisor.read(campaign / "attempts/s01-native.final.json")["accepted"])

    def test_archive_finished_before_receipt_is_reused_after_crash(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            campaign, state, work = (Path(config[key]) for key in ("campaign", "state", "work"))
            candidate = work / "candidate"
            candidate.mkdir()
            (candidate / "progress.json").write_text("candidate data must not be excluded")
            original = supervisor.save

            def crash(path, value):
                if value.get("complete"):
                    raise OSError("after tar close")
                original(path, value)

            with patch.object(supervisor, "save", side_effect=crash), patch.object(
                    supervisor.shutil, "disk_usage", return_value=Mock(free=30 * 1024**3)):
                with self.assertRaisesRegex(OSError, "tar close"):
                    supervisor.archive_candidate(candidate, state, "s01-kryn", campaign)
            archive = state / "interruptions/s01-kryn.tar.gz"
            before = archive.read_bytes()
            with patch.object(supervisor.tarfile, "open", wraps=supervisor.tarfile.open) as opened:
                supervisor.archive_candidate(candidate, state, "s01-kryn", campaign)
                self.assertFalse(any(len(call.args) > 1 and call.args[1] == "w:gz" for call in opened.call_args_list))
            self.assertEqual(before, archive.read_bytes())
            self.assertTrue(supervisor.read(state / "interruptions/s01-kryn.json")["complete"])

    def test_guard_aborted_gold_stays_failed_and_later_pair_can_continue(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            campaign = Path(config["campaign"])
            gold = campaign / "grader/gold-s01"
            gold.mkdir(parents=True)
            supervisor.save(gold / "final.json", {"clean_grade": False, "reason": "resource_preflight", "guard_reason": "warning"})
            before = (gold / "final.json").read_bytes()
            supervisor.recover(config)
            self.assertEqual(before, (gold / "final.json").read_bytes())
            for arm in ("kryn", "native"):
                row = supervisor.read(campaign / f"attempts/s01-{arm}.final.json")
                self.assertFalse(row["accepted"])
                self.assertEqual(row["official"]["reason"], "resource_preflight")

    def test_partial_atomic_writes_and_relocation_crash_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            campaign, state = Path(config["campaign"]), Path(config["state"])
            supervisor.checkpoint(campaign, state)
            partial = campaign / "progress.json.tmp"
            partial.write_text('"partial')
            original = supervisor.os.rename

            def interrupted(source, target):
                original(source, target)
                raise OSError("simulated relocation crash")

            with patch.object(supervisor.os, "rename", side_effect=interrupted):
                with self.assertRaisesRegex(OSError, "relocation crash"):
                    supervisor.recover(config)
            supervisor.recover(config)
            supervisor.checkpoint(campaign, state)
            archive = next((state / "relocations").glob("*/0"))
            self.assertEqual(archive.read_text(), '"partial')
            self.assertFalse(partial.exists())

    def test_unmarked_orphan_and_its_detached_child_are_settled(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self.fixture(root)
            script = root / "research/run_external_patch.py"
            script.parent.mkdir()
            child_pid = root / "child.pid"
            script.write_text("import subprocess,sys,time\nfrom pathlib import Path\n"
                              "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'], start_new_session=True)\n"
                              f"Path({str(child_pid)!r}).write_text(str(p.pid))\n"
                              "time.sleep(60)\n")
            child = subprocess.Popen([sys.executable, str(script), "--evidence", config["campaign"] + "/evidence/s01-kryn"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            original = supervisor.command
            try:
                until = time.monotonic() + 5
                while not child_pid.exists() and time.monotonic() < until:
                    time.sleep(.01)
                self.assertTrue(child_pid.exists())
                descendant = int(child_pid.read_text())
                with patch.object(supervisor, "command", side_effect=lambda argv, **kwargs:
                                  "" if argv[0] == "docker" else original(argv, **kwargs)):
                    supervisor.settle(config)
                child.wait(timeout=5)
                self.assertNotIn("time.sleep(60)", supervisor.live_commands().get(descendant, ""))
            finally:
                if child.poll() is None:
                    child.kill()
                child.wait()

    def test_real_controller_is_stopped_on_battery_and_awake_assertion_released(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self.fixture(root)
            script = root / "research/swebench_controller.py"
            script.parent.mkdir()
            script.write_text("import time\ntime.sleep(60)\n")
            child = subprocess.Popen([sys.executable, str(script), config["campaign"]],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            awake = Mock()
            awake.poll.return_value = None
            original_popen = subprocess.Popen
            try:
                with patch.object(supervisor, "safety", return_value=("battery_power", {"ac": False})), patch.object(
                        supervisor.subprocess, "Popen", side_effect=lambda argv, **kwargs:
                        awake if argv[0] == "/usr/bin/caffeinate" else original_popen(argv, **kwargs)):
                    reason = supervisor.monitor(child, config, [False])
                self.assertEqual(reason, "battery_power")
                self.assertIsNotNone(child.poll())
                awake.terminate.assert_called_once()
            finally:
                if child.poll() is None:
                    child.kill()
                child.wait()

    def test_reused_pid_is_never_signalled(self):
        born = Mock(stdout="Sun Oct  4 12:00:00 2026\n")
        with patch.object(supervisor, "live_commands", return_value={42: "swebench --run_id s01"}), patch.object(
                supervisor.subprocess, "run", return_value=born), patch.object(supervisor.os, "kill") as kill:
            supervisor.stop_pid(42, ["swebench", "--run_id s01"], started_unix=1)
        kill.assert_not_called()

    def test_awake_helper_failure_stops_the_started_controller(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self.fixture(root)
            script = root / "research/swebench_controller.py"
            script.parent.mkdir()
            script.write_text("import time\ntime.sleep(60)\n")
            child = subprocess.Popen([sys.executable, str(script), config["campaign"]],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            original = subprocess.Popen

            def start(argv, **kwargs):
                if argv[0] == "/usr/bin/caffeinate":
                    raise OSError("awake helper unavailable")
                return original(argv, **kwargs)

            try:
                with patch.object(supervisor.subprocess, "Popen", side_effect=start):
                    with self.assertRaisesRegex(OSError, "awake helper unavailable"):
                        supervisor.monitor(child, config, [False])
                self.assertIsNotNone(child.poll())
            finally:
                if child.poll() is None:
                    child.kill()
                child.wait()

    def test_wait_then_resume_and_retry_exit_without_marking_release_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            state, campaign = Path(config["state"]), Path(config["campaign"])
            good = (None, {"ac": True, "adapter_watts": 140, "battery_percent": 90})
            states = iter([("battery_power", {"ac": False}), good, good, good, good, good, good])
            children = [Mock(pid=100, returncode=-9), Mock(pid=101, returncode=0)]

            def run(child, *_):
                if child.pid == 101:
                    supervisor.save(campaign / "final-report.json", {"finished": True})
                return None

            def audit(_):
                supervisor.event(state, "adjudicated", release_qualified=False)

            with patch.object(supervisor, "safety", side_effect=lambda *_a, **_k: next(states, good)), patch.object(
                    supervisor, "preflight", return_value=True), patch.object(supervisor, "settle", side_effect=
                    iter([supervisor.Waiting("docker_unavailable")] + [None] * 50)), patch.object(
                    supervisor, "monitor", side_effect=run), patch.object(supervisor, "command", return_value=""), patch.object(
                    supervisor, "adjudicate", side_effect=audit), patch.object(supervisor.time, "sleep"), patch.object(
                    supervisor.signal, "signal"), patch.object(supervisor.subprocess, "Popen", side_effect=children) as launch:
                supervisor.supervise(config)
                self.assertEqual(launch.call_count, 2)
                supervisor.supervise(config)
                self.assertEqual(launch.call_count, 2)
            self.assertFalse(supervisor.read(state / "status.json")["release_qualified"])
            self.assertIn('"reason": "battery_power"', (state / "events.jsonl").read_text())
            self.assertIn('"reason": "docker_unavailable"', (state / "events.jsonl").read_text())

    def test_two_unexplained_exits_stop_instead_of_restart_spin(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = self.fixture(Path(temporary))
            with patch.object(supervisor, "safety", return_value=(None, {})), patch.object(
                    supervisor, "preflight", return_value=True), patch.object(supervisor, "settle"), patch.object(
                    supervisor, "monitor", return_value=None), patch.object(supervisor, "command", return_value=""), patch.object(
                    supervisor.time, "sleep"), patch.object(supervisor.signal, "signal"), patch.object(
                    supervisor.subprocess, "Popen", return_value=Mock(pid=100, returncode=1)) as launch:
                with self.assertRaisesRegex(RuntimeError, "twice without progress"):
                    supervisor.supervise(config)
                self.assertEqual(launch.call_count, 2)
                supervisor.supervise(config)
                self.assertEqual(launch.call_count, 2)
            self.assertEqual(supervisor.read(Path(config["state"]) / "status.json")["kind"], "needs_action")


if __name__ == "__main__":
    unittest.main()
