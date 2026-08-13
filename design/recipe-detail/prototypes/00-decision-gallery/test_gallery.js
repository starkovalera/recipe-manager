const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await page.goto(`file://${path.join(__dirname, 'index.html').replace(/\\/g, '/')}`);
  await page.waitForLoadState('networkidle');

  if (await page.getByRole('heading', { name: 'Approved Recipe Detail decisions' }).count() !== 1) throw new Error('Gallery heading missing');
  if (await page.getByText('Desktop Basics & Ingredients', { exact: true }).count() !== 1) throw new Error('Desktop core card missing');
  if (await page.getByText('Compact Ingredients + one-item sheet', { exact: true }).count() !== 1) throw new Error('Mobile Ingredients card missing');
  if (await page.locator('img').count() < 10) throw new Error('Current evidence images missing');
  for (const image of await page.locator('img').all()) await image.scrollIntoViewIfNeeded();
  await page.waitForTimeout(100);
  if (!await page.locator('img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth > 0))) throw new Error('Broken gallery image');
  if (!await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)) throw new Error('Desktop horizontal overflow');

  await page.setViewportSize({ width: 390, height: 844 });
  if (!await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)) throw new Error('Mobile horizontal overflow');
  if (pageErrors.length) throw new Error(pageErrors.join(' | '));

  console.log('DECISION_GALLERY_CHECKS_PASS');
  await browser.close();
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
