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
  fs.readFile(file, (error, content) => {
    if (error) return response.writeHead(404).end('Not found');
    response.writeHead(200, { 'Content-Type':path.extname(file) === '.css' ? 'text/css; charset=utf-8' : path.extname(file) === '.js' ? 'text/javascript; charset=utf-8' : 'text/html; charset=utf-8' });
    response.end(content);
  });
});

(async () => {
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const browser = await chromium.launch({ headless:true, executablePath:edgePath });
  try {
    const page = await browser.newPage({ viewport:{ width:1100,height:980 } });
    const url = `http://127.0.0.1:${server.address().port}/index.html`;
    fs.mkdirSync(outputDir, { recursive:true });
    await page.goto(url, { waitUntil:'networkidle' });
    await page.getByRole('button', { name:/Basics 7 fields/ }).click();
    await page.locator('.phone').screenshot({ path:path.join(outputDir,'14a-mobile-edit-basics-v1.png') });
    await page.getByRole('button', { name:/Ingredients 12 of 50/ }).click();
    await page.locator('.phone').screenshot({ path:path.join(outputDir,'14b-mobile-edit-ingredients-v1.png') });
    console.log('MOBILE_EDIT_REFINEMENT_SCREENSHOTS_CAPTURED');
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error.stack || error); process.exitCode=1; });
