const fs = require('fs');
const http = require('http');
const path = require('path');
const { chromium } = require('playwright');

const baseUrl = process.env.PROTOTYPE_URL || 'http://127.0.0.1:4175';
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const outputDir = path.resolve('design/recipe-detail/screenshots/03-panel-resource-refinement');
const prototypeDir = path.resolve('design/recipe-detail/prototypes/03-panel-resource-refinement');
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
  await new Promise((resolve, reject) => server.once('error', reject).listen(4175, '127.0.0.1', resolve));
  return server;
}

let server;
let browser;

(async () => {
  server = await startStaticServer();
  browser = await chromium.launch({ headless: true, executablePath: edgePath });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const pageErrors = []; const consoleErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  await page.goto(baseUrl, { waitUntil: 'networkidle' });

  // A: horizontal actions begin at the title column.
  const coverA = await page.locator('.cover').boundingBox();
  const identityA = await page.locator('.identity').boundingBox();
  const actionsA = await page.locator('.identity .action-cluster').boundingBox();
  assert(actionsA && Math.abs(actionsA.x - identityA.x) < 2, 'A actions start at the title edge');
  assert(actionsA.x > coverA.x + 80, 'A remains offset from the cover edge');
  await screenshot(page, 'desktop-header-a-under-title-1440x900.png');

  // Corrected B: same controls stay horizontal and start at the cover edge.
  await select(page, '#placement-select', 'full-width');
  const coverB = await page.locator('.cover').boundingBox();
  const actionsB = await page.locator('.header-wide-actions .action-cluster').boundingBox();
  const reviewB = await page.locator('.review-status').boundingBox();
  const actionButtons = page.locator('.header-wide-actions button');
  const firstButton = await actionButtons.nth(0).boundingBox();
  const secondButton = await actionButtons.nth(1).boundingBox();
  assert(actionsB && Math.abs(actionsB.x - coverB.x) < 2, 'B actions start at the cover edge');
  assert(Math.abs(firstButton.y - secondButton.y) < 2, 'B actions remain one horizontal row');
  assert(reviewB && Math.abs(reviewB.x - coverB.x) < 2, 'B review status shares the cover-edge alignment');
  await screenshot(page, 'desktop-header-b-cover-edge-1440x900.png');

  // Import Info image rows are identifiable and preview inline.
  await page.getByRole('button', { name: 'Import info' }).click();
  let dialog = page.getByRole('dialog', { name: 'Import info' });
  await dialog.getByRole('heading', { name: 'Imported resources' }).scrollIntoViewIfNeeded();
  assert(await dialog.locator('.resource-thumbnail').count() === 5, 'every active image resource has a thumbnail');
  assert(await dialog.locator('.resource-child').filter({ hasText: 'Video transcript' }).first().locator('.resource-thumbnail').count() === 0, 'transcript does not get a fake thumbnail');
  await screenshot(page, 'desktop-import-image-thumbnails-1440x900.png');
  await dialog.getByRole('button', { name: 'Preview Aubergine browning reference' }).click();
  assert(await dialog.getByAltText('Expanded preview of Aubergine browning reference').count() === 1, 'thumbnail expands inside its resource row');
  await screenshot(page, 'desktop-import-inline-image-preview-1440x900.png');

  // Cascade warning remains inside the selected group and marks affected children.
  await dialog.getByRole('button', { name: 'Remove Instagram reel' }).click();
  const group = dialog.locator('.resource-group').filter({ hasText: 'Instagram reel' }).first();
  const confirm = group.getByRole('alertdialog', { name: 'Remove this link?' });
  assert(await confirm.count() === 1, 'cascade confirmation is inside the selected resource group');
  assert(await group.locator('.will-remove').count() === 5, 'all removable derived resources are marked');
  assert(await group.locator('.will-keep').count() === 1, 'current cover is separately protected');
  assert(await page.evaluate(() => document.activeElement?.textContent.trim() === 'Cancel'), 'safe Cancel action receives focus');
  const primaryBounds = await group.locator('.resource-primary').boundingBox();
  const confirmBounds = await confirm.boundingBox();
  assert(confirmBounds.y >= primaryBounds.y + primaryBounds.height - 2, 'confirmation sits directly below the primary row');
  await screenshot(page, 'desktop-import-inline-cascade-confirmation-1440x900.png');
  await page.keyboard.press('Escape');
  assert(await confirm.count() === 0, 'Escape cancels pending cascade removal without closing Import Info');
  assert(await dialog.count() === 1, 'Import Info remains open after cancelling removal');
  await dialog.getByRole('button', { name: 'Close Import info' }).click();

  // Focus has one shared auxiliary slot and preserves Media state while switching.
  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  await page.getByRole('button', { name: 'Media · 4' }).click();
  dialog = page.getByRole('dialog', { name: 'Cooking media · 4' });
  assert(await page.getByRole('dialog').count() === 1, 'only one auxiliary dialog is open');
  await dialog.locator('[data-media-index="1"]').click();
  await dialog.getByRole('button', { name: 'Expand' }).click();
  await dialog.evaluate(node => { node.scrollTop = 160; });
  await screenshot(page, 'desktop-focus-shared-slot-media-1440x900.png');
  await dialog.getByRole('button', { name: 'Import info' }).click();
  dialog = page.getByRole('dialog', { name: 'Import info' });
  assert(await page.getByRole('dialog').count() === 1, 'Import Info replaces Media in the same slot');
  const importScroll = await dialog.evaluate(node => { node.scrollTop = 420; return node.scrollTop; });
  assert(importScroll > 0, 'Import Info is scrollable in the desktop drawer');
  await screenshot(page, 'desktop-focus-shared-slot-import-1440x900.png');
  await dialog.getByRole('button', { name: 'Media · 4' }).click();
  dialog = page.getByRole('dialog', { name: 'Cooking media · 4' });
  assert(await dialog.getByRole('button', { name: 'Compact' }).count() === 1, 'Media expansion state survives panel switching');
  assert(await dialog.locator('[data-media-index="1"]').getAttribute('aria-pressed') === 'true', 'Media selection survives panel switching');

  // Switching panels cancels an armed destructive confirmation.
  await dialog.getByRole('button', { name: 'Import info' }).click();
  dialog = page.getByRole('dialog', { name: 'Import info' });
  await page.waitForTimeout(50);
  const restoredImportScroll = await dialog.evaluate(node => node.scrollTop);
  assert(Math.abs(restoredImportScroll - importScroll) < 5, `Import Info scroll survives panel switching (${importScroll} → ${restoredImportScroll})`);
  await dialog.getByRole('button', { name: 'Remove Instagram reel' }).scrollIntoViewIfNeeded();
  await dialog.getByRole('button', { name: 'Remove Instagram reel' }).click();
  assert(await dialog.getByRole('alertdialog', { name: 'Remove this link?' }).count() === 1, 'removal is armed before switching');
  await dialog.getByRole('button', { name: 'Media · 4' }).click();
  await page.getByRole('dialog', { name: 'Cooking media · 4' }).getByRole('button', { name: 'Import info' }).click();
  dialog = page.getByRole('dialog', { name: 'Import info' });
  assert(await dialog.getByRole('alertdialog', { name: 'Remove this link?' }).count() === 0, 'panel switching cancels unconfirmed deletion');
  await dialog.getByRole('button', { name: 'Close Import info' }).click();

  // Tablet and mobile retain one modal slot and do not overflow.
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.getByRole('button', { name: 'Media · 4' }).click();
  dialog = page.getByRole('dialog', { name: 'Cooking media · 4' });
  assert(await dialog.getAttribute('aria-modal') === 'true', 'tablet auxiliary slot is modal');
  await dialog.getByRole('button', { name: 'Import info' }).click();
  assert(await page.getByRole('dialog', { name: 'Import info' }).count() === 1, 'tablet switches content without stacking');
  await screenshot(page, 'tablet-focus-shared-slot-import-1024x768.png');
  await page.getByRole('dialog').getByRole('button', { name: 'Close Import info' }).click();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Media · 4' }).click();
  dialog = page.getByRole('dialog', { name: 'Cooking media · 4' });
  await dialog.getByRole('button', { name: 'Import info' }).click();
  assert(await page.getByRole('dialog').count() === 1, 'mobile bottom sheet also has one auxiliary slot');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'mobile has no horizontal overflow');
  await screenshot(page, 'mobile-focus-shared-slot-import-390x844.png');

  assert(pageErrors.length === 0, `no page errors: ${pageErrors.join(' | ')}`);
  assert(consoleErrors.length === 0, `no console errors: ${consoleErrors.join(' | ')}`);
  console.log('PANEL_RESOURCE_REFINEMENT_CHECKS_PASS');
  console.log('Screenshots:', fs.readdirSync(outputDir).sort().join(', '));
  await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
})().catch(async error => {
  console.error(error.stack || error);
  if (browser) await browser.close().catch(() => {});
  if (server) await new Promise(resolve => server.close(resolve));
  process.exitCode = 1;
});
