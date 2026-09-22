"""Read-only, content-free evidence from the pinned native session database.

Counts are diagnostic signals, never proof that an application's requirements pass.
No prompt, tool output, source, credential or command is included in the report.
"""
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3


def summarize(connection, session_id):
    pending, ids, sessions = [session_id], set(), []
    tools, reads, finishes = Counter(), Counter(), Counter()
    counts = Counter()
    usage = {kind: Counter() for kind in ('assistant', 'compaction')}
    limited = False
    for _ in range(64):
        if not pending:
            break
        sid = pending.pop(0)
        if sid in ids:
            raise ValueError('Cycle in native session hierarchy')
        ids.add(sid)
        row = connection.execute('SELECT parent_id, directory, idle_outcome, time_created, time_updated '
                                 'FROM session_v2 WHERE id=?', (sid,)).fetchone()
        if row is None:
            raise ValueError('Native session no longer exists')
        if sessions and row[1] != sessions[0][1]:
            raise ValueError('Child session belongs to another project')
        sessions.append(row)
        pending.extend(r[0] for r in connection.execute('SELECT id FROM session_v2 WHERE parent_id=? ORDER BY id LIMIT 65', (sid,)))
        # SQL extracts only bounded fields. Image payloads and tool output are not loaded.
        rows = connection.execute("""SELECT type,
          json_extract(data,'$.status'), json_extract(data,'$.finish'),
          json_extract(data,'$.tokens.output'),
          json_extract(data,'$.time.created'), json_extract(data,'$.time.completed'),
          json_extract(data,'$.tokens.input'), json_extract(data,'$.tokens.cache.read'),
          json_extract(data,'$.tokens.cache.write'), json_extract(data,'$.tokens.reasoning')
          FROM session_message WHERE session_id=? ORDER BY seq LIMIT 10001""", (sid,)).fetchall()
        if len(rows) > 10000:
            limited = True
        for kind, status, finish, output, created, completed, uncached, cached, written, reasoning in rows[:10000]:
            counts[kind + '_messages'] += 1
            if kind in usage:
                bucket = usage[kind]
                values = (uncached, cached, written, output, reasoning)
                # Native 2.0.10 stores mutually exclusive input/cache fields and
                # separate reported output/reasoning. Missing usage is not zero.
                if all(type(value) is int and value >= 0 for value in values) and any(values):
                    bucket['records_with_usage'] += 1
                    for key, value in zip(('uncached_input_tokens', 'cache_read_tokens',
                                           'cache_write_tokens', 'output_tokens', 'reasoning_tokens'), values):
                        bucket[key] += value
                    prompt = uncached + cached + written
                    bucket['prompt_tokens'] += prompt
                    bucket['max_recorded_prompt_tokens'] = max(bucket['max_recorded_prompt_tokens'], prompt)
                else:
                    bucket['records_without_usable_usage'] += 1
            if kind == 'assistant':
                finishes[finish or 'unknown'] += 1
                counts['output_tokens'] += output if type(output) is int and output >= 0 else 0
                if created and completed:
                    counts['assistant_wall_ms'] += max(0, completed - created)
            if kind == 'compaction' and status == 'completed':
                counts['completed_compactions'] += 1
        calls = connection.execute("""SELECT
          json_extract(p.value,'$.name'), json_extract(p.value,'$.state.status'),
          substr(json_extract(p.value,'$.state.input.path'),1,4096),
          substr(json_extract(p.value,'$.state.input.command'),1,4096),
          json_extract(p.value,'$.state.metadata.exit'),
          json_extract(p.value,'$.state.metadata.output.exit')
          FROM session_message m, json_each(m.data,'$.content') p
          WHERE m.session_id=? AND m.type='assistant' AND json_extract(p.value,'$.type')='tool'
          ORDER BY m.seq LIMIT 20001""", (sid,)).fetchall()
        if len(calls) > 20000:
            limited = True
        for name, status, path, command, exit_code, nested_exit in calls[:20000]:
            tools[name or 'unknown'] += 1
            counts['tool_errors'] += status == 'error'
            if name == 'read' and path:
                reads[(sid, path)] += 1
            if name and name.startswith('browser_') and status == 'completed':
                counts['completed_browser_calls'] += 1
            if name == 'shell' and command:
                code = exit_code if exit_code is not None else nested_exit
                counts['shell_nonzero_exits'] += isinstance(code, int) and code != 0
                if re.search(r'\b(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:test|build|lint|typecheck)\b|\b(?:pytest|unittest)\b|\bnode\s+[^\s;&|]*test[^\s;&|]*', command):
                    counts['check_commands'] += 1
                    counts['check_exit_zero'] += code == 0 and status == 'completed'
                    counts['check_exit_unknown'] += code is None
    limited = limited or bool(pending)
    repeated = max(reads.values(), default=0)
    findings = []
    if repeated >= 3 and counts['completed_compactions'] >= 2:
        findings.append('Repeated reads across compaction; inspect for a review loop.')
    if not counts['completed_browser_calls']:
        findings.append('No completed browser tool calls. UI success is not established by this trace.')
    if counts['tool_errors']:
        findings.append('Tool errors occurred; inspect the native transcript before classifying their cause.')
    if limited:
        findings.append('Report bounds reached; counts are partial.')
    token_usage = {}
    for kind, bucket in usage.items():
        token_usage[kind] = dict(bucket)
        token_usage[kind]['cache_read_fraction'] = (round(bucket['cache_read_tokens'] / bucket['prompt_tokens'], 4)
                                                  if bucket['prompt_tokens'] else None)
    return {'schema': 1, 'session_id': session_id, 'session_count': len(ids),
            'native_outcome': sessions[0][2], 'counts': dict(counts), 'tools': dict(tools),
            'token_usage': token_usage,
            'usage_note': 'Provider-reported usage summed across requests, not unique conversation tokens. '
                          'max_recorded_prompt_tokens is one native record, not the configured context limit. '
                          'Compaction records can aggregate multiple summary attempts. Native missing usage may be normalized to zero; all-zero or incomplete usage is unmeasured. '
                          'Zero reasoning can also mean the provider omitted its breakdown; output may then include reasoning. Cache reuse is not correctness proof.',
            'maximum_reads_of_one_path_per_session': repeated, 'finishes': dict(finishes),
            'partial': limited, 'findings': findings, 'acceptance_verified': False,
            'note': 'Native completion, command exits and model-written reports do not prove task acceptance. '
                    'Compare the actual application with independent checks; copied test logic is insufficient.'}


def report(database, project, session_id=None):
    database, project = Path(database).resolve(), str(Path(project).resolve())
    if not database.is_file():
        raise ValueError('No native session database found')
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=2)) as connection:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')  # One consistent snapshot while the TUI is running.
        ticks = 0
        def bound():
            nonlocal ticks
            ticks += 1
            return ticks > 10000
        connection.set_progress_handler(bound, 10000)
        if session_id is not None:
            if not re.fullmatch(r'ses_[A-Za-z0-9]+', session_id):
                raise ValueError('Invalid native session ID')
            row = connection.execute('SELECT id FROM session_v2 WHERE id=? AND directory=?', (session_id, project)).fetchone()
        else:
            row = connection.execute('SELECT id FROM session_v2 WHERE directory=? AND parent_id IS NULL '
                                     'ORDER BY time_updated DESC LIMIT 1', (project,)).fetchone()
        if row is None:
            raise ValueError('No matching session in this project')
        return summarize(connection, row[0])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=Path.home() / 'Library/Application Support/LocalAI/xdg/data/opencode/opencode.db')
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--session')
    args = parser.parse_args()
    print(json.dumps(report(args.database, args.project, args.session), indent=2))
