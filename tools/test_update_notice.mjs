import assert from 'node:assert/strict';
import { test } from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { setupUpdates, verifiedNotice, CHECK_INTERVAL } from './update_notice.mjs';

const available = { status: 'available', tag: 'v0.1.11', source_revision: 'b'.repeat(40),
  sha256: 'c'.repeat(64), summary: 'Fix startup. Preserve sessions.', prerelease: true };

function fixture(t, options = {}) {
  const state = options.state ?? { checked: 0, notified: '' };
  const notices = [], confirms = [], alerts = [];
  let time = 100000000, busy = options.busy ?? false, checks = 0, confirm = false;
  const context = {
    storage: { store: () => [state, async fn => fn(state)] },
    data: { session: { list: () => [{ id: 'session' }, { id: 'child' }], status: id => busy && id === 'child' ? 'running' : 'idle' } },
    ui: { toast: { show: value => notices.push(value) }, dialog: {
      confirm: async value => { confirms.push(value); return confirm; },
      alert: async value => alerts.push(value),
    } },
  };
  const updates = setupUpdates(context, { now: () => time, ...(options.native ? {} : {
    check: async signal => { checks++; return options.check ? options.check(signal) : available; },
  }) });
  t.after(() => updates.dispose());
  return { state, notices, confirms, alerts, updates, get checks() { return checks; },
    busy(value) { busy = value; }, advance(value) { time += value; }, confirm(value) { confirm = value; } };
}

test('startup and idle checks are throttled, including across restarts', async t => {
  const f = fixture(t);
  await f.updates.poll();
  assert.equal(f.checks, 1);
  assert.equal(f.notices.length, 1);
  assert.match(f.notices[0].message, /v0.1.11 prerelease/);
  await f.updates.poll();
  f.advance(CHECK_INTERVAL);
  await f.updates.poll();
  assert.equal(f.checks, 2);
  assert.equal(f.notices.length, 1);
  f.updates.dispose();
  const restarted = fixture(t, { state: f.state });
  await restarted.updates.poll();
  assert.equal(restarted.notices.length, 0);
});

test('busy child defers startup and results arriving during work wait for idle', async t => {
  let resolve;
  const f = fixture(t, { busy: true, check: () => new Promise(done => { resolve = done; }) });
  await f.updates.poll();
  assert.equal(f.checks, 0);
  f.busy(false);
  const polling = f.updates.poll();
  await new Promise(setImmediate);
  f.busy(true);
  resolve(available);
  await polling;
  assert.equal(f.notices.length, 0);
  assert.equal(f.state.notified, '');
  f.busy(false);
  await f.updates.poll();
  assert.equal(f.notices.length, 1);
});

test('a release published during the session appears at a later idle check', async t => {
  let latest = { status: 'current' };
  const f = fixture(t, { check: () => latest });
  await f.updates.poll();
  assert.equal(f.notices.length, 0);
  f.advance(CHECK_INTERVAL);
  latest = available;
  await f.updates.poll();
  assert.equal(f.notices.length, 1);
});

test('Later is persistent, and Update instructions only shows the exact manual command', async t => {
  const f = fixture(t);
  await f.updates.poll();
  await f.updates.open();
  assert.deepEqual(f.confirms[0].label, { confirm: 'Update instructions', cancel: 'Later' });
  assert.match(f.confirms[0].message, new RegExp(available.source_revision));
  assert.equal(f.alerts.length, 0);
  f.advance(CHECK_INTERVAL);
  await f.updates.poll();
  assert.equal(f.notices.length, 1);
  f.confirm(true);
  await f.updates.open();
  assert.match(f.alerts[0].message, /kryn update v0\.1\.11/);
  assert.match(f.alerts[0].message, /exit KRYN/);
  assert.match(f.alerts[0].message, /kryn rollback/);
});

test('network failure and invalid responses stay quiet and cannot claim current', async t => {
  const f = fixture(t, { check: () => { throw new Error('offline'); } });
  await f.updates.poll();
  await f.updates.open();
  await f.updates.open();
  assert.equal(f.checks, 1);
  assert.equal(f.notices.length, 0);
  assert.match(f.alerts[0].message, /Could not verify/);
  assert.equal(f.confirms.length, 0);
  for (const invalid of [{ status: 'current' }, { ...available, tag: 'main' },
    { ...available, tag: 'v0.1.11; curl example' }, { ...available, source_revision: 'main' },
    { ...available, sha256: '' }, { ...available, summary: '\x1b[2J' }]) assert.equal(verifiedNotice(invalid), false);
});

test('manual checks do not open dialogs during active work', async t => {
  const f = fixture(t, { busy: true });
  await f.updates.open();
  assert.equal(f.checks, 0);
  assert.equal(f.confirms.length, 0);
  assert.match(f.notices[0].message, /Finish the active turn/);
});

test('dispose aborts a pending check and suppresses late UI', async t => {
  let resolve, signal;
  const f = fixture(t, { check: value => { signal = value; return new Promise(done => { resolve = done; }); } });
  const polling = f.updates.poll();
  await new Promise(setImmediate);
  f.updates.dispose();
  assert.equal(signal.aborted, true);
  resolve(available);
  await polling;
  assert.equal(f.notices.length, 0);
});

test('real subprocess boundary invokes only isolated package discovery, with spaces preserved', async t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'kryn notice '));
  const python = path.join(directory, 'package python');
  const record = path.join(directory, 'args');
  fs.writeFileSync(python, `#!/bin/sh\nprintf '%s\\n' "$@" > '${record}'\nprintf '%s\\n' '${JSON.stringify(available)}'\n`, { mode: 0o700 });
  const before = process.env.KRYN_UPDATE_PYTHON;
  process.env.KRYN_UPDATE_PYTHON = python;
  t.after(() => {
    if (before === undefined) delete process.env.KRYN_UPDATE_PYTHON;
    else process.env.KRYN_UPDATE_PYTHON = before;
    fs.rmSync(directory, { recursive: true, force: true });
  });
  const f = fixture(t, { native: true });
  await f.updates.poll();
  assert.deepEqual(fs.readFileSync(record, 'utf8').trim().split('\n'), ['-I', '-B', '-m', 'kryn', 'update', '--check']);
  assert.equal(f.notices.length, 1);
});
