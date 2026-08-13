const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

const prototypeDir = __dirname;
const output = path.resolve(prototypeDir, '../../screenshots/edit-mode/11-mobile-edit-header-a-c-comparison-v1.png');
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const server = http.createServer((request, response) => {
  const relative = request.url === '/' ? 'index.html' : request.url.replace(/^\//, '');
  const file = path.resolve(prototypeDir, relative);
  if (!file.startsWith(prototypeDir + path.sep) && file !== path.join(prototypeDir, 'index.html')) {
    response.writeHead(403).end('Forbidden');
    return;
  }
  fs.readFile(file, (error, content) => {
    if (error) {
      response.writeHead(404).end('Not found');
      return;
    }
    const type = path.extname(file) === '.css' ? 'text/css; charset=utf-8' : 'text/html; charset=utf-8';
    response.writeHead(200, { 'Content-Type': type });
    response.end(content);
  });
});

(async () => {
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const browser = await chromium.launch({ headless: true, executablePath: edgePath });
  try {
    const page = await browser.newPage({ viewport: { width: 1500, height: 1180 } });
    await page.goto(`http://127.0.0.1:${server.address().port}/index.html`, { waitUntil: 'networkidle' });
    assert.equal(await page.locator('.variant').count(), 2, 'renders exactly two comparable variants');
    assert.equal(await page.locator('.phone').count(), 2, 'renders one mobile screen per variant');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true, 'comparison has no horizontal overflow');
    for (const phone of await page.locator('.phone').all()) {
      const box = await phone.boundingBox();
      assert.equal(Math.round(box.width), 390, 'phone evidence uses the approved 390px width');
      assert.equal(Math.round(box.height), 844, 'phone evidence uses the approved 844px height');
    }
    fs.mkdirSync(path.dirname(output), { recursive: true });
    await page.screenshot({ path: output, fullPage: true });
    const phones = page.locator('.phone');
    await phones.nth(0).screenshot({ path: path.join(path.dirname(output), '11a-mobile-edit-header-expanded-v1.png') });
    await phones.nth(1).screenshot({ path: path.join(path.dirname(output), '11c-mobile-edit-header-always-compact-v1.png') });
    console.log('MOBILE_EDIT_HEADER_COMPARISON_CHECKS_PASS');
    console.log(output);
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
