# E2-08 — результат R3, 07.10.2026

**FAIL.** После пяти тестов suite остановлен на
`data_isolation.tests.test_http.IsolationHTTPTests.test_default_deny_and_four_independent_actions`.
Продолжение/повтор серверных тестов не выполнялись. E2-08 и E2-06 остаются
«На проверке», основная beta не внедрялась.

Олег сообщил «залил и разрешаю»; live beta подтверждена как
`971600e8fca04b23d0de41f06bca950b09116883`. Source REV
`149414466473053a5eff7ad2edab4415a216c6b4` получен только Git fast-forward
и новым detached worktree. Начало `2026-10-07T07:49:32Z` (10:49:32 +03:00).

## Доказательства

- Publication/preflight/collision/resource/image/lock checks: PASS.
- Bootstrap/configure/test_database: exit0; новая mw_beta установлена,
  проверены 27 FORCE/ENABLE RLS таблиц, policies/ACL/guards; создана test_mw_beta.
- Suite: `Ran 5 tests in 42.991s`, один зарегистрированный FAIL указан выше;
  failfast, exit1. Точное число остальных PASS/skips не выводилось и не заявляется.
- Runner завершился штатно за53с, `complete=true`, `passed_without_skips=false`.
  События перечитаны из state/suite-events.jsonl; mode0600. Heartbeat работал,
  SSH не оборвался в этом прогоне; это не доказательство устранения всех сетевых причин.
- Результат содержит имя теста, но не строку assert/значения/текст исключения.
  Точная точка отказа не восстановлена; сырых SQL/токенов/traceback не сохранялось.
- Actual web LOGIN scenario, SQL probes, сетевой HTTP, static container,
  dump и restore не выполнялись.
- Main beta, три прежних rehearsal, R1 и R2: metadata до/после совпали.
  Основной source/runtime остаётся cf6f4ccd48106d9a44a64703bcfd79e49513ec3e.

R3 controller/postgres остановлены к `2026-10-07T07:52:04Z`, OOM=false.
Работающих контейнеров R3 нет; web не создавался. Никаких повторных
bootstrap/configure/suite, DROP/down -v/prune или отключения защиты не было.

## Сохранённые ресурсы

- Root `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-08-20261007-01a1105a-r3`.
- Project `marketplace-e208-20261007-01a1105a-r3`.
- Postgres ID `6a7a30b1ec172a431e0b9d30a72e82bd7da81f00ba882a9aa972824d72b0e0e4`;
  StartedAt `2026-10-07T07:49:36.122513263Z`, FinishedAt `2026-10-07T07:52:04.369039947Z`.
- Controller ID `af10ec013ed62122177783612fcca4f1e907c56590822acce3749a65d8947bbe`;
  StartedAt `2026-10-07T07:49:47.080347825Z`, FinishedAt `2026-10-07T07:52:03.810460019Z`.
- Internal network `marketplace-e208-20261007-01a1105a-r3-private`,
  ID `ed27dcd14ac3239de1bd0d770ba8c395a42eabbb7091dc608a19f81da6317799`.
- Volume `marketplace-e208-20261007-01a1105a-r3-data`.
- mw_beta/test_mw_beta, SQL-роли, schema/policies/ACL, новые synthetic secrets,
  state/manifest.json, state/suite-events.jsonl, baseline/preserved metadata.

Реальные ключи не читались, новые синтетические значения не выводились.
Production/Caddy/FBS/WB/Finkos, K3/Telegram и установки не затронуты.
Успешная установка RLS не выдаётся за проверенное поведение web-роли.

## Выявленный локально дефект подготовки и R4

В текущем коде configure записывает ключ только в mw_beta. Django создаёт
схему test_mw_beta миграциями, но миграция оставляет mw_isolation.key пустой;
test_database создаёт только саму БД. Suite R3 использовал обычный DiscoverRunner,
который provisioning ключа не выполняет. SQL export_cabinet всегда требует
успешный claims, даже для оператора. При пустом ключе возвращается NULL,
а положительное скачивание синтетической ссылки не может пройти.
Это доказанный по коду дефект подготовки; его связь с точным assert R3 пока
не подтверждена из-за отсутствия строки отказа в старом протоколе.

Новый IsolationDiscoverRunner вызывается опубликованным suite runner после
создания тестовой схемы. Он отказывает вне точных test_mw_beta/cluster/migrator,
при существующем ключе или не-PostgreSQL; записывает только новый synthetic
project key и проверяет claims через настоящий StatementSigner до HTTP fixture.
Он не ослабляет ACL/RLS и не применяется к основной mw_beta.
Протокол дополнен только статическими test file/line/function; сообщения,
SQL, source lines, locals и значения assert остаются скрытыми.

Локально 13 checks PASS за0.352с (runner redaction/summary gates, запрет key
access для main database, preparation/graph/context); это не PostgreSQL PASS.
Подготовлен отдельный R4 profile с сохранением stopped R1/R2/R3.
Следующий этап требует push Олега, live-проверки точного REV и отдельного
разрешения [плана R4](E2-08_SERVER_PLAN.md). Основная beta — самостоятельный
следующий этап после успешного изолированного прогона.
