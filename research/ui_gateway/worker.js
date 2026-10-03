// Secretless browser worker. The container receives page bytes, never host paths.
const readline = require('node:readline');
const {chromium} = require('playwright-core');

const URL = 'http://candidate.invalid/index.html';
const MAX_HTML = 1024 * 1024;
const MAX_SNAPSHOT = 16 * 1024;
const MAX_SCREENSHOT = 2 * 1024 * 1024;
const KEYS = new Set(['ArrowLeft', 'ArrowRight', 'Home', 'End', 'Tab', 'Enter', 'Space']);
let html = null;

function fail(code) { return {ok: false, error: code}; }
function exact(value, keys) {
  return value && typeof value === 'object' && !Array.isArray(value) &&
    Object.keys(value).sort().join(',') === keys.slice().sort().join(',');
}

(async () => {
  const browser = await chromium.launch({
    executablePath: '/usr/bin/chromium-browser', headless: true,
    args: ['--disable-dev-shm-usage', '--disable-background-networking', '--no-first-run']
  });
  const context = await browser.newContext({acceptDownloads: false, serviceWorkers: 'block',
    viewport: {width: 900, height: 700}});
  let page = await context.newPage();
  context.on('page', opened => { if (opened !== page) opened.close().catch(() => {}); });
  page.on('dialog', dialog => dialog.dismiss().catch(() => {}));
  await context.route('**/*', route => {
    const request = route.request();
    if (html && request.url() === URL && request.isNavigationRequest() &&
        request.frame() === page.mainFrame()) {
      route.fulfill({status: 200, body: html, contentType: 'text/html; charset=utf-8',
        headers: {'content-security-policy': "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; frame-src 'none'; worker-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'",
          'x-content-type-options': 'nosniff'}}).catch(() => {});
    } else route.abort().catch(() => {});
  });
  const snapshot = async () => {
    if (page.isClosed() || page.url() !== URL) return fail('PAGE_LEFT_FIXED_ORIGIN');
    const value = await page.locator('body').ariaSnapshot({timeout: 3000});
    return value.length <= MAX_SNAPSHOT ? {ok: true, text: value} : fail('SNAPSHOT_LIMIT');
  };
  const run = async message => {
    if (!message || typeof message !== 'object' || Array.isArray(message)) return fail('BAD_REQUEST');
    if (message.op === 'open') {
      if (!exact(message, ['op', 'html_b64']) || typeof message.html_b64 !== 'string' ||
          message.html_b64.length > Math.ceil(MAX_HTML * 4 / 3) + 4 ||
          !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(message.html_b64))
        return fail('BAD_PAGE');
      const bytes = Buffer.from(message.html_b64, 'base64');
      if (bytes.length > MAX_HTML) return fail('PAGE_LIMIT');
      html = bytes;
      await page.goto(URL, {waitUntil: 'domcontentloaded', timeout: 5000});
      return snapshot();
    }
    if (html === null) return fail('PAGE_NOT_OPEN');
    if (message.op === 'snapshot' && exact(message, ['op'])) return snapshot();
    if (message.op === 'click' && exact(message, ['op', 'selector']) &&
        typeof message.selector === 'string' && message.selector.length <= 128) {
      if (page.url() !== URL) return fail('PAGE_LEFT_FIXED_ORIGIN');
      await page.locator(message.selector).first().click({timeout: 3000});
      return snapshot();
    }
    if (message.op === 'key' && exact(message, ['op', 'key']) && KEYS.has(message.key)) {
      if (page.url() !== URL) return fail('PAGE_LEFT_FIXED_ORIGIN');
      await page.keyboard.press(message.key);
      return snapshot();
    }
    if (message.op === 'resize' && exact(message, ['op', 'width', 'height']) &&
        Number.isInteger(message.width) && Number.isInteger(message.height) &&
        message.width >= 320 && message.width <= 1440 && message.height >= 240 && message.height <= 1200) {
      await page.setViewportSize({width: message.width, height: message.height});
      return snapshot();
    }
    if (message.op === 'screenshot' && exact(message, ['op'])) {
      if (page.url() !== URL) return fail('PAGE_LEFT_FIXED_ORIGIN');
      const png = await page.screenshot({type: 'png', timeout: 3000});
      return png.length <= MAX_SCREENSHOT ? {ok: true, image_b64: png.toString('base64')} : fail('SCREENSHOT_LIMIT');
    }
    return fail('UNSUPPORTED_ACTION');
  };
  process.stdout.write(JSON.stringify({ready: true}) + '\n');
  for await (const line of readline.createInterface({input: process.stdin, crlfDelay: Infinity})) {
    let result;
    try { result = await run(JSON.parse(line)); }
    catch (error) { console.error(error); result = fail('BROWSER_ACTION_FAILED'); }
    process.stdout.write(JSON.stringify(result) + '\n');
  }
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
