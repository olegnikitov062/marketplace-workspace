# E2-06 — сессии, MFA и восстановление владельца

02.10.2026, Europe/Moscow. Статус: **На проверке**. S1: 63 PostgreSQL-теста без пропусков на 19a6d6a; S2: основная beta мигрирована, основной web обновлён до 14d9f48. Новый отдельный полный R2 на опубликованном 2c2f8f7 прошёл: Chromium 10 PASS, exit 0, pageerrors=0, настоящая operator CLI и итоговый SQL read-only PASS. R2 остановлен и сохранён, основная beta и первый стенд неизменны. Исторические ограничения первого aggregate прогона ниже сохранены; актуальный протокол — SYSTEM_SECURITY_CHECKS.json/browser_r2_run. K1/K2 PASS: новый envelope получен в закрытый локальный файл и расшифрован в памяти паролем из файла по отдельному разрешению Олега. K3 (ручное хранение/обратная проверка Telegram) и рабочий экспорт ещё не закрыты.

## Принятые решения

Олег согласовал обязательный MFA для владельца хотя бы одной активной организации, добровольное подключение для остальных; после подключения проверка обязательна до корректного отключения. Повышение до владельца проверяется по живому членству. Публичной регистрации, общих логинов и staff/superuser нет.

| Действие | Правило |
| --- | --- |
| Подключение | Пароль, ограниченная сессия подключения, правильный новый TOTP; до этого устройство не подтверждено |
| Замена | Недавние пароль + старый TOTP либо пароль + одноразовый восстановительный код; старый фактор действует до подтверждения нового |
| Отключение | Владельцу запрещено; остальным после недавних пароля + TOTP |
| Сроки | Сессия не более 24 часов, простой не более часа; MFA/подключение 5 минут; повторное подтверждение 5 минут |
| Доверенное устройство | 30 дней; при новом входе пароль обязателен, TOTP можно пропустить; для чувствительных действий нужен свежий пароль + TOTP |
| Выход | Текущая сессия; отдельные действия — выбранная собственная сессия или все |
| Смена/reset пароля, блокировка, замена/восстановление MFA, выход везде | Все сессии, доверенные устройства и синтетические ссылки отзываются |
| Парольное восстановление | MFA сохраняется; блокировка не снимается |
| Потеря TOTP | Пароль + одноразовый восстановительный код дают только повторное подключение, без доступа к приложению |
| Потеря всех факторов | Только явный запрос Олега и операторская команда с отдельным аварийным секретом вне Git/БД; затем пароль + одноразовое разрешение на подключение |
| Копия ключа TOTP | Восстанавливает только Олег. Уточнение 02.10.2026: оба отдельных файла (encrypted envelope и пароль) будут храниться им в Telegram; риск общего доступа объяснён и принят. Парольный файл создан вне Git, новый envelope/передача ещё не выполнены |

У добровольного пользователя без подключённого MFA повторное подтверждение требует только пароль; включение MFA не обходится этим правилом.

Технические параметры: TOTP 6 цифр/30 секунд, окно ±1 шаг, без автоматического drift; replay и задержку после ошибок ведёт django-otp. 10 случайных восстановительных кодов по 192 бита, PBKDF2-хеши Django, одноразовое использование под блокировкой строки пользователя. Лимиты попыток используют общий механизм E2-05 (БД, измерения peer/principal, новый cookie их не сбрасывает). Это параметры реализации, не расширение бизнес-ролей.

## Реализация и границы

Применены согласованные django-two-factor-auth 1.18.1, django-otp 1.7.3, cryptography 50.0.2 и шесть согласованных транзитивных пакетов; точные версии/hashes — requirements.lock. Старые pins сохранены. Wheels проверены по SHA-256 release metadata, LICENSE прочитаны, установка без дополнительных пакетов; pip check успешен. Linux dependency image собран в S0, проверен с lock и используется в S2. Телефонные/SMS/WebAuthn методы не включены.

`account_security` использует мастер/формы django-two-factor-auth и алгоритм, replay/throttling django-otp. Адаптер Authenticator меняет хранение, не алгоритм TOTP. Штатные plaintext otp_totp/otp_static таблицы не используются и не получают DML web. Собственный реестр нужен для отзыва, ограниченной стадии входа, шифрования и одноразовых хешированных кодов. Изменений site-packages нет.

Fernet шифрует ключи Authenticator и весь payload Django sessions, включая временные данные мастера. Ключ не выводится из Django SECRET_KEY: runtime требует отдельный read-only `/run/secrets/mfa_encryption_key`. Отсутствующий/некорректный ключ останавливает startup; ошибочный ключ не даёт прочитать старые сессии/факторы. Старые E2-05 cookie не создают новую полноценную сессию. Django dumpdata для зашифрованного поля запрещён: резервирование через pg_dump сохраняет ciphertext. Ротация ключей и внешнее хранилище секретов не реализованы.

SessionGate на каждом запросе проверяет актуального пользователя, version, password hash, сроки, отзыв устройства и обязательность MFA; текущие права организации читаются сервисами E2-04/05. После получения user row lock изменение аккаунтов повторно проверяет HTTP-сессию. До подтверждения обязательного MFA допустимы только setup/QR/CSRF/выход. Старый `/auth/login` не обходит мастер. Доверие устройства — случайный HttpOnly/Secure cookie и отзываемый серверный хеш; пароль не заменяется этим cookie.

Узкие серверные страницы: `/auth/mfa/login/`, `/auth/mfa/setup/`, `/auth/security/`, повторное подтверждение, смена пароля и восстановление. Изменения — POST с CSRF. Секреты показываются только самому пользователю в защищённом ответе, восстановительные коды — один раз; auth-ответы no-store; с опубликованного 14d9f48 Referrer-Policy:same-origin (проверено на отдельном стенде и применено к основной beta 02.10.2026). Журнал содержит категории и внутренний user ID без введённых значений/IP/User-Agent/токенов. Gunicorn access log выключен. Не снимать QR/коды/ответы через скриншоты или подробные HTTP-логи.

| Критерий | Реальный минимальный механизм | Что остаётся |
| --- | --- | --- |
| Немедленная смена прав | Живое Membership + повторная проверка E2-05 owner-действия; демоция запрещает настоящее приглашение в той же сессии | Полная матрица RBAC/Grant — E2-07 |
| Изоляция | Проверка чужой организации в настоящем приглашении и выдаче/чтении синтетического скачивания | RLS и полная предметная изоляция — E2-08 |
| Отзыв старой ссылки | ExportPermit привязан к пользователю, организации и конкретной сессии; HTTP действительно отдаёт фиксированный синтетический CSV и затем отказывает. DB trigger безвозвратно отзывает permit при смене роли/state/archive; возврат роли ссылку не оживляет | Рабочие экспорты/файлы/разрешения E5-07 и RBAC отсутствуют; полный критерий E2-06 остаётся на проверке |
| Потеря фактора владельцем | Одноразовый код или отдельное операторское разрешение дают только ограниченную сессию, без изменения Membership/организаций/блокировки | Синтетическая operator CLI проверена на PostgreSQL; реальная выдача аварийного секрета Олегу и независимое хранение ключа требуют отдельного решения |

Синтетический download закрыт по умолчанию (`SECURITY_DOWNLOAD_PROBE=False`), включается только внутри тестов; публичного HTTP выпуска ссылок нет. Это действующий механизм отзыва и HTTP-проверка, не бизнес-экспорт. E2-07/E2-08/E5-07 не объявляются реализованными.

## SQL и миграции

Добавлены account_security 0001_initial/0002_revocation_guards и необходимые миграции приложений библиотеки. 0002 устанавливает SECURITY INVOKER guards: неизменяемая идентичность записей, монотонная version/last_t, невозможность снять использованность/отзыв; триггеры смены password/is_active/archive и Membership/Organization. Прямой SQL не оживляет отозванное состояние. PostgreSQL-ветвь проверена в S1 на 17.11 и применена в основной beta в S2; SQLite не считается её доказательством.

Точный список таблиц/колонок — `backend/tools/security_web_grants.py` (SECURITY_INSERT/SECURITY_UPDATE/SECURITY_READ). Web получает INSERT только в реестр/факторы/коды/синтетические permits/журнал и UPDATE только изменяемых полей. Нет INSERT RecoveryPermit, UPDATE ключа/пользователя/уровня сессии, UPDATE/DELETE журнала, новых DELETE, DDL, членства ролей, BYPASSRLS, прав оператора/мигратора. Существующий E2-05 SELECT/default SELECT сохраняется; это не изоляция данных от скомпрометированного web и не RLS.

`manage_security_web_grants plan` без подключения показывает точный delta; apply проверяет прежний E2-05 контракт и миграции, атомарно добавляет только delta, проверяет итог. Revoke допускается после выключения потребителя и удаляет только delta, сохраняя прежние ACL. Grant/revoke/reapply и 17 SQL-отказов прошли под настоящим ограниченным LOGIN в S1 на 3db1c0c; в S2 проверен точный основной контракт после применения delta.

## Оператор и ключи

Команды `prepare_owner_recovery`/`issue_owner_recovery` разрешены только beta/migrate, с проверкой current_database/session_user/current_user = mw_beta/mw_beta_migrator/mw_beta_migrator. Web не получает verifier и migrator credentials. Подготовка создаёт два НОВЫХ файла: аварийный секрет Олегу и привязанный к UUID владельца PBKDF2 verifier; не печатает их. Файлы на volume `/run/recovery-output`, 0600, без перезаписи. Подготовка секрета отдельно авторизуется и не выполняется при обычной миграции.

Восстановление требует verifier read-only `/run/secrets/owner_recovery_verifier` и ввод секрета через getpass; неверный секрет/не-владелец/заблокированный аккаунт не получают разрешение. Успех отзывает сессии/доверие/ссылки, записывает 5-минутный одноразовый permit и сохраняет его только в новый закрытый файл. Олег вводит permit и свой пароль на странице operator-recovery, заново подключает TOTP, затем входит заново. Ни Codex, ни наличие SSH сами по себе не подтверждают личность. Автоматической команды «войти владельцем» нет. Доставка секрета/permit не автоматизирована и не разрешена этим документом.

Копия ключа шифруется `python -m tools.mfa_key_backup wrap --input <private-key-file> --output <NEW-private-envelope>`, восстановление — `restore` с новым выходным файлом. Scrypt с фиксированной стоимостью + Fernet; пароль через getpass, не в аргументах/ENV. Обёртка отказана на Windows до отдельной проверки приватного ACL назначения; криптографический roundtrip проверяется в памяти. Telegram здесь не подключён; по уточнению 02.10.2026 Олег переносит оба отдельных файла самостоятельно после проверки новой копии. Это заменяет прежнее решение о хранении пароля вне Telegram и не обеспечивает отдельного канала при компрометации его аккаунта. Потеря и ключа, и копии не устраняется аварийным секретом: это разные секреты.

Исторический dump не знает об отзыве после снимка. Восстановленная БД не включается непосредственно в web: `quarantine_restored_access()` отзывает все сессии/доверие/ссылки/коды/факторы и требует явной сверки текущих полномочий. Членства не меняются и блокировка не снимается. Возврат доступа владельцу — только согласованным операторским путём; массовое восстановление остальных пользователей не автоматизировано в E2-06. Restore rehearsal выполняет эту проверку в rollback-транзакции, сохраняя исходный синтетический снимок.

## Серверный план — не выполнять без нового разрешения

Все команды ниже — план, не свидетельство выполнения. Никаких SSH на текущем этапе. Сначала Олег проверяет и сам публикует локальные commits в beta. В разрешении S0/S1 фиксируются полный опубликованный REV и разрешение сетевой сборки зависимостей; S2 разрешается отдельно после успешного S1. Не повторять E2-05 probes, не менять их БД/роли/dumps.

### S0: ревизия и образ

1. Read-only preflight: чистота beta, опубликованный SHA, project labels, image IDs, StartedAt/mounts web и обоих PostgreSQL, версии, свободные ресурсы. Не печатать docker inspect ENV, resolved compose/секреты. Любое отличие от ожидаемого baseline — остановка, без исправления чужих сервисов.
2. `git fetch origin beta`, проверка принадлежности REV опубликованной beta, `git pull --ff-only origin beta`; новый detached read-only source worktree. Не накладывать изменения на работающий release. Пример переменных/функции для последующих блоков:

```sh
set -euo pipefail
repo=/home/adm_user/marketplace-workspace/beta/app/repository
# REV: полный SHA, выбранный при отдельном разрешении; не подставлять latest.
: "${REV:?explicit published revision required}"
test -z "$(git -C "$repo" status --porcelain)"
git -C "$repo" fetch origin beta
git -C "$repo" merge-base --is-ancestor "$REV" origin/beta
test "$(git -C "$repo" branch --show-current)" = beta
git -C "$repo" pull --ff-only origin beta
release=/home/adm_user/marketplace-workspace/beta/app/releases/$REV
test ! -e "$release"
git -C "$repo" worktree add --detach "$release" "$REV"
test "$(git -C "$release" rev-parse HEAD)" = "$REV"
test -z "$(git -C "$release" status --porcelain)"
export SECURITY_SOURCE="$release/backend"
dc() { docker compose --project-name marketplace-beta --env-file /dev/null --project-directory /home/adm_user/marketplace-workspace/beta/deploy -f /home/adm_user/marketplace-workspace/beta/deploy/compose.json "$@"; }
```

3. Отдельная сборка `docker build --pull=false -t "marketplace-workspace/backend:e2-06-$REV" "$release/backend"`; перед ней отказ при занятом tag. Только requirements.lock, only-binary, require-hashes; offline cache недостаточен по прежним данным, сеть к registry/PyPI требует явного S0. Не устанавливать пакеты в работающий web. Сохранить immutable image ID и сверить requirements.lock внутри image с Git; `SECURITY_IMAGE` далее равен этому ID, не плавающему tag. Старый образ остаётся.

### S1: только postgres-test

1. Проверить свободность имён `mw_beta_test_e2_06_suite`, `mw_beta_test_e2_06_web`, `mw_beta_test_e2_06_recovery`, `mw_beta_test_e2_06_restore` и роли `mw_beta_test_e2_06_web`. При совпадении остановка, без reuse/drop/автовыбора. Это отдельные объекты от E2-05. Test runner имеет CREATEDB только в test-кластере, bootstrap только одноразовому ACL probe.
2. Создание только нового синтетического Fernet key `beta/config/secrets/e2_06_test_encryption_key`, 0600, readable UID 10001, вне Git/БД. Генерация в изолированном процессе без stdout, O_EXCL; не использовать ключ основной beta. Перед разрешением зафиксировать владельца каталога и безопасный способ доставки UID. Проверить отдельную зашифрованную копию и восстановление в другой новый файл; сравнение только boolean, никаких fingerprints/значений ключа в отчёте. Не перезаписывать существующие secret-файлы.
3. Проверить compose merge (`config --quiet`), эффективные сети/порты/UID/limits и секреты по именам: только test-private, без host ports. Для основного web/БД сравнить ID/StartedAt до/после. Запускать команды по очереди:

```sh
: "${SECURITY_IMAGE:?reviewed immutable image ID required}"
dc -f "$release/beta/deploy/compose.security-check.json" config --quiet
dc -f "$release/beta/deploy/compose.security-check.json" run --rm --no-deps -T security-suite </dev/null
dc -f "$release/beta/deploy/compose.security-check.json" run --rm --no-deps -T security-role-check </dev/null
dc -f "$release/beta/deploy/compose.security-check.json" run --rm --no-deps -T security-suite python -m tools.verify_security_recovery seed </dev/null
```

Suite: новая Django test DB, все E2-06 + выбранные ownership/guard regressions, skips запрещены; стандартный runner удаляет только свою вновь созданную disposable suite DB после успеха. Role probe сохраняет свою новую БД/роль, проверяет реальный LOGIN, точные DML, grant/revoke/reapply, HTTP MFA/CSRF, 17 SQL-отказов; finally NOLOGIN/PASSWORD NULL. При обрыве — отдельная проверка/отключение только своей роли, не reuse. Recovery seed создаёт обе новые БД и синтетический ciphertext/history. Результаты Linux/PostgreSQL не предрешены.

4. Dump/restore в контейнере postgres-test, без выдачи bootstrap секрета web; пароль только внутри процесса, shell tracing выключен. Имена seed/restore фиксированы, dump новый (noclobber):

```sh
dump_name="e2-06-synthetic-$(date -u +%Y%m%dT%H%M%SZ).dump"
dc exec -T -e E206_DUMP="$dump_name" postgres-test sh -eu -c 'umask 077; set -C; export PGPASSWORD="$(cat /run/secrets/db_test_bootstrap_password)"; pg_dump -U mw_beta_test_bootstrap -d mw_beta_test_e2_06_recovery --format=custom > "/backups/$E206_DUMP"' </dev/null
dc exec -T -e E206_DUMP="$dump_name" postgres-test sh -eu -c 'export PGPASSWORD="$(cat /run/secrets/db_test_bootstrap_password)"; exec pg_restore -U mw_beta_test_bootstrap --role=mw_beta_test_runner --no-owner --no-acl --exit-on-error -d mw_beta_test_e2_06_restore "/backups/$E206_DUMP"' </dev/null
dc -f "$release/beta/deploy/compose.security-check.json" run --rm --no-deps -T security-suite python -m tools.verify_security_recovery verify </dev/null
```

Verify сравнивает строки/миграции в памяти без печати, проверяет расшифрование отдельным ключом, отказ неправильного ключа и replay, quarantine без повышения прав, сохранность snapshots. ACL не входит в no-acl restore: отдельно проверить применимость точного контракта к restored schema транзакционным apply/verify/rollback с новой тестовой ролью. Последний шаг и восстановление из независимой копии ключа требуют отдельного исполнительного протокола S1; пока **не закрыты**. Сохранить source/restore/dump/key и evidence без значений; не объявлять общий disaster recovery E2-15 выполненным.

5. В S1 отдельно запустить maintenance overlay на одноразовом тестовом сервисе с тем же gunicorn/image, проверить 503 всех auth/бизнес-путей и 200 liveness/503 readiness без БД/ключа. Проверить реальные HTTP в контейнере и минимальные страницы браузером, не сохранять секретные ответы. Локальный Django Client/WSGI unit test не заменяет эту проверку.

### S2: основная beta, отдельное разрешение после S1

1. Повторно сверить SHA/image/lock, baseline web и counts/миграции основной БД (пустота не предполагается). Приватно сохранить metadata и ACL без pg_authid/password; новый main dump `e2-06-before-<UTC>.dump`, 0600/noclobber. Создать только новую `mw_beta_test_e2_06_main_before` в postgres-test, отказ при занятости, REVOKE PUBLIC, pg_restore --no-owner --no-acl --exit-on-error. Сверить все таблицы/миграции в памяти и первоначальный ACL отдельно. Этот main backup/restore не выполнен и нуждается в read-only preflight перед конкретным запуском.
2. Новый отдельный beta TOTP key `beta/config/secrets/mfa_encryption_key`, 0600/read-only UID10001; отдельная зашифрованная копия Олегу и проверка её восстановления. Не включать production. Operator verifier/аварийный секрет пока не создавать: аккаунтов может ещё не быть, их проверка и выдача требуют отдельного явного запроса.
3. Применять только git overlay ниже, старые accounts overlay одновременно не накладывать. До применения сверить additive migration plan и SQL обоих account_security migrations; запрещено удаление предметных данных или расширение ownership прав. На время schema/ACL изменения перевести web в проверенный maintenance, поскольку новые invoker triggers требуют новых прав уже при старых password/block операциях.

```sh
dc -f "$release/beta/deploy/compose.security-web.json" config --quiet
dc -f "$release/beta/deploy/compose.security-web.json" run --rm --no-deps -T migrate python manage.py check </dev/null
dc -f "$release/beta/deploy/compose.security-web.json" run --rm --no-deps -T migrate python manage.py migrate --plan </dev/null
dc -f "$release/beta/deploy/compose.security-web.json" run --rm --no-deps -T migrate python manage.py sqlmigrate account_security 0001 </dev/null
dc -f "$release/beta/deploy/compose.security-web.json" run --rm --no-deps -T migrate python manage.py sqlmigrate account_security 0002 </dev/null
# Только после backup/restore, review и отдельного APPLY-разрешения S2:
dc -f "$release/beta/deploy/compose.security-maintenance.json" up -d --no-deps web
dc -f "$release/beta/deploy/compose.security-web.json" run --rm --no-deps -T migrate python manage.py migrate --noinput </dev/null
dc -f "$release/beta/deploy/compose.security-web.json" run --rm --no-deps -T migrate python -m tools.manage_security_web_grants apply </dev/null
dc -f "$release/beta/deploy/compose.security-web.json" up -d --no-deps web
dc -f "$release/beta/deploy/compose.security-web.json" exec -T web python -m tools.verify_security_web_runtime </dev/null
```

`BACKEND_IMAGE` для maintenance должен быть закреплённым прежним `marketplace-workspace/backend:e2-03-0210f27a7ab1` с проверенным image ID; SECURITY_SOURCE остаётся новым read-only E2-06 release. Maintenance использует только stdlib WSGI, не Django. Ни основной PostgreSQL, ни postgres-test не пересоздавать; сравнить контейнеры/сети после. Основной smoke не создаёт аккаунты и не закрывает полный MFA lifecycle: он проверяется синтетически в S1.

### Откат и восстановление

После включения MFA возвращать обычный E2-05/base-only web нельзя: он умеет входить без MFA. При ошибке только `compose.security-maintenance.json` на проверенном старом image + новом Git source (503 auth/business) либо остановка только beta web. Сохранить новую схему/данные/ключи; предпочтительно исправление вперёд. Проверка реального maintenance в S1 обязательна до S2.

Отзывать только новые ACL через `manage_security_web_grants revoke` после выключения потребителя, не старым E2-05 revoke. Reverse guard 0002→0001 допустим только как проверка в disposable test DB; zero удаляет security-данные и запрещён для используемой БД. Восстановление всегда в новую БД, сверка/карантин доступа, отдельная процедура включения; dump поверх живой БД запрещён. Нет prune/down -v/reset --hard/clean, удаления releases/dumps/ключей/старых тестовых БД.

Локальный откат: сравнить manifest/hashes и поздние правки, обратный diff только E2-06, сохранить журнал добавлением отмены. Девять разрешённых пакетов можно удалить только после проверки отсутствия новых потребителей и восстановления прежнего lock; автоматическое удаление не выполняется. Рабочая beta пока E2-05 по последнему документированному состоянию; этот документ не меняет её запуск.


## Фактический S0/S1 — 2026-10-01T17:07:24+03:00

Олег отдельно разрешил S0/S1. Проверенная опубликованная ревизия: `3db1c0c64880985489b86b52aa725e0c839ca001`. Серверный Git обновлён fast-forward; отдельный release по указанному выше пути. Собран image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`, lock равен Git, pip check успешен. Compose 5.1.3: только test-private, без ports/основных секретов, UID10001, read-only, 256 MiB/0.25 CPU. Весь код на сервер поступил из опубликованной beta; ручных source-правок нет.

PostgreSQL 17.11: 61 тест за 493.226 с, 60 успешны, 1 ошибка, 0 skips. `test_same_recovery_code_has_one_successful_consumer` получил lock_timeout=2000ms на ownership_user: PBKDF2 выполнялся при удержании блокировки. Suite не принят. Disposable suite DB удалена штатным Django runner; основная/исторические тестовые БД не трогались.

Независимый limited LOGIN probe **PASS**: точные DML, grant/revoke/reapply, настоящий HTTP/CSRF/MFA, 17 SQL-отказов. `mw_beta_test_e2_06_web` БД сохранена; одноимённая роль NOLOGIN, PASSWORD NULL. Повторно `verify_security_web_role` не запускать: имя занято.

Новые `mw_beta_test_e2_06_recovery` и `mw_beta_test_e2_06_restore` сохранены. Dump `beta/backups/test/e2-06-synthetic-20261001T135847Z.dump`, 222907 bytes, 0600. Два соседних `.<database>.acl.json` сохранены закрыто. Restore --no-owner/--no-acl/--exit-on-error **PASS**: все проверяемые строки/миграции совпали; отдельно восстановленный ключ расшифровывает TOTP; wrong-key/replay отклонены; quarantine не расширяет членства. Проверки поведения откатились транзакционно, снимки сохранены. Точный ACL применён/отозван/повторно применён на восстановленной схеме в одной транзакции с существующей NOLOGIN-ролью: временный CONNECT переключался только внутри транзакции, после rollback исходные ACL/CONNECT совпали полностью; LOGIN повторно не включался.

Только синтетические ключевые файлы: runtime `beta/config/secrets/e2_06_test_encryption_key`; encrypted envelope `beta/backups/test/e2-06-key-envelope/envelope.json`; пароль отдельно `beta/config/e2-06-test-key-recovery/backup-passphrase`; независимо восстановленный ключ `beta/config/e2-06-test-key-restored/key`. Файлы 0600/UID10001; родительские новые каталоги закрыты. Восстановление выполнялось без mount оригинала, затем равенство проверено boolean, без fingerprints/значений. Сам DB restore verifier запускался с восстановленным ключом в /run/secrets/mfa_encryption_key, оригинальный ключ не монтировался. Это не ключ основной beta, не выдача секрета владельцу и не передача в Telegram.

Maintenance проверен в реальном Gunicorn старого dependency image на новом Git source, в отдельном контейнере network=none, без DB/key: live=200, auth/business/ready=503, no-store. Контейнер удалён. У web и обоих PostgreSQL до/после строго совпали ID/image/StartedAt/mounts/networks/ports; основной E2-05 read-only SQL/runtime smoke PASS. Никакого S2/основного ключа/миграций/прав/перезапуска web не было.

Локальное исправление (следующий коммит): пароль и PBKDF2 резервного кода проверяются до блокировки. В короткой транзакции заново проверяются активность/тот же password hash, тот же verifier и used_at=NULL, затем код расходуется однократно. Хеширование/число итераций/лимиты не ослаблены, PostgreSQL timeouts/CPU не увеличены. Добавлены проверки отсутствия транзакции во время hash verification и отказа при смене пароля между проверкой и lock. Все 34 затронутых локальных теста прошли за 73.747 с; check/makemigrations --check успешны. Это ещё не повторный PostgreSQL результат.

Продолжение уже разрешённого S1: Олег публикует коммит исправления; проверить remote SHA, получить его Git, создать новый detached release, сверить неизменность lock с image выше, задать SECURITY_SOURCE нового release. Выполнить только full security-suite на свежей свободной `mw_beta_test_e2_06_suite`; ожидается 63 теста без skips. Не запускать заново role/seed probes и не удалять занятые БД/роль/backup/key. Результаты SQL/restore относятся к 3db1c0c и не выдаются за тест исправленной функции. Реальный браузерный сценарий и полная operator CLI с фактической доверенной ролью/секретом ещё не выполнены; реальные аккаунты не создавались. S2 остаётся отдельным разрешением после S1.

Технические замечания выполнения: два SSH banner timeout не выполнили команд; проверка Compose сначала сравнила строковый mem_limit с integer, затем тип был корректно нормализован, конфигурация не менялась. Первый блок восстановления выполнил seed и dump, но Docker exec получил stdin SSH и поглотил следующие команды; readback подтвердил существующий dump и пустую restore БД. Продолжение использовало тот же dump в эту пустую БД, без повторного seed/перезаписи. Рецепт выше исправлен добавлением </dev/null к stdin-free docker exec.


## E2-06: повторный PostgreSQL-suite — 2026-10-01T17:31:37+03:00

Публикация 19a6d6a подтверждена; сервер получил исправление только через Git, новый detached release смонтирован read-only. Существующий image использован после проверки неизменного lock; новых сборок/зависимостей нет. PostgreSQL 17.11: 63 теста PASS, 0 ошибок/пропусков за 493.704 с. Конкурентное расходование кода и смена пароля между проверкой и lock прошли при прежних 0.25 CPU/256MiB/lock_timeout=2000ms. Disposable suite DB удалена штатным runner, отсутствие подтверждено SELECT.

Три сохранённые E2-06 БД на месте, роль NOLOGIN/PASSWORD NULL; role/seed probes не повторялись. Доказательства ограниченного LOGIN/17 SQL-отказов и dump/restore остаются привязаны к 3db1c0c. ID/image/StartedAt/mounts/networks/ports основного web и обоих PostgreSQL неизменны; E2-05 SQL/runtime smoke PASS, одноразовых контейнеров нет. S2 не выполнялся. E2-06 остаётся «На проверке»: браузер, полная операторская CLI-процедура, основная beta и фактическое хранение ключа ещё не закрыты; рабочий экспорт зависит от E2-07/E2-08/E5-07. Все 101 строки задач сохранены.

S2 не разрешён: конкретная последовательность backup/restore, отдельного beta ключа, maintenance, миграций/минимальных прав и web-only switch приведена выше. Рабочий web остаётся 82b2004 с accounts overlay; base-only запуск и откат к password-only после подключения MFA недопустимы. Синтетическая копия ключа не подтверждает хранение реального ключа Олегом или его передачу в Telegram. Исторические фразы «не проверено» выше относятся к моменту исходного запуска; актуальная матрица — SYSTEM_SECURITY_CHECKS.json.


## E2-06: применён S2 — 2026-10-01T17:58:26+03:00

По явному текущему разрешению Олега основная beta обновлена до E2-06. Опубликованный протокол f4f6059 получен Git fast-forward; рабочий код закреплён на проверенном 19a6d6a, read-only. Использован существующий dependency image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72` с совпавшим lock; новых установок/сборок нет. Новый dump `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-before-20261001T144009Z.dump` (0600, 75491 bytes), соседние `.acl.json`/`.snapshot.json` и restore в `mw_beta_test_e2_06_main_before` сохранены. Все 18 исходных таблиц совпали; основной ACL до применения не менялся.

Отдельный beta TOTP key вне БД/Git и его парольная encrypted envelope созданы в закрытых файлах 0600/UID10001. Копия восстановлена в другой файл без mount оригинала, равенство проверено без вывода значений. Это техническое восстановление на сервере, не независимое хранение у Олега: Telegram не использован, пароль и envelope ещё не переданы владельцу. Аварийный секрет владельца не создавался.

Проверены Compose/lock/check/план и SQL; RunPython guards прочитаны в опубликованном коде (sqlmigrate их не разворачивает). Maintenance реально закрыл auth/business/ready с 503 и оставил live 200; затем применены 9 операций миграций и точный column-grant delta. В django_migrations теперь 36 записей: two_factor squash записал 8 заменённых плюс собственную, всего 17 новых записей при 9 операциях. Обновлён только web; оба PostgreSQL сохранили ID/image/StartedAt/mounts/networks/ports.

S2 runtime PASS: реальная mw_beta_web, точные ACL/guards, live/ready 200, session 401, старый login GET 405, MFA login GET 200. Chromium проверил анонимные страницы входа/восстановления, обязательные поля, CSRF 403 и no-store через временный localhost SSH-туннель; browser/tunnel закрыты. Это не полный браузерный MFA lifecycle и не публичный TLS. Оба operator CLI отклонены из web-роли; положительная процедура с отдельным секретом не выполнялась.

Финально users/organizations/memberships/authenticators/recovery permits/codes = 0; две анонимные wizard sessions зашифрованы, не являются полноценными аккаунтными сессиями. Штатные plaintext OTP таблицы пусты, locmem и выключенные внешние flags подтверждены; public synthetic export probe выключен. Все oneoff контейнеры удалены. Полный suite 63/63 без skips относится к предыдущему S1 на том же коде и в S2 повторно не запускался. E2-06 остаётся «На проверке»: полный браузерный сценарий, положительный operator CLI, фактическое хранение ключа владельцем и полный экспорт ещё не закрыты; E2-07/E2-08/E5-07 не реализованы.

Текущие команды запуска и запрещённый после MFA E2-05 fallback явно обновлены в SYSTEM_STARTUP.md. Выдача реального owner proof не входит в выполненный S2. Для полного положительного operator/browser rehearsal требуется новый конкретный план изолированных ресурсов: guard команды требует фактические mw_beta/mw_beta_migrator; менять guard, подменять идентичность mock-ом или запускать прежние занятые probes ради отчёта нельзя.


## E2-06: подготовлен дополнительный стенд — 2026-10-02T11:32:42+03:00

Подготовлены конкретный план docs/E2-06_OWNER_REHEARSAL.md, отдельный Compose/guarded provisioning, синтетический fixture и браузерный runner для положительного operator CLI. Новые ресурсы marketplace-e206-owner-check: отдельный PostgreSQL с собственными БД/ролями/ключами, внутренняя сеть, volume и web/controller/issuer; реальные имена DB/LOGIN соответствуют неизменённому operator guard, принадлежность проверяется cluster_name и marker. Основная beta/старые probes не используются для fixture. Четыре синтетических аккаунта/две организации; реальные лимиты не ослабляются, TOTP время не подменяется.

Локально проверены AST/Node syntax, JSON/секретные mounts, чтение плана без действий и безопасные отказы при отсутствии нужной среды; существующие Playwright API/Chromium доступны без установки. SSH/новые серверные ресурсы/полный browser/положительный operator CLI не выполнялись. Публикация e3e5383 подтверждена; подготовку публикует Олег, затем нужно отдельное разрешение точного плана новых ресурсов. E2-06 остаётся «На проверке», все критерии и строки задач сохранены. Основной ключ/его передача/реальный owner proof/рабочий экспорт не входят в новый стенд.

Подробный состав, команды, границы и остановка: [E2-06_OWNER_REHEARSAL.md](E2-06_OWNER_REHEARSAL.md). Это запрос отдельного разрешения после подготовки конкретных файлов, а не продолжение старого разрешения S2 на новые ресурсы.


## E2-06: изолированная проверка и исправление браузерного CSRF — 2026-10-02T12:10:06+03:00

По отдельному разрешению Олега опубликованный 6ec715f получен через Git; новый marketplace-e206-owner-check создан строго по docs/E2-06_OWNER_REHEARSAL.md. Реальные PostgreSQL 17.11/LOGIN/миграции/точные web ACL/изоляция/locmem/lock прошли. Подготовлены четыре синтетических аккаунта, две организации и закрытый owner proof штатным prepare_owner_recovery; не-владельцу отказано. Полная выдача operator permit ещё не проверена.

Chromium выявил блокирующий дефект: native login POST получает 403, поскольку no-referrer даёт Origin:null; cookie/CSRF-поле присутствуют. Вход ещё не выполнялся, факторов/кодов/permits/challenges/аккаунтных сессий/buckets нет. Стенд остановлен с сохранением volume/ключей/fixture/proof. Основной web и оба PostgreSQL не менялись, их baseline и restricted runtime smoke прошли; основной source 19a6d6a сохраняет дефект заголовка.

Локально установлен same-origin, CSRF/Origin и secure cookies сохранены. Отдельная проверка настоящим Chromium/Django LiveServer воспроизвела дефект до исправления и прошла после (1/1); 33 HTTP-регрессии PASS без skips. Это SQLite/локальный браузер, не новый PostgreSQL результат. Новый read-only pre_browser guard и точное продолжение сохранённого стенда не допускают reseed/сброса состояния. Push делает Олег, затем продолжается уже разрешённый изолированный этап. E2-06 остаётся «На проверке»: нужны полный browser/issue CLI и серверная проверка исправления, отдельное обновление основной beta, независимое хранение ключа владельцем; рабочий экспорт зависит от E2-07/E2-08/E5-07. Исходные 101 строка и критерии задач не менялись.


## E2-06: браузер и операторское восстановление на PostgreSQL — 2026-10-02T12:35:46+03:00

Публикация 14d9f48 подтверждена; исправление получено только Git в новый detached release, source переключён только у приложений сохранённого marketplace-e206-owner-check. Read-only pre_browser прошёл: 4/2/5 прежних users/org/memberships, до входа нулевые факторы/сессии/коды/permits/challenges/buckets; повторного provisioning/сброса нет. Существующий image/lock, effective Compose, реальная web LOGIN/SQL-контракт и изоляция прошли. Основная beta осталась на 19a6d6a.

В настоящем Chromium пройдены восемь функциональных этапов: подключение с неверным/просроченным/верным TOTP и однократным показом кодов; replay/CSRF/запрет отключения владельцем; текущий/выборочный/общий отзыв, trusted device и reauth; одноразовое восстановление кодом; настоящая operator CLI с неверным proof/другим владельцем, однократным permit и повторным подключением; смена пароля с сохранением MFA и отзывом доверия; блокировка с отказом кода/operator; добровольный парольный вход обычного участника. CLI действительно работала под mw_beta_migrator через getpass/PTY, не mock. Права/организации/членства сохранены.

Сводный runner завершился exit1: последняя проверка ошибочно ожидала новый пароль после блокировки, хотя E2-05 делает пароль unusable. Это ошибка проверочного скрипта; runtime не изменяется. Правильное конечное состояние отдельно подтверждено read-only на PostgreSQL: владелец заблокирован, оба пароля отвергнуты, все сессии/доверие отозваны, единственный permit использован, 4/2/5 и владение неизменны, данные MFA зашифрованы/коды хешированы, plaintext OTP-таблицы пусты. Полный зелёный exit и нулевой итоговый pageerror count не заявляются. Helper исправлен только локально; весь сценарий на использованном fixture не повторяется.

Четыре контейнера остановлены, volume/ключи/proof/verifier/permit сохранены, browser/tunnel закрыты. Основной web и оба PostgreSQL совпали с baseline до и после остановки, restricted SQL/runtime PASS. План отдельного обновления только основного web — docs/E2-06_WEB_FIX_ROLLOUT.md; его запуск ещё не разрешён. E2-06 остаётся «На проверке»: обновление основной beta, ограничения сводного runner, независимое хранение ключа Олегом и рабочий экспорт не закрыты; E2-07/E2-08/E5-07 не реализованы. 101 строка и критерии задач неизменны.

Уточнение итогового main SELECT: users/org/memberships/authenticators/codes/permits/account sessions=0; четыре Django wizard sessions зашифрованы и анонимны. GET login в runtime smoke может создавать такие записи, поэтому неизменность контейнеров не означает побайтовую неизменность таблицы django_session.


## E2-06: основной web обновлён до 14d9f48 — 2026-10-02T13:41:10+03:00

По отдельному явному разрешению выполнен docs/E2-06_WEB_FIX_ROLLOUT.md. Публикация beta `91b079a30569b6fc38997b47fe18d6af723b9321` подтверждена, чистый серверный repository обновлён только Git fast-forward. Основной web использует существующий read-only release `14d9f48cee6eb2a9d7eca9f029770af51c45b6d9/backend` и прежний immutable dependency image. Исполняемое приложение изменилось только в Referrer-Policy: same-origin; CSRF, secure cookies, lock, схема, SQL-права и ключи сохранены. Пересоздан только web, оба PostgreSQL сохранили ID/image/StartedAt/mounts/networks/ports; четыре контейнера owner rehearsal остались остановленными.

Закрытый metadata checkpoint `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-referrer-before-20261002T102702Z.metadata.json` создан без перезаписи (0600), read-back совпал. Наличие и режимы прежних S2 dump/ACL/snapshot/key envelope и отдельных key/passphrase проверены без вывода содержимого. Новые dump/restore, миграции, GRANT/REVOKE, DB/роли/ключи, установки и сборки не выполнялись; S1/S2 backup/restore остаются историческими доказательствами.

Фактическая ограниченная mw_beta_web, точные SQL-права/guards и runtime smoke PASS: live/ready 200, session 401, legacy login GET 405, MFA login GET 200. В Chromium GET login 200, same-origin/no-store, secure cookie/CSRF-поле, корректный native POST Origin; POST отменён до сервера. Pageerrors=0 только в этой анонимной проверке; она не заменяет полный owner rehearsal и не подтверждает публичный TLS. Browser/tunnel закрыты. Основные users/org/memberships/authenticators/codes/permits/account sessions/attempt buckets/auth denials равны нулю; анонимные encrypted Django sessions выросли с 4 до 6 из-за GET login. Locmem/выключенные внешние flags и public export probe подтверждены.

E2-06 остаётся **На проверке**: чистый итог полного runner/его pageerror counter, запуск исправленного helper на Linux, независимая копия ключа у Олега и критерий рабочего экспорта ещё не закрыты. Реальные owner proof/передача envelope и отдельного пароля не выполнялись и требуют конкретного отдельного разрешения; E2-07/E2-08/E5-07 не реализуются здесь. Полные 63 PostgreSQL-теста S1 и восемь функциональных браузерных этапов прежнего стенда в этом переключении не повторялись.

Протокол: SYSTEM_SECURITY_CHECKS.json/main_web_referrer_rollout. Сохранённый baseline owner rehearsal относится к основному web до этого разрешённого обновления; его нельзя молча переписать или заново запускать pre_browser на уже использованном fixture. Безопасный fallback — согласованный MFA maintenance либо остановка только web, без base-only/accounts overlay и восстановления поверх живой БД.


## E2-06: исправленный finish проверен отдельно — 2026-10-02T13:58:37+03:00

По явному текущему разрешению публикация dd9803597941e9516676e8f03aa0cb6f48f1eb92 подтверждена; серверный repository обновлён только Git fast-forward, новый detached release смонтирован read-only только controller сохранённого marketplace-e206-owner-check. Существующий PostgreSQL стенда запущен без пересоздания, controller пересоздан на прежнем image/lock. Сохранённые web/issuer остались остановленными и неизменными. Код auth, SQL-права и схема не менялись; configure/init/pre_browser/operator/browser не запускались.

Штатный action `finish` опубликованного `tools.owner_rehearsal` вызван через его main в диагностическом процессе с default_transaction_read_only=on с момента подключения; transaction_read_only=on проверен до и после. Настоящие mw_beta/mw_beta_migrator, marker/cluster_name и locmem guards пройдены. PASS: владелец заблокирован, пароль unusable, сессии/доверенные устройства=0, один permit использован, приглашений=0, владение/членства неизменны. Один подтверждённый фактор сохранён у заблокированного аккаунта; доступ запрещён состоянием аккаунта. Закрытые state/output/secret файлы побайтово и по metadata не изменились; значения и fingerprints не выводились.

После проверки все четыре контейнера стенда остановлены; volume/ключи/fixture/proof/permit и старый baseline сохранены. Основной web на 14d9f48 и оба PostgreSQL основной beta совпали по ID/image/StartedAt/mounts/networks/ports до/после. Новый controller ID `6a6602e6b86644bae7614e8f7bb2194c578984883c8d8c8482143d79f3feaf1b`, StartedAt `2026-10-02T10:54:52.361712667Z`; точный протокол — SYSTEM_SECURITY_CHECKS.json/owner_rehearsal_finish_readonly.

E2-06 остаётся **На проверке**. Отдельный PASS finish не превращает прежний aggregate exit 1 в успешный полный браузерный прогон и не подтверждает его итоговый pageerror counter. Независимая копия ключа у Олега и критерий рабочего экспорта остаются открытыми; реальные owner proof/передача ключа не выполнялись. Новые dump/restore, миграции, GRANT/REVOKE, DB/роли/ключи/зависимости не создавались. Повторный полный сценарий требует нового конкретного плана и отдельного разрешения; терминальный fixture не сбрасывать. Откат этого ограниченного запуска — уже выполненная остановка postgres/controller с сохранением данных, без изменений основной beta.


## E2-06: уточнён объём R2 и подготовлена передача ключа — 2026-10-02T14:49:58+03:00

Олег подтвердил полный браузерный прогон на новом отдельном синтетическом стенде и подготовку передачи ключа. R2 подготовлен в 400f462, для запуска требуется его публикация; старый fixture не сбрасывается. SSH/полный browser в этом шаге не выполнялись. Отдельный план фактической обёртки/получения/проверки копии — docs/E2-06_KEY_HANDOFF.md; её исполнение ещё не разрешено подготовкой.

По прямому запросу создан новый случайный пароль в C:/Users/krolo/Documents/marketplace-recovery/beta/e2-06-backup-passphrase-20261002.txt, вне Git, с проверенными Windows ACL текущего пользователя/SYSTEM и read-back без вывода значения/fingerprint. Он предназначен только для будущего нового envelope; существующей копии S2 этот пароль не соответствует. Основной key/envelope с сервера не читались и не передавались.

После явного уточнения Олег выбрал оба отдельных файла в своём Telegram. Это заменяет прежнее решение о хранении пароля отдельно от Telegram; объяснённый риск общего доступа принят. Агент ничего не отправлял. Новая read-only утилита проверяет envelope с getpass в памяти, отказывает неинтерактивному/echo вводу, не пишет plaintext key. Три локальных синтетических теста прошли, без БД/SSH/реальных секретов; реальный терминал и передача envelope ещё не проверены. E2-06 остаётся «На проверке»: полный R2, фактическая независимая копия ключа и рабочий экспорт не закрыты.


## E2-06: полный браузерный R2 пройден — 2026-10-02T15:23:05+03:00

После явного разрешения полного отдельного браузерного прогона и сообщения Олега о публикации проверена origin/beta `2c2f8f737262267d29d06ab40d7bef3571693745`. Сервер получил эту ревизию только Git fast-forward и новый detached release; requirements.lock совпал с существующим image. Runtime auth/accounts/ownership/config/migrations/SQL grants по сравнению с основной 14d9f48 не изменены. Новых зависимостей/сборок нет.

Создан только фиксированный `marketplace-e206-owner-check-r2`: отдельный PostgreSQL 17.11, internal network без host ports, новый volume, закрытые синтетические secrets и fixture 4 example.invalid пользователя / 2 организации / 5 членств. Миграций 36; точный SQL-контракт настоящего mw_beta_web и runtime smoke прошли до браузера. Controller/issuer использовали настоящую mw_beta_migrator; bootstrap-права web не передавались. Effective Compose и фактические mounts/UID/read-only/limits/logging none проверены.

Полный runner настоящего Chromium на этой ревизии: **10 PASS, result=PASS, exit 0**, actualOperatorCli=true. Проверены неправильный/просроченный/верный TOTP и подтверждённое подключение, показ одноразовых кодов только один раз, отказ повторного TOTP и доступа до MFA, запрет отключения владельцу и CSRF; текущий/выборочный/общий отзыв сессий, доверенное устройство и свежая проверка; одноразовый восстановительный код с обязательным подключением нового фактора; настоящая operator CLI с отказом неверному proof/чужому владельцу, одноразовым permit и сохранением прав; смена пароля с сохранением MFA и отзывом доверия; блокировка и отказ code/operator восстановления; вход участника без добровольно подключённого MFA. Глобальный pageerror counter достигнут и равен 0. TOTP использовал настоящее время и штатные throttles, без сброса buckets/last_t или подмены часов.

Дополнительный внешний audit сначала завершился отказом: проверка домена обращалась к User.email, хотя адреса находятся в AccountContact. Полный browser к этому моменту уже завершился exit 0, включая свой finish. Первый отказ и остановка сохранены в протоколе. Для исправленного чтения временно запущены только сохранённые R2 postgres/controller с теми же ID/source, web/issuer остались остановлены; SQL с начала подключения read-only, browser не повторялся. Итог дополнительно прочитан в SQL read-only: владелец неактивен, пароль unusable, действующих сессий/доверенных устройств=0, использованный permit=1, приглашений=0, организации/членства неизменны. Один подтверждённый фактор остаётся у заблокированного аккаунта; блокировка запрещает доступ. Закрытые файлы имеют 0600 и не изменились при итоговой проверке. Только locmem; секреты/QR/cookies/ссылки/тела ответов/трассы/скриншоты не сохранялись в отчёт.

Tunnel закрыт, все четыре R2 контейнера остановлены; volume/network/закрытые файлы и новый release сохранены. Основной web остался на 14d9f48, ID/image/StartedAt/mounts/networks/ports основной beta и остановленного первого стенда совпали до/после. Их ключи/данные/старые baseline не использовались как fixture и не изменялись. R2 root: `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-06-owner-r2-20261002`; ресурсы теперь заняты, повтор provisioning/init/full browser на этом fixture запрещён.

Исторический первый aggregate exit 1 сохранён как факт; новый R2 независимо закрыл чистый полный exit и pageerror counter. Конкурентность, 17 SQL-отказов, синтетическая экспортная ссылка, dump/restore и maintenance остаются доказательствами S1, здесь повторно не запускались. Основной ключ не читался/не передавался; K1/K2/K3 по docs/E2-06_KEY_HANDOFF.md и рабочий экспорт/RBAC/RLS остаются за границами этого прогона. E2-06 **На проверке** до оставшихся критериев; E2-07 и далее не начаты.

Безопасный откат запуска уже выполнен: stop только R2 с сохранением volume/network/files; не down -v, DROP, prune, live restore, reseed или сброс counters. Новый запуск/удаление ресурсов — отдельный конкретный план и разрешение. Подробный протокол: SYSTEM_SECURITY_CHECKS.json/browser_r2_run.


## K1/K2 разрешены; требуется ввод владельца — 2026-10-02T15:44:49+03:00

Олег отдельно разрешил K1/K2 по этому плану. Проверена опубликованная beta b3c50f7034bd454ea8066c6f194010d91ca9068a; для операций выбран уже опубликованный immutable release 2c2f8f737262267d29d06ab40d7bef3571693745. Его backup/crypto/operator/requirements.lock неизменны относительно основной 14d9f48, lock совпал с существующим image. Main source и RO mount TOTP key сверены; ID/image/StartedAt/mounts/networks/ports трёх основных и восьми остановленных тестовых контейнеров неизменны. Значения ключа и старого пароля не читались: проверены только mode/UID/size/mtime/inode существующих key/S2 envelope/passphrase, без их fingerprints.

После проверки отсутствия создан только новый каталог `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-owner-key-envelope-20261002`, 0700/UID10001. Проверена сохранность прежних metadata после подготовки. Сам envelope ещё не создан, runtime key не читался, ничего не скачано; web/БД/ключи/старые копии не менялись, сохранённые стенды не запускались. Локально повторно проверены закрытые ACL каталога marketplace-recovery/beta и существующего файла пароля, отсутствие целевого envelope; пароль не читался.

Локальный интерактивный launcher `.change-backups/2026-10-02/E2-06-key-handoff-k1-k2/owner-key-handoff.ps1` выполняет K1 в терминале Олега, сохраняет только код завершения, ожидает безопасное получение ciphertext агентом и запускает опубликованный read-only verifier K2 с ещё одним скрытым вводом. `owner_wrap_console.py` сохраняет argv через Windows subprocess и наследует терминал без capture/трассировки. Непосредственная передача длинной команды через старый PowerShell не прошла локальную проверку argv и заменена этим вызовом; Python Windows argv roundtrip и отказ без TTY до SSH прошли. Синтаксис PowerShell/Python проверен. Это не выполненный реальный getpass/wrap/transfer/unwrap.

`server_step.py prepare` уже выполнен и повтору не подлежит. После owner-wrap-result exit0 требуется `server_step.py verify`, затем `download_envelope.py`: только новый ciphertext через приватный SSH pipe, размер/формат/0600, эксклюзивная запись вне Git с ACL владельца/SYSTEM, read-back и повторное побайтовое сравнение в памяти. После download-result PASS launcher запросит пароль для локального verifier и запишет безопасный owner-verify-result. Пока результатов владельца нет, K1/K2 считаются ожидающими его ввода, а не выполненными. Новое разрешение K1/K2 не требуется; параметры и назначение не менялись. В чат не передаются пароли/ключи/QR/cookies/ciphertext/fingerprints; Telegram агент не использует.

E2-06 остаётся «На проверке»: actual K1/K2, K3 (ручное хранение и проверка скачанного обратно файла) и экспортные зависимости не закрыты. R2 остаётся PASS из предыдущего этапа. Безопасный откат этой подготовки — сохранить новый закрытый пустой каталог и локальные скрипты; серверные процессы одноразовые завершились с --rm, web/БД откатывать не требуется. Удаление любых новых/частичных файлов требует сверки точного пути и отдельного решения; старые key/envelope/passphrase не удалять, prepare/wrap не повторять вслепую.


## Первый ввод K1 завершился отказом — 2026-10-02T15:56:18+03:00

После разрешения ExecutionPolicy только для процесса владелец запустил свой терминал; screenshot подтвердил достижение штатного `Separate backup passphrase` без раскрытия введённого значения. Пользователь сообщил, что пароль не вставляется; объяснены скрытый ввод и способы вставки. Затем локальный launcher зафиксировал K1 exit1 (2026-10-02T15:50:17.0879930+03:00). Конкретная причина отказа не установлена: получено только безопасное значение кода, терминал и ввод не записывались. Попросили уточнить только текст приглашения/ошибки, без пароля. Не выдаём это за успешное обёртывание или доказанный дефект crypto.

После отказа отдельный read-only контейнер с mount только нового output-каталога подтвердил: каталог пуст, envelope отсутствует. Существующие файлы не перезаписывались, download не запускался, owner verify не выполнен. Первый agent metadata verify был вызван до появления owner completion marker и отказал; его verify-result.json сохранён. До повторного metadata verify/download добавлен обязательный gate owner-wrap-result exit0. Следующий ограниченный verify-after-owner сохраняет отдельный протокол; это не автоматический повтор wrap.

Повторный wrap пока не выполнялся и не подготовлен как обход ввода. K1/K2 остаются разрешёнными, но для продолжения нужно уточнение владельца по терминалу и проверка отсутствия output перед согласованным продолжением. Файл owner-wrap-result.json намеренно блокирует слепой повтор launcher; его не удалять/не перезаписывать. Исходный пароль остаётся в ранее созданном закрытом файле; агент его не читал. Доступ runtime key внутри неудачного разрешённого CLI не определялся; отсутствие вывода или копии не доказывает, что CLI не читал ключ в памяти. Ключ/пароль/ciphertext в отчёт не попадали.

Состояние: E2-06 «На проверке», R2 PASS сохранён, K1 — attempted/failed, K2/K3 — не выполнены. Основной runtime не менялся; серверный output-каталог сохранён пустым. Нового разрешения на неизменные K1/K2 не требуется. Безопасный откат — сохранить evidence и каталог; не удалять результаты отказа или старые ключевые копии, не повторять wrap вслепую. Дальнейшее продолжение определяется фактическим сообщением терминала, а не предположением о причине ошибки.


## K1/K2 выполнены с согласованным чтением закрытого файла — 2026-10-02T16:13:47+03:00

После повторной проблемы вставки Олег остановил интерактивную попытку Ctrl+C (owner-wrap-retry-result exit130) и явно разрешил заменить ручной ввод автоматическим чтением существующего закрытого файла пароля. Это явное изменение способа ввода, а не обход MFA или молчаливое изменение прежнего плана. Повторный launcher был подготовлен только после fresh read-only подтверждения пустого output, отсутствия активного writer и неизменности основной beta/старых копий; первый отказ exit1 сохранён. До автоматического шага подтверждено отсутствие активных контейнеров, использующих новый output. Существующие результаты не удалялись и не перезаписывались.

Первый автоматический запуск остановился до чтения пароля/SSH на локальном ACL-вызове: у дочернего Windows PowerShell5 в этой среде недоступен Get-Acl. Права отдельно подтвердились. Вспомогательный вызов переведён на уже установленный PowerShell7.6.5; повторная ACL-проверка прошла, установки/смены системной ExecutionPolicy нет. Первый отказ automatic-result.json сохранён. Локальный код backup/verifier побайтово совпал с опубликованным2c2f8f7; cryptography/backup алгоритм не менялись.

Фактический результат automatic-after-acl-result.json: **PASS**, K1 wrap_completed=true, K2 download_completed=true/decrypt_verified=true. Процесс прочитал только существующий `C:/Users/krolo/Documents/marketplace-recovery/beta/e2-06-backup-passphrase-20261002.txt` в память после ACL-проверки. Пароль передан только через приватный SSH stdin в одноразовый network-none/logging-none/readonly/UID10001 контейнер с RO опубликованным source и основным key, RW только новым output; никаких значений в argv/ENV/логи/отчёт. Вызывались неизменённые published account_security.key_backup.wrap и operator.write_private_new, без getpass/PTY и без изменения runtime MFA. Парольный файл не изменился.

Создан новый серверный `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-owner-key-envelope-20261002/envelope.json`, 0600/UID10001, O_EXCL/no overwrite. Через приватный SSH pipe получен только ciphertext в новый `C:/Users/krolo/Documents/marketplace-recovery/beta/e2-06-key-envelope-20261002.json`, вне Git, эксклюзивной записью. Проверены regular/size/format/mode, Windows ACL только владельца/SYSTEM, локальный read-back и повторное побайтовое равенство серверу в памяти. С тем же паролем из файла опубликованный verifier успешно расшифровал копию в памяти и проверил формат Fernet key. Plaintext key не записан на диск, не скачан с сервера и не показан; значения/salt/ciphertext/fingerprints не попали в протокол. Локальная расшифровка — автоматическая по новому разрешению, не успешный ручной TTY-тест.

Основная beta и оба остановленных rehearsal совпали по metadata до/после; основной web остаётся14d9f48. Статические metadata исходного key/старого S2 envelope/passphrase неизменны, старые копии сохранены. Одноразовые контейнеры завершены с --rm; web/БД/миграции/роли/сессии не менялись. Основной key был прочитан только разрешённым процессом упаковки, восстановленная копия — только локальным verifier в памяти. Не создавались новый runtime key или реальный owner emergency proof.

K1/K2 закрыты. **K3 ещё не выполнен:** Олег самостоятельно сохраняет оба файла в Telegram согласно принятому решению, затем скачивает их обратно под новыми именами в закрытую папку для проверки. Агент ничего в Telegram не отправлял. Факт успешной локальной расшифровки не выдаётся за проверенное хранение/обратное получение из Telegram. E2-06 остаётся «На проверке» из-за K3 и экспортных зависимостей; R2 PASS сохранён. Нового разрешения на уже выполненные K1/K2 не требуется; новые серверные действия/реальные owner proofs остаются отдельным объёмом.

Безопасный откат: runtime не менялся. Сохранить оба новых файла и прежние S2 копии; password теперь используется созданным envelope, его нельзя удалять как неиспользуемый. Не повторять wrap/автоматический launcher на занятых путях, не регенерировать key/пароль и не перезаписывать ciphertext. Удаление копий — только по отдельному решению владельца после проверки восстановимости и точных путей. Локальные протоколы откатывать только обратным diff с сохранением поздних изменений; журнал дополнять. Конкретные новые файлы пригодны для ручной передачи владельцем, не для коммита.
