# Marketplace workspace — E2-03

React/TypeScript/Vite и Django/DRF/PostgreSQL: проверенная техническая основа, без бизнес-моделей, пользователей, worker и внешних интеграций.

Источники: backend/, frontend/. Закреплённые версии: backend/requirements.lock, frontend/package-lock.json, beta/deploy/images.lock.json. Инструкция: docs/RUNBOOK.md. Документы проекта находятся здесь: [план](SYSTEM_PLAN.md), [архитектура](SYSTEM_ARCHITECTURE.md), [обследование](SYSTEM_DISCOVERY.md), [среды](SYSTEM_ENVIRONMENTS.md), [запуск](SYSTEM_STARTUP.md), [протокол](SYSTEM_STARTUP_CHECKS.json) и [журнал](CHANGELOG.md).

Сервер: /home/adm_user/marketplace-workspace/beta/. Compose marketplace-beta, отдельные main/test PostgreSQL и internal сети. Публичных портов и HTTPS нет; Caddy не менялся. Production запрещена runtime guard. *.template.json — исторические шаблоны E2-02, действующий compose — beta/deploy/compose.json.

Git: codex/e2-03, без commits/push. Посторонние .playwright-cli/ и output/ сохранены. E2-04 не начата.
