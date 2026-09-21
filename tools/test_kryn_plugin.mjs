import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import plugin, { validatedOptions, assertLocal, isCheck, BROWSER_TOOLS, pruneTrackers } from './kryn_plugin.mjs';
const digest = value => createHash('sha256').update(value).digest('hex');
const tick = () => new Promise(resolve => setImmediate(resolve));
function fixture(extra = {}) {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'kryn-plugin-')));
  fs.chmodSync(root, 0o700);
  const hooks = new Map(), pending = [], wake = [], continuations = [];
  let stopped = false, serial = 0;
  const location = { directory: root, project: { canonical: root } };
  const options = { stateDir: root, profileId: 'test-profile', modelID: 'test-Q4', workflowScope: 'disposable_json_cli',
    champion: { revision: digest('Inspect evidence before editing.'), instructions: 'Inspect evidence before editing.' }, ...extra };
  const domain = prefix => ({ hook: async (name, callback) => hooks.set(prefix + '.' + name, callback) });
  const ctx = { location, options, session: domain('session'), tool: domain('tool'), permission: domain('permission'),
    event: { async *subscribe({ signal }) {
      stopped = false;
      signal.addEventListener('abort', () => { stopped = true; wake.splice(0).forEach(f => f()); });
      while (!stopped) {
        if (!pending.length) await new Promise(resolve => wake.push(resolve));
        while (pending.length) yield pending.shift();
      }
    } } };
  ctx.session.get = async ({ sessionID }) => ({ id: sessionID, location, agent: 'build',
    model: { providerID: 'local', id: 'qwen' }, outcome: 'succeeded', time: {} });
  ctx.session.synthetic = async value => { continuations.push(value); };
  return { root, ctx, hooks,
    continuations,
    call: (name, data) => hooks.get(name)(data),
    emit: async (type, data = {}, loc = location) => {
      pending.push({ id: 'evt_' + (++serial), type, data: { sessionID: 'ses_1', ...data }, location: loc });
      wake.splice(0).forEach(f => f()); await tick();
    },
    read: name => {
      const folder = path.join(root, 'learning', name);
      return fs.readdirSync(folder).map(file => JSON.parse(fs.readFileSync(path.join(folder, file), 'utf8')));
    },
    remove: () => fs.rmSync(root, { recursive: true, force: true }) };
}
const model = { providerID: 'local', id: 'qwen' };

test('strict loopback/model guards apply independently of request kind and hot-reloaded refs', async () => {
  const f = fixture(); const cleanup = await plugin.setup(f.ctx);
  try {
    const options = validatedOptions(f.ctx.options);
    for (const kind of ['primary', 'title', 'compaction', 'generate']) {
      f.call('session.model.request', { model, kind, baseURL: options.baseURL });
      assert.throws(() => f.call('session.model.request', { model, kind, baseURL: 'https://example.com/v1' }));
    }
    assert.throws(() => assertLocal({ model: { providerID: 'cloud', id: 'qwen' }, baseURL: options.baseURL }, options));
    await f.call('session.http.request', { model, request: new Request(options.baseURL + '/chat/completions',
      { method: 'POST', body: JSON.stringify({ model: 'test-Q4' }) }) });
    await assert.rejects(() => f.call('session.http.request', { model, request: new Request(options.baseURL + '/chat/completions',
      { method: 'POST', body: JSON.stringify({ model: 'wrong' }) }) }));
    assert.throws(() => f.call('session.experimental.ws.handshake', {}));
    for (const url of ['http://localhost:8000/v1', 'http://127.0.0.1/v1', 'http://127.0.0.1:8000/v1?secret=x', 'http://user@127.0.0.1:8000/v1'])
      assert.throws(() => validatedOptions({ ...f.ctx.options, inferenceBaseURL: url }));
    assert.equal(validatedOptions({ ...f.ctx.options, inferenceBaseURL: 'http://127.0.0.1:23456/v1' }).origin, 'http://127.0.0.1:23456');
  } finally { await cleanup(); f.remove(); }
});

test('auxiliary budgets reserve output for coding and preserve cancellation and private headers', async () => {
  const f = fixture(); const cleanup = await plugin.setup(f.ctx);
  try {
    for (const kind of ['primary', 'compaction', 'generate', 'title']) {
      const controller = new AbortController();
      const body = { model: 'test-Q4', max_tokens: 4096, stream: true,
        messages: [{ role: 'user', content: 'Private task context' }], chat_template_kwargs: { enable_thinking: false } };
      const request = new Request('http://127.0.0.1:8000/v1/chat/completions', { method: 'POST',
        headers: { 'content-type': 'application/json', 'content-length': String(JSON.stringify(body).length),
          authorization: 'Bearer synthetic-test-only', 'x-session-affinity': 'ses_1' },
        body: JSON.stringify(body), signal: controller.signal });
      const event = { model, kind, request };
      await f.call('session.http.request', event);
      const expected = { ...body, max_tokens: kind === 'title' ? 128 : kind === 'compaction' ? 2048 : 4096 };
      if (kind === 'compaction') expected.temperature = 0.2;
      assert.deepEqual(await event.request.clone().json(), expected);
      assert.equal(event.request.method, 'POST'); assert.equal(event.request.url, request.url);
      assert.equal(event.request.headers.get('authorization'), 'Bearer synthetic-test-only');
      assert.equal(event.request.headers.get('x-session-affinity'), 'ses_1');
      if (kind === 'title' || kind === 'compaction') assert.equal(event.request.headers.has('content-length'), false);
      else assert.equal(event.request, request);
      controller.abort(); assert.equal(event.request.signal.aborted, true);
    }
    for (const cap of [64, undefined]) {
      const event = { model, kind: 'title', request: new Request('http://127.0.0.1:8000/v1/chat/completions',
        { method: 'POST', body: JSON.stringify({ model: 'test-Q4', max_tokens: cap }) }) };
      await f.call('session.http.request', event);
      assert.equal((await event.request.json()).max_tokens, cap ?? 128);
    }
  } finally { await cleanup(); f.remove(); }
});

test('truncated top-level Build output gets two bounded native continuations, never replayed tool execution', async () => {
  const f = fixture(); const cleanup = await plugin.setup(f.ctx);
  try {
    f.call('session.prompt', { sessionID: 'ses_1' });
    for (let n = 0; n < 3; n++) await f.emit('session.step.ended', { finish: 'length', tokens: { output: 8192 } });
    assert.deepEqual(f.continuations.map(v => v.resume), [true, true]);
    assert.ok(f.continuations[0].text.includes('do not assume the unfinished tool call executed'));
    assert.equal(f.continuations[0].delivery, 'steer');
    assert.ok(f.continuations.every(v => !Object.hasOwn(v, 'tools') && !Object.hasOwn(v, 'permissions')));
    await f.emit('session.execution.succeeded');
    assert.equal(f.read('trackers')[0].state, 'incomplete');
    await f.emit('session.step.ended', { finish: 'stop' });
    await f.emit('session.execution.succeeded');
    assert.equal(f.read('trackers')[0].state, 'unknown');
    assert.equal(f.continuations.length, 2);
    f.call('session.prompt', { sessionID: 'ses_1' });
    await f.emit('session.step.ended', { finish: 'length' });
    assert.equal(f.continuations.at(-1).resume, true);
  } finally { await cleanup(); f.remove(); }
});

test('output recovery respects interruption, user steering, read-only roles and child ownership', async () => {
  for (const changed of [{ parentID: 'ses_parent' }, { agent: 'audit' }, { agent: 'reviewer' },
    { outcome: 'interrupted', time: { idle: new Date(Date.now() + 1000).toISOString() } },
    { location: { directory: '/other' } }, { revert: {} }]) {
    const f = fixture(); const cleanup = await plugin.setup(f.ctx);
    const original = f.ctx.session.get;
    f.ctx.session.get = async args => ({ ...await original(args), ...changed });
    try {
      await f.emit('session.step.ended', { finish: 'length' });
      assert.equal(f.continuations.length, 0);
    } finally { await cleanup(); f.remove(); }
  }
  const f = fixture(); const cleanup = await plugin.setup(f.ctx);
  const original = f.ctx.session.get;
  f.ctx.session.get = async args => {
    f.call('session.prompt', { sessionID: 'ses_1' });
    return original(args);
  };
  try {
    await f.emit('session.step.ended', { finish: 'length' });
    assert.equal(f.continuations.length, 0);
    await f.emit('session.execution.interrupted');
    await f.emit('session.step.ended', { finish: 'length' });
    assert.equal(f.continuations.length, 0);
  } finally { await cleanup(); f.remove(); }
});

test('write budget uses UTF-8 bytes and leaves small edits available', async () => {
  const f = fixture(); const cleanup = await plugin.setup(f.ctx);
  try {
    assert.doesNotThrow(() => f.call('tool.execute.before', { agent: 'build', tool: 'write', input: { content: 'a'.repeat(12000) } }));
    assert.throws(() => f.call('tool.execute.before', { agent: 'build', tool: 'write', input: { content: '🐴'.repeat(3001) } }), /12,000/);
    assert.doesNotThrow(() => f.call('tool.execute.before', { agent: 'build', tool: 'edit', input: { newString: 'small correction' } }));
    assert.throws(() => f.call('tool.execute.before', { agent: 'build', tool: 'write', input: { path: f.root.slice(1) + '/index.html', content: 'test' } }), /leading/);
    for (const target of ['./index.html', f.root + '/index.html'])
      assert.doesNotThrow(() => f.call('tool.execute.before', { agent: 'build', tool: 'write', input: { path: target, content: 'test' } }));
  } finally { await cleanup(); f.remove(); }
});

test('read-only guards reject every unlisted mutation route without autoapproval; native child is bounded', async () => {
  const f = fixture(); const cleanup = await plugin.setup(f.ctx);
  try {
    for (const agent of ['reviewer', 'explore', 'audit']) {
      for (const tool of ['write', 'edit', 'patch', 'shell', 'execute', 'subagent', 'pty', 'formatter', 'lsp_apply_edit', 'browser_browser_click', 'remote_mutate']) {
        assert.throws(() => f.call('tool.execute.before', { agent, tool }));
        const event = { agent, action: tool, effect: 'allow' };
        f.call('permission.evaluate', event); assert.equal(event.effect, 'deny');
      }
      f.call('tool.execute.before', { agent, tool: 'read' });
    }
    const event = { agent: 'reviewer', action: 'read', effect: 'ask' };
    f.call('permission.evaluate', event); assert.equal(event.effect, 'ask');
    const child = { agent: 'build', tool: 'subagent', sessionID: 'ses_1', id: 'call_1', input: { agent: 'explore', background: true } };
    f.call('tool.execute.before', child); assert.equal(child.input.background, false);
    assert.throws(() => f.call('tool.execute.before', { ...child, id: 'call_2' }));
    f.call('tool.execute.after', { ...child, messageID: 'msg_1', status: 'error' });
    f.call('tool.execute.before', { ...child, id: 'call_3' });
  } finally { await cleanup(); f.remove(); }
});

test('Audit parent stays read-only after one fresh foreground Reviewer and ordinary Build remains available', async () => {
  const f = fixture(); const cleanup = await plugin.setup(f.ctx);
  try {
    await f.emit('session.execution.started');
    const call = { agent: 'audit', tool: 'subagent', sessionID: 'ses_1', id: 'audit_child',
      messageID: 'msg_1', input: { agent: 'reviewer', prompt: 'Review the supplied evidence.', background: false } };
    for (const input of [
      { agent: 'build' }, { agent: 'reviewer', sessionID: 'ses_old' },
      { agent: 'reviewer', sessionID: null }, { agent: 'reviewer', background: true },
      { agent: 'reviewer', model: 'local/qwen#fast' },
    ]) assert.throws(() => f.call('tool.execute.before', { ...call, input }));
    for (const resources of [[], ['build'], ['reviewer', 'build']]) {
      const permission = { agent: 'audit', action: 'subagent', resources, effect: 'allow' };
      f.call('permission.evaluate', permission); assert.equal(permission.effect, 'deny');
    }
    const permission = { agent: 'audit', action: 'subagent', resources: ['reviewer'], effect: 'allow' };
    f.call('permission.evaluate', permission); assert.equal(permission.effect, 'allow');
    f.call('tool.execute.before', call);
    f.call('tool.execute.after', { ...call, status: 'completed' });
    assert.throws(() => f.call('tool.execute.before', { ...call, id: 'second_child' }));
    for (const tool of ['edit', 'write', 'patch', 'shell', 'execute', 'browser_browser_click', 'unknown_mutation']) {
      assert.throws(() => f.call('tool.execute.before', { agent: 'audit', tool }));
      const mutation = { agent: 'audit', action: tool, resources: ['*'], effect: 'allow' };
      f.call('permission.evaluate', mutation); assert.equal(mutation.effect, 'deny');
      f.call('tool.execute.before', { agent: 'build', tool });
    }
    await f.emit('session.execution.succeeded');
    await f.emit('session.execution.started');
    f.call('tool.execute.before', { ...call, id: 'later_audit_child' });
  } finally { await cleanup(); f.remove(); }
});

test('one native task yields metadata-only unknown outcome; nonzero shell exit is a failed check', async () => {
  const f = fixture(); const cleanup = await plugin.setup(f.ctx);
  try {
    await f.emit('session.execution.started');
    await f.emit('session.execution.started', { sessionID: 'foreign' }, { directory: '/different-project' });
    f.call('tool.execute.after', { sessionID: 'ses_1', messageID: 'msg_1', tool: 'shell', status: 'completed',
      input: { command: 'python3 -m unittest' }, result: { output: { status: 'completed', exit: 1, output: 'SYNTHETIC_SECRET_SOURCE' } } });
    f.call('tool.execute.after', { sessionID: 'ses_1', messageID: 'msg_2', tool: 'shell', status: 'completed',
      input: { command: 'pytest -q' }, result: { output: { status: 'completed', exit: 0 } } });
    f.call('session.retry', { sessionID: 'ses_1' });
    await f.emit('session.step.ended', { tokens: { input: 12, output: 3, reasoning: 4 } });
    await f.emit('session.compaction.ended', { text: 'PRIVATE_PROMPT_URL https://private.test/' });
    await f.emit('session.execution.succeeded');
    await f.emit('session.execution.succeeded');
    const records = f.read('events'); assert.equal(records.length, 1);
    assert.equal(records[0].state, 'unknown'); assert.equal(records[0].tool_calls, 2);
    assert.equal(records[0].tool_errors, 1); assert.equal(records[0].check_failures, 1);
    assert.equal(records[0].check_passes, 1); assert.equal(records[0].compactions, 1);
    assert.equal(records[0].output_tokens, 3); assert.equal(records[0].corrections, null);
    assert.equal(records[0].family, 'json_cli');
    assert.equal(f.read('trackers')[0].counts.retries, 1);
    const all = JSON.stringify([...records, ...f.read('trackers')]);
    for (const value of ['SYNTHETIC_SECRET', 'PRIVATE_PROMPT', 'https://', 'python3', 'pytest', f.root])
      assert.equal(all.includes(value), false);
    assert.deepEqual(Object.keys(records[0]).sort(), ['schema', 'task_id', 'champion_revision', 'profile_id', 'state', 'wall_seconds',
      'tool_calls', 'tool_errors', 'check_passes', 'check_failures', 'compactions', 'corrections', 'output_tokens', 'family', 'completed_at'].sort());
  } finally { await cleanup(); f.remove(); }
});

test('session champion survives restart; tool schema pruning and native checkpoint guidance preserve user files', async () => {
  const f = fixture(); let cleanup = await plugin.setup(f.ctx);
  try {
    const context = { sessionID: 'ses_1', agent: 'reviewer', system: [], tools: { read: {}, shell: {}, remote_mutate: {} } };
    f.call('session.context', context); assert.deepEqual(Object.keys(context.tools), ['read']);
    assert.ok(context.system.some(p => p.text.includes('Inspect evidence before editing.')));
    fs.writeFileSync(path.join(f.root, 'TASK.md'), 'user-owned task record');
    const checkpoint = { sessionID: 'ses_1', agent: 'build', system: [], tools: {} };
    f.call('session.compaction', checkpoint); assert.equal(checkpoint.result, undefined);
    assert.ok(checkpoint.system.some(p => p.text.includes('reconcile')));
    await cleanup();
    const newInstructions = 'Different newly promoted guidance.';
    f.ctx.options.champion = { instructions: newInstructions, revision: digest(newInstructions) };
    cleanup = await plugin.setup(f.ctx);
    const resumed = { sessionID: 'ses_1', agent: 'browse', system: [], tools: { browser_browser_snapshot: {}, browser_browser_run_code_unsafe: {}, read: {} } };
    f.call('session.context', resumed);
    assert.equal(resumed.tools.browser_browser_run_code_unsafe, undefined);
    assert.ok(resumed.system.some(p => p.text.includes('Inspect evidence before editing.')));
    assert.equal(resumed.system.some(p => p.text.includes(newInstructions)), false);
    assert.equal(fs.readFileSync(path.join(f.root, 'TASK.md'), 'utf8'), 'user-owned task record');
    assert.equal(BROWSER_TOOLS.length, 17);
  } finally { await cleanup(); f.remove(); }
});

test('Browse advertises only its 22 browser/research tools across request hooks without changing other roles', async () => {
  const f = fixture(); const cleanup = await plugin.setup(f.ctx);
  try {
    const browser = [
      'browser_browser_navigate', 'browser_browser_navigate_back', 'browser_browser_snapshot',
      'browser_browser_click', 'browser_browser_type', 'browser_browser_fill_form',
      'browser_browser_press_key', 'browser_browser_select_option', 'browser_browser_wait_for',
      'browser_browser_take_screenshot', 'browser_browser_console_messages',
      'browser_browser_network_requests', 'browser_browser_resize', 'browser_browser_tabs',
      'browser_browser_handle_dialog', 'browser_browser_file_upload', 'browser_browser_close',
    ];
    const research = ['question', 'webfetch', 'search_web_search_exa',
      'search_web_fetch_exa', 'search_web_search_advanced_exa'];
    const allowed = [...browser, ...research].sort();
    const readOnly = [...research, 'read', 'glob', 'grep'].sort();
    const registry = Object.fromEntries([...allowed, ...readOnly, 'edit', 'write', 'shell', 'skill',
      'subagent', 'execute', 'patch', 'browser_browser_run_code_unsafe', 'browser_future_tool',
      'unknown_tool'].map(name => [name, { description: name }]));
    assert.deepEqual([...BROWSER_TOOLS].sort(), [...browser].sort());
    assert.equal(allowed.length, 22);
    for (const hook of ['context', 'generate', 'compaction']) {
      for (const agent of ['browse', 'build', 'plan', 'general', 'reviewer', 'explore', 'audit']) {
        const event = { sessionID: 'ses_' + agent, agent, system: [], tools: { ...registry } };
        f.call('session.' + hook, event);
        const expected = agent === 'browse' ? allowed
          : agent === 'audit' ? [...readOnly, 'subagent'].sort()
          : ['reviewer', 'explore'].includes(agent) ? readOnly : Object.keys(registry).sort();
        assert.deepEqual(Object.keys(event.tools).sort(), expected, agent + ' ' + hook);
        for (const name of expected) assert.equal(event.tools[name], registry[name]);
      }
    }
  } finally { await cleanup(); f.remove(); }
});

test('private state rejects symlinks and a changed capsule; trials emit no learning events', async () => {
  const f = fixture({ observe: false }); const cleanup = await plugin.setup(f.ctx);
  try {
    await f.emit('session.execution.started'); await f.emit('session.execution.failed');
    assert.equal(f.read('events').length, 0); assert.equal(f.read('trackers').length, 0);
    assert.throws(() => validatedOptions({ ...f.ctx.options, champion: { instructions: 'changed', revision: digest('') } }));
    assert.equal(isCheck('echo pytest'), false); assert.equal(isCheck('pytest; true'), false);
    assert.equal(isCheck('npm test -- --run'), true);
  } finally { await cleanup(); f.remove(); }
  const unsafe = fixture();
  fs.mkdirSync(path.join(unsafe.root, 'learning'));
  fs.symlinkSync(os.tmpdir(), path.join(unsafe.root, 'learning', 'events'));
  try { await assert.rejects(() => plugin.setup(unsafe.ctx)); }
  finally { unsafe.remove(); }
});

test('explicit JSON CLI scope reaches future work while resumed scope and guidance stay pinned', async () => {
  const f = fixture(); let cleanup = await plugin.setup(f.ctx);
  const baseline = { revision: digest(''), instructions: '' };
  try {
    assert.throws(() => validatedOptions({ ...f.ctx.options, workflowScope: null }));
    assert.throws(() => validatedOptions({ ...f.ctx.options, workflowScope: 'all' }));
    const first = { sessionID: 'scoped', agent: 'build', system: [], tools: {} };
    f.call('session.context', first);
    assert.equal(first.system.some(part => part.text.includes(f.ctx.options.champion.instructions)), true);
    const pins = path.join(f.root, 'learning', 'pins');
    const originalPin = fs.readFileSync(path.join(pins, fs.readdirSync(pins)[0]), 'utf8');
    await cleanup();
    f.ctx.options = { ...f.ctx.options, workflowScope: null, champion: baseline };
    cleanup = await plugin.setup(f.ctx);
    const resumed = { sessionID: 'scoped', agent: 'build', system: [], tools: {} };
    f.call('session.context', resumed);
    assert.equal(resumed.system.some(part => part.text.includes('Inspect evidence before editing.')), true);
    await f.emit('session.execution.started', { sessionID: 'scoped' });
    await f.emit('session.execution.failed', { sessionID: 'scoped' });
    const ordinary = { sessionID: 'ordinary', agent: 'build', system: [], tools: {} };
    f.call('session.context', ordinary);
    assert.equal(ordinary.system.some(part => part.text.includes('KRYN validated workflow guidance')), false);
    await f.emit('session.execution.started', { sessionID: 'ordinary' });
    await f.emit('session.execution.failed', { sessionID: 'ordinary' });
    const events = f.read('events');
    assert.equal(events.find(item => item.family === 'json_cli').champion_revision, digest('Inspect evidence before editing.'));
    assert.equal(events.find(item => item.family === 'unknown').champion_revision, baseline.revision);
    assert.equal(fs.readdirSync(pins).map(file => fs.readFileSync(path.join(pins,file),'utf8')).includes(originalPin), true);
    const ordinaryFile = fs.readdirSync(pins).find(file => JSON.parse(fs.readFileSync(path.join(pins,file),'utf8')).revision === baseline.revision);
    const legacy = { owner: 'kryn.product', schema: 1, ...baseline };
    fs.writeFileSync(path.join(pins,ordinaryFile),JSON.stringify(legacy)+'\n',{mode:0o600});
    await cleanup();
    f.ctx.options = { ...f.ctx.options, workflowScope: 'disposable_json_cli', champion: { revision: digest('Newly approved.'), instructions: 'Newly approved.' } };
    cleanup = await plugin.setup(f.ctx);
    const old = { sessionID: 'ordinary', agent: 'build', system: [], tools: {} };
    f.call('session.context',old);
    assert.equal(old.system.some(part => part.text.includes('Newly approved.')),false);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(pins,ordinaryFile),'utf8')),legacy);
  } finally { await cleanup(); f.remove(); }
});

test('bounded pin admission preserves old sessions and tracker retention preserves unknown files', async () => {
  const f = fixture(); const cleanup = await plugin.setup(f.ctx);
  try {
    f.call('session.context', { sessionID: 'saved', agent: 'build', system: [], tools: {} });
    const pins = path.join(f.root, 'learning', 'pins');
    for (let i = 0; i < 499; i++) fs.writeFileSync(path.join(pins, i.toString(16).padStart(64, '0') + '.json'), '{}', { mode: 0o600 });
    assert.throws(() => f.call('session.context', { sessionID: 'new', agent: 'build', system: [], tools: {} }), /500 saved session pins/);
    assert.doesNotThrow(() => f.call('session.context', { sessionID: 'saved', agent: 'build', system: [], tools: {} }));
    assert.equal(fs.readdirSync(pins).length, 500);
    const trackers = path.join(f.root, 'learning', 'trackers');
    for (let i = 0; i < 501; i++) fs.writeFileSync(path.join(trackers, i.toString(16).padStart(64, '0') + '.json'), JSON.stringify({ owner: 'kryn.product' }), { mode: 0o600 });
    fs.writeFileSync(path.join(trackers, 'user-note.txt'), 'preserve');
    pruneTrackers(trackers);
    assert.equal(fs.readdirSync(trackers).filter(name => name.endsWith('.json')).length, 500);
    assert.equal(fs.readFileSync(path.join(trackers, 'user-note.txt'), 'utf8'), 'preserve');
    pruneTrackers(trackers, Date.now() + 31 * 86400_000);
    assert.deepEqual(fs.readdirSync(trackers), ['user-note.txt']);
  } finally { await cleanup(); f.remove(); }
});
