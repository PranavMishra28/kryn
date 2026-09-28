// Read-only KRYN release awareness using the pinned OpenCode V2 plugin context.
import { execFile } from 'node:child_process';
import path from 'node:path';
import { promisify } from 'node:util';

const exec = promisify(execFile);
export const CHECK_INTERVAL = 6 * 60 * 60 * 1000;

async function packageCheck(python, signal) {
  if (!python || !path.isAbsolute(python)) throw new Error('No installed package interpreter');
  const { stdout } = await exec(python, ['-I', '-B', '-m', 'kryn', 'update', '--check'],
    { signal, timeout: 90000, maxBuffer: 32768, windowsHide: true });
  return JSON.parse(stdout);
}

export function verifiedNotice(value) {
  return value?.status === 'available' && /^v\d+\.\d+\.\d+$/.test(value.tag) &&
    /^[a-f0-9]{40}$/.test(value.source_revision) && /^[a-f0-9]{64}$/.test(value.sha256) &&
    typeof value.summary === 'string' && Array.from(value.summary).length <= 241 &&
    !/[\p{Cc}\p{Cf}]/u.test(value.summary);
}

export function setupUpdates(context, { check = (signal) => packageCheck(process.env.KRYN_UPDATE_PYTHON, signal),
    now = Date.now } = {}) {
  const [state, save] = context.storage.store('kryn-release-notice', {
    initial: { checked: 0, notified: '' },
  });
  const controller = new AbortController();
  let result, inFlight, disposed = false, dialogOpen = false, lastAttempt = 0, notified = '';
  const idle = () => context.data.session.list().every(session => context.data.session.status(session.id) === 'idle');
  const identity = () => `${result.tag}:${result.sha256}`;
  const toast = message => context.ui.toast.show({ title: 'KRYN update', message, variant: 'info', duration: 10000 });
  const recent = stamp => Number.isFinite(stamp) && now() >= stamp && now() - stamp < CHECK_INTERVAL;

  async function refresh(force = false) {
    if (inFlight) return inFlight;
    if (!force && recent(state.checked)) return;
    // Repeated palette invocations share a check, including a short failure cooldown.
    if (lastAttempt && now() - lastAttempt < 30000) return;
    lastAttempt = now();
    inFlight = (async () => {
      await save(draft => { draft.checked = now(); });
      try { result = await check(controller.signal); }
      catch { result = { status: 'unavailable' }; }
    })();
    try { await inFlight; } finally { inFlight = undefined; }
  }

  async function poll() {
    if (disposed || !idle()) return;
    try {
      await refresh();
      // Work may have started while HTTPS verification was in progress.
      if (disposed || !idle() || !verifiedNotice(result) || state.notified === identity() || notified === identity()) return;
      notified = identity();
      toast(`${result.tag}${result.prerelease ? ' prerelease' : ''} · ${result.source_revision.slice(0,12)} available. Use /update to review, or leave it for later.`);
      await save(draft => { draft.notified = notified; });
    } catch { /* Storage/network failure must never block coding or repeat prompts. */ }
  }

  async function open() {
    if (disposed || dialogOpen) return;
    if (!idle()) { toast('Finish the active turn before checking KRYN updates.'); return; }
    dialogOpen = true;
    try {
      await refresh(true);
      if (disposed || !idle()) return;
      if (!verifiedNotice(result)) {
        await context.ui.dialog.alert({ title: 'KRYN updates', message: result?.status === 'current'
          ? 'No newer published KRYN release was found. Same-version private builds and main commits are not offered as updates.'
          : 'Could not verify a KRYN release. Check your network and try /update later; your installation is unchanged.' });
        return;
      }
      await save(draft => { draft.notified = identity(); });
      const selected = result;
      const details = `${selected.tag}${selected.prerelease ? ' (prerelease)' : ''}\nSource: ${selected.source_revision}\n\n${selected.summary}\n\nRelease checksums verified.`;
      const instructions = await context.ui.dialog.confirm({ title: 'KRYN update available', message: details,
        label: { confirm: 'Update instructions', cancel: 'Later' } });
      if (!instructions || disposed) return;
      await context.ui.dialog.alert({ title: 'Update KRYN after exit', message:
        `Finish work and exit KRYN, then run in Terminal:\n\nkryn update ${selected.tag}\n\nResume from your project with kryn --continue. Saved sessions remain; kryn rollback restores the previous retained installation.` });
    } catch {
      if (!disposed) toast('KRYN update check unavailable. Try /update later.');
    } finally { dialogOpen = false; }
  }

  const timer = setInterval(() => { void poll(); }, 60000);
  void poll();
  return { open, poll, dispose() { disposed = true; clearInterval(timer); controller.abort(); } };
}
