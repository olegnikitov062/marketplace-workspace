# E2-08 — повторный изолированный стенд R4, план для отдельного разрешения

07.10.2026, Europe/Moscow. **R4 выполнен по отдельному разрешению Олега, все этапы плана завершены.**
Live beta774b00224a13a96549f96bff9c5eed0286c04de3, source409c71f65db53873183c6ffd8d059561c05185d2.
[Фактический результат R4](E2-08_ISOLATED_R4_RESULT.md):83 PostgreSQL tests/0skips,
actual web LOGIN/SQL/HTTP, backup/restore и финальная изоляция PASS. R4 stopped.
Имена/ресурсы заняты; повтор этого плана не разрешён. Основная beta не внедрялась;
для неё подготовлен [отдельный план](E2-08_MAIN_ROLLOUT.md).

Ниже сохранены условия подготовленного плана; заявления о непубликации/отсутствии
допуска относятся к моменту его составления, не к результату R4.

Результат R3: [E2-08_ISOLATED_R3_RESULT.md](E2-08_ISOLATED_R3_RESULT.md).
Сохранённые ресурсы R1/R2/R3 не использовать повторно. Исправление пока локальное;
ниже закреплён новый полный REV, затем требуется push Олега,
live-проверка публикации и отдельное разрешение R4.

## Точные исходники и условие публикации

- Последняя **live-проверенная опубликованная** beta:
  `971600e8fca04b23d0de41f06bca950b09116883` (проверено 07.10.2026).
  Миграции и ACL R3 прошли; suite остановлен на первом FAIL, 5 tests/42.991с.
- Точный подготовленный код E2-08, `REV`:
  **`409c71f65db53873183c6ffd8d059561c05185d2`**.
  На момент составления плана это локальный неопубликованный коммит Oleg.
- Актуальная редакция этого документа публикуется следующим отдельным локальным коммитом без
  изменения backend/deploy. Олег проверяет и выполняет push самостоятельно.
- Перед разрешением повторить live `git ls-remote --heads origin beta`,
  подтвердить достижимость полного REV из фактически опубликованного SHA.
  Если публикации нет, выполнение заблокировано; `origin/beta` само по себе
  доказательством не является. Записать наблюдённый live SHA в протокол допуска.
- После отдельного разрешения сервер получает beta только Git fetch и
  fast-forward чистого `/home/adm_user/marketplace-workspace/beta/app/repository`.
  Создать новый detached worktree `beta/app/releases/<REV>` из опубликованного
  REV; если путь существует — остановиться до проверки назначения/чистоты.
  Никаких архивов исходников, SCP исходников или ручного редактирования кода.
  Использовать актуальный план из опубликованной beta, а backend — из указанного
  REV; более ранняя редакция плана внутри source-release не заменяет этот допуск.

Последний зафиксированный основной runtime —
`cf6f4ccd48106d9a44a64703bcfd79e49513ec3e`, RO backend в соответствующем release.
При разрешённом metadata-preflight подтвердить это; helper проверяет точный
source/image основного web и сохраняет сравнимые metadata. Дрейф — стоп,
не самостоятельное обновление/«исправление» основной beta.

## Новые ресурсы и отказ при коллизии

| Ресурс | Точное значение |
| --- | --- |
| Compose project / cluster_name | `marketplace-e208-20261007-01a1105a-r4` |
| Корень | `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-08-20261007-01a1105a-r4` |
| Network | `marketplace-e208-20261007-01a1105a-r4-private`, internal |
| Volume | `marketplace-e208-20261007-01a1105a-r4-data` |
| Контейнеры | project + `-postgres`, `-web`, `-controller` |
| БД только нового кластера | `mw_beta`, `test_mw_beta`, новая `mw_e208_01a1105a_r4_restore` |
| SQL-роли только нового кластера | `mw_beta_bootstrap`, `mw_beta_migrator`, `mw_beta_web` |
| Схема | новая пустая `mw_isolation`, owner migrator |
| Новый dump | `<корень>/backups/isolation-after.dump` |
| Протоколы | `<корень>/baseline.json`, `preserved-rehearsal.json`, `state/manifest.json` |

Имена `mw_beta`/ролей повторяются **только в отдельном новом PostgreSQL instance**:
guard оператора не расширяется ради теста. Глобально уникальны cluster_name,
project, network, volume, контейнеры и корень. Это не подключение к основной
mw_beta. Helper проверяет cluster_name при каждом административном входе.
Существующий путь/ресурс/роль/БД/dump — отказ, не удаление и не reuse.

Подготовщик проверяет отсутствие контейнеров, labels проекта, network, volume,
корня, новые файлы создаёт O_EXCL. При частичной ошибке сохранить всё созданное;
не повторять bootstrap/configure/scenario и не удалять marker ради повторения.
Перед тестами `test_database` отдельно отказывает при существующей test_mw_beta.

Старые E2-04–E2-07 БД/роли/restore/dumps, оба owner rehearsal и E2-07 rehearsal
сохраняются. Предусмотрено сравнение metadata трёх основных контейнеров и всех
трёх сохранённых rehearsal. Сохранённые стенды должны оставаться stopped. Дополнительно проверяется
сохранённый postgres R1 `marketplace-e208-20261006-01a1105a-postgres`: он должен
оставаться stopped, с теми же ID/image/mounts/StartedAt/network/ports. У R1
не осталось постоянных web/controller — configure запускался в --rm контейнере.
Также сохраняются stopped postgres/controller R2
`marketplace-e208-20261007-01a1105a-r2`; их metadata сравниваются до/после.
R2 web не создавался; его БД/роли/том/ключи не использовать в R4.
Так же защищены stopped postgres/controller R3
`marketplace-e208-20261007-01a1105a-r3` и его state/suite-events.jsonl (0600).

## Ресурсы, секреты и SQL-права

PostgreSQL 384 MiB/0.25 CPU, web 384 MiB/0.25 CPU, controller 256 MiB/0.25 CPU;
bootstrap отдельно 256 MiB/0.25 CPU. До начала минимум 2 GiB свободных RAM и диска.
Штатные connect/statement/lock timeout: 5/5/2 секунды. Тесты последовательные,
кроме явно заданных пар из двух соединений/потоков. Один suite не более 30 минут,
dump/restore не более 10 минут; всё окно не более 60 минут. При timeout/OOM,
нехватке ресурса или влиянии на соседние сервисы — остановить только новый стенд.

Без ports/ingress/Caddy, restart=no, internal network, read-only web/rootfs/source,
UID10001, cap-drop/no-new-privileges, logging=none. Никаких установки/build/pull.
Использовать только уже имеющиеся и сверенные immutable образы:

- Backend: `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`.
- PostgreSQL: `sha256:248efd5e58cd743f2a0e0daec8ea4649e5580145ec2a12e2345bc710d4a77201`.
- requirements.lock SHA256: `35cba592050150a0e5b1f68adc36d3f1c0871ceec79efc6c7f8e4a925fb34e60`.

Разрешение этого плана должно охватывать создание **только нового синтетического**
набора secrets в новом корне и его штатное использование соответствующими
процессами: DB bootstrap/migrator/web passwords, Django key, MFA key и новый
32-byte isolation_signing_key. Их значения не просматриваются агентом,
не печатаются/не записываются в аргументы, протоколы, Git или HTTP-traces.
Файлы 0600, каталоги 0700; web получает только собственный DB password,
Django/MFA/isolation keys. Migrator/administrator credentials в web отсутствуют.
Все адресаты example.invalid, доставка locmem. Реальные ключи/пароли, старые
envelopes, Telegram, передача ключа и K3 не входят в план.

Bootstrap создаёт только пустую private schema AUTHORIZATION migrator; широкое
CREATE DATABASE/schema право migrator не выдаётся. Web сохраняет точные column
ACL E2-07 и не получает DDL/TEMP/SET ROLE/BYPASSRLS/владение/операторские назначения.
Добавляются только USAGE mw_isolation и EXECUTE allowed/claims/export_cabinet.
HMAC/key/record_allowed не становятся публичным API. Provisioning ключа и
проверка контракта выполняются транзакционно из опубликованного helper.

## Последовательность после публикации и отдельного разрешения

SSH запускать с `-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=3`.
Подтверждённого диагноза сетевого разрыва R2 нет; keepalive уменьшает риск idle
разрыва, но не считается доказанным исправлением транспорта. Новый опубликованный
runner выводит только JSON-события и heartbeat не реже 30 секунд ожидания,
синхронно сохраняет их (0600, O_EXCL, fsync) в новом
`<root>/state/suite-events.jsonl`. Сырые stdout/stderr дочернего теста, SQL,
текст traceback, причины исключений и токены не записываются/не выводятся.
Разрешены только статические file/line/function кадров из трёх repository
test-пакетов; строки исходников, значения assert и locals отбрасываются.
После создания test_mw_beta опубликованный IsolationDiscoverRunner проверяет
точные database/cluster/session_user/current_user и пустую mw_isolation.key;
только в свежую test_mw_beta записывает тот же новый синтетический ключ проекта.
ACL/RLS не меняются. Затем реальный StatementSigner должен получить
`SELECT mw_isolation.claims() IS NOT NULL = true`; иначе suite не начинается.
Так исправляется отсутствие test-key provisioning, найденное после R3.
Совпадение с причиной конкретного assert R3 ещё не подтверждено.
Нельзя применять runner к mw_beta, старым БД или повторять при существующем ключе.

Фиксированный набор запускается с --failfast; deadline1750с, пропуски или
отсутствие полной сводки не считаются PASS даже при exit0. При обрыве SSH
остановить только новый стенд, сохранить и прочитать лишь этот sanitized
протокол; не повторять suite и не продолжать другие шаги автоматически.

До следующего блока уже должны быть отдельно разрешены Git/preflight и
подготовлен чистый immutable release. Эти команды сейчас не исполнялись.

```sh
set -eu
base=/home/adm_user/marketplace-workspace/beta
REV=409c71f65db53873183c6ffd8d059561c05185d2
release="$base/app/releases/$REV"
export SECURITY_SOURCE="$release/backend"
export SECURITY_IMAGE=sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72
dc() { timeout 1800 docker compose --project-name marketplace-e208-20261007-01a1105a-r4 --env-file /dev/null -f "$release/beta/deploy/compose.isolation-rehearsal.json" "$@"; }
python3 "$release/beta/deploy/prepare_isolation_rehearsal.py" --apply --revision "$REV"
dc config --quiet </dev/null
dc up -d --wait postgres </dev/null
dc run --rm -T bootstrap </dev/null
dc up -d controller </dev/null
dc exec -T controller python -m tools.isolation_rehearsal configure </dev/null
dc run --rm -T bootstrap python -m tools.isolation_rehearsal test_database </dev/null
dc exec -T controller python -m tools.isolation_test_runner </dev/null
dc exec -T controller python -m tools.isolation_rehearsal scenario </dev/null
dc up -d web </dev/null
dc exec -T web python -m tools.verify_isolation_web_runtime </dev/null
```

Остановиться на первом ненулевом exit; не продолжать остальные команды вручную.
Полный Compose config/ENV и подробные ошибки SQL/HTTP не печатать. PostgreSQL
не должен протоколировать SQL с параметрами; logging none не отменяет запрета
сохранять собственные request/response/cookie dumps.

В R4 controller создаётся один раз через `up -d`, а команды выполняются через
`exec -T`: итоговый metadata-verifier проверяет три постоянных контейнера.
Прежний `run --rm controller` не создавал проверяемый named controller.

Static `data_isolation.tests.test_preparation` требует полного дерева repository:
он запускается отдельно read-only `/source`, workdir `/source/backend`, в том же
имеющемся image, `--network none`, без любых secret mounts, с
`--settings=config.isolation_local_checks`. Не приписывать этот тест PostgreSQL
и не повторять ошибку E2-07 с backend-only mount. Legacy reverse-tests,
предполагающие отключение guards на заполненной схеме, не запускать как обход
нового запрета populated rollback; вместо них есть E2-08 MigrationTests.

## Обязательные критерии изолированного прогона

- Записать точный PostgreSQL version, source/image/lock, actual
  session_user=current_user=mw_beta_web; не SET ROLE из migrator.
- Все PostgreSQL тесты без skips. Новый real-role сценарий после операторского
  fixture действительно переподключается к web LOGIN; cached synthetic TOTP
  используется только тестовым клиентом, runtime-авторизация не mock-ается.
- SQL без подписи/с поддельным GUC закрыт; key/HMAC/DDL/SET ROLE недоступны.
  Тот же личный пользователь в двух организациях; SELECT без WHERE видит
  только подписанный кабинет, Cabinet — выбранную организацию.
  SQL view не разрешает UPDATE даже при отдельном change Grant.
- Реальные ClientCursor/current_query/HMAC совместимы; exception/savepoint
  rollback/reuse не портит соединение и не переносит authority. Сохранённый
  envelope не работает после rollback или на другом backend/transaction.
- HTTP/list/search/detail/change/export: неверные org/cabinet/record/filter,
  independent actions, CSRF, отзыв/новая выдача, прежняя ссылка остаётся закрытой.
  После committed Grant/member/user revoke живые сессии не сохраняют доступ.
- Регрессии MFA владельца/повышения, recovery без расширения Grant/снятия
  блокировки, архивирование, последний владелец, platform support expiry/revoke.
  Конкурентные сценарии нового текущего набора отдельно фиксируются, прежние
  E2-07 результаты не засчитываются. Сбой любого сценария — E2-08 не готова.
- Deferred last-owner и каскады реально работают с SECURITY DEFINER; invoker
  web-lock/web-subject guards остаются прежними. Проверить scope constraints
  вместе с RLS, а не вместо неё.
- Readiness, шесть подготовленных сетевых проверок; authenticated HTTP через
  настоящий SQL-login отдельно от network smoke. Browser/TLS PASS не заявляется.

## Backup/restore и безопасный откат

После успешного fixture остановить только новый web, убедиться в отсутствии
активных writers нового кластера. Не останавливать основные PostgreSQL.
Проверить отсутствие `<корень>/backups/isolation-after.dump` и
`mw_e208_01a1105a_r4_restore`; при наличии — стоп. Под новым bootstrap внутри
нового postgres, без shell tracing, создать custom pg_dump mw_beta в этот
новый файл, mode0600, timeout600. Проверить exit, ненулевой размер и SHA256.

Создать **новую** restore-БД owner mw_beta_migrator; немедленно REVOKE ALL ON
DATABASE … FROM PUBLIC. `pg_restore --exit-on-error` только в неё, timeout600.
Штатный bootstrap password читает только процесс pg_dump/psql внутри этого
нового контейнера через существующий secret mount; значение не выводится.
Исходная mw_beta не заменяется. Проверить `has_database_privilege` для web
CONNECT restore = false. Не выдавать временный CONNECT ради smoke.

```sh
set -eu
dc exec -T controller python -m tools.isolation_restore_check </dev/null
dc up -d web </dev/null
dc exec -T web python -m tools.verify_isolation_web_runtime </dev/null
python3 "$release/beta/deploy/prepare_isolation_rehearsal.py" --verify --revision "$REV"
dc stop web controller postgres </dev/null
```

Helper сравнивает все public-строки, private signing key только в памяти,
политики/функции/ACL, проверяет необратимость Grant, затем карантинирует все
восстановленные сессии/ссылки. Содержимое/отпечаток ключа не сохраняется в отчёт;
dump содержит чувствительные данные и остаётся закрытым. Проверка restore не
является разрешением открыть восстановленную БД или обновить основную beta.

Reverse/forward допускается только пустому test-сценарию; на заполненной области
reverse обязан отказать с сохранением строк и migration record. При любой ошибке
остановить **только новые** процессы, сохранить ресурсы/dump/секреты/evidence.
Не down -v, DROP, prune, не удалять/повторно использовать старые БД/роли/ключи,
не возвращать обычный pre-RLS/E2-07/E2-06 runtime. Очистка — отдельное решение.

## Что требует следующего отдельного решения

Успех этого стенда не разрешает main-beta rollout. Для него понадобятся свежие
metadata/backup/restore основной beta, точный переход ACL/schema/key, проверка
сохранения данных, штатный `compose.security-web.json` + SECURITY_SOURCE/IMAGE,
ограниченное окно остановки только web и отдельное разрешение. Старый base-only
и accounts overlay запрещены. До этого runtime cf6f4cc остаётся без изменений.

В итоговый протокол внести все exit/PASS/skips/failures, версии, время, ресурсные
ID и остановку, новый dump hash/restore result и неизменность старых контейнеров.
Не объявлять защищёнными отсутствующие business-cache/worker/storage/рабочий
экспорт. Статус E2-08 сохраняется «На проверке» до необходимых результатов;
E2-06 и отменённая K3 не пересматриваются этим планом.
