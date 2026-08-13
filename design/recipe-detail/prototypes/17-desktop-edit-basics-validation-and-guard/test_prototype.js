const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(`file://${path.join(__dirname, 'index.html').replace(/\\/g, '/')}`);
  await page.waitForLoadState('networkidle');
  if (await page.locator('body').evaluate(node => node.scrollWidth > node.clientWidth)) throw new Error('Horizontal overflow');
  if (await page.getByRole('heading', { name: 'Basics' }).count() !== 1) throw new Error('Basics missing');
  if (await page.getByLabel('Cooking time').inputValue() !== '45') throw new Error('Cooking time state missing');
  await page.getByRole('button', { name: 'Validation' }).click();
  if (await page.getByText('Enter a positive whole number or leave this empty.', { exact: true }).count() !== 2) throw new Error('Whole-number validation missing');
  await page.getByRole('button', { name: 'Guard' }).click();
  if (await page.getByRole('dialog', { name: 'Unsaved changes' }).count() !== 1) throw new Error('Guard missing');
  if (errors.length) throw new Error(errors.join(' | '));
  console.log('DESKTOP_EDIT_CORE_CHECKS_PASS');
  await browser.close();
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
