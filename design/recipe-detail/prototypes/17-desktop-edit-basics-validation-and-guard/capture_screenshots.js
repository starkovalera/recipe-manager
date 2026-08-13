const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const output = path.resolve(__dirname, '../../screenshots/edit-mode');
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  await page.goto(`file://${path.join(__dirname, 'index.html').replace(/\\/g, '/')}`);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: path.join(output, '17a-desktop-edit-basics-ingredients-v1.png'), fullPage: false });
  await page.getByRole('button', { name: 'Validation' }).click();
  await page.screenshot({ path: path.join(output, '17b-desktop-edit-validation-v1.png'), fullPage: false });
  await page.getByRole('button', { name: 'Guard' }).click();
  await page.screenshot({ path: path.join(output, '17c-desktop-edit-unsaved-guard-v1.png'), fullPage: false });
  console.log('DESKTOP_EDIT_SCREENSHOTS_CAPTURED');
  await browser.close();
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
