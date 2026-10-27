// Только изолированный loopback-сервер проверок. В обычный dev/build не включается.
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const allIds = ['marketplace', 'reports', 'sources', 'airflow', 'bloggers', 'faq', 'rooms'];
const scenarios = ['catalog', 'empty', 'anonymous', 'expired', 'mfa', 'forbidden', 'unavailable', 'missing-api', 'error', 'invalid', 'slow', 'timeout', 'long-name'];
let scenario = 'unavailable';
const fixture = (items, name = 'Тестовая сессия') => ({ session: { status: 'authenticated', user: { id: 'fixture-only', displayName: name } }, applications: items });
const items = () => allIds.map(id => ({ id, access: id === 'bloggers' ? 'denied' : 'allowed', availability: id === 'airflow' ? 'unavailable' : 'available' }));

const server = await createServer({
  root,
  configFile: resolve(root, 'vite.config.ts'),
  server: { host: '127.0.0.1', port: 5192, strictPort: true, open: false },
  plugins: [{
    name: 'basework-isolated-fixtures',
    transformIndexHtml(html) {
      return html.replace('<body>', '<body><aside style="padding:12px 16px;border-bottom:2px solid currentColor;font:14px Segoe UI, sans-serif" aria-label="Режим проверки"><strong>Проверка на фикстурах.</strong> Пользователь, права и ответы API вымышлены. <a href="/__basework_tests">Сценарии проверки</a></aside>');
    },
    configureServer(vite) {
      vite.middlewares.use((request, result, next) => {
        const url = new URL(request.url, 'http://127.0.0.1:5192');
        if (url.pathname === '/__basework_tests') {
          result.setHeader('Content-Type', 'text/html; charset=utf-8');
          result.end(`<!doctype html><html lang="ru"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BaseWork — фикстуры</title><body style="font:16px Segoe UI,sans-serif;max-width:640px;margin:32px;padding:16px"><h1>Изолированная проверка BaseWork</h1><p>Это тестовый сервер на 127.0.0.1:5192. Здесь нет реальных пользователей, назначений и источников.</p><p>Текущий сценарий: ${scenario}</p><ul>${scenarios.map(value => `<li style="margin:16px 0"><a href="/__basework_fixture/${value}">${value}</a></li>`).join('')}</ul><a href="/basework/">Открыть оболочку</a></body></html>`);
          return;
        }
        if (url.pathname.startsWith('/__basework_fixture/')) {
          const selected = url.pathname.slice('/__basework_fixture/'.length);
          if (!scenarios.includes(selected)) { result.statusCode = 404; result.end(); return; }
          scenario = selected;
          result.statusCode = 303;
          result.setHeader('Location', '/basework/');
          result.end();
          return;
        }
        if (url.pathname !== '/api/v1/basework/bootstrap') { next(); return; }
        result.setHeader('Cache-Control', 'no-store');
        result.setHeader('Content-Type', 'application/json; charset=utf-8');
        const selected = scenario;
        const send = () => {
          if (result.destroyed) return;
          const failures = { anonymous: [401, {}], expired: [401, { status: 'session_expired' }], mfa: [403, { status: 'mfa_required' }], forbidden: [403, {}], unavailable: [503, {}], 'missing-api': [404, {}], error: [500, {}] };
          if (selected in failures) { result.statusCode = failures[selected][0]; result.end(JSON.stringify(failures[selected][1])); return; }
          if (selected === 'invalid') { result.end('{'); return; }
          const applications = selected === 'empty' ? [] : [...items(), { id: 'fbs', access: 'allowed', availability: 'available' }];
          result.end(JSON.stringify(fixture(applications, selected === 'long-name' ? 'Проверка длинного имени '.repeat(20) : undefined)));
        };
        if (selected === 'slow' || selected === 'timeout') {
          const timer = setTimeout(send, selected === 'slow' ? 4000 : 12000);
          result.on('close', () => clearTimeout(timer));
        } else send();
      });
    },
  }],
});
await server.listen();
console.log('Изолированные фикстуры: http://127.0.0.1:5192/__basework_tests');
