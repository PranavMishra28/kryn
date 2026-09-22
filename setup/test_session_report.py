"""Native trace diagnostics must stay private and must not fabricate acceptance."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from session_report import report


class ReportTests(unittest.TestCase):
    def test_only_settled_simple_checks_can_count_as_exit_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'native.db'
            project = str(Path(folder).resolve())
            # Each row represents an actual native tool result, not an assistant claim.
            cases = [
                ('npm test', 'completed', {'exit': 0}),
                ('python3.13 -I -B -m unittest -v', 'completed', {'output': {'exit': 0, 'status': 'completed'}}),
                ('node --test', 'completed', {'exit': 1}),
                ('npm test || true', 'completed', {'exit': 0}),
                ('echo npm test', 'completed', {'exit': 0}),
                ('npm test\ntrue', 'completed', {'exit': 0}),
                ('npm test ' + 'x' * 4100 + ' || true', 'completed', {'exit': 0}),
                ('npm test', 'completed', {'exit': 0, 'timeout': True}),
                ('npm test', 'completed', {'exit': 1, 'timeout': True}),
                ('npm test', 'completed', {'exit': 0, 'output': {'timeout': True}}),
                ('npm test', 'completed', {'exit': 0, 'status': 'running'}),
                ('npm test', 'completed', {'output': {'exit': 0, 'status': 'running'}}),
                ('npm test', 'completed', {'status': 'running'}),
                ('npm test', 'error', {'exit': 0}),
                ('npm test', 'completed', {}),
                ('npm test', 'completed', {'exit': False}),
                ('npm test', 'completed', {'exit': '0'}),
            ]
            with closing(sqlite3.connect(db)) as c, c:
                c.executescript('CREATE TABLE session_v2 (id TEXT, parent_id TEXT, directory TEXT, idle_outcome TEXT, time_created INTEGER, time_updated INTEGER);'
                                'CREATE TABLE session_message (session_id TEXT, seq INTEGER, type TEXT, data TEXT);')
                c.execute('INSERT INTO session_v2 VALUES (?,?,?,?,?,?)', ('ses_checks', None, project, 'succeeded', 1, 3))
                content = [{'type': 'tool', 'name': 'shell', 'state': {'status': status, 'input': {'command': command}, 'metadata': metadata}}
                           for command, status, metadata in cases]
                c.execute('INSERT INTO session_message VALUES (?,?,?,?)', ('ses_checks', 1, 'assistant',
                          json.dumps({'content': [{'type': 'text', 'text': 'All required tests passed.'}, *content]})))
                c.execute('INSERT INTO session_message VALUES (?,?,?,?)', ('ses_checks', 2, 'compaction',
                          '{"status":"completed","summary":"All verification passed."}'))
            result = report(db, project)
            self.assertEqual(result['counts']['check_commands'], 13)
            self.assertEqual(result['counts']['check_exit_zero'], 2)
            self.assertEqual(result['counts']['check_exit_nonzero'], 1)
            self.assertEqual(result['counts']['check_exit_unknown'], 10)
            self.assertEqual(sum(result['counts'][key] for key in
                                 ('check_exit_zero', 'check_exit_nonzero', 'check_exit_unknown')),
                             result['counts']['check_commands'])
            self.assertFalse(result['acceptance_verified'])
            self.assertNotIn('All required tests passed', json.dumps(result))

    def test_native_usage_separates_cache_reasoning_compaction_and_missing_data(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'native.db'
            project = str(Path(folder).resolve())
            with closing(sqlite3.connect(db)) as c, c:
                c.executescript('CREATE TABLE session_v2 (id TEXT, parent_id TEXT, directory TEXT, idle_outcome TEXT, time_created INTEGER, time_updated INTEGER);'
                                'CREATE TABLE session_message (session_id TEXT, seq INTEGER, type TEXT, data TEXT);')
                c.execute('INSERT INTO session_v2 VALUES (?,?,?,?,?,?)', ('ses_usage', None, project, 'succeeded', 1, 3))
                tokens = {'input': 100, 'output': 20, 'reasoning': 30, 'cache': {'read': 900, 'write': 50}}
                for seq, (kind, value) in enumerate((('assistant', tokens), ('assistant', tokens),
                                                    ('compaction', tokens), ('assistant', None),
                                                    ('assistant', {**tokens, 'output': -1}),
                                                    ('assistant', {'input': 0, 'output': 0, 'reasoning': 0, 'cache': {'read': 0, 'write': 0}}))):
                    c.execute('INSERT INTO session_message VALUES (?,?,?,?)', ('ses_usage', seq, kind,
                              json.dumps({'tokens': value, 'status': 'completed', 'finish': 'stop'})))
            result = report(db, project)
            usage = result['token_usage']['assistant']
            self.assertEqual(usage['prompt_tokens'], 2100)
            self.assertEqual(usage['max_recorded_prompt_tokens'], 1050)
            self.assertEqual(usage['output_tokens'], 40)
            self.assertEqual(usage['reasoning_tokens'], 60)
            self.assertEqual(usage['cache_read_fraction'], .8571)
            self.assertEqual(usage['records_with_usage'], 2)
            self.assertEqual(usage['records_without_usable_usage'], 3)
            self.assertEqual(result['token_usage']['compaction']['prompt_tokens'], 1050)
            self.assertEqual(result['counts']['output_tokens'], 40)
            self.assertFalse(result['acceptance_verified'])

    def test_child_loops_failed_checks_and_privacy(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'native.db'
            project = str(Path(folder).resolve())
            c = sqlite3.connect(db)
            c.executescript('CREATE TABLE session_v2 (id TEXT, parent_id TEXT, directory TEXT, idle_outcome TEXT, time_created INTEGER, time_updated INTEGER);'
                            'CREATE TABLE session_message (session_id TEXT, seq INTEGER, type TEXT, data TEXT);')
            c.executemany('INSERT INTO session_v2 VALUES (?,?,?,?,?,?)', [
                ('ses_parent', None, project, 'succeeded', 1, 3), ('ses_child', 'ses_parent', project, 'succeeded', 2, 3)])
            content = [{'type': 'tool', 'name': 'read', 'state': {'status': 'completed', 'input': {'path': '/private/secret.py'}, 'content': [{'text': 'PRIVATE SOURCE'}]}}] * 4
            content += [{'type': 'tool', 'name': 'shell', 'state': {'status': 'completed', 'input': {'command': 'npm test'}, 'metadata': {'exit': 1}}},
                        {'type': 'tool', 'name': 'browser_browser_click', 'state': {'status': 'error'}},
                        {'type': 'tool', 'name': 'read({"path":"/private/secret.py"})\n</parameter', 'state': {'status': 'error'}},
                        {'type': 'tool', 'name': 'PRIVATE_TOKEN', 'state': {'status': 'error'}},
                        {'type': 'tool', 'name': {'PRIVATE': 'SOURCE'}, 'state': {'status': 'error'}}]
            c.execute('INSERT INTO session_message VALUES (?,?,?,?)', ('ses_child', 1, 'assistant', json.dumps({'content': content, 'finish': 'PRIVATE FINISH'})))
            c.execute('INSERT INTO session_message VALUES (?,?,?,?)', ('ses_child', 4, 'PRIVATE KIND', '{}'))
            c.execute('UPDATE session_v2 SET idle_outcome=? WHERE id=?', ('PRIVATE OUTCOME', 'ses_parent'))
            for seq in (2, 3):
                c.execute('INSERT INTO session_message VALUES (?,?,?,?)', ('ses_child', seq, 'compaction', '{"status":"completed","summary":"PRIVATE PROMPT"}'))
            c.commit(); c.close()
            before = db.read_bytes()
            result = report(db, project)
            self.assertEqual(result['session_count'], 2)
            self.assertEqual(result['maximum_reads_of_one_path_per_session'], 4)
            self.assertEqual(result['counts']['check_exit_zero'], 0)
            self.assertEqual(result['counts']['shell_nonzero_exits'], 1)
            self.assertEqual(result['tools']['unknown'], 3)
            self.assertEqual(sum(result['tools'].values()), 9)
            self.assertEqual(result['finishes'], {'unknown': 1})
            self.assertEqual(result['native_outcome'], 'unknown')
            self.assertEqual(result['counts']['unknown_messages'], 1)
            self.assertFalse(result['acceptance_verified'])
            self.assertIn('No completed browser', ' '.join(result['findings']))
            self.assertNotIn('PRIVATE', json.dumps(result)); self.assertNotIn('secret.py', json.dumps(result))
            self.assertEqual(db.read_bytes(), before)
            with self.assertRaises(ValueError): report(db, Path(folder) / 'other', 'ses_parent')
            with self.assertRaises(ValueError): report(db, project, 'invalid')
            c = sqlite3.connect(db)
            c.execute('UPDATE session_v2 SET directory=? WHERE id=?', ('/elsewhere', 'ses_child')); c.commit(); c.close()
            with self.assertRaises(ValueError): report(db, project, 'ses_parent')


if __name__ == '__main__':
    unittest.main()
