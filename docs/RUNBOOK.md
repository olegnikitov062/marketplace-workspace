# Beta — текущий E2-07 и история воспроизведения

Текущее состояние после отдельно разрешённого E2-07 rollout (05.10.2026): основной web/БД обновлены, backend закреплён read-only Git worktree cf6f4ccd48106d9a44a64703bcfd79e49513ec3e, прежний MFA dependency image и secret mounts. Обычный запуск требует compose.security-web.json, SECURITY_SOURCE и SECURITY_IMAGE; команды в последнем разделе E2-07 SYSTEM_STARTUP.md. Исторические base-only/accounts overlay и обычный E2-06 ниже запрещены: они обходят MFA или Grant. Безопасный отказ — остановка только web, не автоматический rollback старого приложения.

Проверенная сборка e2-03-0210f27a7ab1. Production и внешние интеграции запрещены. Только новый проект; команды не изменяют другие Compose projects или Caddy.

## Локальные проверки Windows

Из корня проекта, при уже установленных зависимостях:

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -p test_guard.py
backend/.venv/Scripts/python.exe -m pip check
npm --prefix frontend run build
backend/.venv/Scripts/python.exe tools/package_beta.py
```

Новая установка требует отдельного согласия: Python lock устанавливать с --require-hashes --only-binary=:all:, frontend через npm ci --ignore-scripts --no-audit --no-fund. Секреты и данные в архив не включать. Локальная проверка не равна запуску PostgreSQL; Docker/WSL на ноутбуке не устанавливались.

## Разрешённый сервер

Архив передавать и распаковывать только после проверки canonical target, отсутствия чужих файлов и совпадения SHA-256. При существующих исходниках сначала сохранить копии только source/deploy, без secrets/data. Код backend/frontend находится в beta/app/, конфигурация в beta/deploy/, source-manifest.json рядом с ней. Root: /home/adm_user/marketplace-workspace/beta.

```sh
cd /home/adm_user/marketplace-workspace/beta
python3 deploy/beta.py prepare
python3 deploy/beta.py build
python3 deploy/beta.py start
python3 deploy/beta.py test
python3 deploy/beta.py status
```

prepare только для чистой среды: существующие secrets/provisioned marker отклоняются. На нынешней beta prepare повторно не выполнять. Скрипты фиксируют project marketplace-beta, роли и internal сети. start запускает main/test PostgreSQL, однократный provisioning, технические миграции contenttypes и web. Бизнес-моделей и расписаний нет.

Дополнительные проверки:

```sh
python3 deploy/reproduce.py
python3 deploy/verify_isolation.py
python3 deploy/verify_migrations.py
```

reproduce создаёт собственные временные PostgreSQL/network и удаляет только созданные ID; проверены пять tests и teardown. verify_migrations изменяет только собственную test DB, создаёт синтетическую строку, dump и restore DB; повтор при существующем dump запрещён. Сейчас dump уже существует: повтор требует отдельного набора/плана сохранения, существующий dump не удалять ради повторного запуска.

API ready проверяется внутри web, публичных портов нет. Frontend собран и сравнен с локальным dist; браузерный HTTPS не проверялся. Полный протокол: ../SYSTEM_STARTUP_CHECKS.json.

## Безопасный откат

Перед любым откатом сравнить текущие файлы/IDs/labels с манифестом и сохранить позднюю работу. Остановку только marketplace-beta отдельно согласовать; данные/secrets/dump не удалять автоматически. Не применять prune или удаление корня. Source backups — beta/.change-backups/. Локальные исходные копии и change-manifest.json — ../.change-backups/2026-09-30/E2-03-20260930-153934/. Посторонние output/ и .playwright-cli/ сохранить.


## E2-04 — локальная модель владения

Модель и миграции добавлены только в локальные backend-исходники. Запущенная beta и прежний протокол E2-03 не подтверждают E2-04. Локальные команды, границы и отдельно разрешаемая последовательность PostgreSQL/beta/restore: [E2-04_OWNERSHIP.md](E2-04_OWNERSHIP.md). Результаты: [SYSTEM_OWNERSHIP_CHECKS.json](../SYSTEM_OWNERSHIP_CHECKS.json). Старые start/prepare/verify_migrations не запускать для этой задачи автоматически; существующие копии и тестовую restore БД сохранять.


## E2-04 — подтверждение PostgreSQL, 01.10.2026

В изолированном postgres-test beta прошли 17 tests без пропусков, reverse/forward миграций, конкуренция, синтетический dump/restore и проверки ограничений восстановленной БД. Использована чистая Git-копия опубликованной beta e077a7a в beta/app/repository; существующий образ E2-03 с теми же зависимостями, новая source-папка подключена read-only к одноразовым контейнерам. Предыдущий раздел описывает состояние до этих проверок. Основная mw_beta и работающий web не обновлены; новый image offline не собрался, зависимости не устанавливались. Детали/точные команды: [E2-04_OWNERSHIP.md](E2-04_OWNERSHIP.md), фактический протокол: [SYSTEM_OWNERSHIP_CHECKS.json](../SYSTEM_OWNERSHIP_CHECKS.json). Сервер получает дальнейшие source-изменения только через Git после push Олега, не архивами/ручными правками.


## E2-05 — локальный жизненный цикл аккаунта, без обновления сервера

Исходники, предварительные правила, HTTP-контракт и полный порядок A/B PostgreSQL/restore: [E2-05_ACCOUNTS.md](E2-05_ACCOUNTS.md). Протокол: [SYSTEM_ACCOUNT_CHECKS.json](../SYSTEM_ACCOUNT_CHECKS.json). Локально используется `config.accounts_local_checks` (SQLite только test/check); это не PostgreSQL/runtime доказательство. D1 и ownership E2-04 сохранены; E2-06 не выполнена.

Серверные действия текущим заданием не разрешены. После проверки локальных коммитов push выполняет Олег; сервер получает только опубликованную beta через проверенный Git pull --ff-only. Архивный порядок E2-03 выше не применять для E2-05. Не запускать prepare/start/bootstrap/старые destructive recovery probes. Новые probes E2-05 используют свои БД и отказываются при занятых именах; исходники read-only из Git, образ E2-03 только после сверки ID/lock. Работающий web/главная mw_beta остаются на исходной версии, их новая live-проверка не выполнялась.

Текущая web-роль SELECT-only недостаточна для сессий/аккаунтов. Проверка под test_runner не доказывает её работоспособность; минимальные DML/column grants, отдельный web-role HTTP smoke, backup главной БД, миграции и замена web требуют своего конкретного плана и разрешения. Caddy/production/публичный маршрут/другие проекты не входят в объём.


## E2-05 — PostgreSQL A/B выполнены 01.10.2026

По отдельному разрешению Олега сервер получил опубликованную beta 342192b через Git pull --ff-only. 63 PostgreSQL-теста без skips, check/drift и синтетический dump/restore прошли. Существующий image E2-03, Git source read-only, только test-private. Сохранены БД mw_beta_test_e2_05_recovery/mw_beta_test_e2_05_restore и новый dump e2-05-20261001T083919Z.dump; seed повторно не запускать. Равенство данных/миграций и поведение восстановления подтверждены; старые dumps неизменны. Подробности/hashes: [SYSTEM_ACCOUNT_CHECKS.json](../SYSTEM_ACCOUNT_CHECKS.json), [E2-05_ACCOUNTS.md](E2-05_ACCOUNTS.md).

Предыдущий раздел описывает состояние до разрешения A/B. Главная mw_beta и работающий web не обновлены, metadata/migrations/health проверены до/после. E2-05 остаётся на проверке из-за непроверенного lifecycle под ограниченной web-ролью. Пункт C, grants/основные миграции/web restart, Caddy/production и следующие задачи не разрешены и не выполнены.


## 2026-10-01T12:14:52+03:00 — E2-05: подготовка ограниченной web-роли

Исполняемый список DML/column grants и защитных row-lock triggers: `backend/tools/account_web_grants.py`; guarded `tools.manage_account_web_grants` по умолчанию только печатает план без подключения. [E2-05_WEB_ROLE.md](E2-05_WEB_ROLE.md) задаёт C1/C2, точные команды, предусловия и откат. C1 после push и отдельного разрешения создаёт только `mw_beta_test_e2_05_web` (БД/роль), проверяет HTTP lifecycle под настоящей ограниченной LOGIN-ролью, revoke/reapply и SQL-отказы, сохраняет БД и отключённую роль. Главная beta/web не входят в C1.

C2 — отдельное разрешение после C1 той же ревизии: новый основной dump и проверка restore, detached Git worktree, main migration/grant, пересоздание только web с read-only source mount существующего образа. Не использовать общий up/build/prune, не передавать исходники архивом и не менять server source вручную. Сейчас C1/C2 не выполнены; локальные 55 успешных тестов и 12 PostgreSQL-пропусков не подтверждают новый SQL-контракт. Состояние: SYSTEM_ACCOUNT_CHECKS.json; прежние результаты A/B сохраняются.


## 2026-10-01T13:37:23+03:00 — C1 _v2 успешно выполнен

Подробный протокол: [E2-05_WEB_ROLE.md, раздел 7](E2-05_WEB_ROLE.md). На опубликованной 82b2004, PostgreSQL 17.11, отдельный C1 завершился PASS: настоящий ограниченный LOGIN, exact DML/guards, grant/revoke/reapply, HTTP lifecycle/CSRF и 13 SQL-отказов. Runtime source mount read-only/test-private подтверждён. БД/роль mw_beta_test_e2_05_web_v2 сохранены, роль NOLOGIN/PASSWORD NULL, контейнер удалён; первая попытка сохранена. Оба имени заняты, probe повторно не запускать.

Главная beta/contenttypes:2, web/два PostgreSQL контейнера неизменны, readiness 200. C2 ещё не разрешён/не выполнен: требуются новый main backup/restore, main migrations/grants, фиксированный Git worktree 82b2004 и обновление только web с runtime smoke. Точные команды/откат в E2-05_WEB_ROLE.md §3/4. E2-05 остаётся «На проверке» до основной beta-проверки; A/B 63 PostgreSQL-теста и C1 — разные проверки, полный набор 68 в этом запуске не повторялся.


## E2-05 завершена / C2 — 2026-10-01T13:55:12+03:00

После отдельного разрешения C2 опубликованный Git backend 82b200465e15b447a43ed3d36d4522f11742bee1 развёрнут read-only worktree поверх прежнего E2-03 image. Новый main dump и ACL snapshot mode 0600, restore/fingerprints в новой mw_beta_test_e2_05_main_before успешны; 17 новых миграций и точные main web grants/guards применены. Пересоздан только web; C2 runtime/SQL smoke PASS (live/ready 200, anonymous session 401, login GET 405), PostgreSQL контейнеры прежние. Основные account/ownership записи пока отсутствуют, SMTP/источники/порты не включались. Main TEMPORARY=true осталось исходным, C1 temp denial не переносится на него как доказательство.

[Протокол C2, hashes и откат](E2-05_WEB_ROLE.md) — раздел 8/4; текущие команды запуска — [SYSTEM_STARTUP.md](../SYSTEM_STARTUP.md), актуальные факты — SYSTEM_ACCOUNT_CHECKS.json/c2. Base-only web up возвращает E2-03 source; текущий web требует overlay и fixed ACCOUNTS_SOURCE. Имена всех C1/restore БД заняты, probes/restore-create повторно не запускать. Старые разделы выше описывают историю. E2-05 «Готово»; E2-06/UI/TLS/RBAC/worker/реальные аккаунты не входят в результат. Предварительные правила и сроки остаются предварительными.


## E2-06 — только локальная реализация (2026-10-01T15:31:57+03:00)

Серверное состояние E2-05 выше не изменено. Новый код требует отдельного ключа и нового dependency image; нельзя запускать его старым accounts overlay. Принятые правила и проверяемые этапы S0/S1/S2: [E2-06_SESSIONS_MFA.md](E2-06_SESSIONS_MFA.md); результаты: [SYSTEM_SECURITY_CHECKS.json](../SYSTEM_SECURITY_CHECKS.json). Нужны отдельные разрешения до любых SSH/сборок/БД/ролей/ключей/миграций/перезапусков. После включения MFA возврат к обычному E2-05/base-only web запрещён; безопасный fallback — проверенный deny-auth maintenance либо остановленный beta web. Полный restore требует сверки полномочий и карантина сессий/факторов, не прямого включения старого dump.


## E2-06: применён S2 — 2026-10-01T17:58:26+03:00

По явному текущему разрешению Олега основная beta обновлена до E2-06. Опубликованный протокол f4f6059 получен Git fast-forward; рабочий код закреплён на проверенном 19a6d6a, read-only. Использован существующий dependency image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72` с совпавшим lock; новых установок/сборок нет. Новый dump `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-before-20261001T144009Z.dump` (0600, 75491 bytes), соседние `.acl.json`/`.snapshot.json` и restore в `mw_beta_test_e2_06_main_before` сохранены. Все 18 исходных таблиц совпали; основной ACL до применения не менялся.

Отдельный beta TOTP key вне БД/Git и его парольная encrypted envelope созданы в закрытых файлах 0600/UID10001. Копия восстановлена в другой файл без mount оригинала, равенство проверено без вывода значений. Это техническое восстановление на сервере, не независимое хранение у Олега: Telegram не использован, пароль и envelope ещё не переданы владельцу. Аварийный секрет владельца не создавался.

Проверены Compose/lock/check/план и SQL; RunPython guards прочитаны в опубликованном коде (sqlmigrate их не разворачивает). Maintenance реально закрыл auth/business/ready с 503 и оставил live 200; затем применены 9 операций миграций и точный column-grant delta. В django_migrations теперь 36 записей: two_factor squash записал 8 заменённых плюс собственную, всего 17 новых записей при 9 операциях. Обновлён только web; оба PostgreSQL сохранили ID/image/StartedAt/mounts/networks/ports.

S2 runtime PASS: реальная mw_beta_web, точные ACL/guards, live/ready 200, session 401, старый login GET 405, MFA login GET 200. Chromium проверил анонимные страницы входа/восстановления, обязательные поля, CSRF 403 и no-store через временный localhost SSH-туннель; browser/tunnel закрыты. Это не полный браузерный MFA lifecycle и не публичный TLS. Оба operator CLI отклонены из web-роли; положительная процедура с отдельным секретом не выполнялась.

Финально users/organizations/memberships/authenticators/recovery permits/codes = 0; две анонимные wizard sessions зашифрованы, не являются полноценными аккаунтными сессиями. Штатные plaintext OTP таблицы пусты, locmem и выключенные внешние flags подтверждены; public synthetic export probe выключен. Все oneoff контейнеры удалены. Полный suite 63/63 без skips относится к предыдущему S1 на том же коде и в S2 повторно не запускался. E2-06 остаётся «На проверке»: полный браузерный сценарий, положительный operator CLI, фактическое хранение ключа владельцем и полный экспорт ещё не закрыты; E2-07/E2-08/E5-07 не реализованы.

Текущий запуск/maintenance-откат: [SYSTEM_STARTUP.md](../SYSTEM_STARTUP.md), последний раздел E2-06. Все старые E2-05/E2-06 probes и новая mw_beta_test_e2_06_main_before заняты; не выполнять повторное создание/seed/restore поверх них. Новых разрешений на production/Caddy/реальные учётные записи/передачу секретов эта запись не даёт.


## Текущая beta E2-06: исправлен браузерный CSRF — 2026-10-02T13:41:10+03:00

По отдельно разрешённому плану [E2-06_WEB_FIX_ROLLOUT.md](E2-06_WEB_FIX_ROLLOUT.md) пересоздан только основной web: source `14d9f48cee6eb2a9d7eca9f029770af51c45b6d9/backend` read-only, прежний image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`. SQL/runtime и Chromium same-origin/no-store/secure cookie/CSRF/Origin PASS; native POST отменён до сервера. Миграции/SQL-права/ключи сохранены, оба PostgreSQL не пересозданы. Аккаунтов и организаций в основной БД нет, encrypted anonymous Django sessions 4 → 6 от GET login. Owner rehearsal остаётся остановленным.

Metadata до переключения: `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-referrer-before-20261002T102702Z.metadata.json` (0600, no-overwrite, read-back equal). Старые S2 dump/key envelope проверены по наличию/режимам; нового dump/restore нет. Новый ID/StartedAt, обязательные environment/overlay и команды запуска/maintenance — в последнем разделе [SYSTEM_STARTUP.md](../SYSTEM_STARTUP.md); текущий протокол — SYSTEM_SECURITY_CHECKS.json/main_web_referrer_rollout. Ранние разделы описывают историю.

E2-06 «На проверке»: ограничения полного browser runner, независимое хранение ключа владельцем и рабочий экспорт остаются. Main anonymous pageerrors=0 не подтверждает счётчик прежнего полного rehearsal. Реальные owner proof/передача ключевой копии требуют отдельного конкретного разрешения. Старый baseline rehearsal сохраняется как исторический: main web изменён именно этим разрешённым этапом. Не переиспользовать занятые БД/probes/terminal fixture; не запускать обычный старый web или live restore.

## Текущая beta E2-07 — 2026-10-05T14:19:06+03:00

По отдельно разрешённому [E2-07_MAIN_ROLLOUT.md](E2-07_MAIN_ROLLOUT.md) основной web работает на read-only `cf6f4ccd48106d9a44a64703bcfd79e49513ec3e/backend`, прежнем security image и secret mounts. Свежий main dump/restore, две миграции и ограниченный SQL-переход прошли; TEMP отозван у PUBLIC/web. Реальная web LOGIN-роль, 10 SQL-отказов и 10 network anonymous health/auth/default-deny/CSRF проверок — PASS. Подтверждённое окно stop→ready9мин30с. Два PostgreSQL и все 11 сохранённых rehearsal-контейнеров неизменны. Аккаунты/организации/Grant не создавались; anonymous encrypted sessions6→7.

Текущие source/image/env/команды — в последнем разделе E2-07 [SYSTEM_STARTUP.md](../SYSTEM_STARTUP.md). Обязательны compose.security-web.json, SECURITY_SOURCE и SECURITY_IMAGE; не применять base-only/accounts overlay, обычный старый E2-06 или изолированный helper с другим cluster_name. Fallback — остановить только web; обратная схема/restore или возврат к старому коду требуют отдельного плана. Никакого обхода MFA или Grant.

Сохранены checkpoint `beta/backups/database/e2-07-main-20261005-01a10b2d` и закрытая restore-БД `mw_e207_main_restore_20261005_01a10b2d`. Эти имена заняты. Dump mode0600, SHA256 `267dcecac7a3434870f09915deee1b6950a43df672c1eedad6dea2086e006529`; сравнение30таблиц/11sequences и ACL прошло, две формы CHECK после pg_restore проверены на эквивалентность. Не удалять и не переиспользовать ресурсы, не запускать сохранённые стенды без нового допуска. Штатное потребление старых secret mounts было отдельно разрешено; секреты не выводились/не копировались, K3 не проверялся.

E2-07 технически «Готово» в согласованном синтетическом объёме; E2-06 остаётся «На проверке» с прежним ограничением рабочего экспорта и зафиксированным ограничением K3. UI/worker/RLS/финансовая фильтрация/реальные роли D3/браузерная и TLS-проверка основной E2-07 не выполнены и не объявляются частью результата. Протокол — SYSTEM_GRANT_CHECKS.json/main_rollout_result; исторические факты выше не переписывались.
