#!/usr/bin/env node
// Independent outcome checks; this does not certify the model's use of MCP or vision.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { randomUUID } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';
import { spawnSync } from 'node:child_process';

const fields = ['id', 'project', 'minutes', 'date'];
const csv = rows => [fields, ...rows.map(row => fields.map(key => row[key]))]
  .map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\r\n') + '\r\n';
const canonical = rows => rows.map(row => Object.fromEntries(fields.map(key => [key, row[key]])))
  .sort((a, b) => a.id.localeCompare(b.id));
function parseCsv(text) {
  // Reuse the standard-library CSV parser, never candidate code or a new dependency.
  const result = spawnSync('python3', ['-B', '-c',
    'import csv,io,json,sys\nr=csv.DictReader(io.StringIO(sys.stdin.read().lstrip("\\ufeff")))\nassert r.fieldnames==["id","project","minutes","date"]\nprint(json.dumps([dict(x,minutes=int(x["minutes"])) for x in r]))'],
  { input: text, encoding: 'utf8', timeout: 10000, maxBuffer: 2 * 1024 * 1024 });
  assert.equal(result.status, 0, 'Export must be valid CSV with the documented fields');
  return JSON.parse(result.stdout);
}
function localUrl(value) {
  const url = new URL(value);
  assert(url.protocol === 'http:' && ['127.0.0.1', '[::1]', 'localhost'].includes(url.hostname), 'Use an HTTP loopback URL');
  assert(!url.username && !url.password && !url.search && !url.hash, 'URL must not contain credentials/query/fragment');
  assert(url.pathname === '/', 'URL must be the application origin');
  return url;
}
const { values } = parseArgs({ options: {
  url: { type: 'string' }, output: { type: 'string' }, db: { type: 'string' }, task: { type: 'string' },
  task06: { type: 'boolean' }, task08: { type: 'boolean' }, task12: { type: 'boolean' },
  help: { type: 'boolean' }, 'self-check': { type: 'boolean' },
} });
if (values.help) {
  console.log('browser_check.mjs --url http://127.0.0.1:PORT --output NEW_EVIDENCE_DIR --db DISPOSABLE.db --task 06|08|12\nAlso accepts --task06/--task08/--task12. Start the fixture/candidate server separately. No LLM/MCP calls.');
} else if (values['self-check']) {
  const rows = [{ id: 'a', project: '研究, "team"\nnext', minutes: 0, date: '2026-09-11' }];
  assert.deepEqual(parseCsv(csv(rows)), rows);
  assert.throws(() => localUrl('https://example.com/'));
  assert.throws(() => localUrl('http://user:pass@127.0.0.1/'));
  assert.equal(localUrl('http://127.0.0.1:8765').hostname, '127.0.0.1');
  console.log('Offline self-check passed: CSV round-trip and loopback URL restrictions. No browser started.');
} else {
  await main();
}

async function main() {
  const task = values.task ?? ['06', '08', '12'].find(id => values[`task${id}`]);
  const report = { task, kind: 'independent browser outcome verification', pass: false, checks: [],
    screenshots: [], pageErrors: [], console: [], network: [], failedRequests: [],
    limitations: ['Not evidence of model MCP use, model vision, review, compaction, or long-running work.'] };
  let browser, context, page, output, marker, markerOwned = false, created = false;
  const check = async (name, fn) => {
    try { const detail = await fn(); report.checks.push({ name, pass: true, detail }); }
    catch (error) { report.checks.push({ name, pass: false, error: error.message }); throw error; }
  };
  try {
    assert(['06', '08', '12'].includes(task), 'Choose task 06, 08, or 12');
    assert(Number(Boolean(values.task)) + ['06', '08', '12'].filter(id => values[`task${id}`]).length === 1, 'Specify exactly one task');
    const url = localUrl(values.url);
    assert(values.output && values.db, '--output and --db are required');
    output = path.resolve(values.output);
    const db = path.resolve(values.db);
    assert(db.endsWith('.db') && (await fs.lstat(db)).isFile(), '--db must be an existing disposable .db file, not a symlink');
    marker = db.slice(0, -3) + '.fail-next';
    await fs.mkdir(output); // A rerun must use a new evidence directory.
    created = true;
    const module = path.join(os.homedir(), 'Library/Application Support/LocalAI/browser/node_modules/playwright/index.mjs');
    const { chromium } = await import(pathToFileURL(module).href);
    browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
    context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'en-US', timezoneId: 'UTC', acceptDownloads: true });
    context.setDefaultTimeout(10000);
    await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
    await context.route('**/*', route => {
      const requested = new URL(route.request().url());
      return requested.origin === url.origin ? route.continue() : route.abort('blockedbyclient');
    });
    page = await context.newPage();
    page.on('pageerror', error => report.pageErrors.push(error.message));
    page.on('console', message => report.console.push({ type: message.type(), text: message.text(), location: message.location() }));
    page.on('response', response => report.network.push({ method: response.request().method(), url: response.url(), status: response.status() }));
    page.on('requestfailed', request => report.failedRequests.push({ url: request.url(), error: request.failure()?.errorText }));
    const apiRows = async () => {
      const response = await context.request.get(new URL('/api/entries', url).href, { maxRedirects: 0 });
      assert.equal(response.status(), 200, 'Entries API must return 200');
      return response.json();
    };
    const initial = canonical(await apiRows());
    const prefix = `browser-${task}-${randomUUID().slice(0, 8)}`;
    const form = page.locator('#entry-form');
    const save = form.getByRole('button', { name: /^Save$/i });
    const live = page.locator('[role="status"], [role="alert"], [aria-live]').first();
    const fill = async (row, edit = false) => {
      for (const key of fields.filter(key => !edit || key !== 'id')) await form.locator(`[name="${key}"]`).fill(String(row[key]));
    };
    const formValues = () => form.evaluate(el => Object.fromEntries(new FormData(el)));
    const submit = async (method, status) => {
      const [response] = await Promise.all([page.waitForResponse(response => new URL(response.url()).pathname.startsWith('/api/entries')
        && response.request().method() === method), save.click()]);
      assert.equal(response.status(), status, `Expected ${method} status ${status}`);
      return response;
    };
    const cleared = () => page.waitForFunction(() => [...document.querySelectorAll('#entry-form input')].every(input => input.value === ''));
    const screenshot = async name => { await page.screenshot({ path: path.join(output, name), fullPage: true }); report.screenshots.push(name); };
    await page.goto(url.href, { waitUntil: 'networkidle' });
    for (const viewport of [{ width: 390, height: 844 }, { width: 1280, height: 800 }]) {
      await check(`responsive form, save and reload ${viewport.width}x${viewport.height}`, async () => {
        await page.setViewportSize(viewport);
        const box = await save.boundingBox();
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Page has horizontal overflow');
        assert(box && box.width > 0 && box.height > 0 && box.x >= 0 && box.y >= 0
          && box.x + box.width <= viewport.width + 1 && box.y + box.height <= viewport.height + 1, 'Save button is clipped/outside viewport');
        await save.click({ trial: true });
        const row = { id: `${prefix}-${viewport.width}`, project: 'Browser check', minutes: 13, date: '2026-09-11' };
        await fill(row); await submit('POST', 201); await cleared();
        await page.reload({ waitUntil: 'networkidle' });
        assert.deepEqual((await apiRows()).find(item => item.id === row.id), row);
        assert((await page.locator('#entries').innerText()).includes(row.id), 'Saved row must appear after reload');
        await screenshot(`viewport-${viewport.width}x${viewport.height}.png`);
        return { box, persisted: row };
      });
    }
    if (task !== '08') {
      await check('invalid minutes produce accessible feedback without persistence', async () => {
        const row = { id: `${prefix}-invalid`, project: 'Invalid', minutes: -1, date: '2026-09-11' };
        await fill(row); const before = await live.innerText(); await save.click();
        await page.waitForFunction(previous => {
          const input = document.querySelector('#entry-form [name="minutes"]');
          return !input.validity.valid || [...document.querySelectorAll('[role="status"],[role="alert"],[aria-live]')]
            .some(el => el.textContent.trim() && el.textContent !== previous);
        }, before);
        const validation = await form.locator('[name="minutes"]').evaluate(el => ({ valid: el.validity.valid,
          message: el.validationMessage, labelled: Boolean(el.labels?.length || el.getAttribute('aria-label')) }));
        assert((!validation.valid && validation.message && validation.labelled)
          || (await live.isVisible() && (await live.innerText()).trim() !== before), 'No accessible validation feedback');
        assert(!(await apiRows()).some(item => item.id === row.id));
        await screenshot('invalid-feedback.png'); return validation;
      });
      await check('real injected 503 preserves input; one retry creates exactly one row', async () => {
        const row = { id: `${prefix}-retry`, project: 'Retry', minutes: 17, date: '2026-09-12' };
        await fill(row); const before = await formValues(); const oldMessage = await live.innerText();
        await fs.writeFile(marker, '', { flag: 'wx' }); markerOwned = true;
        await submit('POST', 503);
        await page.waitForFunction(previous => [...document.querySelectorAll('[role="status"],[role="alert"],[aria-live]')]
          .some(el => el.textContent.trim() && el.textContent !== previous), oldMessage);
        assert(await live.isVisible()); assert.deepEqual(await formValues(), before);
        assert(!(await apiRows()).some(item => item.id === row.id)); await screenshot('temporary-error.png');
        await submit('POST', 201); await cleared(); await page.reload({ waitUntil: 'networkidle' });
        assert.deepEqual((await apiRows()).filter(item => item.id === row.id), [row]);
      });
    }
    if (task === '12') {
      const imported = [{ id: `${prefix}-upload-a`, project: '研究, team', minutes: 0, date: '2026-09-13' },
        { id: `${prefix}-upload-b`, project: '研究, Team', minutes: 29, date: '2026-09-14' },
        { id: `${prefix}-upload-c`, project: '研究, team extra 🧪', minutes: 7, date: '2026-09-15' }];
      const upload = async (name, rows, status) => {
        const file = path.join(output, name); await fs.writeFile(file, csv(rows), { flag: 'wx' });
        await page.locator('#upload').setInputFiles(file);
        const [response] = await Promise.all([page.waitForResponse(r => new URL(r.url()).pathname === '/api/import'
          && r.request().method() === 'POST'), page.getByRole('button', { name: /^Import$/i }).click()]);
        assert.equal(response.status(), status); return response.json();
      };
      await check('browser file upload and atomic invalid/duplicate rejection', async () => {
        assert.equal((await upload('valid.csv', imported, 201)).count, imported.length);
        const before = canonical(await apiRows());
        for (const [name, rows] of [['invalid.csv', [{ ...imported[0], id: `${prefix}-atomic` }, { ...imported[1], minutes: -1 }]],
          ['duplicate-existing.csv', [{ ...imported[0], id: `${prefix}-atomic` }, imported[1]]],
          ['duplicate-batch.csv', [{ ...imported[0], id: `${prefix}-atomic` }, { ...imported[0], id: `${prefix}-atomic` }]]]) {
          const error = await upload(name, rows, 400); assert(error.error); assert.deepEqual(canonical(await apiRows()), before);
        }
        await page.reload({ waitUntil: 'networkidle' });
        for (const row of imported) assert.deepEqual((await apiRows()).find(item => item.id === row.id), row);
      });
      await check('persistent browser edit, exact filter and downloaded CSV round-trip', async () => {
        await page.locator('#entries > *').filter({ hasText: imported[0].id }).getByRole('button', { name: /^Edit$/i }).click();
        const edited = { ...imported[0], minutes: 41 }; await fill(edited, true); await submit('PATCH', 200); await cleared();
        await page.reload({ waitUntil: 'networkidle' }); assert.deepEqual((await apiRows()).find(row => row.id === edited.id), edited);
        await page.getByLabel('Filter project', { exact: true }).fill(edited.project);
        await page.getByRole('button', { name: /^Filter$/i }).click();
        await page.waitForFunction(id => !document.querySelector('#entries').textContent.includes(id), imported[1].id);
        const visible = await page.locator('#entries').innerText();
        for (const row of await apiRows()) assert.equal(visible.includes(row.id), row.project === edited.project, `Wrong filter visibility: ${row.id}`);
        await screenshot('filtered-edited.png');
        const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('link', { name: /^Export CSV$/i }).click()]);
        const file = path.join(output, 'export.csv'); await download.saveAs(file);
        assert.deepEqual(canonical(parseCsv(await fs.readFile(file, 'utf8'))), canonical(await apiRows()));
      });
    }
    await check('seed preservation, unhandled errors and network inspection', async () => {
      const final = canonical(await apiRows());
      for (const row of initial) assert.deepEqual(final.find(item => item.id === row.id), row, `Pre-existing row changed: ${row.id}`);
      assert.deepEqual(report.pageErrors, [], 'Unhandled JavaScript errors');
      assert.deepEqual(report.failedRequests, [], 'Failed/blocked network requests');
      const unexpected = report.network.filter(item => item.status >= 400 && !([400, 503].includes(item.status)
        && item.method === 'POST' && ['/api/entries', '/api/import'].includes(new URL(item.url).pathname))
        && !(item.status === 404 && new URL(item.url).pathname === '/favicon.ico'));
      assert.deepEqual(unexpected, [], 'Unexpected HTTP errors');
      await fs.writeFile(path.join(output, 'api-before-after.json'), JSON.stringify({ initial, final }, null, 2));
    });
    try { await page.pdf({ path: path.join(output, 'page.pdf'), format: 'A4', printBackground: true }); report.pdf = 'page.pdf'; }
    catch (error) { report.pdf = { available: false, reason: error.message }; }
    report.pass = true;
  } catch (error) {
    report.error = error.stack;
    if (page && created) await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
  } finally {
    if (markerOwned) await fs.unlink(marker).catch(error => { if (error.code !== 'ENOENT') { report.markerCleanupError = error.message; report.pass = false; } });
    if (context && created) await context.tracing.stop({ path: path.join(output, 'trace.zip') }).catch(error => { report.traceError = error.message; report.pass = false; });
    if (browser) await browser.close().catch(error => { report.cleanupError = error.message; report.pass = false; });
    if (created) await fs.writeFile(path.join(output, 'browser-report.json'), JSON.stringify(report, null, 2));
  }
  console.log(JSON.stringify({ pass: report.pass, task, report: created ? path.join(output, 'browser-report.json') : null, error: report.error }));
  process.exitCode = report.pass ? 0 : browser ? 1 : 2;
}
