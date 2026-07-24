const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const prototypeDir = __dirname;
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

function startStaticServer() {
  const contentTypes = {
    '.css': 'text/css; charset=utf-8',
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.svg': 'image/svg+xml'
  };
  const server = http.createServer((request, response) => {
    const relativePath = request.url === '/' ? 'index.html' : request.url.split('?')[0].replace(/^\//, '');
    const filePath = path.resolve(prototypeDir, relativePath);
    if (!filePath.startsWith(prototypeDir + path.sep) && filePath !== path.join(prototypeDir, 'index.html')) {
      response.writeHead(403).end('Forbidden');
      return;
    }
    fs.readFile(filePath, (error, content) => {
      if (error) {
        response.writeHead(404).end('Not found');
        return;
      }
      response.writeHead(200, { 'Content-Type': contentTypes[path.extname(filePath)] || 'application/octet-stream' });
      response.end(content);
    });
  });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

async function close(server, browser) {
  if (browser) await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
}

async function assertText(page, selector, expected, message) {
  assert.equal((await page.locator(selector).first().textContent()).trim(), expected, message);
}

async function assertDefaultView(page, viewport) {
  await page.selectOption('#scenario-select', 'flagged');
  await assertText(page, 'h1', 'Smoky Tomato & Butter Bean Stew', `${viewport.width}px renders the flagged recipe title`);
  assert.equal(await page.getByRole('button', { name: 'Import info', exact: true }).count(), 1, `${viewport.width}px renders one neutral Import info action`);
  assert.equal(await page.locator('[data-action="import"] .warning-icon, [data-action="import"] [aria-label*="warning" i]').count(), 0, `${viewport.width}px keeps Import info neutral`);
  assert.equal(await page.locator('.review-status').count(), 1, `${viewport.width}px renders concise import review status`);
  assert.match(await page.locator('.review-status').textContent(), /3 messages[\s\S]*Review import/i, `${viewport.width}px names the review message count and destination`);
  assert.equal(await page.locator('.source-identity').count(), 1, `${viewport.width}px renders source identity separately`);
  assert.equal(await page.locator('.cooking-facts').count(), 1, `${viewport.width}px renders cooking facts separately`);
  assert.equal(await page.locator('.source-identity, .cooking-facts').evaluateAll(rows => rows.every(row => !/\b(Source|Author)\b/.test(row.textContent))), true, `${viewport.width}px omits visible Source and Author labels`);
  assert.equal(await page.locator('.recipe-section[data-section="ingredients"] li').count(), 12, `${viewport.width}px bounds ingredients to twelve items`);
  assert.equal(await page.locator('.recipe-section[data-section="instructions"] li').count(), 8, `${viewport.width}px bounds instructions to eight items`);
  assert.deepEqual(await page.locator('.secondary-metadata .metadata-row').evaluateAll(rows => rows.map(row => row.dataset.metadata)), ['difficulty-rating', 'collections', 'tags'], `${viewport.width}px uses approved metadata order`);
  assert.equal(await page.locator('nav.mode-actions[aria-label="Recipe mode"] > button').count(), 3, `${viewport.width}px has the three mode actions`);
  assert.equal(await page.locator('nav.mode-actions [data-context="default"][aria-current="page"]').count(), 1, `${viewport.width}px marks View as current`);
  assert.equal(await page.locator('.resource-actions[aria-label="Recipe resources"] > [data-action="media"]').count(), 1, `${viewport.width}px renders Media action`);
  assert.equal(await page.locator('.resource-actions[aria-label="Recipe resources"] > [data-action="import"]').count(), 1, `${viewport.width}px renders Import info action`);
  assert.equal(await page.locator('.resource-actions [data-action="overflow"][aria-label="More recipe actions"]').count(), 1, `${viewport.width}px renders overflow action`);

  await page.selectOption('#scenario-select', 'manual');
  assert.equal(await page.getByRole('button', { name: 'Import info', exact: true }).count(), 0, `${viewport.width}px omits Import info for manual recipes`);
  assert.equal(await page.locator('.source-identity').count(), 0, `${viewport.width}px omits empty manual source identity`);
  assert.equal(await page.locator('.metadata-row[data-metadata="collections"] .metadata-values').count(), 0, `${viewport.width}px does not reserve empty collection space`);
  assert.equal(await page.locator('.metadata-row[data-metadata="tags"] .metadata-values').count(), 0, `${viewport.width}px does not reserve empty tag space`);
  assert.match(await page.locator('.nutrition').textContent(), /Nutrition unavailable/i, `${viewport.width}px makes missing nutrition explicit`);

  await page.selectOption('#scenario-select', 'normal');
  assert.equal(await page.locator('.review-status').count(), 0, `${viewport.width}px omits review status without flags`);

  await page.selectOption('#scenario-select', 'noCover');
  assert.equal(await page.locator('.recipe-cover--empty').count(), 1, `${viewport.width}px renders explicit no-cover treatment`);
  assert.equal(await page.locator('.recipe-header h1').evaluate(title => title.getBoundingClientRect().height > 0), true, `${viewport.width}px preserves a visible wrapped title`);
  assert.equal(await page.locator('.mode-actions').evaluate(actions => actions.getBoundingClientRect().height > 0), true, `${viewport.width}px keeps actions reachable with a long title`);

  await page.selectOption('#scenario-select', 'dense');
  assert.equal(await page.locator('.metadata-row[data-metadata="collections"] [data-disclosure="collections"]').textContent(), '+18', `${viewport.width}px collapses dense collections after two values`);
  assert.equal(await page.locator('.metadata-row[data-metadata="tags"] [data-disclosure="tags"]').textContent(), '+48', `${viewport.width}px collapses dense tags after two values`);

  await page.selectOption('#scenario-select', 'long');
  assert.equal(await page.locator('.recipe-section[data-section="ingredients"] li').count(), 12, `${viewport.width}px keeps long ingredients bounded`);
  assert.equal(await page.locator('.recipe-section[data-section="instructions"] li').count(), 8, `${viewport.width}px keeps long instructions bounded`);
  assert.equal(await page.locator('.recipe-section[data-section="notes"] .section-preview').evaluate(notes => notes.scrollHeight >= notes.clientHeight), true, `${viewport.width}px constrains the initial notes preview`);
  await page.evaluate(() => window.scrollTo(0, 120));
  await page.locator('.recipe-section[data-section="ingredients"] [data-expand="ingredients"]').click();
  assert.ok(await page.evaluate(() => window.scrollY > 2), `${viewport.width}px does not reset reading position after ingredient expansion`);
  await page.locator('.recipe-section[data-section="notes"] [data-expand="notes"]').click();
  assert.ok(await page.evaluate(() => window.scrollY > 2), `${viewport.width}px does not reset reading position after note expansion`);
  assert.equal(await page.locator('.recipe-section[data-section="ingredients"] li').count(), 48, `${viewport.width}px expands ingredients independently`);
  assert.match(await page.locator('.recipe-section[data-section="ingredients"] [data-expand="ingredients"]').textContent(), /Show first 12/i, `${viewport.width}px exposes ingredient collapse control`);
  assert.match(await page.locator('.recipe-section[data-section="notes"] [data-expand="notes"]').textContent(), /Show first 4/i, `${viewport.width}px expands notes independently`);
  await page.locator('.recipe-section[data-section="ingredients"] [data-expand="ingredients"]').click();
  assert.equal(await page.locator('.recipe-section[data-section="ingredients"] li').count(), 12, `${viewport.width}px collapses ingredients back to the bounded preview`);
  assert.match(await page.locator('.recipe-section[data-section="notes"] [data-expand="notes"]').textContent(), /Show first 4/i, `${viewport.width}px preserves expanded notes while ingredients collapse`);
  assert.ok(await page.evaluate(() => window.scrollY > 2), `${viewport.width}px does not reset reading position after collapse`);

  await page.selectOption('#scenario-select', 'loading');
  assert.equal(await page.locator('[aria-busy="true"]').count(), 1, `${viewport.width}px marks loading state busy`);
  await page.selectOption('#scenario-select', 'failed');
  assert.equal(await page.locator('[role="alert"]').count(), 1, `${viewport.width}px exposes failed state as an alert`);
  await page.getByRole('button', { name: 'Try again' }).click();
  await assertText(page, 'h1', 'Smoky Tomato & Butter Bean Stew', `${viewport.width}px retry restores normal recipe`);
  await page.selectOption('#scenario-select', 'missing');
  assert.equal(await page.locator('[role="alert"]').count(), 1, `${viewport.width}px exposes missing state as an alert`);
  await page.getByRole('button', { name: 'Return to recipes' }).click();
  await assertText(page, 'h1', 'Recipes', `${viewport.width}px returns to mock recipes destination`);
}

(async () => {
  let server;
  let browser;
  try {
    server = await startStaticServer();
    const address = server.address();
    browser = await chromium.launch({ headless: true, executablePath: edgePath });
    const page = await browser.newPage();
    const pageErrors = [];
    const consoleErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });

    const viewports = [
      { width: 360, height: 800 },
      { width: 390, height: 844 },
      { width: 430, height: 900 }
    ];
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.goto(`http://127.0.0.1:${address.port}/index.html`, { waitUntil: 'networkidle' });
      await page.locator('#prototype-root [data-product-surface]').waitFor({ timeout: 1_000 });
      assert.equal(await page.locator('#scenario-select option').count(), 9, `${viewport.width}px exposes exactly nine scenarios`);
      assert.equal(await page.locator('#live-region[aria-live="polite"]').count(), 1, `${viewport.width}px includes the polite live region`);
      await assertDefaultView(page, viewport);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true, `${viewport.width}px has no horizontal overflow`);
      assert.deepEqual(pageErrors, [], `${viewport.width}px page errors: ${pageErrors.join(' | ')}`);
      assert.deepEqual(consoleErrors, [], `${viewport.width}px console errors: ${consoleErrors.join(' | ')}`);
    }
    assert.deepEqual(pageErrors, [], `page errors: ${pageErrors.join(' | ')}`);
    assert.deepEqual(consoleErrors, [], `console errors: ${consoleErrors.join(' | ')}`);
    console.log('TASK_2_MOBILE_RECIPE_DETAIL_DEFAULT_VIEW_PASS');
    console.log('TASK_1_MOBILE_RECIPE_DETAIL_SMOKE_PASS');
  } finally {
    await close(server, browser);
  }
})().catch(error => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
