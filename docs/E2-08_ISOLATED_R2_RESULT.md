# E2-08 — результат R2, 07.10.2026

**Прогон прерван: итог PostgreSQL suite не получен из-за разрыва SSH.**
Успех всего набора, реальной web-роли и RLS-поведения не подтверждён.
E2-08 остаётся «На проверке», E2-06 без изменения статуса.

Олег сообщил «залил и разрешаю». Live beta подтверждена как
`e8f857d0fa07d1f419bf1364eb98b25239c77613`; код R2 — её предок
`21548e9040948b16d371fe31add6c0aca2fbbf3f`. Сервер получил код только Git
fast-forward и новым detached worktree. Основной runtime не переключался.

## Выполнение

Начало: `2026-10-07T07:28:37Z` (10:28:37 +03:00).
Preflight публикации/чистоты/коллизий/ресурсов/образов/lock успешен.
Созданы только новые ресурсы R2 и новый синтетический набор secrets.
Bootstrap и configure завершились exit0: миграции, key provisioning и
проверка SQL-контракта (27 ENABLE/FORCE RLS таблиц, policies, ACL, guards)
прошли в новой `mw_beta`. Это успешная установка/metadata-проверка, а не
доказательство разрешения/отказа запросов настоящего web LOGIN.
Создана отдельная новая `test_mw_beta`, bootstrap test_database exit0.

Согласованный Django suite запущен в controller под миграционной ролью,
с --keepdb/--noinput. Обёртка удерживала сырые сообщения только в памяти,
планируя вывести allowlisted сводку по завершении. Подробные SQL, cookies,
токены, response bodies и traceback-содержимое не записывались в файлы/отчёт.
Соединение завершилось сообщением `Connection ... closed by remote host`
и локальным SSH exit1 до получения сводки. Точный итог тестов и число
успешных/неуспешных проверок неизвестны; никакие PASS этого suite не заявляются.
Причина сетевого разрыва не доказана; idle timeout — только возможное объяснение.

При отдельном подключении для остановки в `07:40:09Z` тестовый процесс ещё
существовал (elapsed626 секунд). Повтор suite не выполнялся.
Остановлены controller, затем postgres; web не создавался.
Весь R2 завершён безопасной остановкой в `07:40:20Z`, до 60-минутного лимита.
Проверенные значения нагрузки: postgres примерно52–54 MiB/384 MiB,
controller около82 MiB/256 MiB, CPU controller около25%; OOM=false.

## Сохранность и ресурсы

Main beta, три прежних rehearsal и R1: ID/image/StartedAt/mounts/networks/ports
совпали с baseline. Основной runtime сохранился
`cf6f4ccd48106d9a44a64703bcfd79e49513ec3e`, security image/source не менялись.
Это сравнение metadata, не новый функциональный тест основной beta.

- Project `marketplace-e208-20261007-01a1105a-r2`.
- Root `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-08-20261007-01a1105a-r2`.
- Postgres ID `ccfbd90da741b62b9086512311920e000acaa6fd5f29a98dc6bd68ffdbba64a7`;
  StartedAt `2026-10-07T07:28:41.433054358Z`, FinishedAt `2026-10-07T07:40:20.32426775Z`.
- Controller ID `433f5c7cbff295134af2bddc551fd3c377ae257267cbd5ef3dbbd555b07548ef`;
  StartedAt `2026-10-07T07:28:52.882104633Z`, FinishedAt `2026-10-07T07:40:19.857993391Z`.
- Internal network `marketplace-e208-20261007-01a1105a-r2-private`,
  ID `160b35bcbe3bca7451d8730aa051b40ad812848ae3193dd3d8cddd775c4d6778`.
- Volume `marketplace-e208-20261007-01a1105a-r2-data`.
- Сохранены `mw_beta`, `test_mw_beta`, роли bootstrap/migrator/web,
  schema/policies/ACL, synthetic secrets, state/manifest и baseline metadata.

Оба контейнера stopped, работающих контейнеров проекта нет. Тестовая БД может
содержать незавершённый fixture; её не выдавать за успешно проверенный restore.
Новые dump/restore не создавались. Настоящий web LOGIN scenario, SQL probes,
сетевые HTTP проверки и отдельный static контейнер не запускались.
Удалений/reuse/отключения RLS/отката приложения/установок/push/K3/реальных ключей
не было. Значения новых секретов агенту не выводились.

## Локальная подготовка R3

Новый guarded runner запускает тот же фиксированный набор с failfast и
1750-секундным deadline. Он выводит только безопасные JSON-события, heartbeat
каждые30 секунд ожидания и сохраняет их в новом O_EXCL/0600/fsync evidence-файле.
Сырые сообщения отбрасываются; exit0 без полной сводки или со skips — не PASS.
План добавляет SSH ServerAliveInterval15/ServerAliveCountMax3.
Это подготовленная мера устойчивости/наблюдаемости, не новый серверный результат.

R3 использует новые уникальные имена; guards также сохраняют stopped R2.
Локально 11 проверок runner/redaction/complete-summary/preparation/context PASS,
system check и migration drift PASS. HTTP/SQL бизнес-код и политики не менялись;
предыдущие результаты не засчитываются как новые PostgreSQL-проверки.

Для следующего этапа нужны push Олега, live-проверка нового REV и отдельное
разрешение [плана R3](E2-08_SERVER_PLAN.md). Существующие R1/R2 не перезапускать,
не очищать и не повторять bootstrap/configure/suite в них. Основная beta требует
своего следующего плана/разрешения после успешного изолированного прогона.
