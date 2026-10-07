# E2-08 — результат изолированного R1, 07.10.2026

**FAIL на configure. E2-08 остаётся «На проверке».** Прогон остановлен по
первому сбою; все созданные ресурсы сохранены. Основная beta не внедрялась.

## Допуск и исходники

Олег подтвердил публикацию, затем отдельно разрешил изолированный план.
Live `git ls-remote --heads origin beta` подтвердил
`9e6458ed9d145633e47480e12a8dcbf3be351b3f`; исходники стенда — его предок
`a1eeff72d72369c492c078fb5bd5ce91268f19cd`.
Серверный чистый beta checkout fast-forward обновлён через Git с `18e4a18…`
до опубликованной beta. Создан новый detached release точного source REV.
Код не передавался архивом/SCP и не исправлялся на сервере.

Preflight начат 07.10.2026 10:15:34 +03:00 (07:15:34Z).
Первая read-only команда `docker compose version --short` получила лишний CR
при передаче из PowerShell и exit1. До изменений повторена с удалением CR:
Python сервера 3.12.3, Docker 29.1.3, Compose 5.1.3.
Проверки публикации, коллизий, свободных RAM/диска, immutable images/lock,
основного RO source/image и остановленных прежних стендов прошли.
Backend image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`,
PostgreSQL image `sha256:248efd5e58cd743f2a0e0daec8ea4649e5580145ec2a12e2345bc710d4a77201`,
lock SHA256 `35cba592050150a0e5b1f68adc36d3f1c0871ceec79efc6c7f8e4a925fb34e60`.

## Наблюдаемый результат

| Шаг | Результат |
| --- | --- |
| prepare --apply | exit0; только новые синтетические secrets/metadata |
| Compose config и PostgreSQL start | exit0, healthy; PostgreSQL 17.11 (Debian 17.11-1.pgdg12+2) |
| bootstrap | exit0; роли/пустая private schema нового кластера |
| configure | exit1; безопасное сообщение без SQL/секретных значений |
| Каталог и граф после сбоя, только чтение | нет `django_session`; все 11 trigger functions существуют; RLS-таблиц 0; private tables 0 |
| Новая тестовая БД / suite / actual web LOGIN / HTTP | не запускались |
| dump / restore | не выполнялись |
| Сохранность main beta и трёх прежних стендов | metadata до/после совпали |
| Остановка R1 | exit0; postgres running=false, OOM=false; работающих контейнеров проекта нет |

В migration history есть прежние ownership/accounts/account_security/access_control,
contenttypes/auth миграции. `data_isolation.0001_statement_and_row_policies`
не записана. В pending graph она идёт раньше `sessions.0001_initial`.
Исходное исключение configure намеренно скрыто helper и не восстанавливалось;
текст SQL-ошибки не заявляется известным. Независимая проверка каталога/графа
доказывает блокирующий дефект: RLS применяется к ещё не созданной таблице сессий.
Успешные предшествующие миграции сохранены; повтор configure не выполнялся.

Основной runtime остался `cf6f4ccd48106d9a44a64703bcfd79e49513ec3e`:
ID/image/StartedAt/mounts/networks/ports основных контейнеров совпали с baseline.
Такие же metadata сверены для обоих E2-06 owner rehearsal и E2-07 rehearsal.
Это metadata-проверка сохранности, а не новая функциональная проверка основной beta.

## Сохранённые ресурсы

- Project: `marketplace-e208-20261006-01a1105a`.
- Root: `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-08-20261006-01a1105a`.
- PostgreSQL container ID: `14dd0ff594e2a813c39d0068c41a6df44acd36202b1a4802abad96f4807625aa`.
- StartedAt: `2026-10-07T07:16:20.634956042Z`; FinishedAt: `2026-10-07T07:18:01.338589131Z`.
- Internal network: `marketplace-e208-20261006-01a1105a-private`, ID `70ebab398222948d5dd5abf7ea60c6889af8e77cf1400a76bf7e26898f12284b`.
- Volume: `marketplace-e208-20261006-01a1105a-data`.
- Внутри нового instance: `mw_beta`, роли bootstrap/migrator/web, пустая
  `mw_isolation`, применённые предшествующие миграции.
- Сохранены новые synthetic secrets, `state/manifest.json`, `baseline.json`,
  `preserved-rehearsal.json`, каталоги operator-output/backups. Dump не создан.

Web не создавался. Временные bootstrap/controller завершались штатно с `--rm`;
постоянный controller в R1 не создавался. Не выполнялись DROP/down -v/prune,
чтение реальных ключей, K3/Telegram, установка, push, изменения Caddy/production
или иных проектов. Новые секреты использовались процессами через mounts,
их содержимое не выводилось и не переносилось в отчёт.

## Локальное исправление и следующий допуск

В RLS-миграцию добавлена явная зависимость `sessions.0001_initial`.
Новая проверка строит состояние всех migration parents и требует присутствия
всех 27 целевых таблиц. До исправления FAIL с отсутствующим `django_session`,
после — PASS. Первая черновая версия самой проверки получила TypeError
из-за передачи set вместо списка node keys; исправлена до red/green проверки.
Эта проверка графа не использует PostgreSQL и не доказывает корректность SQL.

Подготовлены новые уникальные R2 имена и guards. R1 добавлен в проверку
сохранённых остановленных стендов. В плане controller запускается через
`up -d` + `exec -T`, чтобы он существовал для итогового metadata-verifier,
который проверяет три постоянных контейнера.
Полные результаты локальных проверок — `SYSTEM_ISOLATION_CHECKS.json`.

Следующий этап: публикация исправленных локальных коммитов Олегом, live-проверка
точного REV и отдельное разрешение [плана R2](E2-08_SERVER_PLAN.md).
Первое разрешение не переносится на повторный запуск с новым кодом/ресурсами.
Основная beta требует другого плана и допуска после успешного изолированного прогона.

Безопасное состояние сейчас — новый стенд остановлен, данные и evidence сохранены.
Не исправлять существующую БД повторным configure, не отключать RLS/Grant/MFA
и не возвращать приложение, обходящее защиту. Старые ресурсы не удалять.
E2-06 остаётся «На проверке» без новых оснований для изменения статуса.
