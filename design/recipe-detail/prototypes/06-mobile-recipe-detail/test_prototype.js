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
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true, `${viewport.width}px has no horizontal overflow`);
      assert.deepEqual(pageErrors, [], `${viewport.width}px page errors: ${pageErrors.join(' | ')}`);
      assert.deepEqual(consoleErrors, [], `${viewport.width}px console errors: ${consoleErrors.join(' | ')}`);
    }
    assert.deepEqual(pageErrors, [], `page errors: ${pageErrors.join(' | ')}`);
    assert.deepEqual(consoleErrors, [], `console errors: ${consoleErrors.join(' | ')}`);
    console.log('TASK_1_MOBILE_RECIPE_DETAIL_SMOKE_PASS');
  } finally {
    await close(server, browser);
  }
})().catch(error => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
