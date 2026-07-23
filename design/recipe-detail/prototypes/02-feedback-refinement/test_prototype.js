const fs = require('fs');
const http = require('http');
const path = require('path');
const { chromium } = require('playwright');

const baseUrl = process.env.PROTOTYPE_URL || 'http://127.0.0.1:4174';
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const outputDir = path.resolve('design/recipe-detail/screenshots/02-feedback-refinement');
const prototypeDir = path.resolve('design/recipe-detail/prototypes/02-feedback-refinement');
fs.mkdirSync(outputDir, { recursive: true });

function assert(condition, message) { if (!condition) throw new Error(`Assertion failed: ${message}`); }
async function select(page, selector, value) { await page.selectOption(selector, value); await page.waitForTimeout(30); }
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
    if (!filePath.startsWith(prototypeDir + path.sep) && filePath !== path.join(prototypeDir, 'index.html')) { response.writeHead(403).end('Forbidden'); return; }
    fs.readFile(filePath, (error, body) => {
      if (error) { response.writeHead(404).end('Not found'); return; }
      response.writeHead(200, { 'Content-Type': types[path.extname(filePath)] || 'application/octet-stream' }); response.end(body);
    });
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(4174, '127.0.0.1', resolve); });
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

  // Compact flagged Default View and split metadata rows.
  assert(await page.getByRole('heading', { name: 'Smoky Tomato & Butter Bean Stew' }).count() === 1, 'flagged recipe renders by default');
  assert(await page.locator('.source-meta').innerText() === 'Instagram video · Marta Cooks', 'source identity uses its own row');
  assert(await page.locator('.cooking-meta').innerText() === '45 min · 4 servings', 'cooking facts use their own row');
  const statusBox = page.locator('.review-status');
  const statusBounds = await statusBox.boundingBox();
  assert(statusBounds.width <= 650, 'review status is compact rather than full-width');
  assert(await page.getByRole('button', { name: 'View', exact: true }).isDisabled(), 'View is active in mode switch');
  assert(await page.getByRole('button', { name: 'Focus', exact: true }).count() === 1, 'Focus is directly available');
  assert(await page.getByRole('button', { name: 'Edit', exact: true }).count() === 1, 'Edit is directly available');
  await screenshot(page, 'desktop-default-actions-under-title-1440x900.png');

  // Controlled action-placement variant.
  await select(page, '#placement-select', 'under-cover');
  assert(await page.locator('.cover-stack .action-cluster').count() === 1, 'action cluster moves beneath cover');
  assert(await page.locator('.identity .action-cluster').count() === 0, 'identity no longer owns actions in under-cover variant');
  const underCoverMeta = await page.locator('.secondary-meta').boundingBox();
  assert(underCoverMeta && underCoverMeta.x + underCoverMeta.width <= 1440, 'under-cover variant keeps organization metadata in view');
  await screenshot(page, 'desktop-default-actions-under-cover-1440x900.png');

  // Long content is initially bounded and independently expandable.
  await select(page, '#scenario-select', 'long');
  assert(await page.getByRole('button', { name: 'Show all 48' }).count() === 1, 'Ingredients collapse after 12');
  assert(await page.getByRole('button', { name: 'Show all 38' }).count() === 1, 'Instructions collapse after 8');
  assert(await page.getByRole('button', { name: 'Show full note' }).count() === 1, 'Notes clamp with explicit expansion');
  await screenshot(page, 'desktop-long-content-collapsed-1440x900.png');
  await page.getByRole('button', { name: 'Show all 48' }).click();
  await page.getByRole('button', { name: 'Show all 38' }).click();
  await page.getByRole('button', { name: 'Show full note' }).click();
  assert(await page.getByRole('button', { name: 'Show first 12' }).count() === 1, 'Ingredients can collapse again');
  await screenshot(page, 'desktop-long-content-expanded-full-page.png', true);

  // Focus is simplified: no checks/scaling, direct mode and Import Info access.
  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  assert(await page.locator('input[type="checkbox"]').count() === 0, 'Focus has no checkboxes');
  assert(await page.getByLabel('Portion scaling').count() === 0, 'Focus has no portion multiplier');
  assert(await page.getByRole('button', { name: 'View', exact: true }).count() === 1, 'Focus can return directly to View');
  assert(await page.getByRole('button', { name: 'Edit', exact: true }).count() === 1, 'Focus can enter Edit directly');
  assert(await page.getByRole('button', { name: 'Import info' }).count() === 1, 'Focus can open Import Info directly');
  await screenshot(page, 'desktop-focus-simplified-1440x900.png');

  // Wide desktop Import Info reflows context and contains only flags/resources/debug.
  await select(page, '#scenario-select', 'flagged');
  await page.getByRole('button', { name: 'Import info' }).click();
  const importDialog = page.getByRole('dialog', { name: 'Import info' });
  assert(await importDialog.getAttribute('aria-modal') === 'false', 'wide desktop Import Info is nonmodal');
  assert(await page.locator('#prototype-root').evaluate(node => !node.inert), 'wide desktop context remains interactive');
  assert(await page.evaluate(() => document.body.classList.contains('wide-drawer-open')), 'wide desktop drawer reallocates width');
  assert(await page.getByText('Extracted result').count() === 0, 'drawer omits duplicated extracted recipe');
  assert(await page.getByText('Provenance').count() === 0, 'drawer omits Provenance');
  assert(await page.getByText('Original source').count() === 0, 'drawer omits Original source');
  assert(await page.getByText('Review needed · 3').count() === 1, 'all general flags appear in one section');
  assert(await page.locator('.resource-group').count() === 3, 'primary resources render as groups');
  assert(await page.locator('.resource-children .resource-child').count() === 6, 'derived resources render beneath primary link');
  assert(await page.getByText('Kept as cover').count() === 1, 'current cover is protected');
  assert(await page.getByRole('button', { name: 'Remove Finished traybake' }).count() === 0, 'current cover has no remove action');
  await screenshot(page, 'desktop-import-resource-groups-1440x900.png');

  // General flags clear only in bulk.
  assert(await page.locator('.flag-list button').count() === 0, 'flags have no per-flag actions');
  await page.getByRole('button', { name: 'Mark all reviewed' }).click();
  assert(await page.getByRole('alertdialog', { name: 'Mark all flags as reviewed?' }).count() === 1, 'bulk review confirmation explains impact');
  assert(await page.getByText('Recipe content and imported resources will not change.').count() === 1, 'bulk review does not imply content edits');
  await page.getByRole('alertdialog', { name: 'Mark all flags as reviewed?' }).getByRole('button', { name: 'Mark all reviewed' }).click();
  assert(await page.getByText('All import messages have been reviewed.').count() === 1, 'bulk review clears drawer flags');
  assert(await page.locator('.review-status').count() === 0, 'bulk review clears Default View status');

  // Primary delete explains cascade and cover exception.
  await page.getByRole('button', { name: 'Remove Instagram reel' }).click();
  assert(await page.getByRole('alertdialog', { name: 'Remove this link?' }).count() === 1, 'primary delete requires confirmation');
  assert(await page.getByText(/5 derived resources will be removed/).count() === 1, 'confirmation reports derived count');
  assert(await page.getByText('The current cover will be kept.').count() === 1, 'confirmation explains cover exception');
  await screenshot(page, 'desktop-primary-delete-confirm-1440x900.png');
  await page.getByRole('button', { name: 'Remove 6 resources' }).click();
  assert(await importDialog.locator('[role="status"]').getByText('Source and derived resources removed. The current cover was kept.').count() === 1, 'cascade deletion result is explicit');
  const removedButton = page.getByRole('button', { name: /Removed resources/ });
  await removedButton.click();
  assert(await page.getByText('Removed resources cannot be restored here.').count() === 1, 'removed summary has no restore promise');
  assert(await importDialog.getByText('Restore', { exact: true }).count() === 0, 'no Restore action exists');
  await page.getByRole('button', { name: 'Close Import info' }).click();

  // Direct Focus → Edit transition.
  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  assert(await page.getByRole('heading', { name: /Edit Smoky Tomato/ }).count() === 1, 'Focus/Edit switch avoids Default View detour');

  // Tablet Import Info overlays without narrowing or replacing context.
  await page.setViewportSize({ width: 1024, height: 768 });
  await select(page, '#scenario-select', 'dense');
  await page.getByRole('button', { name: 'Import info' }).click();
  assert(await page.getByRole('dialog', { name: 'Import info' }).getAttribute('aria-modal') === 'true', 'tablet Import Info is modal overlay');
  assert(await page.locator('#prototype-root').evaluate(node => node.inert), 'tablet overlay makes background inert');
  assert(!await page.evaluate(() => document.body.classList.contains('wide-drawer-open')), 'tablet overlay does not reflow context');
  await screenshot(page, 'tablet-import-overlay-1024x768.png');
  await page.getByRole('button', { name: 'Close Import info' }).click();

  // Mobile Import Info becomes bottom sheet; Focus retains direct navigation.
  await page.setViewportSize({ width: 390, height: 844 });
  await select(page, '#scenario-select', 'dense');
  await select(page, '#placement-select', 'under-title');
  await page.getByRole('button', { name: 'Import info' }).click();
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'mobile resource sheet has no horizontal overflow');
  await screenshot(page, 'mobile-import-resource-sheet-390x844.png');
  await page.getByRole('button', { name: 'Close Import info' }).click();
  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  assert(await page.locator('input[type="checkbox"]').count() === 0, 'mobile Focus also has no checkboxes');
  await screenshot(page, 'mobile-focus-simplified-390x844.png');

  assert(pageErrors.length === 0, `no page errors: ${pageErrors.join(' | ')}`);
  assert(consoleErrors.length === 0, `no console errors: ${consoleErrors.join(' | ')}`);
  console.log('REFINEMENT_BROWSER_CHECKS_PASS');
  console.log('Screenshots:', fs.readdirSync(outputDir).sort().join(', '));
  await browser.close();
  if (staticServer) await new Promise(resolve => staticServer.close(resolve));
})().catch(async error => {
  console.error(error.stack || error);
  if (browser) await browser.close().catch(() => {});
  if (staticServer) await new Promise(resolve => staticServer.close(resolve));
  process.exit(1);
});
