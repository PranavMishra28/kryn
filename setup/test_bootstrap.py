"""Actual shell/stub tests and fake-account deployment; never install or infer."""
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import setup
import deploy_client

SOURCE = Path(__file__).resolve().parents[1]


class BootstrapChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kryn-bootstrap-')
        self.root = Path(self.tmp.name).resolve()
        self.kit = self.root / 'source kit with spaces'
        (self.kit / 'tools').mkdir(parents=True)
        (self.kit / 'setup').mkdir()
        shutil.copyfile(SOURCE / 'bootstrap', self.kit / 'bootstrap')
        (self.kit / 'bootstrap').chmod(0o755)
        (self.kit / 'tools/localai.py').write_text('# never executed by stub')
        (self.kit / 'setup/accepted-profile.json').write_text('{}')
        self.bin = self.root / 'stub bin'
        self.bin.mkdir()
        self.stub = self.bin / 'python3.13'
        # This stub records exact invocation; it never executes a supplied file.
        self.stub.write_text('#!' + sys.executable + '\nimport json,os,sys\n'
            'with open(os.environ["KRYN_STUB_RECORD"],"a") as f:\n'
            ' f.write(json.dumps({"argv":sys.argv[1:],"cwd":os.getcwd()})+"\\n")\n'
            'if "-c" in sys.argv: raise SystemExit(int(os.environ.get("KRYN_STUB_OLD","0")))\n')
        self.stub.chmod(0o755)
        self.record = self.root / 'calls.jsonl'
        self.cwd = self.root / 'caller project'
        self.cwd.mkdir()
        self.env = {**os.environ, 'PATH':str(self.bin)+os.pathsep+'/usr/bin:/bin',
                    'KRYN_STUB_RECORD':str(self.record), 'KRYN_PYTHON':str(self.stub)}

    def tearDown(self): self.tmp.cleanup()

    def invoke(self, args=(), env=None):
        return subprocess.run(['/bin/sh', str(self.kit/'bootstrap'), *args], cwd=self.cwd,
                              env=env or self.env, text=True, capture_output=True, timeout=10)

    def calls(self):
        return [json.loads(line) for line in self.record.read_text().splitlines()] if self.record.exists() else []

    def test_default_read_only_and_exact_profile_from_unrelated_cwd(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[-1]['argv'], ['-E','-B',str(self.kit/'tools/localai.py'),'init','--profile',
                                          str(self.kit/'setup/accepted-profile.json')])
        self.assertEqual(calls[-1]['cwd'], str(self.cwd))
        self.assertNotIn('--apply', calls[-1]['argv'])

    def test_explicit_apply_and_dependency_paths_preserved(self):
        args = ['--apply','--node','/a path/node','--uv=/another path/uv']
        self.assertEqual(self.invoke(args).returncode, 0)
        self.assertEqual(self.calls()[-1]['argv'][-len(args):], args)

    def test_portable_discovery_prefers_python313(self):
        env = dict(self.env)
        env.pop('KRYN_PYTHON')
        self.assertEqual(self.invoke(env=env).returncode, 0)
        self.assertEqual(len(self.calls()), 2)

    def test_old_explicit_python_refused_without_installer(self):
        result = self.invoke(env={**self.env,'KRYN_STUB_OLD':'1'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Python 3.13+', result.stderr)
        self.assertEqual(len(self.calls()), 1)
        self.assertIn('-c', self.calls()[0]['argv'])

    def test_profile_override_and_missing_value_refused_before_python(self):
        for args in (['--profile','/other.json'], ['--profile=/other.json'], ['--node'], ['--deep']):
            with self.subTest(args=args):
                self.assertNotEqual(self.invoke(args).returncode, 0)
                self.assertEqual(self.calls(), [])

    def test_actual_source_deploy_dry_apply_rerun_fake_account(self):
        home = self.root / 'fake account'
        root = home / 'Library/Application Support/LocalAI'
        profile = setup.load_profile(SOURCE/'setup/accepted-profile.json')
        self.assertEqual(profile['repository'], 'gcoli/Qwen3.8-27B-oQ5e-mtp')
        setup.write_same(root/'install-profile.json', setup.encode(profile))
        setup.write_same(root/'xdg/config/opencode/opencode.json', setup.encode(setup.render(root, home/'node', profile)))
        marker = root/profile['model_parent']/setup.model_id(profile)/'.localai-download.json'
        setup.write_same(marker, setup.encode({k:profile[k] for k in ('repository','revision')}))
        protected = {str(p.relative_to(home)):p.read_bytes() for p in home.rglob('*') if p.is_file()}
        with patch.object(Path,'home',return_value=home), patch.object(sys,'argv',['deploy']), redirect_stdout(io.StringIO()) as output:
            deploy_client.main()
        dry = json.loads(output.getvalue())
        self.assertTrue(dry['read_only'])
        self.assertEqual(protected,{str(p.relative_to(home)):p.read_bytes() for p in home.rglob('*') if p.is_file()})
        for _ in range(2):
            with patch.object(Path,'home',return_value=home), patch.object(sys,'argv',['deploy','--apply']), redirect_stdout(io.StringIO()):
                deploy_client.main()
        manifest = json.loads((root/'client/deployment.json').read_text())
        for name,digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((Path(manifest['directory'])/name).read_bytes()).hexdigest(),digest)
        self.assertEqual((home/'.local/bin/kryn').read_text(),manifest['launcher'])
        self.assertEqual((home/'.local/bin/localai').read_text(),manifest['launcher'])
        # Execute the generated shell entry point, but only its pure self-check.
        checked = subprocess.run(['/bin/sh', str(home/'.local/bin/kryn'), '--self-check'],
                                 cwd=self.cwd, env={**os.environ, 'HOME':str(home)},
                                 capture_output=True, text=True, timeout=10)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn('Offline self-check passed', checked.stdout)
        for relative,data in protected.items(): self.assertEqual((home/relative).read_bytes(),data)
        changed = home/'.local/bin/kryn'
        changed.write_bytes(b'user-owned changed launcher')
        before = (changed.read_bytes(),changed.stat().st_mtime_ns)
        for flags in ([],['--apply']):
            with patch.object(Path,'home',return_value=home), patch.object(sys,'argv',['deploy',*flags]), self.assertRaisesRegex(RuntimeError,'Preserving unowned'):
                deploy_client.main()
            self.assertEqual((changed.read_bytes(),changed.stat().st_mtime_ns),before)


if __name__ == '__main__': unittest.main()
