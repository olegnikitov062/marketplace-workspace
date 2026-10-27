/* Local real-Django LiveServer regression; private stdin, allowlisted stdout.
 * No artifacts, package downloads, remote connections or stored credentials.
 */
'use strict';
const { readFileSync, existsSync } = require('node:fs');
let browser;
function expect(value) { if (!value) throw new Error('check_failed'); }
async function main() {
  expect(!process.env.DEBUG && !process.env.PWDEBUG);
  const data = JSON.parse(readFileSync(0, 'utf8'));
  expect(/^http:\/\/localhost:[0-9]+$/.test(data.base));
  const modulePath = process.env.E206_PLAYWRIGHT_MODULE, executablePath = process.env.E206_CHROMIUM;
  expect(modulePath && executablePath && existsSync(modulePath) && existsSync(executablePath));
  const { chromium } = require(modulePath);
  browser = await chromium.launch({ executablePath, headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  let loginOriginSame = false, externalReferrerAbsent = false;
  await context.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== data.base) {
      if (url.origin === 'http://example.invalid') {
        externalReferrerAbsent = !(await request.allHeaders()).referer;
      }
      return route.abort(); // Never contact the external synthetic origin.
    }
    if (url.pathname === '/auth/mfa/login/' && request.method() === 'POST') {
      loginOriginSame = (await request.allHeaders()).origin === data.base;
    }
    return route.continue();
  });
  await page.goto(data.base + '/auth/mfa/login/');
  await page.locator('[name="auth-username"]').fill(data.username);
  await page.locator('[name="auth-password"]').fill(data.password);
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
    page.getByRole('button', { name: 'Продолжить', exact: true }).click(),
  ]);
  expect(loginOriginSame && new URL(page.url()).pathname === '/auth/mfa/setup/');
  expect(await page.evaluate(async () => (await fetch('/auth/session')).status) === 403);
  const checks = await page.evaluate(async () => {
    const csrf = document.querySelector('[name="csrfmiddlewaretoken"]').value;
    const post = async (headers, body) => (await fetch('/auth/logout', {
      method: 'POST', headers, body, redirect: 'manual',
    })).status;
    return {
      missing: await post({}, ''),
      // Sandboxed opaque origin is checked separately in the Django regression.
      accepted: await post({ 'Content-Type': 'application/x-www-form-urlencoded' },
        new URLSearchParams({ csrfmiddlewaretoken: csrf })),
    };
  });
  expect(checks.missing === 403 && checks.accepted === 200);
  await page.goto(data.base + '/auth/mfa/login/');
  await page.evaluate(() => {
    const link = document.createElement('a');
    link.href = 'http://example.invalid/'; link.id = 'external-referrer-check';
    link.textContent = 'Synthetic external link'; document.body.append(link);
  });
  await page.locator('#external-referrer-check').click();
  expect(externalReferrerAbsent);
  process.stdout.write('PASS real-browser-form-csrf-and-referrer\n');
}
main().catch(() => { process.stderr.write('FAIL browser-referrer-regression\n'); process.exitCode = 1; })
  .finally(async () => { if (browser) await browser.close(); });
