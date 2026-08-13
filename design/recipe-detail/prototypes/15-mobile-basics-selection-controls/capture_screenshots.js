const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const prototypeDir = __dirname;
const outputDir = path.resolve(prototypeDir, '../../screenshots/edit-mode');
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

function startServer() {
  const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8' };
  const server = http.createServer((request, response) => {
    const relative = request.url === '/' ? 'index.html' : request.url.split('?')[0].replace(/^\//, '');
    const file = path.resolve(prototypeDir, relative);
    fs.readFile(file, (error, content) => {
      if (error) return response.writeHead(404).end('Not found');
      response.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
      response.end(content);
    });
  });
  return new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', () => resolve(server)); });
}

async function presentMobilePrototype(page, url, controlName) {
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: controlName }).click();
  await page.addStyleTag({ content: '.prototype-toolbar,.review-note{display:none!important}.stage{display:block!important;width:100%!important;margin:0!important}.phone{width:100%!important;height:100vh!important;padding:0!important;border:0!important;border-radius:0!important;box-shadow:none!important}.phone-notch{display:none!important}.mobile-edit-surface,#layer-root{border-radius:0!important}#layer-root{inset:0!important}' });
  await page.locator('.editor-scroll').evaluate(element => { element.scrollTop = 0; });
}

(async () => {
  const server = await startServer();
  const browser = await chromium.launch({ headless: true, executablePath: edgePath });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
    const url = `http://127.0.0.1:${server.address().port}/index.html`;
    fs.mkdirSync(outputDir, { recursive: true });

    await presentMobilePrototype(page, url, /A.*Hybrid controls/);
    await page.screenshot({ path: path.join(outputDir, '15a-mobile-basics-hybrid-v2.png') });

    await presentMobilePrototype(page, url, /B.*Selection sheets/);
    await page.screenshot({ path: path.join(outputDir, '15b-mobile-basics-sheets-v1.png') });

    await presentMobilePrototype(page, url, /A.*Hybrid controls/);
    await page.getByRole('button', { name: 'Source, Instagram', exact: true }).click();
    await page.screenshot({ path: path.join(outputDir, '15c-mobile-basics-source-sheet-v1.png') });
    console.log('MOBILE_BASICS_SELECTION_CONTROLS_SCREENSHOTS_CAPTURED');
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
