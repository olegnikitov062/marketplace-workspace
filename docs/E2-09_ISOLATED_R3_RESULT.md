# E2-09 R3 — остановка на конкурентном восстановлении владельца

**R3 не пройден. E2-09 остаётся «На проверке».** По текущему разрешению Олега
«залил разрешил» выполнен только изолированный docs/E2-09_R3_SERVER_PLAN.md.
Основная beta не обновлялась. R3 остановлен на первой ошибке, без повторов.

## Проверенный source и этапы

Live beta: `bb2729482aa963efffe6c44f26bfcdadf0e0e4aa`.
Source: `88347474f2e8ac6064e893127280dbb3371480d6`, новый detached Git worktree
`/home/adm_user/marketplace-workspace/beta/app/releases/88347474f2e8ac6064e893127280dbb3371480d6`.
Git fetch/source clean, публикация проверена локально и сервером; исходники
на сервере не редактировались, не передавались архивом/SCP. Установок/push нет.

Security image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`;
PostgreSQL image `sha256:248efd5e58cd743f2a0e0daec8ea4649e5580145ec2a12e2345bc710d4a77201`.
Это тот же immutable PG17.11 образ, версия которого подтверждалась в R2;
отдельный SELECT version() в R3 не выполнялся.
Lock SHA256 `35cba592050150a0e5b1f68adc36d3f1c0871ceec79efc6c7f8e4a925fb34e60`.

Все времена ниже 2026-10-07 UTC (Москва UTC+03:00).

| Этап | Время | Результат |
| --- | --- | --- |
| Preflight | 13:22:57Z | новые имена/root/source свободны, disk5815615488bytes, MemAvailable4906868KiB |
| Source checkout | 13:22:58Z | Git-only, clean |
| Prepare / compose config | 13:23:31Z | exit0 |
| PostgreSQL / bootstrap / controller | 13:23:38Z / 13:23:44Z / 13:23:45Z | exit0 |
| Fresh configure | 13:23:55Z | миграции + финансовый ACL contract PASS |
| Новая test_mw_beta | 13:23:59Z | exit0 |
| Лимиты до suite | 13:24:05Z | max_connections20, statement5000ms, lock2000ms, idle20000ms, clients1 |
| Suite | 13:24:28Z–13:46:37Z | **ERROR,130 учтённых тестов,1309.324s; runner1323s,exit1** |
| Controller stopped | 13:47:14.984947901Z | до PostgreSQL, без OOM |
| PostgreSQL stopped | 13:47:15.467843468Z | без OOM |
| Финальная metadata | 13:48:09Z | main и все прежние стенды неизменны |
| Safe evidence readback | 13:48:12Z | совпадает с итогом runner; dump/restore-events отсутствуют |

Нет полного PASS:130 учтённых тестов не выдаются за130 успешных. Suite failfast
зарегистрировал ERROR в
`account_security.tests.test_transactions.SecurityConcurrencyTests.test_same_operator_permit_has_one_successful_consumer`.
Безопасные frame locations: test_transactions.py112(test),85(race),81(execute),111(action).
Сохранены только имя/класс ERROR/места теста, count/unittest_failed/suite_finished;
тип DB-исключения, SQLSTATE и сообщение не сохранялись. Причина серверного
ERROR поэтому **не доказана**. Общий этап завершён за <60 минут.

## Что не выполнено

До separate real web LOGIN scenario, нового web/network, dump/restore и
restore verification R3 не дошёл. Прежняя restore-ошибка R2 остаётся
нелокализованной; R3 restore-events.jsonl не создан. Предыдущие134 PG PASS
и real web LOGIN R2 сохраняются исторически, не подменяют failed R3.
Все оставшиеся тесты после failfast, в том числе финансовые migration tests
в конце набора, не объявляются выполненными в R3. Свежие миграции configure
не заменяют populated upgrade/retention.

## Остановка и сохранность

Root: `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-09-20261007-01a115d9-r3`.
Project/cluster: `marketplace-e209-20261007-01a115d9-r3`.

| Ресурс | Состояние/ID |
| --- | --- |
| postgres | stopped, cde80c2498af3119e59aece26663c5903f82b15b4fa20baffef3fabeea237c43 |
| controller | stopped, 25a9e60b65455ea810c27fd2d60cffaabdcda7d85811860be7a0d33c1a8b6f20 |
| web | не создан |
| private network | internal=true, 671cc53d6787000c0425f47fe30df8e129088f09f0a088eeef01b980e6d3d1db |
| volume | marketplace-e209-20261007-01a115d9-r3-data, сохранён |
| БД | mw_beta/test_mw_beta нового кластера, сохранены; restore не создавалась |

Сохранены роли/7 новых synthetic secret-файлов, state/manifest.json,
state/suite-events.jsonl, baseline.json, preserved-rehearsal.json, каталоги
backups/operator-output и Git release. Не удалять/переиспользовать. R1/R2 и
все E2-06/E2-07/E2-08 стенды, dump/restore/keys/checkpoint сохранены.
Main runtime/source остаётся409c71f65db53873183c6ffd8d059561c05185d2.
Старые БД/секреты не читались. Safe evidence прочитан read-only sudo из-за
UID10001/0600 без chmod; никаких raw logs/дампов/cookies/ключей в отчётах.

Контроль metadata прошёл13:25:46Z,13:31:06Z,13:36:01Z,13:40:27Z,13:46:12Z и
после остановки. Последний рабочий снимок: PG51.82MiB/384MiB,controller118.8MiB/256MiB,
pids8/4,OOMfalse. CPU ограничен cgroup0.25; docker stats25.13% — интервальное
измерение, не изменение quota. Во время suite дополнительных SQL/Django
мониторов не было; непрерывное измерение clients не заявляется.

## Локально подтверждённый дефект и минимальная подготовка R4

Код consume_operator_recovery выполнял user.check_password внутри transaction.atomic
после select_for_update пользователя. Это подтверждено исходниками и новым
локальным regression-тестом: до исправления FAIL (`in_atomic_block=True`).
Дорогое PBKDF2 под блокировкой может конфликтовать с2s lock_timeout и0.25CPU,
но связь с конкретным R3 ERROR — гипотеза, не установленный SQLSTATE.

Минимальный сопутствующий фикс необходим для проверки сохранения восстановления
в E2-09: proof пароля вынесен до lock по существующему recover_with_code,
после lock заново проверяются available/credential hash/owner, state/version,
expiry/used permit. Выдача прав/областей, MFA, Grant/RLS, таймауты, CPU, hashers,
сессии и одноразовость не расширяются. Блокировка или смена пароля между proof
и lock дают отказ без сессии. Операторское назначение/сроки не менялись.

Новые3 теста + RecoveryLockScopeTests + security HTTP:38 PASS,69.087s,0 skips,
SQLite. Financial/Grant/isolation регрессия:82 PASS,120.594s,0 skips,SQLite;
результаты отдельно зафиксированы в SYSTEM_FINANCIAL_CHECKS.json. Новая диагностика runner передаёт только
фиксированную категорию по allowlist SQLSTATE/ASSERTION/OTHER; raw exceptions
не выводятся.13 preparation/redaction-тестов PASS0.446s без БД/сети.
Эти проверки не подтверждают PG concurrency нового кода и не исправляют
неизвестный restore-дефект R2. E2-06 не закрывается.

Подготовлен новый изолированный R4 с сохранением R1/R2/R3:
docs/E2-09_R4_SERVER_PLAN.md. Нужны source/pin в опубликованной beta и отдельный
допуск. Старые таймауты/CPU, полный набор включая исходный конкурентный тест,
строгий restore и stop-on-first-error сохранены. Основная beta требует ещё
одного отдельного плана/разрешения после успешной изоляции.
E2-09/E2-06/E2-08 «На проверке». Cache/worker/storage/готовый экспорт/интеграции
отсутствуют, UI E5-13, рабочий экспорт E5-07, сотрудники/D3 E6-03 отдельно.
