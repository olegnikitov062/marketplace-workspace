/* Synthetic E2-06 browser/operator rehearsal. No trace, screenshots, storage
 * dumps, secret files, or raw error messages. Uses already-installed Playwright.
 * Private SSH stdout is captured ONLY in this process, never forwarded to logs.
 * Run only after the separate rehearsal plan is published and authorized.
 */
'use strict';
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');
const { existsSync } = require('node:fs');
const run = promisify(execFile);
const BASE = 'http://127.0.0.1:18767';
const CONTROLLER = 'marketplace-e206-owner-check-controller';
const ISSUER = 'marketplace-e206-owner-check-issuer';
const modulePath = process.env.E206_PLAYWRIGHT_MODULE;
const executablePath = process.env.E206_CHROMIUM;
const revision = process.argv[2];
let phase = 'local-preconditions';
const passed = [];
function expect(condition) { if (!condition) throw new Error('check_failed'); }
function mark(name) { passed.push(name); process.stdout.write(`PASS ${name}\n`); }
async function ssh(command) {
  const result = await run('ssh', ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', 'wb-prod', command],
    { timeout: 90000, maxBuffer: 65536, windowsHide: true, encoding: 'utf8' });
  return result.stdout.trim(); // Private transport: never log stdout/stderr.
}
async function rpc(action, options = []) {
  expect(['credentials', 'token', 'status', 'operator_issue', 'block', 'blocked_operator', 'finish'].includes(action));
  expect(options.every(x => ['--pending', '--kind', 'valid', 'wrong', 'expired', '--user', 'owner', 'sessions'].includes(x)));
  const container = ['operator_issue', 'blocked_operator'].includes(action) ? ISSUER : CONTROLLER;
  return JSON.parse(await ssh(`docker exec -i ${container} python -m tools.owner_rehearsal ${action} --private-pipe ${options.join(' ')} </dev/null`));
}
async function fetchStatus(page, path, method = 'GET', csrf = false) {
  return page.evaluate(async ({ path, method, csrf }) => {
    const headers = {};
    if (csrf) headers['X-CSRFToken'] = (await (await fetch('/auth/csrf')).json()).csrfToken;
    return (await fetch(path, { method, headers, redirect: 'manual' })).status;
  }, { path, method, csrf });
}
async function submit(page, button) {
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
    page.getByRole('button', { name: button, exact: true }).click(),
  ]);
}
async function passwordStep(page, user, password = user.password) {
  const response = await page.goto(BASE + '/auth/mfa/login/');
  expect((await response.allHeaders())['referrer-policy'] === 'same-origin');
  await page.locator('[name="auth-username"]').fill(user.username);
  await page.locator('[name="auth-password"]').fill(password);
  await submit(page, 'Продолжить');
}
async function otp(page, user, { pending = false, kind = 'valid', remember = false, value } = {}) {
  const options = ['--user', user, '--kind', kind];
  if (pending) options.push('--pending');
  const token = value === undefined ? (await rpc('token', options)).token : value;
  await page.locator(`[name="${pending ? 'generator-token' : 'token-otp_token'}"]`).fill(token);
  if (remember) await page.locator('[name="token-remember"]').check();
  await submit(page, 'Продолжить');
  return token;
}
async function enroll(page, user, negative = false) {
  expect(new URL(page.url()).pathname === '/auth/mfa/setup/');
  expect(await fetchStatus(page, '/auth/session') === 403);
  await submit(page, 'Продолжить');
  await page.locator('[name="generator-token"]').waitFor();
  expect(await page.locator('img').evaluate(img => img.complete ? img.naturalWidth > 0 : new Promise(resolve => {
    const timer = setTimeout(() => resolve(false), 10000);
    img.addEventListener('load', () => { clearTimeout(timer); resolve(img.naturalWidth > 0); }, { once: true });
    img.addEventListener('error', () => { clearTimeout(timer); resolve(false); }, { once: true });
  })));
  if (negative) {
    for (const kind of ['wrong', 'expired']) {
      await otp(page, user, { pending: true, kind });
      expect(await page.locator('[name="generator-token"]').count() === 1);
      expect(await fetchStatus(page, '/auth/session') === 403);
      await page.waitForTimeout(2200); // Actual django-otp throttle; no reset or clock patch.
    }
  }
  const last = await otp(page, user, { pending: true });
  await page.locator('code').first().waitFor();
  const codes = await page.locator('code').allTextContents(); // Secret values stay in memory.
  expect(codes.length === 10 && new Set(codes).size === 10);
  expect(await fetchStatus(page, '/auth/session') === 401);
  await page.goto(BASE + '/auth/mfa/setup/');
  expect(await page.locator('code').count() === 0);
  return { codes, last };
}
async function login(page, user, key, options = {}) {
  await passwordStep(page, user, options.password);
  const requested = await page.locator('[name="token-otp_token"]').count() === 1;
  expect(requested === !options.trusted);
  if (requested) {
    expect(await fetchStatus(page, '/auth/session') !== 200);
    if (options.replay) {
      await otp(page, key, { value: options.replay });
      expect(await page.locator('[name="token-otp_token"]').count() === 1);
      expect(await fetchStatus(page, '/auth/session') !== 200);
      await page.waitForTimeout(1200);
    }
    await otp(page, key, { remember: options.remember });
  }
  expect(await fetchStatus(page, '/auth/session') === 200);
}
async function postExistingForm(page, action) {
  return page.evaluate(async action => {
    const form = Array.from(document.forms).find(f => new URL(f.action).pathname === action);
    if (!form) return -1;
    return (await fetch(form.action, { method: 'POST', body: new URLSearchParams(new FormData(form)), redirect: 'manual' })).status;
  }, action);
}
async function recovery(page, user, code, operator = false, success = true, password = user.password) {
  await page.goto(BASE + (operator ? '/auth/mfa/operator-recovery/' : '/auth/mfa/recovery/'));
  await page.locator('[name="username"]').fill(user.username);
  await page.locator('[name="password"]').fill(password);
  await page.locator('[name="code"]').fill(code);
  await submit(page, 'Подтвердить');
  expect((new URL(page.url()).pathname === '/auth/mfa/setup/') === success);
  expect(await fetchStatus(page, '/auth/session') !== 200);
}

async function main() {
  expect(/^[0-9a-f]{40}$/.test(revision || '') && modulePath && executablePath);
  expect(existsSync(modulePath) && existsSync(executablePath));
  expect(!process.env.DEBUG && !process.env.PWDEBUG); // Debug logging can contain form values.
  const { chromium } = require(modulePath); // No npm, npx, installer or browser download.
  const expectedSource = `/home/adm_user/marketplace-workspace/beta/app/releases/${revision}/backend`;
  for (const container of [CONTROLLER, ISSUER]) {
    const mounts = JSON.parse(await ssh(`docker inspect --format '{{json .Mounts}}' ${container}`));
    expect(mounts.some(m => m.Destination === '/workspace' && !m.RW && m.Source === expectedSource));
  }
  const secrets = await rpc('credentials');
  const browser = await chromium.launch({ executablePath, headless: true });
  const contexts = [];
  let pageErrors = 0;
  async function fresh() {
    const context = await browser.newContext();
    contexts.push(context);
    await context.route('**/*', route => new URL(route.request().url()).origin === BASE ? route.continue() : route.abort());
    const page = await context.newPage();
    page.setDefaultTimeout(60000);
    page.setDefaultNavigationTimeout(120000);
    page.on('pageerror', () => { pageErrors++; });
    return page;
  }
  try {
    phase = 'mandatory-enrollment';
    const owner = await fresh();
    await passwordStep(owner, secrets.owner);
    const initial = await enroll(owner, 'owner', true);
    mark('mandatory-enrollment-invalid-expired-valid-one-time-code-display');
    phase = 'totp-login-and-replay';
    await login(owner, secrets.owner, 'owner', { replay: initial.last, remember: true });
    expect(await fetchStatus(owner, '/auth/security/disable/', 'POST', true) === 403);
    expect(await fetchStatus(owner, '/auth/mfa/recovery/', 'POST') === 403);
    mark('totp-login-replay-denial-owner-disable-denial-csrf');

    phase = 'session-and-trust-lifecycle';
    const a = await fresh(), b = await fresh();
    await passwordStep(a, secrets.sessions);
    await enroll(a, 'sessions');
    await login(a, secrets.sessions, 'sessions', { remember: true });
    await login(b, secrets.sessions, 'sessions');
    expect(await postExistingForm(a, '/auth/logout') === 200);
    expect(await fetchStatus(a, '/auth/session') === 401 && await fetchStatus(b, '/auth/session') === 200);
    await login(a, secrets.sessions, 'sessions', { trusted: true });
    await a.goto(BASE + '/auth/security/confirm/');
    await a.locator('[name="password"]').fill(secrets.sessions.password);
    await a.locator('[name="token"]').fill((await rpc('token', ['--user', 'sessions'])).token);
    await submit(a, 'Подтвердить');
    const otherSession = await a.evaluate(() => Array.from(document.querySelectorAll('li')).find(li =>
      !li.querySelector('strong') && li.querySelector('form[action*="/sessions/"]'))?.querySelector('form').getAttribute('action'));
    expect(otherSession && await postExistingForm(a, otherSession) === 200);
    expect(await fetchStatus(b, '/auth/session') === 401 && await fetchStatus(a, '/auth/session') === 200);
    expect(await postExistingForm(a, '/auth/security/logout-all/') === 200);
    await login(a, secrets.sessions, 'sessions'); // MFA required again: trust was revoked.
    expect(await postExistingForm(a, '/auth/security/logout-all/') === 200);
    mark('logout-current-selected-session-reauth-trust-and-logout-all');

    phase = 'backup-code-recovery';
    const c = await fresh(), replay = await fresh();
    await recovery(c, secrets.owner, initial.codes[0]);
    expect(await fetchStatus(owner, '/auth/session') === 401);
    await recovery(replay, secrets.owner, initial.codes[0], false, false);
    await enroll(c, 'owner');
    await login(c, secrets.owner, 'owner', { remember: true });
    expect((await rpc('status')).ownership_unchanged);
    mark('backup-code-single-use-limited-reenrollment-session-revocation');

    phase = 'real-operator-cli-recovery';
    const issued = await rpc('operator_issue'); // Actual getpass CLI under the real migrator LOGIN.
    expect(issued.wrong_proof_denied && issued.wrong_owner_denied && issued.ownership_and_passwords_unchanged);
    expect(await fetchStatus(c, '/auth/session') === 401);
    const d = await fresh(), reused = await fresh();
    await recovery(d, secrets.owner, issued.permit, true);
    await recovery(reused, secrets.owner, issued.permit, true, false);
    const recovered = await enroll(d, 'owner');
    await login(d, secrets.owner, 'owner', { remember: true });
    expect((await rpc('status')).ownership_unchanged);
    mark('operator-proof-role-binding-single-use-permit-limited-recovery');

    phase = 'password-change-retains-mfa';
    await d.goto(BASE + '/auth/security/password/');
    await d.locator('[name="old_password"]').fill(secrets.owner.password);
    await d.locator('[name="new_password1"]').fill(secrets.next_password);
    await d.locator('[name="new_password2"]').fill(secrets.next_password);
    await submit(d, 'Подтвердить');
    expect(await fetchStatus(d, '/auth/session') === 401);
    expect((await rpc('status')).trusted === 0);
    await login(d, secrets.owner, 'owner', { password: secrets.next_password });
    mark('password-change-revokes-trust-and-retains-mfa');

    phase = 'blocked-recovery';
    await rpc('block');
    expect(await fetchStatus(d, '/auth/session') === 401);
    await recovery(reused, secrets.owner, recovered.codes[0], false, false, secrets.next_password);
    expect((await rpc('blocked_operator')).blocked_operator_denied);
    mark('block-revokes-session-denies-code-and-operator-recovery');
    phase = 'voluntary-member';
    const member = await fresh();
    await passwordStep(member, secrets.member);
    expect(await fetchStatus(member, '/auth/session') === 200);
    expect(await member.locator('[name="token-otp_token"]').count() === 0);
    await postExistingForm(member, '/auth/logout');
    mark('unenrolled-member-password-login');
    phase = 'final-state';
    expect(pageErrors === 0);
    mark('no-browser-script-errors');
    const final = await rpc('finish');
    expect(final.ownership_unchanged && final.invitations === 0);
    mark('unchanged-organizations-memberships-and-blocked-password');
    process.stdout.write(JSON.stringify({ result: 'PASS', checks: passed.length, fullBrowser: true, actualOperatorCli: true,
      limits: 'synthetic isolated cluster; no real-owner proof or main-key custody; no public TLS or business export' }) + '\n');
  } finally {
    for (const context of contexts) await context.close().catch(() => {});
    await browser.close();
  }
}
main().catch(() => {
  process.stderr.write(`FAIL ${phase}; preserve rehearsal state; no secret or error detail emitted\n`);
  process.exitCode = 1;
});
