#!/usr/bin/env node
// Development regression only. The sealed holdout uses a separate oracle.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { pathToFileURL } from 'node:url';

const [base, output] = process.argv.slice(2);
if (!base || !output || new URL(base).hostname !== '127.0.0.1') {
  throw new Error('Use a loopback application URL and a private evidence directory');
}
await fs.mkdir(output, { recursive: true });
const modulePath = path.join(os.homedir(), 'Library/Application Support/LocalAI/browser/node_modules/playwright/index.mjs');
const { chromium } = await import(pathToFileURL(modulePath).href);
const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
const result = { pass: false, checks: [], errors };
const check = async (name, fn) => {
  await fn();
  result.checks.push(name);
};
const rows = async () => {
  const response = await context.request.get(base + 'api/entries');
  assert.equal(response.status(), 200);
  return response.json();
};
const form = page.locator('#entry-form');
const save = form.getByRole('button', { name: /^Save$/i });
const cancel = form.getByRole('button', { name: /^Cancel Edit$/i });
const edit = id => page.locator('#entries > *').filter({ hasText: id }).getByRole('button', { name: /^Edit$/i });
try {
  await page.goto(base, { waitUntil: 'networkidle' });
  await check('Cancel Edit absent outside edit mode', async () => {
    assert.equal(await cancel.isVisible().catch(() => false), false);
    assert.equal(await save.isVisible(), true);
  });
  const before = await rows();
  const original = before.find(row => row.id === 't1');
  assert(original);
  await check('Edit is an accessible control and populates exact stored data', async () => {
    assert.equal(await edit('t1').isVisible(), true);
    await edit('t1').click();
    assert.equal(await cancel.isVisible(), true);
    assert.equal(await form.locator('[name="id"]').inputValue(), original.id);
    assert.equal(await form.locator('[name="project"]').inputValue(), original.project);
  });
  await check('Cancel leaves the stored row intact and restores create form', async () => {
    await cancel.click();
    assert.deepEqual(await rows(), before);
    for (const name of ['id', 'project', 'minutes', 'date']) {
      assert.equal(await form.locator(`[name="${name}"]`).inputValue(), '');
    }
    assert.equal(await save.isVisible(), true);
    assert.equal(await cancel.isVisible().catch(() => false), false);
  });
  await check('Save after Cancel creates once and persists through reload', async () => {
    const created = { id: 'after-cancel-probe', project: 'new-project', minutes: 7, date: '2026-09-05' };
    for (const [key, value] of Object.entries(created)) {
      await form.locator(`[name="${key}"]`).fill(String(value));
    }
    const [response] = await Promise.all([
      page.waitForResponse(response => response.request().method() === 'POST' &&
        new URL(response.url()).pathname === '/api/entries'),
      save.click(),
    ]);
    assert.equal(response.status(), 201);
    assert.equal((await rows()).filter(row => row.id === created.id).length, 1);
    await page.reload({ waitUntil: 'networkidle' });
    assert.equal(await page.locator('#entries > *').filter({ hasText: created.id }).count(), 1);
  });
  await check('Edit keeps hyphenated project text intact', async () => {
    const tricky = { id: 'hyphen-probe', project: 'alpha-beta', minutes: 3, date: '2026-09-06' };
    const response = await context.request.post(base + 'api/entries', { data: tricky });
    assert.equal(response.status(), 201);
    await page.reload({ waitUntil: 'networkidle' });
    assert.equal(await edit(tricky.id).isVisible(), true);
    await edit(tricky.id).click();
    assert.equal(await form.locator('[name="project"]').inputValue(), tricky.project);
    await cancel.click();
    assert.deepEqual((await rows()).find(row => row.id === tricky.id), tricky);
  });
  assert.deepEqual(errors, []);
  result.pass = true;
} catch (error) {
  result.failure = error.message;
  await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
} finally {
  await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(result, null, 2) + '\n');
  await browser.close();
}
console.log(JSON.stringify(result));
process.exitCode = result.pass ? 0 : 1;
