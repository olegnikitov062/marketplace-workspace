# Контракт ролей собственной PostgreSQL, без SQL/миграций

Для каждой среды mw_local / mw_beta / mw_production отдельный экземпляр и БД с тем же именем.
Роли: <prefix>_bootstrap — только первичное администрирование, секрет только у PostgreSQL; <prefix>_migrator — DDL/владелец, никогда у web/worker; <prefix>_web и <prefix>_worker — отдельные LOGIN, NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS, не владельцы таблиц, без членства в migrator/bootstrap; CONNECT только своей БД, DML только согласованных таблиц/операций. PUBLIC CONNECT/CREATE отзывается при будущей реализации. RLS/FORCE RLS и grants реализуются в соответствующих задачах.
Локальные тесты: отдельный postgres-test, mw_local_test, mw_local_test_bootstrap и mw_local_test_runner; раннер может создавать/удалять тестовую БД только в этом экземпляре, не подключается к postgres development.
Роли и секрет migrator пока только описаны; сервис миграций и SQL-init не созданы. POSTGRES_USER в шаблоне — bootstrap, не роль приложения; web/worker не заработают до создания ограниченных ролей. pg_hba будущего PostgreSQL: scram-sha-256, без trust и без широкого доступа извне; разные пароли во всех средах.

## Фактическое уточнение E2-03, 30.09.2026

Главная beta БД: mw_beta; bootstrap владеет БД, migrator владеет public schema, web имеет только необходимое чтение и не состоит в migrator. DDL и подключение web к системной БД проверены как запрещённые.

Отдельный тестовый PostgreSQL: mw_beta_test_bootstrap и mw_beta_test_runner. Test runner имеет CREATEDB и CONNECT к postgres только собственного тестового экземпляра: Django требует это для создания и удаления test database. Привилегия не переносится в главный кластер. Внешних БД и реальных данных нет. Проверены тесты и восстановление синтетического набора. Исторические шаблоны выше не являются исполняемым SQL; фактический provisioning — backend/tools/bootstrap_roles.py, проверка — backend/tools/verify_web_role.py.

