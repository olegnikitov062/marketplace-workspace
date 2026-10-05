# E2-07 — отдельный серверный план и факт исполнения

05.10.2026, Europe/Moscow. План исполнен после push Олега, прямой проверки публикации и отдельного «разрешаю» для `3369e3196753804655a7ae0cc9a845395545036e`. Факт исполнения и ограничения — `docs/E2-07_SERVER_RESULTS.md`, машинный протокол — `SYSTEM_GRANT_CHECKS.json`. Ниже сохранён исходный план; его предварительные формулировки относятся к моменту подготовки. Основная beta не обновлялась.

**Не повторять provisioning:** имена ниже теперь заняты сохранённым остановленным стендом. `bootstrap`, `configure`, `test_database`, `scenario` и создание dump/restore не являются идемпотентными. Новое выполнение/изменение объёма согласовывается отдельно после проверки текущего состояния.

Уточнения исполнения: PostgreSQL запускался через `up -d --wait postgres`; команды `run` выполнялись с `-T` и stdin из `/dev/null`, чтобы контейнер не потреблял последующие команды SSH. Два статических теста `test_preparation` требуют полного дерева Git; их следует запускать отдельно без сети/секретов, как записано в протоколе. Исторический полный запуск ниже дал 70 PASS и две ошибки отсутствующих файлов, не чистый exit 0. Серверные исходники не редактировались.

## Ревизия и стоп-условия

Перед началом локальной реализации непосредственно через GitHub проверена опубликованная beta `d6385c5d209aadaf864923be5205fdbdb6abc5be`. Она **не содержит E2-07**. После push Олега нужно повторить `git ls-remote --heads origin beta`, сверить полный SHA коммита реализации и определить полный REV для разрешения. До этого серверный план заблокирован публикацией и отсутствием разрешения; origin/beta недостаточно.

После отдельного разрешения: проверить чистоту только серверного marketplace repository, получить beta через Git fast-forward, создать новый immutable worktree `beta/app/releases/<REV>` только из опубликованного SHA. Никаких архивов исходников, SCP исходников, ручной правки серверного кода или Git push. Если release уже существует, проверить SHA/чистоту; не переписывать. Серверный подготовщик сверяет актуальную опубликованную beta, SHA release и SHA256 requirements.lock. Образы не собирать/не скачивать: только имеющиеся закреплённые dependency image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72` и PostgreSQL `sha256:248efd5e58cd743f2a0e0daec8ea4649e5580145ec2a12e2345bc710d4a77201`.

Последний подтверждённый основной runtime — `14d9f48cee6eb2a9d7eca9f029770af51c45b6d9`; это исторический факт. При будущем preflight проверить только безопасные metadata своих контейнеров и RO source mount. Не открывать основные key/passphrase/envelope и не проверять K3. При отличии состояния — остановиться до создания ресурсов и пересмотреть план.

## Только новые ресурсы

| Объект | Точное имя |
| --- | --- |
| Compose project | marketplace-e207-20261005-01a10b2d |
| Корень | /home/adm_user/marketplace-workspace/beta/rehearsals/e2-07-20261005-01a10b2d |
| Network | marketplace-e207-20261005-01a10b2d-private, internal=true |
| Volume | marketplace-e207-20261005-01a10b2d-data |
| Контейнеры | marketplace-e207-20261005-01a10b2d-postgres, -web, -controller |
| Одноразовые процессы | bootstrap и подготовщик новых синтетических секретов; только этот project/root |
| БД нового кластера | mw_beta, test_mw_beta, mw_e207_01a10b2d_restore |
| Роли нового кластера | mw_beta_bootstrap, mw_beta_migrator, mw_beta_web |
| Новый dump | <корень>/backups/access-after.dump |
| Metadata | <корень>/baseline.json, preserved-rehearsal.json; безопасные hashes/counts — отдельный новый протокол |

Имена mw_beta/mw_beta_web намеренно сохранены **в новом изолированном кластере**, чтобы не ослаблять штатный guard и operator-проверку фактической SQL-личности. Они не обозначают подключение к основной beta. Уникальность задают project/network/volume/cluster_name; все подключения требуют соответствующий cluster_name. Предложение первого обсуждения об отдельных глобальных именах заменено этим конкретным вариантом без расширения runtime guard. Совпадение любых новых ресурсов/БД/dump — стоп, не переиспользование и не удаление.

Существующие основной и test PostgreSQL, все БД/роли/restore E2-04–E2-06, оба owner rehearsal остаются нетронутыми и не запускаются. Подготовщик сохраняет metadata основной beta и обоих остановленных rehearsal; verify сверяет их после работы.

## Нагрузка и секреты

PostgreSQL 384 MiB/0.25 CPU, web 384 MiB/0.25 CPU, controller 256 MiB/0.25 CPU; bootstrap 256 MiB/0.25 CPU запускается отдельно. Перед стартом минимум 2 GiB свободной памяти и 2 GiB диска; при недостатке ресурсов остановиться. Контроллер по умолчанию завершает ожидание через час. Запуски тестов последовательные, кроме пяти ограниченных гонок по два соединения. Штатные connect/statement/lock timeout — 5/5/2 секунд. Не менять лимиты основной beta и других проектов.

Host-портов, ingress, Caddy и внешних отправок нет. Все сервисы без restart, logging=none; web read-only/UID10001, cap_drop ALL/no-new-privileges. Только новый комплект synthetic Django/MFA/DB secrets, 0600/0700. Web получает только свой DB password + Django/MFA key; migrator/bootstrap секреты в web не монтируются. Старые реальные ключи/пароли не читаются и не передаются. Установки зависимостей/плагинов и сетевые builds не входят в разрешение.

## Исполнимая последовательность после публикации и разрешения

Задать REV только полным SHA, прямо указанным в разрешении. `SECURITY_SOURCE` — его backend. Оболочка dc ниже относится **только к новому стенду**. Основной web по-прежнему требует штатный compose.security-web.json + SECURITY_SOURCE + SECURITY_IMAGE; base-only/accounts overlay недопустимы. Новый standalone compose воспроизводит security stack с собственными секретами; основной overlay с основными mounts на него не накладывать.

```sh
base=/home/adm_user/marketplace-workspace/beta
# REV=<полный опубликованный SHA, отдельно разрешённый Олегом>
release="$base/app/releases/$REV"
export SECURITY_SOURCE="$release/backend"
export SECURITY_IMAGE=sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72
dc() { docker compose --project-name marketplace-e207-20261005-01a10b2d --env-file /dev/null -f "$release/beta/deploy/compose.access-rehearsal.json" "$@"; }
python3 "$release/beta/deploy/prepare_access_rehearsal.py" --apply --revision "$REV"
dc config --quiet
dc up -d postgres
dc run --rm bootstrap
dc run --rm controller python -m tools.access_rehearsal configure
dc run --rm bootstrap python -m tools.access_rehearsal test_database
dc run --rm controller python manage.py test access_control.tests account_security.tests.test_http --keepdb --noinput --verbosity=1
dc run --rm controller python -m tools.access_rehearsal scenario
dc up -d web controller
dc exec -T web python -m tools.verify_access_web_runtime
python3 "$release/beta/deploy/prepare_access_rehearsal.py" --verify --revision "$REV"
```

`test_database` отказывает при существующей test_mw_beta; --keepdb сохраняет только предварительно созданную этим новым запуском БД. После отказа повтор требует проверки фактического состояния, не удаления marker/fixture и не reset. Тесты должны пройти без PostgreSQL-пропусков. Сценарий limited LOGIN создаёт fixture migrator-процессом, затем переподключает Django как настоящий session_user=current_user=mw_beta_web; SET ROLE из владельца не считается проверкой. Он проверяет выдачу/скачивание/отзыв/повторную выдачу, CSRF, админскую поддержку, реальный operator CLI и отрицательные SQL. Ошибки выводятся только безопасной категорией; никакого дампа request/response/cookies/outbox.

SQL-контракт строго поколоночный: `backend/tools/access_web_grants.py`; миграции/оператор отдельны от web. В новом пустом кластере SELECT ограничивается перечисленными таблицами, PUBLIC TEMP/CONNECT закрываются; platform assignment не записывается web. Проверить запрет создания таблиц/TEMP, UPDATE идентичности и platform assignment, DELETE Grant, TRUNCATE, изменения django_migrations и SET ROLE migrator. Проверить web-subject trigger против создания platform Grant, составные FK, необратимость и последнего владельца. RLS не заявляется.

## Новый dump/restore

Остановить только новый web/controller перед снимком, чтобы зафиксировать завершённый fixture. PostgreSQL продолжает работать. Предварительно проверить отсутствие имени restore и файла dump; следующий блок повторно проверяет оба и отказывает. Выполняется внутри нового postgres, с его новым синтетическим паролем; shell tracing запрещён.

```sh
dc stop web controller
dc exec -T postgres sh -eu -c '
  umask 077
  export PGPASSWORD="$(cat /run/secrets/db_bootstrap_password)"
  test ! -e /backups/access-after.dump
  test "$(psql -U mw_beta_bootstrap -d mw_beta -Atc "SELECT count(*) FROM pg_database WHERE datname='"'"'mw_e207_01a10b2d_restore'"'"'")" = 0
  pg_dump -U mw_beta_bootstrap -d mw_beta --format=custom --file=/backups/access-after.dump
  createdb -U mw_beta_bootstrap -O mw_beta_migrator mw_e207_01a10b2d_restore
  psql -v ON_ERROR_STOP=1 -U mw_beta_bootstrap -d mw_beta -c "REVOKE ALL ON DATABASE mw_e207_01a10b2d_restore FROM PUBLIC"
  pg_restore -U mw_beta_bootstrap -d mw_e207_01a10b2d_restore --exit-on-error /backups/access-after.dump
  sha256sum /backups/access-after.dump
'
dc run --rm controller python -m tools.access_restore_check
```

После restore helper сравнивает все public-таблицы в памяти, не выводит строки; проверяет отказ снятия revoked_at у восстановленного Grant, затем переключается только на именованную restore-БД и применяет карантин E2-06. Все восстановленные сессии/ссылки должны быть отозваны. Историческая БД не знает об отзывах после снимка: ни восстановление пароля, ни новое подключение MFA не заменяют отдельную сверку актуальных полномочий перед открытием доступа. Исходная mw_beta и dump сохраняются. Новый synthetic MFA key остаётся только в новом корне, без передачи/проверки реального ключа и без повторения K3.

## Завершение и откат

Снова запустить только новые web/controller для финального runtime/metadata verify, затем остановить три новых сервиса. Не применять down -v, DROP, prune, удаление старых файлов или restore поверх живой БД. Новые volume/network/БД/dump/секреты сохранить для расследования и отдельно согласуемой очистки. В случае сбоя на любом этапе — остановить только новые процессы, зафиксировать безопасную категорию/код и состояние; не продолжать слепым повтором provisioning или расширением SQL-полномочий.

Откат схемы проверяется suite на test_mw_beta: guard reverse/forward сохраняет отозванные строки; zero только на пустой access-схеме. Не откатывать рабочую заполненную схему автоматически. Основная beta не меняется, её откат не нужен. Будущее внедрение E2-07 в основную beta требует отдельного плана с её актуальными backup/ACL/maintenance и отдельного разрешения, даже после успеха этого стенда.

После исполнения записать фактический REV, версию PostgreSQL, количества PASS/skips, SQLSTATE отказов, ID новых ресурсов, restore/dump результат, ограничения, неизменность сохранённых контейнеров и остановку новых процессов. До такого протокола E2-07 остаётся «На проверке». Технический PASS рабочего экспорта, RLS, production или новой проверки K3 не заявляется.
