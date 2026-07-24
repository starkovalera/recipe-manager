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

async function assertMinimumHitArea(locator, viewport, label) {
  const rect = await locator.evaluate(element => {
    const { width, height } = element.getBoundingClientRect();
    return { width, height };
  });
  assert.ok(rect.width >= 44, `${viewport.width}px ${label} is at least 44px wide (got ${rect.width}px)`);
  assert.ok(rect.height >= 44, `${viewport.width}px ${label} is at least 44px tall (got ${rect.height}px)`);
}

async function assertReadyStateOverflow(page, scenario, viewport) {
  await page.selectOption('#scenario-select', scenario);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true, `${viewport.width}px ${scenario} has no horizontal overflow`);
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
  for (const button of await page.locator('.mode-actions button').all()) await assertMinimumHitArea(button, viewport, 'mode action');
  await assertMinimumHitArea(page.locator('.review-status button'), viewport, 'review action');

  await page.selectOption('#scenario-select', 'manual');
  assert.equal(await page.getByRole('button', { name: 'Import info', exact: true }).count(), 0, `${viewport.width}px omits Import info for manual recipes`);
  assert.equal(await page.locator('.source-identity').count(), 0, `${viewport.width}px omits empty manual source identity`);
  assert.equal(await page.locator('.metadata-row[data-metadata="collections"] .metadata-values').count(), 0, `${viewport.width}px does not reserve empty collection space`);
  assert.equal(await page.locator('.metadata-row[data-metadata="tags"] .metadata-values').count(), 0, `${viewport.width}px does not reserve empty tag space`);
  assert.match(await page.locator('.nutrition').textContent(), /Nutrition unavailable/i, `${viewport.width}px makes missing nutrition explicit`);

  await page.selectOption('#scenario-select', 'normal');
  assert.equal(await page.locator('.review-status').count(), 0, `${viewport.width}px omits review status without flags`);
  assert.equal(await page.locator('.recipe-section[data-section="notes"] [data-expand="notes"]').count(), 0, `${viewport.width}px omits Notes disclosure when content fits the four-line preview`);

  await page.selectOption('#scenario-select', 'noCover');
  assert.equal(await page.locator('.recipe-cover--empty').count(), 1, `${viewport.width}px renders explicit no-cover treatment`);
  await assertText(page, '.recipe-header h1', 'Slow-Roasted Aubergine, Butter Bean & Preserved Lemon Traybake with Herby Tahini', `${viewport.width}px uses the no-cover long-title scenario`);
  assert.equal(await page.locator('.recipe-header h1').evaluate(title => {
    const lineHeight = Number.parseFloat(getComputedStyle(title).lineHeight);
    return title.getBoundingClientRect().height >= lineHeight * 1.9;
  }), true, `${viewport.width}px wraps the no-cover title over multiple lines`);
  assert.equal(await page.locator('.mode-actions').evaluate(actions => actions.getBoundingClientRect().height > 0), true, `${viewport.width}px keeps actions reachable with a long title`);

  await page.selectOption('#scenario-select', 'dense');
  assert.equal(await page.locator('.metadata-row[data-metadata="collections"] [data-disclosure="collections"]').textContent(), '+18', `${viewport.width}px collapses dense collections after two values`);
  assert.equal(await page.locator('.metadata-row[data-metadata="tags"] [data-disclosure="tags"]').textContent(), '+48', `${viewport.width}px collapses dense tags after two values`);
  await assertMinimumHitArea(page.locator('[data-disclosure="collections"]'), viewport, 'collection disclosure');
  await assertMinimumHitArea(page.locator('[data-disclosure="tags"]'), viewport, 'tag disclosure');

  await page.selectOption('#scenario-select', 'long');
  assert.equal(await page.locator('.recipe-section[data-section="ingredients"] li').count(), 12, `${viewport.width}px keeps long ingredients bounded`);
  assert.equal(await page.locator('.recipe-section[data-section="instructions"] li').count(), 8, `${viewport.width}px keeps long instructions bounded`);
  assert.equal(await page.locator('.recipe-section[data-section="notes"] .section-preview').evaluate(notes => notes.scrollHeight >= notes.clientHeight), true, `${viewport.width}px constrains the initial notes preview`);
  assert.equal(await page.locator('.recipe-section[data-section="notes"] [data-expand="notes"]').count(), 1, `${viewport.width}px exposes Notes disclosure only when long content is truncated`);
  await assertMinimumHitArea(page.locator('.recipe-section[data-section="ingredients"] [data-expand="ingredients"]'), viewport, 'section disclosure');
  await assertMinimumHitArea(page.locator('.recipe-section[data-section="notes"] [data-expand="notes"]'), viewport, 'Notes disclosure');
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

async function assertCookingFocus(page, viewport) {
  await page.selectOption('#scenario-select', 'normal');
  await page.evaluate(() => window.scrollTo(0, 120));
  const expectedDefaultScroll = await page.evaluate(() => window.scrollY);
  assert.ok(expectedDefaultScroll > 2, `${viewport.width}px starts Focus from a saved reading position`);

  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  assert.equal(await page.locator('.focus-recipe').count(), 1, `${viewport.width}px renders the Cooking Focus surface`);
  assert.equal(await page.locator('.recipe-cover').count(), 0, `${viewport.width}px Focus removes the cover`);
  assert.equal(await page.locator('.source-identity').count(), 0, `${viewport.width}px Focus removes source identity`);
  assert.equal(await page.locator('.secondary-metadata').count(), 0, `${viewport.width}px Focus removes secondary metadata`);
  assert.equal(await page.locator('.review-status').count(), 0, `${viewport.width}px Focus removes review status`);
  assert.equal(await page.locator('.nutrition').count(), 0, `${viewport.width}px Focus removes nutrition`);
  assert.equal(await page.locator('.focus-recipe .cooking-facts').count(), 1, `${viewport.width}px Focus retains cooking facts`);
  assert.equal(await page.locator('nav.mode-actions [data-context="focus"][aria-current="page"]').count(), 1, `${viewport.width}px marks Focus as current`);
  assert.equal(await page.locator('[role="tablist"][aria-label="Focus section"]').count(), 1, `${viewport.width}px exposes the named Focus tablist`);
  assert.equal(await page.getByRole('tab', { name: 'Ingredients', exact: true }).getAttribute('aria-selected'), 'true', `${viewport.width}px selects Ingredients initially`);
  assert.equal(await page.getByRole('tab', { name: 'Instructions', exact: true }).getAttribute('aria-selected'), 'false', `${viewport.width}px marks Instructions inactive initially`);
  assert.equal(await page.locator('.focus-content[data-focus-content="ingredients"]').count(), 1, `${viewport.width}px shows the Ingredients Focus content`);
  assert.equal(await page.locator('.focus-content[data-focus-content="instructions"]').count(), 0, `${viewport.width}px hides Instructions until selected`);
  assert.equal(await page.locator('input[type="checkbox"], [data-complete], [data-action="portion-multiplier"]').count(), 0, `${viewport.width}px Focus has no completion controls or serving multiplier`);

  await page.getByRole('tab', { name: 'Instructions', exact: true }).click();
  assert.equal(await page.getByRole('tab', { name: 'Ingredients', exact: true }).getAttribute('aria-selected'), 'false', `${viewport.width}px updates Ingredients tab semantics`);
  assert.equal(await page.getByRole('tab', { name: 'Instructions', exact: true }).getAttribute('aria-selected'), 'true', `${viewport.width}px updates Instructions tab semantics`);
  assert.equal(await page.locator('.focus-content[data-focus-content="ingredients"]').count(), 0, `${viewport.width}px hides Ingredients after switching`);
  assert.equal(await page.locator('.focus-content[data-focus-content="instructions"]').count(), 1, `${viewport.width}px shows Instructions after switching`);
  assert.equal(await page.locator('.focus-content[data-focus-content="instructions"] [data-section="notes"]').count(), 1, `${viewport.width}px places Notes after Focus instructions`);

  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  assert.equal(await page.locator('nav.mode-actions [data-context="focus"][aria-current="page"]').count(), 1, `${viewport.width}px keeps Focus active after Edit status`);
  assert.equal(await page.locator('#live-region').textContent(), 'Edit Mode is being designed.', `${viewport.width}px announces the unfinished Edit state`);
  assert.equal(await page.getByRole('tab', { name: 'Instructions', exact: true }).getAttribute('aria-selected'), 'true', `${viewport.width}px preserves the Focus tab after Edit status`);

  await page.getByRole('button', { name: 'View', exact: true }).click();
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const restoredScroll = await page.evaluate(() => window.scrollY);
  assert.ok(Math.abs(restoredScroll - expectedDefaultScroll) <= 2, `${viewport.width}px restores Default View position within 2px (expected ${expectedDefaultScroll}, got ${restoredScroll})`);
  assert.equal(await page.locator('nav.mode-actions [data-context="default"][aria-current="page"]').count(), 1, `${viewport.width}px returns to Default View`);

  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  assert.equal(await page.getByRole('tab', { name: 'Instructions', exact: true }).getAttribute('aria-selected'), 'true', `${viewport.width}px preserves the Focus tab across context changes`);
}

async function assertInteractiveLayers(page, viewport) {
  await page.selectOption('#scenario-select', 'flagged');
  await page.selectOption('#context-select', 'default');
  const mediaTrigger = page.getByRole('button', { name: /Media/ });
  await mediaTrigger.click();
  assert.equal(await page.getByRole('dialog', { name: 'Media (4)' }).count(), 1, `${viewport.width}px opens the named Media sheet`);
  assert.equal(await page.getByRole('link', { name: 'Watch Instagram cooking video' }).count(), 1, `${viewport.width}px labels the video action without a raw URL`);
  assert.equal(await page.locator('[data-layer="media"] .destructive-icon').count(), 0, `${viewport.width}px keeps Media free of deletion controls`);
  await page.getByRole('button', { name: 'View Aubergine browning reference' }).click();
  assert.equal(await page.locator('.media-thumbnail.is-selected').getAttribute('aria-label'), 'View Aubergine browning reference', `${viewport.width}px changes Media selection`);
  await page.keyboard.press('Escape');
  assert.equal(await page.getByRole('dialog').count(), 0, `${viewport.width}px Escape closes Media`);
  assert.equal(await page.evaluate(() => document.activeElement.textContent.includes('Media')), true, `${viewport.width}px returns focus to Media`);

  await mediaTrigger.click();
  await page.locator('.sheet-handle').dispatchEvent('pointerdown', { clientY: 20, pointerId: 1 });
  await page.locator('.sheet-handle').dispatchEvent('pointerup', { clientY: 140, pointerId: 1 });
  assert.equal(await page.getByRole('dialog').count(), 0, `${viewport.width}px swipe down from the handle closes Media`);

  await page.selectOption('#scenario-select', 'dense');
  await page.locator('[data-disclosure="collections"]').click();
  assert.equal(await page.getByRole('dialog', { name: 'All collections' }).count(), 1, `${viewport.width}px opens Collections disclosure`);
  assert.equal(await page.locator('[data-layer="disclosure"] input, [data-layer="disclosure"] .destructive-icon').count(), 0, `${viewport.width}px disclosure has no edit or delete controls`);
  await page.getByRole('button', { name: 'Close' }).click();

  await page.selectOption('#scenario-select', 'flagged');
  await page.getByRole('button', { name: 'Import info', exact: true }).click();
  assert.equal(await page.getByRole('dialog', { name: 'Import info' }).count(), 1, `${viewport.width}px opens Import info in the shared sheet slot`);
  assert.equal(await page.getByText('Ignored resources', { exact: true }).count(), 1, `${viewport.width}px groups ignored resources when present`);
  assert.equal(await page.locator('.resource-thumbnail').count() > 0, true, `${viewport.width}px gives imported images recognizable thumbnails`);
  assert.equal(await page.getByText(/Extracted result|Provenance|Original source|Restore/i).count(), 0, `${viewport.width}px omits forbidden import duplication and restore terms`);
  assert.equal(await page.getByText('Debug details', { exact: true }).count(), 0, `${viewport.width}px hides debug details for users`);
  await page.selectOption('#role-select', 'debug');
  assert.equal(await page.getByText('Debug details', { exact: true }).count(), 1, `${viewport.width}px shows debug details only for Debug role`);
  await page.selectOption('#role-select', 'user');
  await page.getByRole('button', { name: 'Remove Packaging photo' }).click();
  assert.equal(await page.getByText('Remove this resource?', { exact: true }).count(), 1, `${viewport.width}px uses inline derived-resource confirmation`);
  assert.match(await page.locator('.resource-confirmation').textContent(), /cannot be restored[\s\S]*saved recipe will not change/i, `${viewport.width}px explains irreversible resource removal without changing recipe`);
  await page.keyboard.press('Escape');
  assert.equal(await page.getByText('Remove this resource?', { exact: true }).count(), 0, `${viewport.width}px Escape cancels pending resource removal`);
  await page.getByRole('button', { name: 'Mark all reviewed' }).click();
  await page.getByRole('button', { name: 'Mark all reviewed', exact: true }).click();
  assert.equal(await page.locator('.review-status').count(), 0, `${viewport.width}px removes the Default review status after marking all reviewed`);
  await page.getByRole('button', { name: 'Close' }).click();

  await page.selectOption('#scenario-select', 'normal');
  await page.selectOption('#delete-result-select', 'failure');
  await page.getByRole('button', { name: 'More recipe actions' }).click();
  assert.equal(await page.getByRole('menu').count(), 1, `${viewport.width}px opens the anchored overflow menu`);
  await page.getByRole('menuitem', { name: 'Delete recipe…' }).click();
  assert.equal(await page.getByRole('dialog', { name: /Delete Smoky Tomato/ }).count(), 1, `${viewport.width}px opens blocking recipe deletion`);
  assert.equal(await page.evaluate(() => document.querySelector('#prototype-root').inert), true, `${viewport.width}px makes background inert for deletion`);
  await page.getByRole('button', { name: 'Delete recipe', exact: true }).click();
  assert.equal(await page.getByText('Recipe couldn’t be deleted. Try again.', { exact: true }).count(), 1, `${viewport.width}px retains deletion sheet on mock failure`);
  await page.keyboard.press('Escape');
  await page.selectOption('#delete-result-select', 'success');
  await page.getByRole('button', { name: 'More recipe actions' }).click();
  await page.getByRole('menuitem', { name: 'Delete recipe…' }).click();
  await page.getByRole('button', { name: 'Delete recipe', exact: true }).click();
  await assertText(page, 'h1', 'Recipes', `${viewport.width}px mock deletion reaches Recipes destination`);
  assert.equal(await page.locator('#live-region').textContent(), 'Recipe deleted', `${viewport.width}px announces recipe deletion`);
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
      for (const scenario of ['flagged', 'dense', 'long', 'noCover']) await assertReadyStateOverflow(page, scenario, viewport);
      await assertDefaultView(page, viewport);
      await assertCookingFocus(page, viewport);
      await assertInteractiveLayers(page, viewport);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true, `${viewport.width}px has no horizontal overflow`);
      assert.deepEqual(pageErrors, [], `${viewport.width}px page errors: ${pageErrors.join(' | ')}`);
      assert.deepEqual(consoleErrors, [], `${viewport.width}px console errors: ${consoleErrors.join(' | ')}`);
    }
    assert.deepEqual(pageErrors, [], `page errors: ${pageErrors.join(' | ')}`);
    assert.deepEqual(consoleErrors, [], `console errors: ${consoleErrors.join(' | ')}`);
    console.log('TASK_4_TO_6_MOBILE_RECIPE_DETAIL_INTERACTIONS_PASS');
    console.log('TASK_3_MOBILE_RECIPE_DETAIL_FOCUS_PASS');
    console.log('TASK_2_MOBILE_RECIPE_DETAIL_DEFAULT_VIEW_PASS');
    console.log('TASK_1_MOBILE_RECIPE_DETAIL_SMOKE_PASS');
  } finally {
    await close(server, browser);
  }
})().catch(error => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
