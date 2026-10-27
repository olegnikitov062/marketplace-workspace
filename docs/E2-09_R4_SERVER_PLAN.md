# E2-09 R4 — проверка восстановления владельца и диагностика restore

**План, не разрешение и не результат. Сейчас серверные действия запрещены.**
Олег публикует согласованные локальные коммиты в main сам. Затем требуется отдельное
разрешение на выкладку и этот изолированный этап; внедрение в основную beta им не покрывается.

Любое подключение к серверу и действие на нём требуют явного поручения Олега на текущую задачу. Файлы из Git доставляются исключительно после отдельно согласованной выкладки через `git pull --ff-only origin main` в согласованном чистом checkout ветки `main`. Если `main` отсутствует или текущий beta-baseline несовместим с этим порядком, выполнение заблокировано до локальной адаптации и отдельного согласования. Нельзя переключать ветку на сервере или подменять `main` на `beta`/`master`. Запрещены fetch+worktree, архивы, SCP/rsync, патчи и прямые правки как способы доставки файлов из Git. Нельзя даже предлагать вручную залить маленькое изменение файла, который хранится в Git. Изменения вне Git требуют отдельного явного поручения.

## Исходники и неизменяемые границы

Актуализация: 20.10.2026. Сейчас разрешены только локальные правки инструкций.
**К исполнению не готов:** helper/Compose используют прежнюю структуру, а план
предусматривал получение исходников из beta через fetch/worktree. Нужна отдельная локальная адаптация под
согласованный git pull из main; серверные проверки и переключения сейчас запрещены.

Исторический source R4: `453d04139be185f04d6db779c6a40b10a21fc5bb`.
Он сохраняется как доказательство исправления lock scope, но не является новым
исполняемым release. Основа будущей адаптации — локальный HEAD
`05e8318f453c6cfd2904ffdbec0e43ce45a365fa` (Python 3.14.8 / Django 5.2.18).
Новый source SHA пока не закреплён. Проверить его diff с историческим source:
lock-scope fix, диагностика и финансовые проверки сохранены, неожиданных изменений нет.
Олег публикует коммиты в main сам. Единственный способ получения исходников на сервере —
отдельно согласованный git pull из main. Предложение прямой заливки даже одного Git-файла запрещено.

R3 остановлен по failfast на SecurityConcurrencyTests.test_same_operator_permit_has_one_successful_consumer:
ERROR,130 учтённых тестов,1309.324s,runner exit1. Web/scenario/dump/restore не
запускались. R3 не локализовал прежний отказ restore R2. Отчёт —
docs/E2-09_ISOLATED_R3_RESULT.md. Попытка R4 08.10 закончилась SSH-таймаутом
до удалённой команды, стенд не запускался. Это не проверка сервера сегодня.

Локально воспроизведено удержание транзакции/строчной блокировки при проверке
пароля consume_operator_recovery. Минимальное исправление переносит дорогой
proof до блокировки и повторно проверяет текущий hash/аккаунт/owner/permit под
блокировкой, аналогично действующему recover_with_code. Новые3 regression-теста
и прежние security HTTP прошли локально. Это не доказательство того, что именно
lock_timeout вызвал R3 ERROR: тип/SQLSTATE там не сохранялись. R4 добавляет
только фиксированные категории ошибок без исходных сообщений, плюс прежние
restore checkpoints. Полный suite, исходный конкурентный тест, финансовые
миграции/HTTP/SQL и строгий restore остаются обязательными; исключать тест или
увеличивать timeout/CPU/password-hasher ради PASS запрещено.

## Новая структура и источники сведений

Ниже — локально прочитанные результаты 13–14.10.2026, не свежий server preflight:
CHANGELOG.md; BETA-RECIPE.txt, PROJECTCTL-CONTRACT.txt, projects.json, images.json,
final-layout.json в `C:/Users/krolo/Documents/selectel-preparation/git-layout-20261013/`.

| Назначение | Путь / идентификатор по сохранённым материалам |
| --- | --- |
| Действующая beta | /srv/projects/marketplace-workspace/beta |
| Штатный checkout beta | /srv/projects/marketplace-workspace/beta/repo, ветка beta |
| Постоянный Compose beta | /srv/projects/marketplace-workspace/beta/config/compose.json |
| Compose project beta | oleg-marketplace-beta; сервисы beta-web/beta-frontend, состав PostgreSQL уточняется preflight |
| Отдельный main | /srv/projects/marketplace-workspace/main/repo, ветка main; по журналу приложение/БД отсутствуют, публичная заглушка 503 |
| Платформа | /srv/platform; gateway, backup, projectctl и их конфигурации не менять |
| Прежний release-путь R4; создание через worktree запрещено | /srv/projects/marketplace-workspace/beta/artifacts/r4-releases/<новый полный source SHA> |
| Новый корень данных R4 | /srv/projects/marketplace-workspace/beta/artifacts/rehearsals/e2-09-20261007-01a115d9-r4 |

Сохранённый deployed commit beta: `05e8318f453c6cfd2904ffdbec0e43ce45a365fa`.
Backend image: `sha256:71fb381a18766c1cc1cb218b06366de879fd1943b87b9a9a39f095bda3880676`;
frontend image: `sha256:1aa66d2c10f46b14d243aa85f363c6a959766040cf740d16323cadd73027339c`.
Это исторические ожидания для сверки, не автоматический выбор image стенда.
Прежние runtime/source 409c71f и mount /home/adm_user относятся к 07.10 и больше
не задают baseline. Нельзя требовать прежние три контейнера/сервис web или source
mount /workspace: новый код может быть в image. Сверить актуальные labels,
immutable images, mounts, сети, порты, StartedAt и health со штатным Compose и
deployment state без чтения секретов. Неизвестное расхождение — STOP и уточнение
плана, а не автоматическая смена baseline.

Новый project/cluster: `marketplace-e209-20261007-01a115d9-r4`.

| Ресурс | Точное имя |
| --- | --- |
| Корень | /srv/projects/marketplace-workspace/beta/artifacts/rehearsals/e2-09-20261007-01a115d9-r4 |
| Контейнеры | marketplace-e209-20261007-01a115d9-r4-postgres, marketplace-e209-20261007-01a115d9-r4-controller, marketplace-e209-20261007-01a115d9-r4-web |
| Сеть | marketplace-e209-20261007-01a115d9-r4-private, internal=true, без портов на хост |
| Volume | marketplace-e209-20261007-01a115d9-r4-data |
| БД нового кластера | mw_beta, test_mw_beta; эти имена повторяются только внутри нового отдельного кластера |
| Роли нового кластера | mw_beta_bootstrap, mw_beta_migrator, mw_beta_web, с новыми секретами, без связей с прежними ролями |
| Restore-БД | mw_e209_01a115d9_r4_restore, owner mw_beta_migrator, web CONNECT=false |
| Dump | <корень>/backups/financial-after.dump, новый, mode0600 |
| События restore | <корень>/state/restore-events.jsonl, O_EXCL/0600, только фиксированные event/stage/index |
| События suite | <корень>/state/suite-events.jsonl, O_EXCL, только разрешённые статусы, без raw traceback/SQL/ответов |

Любой существующий новый root/name/label/volume/network/DB/dump/evidence — стоп.
Не переиспользовать частичный запуск. Дата 20261007 в имени сохранена для связи
с историей, а не как дата нового исполнения. При коллизии STOP; новый профиль
требует отдельной согласованной правки, не самовольного суффикса.

Защищаются действующая beta с frontend/PostgreSQL и постоянными данными, main,
gateway/backup/WB/Airflow/FBS/Finkos, все прежние E2-06/E2-07/E2-08 и E2-09
R1/R2/R3, их evidence/ключи/dumps/volumes. Наличие старых контейнеров не
предполагается: инфраструктура могла попасть в архив при переносе. Будущий
preflight сверяет существующие ресурсы и отсутствие остальных с документированным
архивом; неизвестное исчезновение — STOP. Не восстанавливать контейнеры и не
распаковывать архив ради старого helper. Сравнивать metadata до/после без Env,
содержимого секретов/БД. Отсутствие ресурса тоже фиксировать в baseline.

Образы стенда — только уже локально доступные; pull/build/install в серверный
этап R4 не входят. Новые точные backend/PostgreSQL image IDs пока **не закреплены**.
Исторические pins ниже не активны для нового исполнения:

- security image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`;
- PostgreSQL image `sha256:248efd5e58cd743f2a0e0daec8ea4649e5580145ec2a12e2345bc710d4a77201`;
- старый requirements.lock SHA256 `35cba592050150a0e5b1f68adc36d3f1c0871ceec79efc6c7f8e4a925fb34e60`.

У текущего локального backend/requirements.lock SHA256
`d0097f1fc01a4569ab48fac141d4aff641708bafe375f13731b839724c91a9da`.
После адаптации закрепить хеш нового release и соответствие зависимостей image.
Старый image с новым lock не смешивать. Если подходящего image нет — STOP и
отдельный план подготовки образа; image действующей beta автоматически не брать.

## Обязательная локальная подготовка перед допуском

В этой задаче перечисленные изменения кода **не выполнялись**.

1. Адаптировать `beta/deploy/prepare_financial_rehearsal.py`: source backend только
   из согласованного checkout main после git pull, без создания release через worktree;
   root из таблицы, новый lock/image pin, независимый baseline действующей beta и
   защищённых ресурсов. Убрать предположения о прежнем количестве контейнеров,
   image/mount и обязательном существовании старых стендов, сохранив контроль
   неизменности. Не добавлять live DB/secret чтение ради baseline.
2. Адаптировать `beta/deploy/compose.financial-rehearsal.json`: все secrets/state/
   backups bind paths внутри нового root, source — backend согласованного checkout main
   read-only после git pull. PostgreSQL image согласован с helper. Запрещены mounts постоянных
   config/data/secrets beta/main, Docker socket и архивов.
3. Локально проверить согласованность helper/Compose/плана, отказы при старых
   путях, коллизиях, неверных pins/baseline, JSON и существующие preparation-тесты
   `backend/access_control/tests/test_financial_preparation.py`. Это не PG/runtime PASS.
4. Закрепить новый полный source SHA из main и image/lock pins здесь и в
   SYSTEM_FINANCIAL_CHECKS.json. Сохранить сравнение с историческим source.
   Commit только после отдельного разрешения, публикация — Олегом.
5. Только после пунктов 1–4 и отдельного допуска выполнить fresh серверный
   preflight. До этого исполняемых команд запуска у плана нет. Старые shell-блоки
   удалены из активной инструкции как несовместимые с новой структурой.

## Лимиты и секреты

Весь этап <=60 минут; suite <=2400 секунд, failfast, без повторного прогона.
Controller lifetime 3600 секунд; команды configure/scenario/verify <=180 секунд,
dump и restore по <=600 секунд. На первой ошибке остановиться. Если оставшегося
окна недостаточно, остановиться, не продлевать автоматически.

Postgres384MiB/0.25CPU, web384MiB/0.25CPU, controller256MiB/0.25CPU;
bootstrap256MiB кратковременно, не одновременно с suite/web. pids_limit96.
Предварительно MemAvailable>=2GiB, disk free>=2GiB. max_connections20
(включая резерв PG), фактически <=8 клиентских соединений, конкурентных проб2.
Серверные верхние пределы: statement_timeout15s, lock_timeout5s,
idle-in-transaction20s; штатная Django-сессия уже строже: statement_timeout5s,
lock_timeout2s. Допускаются положительные значения <= серверных пределов,
не требуется равенство15s/5s. Ноль (unlimited), превышение, неполные значения
и >8 клиентов запрещены. Сетевой HTTP timeout5s.
Не проводить нагрузочный benchmark. При превышении, OOM или деградации основной
beta — остановка только нового стенда с сохранением ресурсов.

prepare_financial_rehearsal создаёт только новые случайные synthetic secrets:
db_bootstrap_password и отдельный pg mount той же новой пары, db_migrator_password,
db_web_password, django_secret_key, mfa_encryption_key, isolation_signing_key.
Файлы0600, UID процесса/PG, корень0700; процессы читают их через /run/secrets,
не CLI/env значения. Никаких старых owner recovery verifier/K3/ключей основной beta.
Web получает только web password + Django/MFA/isolation ключи, никогда migrator/
bootstrap. SQL-пароль dump-процесс получает внутри нового postgres из нового mount,
не выводя значение. Не cat ключи в терминал, не inspect Env, не shell tracing,
не curl -v/headers/body/cookie dumps, не писать raw exception/SQL в отчёты.
Только example.invalid и locmem; внешние чтения/запись/доставка/расписания выключены.

## Последовательность после отдельного разрешения

0. Один разрешённый SSH preflight, без повторов при ошибке: доступность Docker,
   ресурсы, наличие согласованных images, безопасный снимок metadata beta и всех
   защищённых сервисов. Branch/origin/HEAD, чистота repo, labels, Compose и deployment
   state должны совпасть с согласованным baseline. Технические health endpoints
   проверяются без личного MFA, записей или бизнес-данных. Материалы 13–14.10
   свежую проверку не заменяют. Неизвестные расхождения — STOP до записи.
1. Только после локальной адаптации и отдельного согласования — git pull из main
   в заранее согласованном чистом checkout main с проверкой origin/ветки/полного SHA
   до и после. Получение исходников через fetch/worktree запрещено. Штатный checkout
   beta и защищённый отдельный main автоматически не переключать и не обновлять.
   Пока совместимый checkout и источник read-only backend не определены локальным
   планом, этот шаг и все зависимые действия заблокированы; обход не предлагать.
2. Отсутствие root/контейнеров/labels/сети/volume/evidence R4, лимиты и оставшееся
   время проверены. Адаптированный helper создаёт только новые root/секреты;
   Compose config проверяется до up. Затем строго: postgres ready → bootstrap →
   controller → configure → test_database → runtime_limits → financial_test_runner
   (один failfast suite) → scenario → web → verify_financial_web_runtime.
   Timeout каждой команды — из раздела лимитов. Ненулевой exit — STOP.
   Действующая beta и её секреты/данные в последовательности не участвуют.

Если image не содержит timeout, использовать host timeout для конкретного docker
exec и по таймауту остановить новый controller; не устанавливать пакет и не оставлять
команду работать в фоне. Главный suite имеет собственный kill/deadline. Проверка runtime_limits выполняется
до suite, использует числовые pg_settings и выводит только несекретные пределы/число
соединений. Её validator локально проверен для более строгих5s/2s, граничных15s/5s,
unlimited/превышений и неполного контекста. Во время suite — только лёгкий metadata/
Docker-stats мониторинг; дополнительный параллельный Django-процесс не запускать.

3. Suite без skipped/failures/errors. FinancialHTTPTests — новая матрица полей/
   формул/итогов, независимости/делегирования, подмен/CSRF, active sessions/revoke,
   overlap/regrant/неоживления ссылок, восстановления/архивов/MFA/support.
   FinancialConcurrencyTests — реальные отдельные PG-соединения, отзыв против
   чтения/изменения/download, после commit отзыва отказ. FinancialMigrationTests —
   переход с E2-08 сохраняет прежние данные/Grant/guards; финансовое populated
   downgrade запрещено. Старые прогоны не засчитывать.
4. Scenario отдельно от suite: fixture создаёт migrator; действительные логин/TOTP,
   затем session_user=current_user=mw_beta_web, не SET ROLE. SQL denies в обеих
   формах (без подписи/с genuine signed statement): прямые столбцы/sum/UPDATE,
   ALTER RLS, private helper, UPDATE finance binding, SET ROLE. Фиксированный
   read запрещён без обоих прав, с control/null/bad/resource/action контекстом,
   чужим кабинетом, repeatable-read. Проверяются exception/savepoint/full rollback,
   reuse, два соединения, оба Grant и неизменяемая ссылка; старый RLS probe выполнен
   на этом новом кластере. Подписываются только статические SQL теста внутри helper,
   клиентского signing endpoint или аргумента SQL не добавлено.
5. Network smoke — шесть статусов Gunicorn + SQL ACL/RLS; authenticated HTTP через
   Django Client с настоящим web LOGIN отдельно. Browser/TLS/load PASS не заявлять.

## Точный ожидаемый переход schema/ACL

Миграций +2: access_control.0003_financial_schema и data_isolation.0002_financial_operations.
Новая public.access_control_syntheticfinance: record_id PK/PROTECT, org/cabinet FK,
четыре numeric(14,2), четыре диапазонных CHECK; составной FK(org,cabinet,record)
и новый UNIQUE(org,cabinet,id) у SyntheticRecord. Новый nullable FK finance_grant_id
у ExportBinding, CHECK access_known_operation расширен только synthetic_finance
четырьмя действиями без platform; существующие Grant/данные не переписываются.

Семь новых trigger-функций/триггеров: finance_scope, finance_identity,
finance_nodelete, finance_binding_scope, finance_binding_immutable, finance_revoke,
finance_manager. Все SECURITY DEFINER/search_path pg_catalog,public/PUBLIC EXECUTE
отозван. Новая таблица ENABLE+FORCE RLS с одной operator policy владельцу migrator;
27 прежних RLS-таблиц/правил сохраняются, всего28. Новые mw_isolation функции:
private finance_allowed(jsonb), finance_read(uuid[],uuid),
finance_write(uuid,numeric,numeric,numeric,numeric); все DEFINER с фиксированным
search_path. Web имеет EXECUTE только последних двух, не finance_allowed.

Web получает только INSERT(finance_grant_id) к прежним столбцам ExportBinding,
без UPDATE этого поля, и EXECUTE двух функций. На SyntheticFinance никаких
табличных/столбцовых SELECT/DML/REFERENCES/TRIGGER прав; унаследованный default
SELECT снимается в транзакции создания таблицы. Никаких DDL/TEMP/role membership/
BYPASSRLS/superuser/GRANT OPTION. Табличные RLS не объявляются защитой столбцов:
финансовый барьер — ACL + две проверяющие функции + серверные потребители.
Первый finance-owner назначается только явным операторским synthetic bootstrap,
не миграцией/ролью/шаблоном. Не вводится право platform_admin на деньги.

Fresh configure снимает default SELECT только внутри нового пустого кластера,
затем устанавливает фиксированный прежний ACL и финансовую дельту. Не применять
этот fresh helper к основной/сохранённой БД. Legacy downgrade-тесты E2-06/E2-07,
снимающие guards заполненной схемы, не обходят запрет E2-08/E2-09.

## Backup/restore после успешных проверок

Остановить только новый web; проверить, что suite/scenario завершились и writers
нет. Не останавливать основную beta. Dump включает синтетические секреты, его не
читать/публиковать; сохранить0600, размер и SHA256 всего dump (не отдельных ключей).
Следующий блок создаёт только новый dump/новую restore-БД, исходную mw_beta не меняет.

До адаптации/pins — последовательность без исполняемых команд:

1. Остановить только R4 web; убедиться в отсутствии writers/suite/scenario.
2. Внутри только R4 postgres проверить cluster_name и отсутствие restore-БД/dump;
   создать новый pg_dump custom-format с исключительным созданием файла/0600,
   сохранить размер и SHA256. Пределы времени dump/restore остаются по 600 секунд.
3. В том же новом кластере создать mw_e209_01a115d9_r4_restore, owner
   mw_beta_migrator, отозвать PUBLIC и исключить web CONNECT; выполнить
   pg_restore --exit-on-error без вывода сырых ошибок/секретов.
4. Один financial_restore_check; только при PASS — R4 web и
   verify_financial_web_runtime, адаптированный helper --verify и сравнение baseline.
5. Остановить R4 web/controller, дождаться завершения, затем R4 postgres.
   Ничего не удалять и не запускать повторно при ошибке.


financial_restore_check сравнивает **до карантина** все public/mw_isolation строки
(включая новый signing key только в памяти), перечень таблиц/последовательностей,
last_value/is_called, столбцы/типы/defaults/ranges, table/column/default/function/
schema ACL, owners, policies/FORCE, функции/search_path, triggers/FK/CHECK/indexes,
django_migrations. DB ACL — намеренное отличие: restore не принимает web CONNECT;
не выдавать его ради теста. Различие остальных данных/metadata — FAIL, не игнорировать.
После сравнения проверяются запреты снять revoke у финансового Grant/permit или
переписать finance binding, затем quarantine_restored_access закрывает все сессии,
ссылки/факторы восстановления и помечает accounts recovery_required. Восстановленная
копия никогда не подключается к web. Historical backup не знает последующих отзывов:
открытие допустимо только после отдельной сверки актуальной матрицы, не regrant.

## Диагностика suite без раскрытия данных

DiagnosticResult передаёт только фиксированную категорию: LOCK_UNAVAILABLE,
QUERY_CANCELLED,SERIALIZATION,DEADLOCK,PERMISSION,CHECK_CONSTRAINT,FOREIGN_KEY,
UNIQUE,ASSERTION,OTHER. Категория определяется по allowlist SQLSTATE через
exception cause, без str/repr/type/locals. financial_test_runner сохраняет
только {event:failure_category,category:<allowlisted value>}; неизвестные строки
по-прежнему отбрасываются. Это локализует класс сбоя, но не доказывает причину.
Никаких raw traceback/SQL/messages. Первая категория ошибки сопровождает STOP,
не даёт разрешения продолжать тесты, повторять запрос или ослаблять проверки.

## Диагностика restore без раскрытия данных

Новый tools.financial_restore_evidence пишет state/restore-events.jsonl только
после marker-проверки, O_EXCL/0600/fsync. Повторный файл — отказ.
События: restore_stage_started, restore_failed, restore_passed;
поля только event/stage/index. Нет traceback, exception message/type, SQL,
аккаунтов, ключей, строк данных, cookies, токенов или ссылок. Индекс1-based:
metadata — порядок неизменённого METADATA, rows/sequences — отсортированный
перечень таблиц/последовательностей, immutable_guard — три фиксированные команды.
Этапы guard/source_acl/restore_connect/restore_identity/metadata/rows/sequences/
revoked_fixture/immutable_guard/quarantine/quarantine_verify локализуют отказ.
Не делать вывод о следующем этапе по предыдущему checkpoint.
Оркестратор показывает только эти allowlisted JSON-события и exit code.
При отказе прочитать только этот файл (при необходимости read-only sudo),
остановить новый стенд; не повторять helper, не читать dump/секреты/сырые ошибки.
Все строгие сравнения по-прежнему обязательны до quarantine.
Финансовый бизнес-код, миграции, SQL ACL/RLS и сами restore-сравнения неизменны.
Сопутствующее минимальное изменение — lock scope consume_operator_recovery;
оно сохраняет проверки доступа и подлежит новому PG concurrency контролю.
Локально13 preparation-тестов PASS0.446s; это не PostgreSQL R4.

## Остановка, откат и результат

Любой отказ guard/SQL/HTTP, skipped, timeout, лишний ACL, неполное сравнение,
несовпадение старых metadata, нехватка ресурсов — STOP. Сохранить только безопасный
статус/имя теста. Сначала остановить новые web/controller и дождаться завершения,
затем новый postgres; не отправлять обоим слоям параллельный stop, чтобы shutdown
БД не создавал вторичную ошибку ещё выполняющегося теста. Никаких DROP,
down -v/prune, перезаписи dump/секретов/БД, удаления evidence или повторного
использования имён. Остановка нового стенда — безопасный откат этого этапа.
Populated schema downgrade и fallback на pre-finance/pre-RLS runtime запрещены;
если обновлённый web не готов, он остаётся остановленным, ограничения не отключать.

В результат внести source/image/lock/PG version, start/stop с TZ, новый список
resources, количество/время tests/skips, реальный web LOGIN, HTTP/SQL/financial/RLS,
upgrade/rollback, dump SHA/restore/quarantine, сохранность старых контейнеров и
точные ошибки без секретов. Успех стенда не меняет runtime основной beta.

Отдельно не покрыты: отсутствующие cache, worker, storage/готовый рабочий экспорт,
интеграции/реальные отчёты/сотрудники/D3. E5-13 UI, E5-07 рабочий экспорт,
E6-03 реальные роли остаются своими задачами. E2-06/E2-08 формально не закрывать.
Внедрение в действующую beta и отдельный main не входят в R4. После PASS нужны
самостоятельный план и разрешение: backup/restore, совместимость схемы/ACL/RLS и
штатный deployment-контракт /srv/platform. Не применять прежние accounts/security
overlays или projectctl update/rollback как часть R4.

## Критерии готовности плана и текущая граница

На 19.10 выполнена только локальная актуализация документа: новая карта путей,
защищённые ресурсы, обязательная адаптация, последовательность и STOP. Сервер,
Git remote, Docker и PostgreSQL этим изменением не проверялись. До допуска нужны
адаптированные helper/Compose, локальные проверки, опубликованный полный source
SHA из main, совместимый checkout и согласованные image/lock pins. Fresh baseline
допустим только в отдельно разрешённом этапе после локальной адаптации порядка доставки.
Сейчас эти условия не закрыты. Исторический docs/E2-09_R4_CONNECTION_RESULT.md
не меняется; его «тот же source» относится к 08.10 и заменён настоящим планом для
будущего запуска. E2-09/E2-06/E2-08 остаются «На проверке».
