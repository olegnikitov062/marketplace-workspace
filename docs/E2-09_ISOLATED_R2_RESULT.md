# E2-09 R2 — PostgreSQL и web проверены, restore verification остановлен

**Общий этап не пройден; E2-09 остаётся «На проверке».** Текущее разрешение
Олега «залил, разрешаю» покрывало только docs/E2-09_R2_SERVER_PLAN.md.
Основная beta не обновлялась. После первой ошибки R2 остановлен, не повторялся.

## Исходники и выполненные этапы

Source `b7e0d66c6ad632544a0db73d7e38d59e0d54a511`; live beta
`0e0bd7d786ba8cdb4fb22d5cfdfc45559931e0b5` подтверждена локально и сервером.
Сервер получил исходники исключительно Git fetch + новый detached worktree
`/home/adm_user/marketplace-workspace/beta/app/releases/b7e0d66c6ad632544a0db73d7e38d59e0d54a511`.
Checkout не изменялся, установки/pull images/push не выполнялись.

Security image: `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`.
PostgreSQL image: `sha256:248efd5e58cd743f2a0e0daec8ea4649e5580145ec2a12e2345bc710d4a77201`.
Lock SHA256: `35cba592050150a0e5b1f68adc36d3f1c0871ceec79efc6c7f8e4a925fb34e60`.
PG17.11 (Debian17.11-1.pgdg12+2).

Времена ниже UTC (Z); Москва = UTC+03:00. Начало локальной проверки
2026-10-07T15:35:36+03:00. Этап завершён в пределах60 минут.

| Этап 2026-10-07 | Время UTC | Результат |
| --- | --- | --- |
| Preflight | 12:35:43Z | clean Git, новые имена/root/release отсутствуют, disk free5901258752bytes, MemAvailable4757036KiB |
| Git source | 12:36:13Z | pinned checkout готов, clean |
| Compose config / postgres start | 12:37:00Z / 12:37:07Z | exit0, только новый private cluster |
| Bootstrap / controller | 12:37:11Z | exit0 |
| Fresh configure | 12:37:22Z | миграции + минимальный financial ACL contract PASS |
| test_mw_beta | 12:37:26Z | новая БД создана, exit0 |
| Runtime limits | 12:37:32Z | max_connections20, session statement5000ms/lock2000ms/idle20000ms, clients1 |
| Suite | 12:37:56Z–13:00:21Z | **134 теста PASS,0 skipped,1325.015s; runner1338s,exit0** |
| Real web LOGIN scenario | 13:01:26Z | exit0, limited_login_http PASS,10 базовых SQL denials, old_link_stays_revoked=true |
| Новый web / network verify | 13:01:50Z / 13:02:04Z | ACL/RLS и6 network checks PASS |
| Web stop перед dump | 13:02:43Z | exit0 |
| Dump + restore | 13:02:47Z | pg_dump/pg_restore exit0, новый restore web CONNECT=false |
| Restore compare/quarantine helper | 13:03:19Z | **exit1; этап и причина внутри helper неизвестны** |
| Stop web/controller, затем postgres | 13:03:55Z | exit0, без повторного запуска |
| Финальная metadata | 13:05:10Z | исходная основная beta и все прежние стенды неизменны; новый R2 изолирован и остановлен |

Suite содержит текущие financial HTTP, финансовую конкуренцию отдельных PG
соединений, populated E2-08→E2-09 migration retention/запрет downgrade и текущие
Grant/session/MFA/platform/isolation регрессии. Это новый PG R2, не прежние PASS.
Полный repository discovery не заявляется (известный legacy E2-06 scenario
из локального отчёта не входит в этот фиксированный suite).

Сценарий отдельно от suite использовал session_user=current_user=mw_beta_web,
реальный login/TOTP через Django Client с CSRF; SET ROLE не заменял LOGIN.
Прошли tools.isolation_sql_probe и tools.financial_sql_probe: прямые/подписанные
SQL denies, fixed read/write, контекст/область, оба Grant, rollback/reuse/два
соединения, необратимость ссылки. Gunicorn проверен шестью network status
запросами. Browser/TLS/load и authenticated network end-to-end не заявляются.

## Отказ restore и сохранённые ресурсы

Dump создан новым с mode0600,623353bytes; SHA256:
`eea747cc7161b475ca2ee4cb0aac33bffa5e6f55695fe20d4664579695ea600c`.
Содержимое dump/ключей не выводилось. Restore создан в новом кластере,
`mw_e209_01a115d9_r2_restore`, owner mw_beta_migrator, web CONNECT=false.
Exit0 pg_restore подтверждает импорт, **не эквивалентность/безопасность restore**.

financial_restore_check вернул1; wrapper и helper не раскрывают исключений и
не записывают этапов. Нельзя утверждать, что ошибка была именно в данных,
ACL, соединении или quarantine. Полное сравнение rows/schema/functions/ACL/
sequences/guards и закрытие восстановленных сессий/ссылок не подтверждены.
Web не подключался к restore. После ошибки не было SQL-диагностики, restart,
повторного helper или ослабления сравнений. Плановые повторные web checks
после restore не выполнялись. Только metadata и безопасные suite-events/stat
прочитаны после остановки; read-only sudo не менял права файлов.

Root: `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-09-20261007-01a115d9-r2`.
Project/cluster: `marketplace-e209-20261007-01a115d9-r2`.

| Контейнер | ID | FinishedAt UTC |
| --- | --- | --- |
| web | dd4de177771e851586112f05db63e8a0ec71fdafe7a21e50fa8d3f34264ceb2d | 13:02:43.230131304Z |
| controller | c606788247870fd4a0015b3f2853a1975d9aac45826823846d332b90f4b061f0 | 13:03:55.326140364Z |
| postgres | ab9c94d84a491edb2f902a2f8f9e5e6b3235f0ad9b97e805a73bbb78465bc6aa | 13:03:55.709516382Z |

Все exited,OOM=false. Network marketplace-e209-20261007-01a115d9-r2-private:
`5b1fc9e510613ee7d830991e19c81bd5ed47f09b05f8815e5a96bea25ca06bdf`,internal=true.
Volume marketplace-e209-20261007-01a115d9-r2-data сохранён. Сохранены БД mw_beta,
test_mw_beta, restore, роли,7 новых synthetic secrets, baseline.json,
preserved-rehearsal.json, state/manifest.json, state/suite-events.jsonl,
backups/financial-after.dump, operator-output и release. Не удалять/переиспользовать.

В12:59:30Z PG52.32MiB/384MiB,controller118.8MiB/256MiB,CPU0%/24.80%,pids8/4.
Лимиты контейнеров действовали; во время suite дополнительных Django/SQL
мониторов не было. Нет оснований заявлять непрерывное измерение числа SQL clients;
проверка clients1 была до suite, параллельные тестовые пробы ограничены2.
Основная beta metadata совпала с baseline, runtime остаётся409c71f65db53873183c6ffd8d059561c05185d2.
Старые БД/ключи не читались и не менялись. Metadata не заменяет main HTTP-тесты.

## Следующий ограниченный шаг

Локально подготовлены R3 (новые имена, сохранение R1/R2) и безопасные checkpoints
restore: только фиксированные event/stage/index, O_EXCL/0600/fsync. SQL, значения,
исключения и персональные данные не записываются. Финансовая реализация, миграции,
ACL/RLS и строгие сравнения неизменны. Это улучшение диагностики, **не доказанное
исправление неизвестной причины**.11 preparation-тестов PASS0.424s; первая попытка
на Windows sandbox дала PermissionError TemporaryDirectory, повтор вне sandbox
успешен. Это локальная проверка без PG/сети, не сервер R3.

Точный новый план — docs/E2-09_R3_SERVER_PLAN.md; нужны его source/pin в live beta
и отдельное разрешение Олега. R2-допуск не переносится. Новая ошибка — опять стоп,
без повторов/обхода. Main rollout требует собственного плана/backup-restore/
разрешения и compose.security-web.json + SECURITY_SOURCE/SECURITY_IMAGE.
E2-09 остаётся «На проверке» до restore и main; E2-06/E2-08 статусы не меняются.
Cache/worker/storage/готовый экспорт/интеграции отсутствуют; UI E5-13,
рабочий экспорт E5-07 и реальные сотрудники/D3 E6-03 вне этого этапа.
