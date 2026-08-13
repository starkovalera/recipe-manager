const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const prototypeDir = __dirname;
const outputDir = path.resolve(prototypeDir, '../../screenshots/edit-mode');
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const server = http.createServer((request, response) => {
  const relative = request.url === '/' ? 'index.html' : request.url.replace(/^\//, '');
  const file = path.resolve(prototypeDir, relative);
  if (!file.startsWith(prototypeDir + path.sep) && file !== path.join(prototypeDir, 'index.html')) return response.writeHead(403).end('Forbidden');
  fs.readFile(file, (error, content) => {
    if (error) return response.writeHead(404).end('Not found');
    response.writeHead(200, { 'Content-Type': path.extname(file) === '.css' ? 'text/css; charset=utf-8' : 'text/html; charset=utf-8' });
    response.end(content);
  });
});

(async () => {
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const browser = await chromium.launch({ headless:true, executablePath:edgePath });
  try {
    const page = await browser.newPage({ viewport:{ width:1500, height:1180 } });
    await page.goto(`http://127.0.0.1:${server.address().port}/index.html`, { waitUntil:'networkidle' });
    assert.equal(await page.locator('.variant').count(), 2);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), true);
    for (const phone of await page.locator('.phone').all()) {
      const box = await phone.boundingBox();
      assert.deepEqual([Math.round(box.width), Math.round(box.height)], [390, 844]);
    }
    fs.mkdirSync(outputDir, { recursive:true });
    await page.screenshot({ path:path.join(outputDir,'12-mobile-edit-save-actions-comparison-v1.png'), fullPage:true });
    await page.locator('.phone').nth(0).screenshot({ path:path.join(outputDir,'12a-mobile-edit-save-top-toolbar-v1.png') });
    await page.locator('.phone').nth(1).screenshot({ path:path.join(outputDir,'12b-mobile-edit-save-bottom-accessory-v1.png') });
    console.log('MOBILE_EDIT_SAVE_ACTION_COMPARISON_CHECKS_PASS');
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error.stack || error); process.exitCode=1; });
