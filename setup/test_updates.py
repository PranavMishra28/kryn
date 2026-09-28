"""Public release discovery without installation, live network or owner state."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kryn import cli, updates

ROOT = Path(__file__).resolve().parents[1]
CURRENT = {'version': '0.1.10', 'source_revision': 'a' * 40}


def release(tag='v0.1.11', **kwargs):
    return {'tag_name': tag, 'draft': False, 'prerelease': True, 'published_at': '2026-09-28T00:00:00Z',
            'body': 'Fixes startup and preserves saved sessions.',
            'assets': [{'name': name, 'state': 'uploaded'} for name in
                       ('SHA256SUMS', 'install-kryn.py', f'kryn-{tag[1:]}-py3-none-any.whl')], **kwargs}


def wheel_bytes(tag='v0.1.11', **overrides):
    import io
    data = io.BytesIO()
    content = b'# Never executed\n'
    manifest = {'schema': 1, 'version': tag[1:], 'source_revision': 'b' * 40, 'source_dirty': False,
                'files': {'install-kryn.py': hashlib.sha256(content).hexdigest()}, **overrides}
    with zipfile.ZipFile(data, 'w') as bundle:
        bundle.writestr('kryn/manifest.json', json.dumps(manifest))
        bundle.writestr('kryn/payload/install-kryn.py', content)
        for name in ('cli.py', 'installer.py', '__init__.py'):
            bundle.writestr('kryn/' + name, content)
    return data.getvalue()


class UpdateChecks(unittest.TestCase):
    def check(self, releases, wheel=None, corrupt=False, current=CURRENT):
        # Exercise the actual updater's SHA256SUMS parser and wheel hash check.
        wheel = wheel if wheel is not None else wheel_bytes()
        calls = []
        class Response:
            def __init__(self, data):
                import io
                self.stream = io.BytesIO(data)
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size): return self.stream.read(size)
        class Opener:
            def open(self, request, timeout):
                url = request.full_url
                calls.append(url)
                if url == updates.RELEASES:
                    return Response(json.dumps(releases).encode())
                if url.endswith('/SHA256SUMS'):
                    digest = '0' * 64 if corrupt else hashlib.sha256(wheel).hexdigest()
                    tag = url.split('/')[-2]
                    return Response(f'{digest}  kryn-{tag[1:]}-py3-none-any.whl\n{"c" * 64}  install-kryn.py\n'.encode())
                if url.endswith('.whl'): return Response(wheel)
                raise AssertionError(url)
        with patch.object(updates, 'payload', return_value=ROOT), \
             patch('urllib.request.build_opener', return_value=Opener()):
            result = updates.check_update(current)
        return result, calls

    def test_new_release_verified_by_existing_downloader_and_manifest(self):
        wheel = wheel_bytes()
        result, calls = self.check([release()], wheel=wheel)
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['tag'], 'v0.1.11')
        self.assertEqual(result['source_revision'], 'b' * 40)
        self.assertEqual(result['sha256'], hashlib.sha256(wheel).hexdigest())
        self.assertEqual(result['installed_revision'], CURRENT['source_revision'])
        self.assertEqual(len(calls), 3)

    def test_same_version_private_commit_and_older_release_do_not_download(self):
        for releases in ([release('v0.1.10')], [release('v0.1.9')], [],
                         [release('v0.1.11', draft=True)], [release('main')],
                         [release('v0.1.11', published_at=None)]):
            with self.subTest(releases=releases):
                result, calls = self.check(releases)
                self.assertEqual(result['status'], 'current')
                self.assertEqual(calls, [updates.RELEASES])

    def test_numeric_order_not_release_date_or_lexicographic_order(self):
        result, _ = self.check([release('v0.1.9'), release('v0.1.11'), release('v0.1.10')])
        self.assertEqual(result['tag'], 'v0.1.11')
        self.assertGreater(updates.version('v0.2.0'), updates.version('v0.1.999'))

    def test_incomplete_corrupt_dirty_or_mismatched_release_is_unknown(self):
        for kwargs in ({'releases': [release(assets=[])]}, {'corrupt': True},
                       {'wheel': wheel_bytes(source_dirty=True)}, {'wheel': wheel_bytes(version='0.1.12')},
                       {'wheel': wheel_bytes(source_revision='main')}, {'wheel': b'not a zip'},
                       {'wheel': wheel_bytes(files={'install-kryn.py': '0' * 64})}):
            with self.subTest(kwargs=kwargs):
                result, _ = self.check(**({'releases': [release()]} | kwargs))
                self.assertEqual(result['status'], 'unavailable')
                self.assertNotIn('tag', result)

    def test_network_failure_is_not_up_to_date(self):
        with patch.object(updates, 'payload', return_value=ROOT), \
             patch('urllib.request.build_opener', side_effect=OSError('network down')):
            self.assertEqual(updates.check_update(CURRENT)['status'], 'unavailable')

    def test_release_notes_are_bounded_and_terminal_controls_removed(self):
        result, _ = self.check([release(body='Fix\x1b\x00\u202e\n' + 'x' * 1000)])
        self.assertLessEqual(len(result['summary']), 241)
        for value in ('\x1b', '\x00', '\u202e', '\n'):
            self.assertNotIn(value, result['summary'])

    def test_unsafe_wheel_entries_are_never_extracted(self):
        with tempfile.TemporaryDirectory() as directory:
            wheel = Path(directory) / 'unsafe.whl'
            for name in ('../escape', '/absolute', 'unrelated/data'):
                with zipfile.ZipFile(wheel, 'w') as bundle: bundle.writestr(name, 'bad')
                with self.assertRaises(ValueError): updates.release_manifest(wheel, 'v0.1.11')
            self.assertEqual(list(Path(directory).iterdir()), [wheel])

    def test_cli_check_verifies_current_payload_and_never_installs(self):
        with patch.object(sys, 'argv', ['kryn', 'update', '--check']), \
             patch.object(cli, 'verify_payload', return_value=CURRENT) as verify, \
             patch.object(updates, 'check_update', return_value={'status': 'current'}) as check, \
             patch.object(cli.subprocess, 'run') as run, patch('builtins.print') as output:
            cli.main()
            verify.assert_called_once()
            check.assert_called_once_with(CURRENT)
            run.assert_not_called()
            self.assertEqual(json.loads(output.call_args.args[0]), {'status': 'current'})

    def test_cli_forwards_exact_offered_wheel_digest_to_installer(self):
        digest = 'a' * 64
        with patch.object(sys, 'argv', ['kryn', 'update', 'v0.1.11', '--expected-wheel-sha256', digest]), \
             patch.object(cli, 'verify_payload'), patch.object(cli.subprocess, 'run') as run:
            cli.main()
            self.assertEqual(run.call_args.args[0][-4:], ['--tag', 'v0.1.11', '--expected-wheel-sha256', digest])


if __name__ == '__main__': unittest.main()
