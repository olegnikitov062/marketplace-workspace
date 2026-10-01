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
