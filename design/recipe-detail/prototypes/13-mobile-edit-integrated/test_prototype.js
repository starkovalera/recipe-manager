const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const prototypeDir = __dirname;
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const missingRequests = [];

function startServer() {
  const types = { '.html':'text/html; charset=utf-8', '.css':'text/css; charset=utf-8', '.js':'text/javascript; charset=utf-8' };
  const server = http.createServer((request, response) => {
    const relative = request.url === '/' ? 'index.html' : request.url.split('?')[0].replace(/^\//, '');
    const file = path.resolve(prototypeDir, relative);
    if (!file.startsWith(prototypeDir + path.sep) && file !== path.join(prototypeDir, 'index.html')) return response.writeHead(403).end('Forbidden');
    fs.readFile(file, (error, content) => {
      if (error) { missingRequests.push(relative); return response.writeHead(404).end('Not found'); }
      response.writeHead(200, { 'Content-Type':types[path.extname(file)] || 'application/octet-stream' });
      response.end(content);
    });
  });
  return new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', () => resolve(server)); });
}

async function productViewport(page, width, height, url) {
  await page.setViewportSize({ width, height });
  await page.goto(url, { waitUntil:'networkidle' });
  await page.addStyleTag({ content:'.prototype-toolbar,.review-note{display:none!important}.stage{display:block!important;width:100%!important;margin:0!important}.phone{width:100%!important;height:100vh!important;padding:0!important;border:0!important;border-radius:0!important}.phone-notch{display:none!important}.mobile-edit-surface{border-radius:0!important}#layer-root{inset:0!important;border-radius:0!important}' });
}

(async () => {
  const server = await startServer();
  const browser = await chromium.launch({ headless:true, executablePath:edgePath });
  try {
    const page = await browser.newPage();
    const url = `http://127.0.0.1:${server.address().port}/index.html`;
    const pageErrors = [];
    const consoleErrors = [];
    const failedResources = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
    page.on('response', response => { if (response.status() >= 400) failedResources.push(`${response.status()} ${response.url()}`); });

    for (const viewport of [{ width:360,height:800 },{ width:390,height:844 },{ width:430,height:900 }]) {
      await productViewport(page, viewport.width, viewport.height, url);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true, `${viewport.width}px has no horizontal overflow`);
      assert.equal(await page.locator('.compact-edit-header').count(), 1, `${viewport.width}px has compact Edit header`);
      assert.equal(await page.getByRole('button', { name:'Save', exact:true }).count(), 1, `${viewport.width}px keeps Save in the top toolbar`);
      assert.equal(await page.getByRole('button', { name:/Media/ }).count(), 0, `${viewport.width}px has no direct Media header action`);
      assert.equal(await page.locator('.accordion-section').count(), 5, `${viewport.width}px renders five edit sections`);
      assert.equal(await page.locator('.accordion-section.is-expanded').count(), 1, `${viewport.width}px keeps one section expanded`);
      assert.equal(await page.locator('.accordion-section.is-expanded').getAttribute('data-section'), 'ingredients', `${viewport.width}px starts from the current Ingredients work`);
      assert.equal(await page.locator('.global-navigation').count(), 1, `${viewport.width}px keeps global navigation`);
      assert.deepEqual(await page.locator('.global-navigation button span').allTextContents(), ['Recipes','Collections','Notifications','Profile'], `${viewport.width}px preserves stable destinations`);

      await page.getByRole('button', { name:/Basics 5 fields/ }).click();
      assert.equal(await page.locator('.accordion-section.is-expanded').getAttribute('data-section'), 'basics', `${viewport.width}px switches accordion section`);
      assert.equal(await page.locator('.accordion-section.is-expanded').count(), 1, `${viewport.width}px closes the previous section`);
      await page.getByRole('button', { name:/Ingredients 12 of 50/ }).click();
      await page.locator('[data-edit-ingredient="1"]').click();
      assert.equal(await page.getByRole('dialog', { name:'Edit ingredient' }).count(), 1, `${viewport.width}px opens the approved ingredient sheet`);
      assert.equal(await page.locator('#app-root').evaluate(element => element.inert), true, `${viewport.width}px makes the editor inert behind a sheet`);
      assert.equal(await page.locator('.unit-chips button').count(), 7, `${viewport.width}px shows six unit chips plus +N`);
      await page.getByRole('button', { name:'Close' }).click();
      assert.equal(await page.locator('#app-root').evaluate(element => element.inert), false, `${viewport.width}px restores the editor after closing a sheet`);

      await page.getByRole('button', { name:'More recipe actions' }).click();
      assert.equal(await page.getByRole('dialog', { name:'Recipe actions' }).count(), 1, `${viewport.width}px opens Overflow`);
      assert.equal(await page.getByRole('button', { name:/Media/ }).count(), 1, `${viewport.width}px moves Media into Overflow`);
      assert.equal(await page.getByRole('button', { name:'Import info' }).count(), 1, `${viewport.width}px keeps Import Info in Overflow`);
      await page.getByRole('button', { name:/Media/ }).click();
      assert.equal(await page.getByRole('dialog', { name:'Media' }).count(), 1, `${viewport.width}px replaces Overflow in the one modal slot`);
      assert.equal(await page.getByText(/draft and active section are preserved/i).count(), 1, `${viewport.width}px explains state preservation`);
      await page.getByRole('button', { name:'Close' }).click();
      assert.equal((await page.evaluate(() => window.mobileEditPrototype.getState())).activeSection, 'ingredients', `${viewport.width}px preserves the active section`);

      await page.getByRole('button', { name:'Back to recipe' }).click();
      assert.equal(await page.getByRole('dialog', { name:'Discard unsaved changes?' }).count(), 1, `${viewport.width}px guards dirty Back`);
      await page.getByRole('button', { name:'Keep editing' }).click();
      await page.getByRole('button', { name:'Save', exact:true }).click();
      await page.getByRole('button', { name:'Saved', exact:true }).waitFor({ timeout:1500 });
      assert.equal((await page.evaluate(() => window.mobileEditPrototype.getState())).dirty, false, `${viewport.width}px clears the mock dirty state after Save`);
      await page.getByRole('button', { name:/Basics 5 fields/ }).click();
      await page.locator('input[name="title"]').fill('Smoky Tomato & Butter Bean Stew updated');
      assert.equal(await page.getByRole('button', { name:'Save', exact:true }).count(), 1, `${viewport.width}px reactivates Save after new input`);
    }

    assert.deepEqual(pageErrors, [], `page errors: ${pageErrors.join(' | ')}`);
    assert.deepEqual(consoleErrors, [], `console errors: ${consoleErrors.join(' | ')}; failed resources: ${failedResources.join(' | ')}; missing requests: ${missingRequests.join(' | ')}`);
    console.log('MOBILE_EDIT_INTEGRATED_CHECKS_PASS');
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error.stack || error); process.exitCode=1; });
