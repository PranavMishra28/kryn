"""Native trace diagnostics must stay private and must not fabricate acceptance."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from session_report import report


class ReportTests(unittest.TestCase):
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
                        {'type': 'tool', 'name': 'browser_browser_click', 'state': {'status': 'error'}}]
            c.execute('INSERT INTO session_message VALUES (?,?,?,?)', ('ses_child', 1, 'assistant', json.dumps({'content': content, 'finish': 'stop'})))
            for seq in (2, 3):
                c.execute('INSERT INTO session_message VALUES (?,?,?,?)', ('ses_child', seq, 'compaction', '{"status":"completed","summary":"PRIVATE PROMPT"}'))
            c.commit(); c.close()
            before = db.read_bytes()
            result = report(db, project)
            self.assertEqual(result['session_count'], 2)
            self.assertEqual(result['maximum_reads_of_one_path_per_session'], 4)
            self.assertEqual(result['counts']['check_exit_zero'], 0)
            self.assertEqual(result['counts']['shell_nonzero_exits'], 1)
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
