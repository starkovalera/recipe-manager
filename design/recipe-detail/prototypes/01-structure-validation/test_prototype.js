const fs = require('fs');
const http = require('http');
const path = require('path');
const { chromium } = require('playwright');

const baseUrl = process.env.PROTOTYPE_URL || 'http://127.0.0.1:4173';
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const outputDir = path.resolve('design/recipe-detail/screenshots/01-structure-validation');
const prototypeDir = path.resolve('design/recipe-detail/prototypes/01-structure-validation');
fs.mkdirSync(outputDir, { recursive: true });

function assert(condition, message) {
  if (!condition) throw new Error(`Assertion failed: ${message}`);
}

async function select(page, selector, value) {
  await page.selectOption(selector, value);
  await page.waitForTimeout(30);
}

async function screenshot(page, name, fullPage = false) {
  await page.evaluate(() => document.body.classList.add('capture-mode'));
  await page.screenshot({ path: path.join(outputDir, name), fullPage });
  await page.evaluate(() => document.body.classList.remove('capture-mode'));
}

async function startStaticServer() {
  if (process.env.PROTOTYPE_URL) return null;
  const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8' };
  const server = http.createServer((request, response) => {
    const relative = request.url === '/' ? 'index.html' : request.url.split('?')[0].replace(/^\//, '');
    const filePath = path.resolve(prototypeDir, relative);
    if (!filePath.startsWith(prototypeDir + path.sep) && filePath !== path.join(prototypeDir, 'index.html')) {
      response.writeHead(403).end('Forbidden'); return;
    }
    fs.readFile(filePath, (error, body) => {
      if (error) { response.writeHead(404).end('Not found'); return; }
      response.writeHead(200, { 'Content-Type': types[path.extname(filePath)] || 'application/octet-stream' });
      response.end(body);
    });
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(4173, '127.0.0.1', resolve);
  });
  return server;
}

let browser;
let staticServer;
(async () => {
  staticServer = await startStaticServer();
  browser = await chromium.launch({ headless: true, executablePath: edgePath });
  const consoleErrors = [];
  const pageErrors = [];
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  page.on('pageerror', error => pageErrors.push(error.message));

  await page.goto(baseUrl, { waitUntil: 'networkidle' });

  // Normal imported recipe: no review status, neutral Import Info, approved B2 order.
  assert(await page.getByRole('heading', { name: 'Smoky Tomato & Butter Bean Stew' }).count() === 1, 'normal recipe title renders');
  assert(await page.getByText('imported details need review').count() === 0, 'normal imported recipe has no review status');
  assert(await page.getByRole('button', { name: 'Import info' }).count() === 1, 'normal imported recipe exposes Import Info');
  const metadataLabels = await page.locator('.secondary-meta .meta-label').allTextContents();
  assert(metadataLabels.join('|') === 'Difficulty · Personal rating|Collections|Tags', 'approved B2 metadata order is preserved');
  await screenshot(page, 'desktop-normal-1440x900.png');

  // Flagged imported recipe: status in Default View and explicit Import Info navigation/return.
  await select(page, '#scenario-select', 'flagged');
  assert(await page.getByText('3 imported details need review', { exact: true }).count() === 1, 'flagged status appears in Default View');
  await page.getByRole('button', { name: 'Review import' }).click();
  assert(await page.getByRole('heading', { name: 'Review imported recipe' }).count() === 1, 'status links to Import Info');
  assert(await page.getByText('Cooking time conflicts').count() === 1, 'detailed flag remains in Import Info');
  await page.getByRole('button', { name: 'View recipe' }).click();
  assert(await page.getByText('3 imported details need review', { exact: true }).count() === 1, 'return restores Default View');

  // Manual recipe: no Import Info entry point.
  await select(page, '#scenario-select', 'manual');
  assert(await page.getByRole('button', { name: 'Import info' }).count() === 0, 'manual recipe omits Import Info');

  // Dense state: fixed visible names, +N disclosure, focus returns to disclosure trigger.
  await select(page, '#scenario-select', 'dense');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'dense mobile state has no horizontal overflow');
  assert(await page.getByRole('button', { name: '+48 more tags' }).count() === 1, 'dense tags collapse to +48');
  assert(await page.getByRole('button', { name: '+18 more collections' }).count() === 1, 'dense collections collapse to +18');
  const tagTrigger = page.getByRole('button', { name: '+48 more tags' });
  await tagTrigger.click();
  assert(await page.getByRole('dialog', { name: 'All tags' }).count() === 1, 'tag disclosure opens a named dialog');
  await page.getByRole('button', { name: 'Close' }).click();
  assert(await tagTrigger.evaluate(node => document.activeElement === node), 'focus returns to tag disclosure trigger');
  await screenshot(page, 'desktop-dense-flagged-1440x900.png');

  // Long content counts and stable sequential structure.
  await select(page, '#scenario-select', 'long');
  assert(await page.getByText('48 items').count() === 1, 'long state includes 48 ingredients');
  assert(await page.getByText('38 steps').count() === 1, 'long state includes 38 steps');
  await screenshot(page, 'desktop-long-content-full-page.png', true);
  await select(page, '#view-select', 'cooking');
  await page.getByRole('button', { name: /Media · 4/ }).click();
  assert(await page.getByRole('dialog', { name: /Cooking media/ }).getAttribute('aria-modal') === 'false', 'desktop media drawer is nonmodal');
  await screenshot(page, 'desktop-cooking-media-drawer-1440x900.png');
  await page.getByRole('button', { name: 'Close' }).click();
  await select(page, '#view-select', 'default');

  // Error-state coverage.
  await select(page, '#scenario-select', 'failed');
  assert(await page.getByRole('heading', { name: 'Recipe failed to load' }).count() === 1, 'failed-load state renders');
  await select(page, '#scenario-select', 'missing');
  assert(await page.getByRole('heading', { name: 'Recipe not found' }).count() === 1, 'missing state renders');

  // Tablet Import Info, lifecycle action error, and role-gated debug detail.
  await page.setViewportSize({ width: 1024, height: 768 });
  await select(page, '#scenario-select', 'long');
  await select(page, '#view-select', 'cooking');
  await page.getByRole('button', { name: /Media · 4/ }).click();
  await screenshot(page, 'tablet-cooking-media-drawer-1024x768.png');
  await page.getByRole('button', { name: 'Close' }).click();
  await select(page, '#scenario-select', 'flagged');
  await select(page, '#view-select', 'import');
  await select(page, '#role-select', 'debug');
  assert(await page.getByRole('heading', { name: 'Eligible debug detail' }).count() === 1, 'debug detail is role-gated and visible to eligible role');
  await page.getByRole('button', { name: 'Restore' }).click();
  assert(await page.getByRole('alert').getByText('Restore failed').count() === 1, 'failed resource action stays in Import Info');
  await page.evaluate(() => window.scrollTo(0, 0));
  await screenshot(page, 'tablet-import-info-debug-1024x768.png');

  // Mobile normal and dense header order.
  await page.setViewportSize({ width: 390, height: 844 });
  await select(page, '#role-select', 'user');
  await select(page, '#scenario-select', 'normal');
  await screenshot(page, 'mobile-normal-390x844.png');
  await select(page, '#scenario-select', 'dense');
  const statusBox = page.locator('.review-status');
  const secondary = page.locator('.secondary-meta');
  assert(await statusBox.evaluate((node, other) => node.compareDocumentPosition(document.querySelector(other)) & Node.DOCUMENT_POSITION_FOLLOWING, '.secondary-meta'), 'mobile DOM places review status before secondary metadata');
  await screenshot(page, 'mobile-dense-flagged-390x844.png');

  // Cooking Focus state survives mobile tab switching and media sheet open/close.
  await select(page, '#scenario-select', 'long');
  await select(page, '#view-select', 'cooking');
  const ingredientCheck = page.locator('[data-check="ingredient"]').first();
  await ingredientCheck.check();
  await page.getByRole('tab', { name: 'Instructions' }).click();
  const stepCheck = page.locator('[data-check="step"]').first();
  await stepCheck.check();
  await page.getByRole('button', { name: /Media · 4/ }).click();
  assert(await page.getByRole('dialog', { name: /Cooking media/ }).count() === 1, 'mobile media opens as explicit layer');
  assert(await page.getByRole('dialog', { name: /Cooking media/ }).getAttribute('aria-modal') === 'true', 'mobile media sheet is modal');
  assert(await page.locator('#prototype-root').evaluate(node => node.inert), 'mobile media sheet makes background content inert');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'mobile media sheet has no horizontal overflow');
  await screenshot(page, 'mobile-cooking-media-sheet-390x844.png');
  await page.getByRole('button', { name: 'Close' }).click();
  assert(!await page.locator('#prototype-root').evaluate(node => node.inert), 'closing mobile media restores background interactivity');
  await page.getByRole('tab', { name: 'Ingredients' }).click();
  assert(await page.locator('[data-check="ingredient"]').first().isChecked(), 'ingredient check survives media and tab transitions');
  await page.getByRole('tab', { name: 'Instructions' }).click();
  assert(await page.locator('[data-check="step"]').first().isChecked(), 'step completion survives media and tab transitions');

  assert(pageErrors.length === 0, `no page errors: ${pageErrors.join(' | ')}`);
  assert(consoleErrors.length === 0, `no console errors: ${consoleErrors.join(' | ')}`);
  console.log('PROTOTYPE_BROWSER_CHECKS_PASS');
  console.log('Screenshots:', fs.readdirSync(outputDir).sort().join(', '));
  await browser.close();
  if (staticServer) await new Promise(resolve => staticServer.close(resolve));
})().catch(async error => {
  console.error(error.stack || error);
  if (browser) await browser.close().catch(() => {});
  if (staticServer) await new Promise(resolve => staticServer.close(resolve));
  process.exit(1);
});
