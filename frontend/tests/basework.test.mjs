import assert from 'node:assert/strict';
import { test } from 'node:test';
import { requestAuthOptions, oidcLoginPath } from '../src/basework/authOptions.ts';
import { applications, applicationPanel, applicationPath, directory, parseBootstrap, requestBootstrap,
  resolveRoute, searchApplications } from '../src/basework/model.ts';

const authenticated = (items = []) => ({
  session: { status: 'authenticated', user: { id: 'fixture-user', displayName: 'Тестовая сессия' } },
  applications: items,
});
const allowed = id => ({ id, access: 'allowed', availability: 'available' });
const ready = items => parseBootstrap(authenticated(items));
const response = (status, body, type = 'application/json') => new Response(type === 'application/json' ? JSON.stringify(body) : body, { status, headers: { 'Content-Type': type } });
const signal = () => new AbortController().signal;

test('Вход Authelia доступен только по явному boolean флагу; адрес фиксирован', async () => {
  assert.equal(oidcLoginPath, '/auth/basework/oidc/login');
  for (const [body, expected] of [[{ oidcEnabled: true }, 'enabled'], [{ oidcEnabled: false }, 'disabled'],
    [{ oidcEnabled: 'true' }, 'unavailable'], [{}, 'unavailable'], [null, 'unavailable']]) {
    assert.equal(await requestAuthOptions(signal(), async (url, options) => {
      assert.equal(url, '/api/v1/basework/auth-options');
      assert.equal(options.cache, 'no-store');
      assert.equal(options.redirect, 'error');
      assert.equal(options.credentials, 'same-origin');
      return response(200, body);
    }), expected);
  }
});

test('Недоступный, перенаправленный или неверный ответ не включает Authelia', async () => {
  for (const result of [response(503, {}), response(200, '<html>', 'text/html'),
    new Response('{', { headers: { 'Content-Type': 'application/json' } })]) {
    assert.equal(await requestAuthOptions(signal(), async () => result), 'unavailable');
  }
  await assert.rejects(requestAuthOptions(signal(), async () => { throw new TypeError('network'); }));
});

test('Каталог ограничен семью согласованными приложениями', () => {
  assert.deepEqual(applications.map(item => item.id), ['marketplace', 'reports', 'sources', 'airflow', 'bloggers', 'faq', 'rooms']);
  assert.equal(new Set(applications.map(item => item.id)).size, 7);
});

test('Данные сервера не расширяют каталог и не задают произвольные адреса', () => {
  const resource = ready([allowed('faq'), allowed('fbs'), allowed('finkos'), allowed('fanbox'), { ...allowed('rooms'), href: 'https://example.invalid', title: 'Чужой заголовок' }]);
  assert.deepEqual(directory(resource).map(item => item.id), ['faq', 'rooms']);
  assert.equal(directory(resource)[1].title, 'Переговорки');
  assert.equal(applicationPath('rooms'), '/basework/apps/rooms');
});

test('Запрещённые и отсутствующие разрешения скрыты из меню и поиска', () => {
  const resource = ready([allowed('faq'), { ...allowed('rooms'), access: 'denied' }]);
  assert.deepEqual(directory(resource).map(item => item.id), ['faq']);
  assert.equal(searchApplications(directory(resource), 'переговорки').length, 0);
  assert.equal(applicationPanel(resource, 'rooms'), 'forbidden');
  assert.equal(applicationPanel(resource, 'reports'), 'forbidden');
});

test('Пустой список назначений остаётся пустым', () => {
  assert.deepEqual(directory(ready([])), []);
  assert.equal(applicationPanel(ready([]), 'faq'), 'forbidden');
});

test('Анонимная, истёкшая и частичная сессии не получают приложений из ответа', () => {
  for (const status of ['anonymous', 'expired', 'mfa_required']) {
    const resource = parseBootstrap({ ...authenticated([allowed('faq')]), session: { status } });
    assert.equal(resource.status, status);
    assert.deepEqual(directory(resource), []);
    assert.equal(applicationPanel(resource, 'faq'), status);
  }
});

test('Неизвестная доступность не превращается в разрешение', () => {
  for (const status of ['error', 'unavailable']) {
    const entries = directory({ status });
    assert.equal(entries.length, 7);
    assert.ok(entries.every(item => item.access === 'unknown' && item.availability === 'unavailable'));
    assert.equal(applicationPanel({ status }, 'faq'), status);
  }
  for (const status of ['loading', 'forbidden', 'anonymous', 'expired', 'mfa_required']) assert.deepEqual(directory({ status }), []);
});

test('Отказ одного модуля сохраняет доступ к соседнему', () => {
  const resource = ready([{ ...allowed('airflow'), availability: 'unavailable' }, allowed('faq')]);
  assert.equal(applicationPanel(resource, 'airflow'), 'module_unavailable');
  assert.equal(applicationPanel(resource, 'faq'), 'not_connected');
  assert.equal(directory(resource).length, 2);
});

test('Дублирующие и неполные назначения отклоняются целиком', () => {
  for (const items of [[allowed('faq'), allowed('faq')], [{ id: 'faq' }], [{ ...allowed('faq'), access: 'admin' }], [{ ...allowed('faq'), availability: 'ready' }], [null]]) {
    assert.equal(ready(items).status, 'error');
  }
});

test('Повреждённая идентичность и формат не подтверждают сессию', () => {
  for (const value of [null, [], {}, { session: {} }, { ...authenticated(), applications: null },
    { ...authenticated(), session: { status: 'admin' } },
    { ...authenticated(), session: { status: 'authenticated', user: { id: '', displayName: 'Имя' } } },
    { ...authenticated(), session: { status: 'authenticated', user: { id: 'id', displayName: ' ' } } },
    { ...authenticated(), session: { status: 'authenticated', user: { id: 'id', displayName: 'x'.repeat(501) } } }]) {
    assert.equal(parseBootstrap(value).status, 'error');
  }
});

test('Поиск учитывает регистр, ё, ключевые слова и несколько слов', () => {
  const entries = directory(ready(applications.map(item => allowed(item.id))));
  assert.deepEqual(searchApplications(entries, ' ОТЧЕТЫ wb ').map(item => item.id), ['reports']);
  assert.deepEqual(searchApplications(entries, 'журналы').map(item => item.id), ['airflow']);
  assert.deepEqual(searchApplications(entries, 'faq').map(item => item.id), ['faq']);
  assert.deepEqual(searchApplications(entries, 'несуществующее'), []);
  assert.equal(searchApplications(entries, '').length, 7);
});

test('Корневые и служебные маршруты разрешаются без данных', () => {
  for (const path of ['/', '/basework', '/basework/']) assert.equal(resolveRoute(path).kind, 'home');
  assert.equal(resolveRoute('/basework/profile').kind, 'profile');
  assert.equal(resolveRoute('/basework/notifications/').kind, 'notifications');
});

test('Каждое приложение имеет прямой адрес; исключённые и повреждённые адреса дают 404', () => {
  for (const item of applications) {
    const route = resolveRoute(applicationPath(item.id));
    assert.equal(route.kind, 'application');
    assert.equal(route.application.id, item.id);
    assert.equal(resolveRoute(applicationPath(item.id) + '/').kind, 'application');
  }
  for (const path of ['/basework/apps/fbs', '/basework/apps/finkos', '/basework/apps/fanbox', '/basework/unknown', '/basework//', '/basework/apps/%66aq', '/basework/apps/faq/extra']) assert.equal(resolveRoute(path).kind, 'missing');
});

test('Запрос API имеет только локальный адрес, cookie сессии, запрет кеширования и перенаправлений', async () => {
  const abortSignal = signal();
  let calls = 0;
  const resource = await requestBootstrap(abortSignal, async (url, options) => {
    calls++;
    assert.equal(url, '/api/v1/basework/bootstrap');
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.redirect, 'error');
    assert.equal(options.signal, abortSignal);
    assert.equal(options.body, undefined);
    assert.equal(options.headers.Authorization, undefined);
    return response(200, authenticated([allowed('faq')]));
  });
  assert.equal(calls, 1);
  assert.equal(resource.status, 'ready');
});

for (const [status, body, expected] of [
  [401, {}, 'anonymous'], [401, { status: 'session_expired' }, 'expired'],
  [403, {}, 'forbidden'], [403, { status: 'mfa_required' }, 'mfa_required'],
  [404, {}, 'unavailable'], [500, {}, 'error'], [502, {}, 'unavailable'],
  [503, {}, 'unavailable'], [504, {}, 'unavailable'], [200, {}, 'error'],
]) test(`API ${status}: ${expected}`, async () => {
  assert.equal((await requestBootstrap(signal(), async () => response(status, body))).status, expected);
});

test('HTML и повреждённый JSON не выдаются за пустой успешный ответ', async () => {
  assert.equal((await requestBootstrap(signal(), async () => response(200, '<html>Вход</html>', 'text/html'))).status, 'error');
  assert.equal((await requestBootstrap(signal(), async () => new Response('{', { headers: { 'Content-Type': 'application/json' } }))).status, 'error');
});

test('Сетевая ошибка остаётся отказом запроса, а не пустыми данными', async () => {
  await assert.rejects(requestBootstrap(signal(), async () => { throw new TypeError('Сеть недоступна'); }), TypeError);
});

import { accessRefreshMs, accessTimeoutMs, createAccessLoader, requestLogout } from '../src/basework/session.ts';

const flush = async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); };
const pending = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };

test('Фоновая проверка и тайм-аут укладываются в 60 секунд', () => {
  assert.equal(accessRefreshMs, 30000);
  assert.ok(accessRefreshMs + accessTimeoutMs < 60000);
});

test('Поздний положительный ответ не возвращает отозванные права', async () => {
  const old = pending(), current = pending(), states = [];
  let count = 0;
  const loader = createAccessLoader(() => (++count === 1 ? old.promise : current.promise), value => states.push(value.status));
  loader.refresh(); loader.refresh();
  current.resolve({ status: 'expired' }); await flush();
  old.resolve(ready([allowed('faq')])); await flush();
  assert.equal(states.at(-1), 'expired');
  loader.stop();
});

test('После тайм-аута старый ответ игнорируется, предыдущий доступ очищен', async () => {
  const old = pending(), states = [];
  let deadline;
  const loader = createAccessLoader(() => old.promise, value => states.push(value.status), handler => { deadline = handler; return 1; }, () => {});
  loader.refresh(); deadline();
  old.resolve(ready([allowed('faq')])); await flush();
  assert.deepEqual(states, ['loading', 'unavailable']);
  loader.stop();
});

test('Отмена перед выходом отбрасывает ответ выполнявшегося bootstrap', async () => {
  const old = pending(), states = [];
  const loader = createAccessLoader(() => old.promise, value => states.push(value.status));
  loader.refresh(); loader.clear();
  old.resolve(ready([allowed('faq')])); await flush();
  assert.equal(states.at(-1), 'loading');
  loader.stop();
});

test('Фоновый опрос сохраняет интерфейс до результата и очищает доступ при отказе', async () => {
  const states = [];
  const loader = createAccessLoader(async () => ({ status: 'expired' }), value => states.push(value.status));
  loader.refresh(true); await flush();
  assert.deepEqual(states, ['expired']);
  loader.stop();
});

test('Выход — CSRF и отдельный POST; токен провайдера не используется', async () => {
  for (const all of [false, true]) {
    const calls = [];
    await requestLogout(all, async (url, options) => {
      calls.push([url, options]);
      return response(200, url === '/auth/csrf' ? { csrfToken: 'a'.repeat(64) } : { status: 'ok' });
    });
    assert.equal(calls[1][0], all ? '/api/v1/basework/logout-all' : '/api/v1/basework/logout');
    assert.equal(calls[1][1].method, 'POST');
    assert.equal(calls[1][1].headers['X-CSRFToken'], 'a'.repeat(64));
    assert.equal(calls[1][1].credentials, 'same-origin');
    assert.equal(calls[1][1].redirect, 'error');
  }
});

test('Ошибки CSRF, сети и сервера не объявляются выходом', async () => {
  await assert.rejects(requestLogout(false, async () => response(200, { csrfToken: 'bad' })));
  await assert.rejects(requestLogout(false, async url => url === '/auth/csrf' ? response(200, { csrfToken: 'a'.repeat(64) }) : response(503, {})));
  await assert.rejects(requestLogout(false, async () => { throw new Error('offline'); }));
});
