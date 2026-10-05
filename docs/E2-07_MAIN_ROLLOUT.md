# E2-07 — план внедрения в основную beta

2026-10-05T13:40:28+03:00, Europe/Moscow. **Подготовлен локально; серверный этап этого плана не выполнялся. Требуется отдельное разрешение после ознакомления с этим конкретным объёмом.** Исходное разрешение E2-07 относилось к отдельному стенду и не разрешало обновлять основную beta. Текущее согласие на следующий шаг использовано для подготовки плана.

## Фиксированная ревизия и объём разрешения

- APP_REV: `cf6f4ccd48106d9a44a64703bcfd79e49513ec3e`, публикация beta повторно подтверждена напрямую через GitHub. Это коммит документов после проверенного `3369e3196753804655a7ae0cc9a845395545036e`; backend и deploy между ними не изменены. Реализация — `10c2af0`.
- Последний подтверждённый основной runtime: `14d9f48cee6eb2a9d7eca9f029770af51c45b6d9`, source `/home/adm_user/marketplace-workspace/beta/app/releases/14d9f48cee6eb2a9d7eca9f029770af51c45b6d9/backend`, read-only. Это baseline для будущего preflight, не результат новой SSH-проверки.
- Исходники только Git из опубликованной beta: новый чистый detached release `/home/adm_user/marketplace-workspace/beta/app/releases/cf6f4ccd48106d9a44a64703bcfd79e49513ec3e`. Если существует — сверить SHA/чистоту, не переписывать. Если beta продвинулась — подтвердить, что APP_REV остаётся её предком; код другой ревизии молча не использовать.
- Dependency image прежний: `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`. Lock SHA256: `35cba592050150a0e5b1f68adc36d3f1c0871ceec79efc6c7f8e4a925fb34e60`. Никаких build/pull/install.
- Разрешаемый будущий объём: SSH preflight; остановка только `marketplace-beta` service `web`; свежий dump основной `mw_beta`, отдельный restore; две миграции access_control и атомарный переход SQL-контракта E2-06 → E2-07; запуск только web на APP_REV со штатным security overlay; read-only/anonymous runtime-проверки; документирование.
- **Только пустая по аккаунтам/организациям beta.** Если появились пользователи, организации, кабинеты, членства, контакты, приглашения, факторы, коды, recovery/export permits, личные сессии или доверенные устройства — стоп до изменений. Не классифицировать найденные аккаунты как синтетические по имени, не выводить строки. Допустимы только существующие анонимные зашифрованные Django sessions и технические счётчики отказов; их сохранить.
- Не создавать основных пользователей/членств/Grant/platform_admin. Не вызывать `bootstrap-owner`, promote/demote или восстановление владельца. Наличие таких данных требует другого плана с точной матрицей и MFA; текущая миграция ничего автоматически не выдаёт.

Исполняемый diff 14d9f48 → APP_REV включает access_control, включение приложения/URL, Grant-потребителей accounts и account_security, разделение owner_required в восстановлении. Остальные изменения — tests/tools/docs и сохранённые rehearsal-инструменты. Старые owner/key tools в этом плане не запускать. Синтетический экспортный probe в основной beta остаётся выключенным, `E207_REHEARSAL` не задаётся.

## Новые имена и сохранность

| Объект | Точный путь/имя |
| --- | --- |
| Закрытый каталог checkpoint | `/home/adm_user/marketplace-workspace/beta/backups/database/e2-07-main-20261005-01a10b2d` |
| Dump | `<checkpoint>/before.dump` (в postgres: `/backups/e2-07-main-20261005-01a10b2d/before.dump`) |
| Безопасные metadata | `<checkpoint>/containers.before.json`, `database.before.json`, `acl.before.json`, `result.json` |
| Новая restore-БД в основном PostgreSQL | `mw_e207_main_restore_20261005_01a10b2d` |
| Владение restore | существующий `mw_beta_migrator`; новые SQL-роли не создаются |
| Source release | `/home/adm_user/marketplace-workspace/beta/app/releases/cf6f4ccd48106d9a44a64703bcfd79e49513ec3e` |

Любое совпадение checkpoint/dump/restore-БД — стоп, без перезаписи, удаления или выбора другого имени на ходу. Новая restore-БД не заменяет `mw_beta`, не подключается к web. Сразу после создания отозвать `PUBLIC CONNECT/TEMP`, не выдавать CONNECT `mw_beta_web`; проверить фактический отказ CONNECT web к restore. Все старые БД/роли/restore, оба owner rehearsal и остановленный E2-07 rehearsal сохраняются и не запускаются.

Каталог 0700, файлы 0600, создание no-overwrite/no-symlink; режим владельца должен позволять запись только штатному backup-процессу. Metadata содержат ID/image/source/StartedAt/UID/limits/mount paths/networks/ports, имена схемы/миграций/ACL и счётчики. Не сохранять `Config.Env`, pg_authid, значения сессий/строки аккаунтов, пароли, ключи, ссылки, cookies или заголовки запросов. Не делать Django dumpdata зашифрованных полей.

Ключи и пароли не просматривать вручную, не копировать, не передавать и не печатать. **Предлагаемый допуск к этому плану включает штатное чтение уже смонтированных SQL/Django/MFA секретов соответствующими сервисами, а также чтение только db_bootstrap_password внутри существующего postgres для pg_dump/pg_restore.** Это существенное уточнение исходного запрета открывать реальные файлы ключей/паролей: без такого допуска эти команды не запускать. Пример ниже читает пароль только в память закрытого процесса и не выводит его. Нового доступа web к bootstrap/migrator секретам нет. Дополнительный key verifier/envelope/passphrase/K3 не нужен. Если штатная аутентификация недоступна — остановиться, не искать другие файлы секретов. Восстановление проверяет ciphertext/схему в памяти без самостоятельного чтения или восстановления MFA-ключа.

## Нагрузка и окно недоступности

Существующие PostgreSQL и postgres-test не пересоздавать/не перезапускать, их лимиты не менять. Одноразовый migrator: 256 MiB, 0.25 CPU, не более двух SQL-соединений, connect/statement/lock timeout 5/5/2 s. Dump/restore последовательно, один job, без нагрузочного теста; для dump/restore отдельный предел команды 120 s и ожидания lock 2 s. Если существующая БД требует больших лимитов — стоп, не увеличивать автоматически. Свободно минимум 2 GiB памяти и 2 GiB диска; перед dump дополнительно проверить запас не менее трёх размеров БД.

Ожидаемое окно остановки web 10–20 минут при подтверждённой пустой beta. При превышении 20 минут прекратить переход на следующий этап и оставить web закрытым до выяснения, без возврата к небезопасному коду. CPU/memory web и сети/порты остаются штатными. Caddy, production, main, FBS, WB API, Finkos, worker и внешние сервисы не затрагиваются.

## Последовательность с проверяемыми стоп-условиями

### 1. Preflight без изменения основной БД/web

1. Сверить опубликованный APP_REV, чистый серверный repository/release, dependency image/lock и diff. Источник только Git, не SCP/архив или ручная правка серверного кода.
2. Снять безопасные metadata основной тройки контейнеров и всех сохранённых rehearsal, отдельно source/UID/read-only/limits/network/ports web. Проверить runtime14d9f48 и штатную конфигурацию `compose.security-web.json`. При расхождении — стоп до остановки web и миграций.
3. Под фактическим migrator LOGIN проверить `current_database= mw_beta`, `session_user=current_user=mw_beta_migrator`, среду beta/migrate, отсутствие E207_REHEARSAL. Сверить полный список миграций: pending должны быть ровно `access_control.0001_initial`, `access_control.0002_access_guards`; никаких дополнительных откатов/миграций.
4. Прочитать только счётчики перечисленных выше сущностей и проверить пустоту. Проверить старый E2-06 SQL-контракт через `tools.security_web_grants.verify_privileges/verify_guards(..., applied=True)`. Сохранить текущие table/column/schema/database/default ACL без credentials. Проверить, что неожиданных GRANT OPTION/других role memberships/посторонних схем нет.
5. Проверить свободные новые имена, место, `pg_dump`/`pg_restore` нужной версии, штатную SQL-аутентификацию и доступность пути backup. Сохранить checkpoint без перезаписи; read-back/hash сравнить без вывода содержимого.

### 2. Остановка web и свежий backup/restore

Остановить только web, убедиться, что его SQL-соединения завершены и нет иных writers. Повторить проверку пустоты/ACL/миграций под блокировкой операторского перехода. Если обнаружены writers — стоп, не убивать чужие процессы.

Сделать `pg_dump --format=custom` текущей `mw_beta` со схемой, ciphertext и ACL в новый `before.dump`; exit 0, режим 0600, ненулевой размер, SHA256. Пароль не передавать в аргументах, не печатать и не читать вне ограниченного процесса backup. Сохранённые старые dump не считать свежим backup.

Операторская команда внутри **существующего основного postgres**, только после подтверждения нового допуска к штатному secret mount, существующего checkpoint и отсутствия restore-БД:

```sh
# dc определяется как в разделе запуска; основной web уже остановлен.
dc exec -T postgres sh -eu -c '
  set +x
  umask 077
  set -C
  IFS= read -r PGPASSWORD < /run/secrets/db_bootstrap_password || test -n "$PGPASSWORD"
  export PGPASSWORD
  export PGUSER=mw_beta_bootstrap
  export PGOPTIONS="-c statement_timeout=120000 -c lock_timeout=2000"
  test -d /backups/e2-07-main-20261005-01a10b2d
  test ! -e /backups/e2-07-main-20261005-01a10b2d/before.dump
  timeout 120s pg_dump --dbname=mw_beta --format=custom --lock-wait-timeout=2s \
    > /backups/e2-07-main-20261005-01a10b2d/before.dump
  test -s /backups/e2-07-main-20261005-01a10b2d/before.dump
  psql -X -v ON_ERROR_STOP=1 -d mw_beta -c "CREATE DATABASE mw_e207_main_restore_20261005_01a10b2d OWNER mw_beta_migrator ALLOW_CONNECTIONS false"
  psql -X -v ON_ERROR_STOP=1 -d mw_beta -c "REVOKE ALL ON DATABASE mw_e207_main_restore_20261005_01a10b2d FROM PUBLIC, mw_beta_web"
  psql -X -v ON_ERROR_STOP=1 -d mw_beta -c "ALTER DATABASE mw_e207_main_restore_20261005_01a10b2d ALLOW_CONNECTIONS true"
  timeout 120s pg_restore --exit-on-error --dbname=mw_e207_main_restore_20261005_01a10b2d \
    /backups/e2-07-main-20261005-01a10b2d/before.dump
  sha256sum /backups/e2-07-main-20261005-01a10b2d/before.dump
' </dev/null
```

Наличие `timeout` проверяется заранее без установки; при отсутствии — стоп/пересмотр команды, не выполнение без ограничения. До CREATE проверить отсутствие нового имени отдельным read-only запросом. При любом отказе сохранённые/частичные файлы и БД не удалять и команду вслепую не повторять.

Через существующий bootstrap создать только новую restore-БД с указанным владельцем и запретом PUBLIC/web CONNECT. Восстановить новый dump с `pg_restore --exit-on-error`, без `--clean`/`--create` и без параллельных jobs. У роли web не должно появиться CONNECT к restore после восстановления ACL. Сравнить в памяти схему/миграции и все public-строки исходника и restore; вывести только PASS/count/hash. Новая БД остаётся закрытой и не получает HTTP-сервис. Данные доступа по preflight отсутствуют; анонимные зашифрованные сессии не расшифровывать и не использовать. Не переносить snapshot обратно в mw_beta.

Если dump/restore/сравнение не прошли — миграции не начинать, сохранить частичные результаты, web оставить остановленным. Ни old dump, ни прежний успешный restore E2-06/E2-07 не заменяют этот этап.

### 3. Закрытие TEMP, затем две миграции и переход DML одной транзакцией

Исходный `bootstrap_roles` отзывает PUBLIC CONNECT, но сам по себе не отзывает TEMP. Поэтому отдельно проверить фактический `has_database_privilege('mw_beta_web','mw_beta','TEMP')`; изолированный стенд уже закрывал TEMP собственным bootstrap, это не доказательство основной beta. После checkpoint/restore под **существующим bootstrap владельцем mw_beta** выполнить в отдельной транзакции `REVOKE TEMPORARY ON DATABASE mw_beta FROM PUBLIC, mw_beta_web`, затем подтвердить отсутствие TEMP у web. Новых роль/credential/широких полномочий не выдавать. Это отдельное сужение database ACL, не часть транзакции migrator ниже: migrator владеет схемой, но не обязательно базой. При последующей ошибке запрет TEMP сохраняется и явно отмечается в протоколе, автоматически не отменяется.

Существующий `access_web_grants.apply_fresh` не является командой обновления основной beta: он ожидает отсутствие DML/guard-объектов. Переход выполнить только через существующие проверенные функции в следующем порядке, на закрытой `mw_beta` и с повторной проверкой пустоты:

```python
# В штатном migrator с config.settings, после всех checkpoint-проверок.
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from account_security.operator import require_operator_process
from tools import security_web_grants as old
from tools import access_web_grants as new

with transaction.atomic():
    require_operator_process()
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(207, 2)')
        old.verify_privileges(cursor, old.MAIN_ROLE, applied=True)
        old.verify_guards(cursor, old.MAIN_ROLE, applied=True)
    executor = MigrationExecutor(connection)
    targets = [('access_control', '0002_access_guards')]
    planned = executor.migration_plan(targets)
    assert [(m.app_label, m.name, backwards) for m, backwards in planned] == [
        ('access_control', '0001_initial', False),
        ('access_control', '0002_access_guards', False),
    ]
    executor.migrate(targets)
    with connection.cursor() as cursor:
        old.revoke_fresh(cursor, old.MAIN_ROLE)
        cursor.execute('REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM mw_beta_web')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM mw_beta_web')
        for table in new.READ_TABLES:
            cursor.execute(f'GRANT SELECT ON public.{table} TO mw_beta_web')
        new.apply_fresh(cursor, new.MAIN_ROLE)
```

Это операторский фрагмент, не самостоятельный обход preflight. Он исполняется только из утверждённого Git-плана в рамках разрешённого перехода. Схемы/default ACL перед ним сверяются с checkpoint. Миграции E2-07 атомарны на PostgreSQL; новый контракт и восстановленные lock guards проверяются до commit. Ошибка/timeout — откат всей транзакции, web не открывать. Не применять изолированный `access_rehearsal configure`: тот отказывает на непустой схеме и предназначен для другого кластера.

Разрешения нового web: SELECT только `new.READ_TABLES`; старые account/security DML сохранены; добавлены ограниченные Grant/SupportWindow/ExportBinding INSERT, Grant/SupportWindow revoked_at UPDATE, SyntheticRecord value UPDATE и Membership role/state. DELETE только django_session. Нет DDL/TEMP, role inheritance, Grant DELETE/TRUNCATE, записи PlatformRoleAssignment или platform-subject Grant. Проверить точный контракт, CONNECT только к mw_beta, default SELECT больше не выдаётся будущим таблицам автоматически. При любом несоответствии не выдавать дополнительные права «для прохождения smoke».

После commit сверить ровно две новые миграции, пять новых пустых access-таблиц, сохранность всех прежних бизнес-строк/прав и ожидаемую разницу ACL. Владельцев/наблюдателей/пользователей кабинета в пустой beta нет, начальные Grant не требуются и не выдаются. Если пустота нарушена — web не запускать.

### 4. Запуск и проверка только основного web

```sh
base=/home/adm_user/marketplace-workspace/beta
APP_REV=cf6f4ccd48106d9a44a64703bcfd79e49513ec3e
release="$base/app/releases/$APP_REV"
export BACKEND_IMAGE=marketplace-workspace/backend:e2-03-0210f27a7ab1
export SECURITY_IMAGE=sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72
export SECURITY_SOURCE="$release/backend"
dc() { docker compose --project-name marketplace-beta --env-file /dev/null --project-directory "$base/deploy" -f "$base/deploy/compose.json" "$@"; }
dc -f "$release/beta/deploy/compose.security-web.json" config --quiet </dev/null
dc -f "$release/beta/deploy/compose.security-web.json" up -d --no-deps web </dev/null
```

До запуска проверить, что merged config сохраняет прежние secret mounts и process flags, UID, read-only source/rootfs, network/no host ports, лимиты и выключенные внешние действия. Не печатать полный `compose config`/Env. Base-only и accounts-overlay запуск запрещён. У миграционных `run` stdin явно из `/dev/null`, если команда не передаёт согласованный операторский фрагмент через stdin.

Под **реальным** SQL LOGIN `mw_beta_web` проверить E2-07 `verify_privileges/verify_guards`, а не SET ROLE из migrator. Сетевые проверки внутри web: live/ready 200; session 401; GET login 405; MFA login 200; анонимный `/api/v1/access/platform/status/` и организация/кабинет/ресурс с синтетическими UUID не дают доступ, изменяющий POST без CSRF отвергнут. Не сохранять body/cookies/headers и не создавать аккаунты. Убедиться в ACCESS_CONTROL_ENABLED и ACCOUNT_SECURITY_ENABLED, SECURITY_DOWNLOAD_PROBE=false, отсутствии E207_REHEARSAL. Проверить запрет web DDL/UPDATE scope/DELETE/TRUNCATE/SET ROLE отдельными откатываемыми SQL-пробами, без реальных строк.

`tools.verify_access_web_runtime` **не запускать в основной beta**: он намеренно привязан к cluster_name изолированного стенда. Не ослаблять его guard. Здесь используются тот же SQL-контракт и явно перечисленные штатные runtime-проверки после проверки metadata основного контейнера. Старый `verify_security_web_runtime` тоже не является verifier нового E2-07 SQL-контракта.

Сверить новые web ID/StartedAt/source/image и неизменность обоих PostgreSQL/всех старых rehearsal; сохранить результат без секретов. Допустима только ожидаемая анонимная Django session от GET MFA login. Новая проверка пользователей/MFA/Grant в основной beta не проводится без отдельно согласованного provisioning; 70 PostgreSQL-тестов, два static PASS и полный authenticated сценарий остаются доказательствами отдельного E2-07 стенда, не браузерным прогоном основной beta.

## Отказ и откат

При ошибке любого этапа остановить только основной web; не продолжать по цепочке. До commit миграций транзакция должна полностью откатиться, что проверяется списком миграций/схемой/старым ACL. После commit сохранить новую схему/права и оставить web остановленным. **Автоматически возвращать обычный E2-06 runtime нельзя:** он проверял часть операций по роли без Grant. Безопасный гарантированный fallback здесь — остановка web; непроверенный maintenance-вариант не запускать как замену.

Не откатывать `0001 → zero` на основной БД, не делать DROP/restore поверх mw_beta, не отзывать Grant ради «отката» и не удалять dump/новую restore-БД. Возврат схемы/данных или открытие старого приложения требует отдельного анализа состояния, плана и разрешения. Restore-БД остаётся закрытым доказательством свежего backup; это не автоматический disaster recovery. Очистка сохранённых ресурсов — отдельное разрешение.

## Приёмка и последующая фиксация

Успех плана: свежий main backup/restore и сравнение PASS; TEMP закрыт; две миграции и точные DML/SELECT ACL commit; основной web на APP_REV с MFA/Grant; runtime/SQL/CSRF anonymous проверки PASS; процессы PostgreSQL/старые стенды неизменны (основной кластер получает только явно перечисленные изменения БД). Любой незакрытый пункт сохраняет E2-07 «На проверке». Даже успешное внедрение не закрывает E2-06 рабочий экспорт, E2-08 RLS, E2-09 финансовую фильтрацию, D3/реальные аккаунты, UI/worker/интеграции, браузер/TLS или K3.

После выполнения сохранить фактические время, APP_REV, dump SHA256, restore result, before/after migrations/ACL metadata, web ID и проверочные результаты. С резервными копиями обновить SYSTEM_GRANT_CHECKS.json, SYSTEM_PLAN.md, SYSTEM_STARTUP.md, docs/RUNBOOK.md, этот документ и CHANGELOG.md; исторические доказательства E2-06 не переписывать. Локальный коммит Oleg, push только Олег.

На момент подготовки проверены только локальные исходники/документы и публикация GitHub. SSH, main backup/restore, миграции, изменение ACL, остановка/запуск сервисов по этому плану **не выполнялись**. План не является свидетельством успешного перехода существующего E2-06 ACL; этот путь проверяется транзакционно при будущем разрешённом исполнении, с отказом при любом отличии.
