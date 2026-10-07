# E2-08 — результат изолированного R4, 07.10.2026

**Изолированный R4 выполнен успешно. Основная beta не внедрялась.**
E2-08 остаётся «На проверке» до отдельного перехода/проверок основной beta.
E2-06 не закрывается; рабочий экспорт, UI, worker, cache и интеграции не добавлены.

## Допуск и воспроизводимость

Текущий допуск Олега: «залил и разрешаю». Live beta:
`774b00224a13a96549f96bff9c5eed0286c04de3`; source REV:
`409c71f65db53873183c6ffd8d059561c05185d2`, подтверждённый предок live beta.
Сервер получил исходники только Git fast-forward и новым detached release.
Окно: `2026-10-07T08:02:03Z`—`08:21:17Z` (11:02:03—11:21:17 +03:00).
Новых установок/build/pull образов, push или ручных серверных правок кода нет.

- PostgreSQL 17.11 (Debian 17.11-1.pgdg12+2).
- Backend image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`.
- PostgreSQL image `sha256:248efd5e58cd743f2a0e0daec8ea4649e5580145ec2a12e2345bc710d4a77201`.
- Lock SHA256 `35cba592050150a0e5b1f68adc36d3f1c0871ceec79efc6c7f8e4a925fb34e60`.

Все коллизии/образы/ресурсы/исходники проверены подготовщиком до создания R4.
Созданы только новый synthetic secret set и новые ресурсы; example.invalid/locmem.
Основные секреты, K3/Telegram и реальные аккаунты не читались/не использовались.

## Выполненные проверки

| Этап | Наблюдаемый результат |
| --- | --- |
| Prepare/bootstrap/configure/test_database | exit0; свежие mw_beta/test_mw_beta; 27 ENABLE/FORCE RLS таблиц и SQL-контракт |
| Подготовка test DB | guarded test-key provisioning и реальный signed claims probe прошли перед suite |
| PostgreSQL suite | **83 tests, 815.835с, OK, skipped0, exit0** |
| Durable runner | complete=true, passed_without_skips=true, elapsed828с; сводка перечитана |
| Actual SQL web LOGIN | session_user=current_user=mw_beta_web; HTTP/SQL/RLS scenario PASS, не SET ROLE |
| Базовые SQL privilege denials | 10/10; отдельные key/HMAC/RLS/role probes также прошли |
| Повторная выдача Grant | старая синтетическая ссылка осталась отозванной |
| Сетевой web smoke | 6/6 до backup и 6/6 после restore-check |
| Static container | 10 tests, 1.998с, PASS; без сети/секретов, не PostgreSQL proof |
| Dump/closed restore | exit0, новый dump0600; web CONNECT restore=false |
| Restore helper | все public-строки и private key равны в памяти, политики/private functions ACL совпали; permanent revoke и quarantine PASS |
| Итоговая изоляция/сохранность | verifier PASS; main beta и все прежние rehearsal metadata неизменны |
| Завершение | web/controller/postgres R4 stopped, OOM=false, работающих контейнеров R4 нет |

Suite включает текущие HTTP-регрессии изоляции, Grant/platform, сессий/MFA,
миграции reverse/refusal/forward и конкурентные сценарии access/security.
Его SQL-роль — migrator, поэтому результат отдельно от actual-web scenario.
Прошлые E2-07 результаты в эти 83 теста не подставлялись.

Actual-web scenario и isolation_sql_probe реально проверили отсутствие/подделку
GUC, восемь NULL claims, запрет key/HMAC/DDL/SET ROLE, две организации и несколько
кабинетов, чтение без WHERE только в подписанной области, независимость view/change,
запись, подмену SQL при старой подписи, rollback/savepoint/повторное соединение,
два конкурентных соединения без переноса контекста, немедленный отзыв Grant,
ограниченное platform support window, HTTP CSRF и необратимость export-ссылки.
Контрольные таблицы сохраняют описанную границу доверия: Python-сервисы/подписант
доверенные, SQL web credential сам по себе подпись не создаёт. Компрометация
Python/key/operator не объявляется покрытой RLS.

`state/suite-events.jsonl`: mode0600,
SHA256 `c58e35c4218310b7fc32dd04732c4f465943acfe2f1b77299a63a62465f15f9c`.
Этот hash относится только к безопасным событиям runner, не к ключам/личным данным.
Сырые SQL/traceback/source lines/locals/cookies/tokens/response bodies не сохранялись.

Нагрузка в двух снимках: postgres 55–60 MiB/384 MiB, controller около116 MiB/256 MiB;
CPU controller около25% при лимите0.25. Web также ограничен384 MiB/0.25 CPU.
Штатное предупреждение Django о запросе из AppConfig.ready() наблюдалось; это
rehearsal cluster guard, не ошибка теста и не основание объявить его отсутствие.

## Backup/restore

Перед dump остановлен только R4 web; проверено отсутствие других SQL-соединений
к исходной mw_beta и отсутствие целевых dump/restore. Bootstrap credential
потреблял только процесс внутри нового R4 postgres, без вывода/аргументов.

Dump: `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-08-20261007-01a1105a-r4/backups/isolation-after.dump`,
292050 bytes, mode0600, SHA256
`d32338679b5ba31e3b5db3ab560605a10d5a398f53c714e73471939911b9b4b4`.
Новая БД `mw_e208_01a1105a_r4_restore`, owner migrator; PUBLIC права отозваны,
web CONNECT=false до/после pg_restore. Исходная mw_beta не заменялась.

Сравнение public-строк/private key выполнено без вывода значений; сравнены
pg_policies и private function source/definer/search_path/ACL. Отдельное полное
сравнение table/column ACL между исходной и restore этим helper не выполняется:
штатный dump/restore завершился без ошибок, точный web-контракт проверен в
исходной R4 до/после. Не выдавать этот предел helper за полную отдельную ACL-diff
проверку restore. В плане основной beta она указана явно.
После сравнения восстановленные сессии/экспортные ссылки отозваны, аккаунты
карантинированы; restore остаётся закрытой. Никакие данные не выводились.

## Сохранённые ресурсы

- Project `marketplace-e208-20261007-01a1105a-r4`.
- Root `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-08-20261007-01a1105a-r4`.
- Postgres ID `c23d15b21bb1d83d31174681d69f7828bddec9c45b6a5a70bb4ecfaf0c4ecb1d`,
  StartedAt `2026-10-07T08:02:07.444778439Z`, FinishedAt `2026-10-07T08:21:07.216472071Z`.
- Controller ID `e06dc494fff289f73e75c4d3ed984b2c3650880faf2141f70f3a174dc059f679`,
  StartedAt `2026-10-07T08:02:19.688777516Z`, FinishedAt `2026-10-07T08:21:17.076355764Z`.
- Web ID `b507d8a843d73f3e0e1063b6edcc42a94893ebbdecaa4b2f9a5f57d0477097c5`,
  последний StartedAt `2026-10-07T08:20:54.098916054Z`, FinishedAt `2026-10-07T08:21:07.857165125Z`.
- Internal network `marketplace-e208-20261007-01a1105a-r4-private`,
  ID `7edf5b78b6258aa0c2beb98282ed6c77f3892fe82b396fbdc65c7e5e3daa3f2c`.
- Volume `marketplace-e208-20261007-01a1105a-r4-data`, все БД/роли/keys/dump/evidence сохранены.

R1/R2/R3, оба owner rehearsal, E2-07 rehearsal и три main-контейнера не менялись
по ID/image/StartedAt/mounts/networks/ports. Main runtime остаётся cf6f4cc.
Остановка R4 не включает удаление, reuse, down-v/prune/DROP или отключение RLS.

## Что остаётся

Основная beta: отдельный [план](E2-08_MAIN_ROLLOUT.md), свежий main backup/restore
с полным ACL-сравнением, миграция/сохранение данных, новая SQL/runtime проверка
и отдельное разрешение. R4 не даёт этого разрешения.
Browser/TLS, бизнес-файлы/cache-hit/worker/интеграции отсутствуют или не проверялись;
рабочий экспорт E5-07, финансовые поля E2-09, D3/реальные сотрудники E6-03 вне scope.
