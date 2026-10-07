# E2-09 R1 — остановленный изолированный прогон

**E2-09 не подтверждена.** Разрешение Олега относилось только к изолированному
плану docs/E2-09_SERVER_PLAN.md. Основная beta не обновлялась. R1 не повторялся.

## Исходники, время и фактический результат

- Live beta: `8835e1669567dce019258ec08bd416d06684cdea`.
- Source: `faed9681ff4540cb49bc46f147c738e516b6dc2e`, получен сервером только
  через Git fetch и новый detached worktree; source не редактировался.
- Начало локальной проверки: 2026-10-07T15:03:45+03:00 (12:03:45Z).
- Preflight сервера12:04:14Z: clean repository, отсутствие новых имён/release/root,
  свободно5998288896 bytes диска, MemAvailable4635952KiB.
- Новый source готов12:04:56Z; prepare создал только новые synthetic files/keys
  и baseline metadata, без просмотра содержимого старых ключей/БД.
- Compose config exit0 —12:06:01Z; postgres started —12:06:08Z;
  bootstrap exit0 и controller started —12:06:13Z.
- Fresh configure exit0 —12:06:51Z: миграции применились, явная ACL-дельта и
  financial_web_contract прошли проверку. Это не upgrade сохранённой основной
  БД и не доказательство работы всех SQL-функций под настоящим web LOGIN.
- Новая test_mw_beta создана12:07:28Z; suite started12:07:53Z.
- PostgreSQL17.11 (Debian17.11-1.pgdg12+2). В12:08:59Z основной runtime и прежние
  стенды совпали с baseline, OOM нет. Новые postgres71.34MiB/384MiB и controller
  118.7MiB/256MiB, CPU15.23%/24.59%, pids8/4: в заданных контейнерных лимитах.

## Причина остановки и границы вывода

Дополнительная read-only проверка соединений была составлена неверно: сравнивала
current_setting(statement_timeout/lock_timeout) с ровно15s/5s из конфигурации PG.
Однако backend/config/settings.py:18 уже задаёт для Django-сессий более строгие
5000ms/2000ms. Такое соединение закономерно не удовлетворяет этому сравнению,
хотя верхние пределы не нарушает. Проверка вернула exit1; значений/сырого исключения
она не сохранила, поэтому фактический снимок количества соединений отсутствует.
Ошибка относится к моей диагностике, а не обосновывает увеличение таймаутов.

По правилу первой ошибки был отправлен stop только двух новых контейнеров.
Команда docker stop с двумя именами останавливает их параллельно: PG завершился
раньше controller. Следовательно, итоговая ошибка suite во время этой остановки
не позволяет самостоятельно заключить, что финансовая авторизация неисправна,
или что её проверка прошла. Повторного запуска/обхода failfast не было.

Сохранённые безопасные события:

- `ERROR`: FinancialHTTPTests.test_scope_intersection_and_same_actor_two_organizations;
  стек указывает на setUp → legacy fixture → login/start_login/post.
- `Ran 20 tests in 210.89s`; unittest_failed.
- suite_finished: complete=true, exit_code=1, passed_without_skips=false,
  elapsed_seconds223; SSH stage end12:11:43Z.
- Сырой traceback/SQL/персональные данные/секреты не сохранялись; точная DB-причина
  ошибки теста не доказана. 20 начатых/учтённых тестов не выдаются за20 PASS.
- PG stopped12:11:40.736837088Z; controller stopped12:11:55.478633792Z; OOM=false.

## Сохранённые ресурсы и неизменность основной beta

Project/cluster `marketplace-e209-20261007-01a115d9-r1`.
Root `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-09-20261007-01a115d9-r1`.

| Ресурс | Состояние/идентификатор |
| --- | --- |
| postgres | stopped, b854e17c3f2d5e6e30e3e52db9866e3a997472d5bb16ac2afd87c924666071ac |
| controller | stopped, 5eaa92c9966790b92e5c7e8ee24db5384286b5e0f8c96a660f407ef191267926 |
| web | не создан |
| private network | internal, 5d56b3d46dcd0e7f19337e501f665330b73d818ac8326ea3936739362452ad3c |
| volume | marketplace-e209-20261007-01a115d9-r1-data, сохранён |
| БД | mw_beta и test_mw_beta нового кластера, не удалялись |
| dump/restore | financial-after.dump и restore-БД не создавались |

Сохранены новый release, семь новых secret-файлов, state/manifest.json,
state/suite-events.jsonl, baseline.json, preserved-rehearsal.json, каталоги
backups/operator-output. Содержимое ключей/паролей не читалось в терминал.
Чтение очищенного suite-events от adm_user было запрещено режимом0600/UID10001;
финальная read-only проверка прочитала только разрешённые события через sudo,
не меняя прав и не открывая secret-файлы.

Финальная metadata-проверка12:14:46Z подтвердила: основная beta running,
прежние IDs/images/StartedAt/mounts/networks/ports совпали; все сохранённые
E2-06/E2-07/E2-08 стенды не изменились. Main web остаётся на read-only source
`409c71f65db53873183c6ffd8d059561c05185d2`. Старые БД/ключи/restore не проверялись
и не менялись. Это проверка metadata, не новые функциональные тесты основной beta.

## Что осталось и локальная подготовка R2

Не выполнены: полный PG suite E2-09, upgrade/retention и конкурентные тесты,
real web LOGIN + финансовые SQL/HTTP сценарии, Gunicorn smoke, backup/restore/
quarantine. Cache/worker/storage/готовый экспорт по-прежнему отсутствуют.
E2-09, E2-06 и E2-08 остаются «На проверке».

Локально добавлен guard-проверяемый tools.financial_runtime_limits: положительные
таймауты <= пределам принимаются, unlimited/превышения/неполный контекст запрещены;
выводятся только числа параметров и количество клиентов. Подготовлен новый R2,
сохраняющий R1 stopped. Проверка лимитов перенесена до suite, остановка — сначала
web/controller, затем postgres. Штатные Django5s/2s и финансовая защита не изменены.
Девять локальных preparation-тестов PASS,0.795s; это не PostgreSQL R2.

Новый точный план: docs/E2-09_R2_SERVER_PLAN.md. Олег должен опубликовать его
source/pin и отдельно разрешить R2. Разрешение R1 не переносится на повторный
стенд. Основная beta — ещё один самостоятельный план и разрешение после успеха.
Удаление/очистка или повторное использование R1 не разрешены.
