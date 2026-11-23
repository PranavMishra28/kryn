import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from research.container_controller import argv_for, stage, eligible, once, wait_ready, problem, prepare_grade
from research.campaign_supervisor import digest


class ControllerTests(unittest.TestCase):
    def test_battery_admission_is_explicit_and_does_not_relax_memory(self):
        with tempfile.TemporaryDirectory() as root, patch('research.container_controller.power',
                return_value={'ac': False, 'battery_percent': 88, 'adapter_watts': None}), patch(
                'research.container_controller.memory_pressure', return_value=1) as pressure, patch(
                'shutil.disk_usage', return_value=Mock(free=20 * 1024**3)):
            self.assertEqual(problem(Path(root)), 'battery_power')
            self.assertIsNone(problem(Path(root), 'battery-capable'))
            pressure.return_value = 2
            self.assertEqual(problem(Path(root), 'battery-capable'), 'host_memory_not_green')

    def test_final_parent_guard_failure_cannot_seal_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'state').mkdir()
            (root / 'manifest.json').write_text('{}')
            guard = Mock()
            guard.__enter__ = Mock(return_value=guard)
            def close(*_):
                guard.check.side_effect = RuntimeError('battery_floor')
            guard.__exit__ = Mock(side_effect=close)
            child = Mock(returncode=0, pid=123)
            child.poll.return_value = 0
            with patch('research.container_controller.wait_ready', return_value=True), patch(
                    'research.container_controller.frozen'), patch('research.container_controller.problem',
                    return_value=None), patch('research.container_controller.runtime_ready', return_value=True), patch(
                    'research.container_controller.HostGuard', return_value=guard) as host, patch(
                    'research.container_controller.subprocess.Popen', return_value=child):
                result = stage(root, {'power_policy': 'battery-capable', 'wall_seconds': 90},
                               'native', 'generation', [False])
                self.assertEqual(result['reason'], 'battery_floor')
                self.assertEqual(host.call_args.kwargs, {'power_policy': 'battery-capable'})
                self.assertTrue((root / 'state/cooldown.json').is_file())

    def test_grader_template_cannot_relabel_power_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'grader-template.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'power policy differ'):
                prepare_grade(root, {'power_policy': 'battery-capable',
                    'grader_template_sha256': digest(root / 'grader-template.json')}, 'native')
            self.assertFalse((root / 'grading').exists())

    def fixture(self, root):
        root = Path(root)
        (root / 'state').mkdir()
        (root / 'manifest.json').write_text('{}')
        marker = root / 'state/native.generation-start.json'
        argv = argv_for(root, 'native', 'generation')
        value = {'arm': 'native', 'phase': 'generation', 'argv': argv,
                 'manifest_sha256': digest(root / 'manifest.json'), 'started_unix': 1}
        once(marker, value)
        return root, marker, value

    def test_interrupted_stage_is_settled_and_never_relaunched(self):
        with tempfile.TemporaryDirectory() as root:
            root, marker, value = self.fixture(root)
            original = marker.read_bytes()
            with patch('research.container_controller.stop_stage') as stop, patch(
                    'research.container_controller.subprocess.Popen') as launch:
                result = stage(root, {}, 'native', 'generation', [False])
                self.assertEqual(result['reason'], 'controller_interrupted')
                self.assertIsNone(result['returncode'])
                stop.assert_called_once_with(value['argv'])
                again = stage(root, {}, 'native', 'generation', [False])
                self.assertEqual(result, again)
                launch.assert_not_called()
            self.assertEqual(marker.read_bytes(), original)

    def test_launch_identity_or_frozen_state_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            root, marker, value = self.fixture(root)
            value['argv'] = ['unrelated']
            marker.write_text(json.dumps(value))
            with patch('research.container_controller.stop_stage') as stop:
                with self.assertRaisesRegex(RuntimeError, 'command or manifest drift'):
                    stage(root, {}, 'native', 'generation', [False])
                stop.assert_not_called()

    def test_terminal_receipt_without_launch_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as root:
            root, marker, value = self.fixture(root)
            marker.unlink()
            once(root / 'state/native.generation-exit.json', {'reason': None, 'returncode': 0})
            with self.assertRaisesRegex(RuntimeError, 'no launch'):
                stage(root, {}, 'native', 'generation', [False])

    def test_unsafe_runtime_wait_does_not_spend_an_arm(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / 'state').mkdir()
            with patch('research.container_controller.wait_ready', return_value=False), patch(
                    'research.container_controller.subprocess.Popen') as launch:
                with self.assertRaisesRegex(RuntimeError, 'supervisor_exit'):
                    stage(root, {}, 'native', 'generation', [True])
                self.assertFalse((root / 'state/native.generation-start.json').exists())
                self.assertFalse((root / 'native').exists())
                launch.assert_not_called()

    def test_temporary_runtime_outage_waits_but_identity_drift_fails(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / 'state').mkdir()
            with patch('research.container_controller.frozen'), patch(
                    'research.container_controller.problem', return_value=None), patch(
                    'research.container_controller.time.sleep'), patch(
                    'research.container_controller.event') as event, patch(
                    'research.container_controller.runtime_ready', side_effect=[ConnectionRefusedError(), True]) as runtime:
                self.assertTrue(wait_ready(root, {}, [False]))
                self.assertEqual(runtime.call_count, 2)
                self.assertTrue(any('unavailable' in str(call) for call in event.call_args_list))
                runtime.side_effect = RuntimeError('ceiling drift')
                with self.assertRaisesRegex(RuntimeError, 'ceiling drift'):
                    wait_ready(root, {}, [False])

    def test_candidate_grading_cannot_admit_guard_or_wire_failure(self):
        value = dict(completed=False, intervention='timeout', cleanup_settled=True,
                     worker_exported=True, inference_relay_settled=True,
                     wire={'matches_frozen': True})
        self.assertTrue(eligible(value))
        for key, wrong in [('guard_reason', 'memory'), ('error', 'failed export'),
                           ('edited_test_paths', ['test.py']), ('cleanup_settled', False),
                           ('wire', {'matches_frozen': False})]:
            self.assertFalse(eligible({**value, key: wrong}))

    def test_write_once_preparation_cannot_change_a_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / 'receipt.json'
            once(p, {'pinned': 1})
            original = p.read_bytes()
            once(p, {'pinned': 1})
            with self.assertRaisesRegex(RuntimeError, 'Immutable'):
                once(p, {'pinned': 2})
            self.assertEqual(p.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
