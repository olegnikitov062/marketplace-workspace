# Запуск beta — E2-08 и история технической основы

Актуально после отдельно разрешённого E2-08 main rollout (07.10.2026): основной web/БД beta обновлены, read-only Git source409c71f65db53873183c6ffd8d059561c05185d2, 27 FORCE RLS tables, прежний MFA dependency image и отдельный isolation key. Текущие команды — в последнем разделе E2-08. Исторические обычные запуски ниже не выполнять: base-only/accounts overlay обходят MFA, E2-06 не проверяет Grant, E2-07 не включает новую изоляцию. Безопасный fallback — остановка web; downgrade/reverse/live restore запрещены.

30.09.2026, Europe/Moscow (UTC+3). D1 сохранено. После отдельного разрешения Олега установлены зависимости нового проекта и запущена изолированная beta. E2-04 и следующие задачи не начинались.

Исходники: `C:/Users/krolo/Documents/marketplace-workspace/backend/`, `frontend/`. Конфигурация запуска: `beta/deploy/compose.json`, `beta/deploy/beta.py`; версии образов: `beta/deploy/images.lock.json`. Полная инструкция: `C:/Users/krolo/Documents/marketplace-workspace/docs/RUNBOOK.md`. Протокол фактических проверок: [SYSTEM_STARTUP_CHECKS.json](SYSTEM_STARTUP_CHECKS.json).

Сборка `e2-03-0210f27a7ab1`: `C:/Users/krolo/Documents/marketplace-workspace/artifacts/e2-03-0210f27a7ab1.tar`, SHA-256 `d225e196afc168e7e92289c1909c6e703b9c656a977758005656ea74827f2f42`. Источники и lock-файлы входят в архив; секреты, данные, node_modules и venv исключены. Серверная копия: `/home/adm_user/marketplace-workspace/beta/app/` и `beta/deploy/`; манифест содержит 30 файлов.

Зависимости: Python 3.14.7, Django 5.2.17, DRF 3.18.1, psycopg 3.3.6, Gunicorn 26.2.0; React 19.3.0, TypeScript 7.0.2, Vite 8.3.1. Python requirements.lock фиксирует все пакеты и hashes, npm package-lock.json фиксирует frontend. Серверные базовые образы закреплены digest; PostgreSQL фактически 17.11.

## Фактическая beta

Compose project `marketplace-beta`: postgres, postgres-test, web. Главная БД `mw_beta`, роли `mw_beta_bootstrap`, `mw_beta_migrator`, `mw_beta_web`. Отдельный тестовый PostgreSQL: `mw_beta_test`, роли `mw_beta_test_bootstrap`, `mw_beta_test_runner`. Test runner имеет CREATEDB и CONNECT к postgres только собственного тестового кластера для создания/удаления Django test database.

Сети `marketplace-beta-private` и `marketplace-beta-test-private` internal; у web нет доступа к тестовой сети. `marketplace-beta-ingress` остаётся пустой. Опубликованных портов нет: проверенный API доступен внутри web на 127.0.0.1:8000. Ранее предложенный серверный 18100 не используется. Frontend собран, но не опубликован. Caddy, TLS и внешний маршрут не применялись.

Web: 384 MiB/0.25 CPU; PostgreSQL: 512 MiB/0.5 CPU; тестовый PostgreSQL: 384 MiB/0.25 CPU. PID 128, логи 10 MiB × 3, restart=no. Web без root, capabilities, с read-only filesystem и временным tmpfs. Рабочие данные, тестовые данные и копии находятся в отдельных beta-каталогах. Шесть секретов сгенерированы только на сервере; значения не экспортировались.

## Подтверждённые проверки

- Windows: два теста guard с отрицательными сценариями, pip check, TypeScript и Vite build.
- Linux beta: пять Django tests, создание и удаление тестовой БД, ready endpoint.
- Чистый временный PostgreSQL и отдельная internal сеть: provisioning, миграции, пять tests и teardown; временные ресурсы удалены по собственным ID.
- Шесть неверных конфигураций отклонены до подключения: production, чужой host/DB/admin role, реальные отправки, внешний source URL. Внешние адреса не опрашивались.
- Web-роль: DDL и CONNECT к системной БД запрещены, административных прав и членства в migrator нет. TCP-доступ из web к собственному тестовому PostgreSQL в другой сети отклонён.
- Миграция contenttypes назад/вперёд и восстановление dump в отдельную тестовую БД прошли с синтетической строкой. Копия: `/home/adm_user/marketplace-workspace/beta/backups/test/migrations-before.dump`, SHA-256 `6d0e539f5814a764130c08a889aa853ba368a9b7e6b7ab41d02649a6f8f176b8`.
- Все 30 серверных исходников совпали с манифестом, три frontend build-файла совпали с локальной сборкой.

При разработке исправлены Windows/POSIX-проверка пути secrets, новый control socket Gunicorn, доступ test runner для teardown, вызов Python-модуля и синтаксис migration checker. Итоговые проверки после исправлений прошли.

## Границы и откат

Проверена техническая основа, а не готовая рабочая система: нет пользователей, организаций, бизнес-моделей, worker, расписаний, внешних интеграций и реальных отправок. Production guard запрещает запуск. Полный Windows-запуск PostgreSQL/Docker не проверялся и не устанавливался; чистый запуск проверен на разрешённом сервере. Публичный HTTPS, пиковая нагрузка и аудит всего firewall не проверены. Новые источники данных и общий Caddy требуют отдельного конкретного разрешения.

Во время проверки FBS перезапускался параллельно; Олег подтвердил, что это его действие. Наши команды не перезапускали FBS. Остальные семь сравниваемых контейнеров, включая Caddy, сохранили metadata.

Копии изменяемых локальных файлов: `C:/Users/krolo/Documents/marketplace-workspace/.change-backups/2026-09-30/E2-03-20260930-153934/`. Перечень артефактов и hashes: `change-manifest.json` в этой папке. Перед откатом сравнить текущие hashes, сохранить поздние изменения; вернуть только собственные изменения документов. CHANGELOG сохранять и дописать отмену. Новый код/архивы удалять только при совпадении манифеста и отсутствии поздней работы; посторонние `.playwright-cli/` и `output/` сохранить.

Серверный откат отдельно разрешается: сначала сверить project labels, контейнеры, сети и mounted paths с протоколом; остановить только marketplace-beta. Данные, secrets и dump автоматически не удалять. Не применять общий prune, reset или рекурсивное удаление корня. Серверные source-копии находятся в `beta/.change-backups/`; позднюю работу сохранить. Старые сборочные образы и кеши не очищались.

Имена серверных secret-файлов (без значений): db_bootstrap_password, db_migrator_password, db_web_password, db_test_bootstrap_password, db_test_runner_password, django_secret_key.



## Историческая beta после E2-05 C2 — 2026-10-01T13:55:12+03:00

Серверный основной Git checkout: `/home/adm_user/marketplace-workspace/beta/app/repository`, beta b1a9450 на момент применения. Работающий backend зафиксирован отдельно: `/home/adm_user/marketplace-workspace/beta/app/releases/82b200465e15b447a43ed3d36d4522f11742bee1/backend` (read-only), detached HEAD 82b200465e15b447a43ed3d36d4522f11742bee1; последующие pull основного checkout не меняют этот mount. Image: `marketplace-workspace/backend:e2-03-0210f27a7ab1`, ID sha256:eade0170f4aaf5984fc22664d479f30bfc8dac085c9d31b78e70190aeb810e4b; requirements.lock совпал, новой сборки не было. Основные миграции accounts:2/auth:12/contenttypes:2/ownership:2/sessions:1 и точный DML/guard contract применены. Web ID b2d0be7a01c46d46d584b247394fca7e56021ef797d26840cbf75d355614faf8, StartedAt 2026-10-01T10:47:55.161037866Z, только private, опубликованных портов нет.

Архивные команды ниже воспроизводили E2-05; **после E2-06 их запуск запрещён**. Для текущего запуска и отката использовать только последний раздел E2-06:

```sh
cd /home/adm_user/marketplace-workspace/beta
export BACKEND_IMAGE=marketplace-workspace/backend:e2-03-0210f27a7ab1
release=/home/adm_user/marketplace-workspace/beta/app/releases/82b200465e15b447a43ed3d36d4522f11742bee1
export ACCOUNTS_SOURCE="$release/backend"
dc() { docker compose --project-name marketplace-beta --env-file /dev/null --project-directory /home/adm_user/marketplace-workspace/beta/deploy -f /home/adm_user/marketplace-workspace/beta/deploy/compose.json "$@"; }
dc -f "$release/beta/deploy/compose.accounts-web.json" config --quiet
dc -f "$release/beta/deploy/compose.accounts-web.json" up -d --no-deps web
dc exec -T web python -m tools.verify_account_web_runtime </dev/null
```

C2 подтвердил actual SQL role/ACL/guards, live/ready 200, session 401/login GET 405. Полный lifecycle под ограниченной ролью отдельно подтверждён C1. В основной БД пока нет организаций/аккаунтов/членств/контактов/приглашений/сессий. TEMPORARY=true у main web сохранено из исходной политики; public routes/TLS/реальных писем/источников нет. Оба PostgreSQL не пересоздавались, C1-роли отключены. Startup/ownership JSON старых этапов сохраняются как исторические snapshots; текущее доказательство — SYSTEM_ACCOUNT_CHECKS.json, секция c2.

Перед C2 сохранены новый `/home/adm_user/marketplace-workspace/beta/backups/database/e2-05-main-before-20261001T104501Z.dump` и соседний `.acl.json` (оба 0600), restore в mw_beta_test_e2_05_main_before сверён. Hashes/точный состав/ограничения — docs/E2-05_WEB_ROLE.md §8. Исторический E2-05 base-only откат после включения MFA запрещён; использовать только maintenance из актуального раздела E2-06 ниже. Добавочную схему/данные/worktree/dumps сохранять, zero/live restore не применять. Удалять release, который смонтирован web, нельзя.


## Историческая beta после E2-06 S2 — 2026-10-01T17:58:26+03:00

Снимок и команды этого раздела описывают S2. Текущий рабочий source и команды приведены в следующем разделе от 02.10.2026; source19a6d6a не возвращать в обычный web из-за браузерного CSRF-отказа.

Рабочий код: `/home/adm_user/marketplace-workspace/beta/app/releases/19a6d6a9bbdd06c683f68f438215dd99cba6204e/backend` (read-only), SHA `19a6d6a9bbdd06c683f68f438215dd99cba6204e`. Dependency image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`; опубликованный Git checkout f4f6059. Web `42ea5c212f1fc3062df51214ca97428e4613741adb8fac7897e494faaeb8e106`, StartedAt `2026-10-01T14:48:24.953976075Z`. PostgreSQL контейнеры прежние, только private сеть, host ports отсутствуют. Django migrations: account_security:2/accounts:2/auth:12/contenttypes:2/otp_static:3/otp_totp:3/ownership:2/sessions:1/two_factor:9 (squash учитывает заменённые записи).

Обычный запуск требует **compose.security-web.json + SECURITY_SOURCE + SECURITY_IMAGE**. Accounts overlay/ACCOUNTS_SOURCE и base-only запуск больше не являются допустимым запуском/откатом: они возвращают обход MFA. Следующие команды воспроизводят проверенную конфигурацию, но не разрешают будущий рестарт без задания. Не запускать общий up/prepare/start/bootstrap:

```sh
base=/home/adm_user/marketplace-workspace/beta
release="$base/app/releases/19a6d6a9bbdd06c683f68f438215dd99cba6204e"
export BACKEND_IMAGE=marketplace-workspace/backend:e2-03-0210f27a7ab1
export SECURITY_IMAGE=sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72
export SECURITY_SOURCE="$release/backend"
dc() { docker compose --project-name marketplace-beta --env-file /dev/null --project-directory "$base/deploy" -f "$base/deploy/compose.json" "$@"; }
dc -f "$release/beta/deploy/compose.security-web.json" config --quiet
dc -f "$release/beta/deploy/compose.security-web.json" up -d --no-deps web
dc -f "$release/beta/deploy/compose.security-web.json" exec -T web python -m tools.verify_security_web_runtime </dev/null
```

BACKEND_IMAGE нужен базовой интерполяции и maintenance; SECURITY_IMAGE определяет обычный MFA web. Ключ `/home/adm_user/marketplace-workspace/beta/config/secrets/mfa_encryption_key` монтируется read-only только web/migrate. Существующий server deploy/compose.json не редактировался; overlay берётся из опубликованного Git release. Production/Caddy/TLS/frontend/worker не менялись.

Безопасный откат при отказе: оставить схему/ключи/данные и закрыть вход проверенным maintenance либо остановить только web. При тех же base/release/env/dc:

```sh
dc -f "$release/beta/deploy/compose.security-maintenance.json" up -d --no-deps web
```

Maintenance на старом закреплённом dependency image с E2-06 source даёт 503 auth/business/ready, 200 live. Старый E2-05 web запускать нельзя; новый ACL revoke допустим только при отключённом потребителе, обычный старый revoke не применять. Zero, restore поверх живой БД, удаление mounted release/ключей/БД/dumps запрещены.

До применения сохранены dump `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-before-20261001T144009Z.dump`, `.acl.json` и `.snapshot.json` (0600), все 18 таблиц сверены с `mw_beta_test_e2_06_main_before`; имя занято. Копия ключа `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-main-key-envelope/envelope.json`, пароль отдельно `/home/adm_user/marketplace-workspace/beta/config/e2-06-main-key-recovery/backup-passphrase`, проверенный восстановленный файл `/home/adm_user/marketplace-workspace/beta/config/e2-06-main-key-restored/key`; все 0600/UID10001, каталоги 0700. Это серверные закрытые файлы, не подтверждённая независимая копия у Олега. Не включать значения/ключевые fingerprints в отчёты. Telegram/реальные owner proof/передача не выполнялись.

Runtime/анонимный Chromium smoke успешны, аккаунты/организации/членства/факторы/permits/codes отсутствуют; 2 анонимные зашифрованные wizard sessions от проверок. Все oneoff/browser/tunnel закрыты. Полные критерии E2-06 остаются «На проверке»; точный протокол и границы — SYSTEM_SECURITY_CHECKS.json/s2 и docs/E2-06_SESSIONS_MFA.md.


## Текущая beta E2-06 после исправления Referrer-Policy — 2026-10-02T13:41:10+03:00

Рабочий source: `/home/adm_user/marketplace-workspace/beta/app/releases/14d9f48cee6eb2a9d7eca9f029770af51c45b6d9/backend`, read-only. Серверный repository: `91b079a30569b6fc38997b47fe18d6af723b9321` (опубликованная чистая beta), он не определяет runtime без SECURITY_SOURCE. Web ID `53dd81f2850521138b9596d1aa5f910f7889785d8836329efbbfb0f7b57654c5`, StartedAt `2026-10-02T10:28:21.386899228Z`. Dependency image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72` и lock прежние; UID10001:10001, read-only, 384MiB/0.25CPU, marketplace-beta-private, без host ports. Прежний отдельный TOTP key смонтирован read-only, 0600/UID10001.

Оба PostgreSQL сохранили ID/image/StartedAt/mounts/networks/ports. Схема и SQL-права не менялись: account_security:2/accounts:2/auth:12/contenttypes:2/otp_static:3/otp_totp:3/ownership:2/sessions:1/two_factor:9. Ограниченный web LOGIN/guards, live/ready и анонимный Chromium Origin прошли; native POST отменён до отправки. Основных аккаунтов/организаций/членств нет; 6 анонимных зашифрованных Django sessions после GET-проверок. Точный протокол: SYSTEM_SECURITY_CHECKS.json/main_web_referrer_rollout; локальный SYSTEM_STARTUP_CHECKS.json обновлён, остаётся вне Git.

Следующие команды воспроизводят текущую конфигурацию, но не разрешают будущий рестарт без задания. Нужны security overlay и все три переменные; BACKEND_IMAGE служит базовой интерполяции и maintenance. Base-only и accounts overlay запрещены:

```sh
base=/home/adm_user/marketplace-workspace/beta
release="$base/app/releases/14d9f48cee6eb2a9d7eca9f029770af51c45b6d9"
export BACKEND_IMAGE=marketplace-workspace/backend:e2-03-0210f27a7ab1
export SECURITY_IMAGE=sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72
export SECURITY_SOURCE="$release/backend"
dc() { docker compose --project-name marketplace-beta --env-file /dev/null --project-directory "$base/deploy" -f "$base/deploy/compose.json" "$@"; }
dc -f "$release/beta/deploy/compose.security-web.json" config --quiet </dev/null
dc -f "$release/beta/deploy/compose.security-web.json" up -d --no-deps web </dev/null
dc -f "$release/beta/deploy/compose.security-web.json" exec -T web python -m tools.verify_security_web_runtime </dev/null
```

Безопасный fallback при отдельном задании — MFA maintenance либо остановка только web, с теми же base/release/env/dc:

```sh
dc -f "$release/beta/deploy/compose.security-maintenance.json" up -d --no-deps web </dev/null
# либо остановить только web, если maintenance не подтверждён:
dc -f "$release/beta/deploy/compose.security-web.json" stop web </dev/null
```

Checkpoint `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-referrer-before-20261002T102702Z.metadata.json` сохранён 0600 и сверен read-back. Прежние S2 backup/key файлы сохранены; нового dump/restore в этом code-only этапе нет. Схему/данные/ключи/releases/старые тестовые БД не удалять, live restore/reverse migrations не выполнять. Maintenance фактически проверялся в S1/S2, здесь не включался. E2-06 остаётся «На проверке»; независимой копии у Олега и реального owner proof пока нет. Сохранённый owner rehearsal остановлен; его baseline основного web относится к периоду до этого обновления.

## Текущая beta E2-07 — 2026-10-05T14:19:06+03:00

После отдельного разрешения опубликованного [плана основной beta](docs/E2-07_MAIN_ROLLOUT.md) основной runtime — `cf6f4ccd48106d9a44a64703bcfd79e49513ec3e`, серверный repository18e4a18. Web ID `969d11c5bfd1c13e58a9bbcef07659d3bdf0662ec0cc5e53af06b71476c17807`, StartedAt `2026-10-05T11:16:12.521846356Z`. Прежние image/lock/MFA secret mounts, UID10001:10001, 384MiB/0.25CPU, read-only и internal/no ports сохранены. Процессы двух PostgreSQL и 11 контейнеров старых rehearsal не изменялись. Не выводить секреты и не менять источник runtime через base-only команды.

Актуальная последовательность запуска **только при отдельном разрешении на новый запуск/перезапуск**:

```sh
base=/home/adm_user/marketplace-workspace/beta
release="$base/app/releases/cf6f4ccd48106d9a44a64703bcfd79e49513ec3e"
export BACKEND_IMAGE=marketplace-workspace/backend:e2-03-0210f27a7ab1
export SECURITY_IMAGE=sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72
export SECURITY_SOURCE="$release/backend"
dc() { docker compose --project-name marketplace-beta --env-file /dev/null --project-directory "$base/deploy" -f "$base/deploy/compose.json" "$@"; }
dc -f "$release/beta/deploy/compose.security-web.json" config --quiet </dev/null
dc -f "$release/beta/deploy/compose.security-web.json" up -d --no-deps web </dev/null
```

Новые `access_control.0001/0002` и точный поколоночный ACL применены одной транзакцией. TEMP закрыт отдельно bootstrap; default SELECT будущим таблицам отозван, web CONNECT к restore закрыт. Проверены реальный web LOGIN/10 SQL-отказов и 10 сетевых anonymous health/auth/default-deny/CSRF запросов. ACCESS_CONTROL_ENABLED и ACCOUNT_SECURITY_ENABLED=true, SECURITY_DOWNLOAD_PROBE=false, E207_REHEARSAL не задавать. Изолированный `tools.verify_access_web_runtime` привязан к другому cluster_name и для основной beta непригоден; старый E2-06 verifier тоже не проверяет новый ACL. Фактические проверки основной beta перечислены в плане/протоколе, guards не ослаблять ради переиспользования helper.

Свежий checkpoint `/home/adm_user/marketplace-workspace/beta/backups/database/e2-07-main-20261005-01a10b2d`: новые private metadata/ACL и before.dump0600, SHA256 `267dcecac7a3434870f09915deee1b6950a43df672c1eedad6dea2086e006529`. Restore `mw_e207_main_restore_20261005_01a10b2d` закрыт от web и сохранён; 30 таблиц/11 sequences сравнили, две текстовые формы CHECK доказаны эквивалентными. Не повторять CREATE/provision/restore по занятым именам. Основные аккаунты/организации/Grant пусты; anonymous sessions6→7 от GET входа.

Безопасный отказ после новой схемы — остановка только web указанным dc/security overlay. Обычный E2-06 runtime14d9f48 возвращать нельзя: он обходил Grant. Не делать reverse/zero/live restore, не удалять checkpoint/restore/старые стенды без отдельного плана/разрешения. Подробности — SYSTEM_GRANT_CHECKS.json/main_rollout_result; SYSTEM_STARTUP_CHECKS.json/latest_runtime_e207. Исторические разделы выше сохранены как доказательства прежних этапов, а не актуальные команды отката. E2-06 остаётся «На проверке», рабочий экспорт/K3 этим этапом не закрываются.


## Текущая beta E2-08 — 2026-10-07T12:47:04+03:00

Основной runtime409c71f65db53873183c6ffd8d059561c05185d2, серверный repository1d3076a0825cf90259d16333e3cc24668fa33e81. Web ID4c30e68d246015c013aa071f4a8dc6af7088abdb9c9329ef22509db9cebadaa2, StartedAt2026-10-07T09:43:33.3431035Z. Прежний dependency image, UID10001:10001,384MiB/0.25CPU, read-only source, internal network/no host ports; добавлен только отдельный isolation key mount к прежним web secrets. 27 ENABLE/FORCE RLS tables, реальный mw_beta_web, Grant/MFA/изоляция включены, synthetic export probe выключен. Rehearsal/offline flags запрещены.

Команды воспроизведения только после отдельного разрешения нового запуска/перезапуска; текущий web уже работает:

```sh
set -eu
base=/home/adm_user/marketplace-workspace/beta
release="$base/app/releases/409c71f65db53873183c6ffd8d059561c05185d2"
export BACKEND_IMAGE=marketplace-workspace/backend:e2-03-0210f27a7ab1
export SECURITY_IMAGE=sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72
export SECURITY_SOURCE="$release/backend"
dc() { timeout 120 docker compose --project-name marketplace-beta --env-file /dev/null --project-directory "$base/deploy" -f "$base/deploy/compose.json" -f "$release/beta/deploy/compose.security-web.json" "$@"; }
dc config --quiet </dev/null
dc up -d --no-deps web </dev/null
```

Fallback при разрешённом задании — `dc stop web` с теми же base/release/env/security overlay. Не запускать cf6f4cc или другой pre-RLS код, не выполнять base-only/accounts overlay, reverse/live restore, не отключать RLS/MFA/Grant. Изолированный verifier имеет guard другого cluster и для main не вызывается.

Свежие checkpoint beta/backups/database/e2-08-main-20261007-01a1105a и restore mw_e208_main_restore_20261007_01a1105a сохранены закрытыми; все имена заняты. Dump204905bytes0600 SHA256b24f013c801fbd148f9e8f398fde460e7bee5751c6d57d4a517d4e1b641190f9. Текущий итог result.final.json, промежуточный result.json сохранён исторически. Полное сравнение данных/ACL, реальный SQL/9 отказов и9 network HTTP/2 CSRF PASS; оба PostgreSQL и все прежние стенды неизменны. Окно stop→проверенный ready8мин01с. Протокол — [E2-08_MAIN_RESULT.md](docs/E2-08_MAIN_RESULT.md), SYSTEM_STARTUP_CHECKS.json/latest_runtime_e208. E2-08 «На проверке» по отсутствующим cache/job/file-export критериям; E2-06 без изменения.
