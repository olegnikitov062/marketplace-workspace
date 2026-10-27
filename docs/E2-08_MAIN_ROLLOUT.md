# E2-08 — отдельный план основной beta

07.10.2026, Europe/Moscow. **Исполнен по отдельному текущему разрешению Олега;
основной rollout PASS.** [Фактический протокол](E2-08_MAIN_RESULT.md) содержит
результаты, промежуточные ошибки проверок и их проверенное разрешение.
Ниже сохранён план этапа: его CREATE/provision нельзя повторять, имена заняты.
Live beta при допуске `1d3076a0825cf90259d16333e3cc24668fa33e81`, runtime APP_REV ниже.

## Точные исходники и границы

- APP_REV: **409c71f65db53873183c6ffd8d059561c05185d2** — проверенный код R4.
- Live опубликованная beta на проверке R4: `774b00224a13a96549f96bff9c5eed0286c04de3`.
  Этот новый документ Олег публикует отдельно; перед допуском повторить live
  ls-remote и проверить APP_REV ancestor фактической beta. Backend/deploy
  нельзя молча заменить более поздней ревизией.
- Исходники только Git beta; существующий detached release APP_REV проверить
  по SHA/чистоте/read-only mount. Не переписывать его, не SCP и не архив.
- Исходный main runtime: `cf6f4ccd48106d9a44a64703bcfd79e49513ec3e`, RO source
  `/home/adm_user/marketplace-workspace/beta/app/releases/cf6f4ccd48106d9a44a64703bcfd79e49513ec3e/backend`.
- Existing backend image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`;
  lock SHA256 `35cba592050150a0e5b1f68adc36d3f1c0871ceec79efc6c7f8e4a925fb34e60`.
  Никаких install/build/pull или изменения PostgreSQL image.
- Только пустая по личным аккаунтам/организациям beta, как при E2-07 rollout.
  Preflight проверяет только counts: users, orgs, memberships, cabinets, contacts,
  invitations, factors, security states, recovery/export permits, devices,
  personal sessions, Grant/platform/support/records должны отсутствовать.
  Если появились — стоп до остановки web, без вывода строк и без предположения
  «они синтетические». Нужен другой план сохранения/проверки населённой beta.
  Анонимные Django sessions и технические счётчики сохраняются.
- Не создавать пользователей/Grant/platform_admin, не bootstrap-owner, не recovery,
  не включать синтетический probe и не задавать E208_REHEARSAL в main.

Разрешаемый отдельный объём: SSH/Git/preflight, новые checkpoint/restore/key,
остановка только main web, backup/restore, одна RLS-миграция и минимальный
SQL-контракт, запуск только web через штатный security overlay, read-only и
анонимные SQL/HTTP/CSRF-проверки, документирование. Production/main Git branch,
Caddy/FBS/WB/Finkos/worker/внешние подключения не входят.

## Новые имена и секреты

| Ресурс | Точное значение |
| --- | --- |
| Checkpoint | `/home/adm_user/marketplace-workspace/beta/backups/database/e2-08-main-20261007-01a1105a` |
| Dump | `<checkpoint>/before.dump`, внутри postgres `/backups/e2-08-main-20261007-01a1105a/before.dump` |
| Metadata | `<checkpoint>/containers.before.json`, `database.before.json`, `acl.before.json`, `result.json` |
| Закрытая restore-БД | `mw_e208_main_restore_20261007_01a1105a`, owner `mw_beta_migrator` |
| Новая main schema | `mw_isolation`, owner `mw_beta_migrator` |
| Новый main key file | `/home/adm_user/marketplace-workspace/beta/config/secrets/isolation_signing_key` |
| Runtime source | `/home/adm_user/marketplace-workspace/beta/app/releases/409c71f65db53873183c6ffd8d059561c05185d2/backend` |

Любая коллизия checkpoint/dump/restore/schema/key — стоп, без перезаписи/reuse
и выбора другого имени на ходу. Symlink/canonical path проверки обязательны.
Каталоги0700, новые файлы0600/O_EXCL; metadata без Config.Env, pg_authid,
личных строк, session payloads, ключей и их отпечатков. Backup содержит
чувствительные данные и остаётся закрытым. Все R1–R4 и прежние rehearsal
сохраняются stopped; PostgreSQL main/postgres-test не пересоздаются.

**Новый допуск должен включать штатное потребление уже смонтированных DB/Django/MFA
секретов соответствующими процессами и db_bootstrap_password только процессом
внутри основного postgres для dump/restore/schema provisioning.** Агент не читает
и не выводит содержимое реальных файлов. Не искать запасные ключи/пароли,
не делать K3/Telegram/envelope/passphrase/передачу ключа.

Допуск также охватывает генерацию одного нового 32-byte isolation key закрытым
процессом из existing image непосредственно в новый main key file (0600,
UID10001, O_EXCL/no-symlink), без печати/аргументов/копирования из R4.
Web получает только этот ключ плюс прежние собственные DB/Django/MFA mounts;
bootstrap/migrator credentials в web запрещены. Ключ provisioning читается
только штатным migrator-процессом в память; не хэшировать его в отчёте.

## Лимиты

Минимум2GiB свободных RAM/диска и запас диска не менее трёх размеров main DB.
Одноразовый migrator256MiB/0.25CPU, максимум2SQL connections;
connect/statement/lock timeouts5/5/2с. Dump/restore по одному job,
каждый timeout120с, lock wait2с; лимиты не повышать автоматически.
Полное окно main web stop — до20минут, весь этап до45минут.
Timeout/OOM/drift/неожиданные данные/права/ошибка — стоп следующих шагов,
web оставить закрытым; не возвращать pre-RLS приложение.
SSH keepalive15с/3, без трассировки shell и подробных SQL/HTTP logs.

## 1. Preflight до остановки web

1. Проверить live beta/APP_REV, существующий чистый release/image/lock и ровно
   ожидаемый diff cf6f4cc→APP_REV. Снять безопасные metadata трёх основных
   контейнеров и всех сохранённых rehearsal; проверить source/image/UID/read-only,
   сети/порты/лимиты/штатный compose.security-web.json. Любой drift — стоп.
2. Через фактический migrator LOGIN проверить `current_database=mw_beta`,
   `session_user=current_user=mw_beta_migrator`, beta/migrate и отсутствие
   rehearsal flags. Pending migration должна быть ровно
   `data_isolation.0001_statement_and_row_policies`, forward, без других миграций.
3. Проверить пустоту доменных данных выше и старый E2-07 контракт через
   `tools.access_web_grants.verify_privileges/verify_guards(...,True)`.
   Сохранить table/column/schema/database/default ACL, owner, role flags/memberships,
   function privilege/definer/search_path metadata, без credentials.
4. Проверить отсутствие RLS/schema/key, свободные новые имена, место/ресурсы,
   доступность штатных mounts и backup path. Существующие секреты не открывать.
   Создать checkpoint/key только после всех допускающих проверок, без перезаписи.
5. Проверить merged compose только `config --quiet` и выборочные metadata:
   прежние mounts/flags/UID/read-only/network/limits сохранены, добавлен только
   isolation key для web/migrate. Полный config/ENV не печатать.

## 2. Свежий backup/restore основной beta

Остановить только main web. Дождаться исчезновения его SQL connections;
если есть иной writer — стоп, чужие процессы не убивать. Повторить domain
counts/миграции/ACL; зафиксировать transaction-consistent снимок для сравнения.

Внутри существующего main postgres штатный bootstrap-процесс создаёт новый
custom pg_dump mw_beta в before.dump,0600,120с; проверить exit0/size/SHA256.
Создать новую restore-БД owner migrator, немедленно REVOKE PUBLIC CONNECT/TEMP;
web CONNECT=false до/после `pg_restore --exit-on-error`,120с.
Никаких временных CONNECT web, замены исходной mw_beta или запуска web на restore.

Сравнить в памяти все public-строки включая ciphertext, список миграций, функции,
constraints/triggers/indexes, table/column/schema/default ACL и owners;
database ACL сравнить с единственным ожидаемым отличием закрытой restore.
Не сохранять строки/отпечатки session/key данных в metadata. Сохранить только
counts и булевы результаты. Любое отличие — стоп до main migration.
R4 restore helper не вызывать здесь: он привязан к rehearsal и новой RLS-схеме.
Его предел table/column ACL comparison не переносить в эту проверку.

## 3. Минимальный переход SQL

Bootstrap, после повторной проверки main identity, создаёт только пустую
`mw_isolation AUTHORIZATION mw_beta_migrator`, REVOKE ALL FROM PUBLIC.
Никаких новых SQL-ролей, CREATEDB/CREATE DB для migrator, BYPASSRLS/DDL/TEMP
для web. Этот schema шаг отдельный: при отказе оставить пустую schema и web
закрытыми, не скрывать частичный результат удалением.

В штатном migrate из APP_REV с security overlay выполнить операторский фрагмент
из опубликованного Git-плана (не rehearsal configure). Секрет читается только
закрытым migrator-процессом, аргументы/значение не выводятся:

```python
from pathlib import Path
from psycopg import Cursor
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from account_security.operator import require_operator_process
from tools import access_web_grants as old, isolation_web_contract as new

with transaction.atomic():
    require_operator_process()
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(208, 1)')
        cursor.execute('SELECT current_database(),session_user,current_user')
        assert cursor.fetchone() == ('mw_beta', 'mw_beta_migrator', 'mw_beta_migrator')
        old.verify_privileges(cursor, old.MAIN_ROLE, True)
        old.verify_guards(cursor, old.MAIN_ROLE, True)
    executor = MigrationExecutor(connection)
    targets = [('data_isolation', '0001_statement_and_row_policies')]
    assert [(m.app_label, m.name, reverse) for m, reverse in executor.migration_plan(targets)] == [
        ('data_isolation', '0001_statement_and_row_policies', False),
    ]
    executor.migrate(targets)
    with Cursor(connection.connection) as cursor:
        new.apply(cursor, Path('/run/secrets/isolation_signing_key').read_bytes())
```

В исполненном этапе key INSERT использовал server-bound Cursor: до записи
проверены log_statement=none, log_parameter_max_length_on_error=0,
log_min_duration_statement/log_min_duration_sample=-1. Значение ключа не
включается в текст SQL; runtime ClientCursor signer не изменён.
До фрагмента обязательны повторные counts/preflight/backup/restore; он не
разрешает обход этих условий. `apply_fresh` E2-07 и rehearsal configure запрещены.
Новые права web — только USAGE mw_isolation и EXECUTE allowed/claims/export_cabinet;
key/HMAC/private record predicate недоступны. Существующий DML/column ACL не расширять.
27 таблиц ENABLE/FORCE, 11 фиксированных trigger functions SECURITY DEFINER с
закреплённым search_path; lock-only/web-subject остаются INVOKER.

До открытия web проверить одну новую migration record, полный SQL-контракт,
сохранность всех прежних строк/ACL и только ожидаемый diff policies/functions/schema.
Ошибки миграции/ACL откатывают единую транзакцию; schema/key остаются закрытыми.
После commit reverse на основной БД не выполнять даже при пустой domain.

## 4. Штатный запуск и приёмка

```sh
set -eu
base=/home/adm_user/marketplace-workspace/beta
APP_REV=409c71f65db53873183c6ffd8d059561c05185d2
release="$base/app/releases/$APP_REV"
export BACKEND_IMAGE=marketplace-workspace/backend:e2-03-0210f27a7ab1
export SECURITY_IMAGE=sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72
export SECURITY_SOURCE="$release/backend"
dc() { timeout 120 docker compose --project-name marketplace-beta --env-file /dev/null --project-directory "$base/deploy" -f "$base/deploy/compose.json" -f "$release/beta/deploy/compose.security-web.json" "$@"; }
dc config --quiet </dev/null
dc up -d --no-deps web </dev/null
```

Base-only/accounts overlay запрещены. Не трогать postgres/postgres-test/Caddy.
Реальный SQL LOGIN mw_beta_web, не SET ROLE: проверить isolation_web_contract.verify,
роль/отсутствие key/private function/DDL/TEMP/role access, unsigned/поддельный GUC
и изменяющие SQL только в откатываемых транзакциях. Пустая main DB сама по себе
не доказывает разграничение строк: соответствующее доказательство — текущий R4,
не выдавать эти пустые SELECT за новый положительный multi-tenant сценарий.

Внутренние сетевые проверки: live/ready200, session401, GET login405,
MFA login200, anonymous platform/status403, чужие synthetic UUID не раскрывают
данные, изменяющий POST без CSRF отвергнут. Bodies/cookies/tokens не сохранять.
ISOLATION_ENABLED/ACCESS_CONTROL_ENABLED/ACCOUNT_SECURITY_ENABLED=true;
SECURITY_DOWNLOAD_PROBE=false, никаких E208_REHEARSAL/ISOLATION_OFFLINE.
Rehearsal runtime verifier в main не вызывать и его guard не ослаблять.

Сверить новые web ID/StartedAt/source/image и неизменность обоих PostgreSQL/всех
rehearsal metadata. Допустимая новая анонимная Django session от GET MFA login
должна быть отдельно учтена; личные accounts/Grant не создавать.

## Отказ, откат и результат

При любом отказе остановить только main web; сохранить БД/key/checkpoint/restore.
До commit проверить rollback migration/ACL; после commit оставить RLS включённой.
**Гарантированный безопасный fallback — остановленный web.** Не запускать cf6f4cc
или иной pre-RLS код, не выключать политики, не reverse/drop/revoke ради smoke,
не restore поверх mw_beta, не удалять dump/schema/key или прежние ресурсы.
Восстановление/очистка требуют нового отдельного плана/разрешения.

Успех: свежий main backup/restore и полный ACL/data comparison; атомарный RLS
переход с сохранением данных/прав; main web на APP_REV с реальной ограниченной
SQL-ролью и успешными SQL/HTTP/CSRF checks; unchanged соседние процессы.
Если хоть один критерий открыт — E2-08 «На проверке» с точным перечнем.
E2-06/рабочий экспорт, E2-09, D3/E6-03, browser/TLS, absent cache/worker/storage,
реальные сотрудники и K3 этим планом не закрываются.

После выполнения обновить с backups: SYSTEM_ISOLATION_CHECKS.json,
SYSTEM_PLAN.md, SYSTEM_STARTUP.md, docs/RUNBOOK.md, этот протокол, CHANGELOG.md.
Локальные коммиты Oleg; push только Олег. Main-действия, штатное потребление
существующих secrets и новая key generation отдельно разрешены и выполнены
07.10.2026; повторное выполнение этим документом не разрешается.

Дополнение по фактическому сравнению: четыре константных массива в трёх
CHECK после pg_restore имеют иную форму varchar[]→text[] cast. Их значения,
типы и полные определения после только этих точных замен совпали; неизвестные
различия по-прежнему запрещены. PUBLIC EXECUTE удалён только у 11 функций из
TRUSTED_TRIGGERS, как прямо задано install; остальные function ACL сохранены.
Промежуточный result.json не перезаписывался, итог — result.final.json.
