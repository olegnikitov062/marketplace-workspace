# E2-05 — жизненный цикл личного аккаунта

01.10.2026, Europe/Moscow (UTC+3). Единственный статус задачи — SYSTEM_PLAN.md. Реализовано локально в ветке beta; серверные действия в этом задании запрещены. PostgreSQL/runtime/dump-restore E2-05 ещё не проверены.

## Основание и предварительные правила

Принятый D1, SYSTEM_ARCHITECTURE.md §5: личный логин/пароль Django, одноразовые приглашения с hash, серверная сессия/CSRF, восстановление без реальной доставки, блокировка, ограничение попыток. Модель владения E2-04 и её миграции не изменены. `ownership.User.username` остаётся логином (с учётом штатной Unicode-нормализации Django и чувствительности к регистру); email не становится логином.

Олег в текущем задании подтвердил **как предварительные тестовые правила**, а не окончательные бизнес-решения: приглашение 24 часа, восстановление 30 минут, повторное приглашение только неактивированному аккаунту с той же организацией/ролью, глобальная блокировка только доверенной операторской операцией, без разблокировки через приглашение. Остальные предложения конфигурации: сессия 8 часов, окно попыток 15 минут, 5 попыток на логин/операцию и 30 на сетевого отправителя/операцию. Все значения собраны в `backend/accounts/policy.py`, не считаются принятыми production SLA/политиками.

Минимальная зависимость от E2-06 была явно обозначена до реализации: штатная серверная сессия Django необходима для входа, отказ по актуальному `is_active` и смена password hash необходимы для блокировки. Реализованы только вход, выход и технический ответ authenticated/401. Нет инвентаря/выборочного отзыва сессий, TOTP, восстановления второго фактора, экспортных ссылок, UI, worker, RBAC/Grant/RLS. E2-06 не отмечена выполненной.

Дополнительные консервативные ограничения E2-05, не матрица D3:

- Приглашает только действующий owner указанной организации; suspended/archived/чужое членство не подходит. Выдаётся только observer/cabinet_user. Приглашение нового owner, правила последнего владельца и изменение уже выданных прав отложены до отдельного решения.
- Первичное приглашение создаёт новый User с непригодным паролем и одно членство. Добавить существующего пользователя в другую организацию этим API нельзя; существующие многоорганизационные пользователи E2-04 сохраняются без изменений.
- Pending User технически имеет `is_active=True`, Membership — `active`; вход закрывают непригодный пароль и проверка отсутствия `activated_at`. Это не блокировка. Принятие устанавливает пароль/activated_at, но не меняет членство, роль или организацию и не создаёт сессию автоматически.
- Блокировка глобальная, потому что User общий для организаций. Tenant owner не получает HTTP-операции глобальной блокировки другого пользователя. Операторская `block_personal_account <UUID>` явно блокирует аккаунт во всех организациях; данные/членства сохраняются. Установлены `is_active=False` и новый непригодный пароль, отозваны неиспользованные приглашения. Это безвозвратно лишает силы старый пароль, session hash и reset token, даже если позднее кто-то изменит только is_active. Разблокировка/новое удостоверение личности не реализованы.
- Старые User без нового AccountContact автоматически не приобретают контакт или восстановление. Тестовые владельцы создаются fixtures; endpoint саморегистрации/публичного bootstrap отсутствует.

## Модель и операции

`accounts.AccountContact`: OneToOne к User, уникальный нормализованный email только `example.invalid`, activated_at. Контакт отделён от владения и неизменяем в E2-05. Реальные адреса запрещены в сервисе и CHECK БД.

`accounts.Invitation`: UUID, единственный FK к Membership, SHA-256 случайного 256-bit токена, срок, created/used/revoked и отпечаток `membership/user/organization/role`. Отдельного FK к чужой организации нет. При принятии и повторе живое членство сравнивается с отпечатком; смена пользователя, организации или роли, добавленное второе членство, блокировка, suspension или архив приводят к отказу. Нет роли или organization из тела запроса принятия.

Повторное приглашение допускается для ещё открытого (в том числе истёкшего) приглашения pending-аккаунта: старое получает revoked_at, новое получает новый hash и срок, в одной транзакции и с тем же членством. Повтор старого запроса, использованный или явно отозванный объект отклоняется. Явный отзыв не восстанавливается этим API. Уникальный частичный индекс допускает лишь одно открытое приглашение на членство; истёкшее считается открытым до явного отзыва/повтора. PostgreSQL-триггеры запрещают перепривязку/изменение hash/срока/области и снятие terminal state, изменение контакта/снятие activation. SQLite не доказывает эти триггеры.

Принятие/повтор/отзыв: транзакция, блокировки organization → users по UUID → membership → invitation/contact. Восстановление, вход и блокировка сериализуются на User. Штатные `AuthenticationForm`, `SetPasswordForm`, `login/logout`, PBKDF2 и `PasswordResetTokenGenerator` Django. Восстановление доступно только активному, неархивному, уже активированному аккаунту с пригодным паролем и контактом. Запрос всегда отвечает 202 одинаковым телом для существующего/отсутствующего/pending/blocked аккаунта; только доступному аккаунту создаётся locmem-сообщение. Не обещается постоянное время ответа. Reset token истекает по штатному правилу Django (отказ при возрасте > timeout); после успешной смены пароля все прежние reset tokens/session hashes недействительны. Повторная заявка на восстановление сама по себе не отзывает предыдущий reset token, а запросы в одну секунду могут дать одинаковый токен Django.

`AttemptBucket`: атомарный счётчик в общей БД, ключ HMAC логина или REMOTE_ADDR с отдельной областью операции, без сырых значений. Проверяется до выполнения HTTP-операции, ограничиваются в том числе успешные попытки. X-Forwarded-For не доверяем; до публикации надо отдельно проверить фактический peer/proxy и разумные лимиты. `AuthDenial` содержит только категорию отказа и время. Полноценный аудит/ретенция/автоочистка не реализованы. CSRF/метод проверяет Django; CSRF-отказы остаются в штатном техническом журнале. Сервисные функции предназначены для доверенного кода; публичный вход идёт через views с лимитами.

Доставка принудительно `django.core.mail.backends.locmem.EmailBackend`, только `example.invalid`. Даже подмена EMAIL_BACKEND на SMTP вызывает отказ до создания SMTP-соединения и откат приглашения. Тело сообщения — JSON для тестового приёмника, без HTTP-ссылки/Host. Сырые токены доступны только в памяти получателя; в ответах API их нет. Locmem не долговечная очередь и не гарантирует доставку между процессами — это тестовый механизм этапов 2–5. Пароли, тела запросов, токены, сообщения и адреса не печатать, не сохранять в протоколы и не выгружать outbox.

## HTTP-контракт без UI

Все изменяющие запросы — POST `application/x-www-form-urlencoded`, точный набор полей без дубликатов; пустые операции допускают пустое тело. CSRF обязателен также до входа. HTTPS same-origin, host-only Secure/HttpOnly/SameSite=Lax session cookie, Cache-Control no-store. Токены только в POST body, не в URL/query/path.

| Путь | Поля / ответ |
| --- | --- |
| GET `/auth/csrf` | CSRF token и cookie, только для подготовки запроса |
| POST `/auth/login` | username, password; 200 либо общий отказ 401 |
| POST `/auth/logout` | пусто; штатный flush текущей сессии |
| GET `/auth/session` | только authenticated, 200/401; без личности и прав |
| POST `/auth/invitations` | organization_id, username, email, role; owner; ответ только invitation_id |
| POST `/auth/invitations/<UUID>/reinvite` | пусто; owner исходной организации; новый invitation_id |
| POST `/auth/invitations/<UUID>/revoke` | пусто; owner исходной организации |
| POST `/auth/invitations/accept` | token, new_password1, new_password2; без автоматического входа |
| POST `/auth/recovery/request` | username; одинаковый 202 |
| POST `/auth/recovery/confirm` | user_id, token, new_password1, new_password2 |

Нет `/auth/register`, `/auth/block`, `/auth/unblock`, `/auth/totp` или admin. Ошибки payload/токена — общий 400, недостаточные полномочия — 403, лимит — 429. Без CSRF — 403; GET на изменяющий маршрут — 405. Проверка готовности теперь требует ownership 0002, accounts 0002, sessions 0001 и contenttypes 0002, а не только старую contenttypes.

## Выполненные локальные проверки

Существующий venv: Python 3.14.7, Django 5.2.17; ничего не установлено. Docker/psql в PATH отсутствуют. Исходное дерево чистое, beta `2cfec7e`; read-only `git ls-remote origin refs/heads/beta` подтвердил опубликованную `e077a7a5aed263b50d1212176806220a7ca4f971`, то есть `2cfec7e` ещё не опубликован на момент проверки. Main до работы: `a0463985eea5b02c1c5f1878e261b8422c1a4662`.

```powershell
backend/.venv/Scripts/python.exe backend/manage.py test tests --settings=config.accounts_local_checks --verbosity=1
backend/.venv/Scripts/python.exe backend/manage.py check --settings=config.accounts_local_checks
backend/.venv/Scripts/python.exe backend/manage.py makemigrations --check --dry-run --settings=config.accounts_local_checks
backend/.venv/Scripts/python.exe -m pip check
git -c core.whitespace=cr-at-eol diff --check
```

Offline settings разрешает только test/check/makemigrations/sqlmigrate, использует SQLite `:memory:` без runtime config/secrets и не запускает сервер. 63 теста: 51 успешно, 12 пропущены (8 новых PostgreSQL concurrency/trigger, 3 E2-04 PostgreSQL, 1 runtime роли/БД). Включены допустимые/истёкшие/использованные/отозванные приглашения; замена токена; правильный/неправильный пароль; блокировка существующих сессий; recovery одноразовость/срок/блокировка; две организации/запрет расширения; CSRF anonymous/authenticated и чужой Origin; locmem/no SMTP; ограничения попыток; миграции accounts reverse/forward и zero/forward пустых собственных таблиц с сохранением ownership. Система/дрейф/зависимости и синтаксис проверены. Подробный машинный протокол: `SYSTEM_ACCOUNT_CHECKS.json`.

**Не выполнены** PostgreSQL E2-05, реальная конкуренция/триггеры, PostgreSQL миграции/restore и проверка HTTP под ограниченной web-ролью. Сохранённое состояние сервера — web/главная БД E2-03 и отдельные E2-04 тестовые БД; это сведения SYSTEM_OWNERSHIP_CHECKS.json от 01.10, не новая SSH-проверка. Локальные файлы не означают обновления работающей beta.

## План beta-проверок — только после отдельного разрешения

### A. Получение исходников и изолированные PostgreSQL-тесты

1. Олег проверяет локальные коммиты и сам публикует beta. Зафиксировать полный SHA последнего проверяемого коммита, проверить `git ls-remote` и совпадение. Push агента запрещён.
2. После разрешения серверного чтения проверить **только** `/home/adm_user/marketplace-workspace/beta/app/repository`: canonical path, чистоту Git, origin, ветку и HEAD; текущие ID/image/StartedAt web и health, наличие test PostgreSQL. Не печатать полные inspect/config/env, секреты или логи. Сохранить как протокол только метаданные. Если дерево грязное, remote/ветка не совпали или изменились пути/сервисы — остановить этот шаг.
3. После разрешения обновления Git: `git -C /home/adm_user/marketplace-workspace/beta/app/repository pull --ff-only origin beta`, затем `rev-parse HEAD` и `diff --quiet`; HEAD обязан равняться выбранному SHA. Никаких архивов/ручных server source правок. Старые app/backend/frontend/deploy не заменять.
4. Сверить SHA-256 `repository/backend/requirements.lock` с текущим `app/backend/requirements.lock` (исходный lock E2-03) и проверенный image ID. Использовать существующий образ `marketplace-workspace/backend:e2-03-0210f27a7ab1` только если ID равен `sha256:eade0170f4aaf5984fc22664d479f30bfc8dac085c9d31b78e70190aeb810e4b` и lock совпадает. Новую offline build не запускать: прежняя не имела pip cache. При несовпадении остановиться, не скачивать/устанавливать компоненты.
5. Убедиться, что нет `test_mw_beta_test` и параллельного test-runner. Запустить ниже свежую тестовую БД. Скрипт `check_accounts_postgresql` требует точный guarded beta/test runtime, заранее отклоняет существующую test DB и считает любой skipped тест ошибкой. `interactive=True` сохраняет Django-защиту от удаления занятой БД при гонке; stdin закрыт, поэтому на неожиданном запросе запуск должен завершиться, а не соглашаться удалить.

```sh
cd /home/adm_user/marketplace-workspace/beta
export BACKEND_IMAGE=marketplace-workspace/backend:e2-03-0210f27a7ab1
dc() { docker compose --project-name marketplace-beta --env-file /dev/null --project-directory /home/adm_user/marketplace-workspace/beta/deploy -f /home/adm_user/marketplace-workspace/beta/deploy/compose.json "$@"; }
dc run --rm --no-deps -T -v /home/adm_user/marketplace-workspace/beta/app/repository/backend:/workspace:ro test python -m tools.check_accounts_postgresql </dev/null
dc run --rm --no-deps -T -v /home/adm_user/marketplace-workspace/beta/app/repository/backend:/workspace:ro test python manage.py check
dc run --rm --no-deps -T -v /home/adm_user/marketplace-workspace/beta/app/repository/backend:/workspace:ro test python manage.py makemigrations --check --dry-run
```

Ожидание: все 63 tests без skips, новая Django test DB удалена штатным teardown; одноразовые контейнеры удалены. Проверить PostgreSQL version, неизменность ID/image/StartedAt работающего web и отсутствие новых миграций в главной mw_beta. Это **не деплой web** и не проверка его DML grants.

### B. Новый синтетический dump/restore

Отдельно разрешить создание **только** `mw_beta_test_e2_05_recovery` и `mw_beta_test_e2_05_restore` в `postgres-test`, owner `mw_beta_test_runner`, и новый dump в `beta/backups/test/`. Seed отклоняет наличие любого из двух имён; прежние E2-03/E2-04 БД и dump сохраняются. При частичном seed не удалять/повторять автоматически. Скрипт не читает реальные источники, не выводит строки/письма/пароли. Параметры подключения потребляются внутри своего контейнера из существующих файлов, не экспортируются с сервера.

```sh
# dc и BACKEND_IMAGE — из проверенного шага A, тот же SHA Git.
dc run --rm --no-deps -T -v /home/adm_user/marketplace-workspace/beta/app/repository/backend:/workspace:ro test python -m tools.verify_account_recovery seed
dc exec -T postgres-test sh -eu -c '
  umask 077
  export PGPASSWORD="$(cat /run/secrets/db_test_bootstrap_password)"
  recovery_dump="/backups/e2-05-$(date -u +%Y%m%dT%H%M%SZ).dump"
  set -C
  pg_dump -U mw_beta_test_bootstrap -d mw_beta_test_e2_05_recovery --format=custom > "$recovery_dump"
  pg_restore -U mw_beta_test_bootstrap -d mw_beta_test_e2_05_restore --exit-on-error "$recovery_dump"
  sha256sum "$recovery_dump"
'
dc run --rm --no-deps -T -v /home/adm_user/marketplace-workspace/beta/app/repository/backend:/workspace:ro test python -m tools.verify_account_recovery verify
```

Перед запуском restore убедиться, что целевая БД создана именно этим seed и пуста. Dump сохраняет только синтетические строки и хеши; активные session cookies и сырые invitation/reset tokens в seed не сохраняются. Проверить равенство всех ownership/accounts/session-строк и migration records в памяти; две организации, pending/active/blocked/revoked; повтор/принятие, Django login/reset/block и SQL-отказы перепривязки/изменения контакта/возврата отозванного токена. Поведенческие проверки идут внутри rollback-транзакций: сохранённые source/restore snapshots остаются равны. Вывести только результат и SHA-256 dump. БД и dump не удалять автоматически.

### C. Работающий web — отдельная операция, не часть разрешения A/B

Текущий `mw_beta_web` имеет только SELECT; вход требует DML для User.last_login/password, django_session, accounts counters/audit/invitations/contact и создания приглашённых User/Membership. SELECT-тесты E2-04 это не доказывают. До реального обновления web отдельно подготовить и проверить точные минимальные GRANT/column privileges (row locks также требуют UPDATE privilege), отрицательные проверки изменения роли/чужих таблиц/DDL/admin/system DB, и HTTP smoke под этой ролью в отдельной одноразовой тестовой БД. Это SQL-привилегии процесса, не прикладной RBAC/RLS. Текущий bootstrap_roles не перезапускать для выдачи прав.

Затем отдельно разрешаются: закрытый backup главной mw_beta с проверкой восстановления в новой БД, `migrate --plan`/`sqlmigrate accounts 0001/0002`/sessions, применение основной схемы, минимальные grants и замена только beta web проверенной Git-сборкой. Новая сборка/зависимости при отсутствии cache потребуют отдельного решения. Работающий web не должен получать тестовую роль/CREATEDB/bootstrap-секреты или запускаться как migrator. Caddy, production и публичный маршрут не входят в A/B/C. До подготовки конкретного SQL/образа/backup и отдельного разрешения C не исполнять.

## Откат и сохранение работы

До правок исходные копии шести существующих файлов сохранены с относительными путями в `.change-backups/2026-10-01/E2-05-local/`: backend/config/settings.py, backend/config/urls.py, backend/tests/test_runtime.py, SYSTEM_PLAN.md, docs/RUNBOOK.md, CHANGELOG.md. `manifest.json` там содержит исходные/итоговые hashes и точный список новых файлов. Сначала сравнить текущие hashes/поздние правки, затем применить только обратный diff E2-05; цельные копии возвращать только без поздних изменений. CHANGELOG не сокращать, добавлять отмену. Новые файлы удалять только по манифесту, если совпали и не появились новые потребители/полезная работа; сначала убрать регистрацию accounts/URL. Не применять reset --hard/clean и удаление корня.

`accounts 0002 → 0001 → 0002` сохраняет строки, но временно снимает immutability guards; только в закрытой одноразовой тестовой БД. `accounts → zero` удаляет аккаунтные таблицы и допустимо исключительно на пустой тестовой схеме. Не откатывать заполненную схему через zero и не откатывать ownership ради аккаунтов. Для заполненной beta сохранять схему и возвращать совместимый код или восстанавливать проверенный dump в отдельную новую БД после разрешения. При возврате старого web новые маршруты отключатся; добавленные schema objects не удалять автоматически. Сервер сейчас не менялся, поэтому текущий локальный результат не требует серверного rollback.

Штатные основания Django: [auth/session/password forms](https://docs.djangoproject.com/en/5.2/topics/auth/default/), [ModelBackend и отсутствие встроенного rate limiting](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/). Поведение дополнительно проверено по установленному Django 5.2.17 и локальными тестами; это не утверждение о PostgreSQL E2-05.
