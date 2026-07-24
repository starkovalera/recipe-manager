const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const prototypeDir = __dirname;
const outputDir = path.resolve(prototypeDir, '../../screenshots/06-mobile-recipe-detail');
const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

function startServer() {
  const types = { '.css': 'text/css; charset=utf-8', '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml' };
  const server = http.createServer((request, response) => {
    const relative = request.url === '/' ? 'index.html' : request.url.split('?')[0].replace(/^\//, '');
    const file = path.resolve(prototypeDir, relative);
    if (!file.startsWith(prototypeDir + path.sep) && file !== path.join(prototypeDir, 'index.html')) return response.writeHead(403).end('Forbidden');
    fs.readFile(file, (error, content) => {
      if (error) return response.writeHead(404).end('Not found');
      response.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
      response.end(content);
    });
  });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

async function fresh(page, url, scenario, context = 'default') {
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.selectOption('#scenario-select', scenario);
  await page.selectOption('#context-select', context);
  await page.addStyleTag({ content: '.prototype-toolbar{display:none!important}' });
  await page.locator('#prototype-root [data-product-surface]').waitFor();
  await page.evaluate(() => Promise.all([...document.images].map(image => image.complete ? Promise.resolve() : new Promise(resolve => image.addEventListener('load', resolve, { once: true })) )));
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(outputDir, name) });
}

(async () => {
  fs.mkdirSync(outputDir, { recursive: true });
  const server = await startServer();
  const browser = await chromium.launch({ headless: true, executablePath: edgePath });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const url = `http://127.0.0.1:${server.address().port}/index.html`;

    await fresh(page, url, 'normal');
    await shot(page, 'mobile-normal-390x844.png');

    await fresh(page, url, 'flagged');
    await shot(page, 'mobile-flagged-390x844.png');

    await fresh(page, url, 'normal', 'focus');
    await shot(page, 'mobile-focus-ingredients-390x844.png');
    await page.getByRole('tab', { name: 'Instructions' }).click();
    await shot(page, 'mobile-focus-instructions-390x844.png');

    await fresh(page, url, 'flagged');
    await page.getByRole('button', { name: /Media/ }).click();
    await shot(page, 'mobile-media-sheet-390x844.png');

    await fresh(page, url, 'flagged');
    await page.getByRole('button', { name: 'Import info', exact: true }).click();
    await shot(page, 'mobile-import-info-sheet-390x844.png');
    await page.getByRole('button', { name: 'Remove Packaging photo' }).click();
    await shot(page, 'mobile-resource-confirmation-390x844.png');

    await fresh(page, url, 'normal');
    await page.getByRole('button', { name: 'More recipe actions' }).click();
    await page.getByRole('menuitem', { name: 'Delete recipe…' }).click();
    await shot(page, 'mobile-delete-recipe-390x844.png');

    await page.setViewportSize({ width: 360, height: 800 });
    await fresh(page, url, 'noCover');
    await shot(page, 'mobile-long-title-360x800.png');
    console.log('MOBILE_RECIPE_DETAIL_SCREENSHOTS_CAPTURED');
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
