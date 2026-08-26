const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror:' + e.message));
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push('console:' + msg.text());
  });

  await page.goto('http://localhost:4173', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  const signInButton = page.locator('button').filter({ hasText: /تسجيل الدخول|Sign In|Login/i }).first();
  await signInButton.click();
  await page.waitForSelector('input[type="email"]', { timeout: 15000 });
  console.log('BUTTON_NAMES=' + JSON.stringify(await page.locator('button').allTextContents()));
  await page.fill('input[type="email"]', 'gbilal1717@gmail.com');
  await page.fill('input[type="password"]', 'DjBilal@2026');
  const submitButtons = page.locator('button').filter({ hasText: /تسجيل الدخول|Sign In|Login|Create Account|Register/i });
  console.log('SUBMIT_COUNT=' + await submitButtons.count());
  await submitButtons.last().click();
  await page.waitForTimeout(4000);

  const bodyText = await page.locator('body').innerText();
  console.log('BODY_SNIP=' + bodyText.slice(0, 2000));
  console.log('ERRORS=' + JSON.stringify(errors));
  console.log('URL=' + page.url());

  await browser.close();
})();
