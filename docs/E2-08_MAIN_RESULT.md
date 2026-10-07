# E2-08 — результат внедрения в основную beta

07.10.2026, Europe/Moscow. Основной переход выполнен по текущему разрешению
Олега «залил, разрешил». Серверное окно 12:25:31–12:47:00 +03:00.
Live beta проверена непосредственно: `1d3076a0825cf90259d16333e3cc24668fa33e81`.
Приложение закреплено на проверенном R4
`409c71f65db53873183c6ffd8d059561c05185d2`, только опубликованный Git.
Документальный commit и runtime — разные ревизии.

## Фактический результат

- Preflight: пустые доменные таблицы, прежний E2-07 SQL-контракт, ровно одна
  pending migration. 35 public tables: 112 permissions, 28 content types,
  38 migrations, 7 anonymous Django sessions; остальные пусты. Новых личных
  аккаунтов, организаций, Grant или platform_admin не создавали.
- Основной web остановлен в `2026-10-07T09:36:37Z`. Посторонних подключений
  к mw_beta не было. Оба PostgreSQL и сохранённые стенды не останавливались
  и не пересоздавались в этом этапе.
- Новый custom dump: 204905 bytes,0600, SHA256
  `b24f013c801fbd148f9e8f398fde460e7bee5751c6d57d4a517d4e1b641190f9`.
  Закрытый restore завершился exit0; web CONNECT/TEMP=false до/после.
- Все строки 35 public tables сравнены в памяти, без вывода строк/отпечатков
  сессий. Table/column/schema/default/function ACL, owners, sequences,
  indexes, triggers и роли совпали. Database ACL отличается только
  предписанным владельцем/закрытостью restore-БД.
- Три CHECK после pg_restore имеют эквивалентную, но не побайтно одинаковую
  форму SQL. Проверка описана ниже; ограничения не изменялись.
- Bootstrap создал только пустую закрытую mw_isolation, owner migrator.
  Одна миграция `data_isolation.0001_statement_and_row_policies`, запись ключа
  и минимальный контракт применены одной транзакцией; COMMIT подтверждён
  к `2026-10-07T09:41:23Z`.
- 27 таблиц ENABLE/FORCE RLS. 11 фиксированных trigger functions стали
  SECURITY DEFINER с закреплённым search_path и без PUBLIC EXECUTE.
  Табличные/поколоночные/database/default ACL не расширены. Web получил
  только USAGE private schema и три разрешённые EXECUTE; ключ недоступен.
- До запуска web повторно сравнены все прежние строки с restore: добавлены
  только migration row и соответствующее увеличение sequence. Изменения
  схемы/ACL совпали с опубликованной миграцией; тела функций сохранены.
- Пересоздан только web через compose.security-web.json, SECURITY_SOURCE
  и SECURITY_IMAGE. Новый ID
  `4c30e68d246015c013aa071f4a8dc6af7088abdb9c9329ef22509db9cebadaa2`,
  StartedAt `2026-10-07T09:43:33.3431035Z`.
  Source `/home/adm_user/marketplace-workspace/beta/app/releases/409c71f65db53873183c6ffd8d059561c05185d2/backend`, read-only.
  Image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`;
  UID10001:10001,384MiB/0.25CPU, internal network/no host ports сохранены.
- Фактические session_user/current_user=mw_beta_web, полный RLS/ACL контракт
  PASS. 23 unsigned SELECT ничего не раскрывают, включая существующие
  anonymous sessions. Четыре поддельных/отсутствующих контекста не читают
  сессии и не изменяют записи; rollback/reuse очищает GUC.
- Девять отказов SQL42501: key SELECT, private HMAC EXECUTE, DISABLE RLS,
  CREATE public table, CREATE TEMP, SET ROLE migrator/bootstrap, TRUNCATE
  synthetic records, DELETE users. Пробы транзакционные, неожиданные
  изменения откатывались бы; все девять действительно отвергнуты.
- Девять внутренних сетевых HTTP-проверок PASS: live/ready200, session401,
  GET login405, MFA login200, anonymous platform403, synthetic organization
  memberships403, два изменяющих POST без CSRF403. Ответы/cookies не сохранены.
  Ready подтверждён к `2026-10-07T09:44:38Z`: stop→приёмка 8мин01с.
- После HTTP все прежние строки сохранены, migrations38→39 и anonymous
  sessions7→8 от страницы MFA входа. Доменные таблицы по-прежнему пусты.
  Оба PostgreSQL и все прежние rehearsal, включая R1–R4, сверены неизменными;
  сохранённые стенды остаются stopped. Финальный read-back завершён09:47:00Z.

## Остановки проверок и их разрешение

Первый metadata assert сравнивал Compose alias `private` с Docker name
`marketplace-beta-private`. После разрешения alias через merged Compose
совпадение подтверждено. Полный config/Env не выводился.

Первое restore comparison остановилось на CHECK `access_known_operation`,
`membership_role_valid`, `membership_state_valid`: PostgreSQL заменил
`(ARRAY['…'::character varying, …])::text[]` на
`ARRAY[('…'::character varying)::text, …]`. Для четырёх точных константных
массивов проверены IS NOT DISTINCT FROM и равенство pg_typeof. Замена только
этих четырёх выражений делает три полных определения идентичными; все остальные
constraints совпали буквально. Структурных/семантических расхождений нет.
До этого доказательства следующая фаза не выполнялась; после него продолжен
тот же разрешённый переход. Это не исключение, допускающее неизвестный drift.

`result.json` сохраняет промежуточную остановку, включая тогдашний признак
неприменённой миграции. Он намеренно не перезаписан. **Текущий результат —
result.final.json, migration.after.json и containers.after.json**.

Post-migration comparison сначала ошибочно ожидал неизменный function ACL.
Опубликованный install явно отзывает PUBLIC EXECUTE у 11 TRUSTED_TRIGGERS.
Подтверждены ровно эти 11 удалений, ноль добавлений и неизменность остальных
function ACL; затем полное сравнение пройдено. Дополнительного SQL-изменения
для исправления проверок не было.

Промежуточный контейнерный assert смешал Name с/без `/` и Ports из двух
разделов Docker inspect. Повторная проверка использовала исходные поля:
Config/State/NetworkSettings и Mounts. Неизменность соседей подтверждена.
Ошибочные первичные assert не выдаются за успешные проверки.

## Секреты и сохранённые ресурсы

Checkpoint:
`/home/adm_user/marketplace-workspace/beta/backups/database/e2-08-main-20261007-01a1105a`.
Файлы: `before.dump`, `containers.before.json`, `database.before.json`,
`acl.before.json`, `result.json`, `migration.after.json`, `result.final.json`,
`containers.after.json`. Каталог0700, файлы0600, UID10001, O_EXCL/no overwrite;
семь JSON перечитаны, dump размер/hash проверены повторно. Данные dump закрыты.
Restore `mw_e208_main_restore_20261007_01a1105a`, owner mw_beta_migrator,
PUBLIC/web CONNECT/TEMP отсутствуют. Эти имена теперь заняты.

Новый key file `beta/config/secrets/isolation_signing_key`:32 random bytes,
0600,UID10001,O_EXCL/no-symlink, отдельный от R4. Значение/отпечаток не выводились.
Существующие DB/Django/MFA секреты потребляли только разрешённые штатные
процессы. Агент реальные ключи/пароли не просматривал, K3/Telegram не выполнял.

Основной PostgreSQL имеет log_min_error_statement=error. Поэтому key INSERT
передан через **psycopg.Cursor server binding**, не Django ClientCursor:
значение не в тексте SQL. До записи проверены log_statement=none,
log_parameter_max_length_on_error=0 и оба duration logging=-1. Глобальные
настройки и SQL-права для логирования не менялись. Обычный runtime signer
сохраняет ClientCursor; смена касалась только операторского provisioning.

## Границы результата и откат

Это новая проверка основной E2-08. Полный сценарий двух организаций/кабинетов,
независимых действий, отзыва Grant/членств/support, MFA/блокировок/архива,
конкурентности и необратимого отзыва ссылки — отдельный успешный R4 на том же
APP_REV:83 PostgreSQL tests/0skips и actual web LOGIN. В main он не повторялся:
пустая main сама по себе не доказывает положительный multi-tenant сценарий.

E2-08 остаётся **«На проверке»**: существующие потребители и основной runtime
проверены, но критерии business cache-hit после отзыва, фоновых заданий и
реального файлового/готового экспорта не проверены — этих потребителей нет.
Синтетическая экспортная ссылка покрыта, рабочий экспорт относится к E5-07.
Наличие helper или locmem не объявлено защитой отсутствующего business cache.
E2-06 остаётся «На проверке»; E2-07 без изменения. Brand scope, финансовая
фильтрация E2-09, UI, worker, integrations, D3/E6-03, browser/TLS вне этапа.

Безопасный fallback после COMMIT — остановить только основной web. Не
возвращать cf6f4cc/pre-RLS код, не выключать RLS/MFA/Grant, не делать reverse,
live restore или очистку. Все DB/roles/keys/checkpoints/стенды сохраняются.
Восстановление, очистка или новый перезапуск требуют конкретного нового плана
и разрешения; дополнительных действий для текущего успешного rollout не нужно.
Локально публикуется только отчёт после проверки Олегом; агент push не делает.
