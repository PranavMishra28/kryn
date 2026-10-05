import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.container_controller import argv_for, stage, eligible, once, wait_ready
from research.campaign_supervisor import digest


class ControllerTests(unittest.TestCase):
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
