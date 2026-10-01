# E2-03 — инструкция воспроизведения

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
