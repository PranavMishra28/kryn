// Supported OpenCode 2.0.10 hooks. No agent loop, automatic approvals or model calls.
import { createHash, randomBytes } from 'node:crypto';
import * as fs from 'node:fs';
import path from 'node:path';

const sha = text => createHash('sha256').update(text).digest('hex');
const HASH = /^[a-f0-9]{64}$/;
const MAX_SESSION_PINS = 500;
const READ_TOOLS = new Set(['read', 'glob', 'grep', 'webfetch', 'question',
  'search_web_search_exa', 'search_web_fetch_exa', 'search_web_search_advanced_exa']);
const READ_ROLES = new Set(['reviewer', 'explore']);
const READ_ACTIONS = new Set([...READ_TOOLS, 'external_directory']);
export const BROWSER_TOOLS = [
  'browser_browser_navigate', 'browser_browser_navigate_back', 'browser_browser_snapshot',
  'browser_browser_click', 'browser_browser_type', 'browser_browser_fill_form',
  'browser_browser_press_key', 'browser_browser_select_option', 'browser_browser_wait_for',
  'browser_browser_take_screenshot', 'browser_browser_console_messages',
  'browser_browser_network_requests', 'browser_browser_resize', 'browser_browser_tabs',
  'browser_browser_handle_dialog', 'browser_browser_file_upload', 'browser_browser_close',
];
const BROWSER_SET = new Set(BROWSER_TOOLS);
const TRACKER_GUIDANCE = 'Keep the native checkpoint concise: objective and observable acceptance criteria; constraints and decisions; relevant file/symbol references; completed work; actual check commands and results; unresolved failures; disproven hypotheses; one next action. Separate observations from hypotheses. On continuation, reconcile the checkpoint with current Git, files and checks before trusting it. Do not create or overwrite TASK.md, tracker.md or other user files merely to record a checkpoint.';
const count = value => Number.isFinite(value) && value >= 0 ? Math.min(Math.floor(value), 1e9) : 0;

export function validatedOptions(options) {
  if (!options || typeof options.stateDir !== 'string' || !path.isAbsolute(options.stateDir))
    throw new Error('KRYN requires an absolute owned stateDir');
  if (typeof options.profileId !== 'string' || !/^[A-Za-z0-9._-]{1,128}$/.test(options.profileId))
    throw new Error('KRYN requires a bounded profile ID');
  if (typeof options.modelID !== 'string' || !/^[A-Za-z0-9._-]{1,128}$/.test(options.modelID))
    throw new Error('KRYN requires an exact local model ID');
  const champion = options.champion;
  if (!champion || typeof champion.instructions !== 'string' || champion.instructions.length > 1500 ||
      !HASH.test(champion.revision) || sha(champion.instructions) !== champion.revision)
    throw new Error('KRYN champion instruction hash does not match');
  const workflowScope = options.workflowScope ?? null;
  if (workflowScope !== null && workflowScope !== 'disposable_json_cli')
    throw new Error('KRYN does not recognize the selected workflow scope');
  if (champion.instructions && workflowScope !== 'disposable_json_cli')
    throw new Error('KRYN learned guidance requires the explicit JSON CLI workflow');
  const base = new URL(options.inferenceBaseURL ?? 'http://127.0.0.1:8000/v1');
  if (base.protocol !== 'http:' || base.hostname !== '127.0.0.1' || !base.port ||
      base.pathname !== '/v1' || base.username || base.password || base.search || base.hash)
    throw new Error('KRYN model endpoint must be an explicit loopback port at /v1');
  return Object.freeze({ stateDir: path.resolve(options.stateDir), profileId: options.profileId,
    modelID: options.modelID, baseURL: base.href, origin: base.origin, observe: options.observe !== false,
    workflowScope, champion: Object.freeze({ ...champion }) });
}

function ownedDirectory(directory, create = false) {
  if (create) {
    try { fs.mkdirSync(directory, { mode: 0o700 }); }
    catch (error) { if (error.code !== 'EEXIST') throw error; }
  }
  const info = fs.lstatSync(directory);
  if (!info.isDirectory() || info.isSymbolicLink() || info.uid !== process.getuid() ||
      (info.mode & 0o022) || fs.realpathSync(directory) !== path.resolve(directory))
    throw new Error('KRYN state directory is not private and owned');
  return directory;
}
function ownedFile(file) {
  const info = fs.lstatSync(file);
  if (!info.isFile() || info.isSymbolicLink() || info.uid !== process.getuid() || info.nlink !== 1 ||
      (info.mode & 0o077) || info.size > 32768) throw new Error('KRYN state file is not private and owned');
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}
function writeJSON(file, value, replace = false) {
  ownedDirectory(path.dirname(file));
  if (fs.existsSync(file) || fs.lstatSync(file, { throwIfNoEntry: false })) {
    const previous = ownedFile(file);
    if (!replace) return previous;
    if (previous.owner !== 'kryn.product') throw new Error('KRYN refuses an unowned tracker');
  }
  const temporary = file + '.' + randomBytes(8).toString('hex') + '.tmp';
  const fd = fs.openSync(temporary, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL |
    fs.constants.O_NOFOLLOW, 0o600);
  try { fs.writeFileSync(fd, JSON.stringify(value) + '\n'); fs.fsyncSync(fd); }
  finally { fs.closeSync(fd); }
  try {
    if (replace) fs.renameSync(temporary, file);
    else { fs.linkSync(temporary, file); fs.unlinkSync(temporary); }
  } catch (error) {
    fs.rmSync(temporary, { force: true });
    if (error.code !== 'EEXIST' || replace) throw error;
  }
  return value;
}

export function pruneTrackers(directory, now = Date.now()) {
  const records = [];
  for (const name of fs.readdirSync(directory)) {
    if (!/^[a-f0-9]{64}\.json$/.test(name)) continue;
    const file = path.join(directory, name);
    try {
      if (ownedFile(file).owner !== 'kryn.product') continue;
      records.push({ file, modified: fs.statSync(file).mtimeMs });
    } catch { continue; } // Unknown/linked user files are preserved.
  }
  records.sort((a, b) => b.modified - a.modified);
  for (const [index, item] of records.entries())
    if (index >= 500 || item.modified < now - 30 * 86400_000) fs.unlinkSync(item.file);
}

// Only simple test commands count. Exit zero remains evidence of a command, not task correctness.
export function isCheck(command) {
  if (typeof command !== 'string' || command.length > 4096 || /[;&|`$\n\r<>]/.test(command)) return false;
  return /^(?:python(?:3(?:\.\d+)?)?\s+-m\s+(?:unittest|pytest)(?:\s|$)|pytest(?:\s|$)|(?:npm|pnpm|yarn)\s+(?:run\s+)?test(?:\s|$)|go\s+test(?:\s|$)|cargo\s+test(?:\s|$))/.test(command.trim());
}
export function assertLocal(event, options, wire = false) {
  if (event.model?.providerID !== 'local' || event.model?.id !== 'qwen')
    throw new Error('KRYN blocked a nonlocal model role');
  const raw = wire ? event.request.url : event.baseURL;
  let url;
  try { url = new URL(raw); } catch { throw new Error('KRYN blocked an invalid model destination'); }
  if (url.origin !== options.origin || url.username || url.password || url.search || url.hash ||
      (wire ? url.pathname !== '/v1/chat/completions' : url.pathname !== '/v1'))
    throw new Error('KRYN blocked a changed model destination');
}

export default {
  id: 'kryn.product',
  async setup(ctx) {
    const options = validatedOptions(ctx.options);
    ownedDirectory(options.stateDir);
    const learning = ownedDirectory(path.join(options.stateDir, 'learning'), true);
    const folders = Object.fromEntries(['events', 'pins', 'trackers'].map(name =>
      [name, ownedDirectory(path.join(learning, name), true)]));
    if (options.observe) pruneTrackers(folders.trackers);
    const sessions = new Map();
    const activeChildren = new Map();
    const seen = new Set();
    let failed;
    const assertHealthy = () => { if (failed) throw new Error('KRYN observer failed; restart and inspect owned state'); };
    const sameLocation = location => location?.directory === ctx.location.directory &&
      (location?.workspaceID ?? null) === (ctx.location.workspaceID ?? null);
    const sessionKey = id => sha(ctx.location.project.canonical + '\0' + id);
    function session(id) {
      if (typeof id !== 'string' || id.length > 160) throw new Error('KRYN invalid session identity');
      if (sessions.has(id)) return sessions.get(id);
      const key = sessionKey(id), file = path.join(folders.pins, key + '.json');
      // Preserve every saved champion identity, including resumed old sessions.
      // Reaching this bound refuses a new session; it never silently re-pins one.
      if (!fs.existsSync(file) && fs.readdirSync(folders.pins).filter(name => /^[a-f0-9]{64}\.json$/.test(name)).length >= MAX_SESSION_PINS)
        throw new Error('KRYN has reached 500 saved session pins; inspect and archive owned session state before creating another session');
      const pin = writeJSON(file, { owner: 'kryn.product', schema: 2, ...options.champion,
        workflowScope: options.workflowScope });
      if (pin.owner !== 'kryn.product' || ![1, 2].includes(pin.schema) || typeof pin.instructions !== 'string' ||
          pin.instructions.length > 1500 || sha(pin.instructions) !== pin.revision ||
          (pin.schema === 2 && pin.workflowScope !== null && pin.workflowScope !== 'disposable_json_cli') ||
          (pin.schema === 2 && pin.instructions && pin.workflowScope !== 'disposable_json_cli') ||
          (pin.schema === 1 && pin.workflowScope !== undefined))
        throw new Error('KRYN saved session pin changed');
      const item = { key, native_session_id: id, pin: Object.freeze(pin), turn: undefined, checkpoint: null };
      sessions.set(id, item);
      return item;
    }
    function start(id, token) {
      const item = session(id);
      if (item.turn) return item;
      item.turn = { task_id: sha(item.key + '\0' + token), started: Date.now(), tool_calls: 0,
        tool_errors: 0, check_passes: 0, check_failures: 0, compactions: 0, output_tokens: 0,
        retries: 0, input_tokens: 0, reasoning_tokens: 0 };
      return item;
    }
    function tracker(item, state = 'unknown') {
      if (!options.observe || !item.turn) return;
      writeJSON(path.join(folders.trackers, item.key + '.json'), { owner: 'kryn.product', schema: 1,
        task_id: item.turn.task_id, champion_revision: item.pin.revision,
        native_session_id: item.native_session_id, native_checkpoint_event: item.checkpoint,
        state, counts: Object.fromEntries(Object.entries(item.turn).filter(([key]) => key !== 'started' && key !== 'task_id')),
        updated_at: new Date().toISOString(),
        note: 'Continuity aid only. Native checkpoint holds task details; reconcile Git, files and checks on resume.' }, true);
    }
    function finish(id, state) {
      const item = sessions.get(id);
      if (!item?.turn) return;
      if (options.observe) {
        const t = item.turn;
        writeJSON(path.join(folders.events, t.task_id + '.json'), { schema: 1, task_id: t.task_id,
          champion_revision: item.pin.revision, profile_id: options.profileId, state,
          wall_seconds: Math.max(0, (Date.now() - t.started) / 1000), tool_calls: t.tool_calls,
          tool_errors: t.tool_errors, check_passes: t.check_passes, check_failures: t.check_failures,
          compactions: t.compactions, corrections: null, output_tokens: t.output_tokens,
          family: item.pin.workflowScope === 'disposable_json_cli' ? 'json_cli' : 'unknown',
          completed_at: new Date().toISOString() });
        tracker(item, state);
        pruneTrackers(folders.trackers);
      }
      item.turn = undefined;
      activeChildren.delete(id);
    }

    await ctx.session.hook('prompt', event => {
      assertHealthy();
      session(event.sessionID); // Native execution events group steered prompts into one task.
    });
    const instructions = event => {
      assertHealthy();
      const item = session(event.sessionID);
      if (item.pin.instructions) event.system.push({ type: 'text', text:
        'KRYN validated workflow guidance (subordinate to current user authorization and safety):\n' + item.pin.instructions });
      event.system.push({ type: 'text', text: TRACKER_GUIDANCE });
      if (READ_ROLES.has(event.agent))
        for (const name of Object.keys(event.tools ?? {})) if (!READ_TOOLS.has(name)) delete event.tools[name];
      if (event.agent === 'browse')
        for (const name of Object.keys(event.tools ?? {}))
          if (name.startsWith('browser_') && !BROWSER_SET.has(name)) delete event.tools[name];
    };
    await ctx.session.hook('context', instructions);
    await ctx.session.hook('generate', instructions);
    await ctx.session.hook('compaction', event => { instructions(event); tracker(session(event.sessionID)); });
    await ctx.session.hook('retry', event => {
      const item = start(event.sessionID, 'retry-' + Date.now());
      item.turn.retries = count(item.turn.retries + 1); tracker(item);
    });
    await ctx.session.hook('model.request', event => { assertHealthy(); assertLocal(event, options); });
    await ctx.session.hook('http.request', async event => {
      assertHealthy(); assertLocal(event, options, true);
      if (event.request.method !== 'POST') throw new Error('KRYN blocked unexpected model HTTP method');
      const body = await event.request.clone().json();
      if (body.model !== options.modelID) throw new Error('KRYN blocked a changed runtime model ID');
      if (event.kind === 'title') {
        // Native 2.0.10 has no title output budget. This final wire hook runs
        // after model.body overlays, which otherwise replace generation limits.
        body.max_tokens = Number.isInteger(body.max_tokens) && body.max_tokens > 0
          ? Math.min(body.max_tokens, 128) : 128;
        const headers = new Headers(event.request.headers);
        headers.delete('content-length');
        event.request = new Request(event.request, { headers, body: JSON.stringify(body) });
      }
    });
    await ctx.session.hook('experimental.ws.handshake', () => { throw new Error('KRYN has not qualified model WebSocket transport'); });
    await ctx.permission.hook('evaluate', event => {
      if (READ_ROLES.has(event.agent) && !READ_ACTIONS.has(event.action)) {
        event.effect = 'deny'; event.message = 'KRYN managed read-only role';
      }
    });
    await ctx.tool.hook('execute.before', event => {
      assertHealthy();
      if (READ_ROLES.has(event.agent) && !READ_TOOLS.has(event.tool))
        throw new Error('KRYN managed read-only role cannot execute this tool');
      if (event.agent === 'browse' && event.tool.startsWith('browser_') && !BROWSER_SET.has(event.tool))
        throw new Error('KRYN Browse tool is outside the qualified surface');
      if (event.tool === 'subagent') {
        if (activeChildren.has(event.sessionID)) throw new Error('KRYN allows one foreground child at a time');
        if (!event.input || typeof event.input !== 'object') throw new Error('KRYN invalid subagent input');
        event.input = { ...event.input, background: false };
        activeChildren.set(event.sessionID, event.id);
      }
    });
    await ctx.tool.hook('execute.after', event => {
      const item = start(event.sessionID, event.messageID);
      const t = item.turn;
      t.tool_calls = count(t.tool_calls + 1);
      if (event.status === 'error') t.tool_errors = count(t.tool_errors + 1);
      if (event.tool === 'shell' && event.status === 'completed' &&
          (event.result?.output?.exit !== undefined && event.result.output.exit !== 0 || event.result?.output?.timeout))
        t.tool_errors = count(t.tool_errors + 1);
      if (event.tool === 'shell' && event.status === 'completed' && isCheck(event.input?.command)) {
        const output = event.result?.output;
        if (typeof output?.exit === 'number' && output.status !== 'running') {
          if (output.exit === 0 && !output.timeout) t.check_passes = count(t.check_passes + 1);
          else t.check_failures = count(t.check_failures + 1);
        }
      }
      if (event.tool === 'subagent' && activeChildren.get(event.sessionID) === event.id)
        activeChildren.delete(event.sessionID);
      if (t.tool_errors || t.check_failures) tracker(item);
    });

    const controller = new AbortController();
    const pump = (async () => {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        if (!sameLocation(event.location) || typeof event.data?.sessionID !== 'string') continue;
        if (seen.has(event.id)) continue;
        seen.add(event.id);
        if (seen.size > 4096) seen.delete(seen.values().next().value);
        const id = event.data.sessionID;
        if (event.type === 'session.execution.started') start(id, event.id);
        if (event.type === 'session.step.ended') {
          const item = start(id, event.id);
          item.turn.output_tokens = count(item.turn.output_tokens + count(event.data.tokens?.output));
          item.turn.input_tokens = count(item.turn.input_tokens + count(event.data.tokens?.input));
          item.turn.reasoning_tokens = count(item.turn.reasoning_tokens + count(event.data.tokens?.reasoning));
        }
        if (event.type === 'session.compaction.ended') {
          const item = start(id, event.id);
          item.turn.compactions = count(item.turn.compactions + 1);
          item.checkpoint = event.id;
          tracker(item);
        }
        if (event.type === 'session.execution.succeeded') finish(id, 'unknown');
        if (event.type === 'session.execution.failed') finish(id, 'failed');
        if (event.type === 'session.execution.interrupted') finish(id, 'incomplete');
      }
    })().catch(error => { if (!controller.signal.aborted) failed = error; });
    return async () => {
      controller.abort();
      await pump;
      for (const id of sessions.keys()) finish(id, 'incomplete');
    };
  },
};
