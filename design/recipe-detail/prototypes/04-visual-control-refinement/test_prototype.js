const fs = require('fs');
const http = require('http');
const path = require('path');
const { chromium } = require('playwright');

const baseUrl = process.env.PROTOTYPE_URL || 'http://127.0.0.1:4176';
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const outputDir = path.resolve('design/recipe-detail/screenshots/04-visual-control-refinement');
const prototypeDir = path.resolve('design/recipe-detail/prototypes/04-visual-control-refinement');
fs.mkdirSync(outputDir, { recursive: true });

function assert(condition, message) { if (!condition) throw new Error(`Assertion failed: ${message}`); }
async function select(page, selector, value) { await page.selectOption(selector, value); await page.waitForTimeout(40); }
async function screenshot(page, name) {
  await page.evaluate(() => document.body.classList.add('capture-mode'));
  await page.screenshot({ path: path.join(outputDir, name) });
  await page.evaluate(() => document.body.classList.remove('capture-mode'));
}
async function startStaticServer() {
  if (process.env.PROTOTYPE_URL) return null;
  const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml' };
  const server = http.createServer((request, response) => {
    const relative = request.url === '/' ? 'index.html' : request.url.split('?')[0].replace(/^\//, '');
    const filePath = path.resolve(prototypeDir, relative);
    if (!filePath.startsWith(prototypeDir + path.sep) && filePath !== path.join(prototypeDir, 'index.html')) { response.writeHead(403).end('Forbidden'); return; }
    fs.readFile(filePath, (error, data) => {
      if (error) { response.writeHead(404).end('Not found'); return; }
      response.writeHead(200, { 'Content-Type': types[path.extname(filePath)] || 'application/octet-stream' }); response.end(data);
    });
  });
  await new Promise((resolve, reject) => server.once('error', reject).listen(4176, '127.0.0.1', resolve));
  return server;
}

let server; let browser;
(async () => {
  server = await startStaticServer();
  browser = await chromium.launch({ headless: true, executablePath: edgePath });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const pageErrors = []; const consoleErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  await page.goto(baseUrl, { waitUntil: 'networkidle' });

  // Fair A/B comparison: same compact warning width, alignment only changes.
  const identity = await page.locator('.identity').boundingBox();
  const cover = await page.locator('.cover').boundingBox();
  const warningA = await page.locator('.review-status').boundingBox();
  assert(Math.abs(warningA.x - identity.x) < 2, 'A warning starts at title edge');
  assert(warningA.width <= 622, 'A warning remains compact');
  await screenshot(page, 'desktop-flagged-a-under-title-1440x900.png');
  await select(page, '#placement-select', 'full-width');
  const warningB = await page.locator('.review-status').boundingBox();
  assert(Math.abs(warningB.x - cover.x) < 2, 'B warning starts at cover edge');
  assert(Math.abs(warningB.width - warningA.width) < 2, 'A and B use identical warning width');
  await screenshot(page, 'desktop-flagged-b-cover-edge-1440x900.png');

  // Long-title/no-cover stress keeps both variants available.
  await page.setViewportSize({ width: 1024, height: 768 });
  await select(page, '#scenario-select', 'long');
  await select(page, '#placement-select', 'under-title');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'long-title A has no horizontal overflow');
  await screenshot(page, 'tablet-long-title-a-1024x768.png');
  await select(page, '#placement-select', 'full-width');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'long-title B has no horizontal overflow');
  await screenshot(page, 'tablet-long-title-b-1024x768.png');

  // Resource controls use distinct icons and stable consequence alignment.
  await page.setViewportSize({ width: 1440, height: 900 });
  await select(page, '#scenario-select', 'flagged');
  await page.getByRole('button', { name: 'Import info' }).click();
  let dialog = page.getByRole('dialog', { name: 'Import info' });
  await dialog.getByRole('heading', { name: 'Imported resources' }).scrollIntoViewIfNeeded();
  const trash = dialog.getByRole('button', { name: 'Remove Aubergine browning reference' });
  const trashBounds = await trash.boundingBox();
  assert(trashBounds.width >= 40 && trashBounds.height >= 40, 'trash icon has a usable hit target');
  assert((await trash.innerText()).trim() === '', 'resource removal is an icon, not a cross character');
  await dialog.getByRole('button', { name: 'Preview Aubergine browning reference' }).click();
  const closePreview = dialog.getByRole('button', { name: 'Close preview of Aubergine browning reference' });
  const closeBounds = await closePreview.boundingBox();
  assert(closeBounds.width === 40 && closeBounds.height === 40, 'preview close uses a compact icon target');
  assert((await closePreview.innerText()).trim() === '', 'preview close has no oversized text label');
  await screenshot(page, 'desktop-resource-icons-and-preview-1440x900.png');

  await dialog.getByRole('button', { name: 'Remove Instagram reel' }).click();
  const confirm = dialog.getByRole('alertdialog', { name: 'Remove this link?' });
  assert(await confirm.getByText('Your saved recipe will not change.', { exact: false }).count() === 1, 'cascade copy protects the saved recipe explicitly');
  assert(await confirm.getByText(/Only this source and 5 related imported resources/).count() === 1, 'cascade copy limits the destructive scope');
  const consequences = dialog.locator('.resource-group.pending-removal .resource-consequence');
  assert(await consequences.count() === 6, 'every derived row has one consequence label');
  const rightEdges = await consequences.evaluateAll(nodes => nodes.map(node => { const box = node.getBoundingClientRect(); return Math.round(box.right); }));
  assert(Math.max(...rightEdges) - Math.min(...rightEdges) <= 2, 'all consequence labels share one right edge');
  await screenshot(page, 'desktop-cascade-recipe-unchanged-1440x900.png');
  await page.keyboard.press('Escape');
  await dialog.getByRole('button', { name: 'Close Import info' }).click();

  // Media is the common task: equal-width drawer, images plus external links, no Compact or persistent tabs.
  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  await page.getByRole('button', { name: 'Media · 6' }).click();
  dialog = page.getByRole('dialog', { name: 'Cooking media · 6' });
  const mediaWidth = (await dialog.boundingBox()).width;
  assert(await dialog.getByRole('button', { name: /Compact|Expand/ }).count() === 0, 'Media has no ambiguous Compact or Expand action');
  assert(await dialog.locator('.panel-switcher').count() === 0, 'Media has no persistent Import Info tab');
  assert(await dialog.getByRole('heading', { name: 'Images · 4' }).count() === 1, 'Media separates images');
  assert(await dialog.getByRole('heading', { name: 'Videos & links · 2' }).count() === 1, 'Media separates external references');
  const externalLinks = dialog.locator('a.media-link');
  assert(await externalLinks.count() === 2, 'two cooking links are available');
  assert(await externalLinks.first().getAttribute('target') === '_blank', 'external cooking link opens separately');
  assert((await externalLinks.first().getAttribute('rel')).includes('noopener'), 'external cooking link uses safe rel');
  await dialog.locator('[data-media-index="1"]').click();
  await screenshot(page, 'desktop-media-images-and-links-1440x900.png');

  // Rare transition is in overflow; Import Info receives contextual Back only on this path.
  await dialog.getByRole('button', { name: 'More media actions' }).click();
  assert(await dialog.getByRole('menuitem', { name: 'Import info' }).count() === 1, 'rare Import Info action lives in Media overflow');
  await dialog.getByRole('menuitem', { name: 'Import info' }).click();
  dialog = page.getByRole('dialog', { name: 'Import info' });
  const contextualImportWidth = (await dialog.boundingBox()).width;
  assert(Math.abs(contextualImportWidth - mediaWidth) < 2, 'Media and Import Info use the same desktop width');
  assert(await dialog.getByRole('button', { name: 'Back to media' }).count() === 1, 'contextual Import Info can return to Media');
  assert(await page.getByRole('dialog').count() === 1, 'panel replacement never stacks dialogs');
  await screenshot(page, 'desktop-contextual-import-back-to-media-1440x900.png');
  await dialog.getByRole('button', { name: 'Back to media' }).click();
  dialog = page.getByRole('dialog', { name: 'Cooking media · 6' });
  assert(await dialog.locator('[data-media-index="1"]').getAttribute('aria-pressed') === 'true', 'Media selection survives contextual Import Info');
  await dialog.getByRole('button', { name: 'Close' }).click();

  // Direct Import Info remains single-purpose and has no artificial Media navigation.
  await page.getByRole('button', { name: 'Import info' }).click();
  dialog = page.getByRole('dialog', { name: 'Import info' });
  assert(await dialog.getByRole('button', { name: 'Back to media' }).count() === 0, 'direct Import Info has no Back to media');
  assert(Math.abs((await dialog.boundingBox()).width - mediaWidth) < 2, 'direct Import Info keeps the same drawer width');
  await dialog.getByRole('button', { name: 'Close Import info' }).click();

  // Tablet contextual replacement and mobile direct path retain one modal sheet without overflow.
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.getByRole('button', { name: 'Media · 6' }).click();
  dialog = page.getByRole('dialog', { name: 'Cooking media · 6' });
  await dialog.getByRole('button', { name: 'More media actions' }).click();
  await dialog.getByRole('menuitem', { name: 'Import info' }).click();
  dialog = page.getByRole('dialog', { name: 'Import info' });
  assert(await dialog.getAttribute('aria-modal') === 'true', 'tablet contextual Import Info is modal');
  assert(await dialog.getByRole('button', { name: 'Back to media' }).count() === 1, 'tablet keeps contextual return');
  await screenshot(page, 'tablet-contextual-import-1024x768.png');
  await dialog.getByRole('button', { name: 'Close Import info' }).click();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Media · 6' }).click();
  dialog = page.getByRole('dialog', { name: 'Cooking media · 6' });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'mobile Media has no horizontal overflow');
  await screenshot(page, 'mobile-media-images-and-links-390x844.png');
  await dialog.getByRole('button', { name: 'Close' }).click();

  assert(pageErrors.length === 0, `no page errors: ${pageErrors.join(' | ')}`);
  assert(consoleErrors.length === 0, `no console errors: ${consoleErrors.join(' | ')}`);
  console.log('VISUAL_CONTROL_REFINEMENT_CHECKS_PASS');
  console.log('Screenshots:', fs.readdirSync(outputDir).sort().join(', '));
  await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
})().catch(async error => {
  console.error(error.stack || error);
  if (browser) await browser.close().catch(() => {});
  if (server) await new Promise(resolve => server.close(resolve));
  process.exitCode = 1;
});
