import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const template = readFileSync(new URL('../../backend/account_security/templates/account_security/panel.html', import.meta.url), 'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1];

function page(fetch, action = 'refresh') {
  let submit;
  const status = { textContent: '', focus() { this.focused = true; } };
  const button = { disabled: false };
  const navigations = [];
  const form = { action: 'https://testserver/auth/security/sessions/test/revoke/', dataset: { securityAction: action }, addEventListener(name, callback) { submit = callback; } };
  const document = {
    querySelectorAll(selector) { return selector.endsWith('button') ? [button] : [form]; },
    getElementById() { return status; },
  };
  const context = vm.createContext({ document, fetch, URLSearchParams, AbortSignal,
    FormData: class { *[Symbol.iterator]() { yield ['csrfmiddlewaretoken', 'synthetic-csrf']; } },
    location: { assign(path) { navigations.push(path); }, reload() { navigations.push('reload'); } },
  });
  vm.runInContext(script, context);
  return { submit: () => submit({ preventDefault() {} }), status, button, navigations };
}

test('Отзыв отправляет CSRF и обновляет страницу только после подтверждённого успеха', async () => {
  const calls = [];
  const view = page(async (url, options) => { calls.push({ url, options }); return { ok: true, json: async () => ({ status: 'ok' }) }; });
  await view.submit();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.credentials, 'same-origin');
  assert.equal(calls[0].options.redirect, 'error');
  assert.equal(calls[0].options.body.toString(), 'csrfmiddlewaretoken=synthetic-csrf');
  assert.deepEqual(view.navigations, ['reload']);
});

test('Выход возвращает к форме входа после ответа сервера', async () => {
  const view = page(async () => ({ ok: true, json: async () => ({ status: 'ok' }) }), 'login');
  await view.submit();
  assert.deepEqual(view.navigations, ['/auth/basework/login']);
});

for (const [code, expected] of [[403, 'Подтвердите личность'], [429, 'Повторите позже'], [500, 'Сервер не подтвердил']]) {
  test(`Ошибка ${code} остаётся на странице и не объявляется успехом`, async () => {
    const view = page(async () => ({ ok: false, status: code }));
    await view.submit();
    assert.deepEqual(view.navigations, []);
    assert.ok(view.status.textContent.includes(expected));
    assert.equal(view.status.focused, true);
    assert.equal(view.button.disabled, false);
  });
}

test('Обрыв запроса и неверный JSON требуют проверки состояния перед повтором', async () => {
  for (const fetch of [async () => { throw new Error('network'); }, async () => ({ ok: true, json: async () => ({ status: 'unknown' }) })]) {
    const view = page(fetch);
    await view.submit();
    assert.deepEqual(view.navigations, []);
    assert.ok(view.status.textContent.includes('перед повторной попыткой'));
    assert.equal(view.button.disabled, false);
  }
});

test('Повторный клик во время запроса не отправляет второй отзыв', async () => {
  let finish;
  let calls = 0;
  const view = page(() => { calls += 1; return new Promise(resolve => { finish = resolve; }); });
  const first = view.submit();
  assert.equal(view.button.disabled, true);
  await view.submit();
  assert.equal(calls, 1);
  finish({ ok: true, json: async () => ({ status: 'ok' }) });
  await first;
});
