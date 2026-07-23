const fs = require('fs');
const http = require('http');
const path = require('path');
const { chromium } = require('playwright');

const baseUrl = process.env.PROTOTYPE_URL || 'http://127.0.0.1:4177';
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const outputDir = path.resolve('design/recipe-detail/screenshots/05-main-actions-and-responsive-panels');
const prototypeDir = path.resolve('design/recipe-detail/prototypes/05-main-actions-and-responsive-panels');
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
  await new Promise((resolve, reject) => server.once('error', reject).listen(4177, '127.0.0.1', resolve));
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

  // Approved B: one cover-edge row with distinct mode and resource groups.
  const cover = await page.locator('.cover').boundingBox();
  const actions = await page.locator('.header-wide-actions').boundingBox();
  assert(Math.abs(cover.x - actions.x) < 2, 'approved B starts actions at the cover edge');
  assert(await page.locator('.header-wide-actions .mode-switch').count() === 1, 'mode group is present');
  assert(await page.locator('.header-wide-actions .utility-actions').count() === 1, 'resource group is present');
  assert(await page.getByRole('button', { name: 'Media · 6' }).count() === 1, 'Media is visible in Default View');
  assert(await page.getByRole('button', { name: 'Import info' }).count() === 1, 'Import info is visible for imported recipe');
  await screenshot(page, 'desktop-approved-b-main-actions-1440x900.png');

  // Delete recipe is de-emphasized in overflow and requires irreversible confirmation.
  await page.getByRole('button', { name: 'More recipe actions' }).click();
  let menu = page.getByRole('menu', { name: 'More recipe actions' });
  const deleteMenuItem = menu.getByRole('menuitem', { name: 'Delete recipe…' });
  assert(await deleteMenuItem.count() === 1, 'Delete recipe is available in overflow');
  assert(await deleteMenuItem.locator('svg').count() === 1, 'Delete recipe menu item has a trash icon');
  assert(await menu.locator('.overflow-separator + [role="menuitem"]').getAttribute('data-action') === 'delete-recipe', 'Delete recipe is the final separated menu item');
  await screenshot(page, 'desktop-delete-recipe-overflow-1440x900.png');
  await deleteMenuItem.click();
  let deleteDialog = page.getByRole('dialog', { name: 'Delete “Smoky Tomato & Butter Bean Stew”?' });
  assert(await deleteDialog.getByText('This permanently deletes the recipe and its imported files, images, and links. It cannot be restored.', { exact: true }).count() === 1, 'confirmation explains irreversible imported scope');
  assert(await deleteDialog.getByRole('textbox').count() === 0, 'confirmation does not require typing the title');
  assert(await deleteDialog.getByRole('button', { name: 'Cancel' }).count() === 1, 'confirmation can be cancelled');
  assert(await deleteDialog.getByRole('button', { name: 'Delete recipe', exact: true }).count() === 1, 'confirmation has explicit destructive action');
  await screenshot(page, 'desktop-delete-recipe-confirmation-1440x900.png');
  await page.keyboard.press('Escape');
  assert(await page.getByRole('dialog').count() === 0, 'Escape cancels recipe deletion');

  await select(page, '#delete-result-select', 'failure');
  await page.getByRole('button', { name: 'More recipe actions' }).click();
  await page.getByRole('menuitem', { name: 'Delete recipe…' }).click();
  deleteDialog = page.getByRole('dialog', { name: 'Delete “Smoky Tomato & Butter Bean Stew”?' });
  await deleteDialog.getByRole('button', { name: 'Delete recipe', exact: true }).click();
  assert(await deleteDialog.getByRole('alert').getByText('Recipe couldn’t be deleted. Try again.', { exact: true }).count() === 1, 'failure keeps confirmation open with next step');
  await screenshot(page, 'desktop-delete-recipe-failure-1440x900.png');
  await deleteDialog.getByRole('button', { name: 'Cancel' }).click();

  await select(page, '#delete-result-select', 'success');
  await page.getByRole('button', { name: 'More recipe actions' }).click();
  await page.getByRole('menuitem', { name: 'Delete recipe…' }).click();
  await page.getByRole('dialog', { name: 'Delete “Smoky Tomato & Butter Bean Stew”?' }).getByRole('button', { name: 'Delete recipe', exact: true }).click();
  assert(await page.getByRole('heading', { name: 'Recipes' }).count() === 1, 'success navigates to recipe-list destination');
  assert(await page.getByRole('status').getByText('Recipe deleted', { exact: true }).count() === 1, 'success announces recipe deletion');
  await select(page, '#scenario-select', 'flagged');

  // Media remains in all contexts; manual/no-media hides resource-specific actions.
  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  assert(await page.getByRole('button', { name: 'Media · 6' }).count() === 1, 'Media is visible in Focus');
  assert(await page.getByRole('button', { name: 'More recipe actions' }).count() === 1, 'overflow is visible in Focus');
  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  assert(await page.getByRole('button', { name: 'Media · 6' }).count() === 1, 'Media is visible in Edit');
  assert(await page.getByRole('button', { name: 'More recipe actions' }).count() === 1, 'overflow is visible in Edit');
  await select(page, '#scenario-select', 'manual');
  assert(await page.getByRole('button', { name: /^Media/ }).count() === 0, 'Media is hidden when unavailable');
  assert(await page.getByRole('button', { name: 'Import info' }).count() === 0, 'Import info is hidden for manual recipe');
  await page.getByRole('button', { name: 'More recipe actions' }).click();
  await page.getByRole('menuitem', { name: 'Delete recipe…' }).click();
  deleteDialog = page.getByRole('dialog', { name: 'Delete “Roasted Carrot, Lentil & Dill Salad”?' });
  assert(await deleteDialog.getByText('This permanently deletes the recipe. It cannot be restored.', { exact: true }).count() === 1, 'manual recipe confirmation omits imported-resource scope');
  await deleteDialog.getByRole('button', { name: 'Cancel' }).click();
  await select(page, '#scenario-select', 'flagged');

  // Wide desktop reflows around the nonmodal slot and permits direct replacement from the main row.
  await page.getByRole('button', { name: 'Media · 6' }).click();
  let dialog = page.getByRole('dialog', { name: 'Cooking media · 6' });
  const mediaWidth = (await dialog.boundingBox()).width;
  assert(await dialog.getAttribute('aria-modal') === 'false', 'wide desktop panel is nonmodal');
  assert(await dialog.getByRole('button', { name: /Import info/ }).count() === 0, 'Media panel contains no Import Info transition');
  assert(await dialog.getByRole('button', { name: /Delete recipe/ }).count() === 0, 'Media panel contains no recipe deletion');
  assert(await dialog.getByRole('button', { name: 'Close Cooking media' }).count() === 1, 'Media closes with a cross control');
  assert((await dialog.getByRole('button', { name: 'Close Cooking media' }).innerText()).trim() === '', 'Media close has no text label');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'wide open panel has no page overflow');
  await page.getByRole('button', { name: 'Import info' }).click();
  dialog = page.getByRole('dialog', { name: 'Import info' });
  assert(await page.getByRole('dialog').count() === 1, 'main action replaces the single auxiliary slot');
  assert(Math.abs((await dialog.boundingBox()).width - mediaWidth) < 2, 'Media and Import Info use equal widths');
  assert(await dialog.getByRole('button', { name: /Back to media/ }).count() === 0, 'Import panel has no Back to media');
  assert(await dialog.getByRole('button', { name: /Delete recipe/ }).count() === 0, 'Import panel contains no recipe deletion');

  // Ignored resources are conditional, grouped by their primary source, and retain previews/removal.
  const ignored = dialog.locator('.ignored-section');
  assert(await ignored.getByRole('heading', { name: 'Ignored resources · 2' }).count() === 1, 'ignored section reports its count');
  assert(await ignored.getByText('Instagram reel', { exact: true }).count() === 1, 'ignored resources retain primary-source grouping');
  assert(await ignored.getByRole('button', { name: 'Preview Packaging photo' }).count() === 1, 'ignored image has a preview');
  const ignoredTrash = ignored.getByRole('button', { name: 'Remove Packaging photo' });
  assert(await ignoredTrash.count() === 1, 'ignored item uses trash removal');
  await ignoredTrash.click();
  let childConfirm = ignored.getByRole('alertdialog', { name: 'Remove this resource?' });
  assert(await childConfirm.getByText('This resource cannot be restored.', { exact: false }).count() === 1, 'ignored resource warns that removal is irreversible');
  assert(await ignored.getByRole('button', { name: 'Preview Packaging photo' }).count() === 1, 'ignored image preview remains visible during confirmation');
  assert(await ignored.getByRole('button', { name: 'Remove resource', exact: true }).count() === 1, 'ignored confirmation has an explicit destructive action');
  await screenshot(page, 'desktop-ignored-secondary-removal-confirmation-1440x900.png');
  await childConfirm.getByRole('button', { name: 'Cancel' }).click();
  assert(await ignored.getByRole('button', { name: 'Remove Packaging photo' }).count() === 1, 'cancelling restores ignored-resource trash action');
  await ignored.scrollIntoViewIfNeeded();
  await screenshot(page, 'desktop-import-ignored-resources-1440x900.png');

  // All resource removal controls use trash icons; cascade copy preserves the recipe explicitly.
  const primaryTrash = dialog.getByRole('button', { name: 'Remove Instagram reel' });
  const childTrash = dialog.getByRole('button', { name: 'Remove Aubergine browning reference' });
  assert((await primaryTrash.innerText()).trim() === '' && (await childTrash.innerText()).trim() === '', 'top-level and child removals are icon-only');
  await childTrash.click();
  childConfirm = dialog.getByRole('alertdialog', { name: 'Remove this resource?' });
  assert(await childConfirm.getByText('This resource cannot be restored.', { exact: false }).count() === 1, 'derived resource warns that removal is irreversible');
  assert(await dialog.getByText('Aubergine browning reference', { exact: true }).count() >= 1, 'derived resource remains visible before confirmation');
  await childConfirm.scrollIntoViewIfNeeded();
  await screenshot(page, 'desktop-secondary-removal-confirmation-1440x900.png');
  await page.keyboard.press('Escape');
  assert(await dialog.getByRole('button', { name: 'Remove Aubergine browning reference' }).count() === 1, 'Escape cancels child removal and restores focus target');
  await primaryTrash.scrollIntoViewIfNeeded();
  await primaryTrash.click();
  const confirm = dialog.getByRole('alertdialog', { name: 'Remove this link?' });
  assert(await confirm.getByText('Your saved recipe will not change.', { exact: false }).count() === 1, 'cascade warning protects the saved recipe');
  assert(await confirm.getByText(/Only this source and 5 related imported resources/).count() === 1, 'cascade warning reports affected resources');
  await screenshot(page, 'desktop-import-ignored-and-cascade-1440x900.png');
  await page.keyboard.press('Escape');
  await dialog.getByRole('button', { name: 'Close Import info' }).click();

  // Narrow desktop overlays instead of compressing the approved menu or recipe columns.
  await page.setViewportSize({ width: 1280, height: 800 });
  const menuBefore = await page.locator('.header-wide-actions').boundingBox();
  await page.getByRole('button', { name: 'Media · 6' }).click();
  dialog = page.getByRole('dialog', { name: 'Cooking media · 6' });
  const menuAfter = await page.locator('.header-wide-actions').boundingBox();
  assert(await dialog.getAttribute('aria-modal') === 'true', 'narrow desktop panel is modal overlay');
  assert(Math.abs(menuBefore.x - menuAfter.x) < 2 && Math.abs(menuBefore.width - menuAfter.width) < 2, 'open panel does not recompute main-menu geometry');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), '1280 overlay has no horizontal overflow');
  await screenshot(page, 'narrow-desktop-media-overlay-1280x800.png');
  await dialog.getByRole('button', { name: 'Close Cooking media' }).click();

  await page.setViewportSize({ width: 1024, height: 768 });
  await page.getByRole('button', { name: 'Import info' }).click();
  dialog = page.getByRole('dialog', { name: 'Import info' });
  assert(await dialog.getAttribute('aria-modal') === 'true', '1024 Import Info is modal overlay');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), '1024 overlay has no horizontal overflow');
  await screenshot(page, 'compact-desktop-import-overlay-1024x768.png');
  await dialog.getByRole('button', { name: 'Close Import info' }).click();

  // Mobile menu uses two semantic rows; sheet has cross plus downward-swipe dismissal.
  await page.setViewportSize({ width: 390, height: 844 });
  const modeBox = await page.locator('.mode-switch').boundingBox();
  const utilityBox = await page.locator('.utility-actions').boundingBox();
  assert(utilityBox.y > modeBox.y + modeBox.height - 2, 'mobile puts resources on a second row');
  await screenshot(page, 'mobile-two-row-main-actions-390x844.png');
  await page.getByRole('button', { name: 'More recipe actions' }).click();
  await page.getByRole('menuitem', { name: 'Delete recipe…' }).click();
  deleteDialog = page.getByRole('dialog', { name: 'Delete “Smoky Tomato & Butter Bean Stew”?' });
  assert(await deleteDialog.evaluate(node => node.classList.contains('delete-recipe-dialog')), 'mobile uses the dedicated blocking delete sheet');
  assert(await deleteDialog.getByRole('button', { name: 'Close delete recipe confirmation' }).count() === 1, 'mobile delete sheet retains a cross');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'mobile delete confirmation has no horizontal overflow');
  await screenshot(page, 'mobile-delete-recipe-confirmation-390x844.png');
  await deleteDialog.getByRole('button', { name: 'Cancel' }).click();
  await page.getByRole('button', { name: 'Media · 6' }).click();
  dialog = page.getByRole('dialog', { name: 'Cooking media · 6' });
  assert(await dialog.locator('.sheet-handle').count() === 1, 'mobile sheet exposes a drag handle');
  assert(await dialog.getByRole('button', { name: 'Close Cooking media' }).count() === 1, 'mobile sheet retains the cross');
  await screenshot(page, 'mobile-main-actions-and-media-sheet-390x844.png');
  const handle = await dialog.locator('.sheet-handle').boundingBox();
  await page.mouse.move(handle.x + handle.width / 2, handle.y + 12);
  await page.mouse.down();
  await page.mouse.move(handle.x + handle.width / 2, handle.y + 150, { steps: 5 });
  await page.mouse.up();
  await page.waitForTimeout(80);
  assert(await page.getByRole('dialog').count() === 0, 'downward swipe closes the mobile sheet');

  await page.getByRole('button', { name: 'Import info' }).click();
  dialog = page.getByRole('dialog', { name: 'Import info' });
  const mobileChildTrash = dialog.getByRole('button', { name: 'Remove Aubergine browning reference' });
  await mobileChildTrash.scrollIntoViewIfNeeded();
  await mobileChildTrash.click();
  childConfirm = dialog.getByRole('alertdialog', { name: 'Remove this resource?' });
  assert(await childConfirm.getByText('This resource cannot be restored.', { exact: false }).count() === 1, 'mobile keeps irreversible warning inline');
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'mobile child confirmation has no horizontal overflow');
  await screenshot(page, 'mobile-secondary-removal-confirmation-390x844.png');
  await childConfirm.getByRole('button', { name: 'Cancel' }).click();
  await dialog.getByRole('button', { name: 'Remove Caption text' }).click();
  childConfirm = dialog.getByRole('alertdialog', { name: 'Remove this resource?' });
  await childConfirm.getByRole('button', { name: 'Remove resource', exact: true }).click();
  assert(await dialog.getByRole('button', { name: 'Remove Caption text' }).count() === 0, 'confirmed secondary resource is removed');
  assert(await dialog.getByText('Caption text removed. It cannot be restored.', { exact: true }).count() === 1, 'confirmed removal announces irreversible result');
  await dialog.getByRole('button', { name: 'Close Import info' }).click();

  assert(pageErrors.length === 0, `no page errors: ${pageErrors.join(' | ')}`);
  assert(consoleErrors.length === 0, `no console errors: ${consoleErrors.join(' | ')}`);
  console.log('MAIN_ACTIONS_RESPONSIVE_PANELS_CHECKS_PASS');
  console.log('Screenshots:', fs.readdirSync(outputDir).sort().join(', '));
  await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
})().catch(async error => {
  console.error(error.stack || error);
  if (browser) await browser.close().catch(() => {});
  if (server) await new Promise(resolve => server.close(resolve));
  process.exitCode = 1;
});
