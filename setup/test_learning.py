"""Offline controls and disposable black-box grader tests; no model/runtime calls."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from unittest.mock import MagicMock
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import learning
import native_client


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)
        self.state = self.base / 'state'

    def event(self, **extra):
        return {**dict(schema=1, task_id='a'*64, champion_revision=learning.EMPTY,
                      profile_id='b'*64, state='unknown', wall_seconds=8,
                      tool_calls=4, tool_errors=2, check_passes=0, check_failures=1,
                      compactions=0, corrections=None, output_tokens=100, family='unknown',
                      completed_at=datetime.now(timezone.utc).isoformat()), **extra}

    def candidate(self):
        return learning.parse_proposal(json.dumps(dict(decision='propose', instructions='For JSON CLI tasks, run relevant checks before reporting completion.',
            scope='disposable_json_cli', reason='verification_gap')))

    def rows(self, baseline=100, candidate=80):
        result = []
        for family in learning.FAMILIES:
            for repeat in range(3):
                for arm in ('baseline', 'candidate'):
                    result.append(dict(family=family, repeat=repeat, arm=arm, split='selection',
                        passed=True, native_completed=True, conditions_verified=True,
                        cache_matched=True, seconds=baseline if arm == 'baseline' else candidate))
        result += [dict(family=family, repeat=0, arm='candidate', split='protected', passed=True,
                        conditions_verified=True, seconds=80) for family in learning.FAMILIES]
        return result

    def test_event_has_no_private_content_channel(self):
        self.assertEqual(learning.valid_event(self.event())['state'], 'unknown')
        for extra in ({'prompt': 'secret'}, {'task_id': '/private/name'}, {'tool_calls': -1}):
            with self.assertRaises(ValueError): learning.valid_event(self.event(**extra))
        self.assertFalse(learning.meaningful(self.event(tool_errors=0, check_failures=0)))

    def test_proposal_is_generated_data_with_exact_instruction_hash(self):
        candidate = self.candidate()
        self.assertEqual(candidate['revision'], hashlib.sha256(candidate['instructions'].encode()).hexdigest())
        for change in ({'scope':'security'}, {'instructions':'x'*1501}, {'decision':'execute'}):
            value = {k:v for k,v in candidate.items() if k != 'revision'}; value.update(change)
            with self.assertRaises(ValueError): learning.parse_proposal(json.dumps(value))

    def test_relay_overrides_every_native_config_layer_and_preserves_selected_variant(self):
        config={'model':'local/qwen#low','agents':{'build':{'model':'local/qwen#low'}},
                'providers':{'local':{'settings':{'baseURL':'http://127.0.0.1:8000/v1'},'models':{'qwen':{
                    'settings':{'baseURL':'http://127.0.0.1:8000/v1'},'variants':[{'id':'low','settings':{'baseURL':'http://127.0.0.1:8000/v1'}}]}}}},
                'plugins':[{'package':'/reviewed/plugin','options':{'champion':learning.BASELINE}}]}
        base='http://127.0.0.1:19876/v1'
        effective=learning.plugin_config(config,learning.BASELINE,self.base,base)
        provider=effective['providers']['local']; model=provider['models']['qwen']
        self.assertEqual(provider['settings']['baseURL'],base)
        self.assertEqual(model['settings']['baseURL'],base)
        self.assertEqual(model['variants'][0]['settings']['baseURL'],base)
        self.assertEqual(effective['agents']['build']['model'],'local/qwen#low')
        self.assertEqual(effective['plugins'][0]['options']['inferenceBaseURL'],base)
        self.assertEqual(effective['plugins'][0]['options']['workflowScope'],'disposable_json_cli')
        self.assertEqual(config['providers']['local']['settings']['baseURL'],'http://127.0.0.1:8000/v1')

    def test_reflection_uses_frozen_fast_profile_and_trials_preserve_selected_variant(self):
        import context_probe
        import owner_auth
        workspace=self.base/'run'/'workspace'; workspace.mkdir(parents=True)
        private=self.base/'private'; private.mkdir()
        config={'model':'local/qwen#think','agents':{'build':{'model':'local/qwen#think'}},
                'providers':{'local':{'settings':{'baseURL':'http://127.0.0.1:8000/v1'},'models':{'qwen':{
                    'modelID':'test-model','body':{'max_tokens':4096},'variants':[{'id':'fast'},{'id':'think'}]}}}},
                'plugins':[{'package':'/reviewed/plugin','options':{'champion':learning.BASELINE}}]}
        requests=[]
        def request(method,path,body=None,**kwargs):
            requests.append((method,path,body))
            if path=='/api/session': return {'data':{'id':'ses_test'}}
            return {'data':{'info':{'outcome':'succeeded'},'messages':[{'type':'assistant','finish':'stop',
                     'model':{'providerID':'local','id':'qwen'},'content':[{'type':'text','text':'{}'}]}]}}
        server=SimpleNamespace(env={},background_prefix=[],url='http://127.0.0.1:19877',request=request,temporary=SimpleNamespace(name=str(private)))
        owner=MagicMock(); owner.__enter__.return_value=server
        relay=SimpleNamespace(port=19876,records=[{'model':'test-model'}],cancel=lambda:None)
        relay_owner=MagicMock(); relay_owner.__enter__.return_value=relay
        child=MagicMock(returncode=0); child.communicate.return_value=(b'{}',None); child.poll.return_value=0
        sample={'pressure_level':1,'swap_used_bytes':0,'listener_processes':[{'pid':123,'rss_bytes':1,'phys_footprint_bytes':1}]}
        with patch.object(native_client,'NativeServer',return_value=owner), patch.object(native_client,'background_boundary',return_value=[]), \
             patch.object(learning,'InferenceRelay',return_value=relay_owner), patch.object(learning,'settle_background',return_value={'idle':True}), \
             patch.object(context_probe,'resources',return_value=sample), patch.object(owner_auth,'authorize'), \
             patch.object(learning.subprocess,'Popen',return_value=child) as launch, patch.object(learning.time,'sleep'), \
             patch.object(learning,'grade',return_value={'passed':True}):
            result=learning.native_turn(self.state,config,workspace,'reflect',learning.BASELINE,120,reflection=True)
            reflection_command=launch.call_args.args[0]
            trial_workspace=self.base/'trial'/'workspace'; trial_workspace.mkdir(parents=True)
            (trial_workspace.parent/'case.json').write_text(json.dumps({'family':'collections','split':'selection'}))
            trial=learning.native_turn(self.state,config,trial_workspace,'repair',learning.BASELINE,120)
            trial_command=launch.call_args.args[0]
            failed_workspace=self.base/'failed'/'workspace'; failed_workspace.mkdir(parents=True)
            child.returncode=1; child.poll.return_value=1
            child.communicate.return_value=(b'{"type":"error","message":"UnexpectedStatus"}',b'synthetic startup failure')
            relay.records=[]
            failed=learning.native_turn(self.state,config,failed_workspace,'reflect',learning.BASELINE,120,reflection=True)
        self.assertTrue(result['native_completed'])
        self.assertTrue(trial['native_completed'])
        create,trial_create=[body for method,path,body in requests if path=='/api/session'][:2]
        self.assertEqual(create['model']['variant'],'fast')
        self.assertEqual(create['title'],'KRYN background reflection')
        self.assertIsInstance(create['model']['variant'],str)
        self.assertEqual(create['permissions'],[{'action':'*','resource':'*','effect':'deny'}])
        self.assertIn('local/qwen#fast',reflection_command)
        self.assertEqual(trial_create['model']['variant'],'think')
        self.assertEqual(trial_create['title'],'KRYN background trial')
        self.assertIn('local/qwen#think',trial_command)
        self.assertEqual(config['agents']['build']['model'],'local/qwen#think')
        requested=json.loads((workspace.parent/'evidence/requested-config.json').read_text())
        self.assertEqual(requested['agents']['build']['model'],'local/qwen#fast')
        self.assertEqual(requested['providers']['local']['models']['qwen']['body']['max_tokens'],768)
        telemetry=json.loads((workspace.parent/'evidence/telemetry.json').read_text())
        self.assertEqual(telemetry['requested_variant'],'fast')
        self.assertTrue(telemetry['settlement']['idle'])
        self.assertEqual(telemetry['resources'][0]['pressure_level'],1)
        self.assertFalse(failed['native_completed'])
        self.assertEqual(failed['requests'],[])
        failure=json.loads((failed_workspace.parent/'evidence/native-process.json').read_text())
        self.assertEqual(failure['exit_code'],1)
        self.assertIn('UnexpectedStatus',failure['stdout'])
        self.assertEqual(failure['stderr'],'synthetic startup failure')
        failed_telemetry=json.loads((failed_workspace.parent/'evidence/telemetry.json').read_text())
        self.assertEqual(failed_telemetry['native_process']['exit_code'],1)
        self.assertTrue(failed_telemetry['dispatch_evidence_complete'])
        self.assertNotIn('UnexpectedStatus',json.dumps(failed_telemetry))

    def test_failed_native_diagnostics_are_bounded_private_and_content_free_in_telemetry(self):
        logs=learning.state._directory(self.base/'evidence')
        result=learning.record_native_process(logs,b'x'*(2*1024**2+1),b'private error'*(64*1024),1)
        raw=json.loads((logs/'native-process.json').read_text())
        self.assertEqual(len(raw['stdout']),2*1024**2)
        self.assertEqual(len(raw['stderr']),64*1024)
        self.assertTrue(result['stdout_truncated'])
        self.assertTrue(result['stderr_truncated'])
        self.assertEqual((logs/'native-process.json').stat().st_mode & 0o777,0o600)
        safe=learning.safe_run_telemetry({'native_process':raw})
        self.assertNotIn('private error',json.dumps(safe))
        self.assertNotIn('stdout',safe['native_process'])

    def test_run_telemetry_drops_private_content_and_preserves_settlement_evidence(self):
        secret='SYNTHETIC_SECRET_PROMPT_ANSWER_URL'
        raw={'schema':1,'policy':learning.POLICY['version'],'reflection':False,'requested_model':'test',
             'requested_variant':'fast','champion_revision':learning.EMPTY,'started_unix':123,
             'prompt':secret,'text':secret,'expected_answers':secret,
             'requests':[{'max_tokens':768,'started':125,'tool_count':0,'body':secret,'messages':[secret],
                'thinking':{'enable_thinking':False,'private':secret},
                'numeric':{'temperature':.7,'max_tokens':768,'private':secret}}],
             'settlement':{'idle':True,'acknowledged':True,'idle_samples':2,'acknowledgement_count':1,
                'interrupted_count':1,'seconds':.8,'body':secret},
             'samples':[{'pressure_level':1,'swap_used_bytes':0,'prompt':secret,
                 'listener_processes':[{'pid':42,'rss_bytes':4096,'command':secret}]}]}
        safe=learning.safe_run_telemetry(raw)
        self.assertNotIn(secret,json.dumps(safe))
        self.assertNotIn('messages',json.dumps(safe))
        self.assertEqual(safe['settlement']['acknowledgement_count'],1)
        self.assertEqual(safe['settlement']['idle_samples'],2)
        self.assertEqual(safe['requests'][0]['enable_thinking'],False)
        self.assertEqual(safe['resources'][0]['listeners'][0]['pid'],42)

    def test_missing_frozen_reflection_variant_fails_without_fallback_or_process(self):
        import owner_auth
        workspace=self.base/'workspace'; workspace.mkdir()
        config={'agents':{'build':{'model':'local/qwen#think'}},'providers':{'local':{'models':{'qwen':{
            'modelID':'test','variants':[{'id':'think'}]}}}}}
        with patch.object(owner_auth,'authorize'), patch.object(learning,'InferenceRelay') as relay:
            with self.assertRaisesRegex(RuntimeError,'no fallback'):
                learning.native_turn(self.state,config,workspace,'reflect',learning.BASELINE,120,reflection=True)
        relay.assert_not_called()
        self.assertEqual(json.loads((self.base/'evidence/telemetry.json').read_text())['error_class'],'RuntimeError')

    def test_repeated_efficiency_can_promote_without_baseline_failure(self):
        rows = self.rows()
        self.assertEqual(learning.decide(rows, protected_complete=True), ('accept','noninferior_efficiency_gain'))
        self.assertEqual(learning.decide(rows[:2])[0], 'defer')
        for row in rows: row['cache_matched'] = False
        self.assertEqual(learning.decide(rows, protected_complete=True), ('reject','no_defensible_benefit'))

    def test_no_gain_regression_incomplete_and_lucky_pair(self):
        self.assertEqual(learning.decide(self.rows(candidate=99), protected_complete=True)[0], 'reject')
        rows = self.rows(); rows[1]['passed'] = False
        self.assertEqual(learning.decide(rows, protected_complete=True)[1], 'correctness_regression')
        rows = self.rows(); rows[0]['conditions_verified'] = False
        self.assertEqual(learning.decide(rows, protected_complete=True)[0], 'defer')
        self.assertEqual(learning.decide(self.rows()[:-3])[1], 'protected_checks_required')

    def test_immutable_champion_and_repeated_regression_rollback(self):
        candidate = self.candidate(); rows = self.rows()
        learning.promote(self.state, candidate, rows)
        active = learning.active_champion(self.state, scope='disposable_json_cli')
        self.assertEqual(active['revision'], candidate['revision'])
        self.assertEqual(learning.active_champion(self.state), learning.BASELINE)
        self.assertEqual(learning.active_champion(self.state, scope='research'), learning.BASELINE)
        with self.assertRaises(RuntimeError): learning.rollback(self.state, active['revision'], [])
        learning.rollback(self.state, active['revision'], [dict(previous_passed=True,current_passed=False)]*2)
        self.assertEqual(learning.active_champion(self.state), learning.BASELINE)
        self.assertEqual(active['revision'], candidate['revision'])  # Prior in-memory session pin is unchanged.

    def test_foreground_intent_is_held_and_stale_intent_is_removed(self):
        with learning.foreground(self.state):
            self.assertTrue(learning.foreground_requested(self.state))
        self.assertFalse(learning.foreground_requested(self.state))
        directory = learning.root(self.state) / 'intent'
        stale = directory / ('c'*32+'.json'); stale.write_text('{}')
        self.assertFalse(learning.foreground_requested(self.state))
        self.assertFalse(stale.exists())

    def test_foreground_exception_does_not_reenter_context(self):
        with self.assertRaisesRegex(RuntimeError, 'application'):
            with learning.foreground(self.state): raise RuntimeError('application')
        self.assertFalse(learning.foreground_requested(self.state))

    def test_foreground_cooperatively_preempts_optional_lease(self):
        started, acknowledged = threading.Event(), threading.Event()
        def optional():
            with learning.state.foreground(self.state):
                started.set()
                until = time.monotonic() + 2
                while time.monotonic() < until and not learning.foreground_requested(self.state): time.sleep(.01)
                acknowledged.set()
        worker = threading.Thread(target=optional)
        worker.start(); self.assertTrue(started.wait(1))
        clock = time.monotonic()
        with learning.foreground(self.state):
            self.assertTrue(acknowledged.is_set())
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertLess(time.monotonic()-clock,1)

    def test_pause_disable_and_budget(self):
        learning.control(self.state, 'pause'); self.assertTrue(learning.foreground_requested(self.state))
        learning.control(self.state, 'resume'); self.assertFalse(learning.foreground_requested(self.state))
        learning.control(self.state, 'disable'); self.assertTrue(learning.foreground_requested(self.state))
        self.assertEqual(learning.budget(self.state)['seconds'], 0)

    def test_final_prospective_opportunity_preserves_spent_time_and_stops_at_three(self):
        base=learning.root(self.state)
        previous={'date':learning.utc_day(),'seconds':15.200058583985083,'candidates':2}
        learning.put(base/'budget.json',previous)
        learning.put(base/'consumed.json',['b'*64,'c'*64])
        learning.reserve_reflection_attempt(self.state,self.event())
        self.assertEqual(learning.budget(self.state),{**previous,'candidates':3})
        self.assertEqual(set(learning.read(base/'consumed.json')),{'a'*64,'b'*64,'c'*64})
        with self.assertRaises(learning.state.Deferred):
            learning.reserve_reflection_attempt(self.state,self.event(task_id='d'*64))
        self.assertEqual(learning.budget(self.state)['seconds'],previous['seconds'])

    def test_exit_prunes_nonactionable_events_without_starting_worker(self):
        folder=learning.state._directory(learning.root(self.state)/'events')
        for index in range(503):
            item=self.event(task_id=f'{index:064x}',tool_errors=0,check_failures=0)
            learning.state._write_new(folder/(item['task_id']+'.json'),item)
        with patch.object(learning.subprocess,'Popen') as launch:
            self.assertIsNone(learning.start_after_exit(self.state,{}))
        launch.assert_not_called()
        self.assertEqual(len(list(folder.glob('*.json'))),500)

    def test_blackbox_rejects_forged_counters_and_import_tampering(self):
        workspace = self.base / 'workspace'; workspace.mkdir()
        program = workspace / 'solve.py'
        program.write_text('import json,os\nprint(json.dumps({"tests_run":3,"passed":True,"failures":0,"errors":0}),flush=True)\nos._exit(0)\n')
        self.assertFalse(learning.grade(workspace,'collections')['passed'])
        program.write_text('import unittest,json\nunittest.TestCase.assertEqual=lambda *a:None\nprint(json.dumps([]))\n')
        self.assertFalse(learning.grade(workspace,'collections')['passed'])
        self.assertNotEqual(unittest.TestCase.assertEqual.__name__, '<lambda>')
        program.write_text('import json,sys\nseen=set();out=[]\nfor x in json.load(sys.stdin):\n if x.casefold() not in seen: out.append(x);seen.add(x.casefold())\nprint(json.dumps(out))\n')
        self.assertTrue(learning.grade(workspace,'collections')['passed'])
        self.assertTrue(learning.grade(workspace,'collections',True)['passed'])

    def test_all_selection_graders_accept_correct_and_reject_broken_programs(self):
        workspace=self.base/'workspace'; workspace.mkdir()
        solutions={
            'collections':'import json,sys\nout=[];seen=set()\nfor x in json.load(sys.stdin):\n if x.casefold() not in seen:out.append(x);seen.add(x.casefold())\nprint(json.dumps(out))\n',
            'records':"import json,sys\nx=json.load(sys.stdin)\nrows=[r for r in x['rows'] if 'project' not in x or r['project']==x['project']]\nprint(json.dumps({'count':len(rows),'minutes':sum(r['minutes'] for r in rows)}))\n",
            'text':"import csv,io,json,sys\nx=json.load(sys.stdin)\nprint(json.dumps([{'name':r['name'],'minutes':int(r['minutes'])} for r in csv.DictReader(io.StringIO(x['text'].lstrip('\\ufeff')))]))\n"}
        for family,good in solutions.items():
            with self.subTest(family=family):
                (workspace/'solve.py').write_text(learning.fixture(family)[1])
                self.assertFalse(learning.grade(workspace,family)['passed'])
                (workspace/'solve.py').write_text(good)
                self.assertTrue(learning.grade(workspace,family)['passed'])
                self.assertTrue(learning.grade(workspace,family,True)['passed'])

    def test_grading_yields_before_starting_another_candidate_process(self):
        with patch.object(learning.subprocess,'Popen') as launch:
            self.assertFalse(learning.grade(self.base,'collections',cancel=lambda:True)['passed'])
        launch.assert_not_called()

    def test_whole_process_boundary_has_no_home_state_or_runtime_admin_allowance(self):
        workspace = self.base / 'workspace'; private = self.base / 'private'
        workspace.mkdir(); private.mkdir()
        prefix = native_client.background_boundary(workspace, private, [Path(sys.prefix).resolve()], 19876, 19877)
        profile = prefix[-1]
        self.assertIn('(deny file-read-data)', profile)
        self.assertIn('(deny network*)', profile)
        self.assertIn('(allow process-info* (target self))',profile)
        self.assertIn('(literal '+json.dumps(str(self.base.parent))+')',profile)
        self.assertNotIn('(subpath '+json.dumps(str(self.base.parent))+')',profile)
        self.assertIn('(subpath "/private/var/db/timezone")',profile)
        self.assertIn('localhost:19876',profile)
        self.assertNotIn('localhost:8000',profile)
        self.assertIn('opencode.jsonc',profile)
        self.assertNotIn('(subpath '+json.dumps(str(Path.home()))+')',profile)
        with self.assertRaises(RuntimeError): native_client.background_boundary(Path.home(),private,[],19876)
        grading = native_client.background_boundary(workspace,private,[Path(sys.prefix).resolve()],None)[-1]
        self.assertNotIn('(allow network-outbound',grading)

    def test_installed_nested_venv_does_not_expose_package_or_hidden_answers(self):
        runtime=self.base/'base-python'; runtime.mkdir()
        binary=runtime/'python'; binary.write_text('interpreter')
        venv=self.base/'packages'/'release'/'venv'; venv.mkdir(parents=True)
        (venv/'pyvenv.cfg').write_text('home = '+str(runtime))
        payload=venv/'lib'/'python3.13'/'site-packages'/'kryn_cli'/'payload'
        (payload/'tools').mkdir(parents=True)
        (payload/'tools'/'learning.py').write_text('HIDDEN_EXPECTED_ANSWER')
        workspace=self.base/'workspace'; workspace.mkdir()
        private=self.base/'private'; private.mkdir()
        with patch.object(learning.sys,'prefix',str(venv)), patch.object(learning.sys,'base_prefix',str(runtime)), patch.object(learning.sys,'executable',str(binary)):
            dependencies=learning.python_dependencies()
        self.assertNotIn(venv,dependencies)
        self.assertEqual(set(dependencies),{runtime,binary,venv/'pyvenv.cfg'})
        with patch.object(native_client,'PROJECT',payload):
            profile=native_client.background_boundary(workspace,private,dependencies,None)[-1]
        self.assertIn('(deny file-read-data file-write* (subpath '+json.dumps(str(payload/'tools')),profile)
        self.assertNotIn('(subpath '+json.dumps(str(venv))+')',profile)

    def test_native_background_uses_private_discovery_and_read_only_public_git(self):
        workspace=self.base/'workspace'; workspace.mkdir()
        server=native_client.NativeServer(workspace,{},self.base/'native.log',
                                         background={'dependencies':[],'inference_port':19876})
        process=MagicMock(); process.poll.return_value=None
        try:
            with patch.object(native_client.subprocess,'Popen',return_value=process), \
                 patch.object(server,'request',return_value={}):
                server._enter_background()
            self.assertEqual(server.env['OPENCODE_TEST_HOME'],server.temporary.name)
            self.assertEqual(server.env['HOME'],server.temporary.name)
            self.assertEqual(server.env['OPENCODE_CONFIG_PROJECT_DISABLE'],'true')
            profile=server.background_prefix[-1]
            toolchain=Path('/Library/Developer/CommandLineTools')
            if toolchain.is_dir():self.assertIn('(subpath '+json.dumps(str(toolchain.resolve()))+')',profile)
            self.assertIn('(deny file-write*)',profile)
            self.assertNotIn('(subpath '+json.dumps(str(Path.home()))+')',profile)
            writes='(allow file-write* (subpath '+json.dumps(str(workspace))+') (subpath '+json.dumps(server.temporary.name)+'))'
            self.assertIn(writes,profile)
        finally:
            if server.log_file:server.log_file.close()
            if server.temporary:server.temporary.cleanup()

    def test_automatic_control_flow_runs_reflection_and_all_matched_trials_then_rejects(self):
        base = learning.root(self.state); folder = learning.state._directory(base/'events')
        item = self.event(); learning.state._write_new(folder/(item['task_id']+'.json'),item)
        calls=[]
        def fake_turn(directory,config,workspace,prompt,champion,seconds,reflection=False):
            calls.append(reflection)
            if reflection:
                proposal={k:v for k,v in self.candidate().items() if k!='revision'}
                return dict(native_completed=True,conditions_verified=True,text=json.dumps(proposal))
            return dict(passed=True,native_completed=True,conditions_verified=True,cache_matched=True,seconds=10,reason='completed')
        with patch.dict(learning.POLICY,idle_seconds=0), patch.object(learning,'power_ready',return_value=True):
            learning.worker(self.state, {}, turn=fake_turn)
        self.assertEqual(calls.count(True),1)
        self.assertEqual(calls.count(False),18)
        decision=learning.read(base/'last-decision.json')
        self.assertEqual((decision['decision'],decision['reason']),('reject','no_defensible_benefit'))
        self.assertEqual(learning.active_champion(self.state),learning.BASELINE)
        self.assertEqual(learning.read(base/'queue.json'),[])
        self.assertEqual(learning.budget(self.state)['candidates'],1)

    def test_zero_dispatch_failure_is_charged_and_retryable_without_rewriting_prior_history(self):
        base=learning.root(self.state); item=self.event()
        learning.state._write_new(learning.state._directory(base/'events')/(item['task_id']+'.json'),item)
        original={'date':learning.utc_day(),'seconds':5.542,'candidates':1}
        learning.put(base/'budget.json',original)
        learning.put(base/'consumed.json',['c'*64])
        prior=learning.record_decision(self.state,None,'defer','prior_reflection_incomplete')
        archived=next((base/'decisions').glob('*.json')); archived_bytes=archived.read_bytes()
        calls=[]
        def startup_failure(directory,config,workspace,*args,**kwargs):
            calls.append(workspace)
            evidence=learning.state._directory(workspace.parent/'evidence')
            learning.state._write_new(evidence/'telemetry.json',{'dispatch_evidence_complete':True,'requests':[]})
            time.sleep(.01)
            return {'native_completed':False,'conditions_verified':False,'requests':[]}
        with patch.dict(learning.POLICY,idle_seconds=0),patch.object(learning,'power_ready',return_value=True):
            learning.worker(self.state,{},turn=startup_failure)
        self.assertEqual(len(calls),1)  # No retry loop inside a worker invocation.
        self.assertEqual(learning.budget(self.state)['candidates'],1)
        self.assertGreater(learning.budget(self.state)['seconds'],original['seconds'])
        self.assertEqual(learning.read(base/'consumed.json'),['c'*64])
        self.assertEqual(archived.read_bytes(),archived_bytes)
        receipt=learning.read(calls[0].parent/'reflection-attempt.json')
        self.assertTrue(receipt['candidate_reserved'])
        self.assertTrue(receipt['release_authorized'])
        self.assertEqual(receipt['accepted_requests'],0)
        self.assertEqual(learning.read(base/'last-decision.json')['reason'],'reflection_startup_no_dispatch')

    def test_incomplete_or_uncertain_dispatch_and_post_dispatch_exception_spend_attempt(self):
        for label,telemetry,raises in (
            ('missing',None,False),
            ('incomplete',{'requests':[]},False),
            ('model_failure',{'dispatch_evidence_complete':True,'requests':[{}]},False),
            ('exception',{'dispatch_evidence_complete':True,'requests':[{}]},True),
        ):
            with self.subTest(label=label):
                directory=self.base/label; base=learning.root(directory); item=self.event()
                learning.state._write_new(learning.state._directory(base/'events')/(item['task_id']+'.json'),item)
                def failure(directory,config,workspace,*args,**kwargs):
                    if telemetry is not None:
                        learning.state._write_new(learning.state._directory(workspace.parent/'evidence')/'telemetry.json',telemetry)
                    if raises: raise RuntimeError('synthetic adapter failure')
                    return {'native_completed':False,'conditions_verified':False,'requests':[]}
                with patch.dict(learning.POLICY,idle_seconds=0),patch.object(learning,'power_ready',return_value=True):
                    learning.worker(directory,{},turn=failure)
                self.assertEqual(learning.budget(directory)['candidates'],1)
                self.assertEqual(learning.read(base/'consumed.json'),[item['task_id']])
                decision=learning.read(base/'last-decision.json')
                self.assertEqual(decision['reason'],'reflection_incomplete')
                self.assertTrue(decision['candidate_spent'])
                if raises:self.assertEqual(decision['error_class'],'RuntimeError')

    def test_attempt_reservation_survives_failed_diagnostics_and_process_interruptions(self):
        for label,exception in (('diagnostic_error',None),('keyboard',KeyboardInterrupt),('exit',SystemExit)):
            with self.subTest(label=label):
                directory=self.base/label; base=learning.root(directory); item=self.event()
                learning.state._write_new(learning.state._directory(base/'events')/(item['task_id']+'.json'),item)
                write=learning.state._write_new
                def fail_receipt(path,value):
                    if label=='diagnostic_error' and Path(path).name=='reflection-attempt.json':
                        raise OSError('synthetic full disk')
                    return write(path,value)
                def turn(directory,config,workspace,*args,**kwargs):
                    self.assertEqual(learning.budget(directory)['candidates'],1)
                    self.assertIn(item['task_id'],learning.read(base/'consumed.json'))
                    learning.state._write_new(learning.state._directory(workspace.parent/'evidence')/'telemetry.json',
                                             {'dispatch_evidence_complete':True,'requests':[{}]})
                    if exception:raise exception('synthetic interruption after dispatch')
                    return {'native_completed':False,'conditions_verified':False}
                with patch.dict(learning.POLICY,idle_seconds=0),patch.object(learning,'power_ready',return_value=True), \
                     patch.object(learning.state,'_write_new',side_effect=fail_receipt):
                    with self.assertRaises(exception or OSError):learning.worker(directory,{},turn=turn)
                self.assertEqual(learning.budget(directory)['candidates'],1)
                self.assertEqual(learning.read(base/'consumed.json'),[item['task_id']])
                self.assertGreater(learning.budget(directory)['seconds'],0)

    def test_failed_zero_dispatch_receipt_cannot_release_reservation(self):
        item=self.event(); folder=learning.state._directory(self.base/'run')
        reservation=learning.reserve_reflection_attempt(self.state,item)
        learning.state._write_new(learning.state._directory(folder/'evidence')/'telemetry.json',
                                 {'dispatch_evidence_complete':True,'requests':[]})
        with patch.object(learning.state,'_write_new',side_effect=OSError('synthetic full disk')):
            with self.assertRaises(OSError):
                learning.finish_reflection_attempt(self.state,folder,item,{},reservation,time_charged=True)
        self.assertEqual(learning.budget(self.state)['candidates'],1)
        self.assertEqual(learning.read(learning.root(self.state)/'consumed.json'),[item['task_id']])

    def test_zero_dispatch_requires_successful_elapsed_time_charge_to_release(self):
        item=self.event(); folder=learning.state._directory(self.base/'run')
        reservation=learning.reserve_reflection_attempt(self.state,item)
        learning.state._write_new(learning.state._directory(folder/'evidence')/'telemetry.json',
                                 {'dispatch_evidence_complete':True,'requests':[]})
        attempt=learning.finish_reflection_attempt(self.state,folder,item,{},reservation,time_charged=False)
        self.assertTrue(attempt['candidate_spent'])
        self.assertFalse(attempt['release_authorized'])
        self.assertEqual(learning.budget(self.state)['candidates'],1)
        self.assertEqual(learning.read(learning.root(self.state)/'consumed.json'),[item['task_id']])

    def test_reservation_setup_failure_never_calls_inference(self):
        for filename in ('budget.json','consumed.json'):
            with self.subTest(filename=filename):
                directory=self.base/filename; base=learning.root(directory); item=self.event()
                learning.state._write_new(learning.state._directory(base/'events')/(item['task_id']+'.json'),item)
                write=learning.put
                def fail_reservation(path,value):
                    if Path(path).name==filename:raise OSError('synthetic reservation setup failure')
                    return write(path,value)
                turn=MagicMock()
                with patch.dict(learning.POLICY,idle_seconds=0),patch.object(learning,'power_ready',return_value=True), \
                     patch.object(learning,'put',side_effect=fail_reservation):
                    with self.assertRaises(OSError):learning.worker(directory,{},turn=turn)
                turn.assert_not_called()

    def test_monitor_dispatches_real_adapter_pairs_and_rolls_back_only_repeated_regression(self):
        candidate=self.candidate(); learning.promote(self.state,candidate,self.rows())
        base=learning.root(self.state); folder=learning.state._directory(base/'events')
        for character in ('d','e'):
            item=self.event(task_id=character*64,champion_revision=candidate['revision'],family='json_cli')
            learning.state._write_new(folder/(item['task_id']+'.json'),item)
        calls=[]
        def adapter(directory,config,workspace,prompt,champion,seconds):
            calls.append(champion['revision'])
            return dict(passed=champion==learning.BASELINE,native_completed=True,conditions_verified=True,cache_matched=False,seconds=1,reason='completed')
        with patch.object(learning,'power_ready',return_value=True): learning.monitor_champion(self.state,{},adapter)
        self.assertEqual(len(calls),4)
        self.assertEqual(learning._champion(self.state),learning.BASELINE)
        self.assertEqual(learning.read(base/'last-decision.json')['decision'],'rollback')

    def test_monitor_ignores_failures_without_explicit_matching_workflow_scope(self):
        candidate=self.candidate(); learning.promote(self.state,candidate,self.rows())
        folder=learning.state._directory(learning.root(self.state)/'events')
        for character in ('d','e'):
            item=self.event(task_id=character*64,champion_revision=candidate['revision'],family='unknown')
            learning.state._write_new(folder/(item['task_id']+'.json'),item)
        adapter=MagicMock()
        learning.monitor_champion(self.state,{},adapter)
        adapter.assert_not_called()
        self.assertEqual(learning.active_champion(self.state,scope='disposable_json_cli')['revision'],candidate['revision'])


if __name__ == '__main__': unittest.main()
