# E2-09 — отдельный изолированный PostgreSQL-прогон

**План, не разрешение и не результат. Сейчас серверные действия запрещены.**
Олег публикует локальные коммиты в beta сам. Затем требуется отдельное разрешение
на этот изолированный этап; внедрение в основную beta этим разрешением не покрывается.

## Исходники и неизменяемые границы

Source commit: `SOURCE_SHA_PENDING_LOCAL_COMMIT`. Этот SHA должен присутствовать
в опубликованной beta; точный release checkout — именно он, даже если HEAD beta
позже содержит документ с закреплённым SHA. Git live remote проверяется заново.
Нельзя передавать исходники SCP/архивом или изменять серверный checkout.

До разрешения сервер не проверялся. Подтверждённый ранее main runtime:
`409c71f65db53873183c6ffd8d059561c05185d2`, mount
`/home/adm_user/marketplace-workspace/beta/app/releases/409c71f65db53873183c6ffd8d059561c05185d2/backend`.
Последняя проверенная публикация до E2-09: `aac9cbd32eb5e9c846ece90a0ad75c4aca74a57b`.
Расхождение runtime/source/image/preflight — стоп, без подгонки baseline.

Новый project/cluster: `marketplace-e209-20261007-01a115d9-r1`.

| Ресурс | Точное имя |
| --- | --- |
| Корень | /home/adm_user/marketplace-workspace/beta/rehearsals/e2-09-20261007-01a115d9-r1 |
| Контейнеры | marketplace-e209-20261007-01a115d9-r1-postgres, marketplace-e209-20261007-01a115d9-r1-controller, marketplace-e209-20261007-01a115d9-r1-web |
| Сеть | marketplace-e209-20261007-01a115d9-r1-private, internal=true, без портов на хост |
| Volume | marketplace-e209-20261007-01a115d9-r1-data |
| БД нового кластера | mw_beta, test_mw_beta; эти имена повторяются только внутри нового отдельного кластера |
| Роли нового кластера | mw_beta_bootstrap, mw_beta_migrator, mw_beta_web, с новыми секретами, без связей с прежними ролями |
| Restore-БД | mw_e209_01a115d9_r1_restore, owner mw_beta_migrator, web CONNECT=false |
| Dump | <корень>/backups/financial-after.dump, новый, mode0600 |
| События suite | <корень>/state/suite-events.jsonl, O_EXCL, только разрешённые статусы, без raw traceback/SQL/ответов |

Любой существующий новый root/name/label/volume/network/DB/dump/evidence — стоп.
Не переиспользовать частичный запуск. Сохраняются все E2-06/E2-07/E2-08 R1–R4,
основная beta, её оба PostgreSQL, все keys/checkpoint/restore и Finkos. Helper
сверяет metadata старых контейнеров до/после, не открывает их secret-файлы/БД.

Образы только уже имеющиеся, pull/build/install запрещены:

- security image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`;
- PostgreSQL image `sha256:248efd5e58cd743f2a0e0daec8ea4649e5580145ec2a12e2345bc710d4a77201`;
- requirements.lock SHA256 `35cba592050150a0e5b1f68adc36d3f1c0871ceec79efc6c7f8e4a925fb34e60`.

## Лимиты и секреты

Весь этап <=60 минут; suite <=2400 секунд, failfast, без повторного прогона.
Controller lifetime 3600 секунд; команды configure/scenario/verify <=180 секунд,
dump и restore по <=600 секунд. На первой ошибке остановиться. Если оставшегося
окна недостаточно, остановиться, не продлевать автоматически.

Postgres384MiB/0.25CPU, web384MiB/0.25CPU, controller256MiB/0.25CPU;
bootstrap256MiB кратковременно, не одновременно с suite/web. pids_limit96.
Предварительно MemAvailable>=2GiB, disk free>=2GiB. max_connections20
(включая резерв PG), фактически <=8 клиентских соединений, конкурентных проб2.
statement_timeout15s, lock_timeout5s, idle-in-transaction20s; сетевой HTTP timeout5s.
Не проводить нагрузочный benchmark. При превышении, OOM или деградации основной
beta — остановка только нового стенда с сохранением ресурсов.

prepare_financial_rehearsal создаёт только новые случайные synthetic secrets:
db_bootstrap_password и отдельный pg mount той же новой пары, db_migrator_password,
db_web_password, django_secret_key, mfa_encryption_key, isolation_signing_key.
Файлы0600, UID процесса/PG, корень0700; процессы читают их через /run/secrets,
не CLI/env значения. Никаких старых owner recovery verifier/K3/ключей основной beta.
Web получает только web password + Django/MFA/isolation ключи, никогда migrator/
bootstrap. SQL-пароль dump-процесс получает внутри нового postgres из нового mount,
не выводя значение. Не cat ключи в терминал, не inspect Env, не shell tracing,
не curl -v/headers/body/cookie dumps, не писать raw exception/SQL в отчёты.
Только example.invalid и locmem; внешние чтения/запись/доставка/расписания выключены.

## Последовательность после отдельного разрешения

1. Git preflight: fresh ls-remote origin refs/heads/beta; fetch beta в штатном
   repository; проверить полный SHA и merge-base --is-ancestor source live-beta.
   Создать новый detached worktree release/source только через Git, после проверки
   отсутствия release-каталога/коллизий. Чистый status, HEAD/source/image/lock совпали.
   Сохранить только несекретные значения проверки. Git fetch сам runtime не меняет.
2. Подготовить новые файлы/секреты и проверить Compose. Следующий блок — команды
   для будущего выполнения, сейчас они не выполнялись. Первый ненулевой exit — стоп.

```sh
set -eu
base=/home/adm_user/marketplace-workspace/beta
REV=SOURCE_SHA_PENDING_LOCAL_COMMIT
release="$base/app/releases/$REV"
export SECURITY_SOURCE="$release/backend"
export SECURITY_IMAGE=sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72
dc() { timeout 2500 docker compose --project-name marketplace-e209-20261007-01a115d9-r1 --env-file /dev/null -f "$release/beta/deploy/compose.financial-rehearsal.json" "$@"; }
timeout 180 python3 "$release/beta/deploy/prepare_financial_rehearsal.py" --apply --revision "$REV"
dc config --quiet </dev/null
dc up -d --wait postgres </dev/null
dc run --rm -T bootstrap </dev/null
dc up -d controller </dev/null
dc exec -T controller timeout 180 python -m tools.financial_rehearsal configure </dev/null
dc run --rm -T bootstrap python -m tools.financial_rehearsal test_database </dev/null
dc exec -T controller python -m tools.financial_test_runner </dev/null
dc exec -T controller timeout 180 python -m tools.financial_rehearsal scenario </dev/null
dc up -d web </dev/null
dc exec -T web timeout 180 python -m tools.verify_financial_web_runtime </dev/null
```

Если image не содержит timeout, использовать host timeout для конкретного docker
exec и по таймауту остановить новый controller; не устанавливать пакет и не оставлять
команду работать в фоне. Главный suite имеет собственный kill/deadline.

3. Suite без skipped/failures/errors. FinancialHTTPTests — новая матрица полей/
   формул/итогов, независимости/делегирования, подмен/CSRF, active sessions/revoke,
   overlap/regrant/неоживления ссылок, восстановления/архивов/MFA/support.
   FinancialConcurrencyTests — реальные отдельные PG-соединения, отзыв против
   чтения/изменения/download, после commit отзыва отказ. FinancialMigrationTests —
   переход с E2-08 сохраняет прежние данные/Grant/guards; финансовое populated
   downgrade запрещено. Старые прогоны не засчитывать.
4. Scenario отдельно от suite: fixture создаёт migrator; действительные логин/TOTP,
   затем session_user=current_user=mw_beta_web, не SET ROLE. SQL denies в обеих
   формах (без подписи/с genuine signed statement): прямые столбцы/sum/UPDATE,
   ALTER RLS, private helper, UPDATE finance binding, SET ROLE. Фиксированный
   read запрещён без обоих прав, с control/null/bad/resource/action контекстом,
   чужим кабинетом, repeatable-read. Проверяются exception/savepoint/full rollback,
   reuse, два соединения, оба Grant и неизменяемая ссылка; старый RLS probe выполнен
   на этом новом кластере. Подписываются только статические SQL теста внутри helper,
   клиентского signing endpoint или аргумента SQL не добавлено.
5. Network smoke — шесть статусов Gunicorn + SQL ACL/RLS; authenticated HTTP через
   Django Client с настоящим web LOGIN отдельно. Browser/TLS/load PASS не заявлять.

## Точный ожидаемый переход schema/ACL

Миграций +2: access_control.0003_financial_schema и data_isolation.0002_financial_operations.
Новая public.access_control_syntheticfinance: record_id PK/PROTECT, org/cabinet FK,
четыре numeric(14,2), четыре диапазонных CHECK; составной FK(org,cabinet,record)
и новый UNIQUE(org,cabinet,id) у SyntheticRecord. Новый nullable FK finance_grant_id
у ExportBinding, CHECK access_known_operation расширен только synthetic_finance
четырьмя действиями без platform; существующие Grant/данные не переписываются.

Семь новых trigger-функций/триггеров: finance_scope, finance_identity,
finance_nodelete, finance_binding_scope, finance_binding_immutable, finance_revoke,
finance_manager. Все SECURITY DEFINER/search_path pg_catalog,public/PUBLIC EXECUTE
отозван. Новая таблица ENABLE+FORCE RLS с одной operator policy владельцу migrator;
27 прежних RLS-таблиц/правил сохраняются, всего28. Новые mw_isolation функции:
private finance_allowed(jsonb), finance_read(uuid[],uuid),
finance_write(uuid,numeric,numeric,numeric,numeric); все DEFINER с фиксированным
search_path. Web имеет EXECUTE только последних двух, не finance_allowed.

Web получает только INSERT(finance_grant_id) к прежним столбцам ExportBinding,
без UPDATE этого поля, и EXECUTE двух функций. На SyntheticFinance никаких
табличных/столбцовых SELECT/DML/REFERENCES/TRIGGER прав; унаследованный default
SELECT снимается в транзакции создания таблицы. Никаких DDL/TEMP/role membership/
BYPASSRLS/superuser/GRANT OPTION. Табличные RLS не объявляются защитой столбцов:
финансовый барьер — ACL + две проверяющие функции + серверные потребители.
Первый finance-owner назначается только явным операторским synthetic bootstrap,
не миграцией/ролью/шаблоном. Не вводится право platform_admin на деньги.

Fresh configure снимает default SELECT только внутри нового пустого кластера,
затем устанавливает фиксированный прежний ACL и финансовую дельту. Не применять
этот fresh helper к основной/сохранённой БД. Legacy downgrade-тесты E2-06/E2-07,
снимающие guards заполненной схемы, не обходят запрет E2-08/E2-09.

## Backup/restore после успешных проверок

Остановить только новый web; проверить, что suite/scenario завершились и writers
нет. Не останавливать основную beta. Dump включает синтетические секреты, его не
читать/публиковать; сохранить0600, размер и SHA256 всего dump (не отдельных ключей).
Следующий блок создаёт только новый dump/новую restore-БД, исходную mw_beta не меняет.

```sh
dc stop web </dev/null
dc exec -T postgres sh -s <<'FINANCIAL_BACKUP'
set -eu
set +x
umask 077
export PGPASSWORD="$(cat /run/secrets/db_bootstrap_password)"
export PGHOST=127.0.0.1 PGUSER=mw_beta_bootstrap
test "$(psql -d mw_beta -Atqc "SELECT current_setting('cluster_name')" 2>/dev/null)" = marketplace-e209-20261007-01a115d9-r1
test "$(psql -d mw_beta -Atqc "SELECT count(*) FROM pg_stat_activity WHERE datname='mw_beta' AND pid<>pg_backend_pid() AND state<>'idle'" 2>/dev/null)" = 0
test "$(psql -d mw_beta -Atqc "SELECT count(*) FROM pg_database WHERE datname='mw_e209_01a115d9_r1_restore'" 2>/dev/null)" = 0
test ! -e /backups/financial-after.dump
set -C
timeout 600 pg_dump -Fc -d mw_beta > /backups/financial-after.dump 2>/dev/null
test -s /backups/financial-after.dump
chmod 600 /backups/financial-after.dump
sha256sum /backups/financial-after.dump
psql -d mw_beta -v ON_ERROR_STOP=1 -qc 'CREATE DATABASE mw_e209_01a115d9_r1_restore OWNER mw_beta_migrator' 2>/dev/null
psql -d mw_beta -v ON_ERROR_STOP=1 -qc 'REVOKE ALL ON DATABASE mw_e209_01a115d9_r1_restore FROM PUBLIC' 2>/dev/null
timeout 600 pg_restore --exit-on-error -d mw_e209_01a115d9_r1_restore /backups/financial-after.dump >/dev/null 2>&1
test "$(psql -d mw_beta -Atqc "SELECT has_database_privilege('mw_beta_web','mw_e209_01a115d9_r1_restore','CONNECT')" 2>/dev/null)" = f
unset PGPASSWORD
FINANCIAL_BACKUP
dc exec -T controller timeout 180 python -m tools.financial_restore_check </dev/null
dc up -d web </dev/null
dc exec -T web timeout 180 python -m tools.verify_financial_web_runtime </dev/null
timeout 180 python3 "$release/beta/deploy/prepare_financial_rehearsal.py" --verify --revision "$REV"
dc stop web controller postgres </dev/null
```

financial_restore_check сравнивает **до карантина** все public/mw_isolation строки
(включая новый signing key только в памяти), перечень таблиц/последовательностей,
last_value/is_called, столбцы/типы/defaults/ranges, table/column/default/function/
schema ACL, owners, policies/FORCE, функции/search_path, triggers/FK/CHECK/indexes,
django_migrations. DB ACL — намеренное отличие: restore не принимает web CONNECT;
не выдавать его ради теста. Различие остальных данных/metadata — FAIL, не игнорировать.
После сравнения проверяются запреты снять revoke у финансового Grant/permit или
переписать finance binding, затем quarantine_restored_access закрывает все сессии,
ссылки/факторы восстановления и помечает accounts recovery_required. Восстановленная
копия никогда не подключается к web. Historical backup не знает последующих отзывов:
открытие допустимо только после отдельной сверки актуальной матрицы, не regrant.

## Остановка, откат и результат

Любой отказ guard/SQL/HTTP, skipped, timeout, лишний ACL, неполное сравнение,
несовпадение старых metadata, нехватка ресурсов — STOP. Сохранить только безопасный
статус/имя теста, остановить только новые web/controller/postgres. Никаких DROP,
down -v/prune, перезаписи dump/секретов/БД, удаления evidence или повторного
использования имён. Остановка нового стенда — безопасный откат этого этапа.
Populated schema downgrade и fallback на pre-finance/pre-RLS runtime запрещены;
если обновлённый web не готов, он остаётся остановленным, ограничения не отключать.

В результат внести source/image/lock/PG version, start/stop с TZ, новый список
resources, количество/время tests/skips, реальный web LOGIN, HTTP/SQL/financial/RLS,
upgrade/rollback, dump SHA/restore/quarantine, сохранность старых контейнеров и
точные ошибки без секретов. Успех стенда не меняет runtime основной beta.

Отдельно не покрыты: отсутствующие cache, worker, storage/готовый рабочий экспорт,
интеграции/реальные отчёты/сотрудники/D3. E5-13 UI, E5-07 рабочий экспорт,
E6-03 реальные роли остаются своими задачами. E2-06/E2-08 формально не закрывать.
Следующий main rollout требует нового конкретного плана, backup/restore основной
beta, штатного compose.security-web.json + SECURITY_SOURCE/SECURITY_IMAGE и нового
разрешения. Base-only/accounts overlay и перенос прежних разрешений запрещены.
