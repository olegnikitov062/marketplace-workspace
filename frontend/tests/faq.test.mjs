import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parseFaq, requestFaq } from '../src/basework/faqApi.ts';

const doc = { version: 7, updatedAt: '2026-10-29', total: 2, categories: ['Тема'],
  people: [{ name: 'Тестовый сотрудник', role: 'Склад' }],
  items: [{ id: 'q-1', cat: 'Тема', q: 'Вопрос', contacts: [['Тестовый сотрудник', 'Примечание']] },
    { id: 'q-2', cat: 'Тема', q: 'Без ответственного', contacts: [] }] };
const response = (status, value) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });

test('FAQ сохраняет вопросы, категории, контакты, версию и пустой результат', () => {
  assert.deepEqual(parseFaq(doc), { status: 'ready', data: doc });
  assert.deepEqual(parseFaq({ ...doc, items: [] }), { status: 'ready', data: { ...doc, items: [] } });
  assert.equal(parseFaq({ version: 0, updatedAt: '', total: 0, people: [], items: [], categories: [] }).status, 'ready');
});

test('FAQ отклоняет неверные типы, дубли и нарушенные связи', () => {
  for (const value of [null, { ...doc, version: '7' }, { ...doc, version: -1 },
    { ...doc, items: [doc.items[0], doc.items[0]] }, { ...doc, people: [] },
    { ...doc, categories: [] }, { ...doc, total: 1 }, { ...doc, people: [doc.people[0], doc.people[0]] }]) {
    assert.equal(parseFaq(value).status, 'error');
  }
});

test('FAQ использует только same-origin GET без ключа, с no-store и закодированным поиском', async () => {
  const signal = new AbortController().signal;
  const result = await requestFaq('отчёт & склад', 'Тема', signal, async (url, options) => {
    const parsed = new URL(url, 'https://example.invalid');
    assert.equal(parsed.pathname, '/api/v1/basework/faq/items');
    assert.equal(parsed.searchParams.get('q'), 'отчёт & склад');
    assert.equal(parsed.searchParams.get('category'), 'Тема');
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.redirect, 'error');
    assert.equal(options.signal, signal);
    assert.deepEqual(options.headers, { Accept: 'application/json' });
    assert.equal(options.body, undefined);
    return response(200, doc);
  });
  assert.deepEqual(result, { status: 'ready', data: doc });
});

test('Отказ доступа, сессии и источника никогда не содержит старые данные', async () => {
  for (const [status, body, expected] of [[401, {}, 'expired'], [403, {}, 'forbidden'],
    [403, { status: 'mfa_required' }, 'mfa_required'], [503, {}, 'unavailable'], [500, {}, 'error']]) {
    assert.deepEqual(await requestFaq('', '', new AbortController().signal, async () => response(status, body)), { status: expected });
  }
});

test('HTML и повреждённый JSON источника не считаются пустым FAQ', async () => {
  for (const value of [new Response('<html>'), new Response('{', { headers: { 'Content-Type': 'application/json' } })]) {
    assert.deepEqual(await requestFaq('', '', new AbortController().signal, async () => value), { status: 'error' });
  }
});

test('Отмена загрузки FAQ передаётся запросу', async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(requestFaq('', '', controller.signal, async (_, options) => {
    options.signal.throwIfAborted();
  }), { name: 'AbortError' });
});
