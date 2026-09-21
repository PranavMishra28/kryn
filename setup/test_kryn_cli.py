"""Offline launcher checks. All processes, runtime calls and telemetry are mocked."""
from contextlib import nullcontext, redirect_stdout, redirect_stderr
import io
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import localai
import deploy_client
import setup


def sample(level=1, swap=100, pid=42):
    return {'pressure_level': level, 'swap_used_bytes': swap,
            'listener_processes': [{'pid': pid, 'rss_bytes': 1024}]}


class Child:
    def __init__(self, waits):
        self.waits, self.code, self.signals = iter(waits), None, []
    def wait(self, timeout):
        value = next(self.waits, 0)
        if isinstance(value, BaseException):
            raise value
        self.code = value
        return value
    def poll(self): return self.code
    def send_signal(self, sig): self.signals.append(sig)
    def terminate(self): self.signals.append('terminate')
    def kill(self): self.signals.append('kill')


class KrynChecks(unittest.TestCase):
    def setUp(self):
        # Separate owner-session tests cover authentication; these exercise lifecycle without production state.
        self.enterContext(patch.object(localai.owner_auth, 'authorize', return_value={'owner_id': 90290458, 'expires_at': 9999999999}))
        self.enterContext(patch.object(localai.learning, 'active_champion', return_value=localai.learning.BASELINE))
        self.enterContext(patch.object(localai.learning, 'start_after_exit'))
        self.enterContext(patch.object(localai, 'owned_config', return_value={}))

    def guarded(self, samples, child, outcome=None, **options):
        outcome = {} if outcome is None else outcome
        server = Mock(env={}, directory=Path('/owned/project'), url='http://127.0.0.1:12345')
        with patch.object(localai, 'resources', side_effect=samples) as readings, \
             patch.object(localai, 'runtime_identity', return_value=42), \
             patch.object(localai.time, 'sleep') as sleep, \
             patch.object(localai.subprocess, 'Popen', return_value=child) as popen, \
             patch.object(localai, 'interrupt_owned_sessions') as interrupt:
            result = localai.guarded_run(server, ['native'], server.directory, outcome, **options)
            return result, outcome, readings, sleep, popen, interrupt

    def test_three_green_and_normal_cleanup(self):
        child = Child([0])
        code, outcome, readings, sleep, popen, interrupt = self.guarded([sample()] * 4, child)
        self.assertEqual(code, 0)
        self.assertEqual(readings.call_count, 4)
        self.assertEqual([x.args for x in sleep.call_args_list], [(2,), (2,)])
        popen.assert_called_once()
        interrupt.assert_called_once()
        self.assertEqual(child.signals, [])
        self.assertEqual(outcome['swap_growth_bytes'], 0)

    def test_bad_preflight_never_starts_child(self):
        for bad in (sample(2), sample(4), {}, sample(pid=99)):
            with self.subTest(bad=bad), patch.object(localai, 'resources', return_value=bad), \
                 patch.object(localai, 'runtime_identity', return_value=42), \
                 patch.object(localai.subprocess, 'Popen') as popen, \
                 patch.object(localai, 'interrupt_owned_sessions'), self.assertRaises(RuntimeError):
                localai.guarded_run(Mock(), ['native'], Path('/owned'), {})
            popen.assert_not_called()

    def test_web_uses_clean_loopback_url_inside_the_existing_resource_guard(self):
        with patch.object(localai.subprocess, 'run', return_value=Mock(returncode=0)) as opened:
            code, _, _, _, popen, interrupt = self.guarded([sample()] * 4, Child([0]), web=True)
        self.assertEqual(code, 0)
        self.assertEqual(opened.call_args.args[0], ['/usr/bin/open', 'http://127.0.0.1:12345'])
        popen.assert_called_once()
        interrupt.assert_called_once()
        with patch.object(localai.subprocess, 'run') as opened, self.assertRaises(localai.ResourceStop):
            self.guarded([sample(2)], Child([0]), web=True)
        opened.assert_not_called()

    def test_browser_open_failure_preserves_the_guarded_terminal(self):
        with patch.object(localai.subprocess, 'run', side_effect=OSError('unavailable')), redirect_stderr(io.StringIO()) as error:
            code, _, _, _, _, interrupt = self.guarded([sample()] * 4, Child([0]), web=True)
        self.assertEqual(code, 0)
        self.assertIn('Use /web', error.getvalue())
        interrupt.assert_called_once()

    def test_each_guard_gate_cancels_owned_child(self):
        cases = ([sample(2), sample(2)], [sample(4)], [{}], [sample(None)], [sample(pid=99)],
                 [sample(swap=100+512*1024**2+1)])
        for after in cases:
            child = Child([subprocess.TimeoutExpired('native', 2)] * len(after) + [0])
            outcome = {}
            with self.subTest(after=after), self.assertRaisesRegex(RuntimeError, 'Resource guard'):
                self.guarded([sample()] * 3 + after, child, outcome)
            self.assertEqual(outcome['failure_code'], 'resource')
            self.assertEqual(outcome['interventions'], 1)
            self.assertEqual(child.signals, [localai.signal.SIGINT])
            self.assertEqual(child.poll(), 0)

    def test_single_warning_resets(self):
        child = Child([subprocess.TimeoutExpired('native', 2), 0])
        code, outcome, *_ = self.guarded([sample()] * 3 + [sample(2), sample()], child)
        self.assertEqual(code, 0)
        self.assertEqual(outcome['pressure_warning_samples'], 1)

    def test_exact_swap_budget_allowed_and_warning_count_resets(self):
        after = [sample(2), sample(), sample(2), sample(swap=100+512*1024**2)]
        child = Child([subprocess.TimeoutExpired('native', 2)] * 3 + [0])
        code, outcome, *_ = self.guarded([sample()] * 3 + after, child)
        self.assertEqual(code, 0)
        self.assertEqual(outcome['swap_growth_bytes'], 512*1024**2)
        self.assertEqual(outcome['pressure_warning_samples'], 2)

    def test_telemetry_exception_fails_closed(self):
        child = Child([subprocess.TimeoutExpired('native', 2), 0])
        with self.assertRaisesRegex(RuntimeError, 'telemetry'):
            self.guarded([sample()] * 3 + [OSError('unavailable')], child)
        self.assertEqual(child.poll(), 0)

    def test_timeout_counts_one_intervention(self):
        child = Child([subprocess.TimeoutExpired('native', 2), 0])
        outcome = {}
        with patch.object(localai, 'resources', return_value=sample()), \
             patch.object(localai, 'runtime_identity', return_value=42), \
             patch.object(localai.time, 'sleep'), patch.object(localai.time, 'monotonic', side_effect=[0, 2]), \
             patch.object(localai.subprocess, 'Popen', return_value=child), \
             patch.object(localai, 'interrupt_owned_sessions'), self.assertRaisesRegex(RuntimeError, 'time limit'):
            localai.guarded_run(Mock(), ['native'], Path('/owned'), outcome, timeout=1)
        self.assertEqual(outcome['interventions'], 1)
        self.assertEqual(outcome['failure_code'], 'timeout')
        self.assertEqual(child.poll(), 0)

    def test_interrupt_preserved_and_owned_child_stopped(self):
        child = Child([KeyboardInterrupt(), 0])
        with self.assertRaises(KeyboardInterrupt):
            self.guarded([sample()] * 3, child)
        self.assertEqual(child.poll(), 0)

    def test_cleanup_failure_preserves_original_error(self):
        child = Child([KeyboardInterrupt(), 0])
        with patch.object(localai, 'resources', return_value=sample()), \
             patch.object(localai, 'runtime_identity', return_value=42), \
             patch.object(localai.time, 'sleep'), patch.object(localai.subprocess, 'Popen', return_value=child), \
             patch.object(localai, 'interrupt_owned_sessions', side_effect=RuntimeError('unavailable')), \
             self.assertRaises(KeyboardInterrupt) as caught:
            localai.guarded_run(Mock(), ['native'], Path('/owned'), {})
        self.assertEqual(child.poll(), 0)
        self.assertIn('cleanup', caught.exception.__notes__[0])

    def test_native_closes_before_idle_check(self):
        order = []
        owner, server = Mock(), Mock(env={}, url='http://127.0.0.1:12345')
        owner = Mock(__enter__=Mock(return_value=server), __exit__=Mock(side_effect=lambda *a: order.append('closed')))
        args = Mock(command_or_project='launch', json_cli=False, deep=False, project=str(Path.cwd()), apply=False, profile=None, node=None, uv=None)
        with patch.object(localai, 'prerequisites', return_value={}), \
             patch.object(localai.improvement, 'active_skill_directory', return_value=None), \
             patch.object(localai, 'dependency_report', return_value={}), \
             patch.object(localai, 'ensure_runtime', return_value={'active_requests': 0, 'waiting_requests': 0}), \
             patch.object(localai, 'NativeServer', return_value=owner), patch.object(localai, 'inventory'), \
             patch.object(localai, 'mcp_status', return_value={}), \
             patch.object(localai, 'guarded_run', side_effect=lambda *a, **k: order.append('tui') or 0), \
             patch.object(localai, 'await_runtime_idle', side_effect=lambda: order.append('idle')):
            self.assertEqual(localai.run(args, {}), 0)
        self.assertEqual(order, ['tui', 'closed', 'idle'])

    def test_runtime_idle_requires_two_observations(self):
        with patch.object(localai, 'runtime_metadata', side_effect=[{'active_requests': 1, 'waiting_requests': 0},
                    {'active_requests': 0, 'waiting_requests': 0}, {'active_requests': 0, 'waiting_requests': 0}]) as status, \
             patch.object(localai.time, 'sleep'):
            localai.await_runtime_idle()
        self.assertEqual(status.call_count, 3)

    def test_resource_stop_releases_runtime_only_after_native_close_idle_and_identity(self):
        for idle_error, identity_error in ((False, False), (True, False), (False, True)):
            order = []
            server = Mock(env={}, url='http://127.0.0.1:12345')
            owner = Mock(__enter__=Mock(return_value=server), __exit__=Mock(side_effect=lambda *a: order.append('closed')))
            args = Mock(command_or_project='launch', json_cli=False, deep=False, project=str(Path.cwd()),
                        apply=False, profile=None, node=None, uv=None, continue_session=True, session=None)
            def idle():
                order.append('idle')
                if idle_error: raise RuntimeError('busy')
            def identity():
                order.append('identity')
                if identity_error: raise RuntimeError('foreign process')
            with patch.object(localai, 'prerequisites', return_value={}), \
                 patch.object(localai, 'dependency_report', return_value={}), \
                 patch.object(localai, 'ensure_runtime', return_value={'active_requests': 0, 'waiting_requests': 0}), \
                 patch.object(localai, 'NativeServer', return_value=owner), patch.object(localai, 'inventory'), \
                 patch.object(localai, 'mcp_status', return_value={}), \
                 patch.object(localai, 'guarded_run', side_effect=localai.ResourceStop('memory')) as launch, \
                 patch.object(localai, 'await_runtime_idle', side_effect=idle), \
                 patch.object(localai, 'runtime_identity', side_effect=identity), \
                 patch.object(localai, 'runtime_command', side_effect=lambda op: order.append(op)) as command, \
                 redirect_stderr(io.StringIO()), self.assertRaises(localai.ResourceStop):
                localai.run(args, {})
            self.assertIn('--continue', launch.call_args.args[1])
            self.assertEqual(order[:2], ['closed', 'idle'])
            if idle_error or identity_error:
                command.assert_not_called()
            else:
                self.assertEqual(order, ['closed', 'idle', 'identity', 'stop'])

    def test_guard_retains_bounded_numeric_diagnostics(self):
        reading = sample()
        reading['listener_processes'][0]['phys_footprint_bytes'] = 9000
        _, outcome, *_ = self.guarded([reading] * 4, Child([0]))
        self.assertEqual(outcome['last_pressure_level'], 1)
        self.assertEqual(outcome['max_runtime_footprint_bytes'], 9000)
        localai.improvement._outcome({**outcome, 'command': 'run', 'status': 'incomplete', 'wall_seconds': 1})
        for field, value in [('last_pressure_level', True), ('last_pressure_level', 'private text'),
                             ('max_runtime_footprint_bytes', -1), ('max_runtime_footprint_bytes', {})]:
            with self.assertRaises(ValueError):
                localai.improvement._outcome({**outcome, 'command': 'run', 'status': 'incomplete',
                                             'wall_seconds': 1, field: value})

    def test_explicit_resume_requires_matching_session_project_and_local_model(self):
        project = str(Path.cwd().resolve())
        valid = {'id': 'ses_owned', 'location': {'directory': project},
                 'model': {'providerID': 'local', 'id': 'qwen'}}
        for change in ({}, {'id': 'ses_other'}, {'location': {'directory': '/other'}},
                       {'location': {}}, {'model': {'providerID': 'remote', 'id': 'qwen'}}):
            server = Mock(env={}, url='http://127.0.0.1:12345')
            server.request.return_value = {'data': {**valid, **change}}
            owner = Mock(__enter__=Mock(return_value=server), __exit__=Mock(return_value=False))
            args = Mock(command_or_project='launch', json_cli=False, deep=False, project=project,
                        apply=False, profile=None, node=None, uv=None, continue_session=False, session='ses_owned')
            with patch.object(localai, 'prerequisites', return_value={}), \
                 patch.object(localai, 'dependency_report', return_value={}), \
                 patch.object(localai, 'ensure_runtime', return_value={'active_requests': 0, 'waiting_requests': 0}), \
                 patch.object(localai, 'NativeServer', return_value=owner), patch.object(localai, 'inventory'), \
                 patch.object(localai, 'mcp_status', return_value={}), \
                 patch.object(localai, 'guarded_run', return_value=0) as launch, \
                 patch.object(localai, 'await_runtime_idle'):
                if change:
                    with self.assertRaisesRegex(RuntimeError, 'Resume session'):
                        localai.run(args, {})
                    launch.assert_not_called()
                else:
                    self.assertEqual(localai.run(args, {}), 0)
                    self.assertEqual(launch.call_args.args[1][-2:], ['--session', 'ses_owned'])

    def test_removed_efforts_are_allowed_only_for_owned_session_compatibility(self):
        for variant in localai.LEGACY_VARIANTS:
            ref = {'providerID': 'local', 'id': 'qwen', 'variant': variant}
            self.assertFalse(localai.local_reference(ref))
            self.assertTrue(localai.local_reference(ref, legacy=True))
            self.assertTrue(localai.local_reference('local/qwen#' + variant, legacy=True))
        self.assertFalse(localai.local_reference('cloud/qwen#high', legacy=True))
        self.assertFalse(localai.local_reference('local/qwen#unknown', legacy=True))

    def test_memory_status_distinguishes_host_pressure_from_runtime_health(self):
        for level, label in ((1, 'normal'), (2, 'warning'), (4, 'critical'), (6, 'critical'), (None, 'unknown')):
            with patch.object(localai, 'resources', return_value=sample(level)):
                self.assertEqual(localai.memory_status()['pressure'], label)
        with patch.object(localai, 'resources', side_effect=OSError('unavailable')):
            self.assertEqual(localai.memory_status()['pressure'], 'unknown')

    def test_permission_modes_keep_default_prompts_and_unlock_only_on_opt_in(self):
        project = str(Path.cwd().resolve())
        modes = [([], False, False), (['--auto'], True, False),
                 (['--permissions', 'ask'], False, False),
                 (['--permissions', 'auto'], True, False),
                 (['--permissions', 'interactive'], False, True)]
        for flags, auto, interactive in modes:
            server = Mock(env=localai.environment({}), url='http://127.0.0.1:12345')
            owner = Mock(__enter__=Mock(return_value=server), __exit__=Mock(return_value=False))
            with patch.object(localai, 'prerequisites', return_value={}), \
                 patch.object(localai, 'dependency_report', return_value={}), \
                 patch.object(localai, 'ensure_runtime', return_value={'active_requests': 0, 'waiting_requests': 0}), \
                 patch.object(localai, 'NativeServer', return_value=owner), patch.object(localai, 'inventory'), \
                 patch.object(localai, 'mcp_status', return_value={}), \
                 patch.object(localai, 'guarded_run', return_value=0) as launch, \
                 patch.object(localai, 'await_runtime_idle'):
                self.assertEqual(localai.main([project, *flags]), 0)
                self.assertEqual('--auto' in launch.call_args.args[1], auto)
                self.assertEqual('OPENCODE_CLI_CONFIG_CONTENT' not in server.env, interactive)
                if not interactive:
                    self.assertEqual(json.loads(server.env['OPENCODE_CLI_CONFIG_CONTENT'])['session']['permissions'], 'prompt')
        with self.assertRaisesRegex(RuntimeError, '--auto'):
            localai.main(['doctor', '--auto'])
        with self.assertRaisesRegex(RuntimeError, '--permissions'):
            localai.main(['doctor', '--permissions', 'interactive'])
        with self.assertRaisesRegex(RuntimeError, '--web'):
            localai.main(['doctor', '--web'])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            localai.main([project, '--auto', '--permissions', 'ask'])

    def test_controls_are_available_offline_without_starting_or_authorizing_services(self):
        output = io.StringIO()
        with patch.object(localai.owner_auth, 'authorize') as auth, \
             patch.object(localai, 'run') as run, redirect_stdout(output):
            self.assertEqual(localai.main(['controls']), 0)
        auth.assert_not_called()
        run.assert_not_called()
        self.assertIn('/web', output.getvalue())
        self.assertIn('--permissions interactive', output.getvalue())

    def test_session_ownership_before_interrupt(self):
        server = Mock(directory=Path('/owned/project'))
        info = {'id': 'ses_abc', 'location': {'directory': '/owned/project'},
                'model': {'providerID': 'local', 'id': 'qwen', 'variant': 'fast'}}
        server.request.side_effect = [{'data': {'ses_abc': {}}}, {'data': info}, {'interrupted': True}]
        localai.interrupt_owned_sessions(server)
        self.assertEqual(server.request.call_args_list[-1].args[:2], ('POST', '/api/session/ses_abc/interrupt'))
        for changed in ({**info, 'location': {'directory': '/other'}}, {**info, 'model': 'cloud/qwen'}):
            server.reset_mock()
            server.request.side_effect = [{'data': {'ses_abc': {}}}, {'data': changed}]
            with self.assertRaisesRegex(RuntimeError, 'unrelated'):
                localai.interrupt_owned_sessions(server)
            self.assertTrue(all(c.args[0] == 'GET' for c in server.request.call_args_list))

    def test_stop_refuses_foreign_or_busy_runtime(self):
        args = Mock(command_or_project='stop', json_cli=False, deep=False, apply=False, profile=None, node=None, uv=None)
        for identity, state in ((RuntimeError('foreign'), {}), (42, {'active_requests': 1, 'waiting_requests': 0})):
            with patch.object(localai, 'runtime_identity', side_effect=identity if isinstance(identity, Exception) else None,
                              return_value=identity), patch.object(localai, 'runtime_metadata', return_value=state), \
                 patch.object(localai, 'runtime_command') as stop, self.assertRaises(RuntimeError):
                localai.run(args, {})
            stop.assert_not_called()

    def test_existing_init_never_reinstalls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cfg = root / 'xdg/config/opencode/opencode.json'
            cfg.parent.mkdir(parents=True)
            cfg.write_bytes(b'untouched')
            before = cfg.stat().st_mtime_ns
            with patch.object(localai, 'ROOT', root), patch.object(localai, 'prerequisites', return_value={}), \
                 patch.object(localai, 'dependency_report', return_value={}), \
                 patch.object(localai.subprocess, 'run') as process, redirect_stdout(io.StringIO()):
                self.assertEqual(localai.initialize(Mock(apply=True)), 0)
            process.assert_not_called()
            self.assertEqual((cfg.read_bytes(), cfg.stat().st_mtime_ns), (b'untouched', before))

    def test_fresh_init_requires_explicit_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'setup').mkdir()
            (root / 'setup/setup.py').write_text('# fixture')
            profile = root / 'setup/accepted-profile.json'
            profile.write_text('{}')
            for apply in (False, True):
                args = Mock(profile=profile, node=Path('/native/node'), uv=Path('/tools/uv'), apply=apply)
                with patch.object(localai, 'ROOT', root / 'absent'), patch.object(localai, 'PROJECT', root), \
                     patch.object(localai.subprocess, 'run', return_value=Mock(returncode=0)) as process, redirect_stdout(io.StringIO()):
                    self.assertEqual(localai.initialize(args), 0)
                vector = process.call_args.args[0]
                self.assertEqual(vector[1:3], ['-E', '-B'])
                self.assertEqual('--apply' in vector, apply)
                self.assertIn(str(profile), vector)

    def test_outcomes_do_not_leak_or_claim_task_success(self):
        for result in (0, RuntimeError('secret source /private/customer'), KeyboardInterrupt()):
            with patch.object(localai, 'run', side_effect=result if isinstance(result, BaseException) else None,
                              return_value=result), patch.object(localai.learning, 'foreground', return_value=nullcontext()), \
                 patch.object(localai.improvement, 'record_outcome') as record:
                if isinstance(result, BaseException):
                    with self.assertRaises(type(result)): localai.main(['.'])
                else:
                    self.assertEqual(localai.main(['.']), 0)
                entry = record.call_args.args[1]
                self.assertNotIn('secret', json.dumps(entry))
                self.assertNotIn('/private/customer', json.dumps(entry))
                self.assertLessEqual(set(entry), localai.improvement.FIELDS)
                self.assertEqual(entry['status'], 'incomplete' if result == 0 else 'interrupted'
                                 if isinstance(result, KeyboardInterrupt) else 'failure')

    def test_outcome_write_failure_is_not_success(self):
        with patch.object(localai, 'run', return_value=0), \
             patch.object(localai.learning, 'foreground', return_value=nullcontext()), \
             patch.object(localai.improvement, 'record_outcome', side_effect=OSError('denied')), \
             redirect_stderr(io.StringIO()), self.assertRaisesRegex(RuntimeError, 'not recorded'):
            localai.main(['.'])

    def test_deployer_preserves_foreign_kryn_and_keeps_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            root = home / 'Library/Application Support/LocalAI'
            profile = setup.load_profile(setup.HERE / 'accepted-profile.json')
            setup.write_same(root / 'install-profile.json', setup.encode(profile))
            setup.write_same(root / 'xdg/config/opencode/opencode.json', setup.encode(setup.render(root, home / 'node', profile)))
            marker = root / profile['model_parent'] / setup.model_id(profile) / '.localai-download.json'
            setup.write_same(marker, setup.encode({k: profile[k] for k in ('repository', 'revision')}))
            with patch.object(Path, 'home', return_value=home), patch.object(sys, 'argv', ['deploy', '--apply']), redirect_stdout(io.StringIO()):
                deploy_client.main()
                deploy_client.main()
            manifest = json.loads((root / 'client/deployment.json').read_text())
            with patch.object(localai, 'ROOT', root):
                self.assertEqual(localai.verify_release(current=False), manifest)
                with self.assertRaisesRegex(RuntimeError, 'not the installed release'):
                    localai.verify_release()
                with patch.object(localai, 'PROJECT', Path(manifest['directory'])):
                    self.assertEqual(localai.verify_release(), manifest)
            for path in (root/'kryn', root/'localai', home/'.local/bin/kryn', home/'.local/bin/localai'):
                self.assertEqual(path.read_text(), manifest['launcher'])
                self.assertIn(' -E -B ', path.read_text())
            self.assertTrue({'tools/context_probe.py', 'tools/improvement.py'} <= manifest['files'].keys())
            foreign = home / '.local/bin/kryn'
            foreign.write_text('# unowned replacement\n')
            before = (foreign.read_bytes(), foreign.stat().st_mtime_ns)
            for flags in ([], ['--apply']):
                with patch.object(Path, 'home', return_value=home), patch.object(sys, 'argv', ['deploy', *flags]), \
                     self.assertRaisesRegex(RuntimeError, 'Preserving unowned'):
                    deploy_client.main()
                self.assertEqual((foreign.read_bytes(), foreign.stat().st_mtime_ns), before)
            changed = Path(manifest['directory']) / 'tools/localai.py'
            changed.write_text('# changed')
            with patch.object(localai, 'ROOT', root), self.assertRaisesRegex(RuntimeError, 'release file changed'):
                localai.verify_release(current=False)

    def test_expected_runtime_allowlist_without_secret_output(self):
        profile = setup.load_profile(setup.HERE / 'accepted-profile.json')
        expected = {'global': setup.runtime_settings(Path('/owned'), profile), 'model': setup.model_settings(profile)}
        actual = copy.deepcopy(expected)
        actual['global']['api_key'] = 'private sentinel'
        actual['global']['memory']['memory_guard_custom_ceiling_gb'] = float(profile['memory_gib'])
        with patch.object(localai, 'private_json', side_effect=[expected, actual['global'], actual['model']]), \
             redirect_stdout(io.StringIO()) as output:
            self.assertIsNone(localai.validate_runtime_files(Path('/release')))
        self.assertEqual(output.getvalue(), '')
        modifications = [('global', ['model','model_dirs'], ['/other']), ('global',['model','model_fallback'],True),
                         ('global',['scheduler','max_concurrent_requests'],2), ('global',['memory','prefill_memory_guard'],False),
                         ('global',['memory','memory_guard_custom_ceiling_gb'],32), ('global',['cache','ssd_cache_max_size'],'16GB'),
                         ('global',['cache','hot_cache_max_size'],'1GB')]
        for key, value in [('max_context_window',65536),('max_tokens',16384),('mtp_enabled',True),
                           ('mtp_num_draft_tokens',4),('vlm_mtp_enabled',True),('dflash_enabled',True),
                           ('specprefill_enabled',True),('turboquant_kv_enabled',True),('qwen35_ane_prefill_enabled',True)]:
            modifications.append(('model',['models',localai.MODEL_ID,key],value))
        for section, keys, value in modifications:
            changed = copy.deepcopy(actual)
            cursor = changed[section]
            for key in keys[:-1]: cursor = cursor[key]
            cursor[keys[-1]] = value
            with self.subTest(keys=keys), patch.object(localai, 'private_json', side_effect=[expected,changed['global'],changed['model']]), \
                 self.assertRaisesRegex(RuntimeError, 'profile differs'):
                localai.validate_runtime_files(Path('/release'))

    def test_deep_model_hash_and_ordinary_disclosure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            model = root / localai.MODEL_PARENT / localai.MODEL_ID
            model.mkdir(parents=True)
            artifact = model / 'weights.safetensors'
            artifact.write_bytes(b'tiny deterministic fixture')
            profile = {'repository':localai.REPOSITORY, 'revision':localai.REVISION,
                       'model_parent':localai.MODEL_PARENT, 'memory_gib':localai.MEMORY_GIB,
                       'files':{'weights.safetensors':hashlib.sha256(artifact.read_bytes()).hexdigest()}}
            with patch.object(localai, 'ROOT', root), patch.object(localai, 'verify_release', return_value={'directory':'/release'}), \
                 patch.object(localai, 'private_json', return_value=profile):
                self.assertIn('not rehashed', localai.model_integrity())
                self.assertIn('SHA256 verified', localai.model_integrity(True))
                artifact.write_bytes(b'changed')
                with self.assertRaisesRegex(RuntimeError, 'content changed'):
                    localai.model_integrity(True)

    def test_control_socket_refuses_regular_and_link_before_any_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / 'control.sock'
            target.write_text('not a socket')
            linked = target.with_name('linked.sock')
            linked.symlink_to(target)
            for path in (target, linked):
                with patch.object(localai, 'CONTROL', path), patch.object(localai.subprocess, 'run') as process, \
                     patch.object(localai.socket, 'socket') as socket, self.assertRaises(RuntimeError):
                    localai.runtime_identity()
                process.assert_not_called()
                socket.assert_not_called()

    def test_only_verified_champion_snapshot_is_added_without_policy_changes(self):
        config = localai.expected_config()
        before = copy.deepcopy(config)
        for selected in (localai.learning.BASELINE, {'revision': hashlib.sha256(b'check').hexdigest(), 'instructions': 'check'}):
            with patch.object(localai.learning, 'active_champion', return_value=selected), \
                 patch.object(localai.improvement, 'active_skill_directory', side_effect=AssertionError('legacy activation must not run')):
                effective = localai.with_verified_skill(config)
            expected = copy.deepcopy(before)
            for item in expected['plugins']:
                if isinstance(item, dict): item['options']['champion'] = selected
            self.assertEqual(effective, expected)
            self.assertEqual(config, before)
        with patch.object(localai.learning, 'active_champion', side_effect=RuntimeError('artifact drift')), \
             self.assertRaisesRegex(RuntimeError, 'artifact drift'):
            localai.with_verified_skill(config)
        with patch.object(localai.learning, 'active_champion', return_value=selected) as champion:
            effective = localai.with_verified_skill(config, json_cli=True)
            champion.assert_called_once_with(localai.ROOT / 'state/improvement', scope='disposable_json_cli')
        product = next(item for item in effective['plugins'] if isinstance(item, dict))
        self.assertEqual(product['options']['workflowScope'], 'disposable_json_cli')
        self.assertEqual(product['options']['champion'], selected)
        self.assertEqual(config, before)

    def test_improve_uses_only_owned_automatic_controls_without_task_success_record(self):
        for tail in ([], ['status'], ['pause'], ['disable']):
            with patch.object(localai, 'verify_release') as verify, \
                 patch.object(localai.learning, 'status', return_value={}) as status, \
                 patch.object(localai.learning, 'control', return_value={}) as controls, \
                 patch.object(localai.improvement, 'record_outcome') as record, redirect_stdout(io.StringIO()):
                self.assertEqual(localai.main(['improve', *tail]), 0)
            verify.assert_called_once_with()
            if not tail or tail == ['status']:
                status.assert_called_once_with(localai.ROOT/'state/improvement')
            else:
                controls.assert_called_once_with(localai.ROOT/'state/improvement', tail[0])
            record.assert_not_called()
        for tail in (['--state','/elsewhere','status'], ['--state=/elsewhere','status'], ['--sta','/elsewhere','status'], ['--s=/elsewhere','status'], ['promote','unqualified']):
            with patch.object(localai, 'verify_release'), patch.object(localai.learning, 'control') as controls, self.assertRaises(RuntimeError):
                localai.main(['improve', *tail])
            controls.assert_not_called()


if __name__ == '__main__': unittest.main()
