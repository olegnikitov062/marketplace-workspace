# E2-06 — сессии, MFA и восстановление владельца

01.10.2026, Europe/Moscow. Статус: **На проверке**. Код подготовлен локально в beta; основная beta не обновлялась. Подготовка и исходное обследование: [E2-06_PREPARATION.md](E2-06_PREPARATION.md). Машиночитаемый результат: [SYSTEM_SECURITY_CHECKS.json](../SYSTEM_SECURITY_CHECKS.json). Разрешения E2-05 не распространяются на этапы ниже.

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
| Копия ключа TOTP | Восстанавливает только Олег; в Telegram допустима только зашифрованная копия, пароль отдельно. Передача не выполнялась |

У добровольного пользователя без подключённого MFA повторное подтверждение требует только пароль; включение MFA не обходится этим правилом.

Технические параметры: TOTP 6 цифр/30 секунд, окно ±1 шаг, без автоматического drift; replay и задержку после ошибок ведёт django-otp. 10 случайных восстановительных кодов по 192 бита, PBKDF2-хеши Django, одноразовое использование под блокировкой строки пользователя. Лимиты попыток используют общий механизм E2-05 (БД, измерения peer/principal, новый cookie их не сбрасывает). Это параметры реализации, не расширение бизнес-ролей.

## Реализация и границы

Применены согласованные django-two-factor-auth 1.18.1, django-otp 1.7.3, cryptography 50.0.2 и шесть согласованных транзитивных пакетов; точные версии/hashes — requirements.lock. Старые pins сохранены. Wheels проверены по SHA-256 release metadata, LICENSE прочитаны, установка без дополнительных пакетов; pip check успешен. Linux image ещё не собран. Телефонные/SMS/WebAuthn методы не включены.

`account_security` использует мастер/формы django-two-factor-auth и алгоритм, replay/throttling django-otp. Адаптер Authenticator меняет хранение, не алгоритм TOTP. Штатные plaintext otp_totp/otp_static таблицы не используются и не получают DML web. Собственный реестр нужен для отзыва, ограниченной стадии входа, шифрования и одноразовых хешированных кодов. Изменений site-packages нет.

Fernet шифрует ключи Authenticator и весь payload Django sessions, включая временные данные мастера. Ключ не выводится из Django SECRET_KEY: runtime требует отдельный read-only `/run/secrets/mfa_encryption_key`. Отсутствующий/некорректный ключ останавливает startup; ошибочный ключ не даёт прочитать старые сессии/факторы. Старые E2-05 cookie не создают новую полноценную сессию. Django dumpdata для зашифрованного поля запрещён: резервирование через pg_dump сохраняет ciphertext. Ротация ключей и внешнее хранилище секретов не реализованы.

SessionGate на каждом запросе проверяет актуального пользователя, version, password hash, сроки, отзыв устройства и обязательность MFA; текущие права организации читаются сервисами E2-04/05. После получения user row lock изменение аккаунтов повторно проверяет HTTP-сессию. До подтверждения обязательного MFA допустимы только setup/QR/CSRF/выход. Старый `/auth/login` не обходит мастер. Доверие устройства — случайный HttpOnly/Secure cookie и отзываемый серверный хеш; пароль не заменяется этим cookie.

Узкие серверные страницы: `/auth/mfa/login/`, `/auth/mfa/setup/`, `/auth/security/`, повторное подтверждение, смена пароля и восстановление. Изменения — POST с CSRF. Секреты показываются только самому пользователю в защищённом ответе, восстановительные коды — один раз; auth-ответы no-store/no-referrer. Журнал содержит категории и внутренний user ID без введённых значений/IP/User-Agent/токенов. Gunicorn access log выключен. Не снимать QR/коды/ответы через скриншоты или подробные HTTP-логи.

| Критерий | Реальный минимальный механизм | Что остаётся |
| --- | --- | --- |
| Немедленная смена прав | Живое Membership + повторная проверка E2-05 owner-действия; демоция запрещает настоящее приглашение в той же сессии | Полная матрица RBAC/Grant — E2-07 |
| Изоляция | Проверка чужой организации в настоящем приглашении и выдаче/чтении синтетического скачивания | RLS и полная предметная изоляция — E2-08 |
| Отзыв старой ссылки | ExportPermit привязан к пользователю, организации и конкретной сессии; HTTP действительно отдаёт фиксированный синтетический CSV и затем отказывает. DB trigger безвозвратно отзывает permit при смене роли/state/archive; возврат роли ссылку не оживляет | Рабочие экспорты/файлы/разрешения E5-07 и RBAC отсутствуют; полный критерий E2-06 остаётся на проверке |
| Потеря фактора владельцем | Одноразовый код или отдельное операторское разрешение дают только ограниченную сессию, без изменения Membership/организаций/блокировки | Проверка operator CLI с реальным разделением ролей и PostgreSQL ещё не выполнена |

Синтетический download закрыт по умолчанию (`SECURITY_DOWNLOAD_PROBE=False`), включается только внутри тестов; публичного HTTP выпуска ссылок нет. Это действующий механизм отзыва и HTTP-проверка, не бизнес-экспорт. E2-07/E2-08/E5-07 не объявляются реализованными.

## SQL и миграции

Добавлены account_security 0001_initial/0002_revocation_guards и необходимые миграции приложений библиотеки. 0002 устанавливает SECURITY INVOKER guards: неизменяемая идентичность записей, монотонная version/last_t, невозможность снять использованность/отзыв; триггеры смены password/is_active/archive и Membership/Organization. Прямой SQL не оживляет отозванное состояние. PostgreSQL-ветвь ещё не исполнялась; SQLite не доказывает её корректность.

Точный список таблиц/колонок — `backend/tools/security_web_grants.py` (SECURITY_INSERT/SECURITY_UPDATE/SECURITY_READ). Web получает INSERT только в реестр/факторы/коды/синтетические permits/журнал и UPDATE только изменяемых полей. Нет INSERT RecoveryPermit, UPDATE ключа/пользователя/уровня сессии, UPDATE/DELETE журнала, новых DELETE, DDL, членства ролей, BYPASSRLS, прав оператора/мигратора. Существующий E2-05 SELECT/default SELECT сохраняется; это не изоляция данных от скомпрометированного web и не RLS.

`manage_security_web_grants plan` без подключения показывает точный delta; apply проверяет прежний E2-05 контракт и миграции, атомарно добавляет только delta, проверяет итог. Revoke допускается после выключения потребителя и удаляет только delta, сохраняя прежние ACL. Grant/revoke/reapply и 17 SQL-отказов подготовлены под настоящим ограниченным LOGIN, но пока не выполнены.

## Оператор и ключи

Команды `prepare_owner_recovery`/`issue_owner_recovery` разрешены только beta/migrate, с проверкой current_database/session_user/current_user = mw_beta/mw_beta_migrator/mw_beta_migrator. Web не получает verifier и migrator credentials. Подготовка создаёт два НОВЫХ файла: аварийный секрет Олегу и привязанный к UUID владельца PBKDF2 verifier; не печатает их. Файлы на volume `/run/recovery-output`, 0600, без перезаписи. Подготовка секрета отдельно авторизуется и не выполняется при обычной миграции.

Восстановление требует verifier read-only `/run/secrets/owner_recovery_verifier` и ввод секрета через getpass; неверный секрет/не-владелец/заблокированный аккаунт не получают разрешение. Успех отзывает сессии/доверие/ссылки, записывает 5-минутный одноразовый permit и сохраняет его только в новый закрытый файл. Олег вводит permit и свой пароль на странице operator-recovery, заново подключает TOTP, затем входит заново. Ни Codex, ни наличие SSH сами по себе не подтверждают личность. Автоматической команды «войти владельцем» нет. Доставка секрета/permit не автоматизирована и не разрешена этим документом.

Копия ключа шифруется `python -m tools.mfa_key_backup wrap --input <private-key-file> --output <NEW-private-envelope>`, восстановление — `restore` с новым выходным файлом. Scrypt с фиксированной стоимостью + Fernet; пароль через getpass, не в аргументах/ENV. Обёртка отказана на Windows до отдельной проверки приватного ACL назначения; криптографический roundtrip проверяется в памяти. Telegram здесь не подключён; Олег переносит только envelope самостоятельно после отдельной проверки копии и хранения пароля. Потеря и ключа, и копии не устраняется аварийным секретом: это разные секреты.

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
dc exec -T -e E206_DUMP="$dump_name" postgres-test sh -eu -c 'umask 077; set -C; export PGPASSWORD="$(cat /run/secrets/db_test_bootstrap_password)"; pg_dump -U mw_beta_test_bootstrap -d mw_beta_test_e2_06_recovery --format=custom > "/backups/$E206_DUMP"'
dc exec -T -e E206_DUMP="$dump_name" postgres-test sh -eu -c 'export PGPASSWORD="$(cat /run/secrets/db_test_bootstrap_password)"; exec pg_restore -U mw_beta_test_bootstrap --role=mw_beta_test_runner --no-owner --no-acl --exit-on-error -d mw_beta_test_e2_06_restore "/backups/$E206_DUMP"'
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
