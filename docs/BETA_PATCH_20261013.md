# Подготовка закрытого обновления beta на Selectel

Дата: 13.10.2026, Europe/Moscow (UTC+3). Подготовка, не выкладка.

## Итог и границы доказательств

Подготовлены Python **3.14.8** и Django **5.2.18**. Major Python/Django/PostgreSQL сохранены.
Другие зависимости не обновлялись. Код приложения, миграции, MFA, Grant и RLS не менялись.
На постоянном Selectel выполнено только чтение. Commit/push, перезапуски, миграции,
создание владельцев/организаций/подключений, отправки и включение обработчиков не выполнялись.

**Допуск к выкладке пока закрыт:** на ноутбуке нет Docker CLI/Engine и PostgreSQL 17;
отдельный Linux Docker endpoint не предоставлен. На постоянном Selectel разрешено
только чтение, поэтому он не использован для сборок и создания тестовых ресурсов.
Linux-образ не собран; его image ID/digest ещё не существует. PostgreSQL-проверки
новой комбинации версий, restore и полный браузерный auth lifecycle не выполнены.
Локальные проверки и статический контроль комплекта не заменяют эти этапы.

## Было и подготовлено

| Компонент | Было → подготовлено | Как проверено | Что осталось |
|---|---|---|---|
| Python | Selectel 3.14.7 → 3.14.8 | Официальный выпуск, digest Registry; переносимый Windows 3.14.8 с проверенным SHA-256 | Собрать и запустить Linux amd64 образ |
| Django | Selectel 5.2.17 → 5.2.18 | Официальный выпуск/PyPI; hash-locked установка, pip check, 25 тестов без БД | Полный PostgreSQL/HTTP набор на новом образе |
| PostgreSQL | 17.11 → 17.11 | Чтение реальной web-роли; версия образа тестовой БД сверена с Registry | Чистые миграции, upgrade искусственного состояния и restore |
| MFA/Grant/RLS | Сохранены | Selectel: 28 FORCE RLS таблиц, financial ACL contract PASS, опасные флаги роли отсутствуют | Отрицательные HTTP/SQL тесты новой сборки в двух организациях |
| Frontend | Прежняя заготовка → прежняя заготовка | TypeScript/Vite build PASS; Chrome отображает ожидаемый экран | Рабочих пользовательских экранов в этой сборке нет |

## Исходное состояние, подтверждённое чтением

- Git: ветка `beta`, HEAD `c47547df6d543b1fcd02aac5dd830019abeb1a2d`.
- До работы уже изменены CHANGELOG.md и файлы docs/design; были новые
  docs/design/organization-scope.js и docs/design/sheet-style.css. Их исходные хеши
  сохранены, файлы дизайна не редактировались. Начальный текст журнала сохранён.
- Selectel: Compose project `oleg-closed`, `/srv/oleg/closed-20261013/compose.json`.
  Backend — `closed-beta-web` / service `beta-web`, БД — `closed-beta-db` / `beta-db`.
- Все 161 Python-файл работающего `/workspace` совпали с местным backend по SHA-256.
  Прежние документы E2-08 описывают исторический сервер; на Selectel уже применены
  financial migrations и **28**, а не 27 FORCE RLS таблиц. Pending migrations = 0.
- Реальные session_user/current_user: `mw_beta_web`; база `mw_beta`.
  SUPERUSER, BYPASSRLS, CREATEDB, CREATEROLE, REPLICATION = false;
  членство в `mw_beta_migrator` = false. Штатный financial_web_contract.verify PASS.
- Python 3.14.7, Django 5.2.17, PostgreSQL 17.11. На момент чтения beta healthy.
  MemAvailable около 14.1 GiB, свободно около 106 GiB; это снимок, не будущий допуск.
- Повторное чтение в конце подтвердило прежние image IDs/StartedAt обоих beta
  контейнеров и healthy. Исходный backend также Debian12 bookworm; смены дистрибутива нет.
- По сохранённому закрытому Compose: beta-web только в internal beta network,
  без собственных host ports; gateway остаётся существующим закрытым маршрутом.
  БД также подключена к backup network, порт БД только 127.0.0.1:5435.
  Конфигурацию общих сетей/шлюза/backup этим обновлением не менять.

Доказательства: `artifacts/beta-update-20261013-130650/server-readonly.json`,
`registry-evidence.json`, прежние RESULT-20261013.txt/RUNBOOK-20261013.txt и
closed-20261013/compose.json в selectel-preparation. Старые отчёты сохранены.
Реальные HTTP login GET на Selectel не выполнялись: они могут создавать сессии.

## Версии, совместимость и образы

Python 3.14.8 опубликован 30.09.2026 как security maintenance release.
Среди исправлений — SSLContext, обработка архивов и urllib credential handling.
Это обоснование обновления ветки, не утверждение об эксплуатации CVE в beta.
Источник: https://www.python.org/downloads/release/python-3148/

Django 5.2.18 от 06.10.2026 исправляет DoS в обработке языковых кодов/HTTP-заголовков,
проверки model formsets и GeoDjango. Изменён парсер параметров HTTP-заголовков —
формы, CSRF и MFA должны пройти регрессию. GeoDjango не включён в INSTALLED_APPS.
Источник: https://docs.djangoproject.com/en/5.2/releases/5.2.18/

Django 5.2 официально поддерживает Python 3.14 начиная с 5.2.8:
https://docs.djangoproject.com/en/5.2/faq/install/
Для новой Django сохранённые asgiref/sqlparse удовлетворяют metadata requirements.
Сопутствующих обновлений не потребовалось; полный CVE-аудит всех OS/Node/Python
пакетов не проводился и этим отчётом не заявляется.

| Назначение | Точная фиксация |
|---|---|
| Новый базовый Python | `python:3.14.8-slim-bookworm@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83` |
| Его Linux amd64 manifest | `sha256:a66d3a463d0be3cc537c269b0d3418746dda512417a975559a0eaa8a6406baaf` |
| Прежний базовый Python | `python@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56` |
| Тестовый PostgreSQL 17.11, без обновления | `postgres@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652` |
| Установленный Selectel beta-web | `sha256:f24a05184dc8a4e10247fd892abbe7bf4073712f8a23f86aa6097bbb15625d95` |
| Установленный Selectel beta-db с pgBackRest | `sha256:012846bf14bd9fa65bd968b3231d4ba44715515d7489c2747ae76c14dd0c45e1` |
| Неизменный frontend build base | `node@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6` |

Нельзя заменить установленный beta-db обычным тестовым postgres image: установленный
образ содержит pgBackRest. Он не требует изменений для Python/Django patch.
Новый backend image ID фиксируется **после** сборки; не подставлять выдуманный digest.
Локальные теги стендов уникальны, runtime получает разрешённый через inspect image ID.
`latest` не используется.

Python pins после подготовки: Django5.2.18, DRF3.18.1, psycopg/psycopg-binary3.3.6,
gunicorn26.2.0, django-two-factor-auth1.18.1, django-otp1.7.3, cryptography50.0.2,
asgiref3.12.1, sqlparse0.6.0, tzdata2026.4, django-formtools2.7,
django-phonenumber-field8.5.0, qrcode8.2, cffi2.1.1, pycparser3.0;
colorama0.4.6 только Windows. Точные wheel hashes — backend/requirements.lock.
Django wheel SHA-256: `92ed81d500be6408ecd704d7bd1366c534f30427bffcc63c5fefb129561aec7c`.

Frontend package.json/package-lock.json сохранены: React/React DOM19.3.0,
TypeScript7.0.2, Vite8.3.1, plugin-react6.1.1, types React/DOM19.3.0.

Места фиксации просмотрены: backend/Dockerfile, requirements.in/lock,
beta/deploy/images.lock.json, beta/deploy Compose и beta.py/reproduce.py,
frontend/Dockerfile и package.json/package-lock.json, local/production deploy,
старые prepare_*rehearsal.py и SYSTEM_STARTUP/RUNBOOK.
Исторические rehearsal image/lock hashes и заголовки старых миграций не переписаны:
они описывают прежние проверки и не являются рецептом новой выкладки Selectel.

## Выполненные проверки

1. Новое отдельное venv; установка полного lock с `--require-hashes --only-binary=:all:`.
   `pip check`: PASS. Глобальные Python/пакеты/плагины не обновлялись.
2. Переносимый Python3.14.8 скачан с python.org внутрь artifacts, SHA-256 проверен.
   На нём с Django5.2.18: **25 тестов, 0 ошибок, 0 пропусков**. Только существующие
   test_guard, isolation test_runner/test_preparation, financial test_preparation,
   key_envelope_check. DATABASES использует dummy backend, подключения к БД нет.
   Никаких SQLite-доказательств. При первом запуске были 5 ошибок настройки runner:
   не зарегистрированы приложения для MigrationLoader и sandbox запрещал Temp.
   После регистрации штатных приложений и отдельного temp внутри artifacts все 25 PASS;
   код приложения и тесты для этого не менялись, защиты не отключались.
3. Закреплённые Linux amd64 CPython3.14/abi3 wheels скачаны и сверены с lock hashes.
   Это доступность артефактов, не исполнение Linux-кода. В download набор попал
   Windows-only colorama из-за платформы запуска pip; в Linux install marker его исключает.
4. Все 44 встроенных Django migration .py одинаковы между5.2.17 и5.2.18.
   Собственные миграции не менялись; изменения схемы не ожидаются.
5. `npm run build`: TypeScript и Vite PASS. Chrome: ожидаемые три текстовых элемента,
   страница «Основа подготовлена». Единственное сообщение console — favicon.ico404;
   посторонний UI-код для этого не менялся. Снимок:
   `output/playwright/beta-patch-20261013.png`. Браузерная сессия закрыта.
6. Комплекты fresh-final/upgrade-final: манифесты513 файлов каждый, AST487 Python-файлов
   каждый, JSON/internal network/секреты web/отсутствие ports/restart=no и `bash -n`: PASS.
   Чистый image-source побайтно совпадает с текущим backend. Никаких Docker-команд
   из run.sh локально или на Selectel не исполнялось.
7. Git diff проверен с учётом существующих Windows CRLF (`core.whitespace=cr-at-eol`);
   исходные изменённые файлы дизайна сохранены, HEAD прежний, журнал дополняется.

## Воспроизводимый комплект изолированных проверок

Генератор: `tools/prepare_beta_patch_checks.py` — стандартная библиотека Python,
не требует новых пакетов. Он только формирует файлы, не подключается к серверу.

Готовые окончательные каталоги:

- `artifacts/beta-update-20261013-130650/fresh-final`;
- `artifacts/beta-update-20261013-130650/upgrade-final`.

Каталоги fresh/upgrade и fresh-v2/upgrade-v2 — сохранённые промежуточные варианты;
для запуска использовать только **-final** с соответствующим манифестом.

Переносимый комплект обоих окончательных каталогов:
`artifacts/beta-update-20261013-130650/beta-isolated-checks-20261013.tar.gz`,
SHA-256 `383f4ac265c767ae25a40df24003471ee5eea75a8e64f16187c33a6193c47a19`.
Прочитанные обратно архивы комплекта и исходников совпали с вложенными манифестами.

Нужен отдельный Linux amd64 Docker Engine + Compose v2/v5, Python3 и стандартные
coreutils; административный доступ только к этому одноразовому стенду. Интернет нужен
сборщику для закреплённых image/wheels, не тестовому приложению. Желательно >=4GiB RAM
и >=10GiB диска; фактические лимиты контейнеров не увеличены ради прохождения тестов.
Не устанавливать эти инструменты на ноутбук без отдельного согласования.
Запуск на постоянном Selectel запрещён; скрипт также отказывается при наличии
контейнера closed-beta-web. Отсутствие такого имени само по себе не является разрешением.

На отдельном разрешённом стенде, в каждом скопированном каталоге:

```sh
# Проверить source-manifest.json и отсутствие старых ресурсов этого run-id.
# Только один сценарий за раз. Не применять на постоянном Selectel.
sudo sh run.sh
```

run.sh фиксирует ID двух собранных образов в image-ids.txt. Новый образ собирается
из чистого image-source без venv, секретов, незарегистрированных файлов и тестовых
инъекций. Baseline отличается только прежними Dockerfile/requirements.in/lock.
Для проверки монтируется отдельная копия backend: изменены только имена/маркеры
стенда и добавлены тестовые probes. Реальный код приложения в image-source неизменен.

Сценарии создают новые отдельные project/network/volume, секреты и БД. Коллизия любого
имени или каталога — остановка, без удаления. Bootstrap superuser используется только
для создания тестовых ролей/БД и dump/restore. Миграции — штатный migrator.
Существующий suite с transaction/migration тестами использует ограниченный migrator;
отдельный scenario явно переподключается как реальный `mw_beta_web`. Нельзя считать
весь suite проверкой web-прав: именно scenario/SQL probes подтверждают этот контракт.

Контрольный состав:

- fresh: штатные миграции на новой17.11, 28 FORCE RLS/ACL, штатный financial_test_runner;
- upgrade: тот же исходный код на прежних зависимостях создаёт искусственное состояние;
  после смены только dependency image сравниваются все строки, последовательности,
  schema/ACL/policies/functions/triggers и отсутствие новых migrations;
- существующие MFA/session/CSRF/logout/recovery/Grant/default-deny HTTP tests;
- две искусственные организации/кабинеты, реальные SQL LOGIN, отрицательные HTTP/SQL
  и подписанный/неподписанный контекст, запрещённые ALTER RLS/SET ROLE migrator;
- дополнительный patch_auth_probe: invitation/reinvite/accept, одноразовый reset,
  logout/CSRF/foreign organization/default-deny под web LOGIN; письма только locmem
  и example.invalid, токены/пароли остаются в памяти;
- реальный Gunicorn, live/ready и шесть сетевых HTTP probes; TCP egress deny probes;
- новый synthetic dump, восстановление в отдельную БД с запретом web CONNECT,
  строгое сравнение данных/метаданных, quarantine восстановленных полномочий.

Нельзя делать вывод об успешности этих сценариев до исполнения. Дополнительный
patch_auth_probe также ещё не проверен на PostgreSQL. Старый E2-09 R4 имел незакрытые
проверки; прежние результаты не объявлены PASS для этого комплекта. Любой его отказ
нужно локализовать, сохранив защиты, а не исключать тест/повышать права/таймауты.
При ошибке run.sh останавливает только свой web/controller/postgres; тома, ключи,
dump и обезличенные suite/restore events сохраняются. Никакого down-v/prune.

Полный браузерный MFA onboarding/recovery не воспроизводился: нет отдельного
живого backend. Приложенные HTTP tests не заменяют этот браузерный этап.
Рабочий экспорт файлов/cache/worker и бизнес-экраны остаются вне реализованного scope.

Исходный release archive (не Docker-образ):
`artifacts/beta-update-20261013-130650/beta-patch-source-20261013.tar.gz`.
SHA-256: `8fd362b9f25e6e7bb3cd0de6d2de2a616c56d07f1889456cff364157f9544b1e`.
Архив содержит только backend и images.lock плюс release-manifest.json;
timestamps/uid/gid фиксированы. Пины и hashes воспроизводят входы сборки;
побайтовое равенство двух Docker images без отдельной проверки не обещается.

## Конкретный план закрытой выкладки — для отдельного согласования

Это план будущей операции. Ни одна изменяющая сервер команда ниже не выполнена.

1. **Допуск.** Оба окончательных стенда должны завершиться без FAIL/skips; сохранить
   source manifest, image ID, pip check, версии, migration plan, SQL/HTTP/restore
   evidence и результат браузерного MFA сценария. Собрать финальный backend из
   того же чистого source archive; сверить с image-source проверенного стенда.
   Зафиксировать фактический immutable image ID, сохранить Docker image archive и
   checksum. Отдельно согласовать этот конкретный ID и окно обновления.
2. **Preflight Selectel только чтением.** Сверить oleg-closed, compose, current
   beta-web/beta-db IDs из таблицы, 161 source hash, migrations, 28 FORCE RLS и
   web-role contract. Зафиксировать ID/StartedAt/mounts/networks/ports всех соседних
   контейнеров без Env/секретов. При расхождении baseline — остановиться и пересмотреть
   diff. Проверить MemAvailable>=2GiB и free disk>=10GiB, отсутствие backup lock,
   OOM, новых подключений/интеграций, ожиданий миграции и неизвестных писателей.
3. **Checkpoint только beta.** Остановить исключительно service beta-web, сохранив
   закрытый gateway и работающую БД. Убедиться в отсутствии beta-писателей.
   Создать новую beta-specific копию БД со штатной stanza=beta и новым checkpoint ID,
   не запускать общий backup.py full для всех БД. Команды ниже выведены из текущего
   backup.py, но ограничены beta; выполнять в отдельной root-shell только в будущем
   согласованном окне, с `set -eu` и без `set -x`:

   ```sh
   exec 9>/run/lock/oleg-closed-backup.lock
   flock -n 9
   docker exec -u postgres closed-beta-db pgbackrest --stanza=beta check
   docker exec -u postgres closed-beta-db pgbackrest --stanza=beta --type=incr --no-expire-auto backup
   docker exec -u postgres closed-beta-db pgbackrest --stanza=beta --output=json info
   ```

   Сохранить label именно новой завершённой копии; отсутствие label/ошибки архиватора — STOP.
   `--no-expire-auto` отключает expire только этой команды, не будущую штатную retention.
   После окончания backup освободить FD9 (`exec 9>&-`), не держать общий lock всё окно
   обновления. Сохранить независимый checkpoint до будущего expire. Не выводить
   connection/secrets. Сохранить
   globals/ownership/ACL, metadata контейнера, текущий compose и старый image archive.
   Защитить checkpoint от удаления очередной retention, учесть дополнительный размер.
4. **Конфигурация и ключи.** Отдельный закрытый зашифрованный beta checkpoint включает
   db_web/migrator connection material, Django/MFA/isolation ключи, конфигурацию
   резервирования и мониторинга, mapping тома и оба image ID. Файлы0600/каталоги0700,
   ключ расшифрования отдельно, секреты не в Git/отчёте/CLI. Проверить checksum,
   чтение независимой копии и расшифрование в новый закрытый staging без вывода значений.
5. **Проверка восстановления до смены образа.** Восстановить beta в новый том/каталог
   PostgreSQL17.11, без host ports, archive_mode=off, restart=no и приложений-потребителей.
   Не использовать beta-data. Сверить rows/sequences/schema/owners/ACL/functions/RLS,
   независимость MFA/isolation/Django keys и отсутствие web CONNECT у restore-БД.
   При неуспехе оставить закрытый старый beta-web либо остановленным по согласованному
   решению; новый образ не запускать. Исторический restore-final.py целиком не запускать:
   он содержит этапы первичного наполнения, а не только restore.
   Для restore выбрать новый `beta-patch-restore-<checkpoint>` и новый одноимённый
   `-data` volume, сначала проверить отсутствие обоих. Использовать установленный
   beta-db image из таблицы, secret config beta-pgbackrest.conf read-only и сеть
   oleg-closed_backup только для скачивания. Команда pgBackRest внутри одноразового
   процесса: `--stanza=beta --set=<NEW_BACKUP_LABEL> --type=immediate --target-action=promote restore`.
   Никакого `--delta`, повторного использования тома или restore на beta-data.
   Для replay необходимых WAL временный экземпляр также может требовать backup network;
   после `pg_is_in_recovery()=false` отключить её и проверять через docker exec без сети.
   Не объявлять restore с network=none рабочим до проверки наличия всех WAL.
   Параметры backup/restore сверены по https://pgbackrest.org/command.html.
6. **Только beta-web.** Новый override Compose должен содержать единственное изменение:
   services.beta-web.image = согласованный `sha256:<NEW_IMAGE_ID>`.
   Этот placeholder не является готовым ID. Предварительно сравнить полностью merged
   Compose; networks/secrets/mounts/limits/command/labels прочих компонентов неизменны.
   Проверить, что metadata project остаётся oleg-closed, исходный compose тот же.

   ```sh
   docker compose --project-name oleg-closed \
     -f /srv/oleg/closed-20261013/compose.json \
     -f /srv/oleg/closed-20261013/beta-patch-APPROVED-ID.json \
     up -d --no-deps --pull never beta-web
   ```

   Команда применяется только после отдельного разрешения и checkpoint/restore PASS.
   beta-db, gateway, frontend, WB/Airflow/FBS не пересоздавать. Общий compose up запрещён.
7. **Миграции.** Ожидаемый plan пуст: свои миграции и44 Django migration files не
   изменены. В новой сборке выполнить read-only MigrationExecutor plan под штатным
   подключением. Любая pending migration — STOP; не выполнять неожиданную схему.
   Если появится обоснованная необходимость изменения схемы, подготовить отдельный
   reviewed plan под migrator с проверенным restore, не запускать bootstrap/provision.
8. **Проверка после запуска.** Python3.14.8/Django5.2.18, pip check, readiness200,
   реальный web LOGIN/role flags/no migrator membership, точный ACL/RLS contract,
   MFA/Grant enabled, внешние flags=false, прежний loopback access и internal network.
   Только разрешённые закрытые анонимные HTTP проверки; создание даже тестовых сессий
   на постоянной БД учитывать как будущую разрешённую запись. Межорганизационные
   разрушающие probes — исключительно на изолированном клоне, не в основной БД.
   Соседние container IDs/StartedAt/volumes должны совпасть с checkpoint.
9. **Backup и мониторинг.** Проверить beta stanza, WAL archive, доступность независимой
   копии, последний успешный restore, штатные сроки freshness/пороги и отсутствие новых
   ошибок oleg-health. Сам монитор/его таймеры/Telegram-настройки не менять. Отправка
   нового тестового сообщения отдельно разрешается. Наблюдать health/5xx/OOM/БД минимум
   15 минут. Проверить следующую штатную beta backup и свежесть мониторинга;
   только после этого закрыть change record, сохранив предыдущий checkpoint.

## Неуспех, остановка и откат

STOP до переключения: не пройдены изолированные тесты/restore, неизвестный образ,
drift исходного кода/Compose/схемы, нехватка ресурсов, неработающий backup, расширение
SQL-прав, отключённые MFA/Grant/RLS, открытый egress/public listener, живые обработчики.

STOP после переключения: readiness не200 более120с, login/CSRF/MFA regression,
неожиданный5xx, OOM, потеря данных, изменение ACL/RLS, миграция вне плана, изменение
соседних контейнеров, сбой beta backup/WAL/мониторинга. Не исправлять это выдачей
SUPERUSER/BYPASSRLS, отключением MFA/RLS или запуском старого pre-Grant кода.

Безопасное первое действие — остановить **только beta-web**. БД/том/ключи сохранить.
При подтверждённо неизменной схеме, совместимых данных и правах согласованный откат
может вернуть ровно прежний image ID `f24a0518…`, с теми же MFA/Grant/RLS/keys/networks.
Это текущий защищённый Selectel образ, не старый E2-03/E2-05 fallback.
Возврат старого образа возвращает прежние patch-уязвимости; оставить режим закрытым.

Если схема или данные изменились/повреждены, старый образ сам по себе не является
откатом. Оставить web остановленным, сохранить failed state, восстановить checkpoint
в **новый** том вместе с согласованными ключами/config/code, проверить quarantine
сессий/permits/recovery и текущие отозванные полномочия. Переключение mapping БД или
восстановление постоянной базы требует отдельного разрешения. Автоматический reverse
migrate, восстановление поверх beta-data, возврат старых прав и удаление failed тома
не предусмотрены. RPO — согласованный checkpoint до stop, не произвольная старая копия.

## Изменённые файлы и локальный откат

Существующие файлы:

- backend/Dockerfile — новый exact Python base;
- backend/requirements.in — Django5.2.18;
- backend/requirements.lock — Django5.2.18 и новый wheel hash, остальные pins/hashes сохранены;
- beta/deploy/images.lock.json — тот же новый Python base;
- CHANGELOG.md — только добавленные записи текущей работы.

Новые файлы: tools/prepare_beta_patch_checks.py, docs/BETA_PATCH_20261013.md,
выходные artifacts/beta-update-20261013-130650/**, output/playwright/beta-patch-20261013.png,
связанные .playwright-cli page/console files и внешняя датированная копия отчёта.
Точный перечень/хеши файлов artifacts фиксируется в artifact-inventory.json;
generated venv/runtime/wheels не добавляются в Git. Реальные секреты не копировались.

Исходные копии: `.change-backups/beta-update-20261013-130650/`; manifest.json содержит
начальные хеши местной работы. Перед откатом сравнить текущие файлы с итоговым
change manifest, сохранить поздние изменения и вернуть только четыре изменения pins
из копий. CHANGELOG не заменять: дописать отмену. Новые файлы можно удалить только
если их хеши совпадают, они нигде не используются и в них нет поздней работы.
Никаких git reset --hard/git clean; прежние docs/design и чужие artifacts сохранить.
