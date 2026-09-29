#!/usr/bin/env node
// Private outcome oracle. Never copy this file into the candidate workspace.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

const { values } = parseArgs({ options: {
  url: { type: 'string' }, db: { type: 'string' }, output: { type: 'string' },
  'self-check': { type: 'boolean' },
} });
const origin = value => {
  const url = new URL(value);
  assert.equal(url.protocol, 'http:');
  assert(['localhost', '127.0.0.1', '[::1]'].includes(url.hostname));
  assert(!url.username && !url.password && !url.search && !url.hash && url.pathname === '/');
  return url;
};

if (values['self-check']) {
  assert.equal(origin('http://127.0.0.1:8765').hostname, '127.0.0.1');
  assert.throws(() => origin('https://example.com'));
  assert.throws(() => origin('http://user:pass@127.0.0.1'));
  console.log('Review-queue browser oracle offline self-check passed; no browser started.');
} else {
  await main();
}

async function main() {
  const report = { kind: 'independent review-queue browser acceptance', pass: false,
    checks: [], screenshots: [], pageErrors: [], console: [], network: [], failedRequests: [] };
  let browser, context, page, output, marker, ownsMarker = false;
  const check = async (name, fn) => {
    try {
      const detail = await fn();
      assert.deepEqual(report.pageErrors, [], 'Unhandled page JavaScript error');
      report.checks.push({ name, pass: true, detail });
    } catch (error) {
      report.checks.push({ name, pass: false, error: error.message });
      throw error;
    }
  };
  try {
    const url = origin(values.url);
    assert(values.db && values.output, '--db and --output are required');
    const db = path.resolve(values.db);
    assert(db.endsWith('.db') && (await fs.lstat(db)).isFile(), 'Use an existing disposable .db');
    marker = db.slice(0, -3) + '.fail-next';
    output = path.resolve(values.output);
    await fs.mkdir(output);
    const module = path.join(os.homedir(), 'Library/Application Support/LocalAI/browser/node_modules/playwright/index.mjs');
    const { chromium } = await import(pathToFileURL(module).href);
    browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
    context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'en-US' });
    context.setDefaultTimeout(10000);
    await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
    await context.route('**/*', route => new URL(route.request().url()).origin === url.origin
      ? route.continue() : route.abort('blockedbyclient'));
    page = await context.newPage();
    page.on('pageerror', error => report.pageErrors.push(error.message));
    page.on('console', message => report.console.push({ type: message.type(), text: message.text() }));
    page.on('response', response => report.network.push({ method: response.request().method(),
      path: new URL(response.url()).pathname, status: response.status() }));
    page.on('requestfailed', request => report.failedRequests.push({ url: request.url(),
      error: request.failure()?.errorText }));
    const api = async () => {
      const response = await context.request.get(new URL('/api/review', url).href);
      assert.equal(response.status(), 200);
      return response.json();
    };
    const state = async id => (await api()).find(row => row.id === id)?.reviewed;
    const filter = page.getByLabel(/Review status/i);
    const list = page.locator('#entries');
    const row = id => list.locator(':scope > *').filter({ hasText: id });
    const status = page.locator('[role="status"], [role="alert"], [aria-live]').first();
    const screenshot = async name => {
      await page.screenshot({ path: path.join(output, name), fullPage: true });
      report.screenshots.push(name);
    };
    const postResponse = async (button, code) => {
      const [response] = await Promise.all([page.waitForResponse(response =>
        new URL(response.url()).pathname === '/api/review' && response.request().method() === 'POST'), button.click()]);
      assert.equal(response.status(), code);
    };
    await page.goto(url.href, { waitUntil: 'networkidle' });
    await check('pending filter and initial state', async () => {
      assert.equal(await state('t1'), false);
      await filter.selectOption({ label: 'All' });
      for (const id of ['t1', 't2', 't3']) await row(id).waitFor({ state: 'visible' });
      assert.equal(await list.locator(':scope > *').count(), 3);
      await filter.selectOption({ label: 'Pending' });
      await row('t1').waitFor({ state: 'visible' });
      assert.equal(await row('t1').count(), 1);
      assert.equal(await row('t1').getByRole('button', { name: /^Mark reviewed$/i }).count(), 1);
      await filter.selectOption({ label: 'Reviewed' });
      await row('t1').waitFor({ state: 'hidden' });
      assert.equal(await row('t1').count(), 0);
      await filter.selectOption({ label: 'Pending' });
      await row('t1').waitFor({ state: 'visible' });
      await screenshot('pending-390.png');
      return { initial: 'pending', filter: 'Pending' };
    });
    await check('503 keeps state, filter and manual retry action', async () => {
      await fs.writeFile(marker, '', { flag: 'wx' }); ownsMarker = true;
      const button = row('t1').getByRole('button', { name: /^Mark reviewed$/i });
      const before = await status.innerText();
      await postResponse(button, 503);
      await page.waitForFunction(previous => [...document.querySelectorAll('[role="status"],[role="alert"],[aria-live]')]
        .some(el => el.textContent.trim() && el.textContent !== previous), before);
      assert(await status.isVisible());
      assert.equal(await filter.evaluate(el => el.selectedOptions[0]?.textContent.trim()), 'Pending');
      assert.equal(await row('t1').count(), 1);
      assert.equal(await button.count(), 1);
      await page.waitForTimeout(1200);
      assert.equal(await state('t1'), false, 'State changed before user retry');
      await screenshot('503-retained-390.png');
      await postResponse(button, 200);
      assert.equal(await state('t1'), true);
      await page.waitForFunction(() => !document.querySelector('#entries')?.textContent.includes('t1'));
      return { first: 503, retry: 200, manual: true };
    });
    await check('reviewed filter, reload and reopen', async () => {
      await filter.selectOption({ label: 'Reviewed' });
      await row('t1').waitFor({ state: 'visible' });
      assert.equal(await row('t1').count(), 1);
      assert.equal(await row('t1').getByRole('button', { name: /^Return to pending$/i }).count(), 1);
      await page.reload({ waitUntil: 'networkidle' });
      await page.getByLabel(/Review status/i).selectOption({ label: 'Reviewed' });
      await row('t1').waitFor({ state: 'visible' });
      assert.equal(await row('t1').count(), 1);
      await postResponse(row('t1').getByRole('button', { name: /^Return to pending$/i }), 200);
      assert.equal(await state('t1'), false);
      await page.getByLabel(/Review status/i).selectOption({ label: 'Pending' });
      await row('t1').waitFor({ state: 'visible' });
      assert.equal(await row('t1').count(), 1);
      await screenshot('reopened-390.png');
      return { reload: true, reopened: true };
    });
    await check('wide viewport, stored text and original controls', async () => {
      await page.setViewportSize({ width: 1280, height: 800 });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      const action = row('t2').getByRole('button', { name: /^Mark reviewed$/i });
      const box = await action.boundingBox();
      assert(box && box.width > 0 && box.height > 0 && box.x >= 0 && box.x + box.width <= 1281);
      await action.click({ trial: true });
      assert.equal(await page.locator('#entry-form').count(), 1);
      assert.equal(await page.getByRole('button', { name: /^Import$/i }).count(), 1);
      assert.equal(await page.getByRole('link', { name: /^Export CSV$/i }).count(), 1);
      const probe = { id: 'review-markup-probe', project: '<img src=x onerror="window.__reviewXss=1">',
        minutes: 0, date: '2026-09-04' };
      const create = await context.request.post(new URL('/api/entries', url).href, { data: probe });
      assert.equal(create.status(), 201);
      await page.reload({ waitUntil: 'networkidle' });
      const item = row(probe.id);
      assert.equal(await item.count(), 1);
      assert.equal(await item.locator('img').count(), 0);
      assert.equal(await page.evaluate(() => window.__reviewXss === 1), false);
      assert((await item.innerText()).includes(probe.project));
      await screenshot('wide-1280.png');
      return { actionBox: box, storedTextInert: true };
    });
    await check('console and network have only expected failures', async () => {
      assert.deepEqual(report.pageErrors, []);
      assert.deepEqual(report.failedRequests, []);
      const unexpectedConsole = report.console.filter(item => item.type === 'error' &&
        !/^Failed to load resource: the server responded with a status of 503/.test(item.text));
      assert.deepEqual(unexpectedConsole, []);
      const unexpected = report.network.filter(item => item.status >= 400 &&
        !(item.status === 503 && item.path === '/api/review') &&
        !(item.status === 404 && item.path === '/favicon.ico'));
      assert.deepEqual(unexpected, []);
      return { responses: report.network.length };
    });
    report.pass = true;
  } catch (error) {
    report.error = error.stack;
    if (page && output) await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
  } finally {
    if (ownsMarker) await fs.unlink(marker).catch(error => { if (error.code !== 'ENOENT') report.cleanupError = error.message; });
    if (context && output) await context.tracing.stop({ path: path.join(output, 'trace.zip') }).catch(() => {});
    if (browser) await browser.close().catch(() => {});
    if (output) await fs.writeFile(path.join(output, 'browser-report.json'), JSON.stringify(report, null, 2));
  }
  console.log(JSON.stringify({ pass: report.pass, report: output && path.join(output, 'browser-report.json'), error: report.error }));
  process.exitCode = report.pass ? 0 : browser ? 1 : 2;
}
