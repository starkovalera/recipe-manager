const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const prototypeDir = __dirname;
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const missingRequests = [];

function startServer() {
  const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8' };
  const server = http.createServer((request, response) => {
    const relative = request.url === '/' ? 'index.html' : request.url.split('?')[0].replace(/^\//, '');
    const file = path.resolve(prototypeDir, relative);
    if (!file.startsWith(prototypeDir + path.sep) && file !== path.join(prototypeDir, 'index.html')) return response.writeHead(403).end('Forbidden');
    fs.readFile(file, (error, content) => {
      if (error) { missingRequests.push(relative); return response.writeHead(404).end('Not found'); }
      response.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
      response.end(content);
    });
  });
  return new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', () => resolve(server)); });
}

async function productViewport(page, width, height, url, view) {
  await page.setViewportSize({ width, height });
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: view === 'hybrid' ? /A.*Hybrid controls/ : /B.*Selection sheets/ }).click();
  await page.addStyleTag({ content: '.prototype-toolbar,.review-note{display:none!important}.stage{display:block!important;width:100%!important;margin:0!important}.phone{width:100%!important;height:100vh!important;padding:0!important;border:0!important;border-radius:0!important;box-shadow:none!important}.phone-notch{display:none!important}.mobile-edit-surface,#layer-root{border-radius:0!important}#layer-root{inset:0!important}' });
}

async function optionLabels(page) {
  return page.locator('.option-row > span:first-child').allTextContents();
}

async function assertTouchTargets(page, label) {
  const undersized = await page.locator('#app-root button, #layer-root button').evaluateAll(buttons => buttons
    .map(button => {
      const rect = button.getBoundingClientRect();
      return { name: button.getAttribute('aria-label') || button.textContent.trim(), width: Math.round(rect.width), height: Math.round(rect.height) };
    })
    .filter(target => target.width < 44 || target.height < 44));
  assert.deepEqual(undersized, [], `${label} provides 44px touch targets: ${JSON.stringify(undersized)}`);
}

async function assertClosed(page, trigger, label) {
  await assertTouchTargets(page, `${label} after close`);
  assert.equal(await page.getByRole('dialog').count(), 0, `${label} closes the sheet`);
  assert.equal(await page.locator('#app-root').evaluate(element => element.inert), false, `${label} restores the background`);
  assert.equal(await page.locator(`[data-open="${trigger}"]`).evaluate(element => document.activeElement === element), true, `${label} restores trigger focus`);
}

async function assertDismissalMethods(page, trigger) {
  await page.locator(`[data-open="${trigger}"]`).click();
  assert.equal(await page.locator('#app-root').evaluate(element => element.inert), true, `${trigger} sheet makes the editor inert`);
  assert.equal(await page.locator('.sheet-backdrop').count(), 1, `${trigger} sheet provides an interactive backdrop`);
  await page.keyboard.press('Escape');
  await assertClosed(page, trigger, `${trigger} Escape`);

  await page.locator(`[data-open="${trigger}"]`).click();
  await page.locator('.sheet-backdrop').click({ position: { x: 4, y: 4 } });
  await assertClosed(page, trigger, `${trigger} backdrop`);

  await page.locator(`[data-open="${trigger}"]`).click();
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await assertClosed(page, trigger, `${trigger} Close button`);

  await page.locator(`[data-open="${trigger}"]`).click();
  await page.locator('.sheet-handle').evaluate(handle => {
    handle.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientY: 100 }));
    handle.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, clientY: 220 }));
  });
  await assertClosed(page, trigger, `${trigger} downward swipe`);
}

async function assertHybrid(page, width) {
  assert.equal(await page.getByRole('button', { name: 'Source, Instagram', exact: true }).count(), 1, `${width}px A names Source with its value`);
  assert.equal(await page.getByRole('group', { name: 'Difficulty', exact: true }).count(), 1, `${width}px A labels Difficulty`);
  assert.deepEqual(await page.getByRole('group', { name: 'Difficulty', exact: true }).getByRole('button').allTextContents(), ['Easy', 'Moderate', 'Hard'], `${width}px A has three direct Difficulty choices`);
  assert.equal(await page.getByRole('button', { name: 'Moderate', exact: true }).getAttribute('aria-pressed'), 'true', `${width}px A marks the selected difficulty`);
  assert.equal(await page.getByRole('button', { name: 'Clear', exact: true }).count(), 2, `${width}px A exposes Clear only for populated direct controls`);
  assert.equal(await page.getByRole('group', { name: 'Personal rating', exact: true }).count(), 1, `${width}px A labels Personal rating`);
  assert.deepEqual(await page.getByRole('group', { name: 'Personal rating', exact: true }).getByRole('button').evaluateAll(buttons => buttons.map(button => button.getAttribute('aria-label'))), ['Rate 1 out of 5', 'Rate 2 out of 5', 'Rate 3 out of 5', 'Rate 4 out of 5', 'Rate 5 out of 5'], `${width}px A exposes exact rating names`);
  const ratingAlignment = await page.locator('.rating-row').evaluate(row => {
    const buttons = [...row.querySelectorAll('.star-button')];
    const parentRect = row.closest('.wide-choice').getBoundingClientRect();
    const firstRect = buttons[0].getBoundingClientRect();
    const lastRect = buttons[buttons.length - 1].getBoundingClientRect();
    return {
      groupCenter: (firstRect.left + lastRect.right) / 2,
      parentCenter: (parentRect.left + parentRect.right) / 2,
    };
  });
  assert.ok(Math.abs(ratingAlignment.groupCenter - ratingAlignment.parentCenter) <= 1, `${width}px A centers the five-star group`);
  await page.getByRole('button', { name: 'Source, Instagram', exact: true }).click();
  assert.equal(await page.getByRole('dialog', { name: 'Select source', exact: true }).count(), 1, `${width}px A opens the Source sheet`);
  assert.deepEqual(await optionLabels(page), ['Manual', 'Instagram', 'Threads', 'TikTok', 'Other'], `${width}px A Source sheet uses the exact five options`);
  assert.equal(await page.locator('.option-row[aria-pressed="true"]').count(), 1, `${width}px A Source sheet has one checked value`);
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await assertDismissalMethods(page, 'source');
}

async function assertSheets(page, width) {
  for (const [field, value, title, expected] of [
    ['source', 'Instagram', 'Select source', ['Manual', 'Instagram', 'Threads', 'TikTok', 'Other']],
    ['difficulty', 'Moderate', 'Select difficulty', ['Not set', 'Easy', 'Moderate', 'Hard']],
    ['rating', '4 out of 5', 'Select personal rating', ['Not rated', '1 out of 5', '2 out of 5', '3 out of 5', '4 out of 5', '5 out of 5']],
  ]) {
    const name = `${field[0].toUpperCase() + field.slice(1)}, ${value}`;
    assert.equal(await page.getByRole('button', { name, exact: true }).count(), 1, `${width}px B names ${field} with its value`);
    await page.getByRole('button', { name, exact: true }).click();
    assert.equal(await page.getByRole('dialog', { name: title, exact: true }).count(), 1, `${width}px B opens the ${field} sheet`);
    assert.deepEqual(await optionLabels(page), expected, `${width}px B ${field} sheet has exact options`);
    assert.equal(await page.locator('.option-row[aria-pressed="true"]').count(), 1, `${width}px B ${field} sheet has one checked value`);
    await page.getByRole('button', { name: 'Close', exact: true }).click();
  }
  await assertDismissalMethods(page, 'rating');
}

(async () => {
  const server = await startServer();
  const browser = await chromium.launch({ headless: true, executablePath: edgePath });
  try {
    const page = await browser.newPage();
    const url = `http://127.0.0.1:${server.address().port}/index.html`;
    const pageErrors = [];
    const consoleErrors = [];
    const failedResources = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
    page.on('response', response => { if (response.status() >= 400) failedResources.push(`${response.status()} ${response.url()}`); });

    for (const viewport of [{ width: 360, height: 800 }, { width: 390, height: 844 }, { width: 430, height: 900 }]) {
      for (const view of ['hybrid', 'sheets']) {
        await productViewport(page, viewport.width, viewport.height, url, view);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true, `${viewport.width}px ${view} has no horizontal page overflow`);
        assert.equal(await page.locator('#app-root').evaluate(element => element.scrollWidth <= element.clientWidth), true, `${viewport.width}px ${view} Basics surface has no horizontal overflow`);
        assert.equal(await page.locator('.basics-grid').count(), 1, `${viewport.width}px ${view} renders one Basics grid`);
        await assertTouchTargets(page, `${viewport.width}px ${view}`);
        if (view === 'hybrid') await assertHybrid(page, viewport.width);
        else await assertSheets(page, viewport.width);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true, `${viewport.width}px ${view} remains overflow-free after interactions`);
      }
    }

    assert.deepEqual(pageErrors, [], `page errors: ${pageErrors.join(' | ')}`);
    assert.deepEqual(consoleErrors, [], `console errors: ${consoleErrors.join(' | ')}`);
    assert.deepEqual(failedResources, [], `failed resources: ${failedResources.join(' | ')}`);
    assert.deepEqual(missingRequests, [], `missing requests: ${missingRequests.join(' | ')}`);
    console.log('MOBILE_BASICS_SELECTION_CONTROLS_CHECKS_PASS');
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
