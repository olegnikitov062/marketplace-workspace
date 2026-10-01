# E2-03 — проверенный запуск технической основы

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

