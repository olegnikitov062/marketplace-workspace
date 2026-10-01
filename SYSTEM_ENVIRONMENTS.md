# E2-02 — разделение локальной, beta и production сред

Дата подготовки: 30.09.2026, Europe/Moscow (UTC+3). Автор решения — Олег. Основание: принятое D1, SYSTEM_ARCHITECTURE.md, разделы 2.1, 2.2, 3 и 3.1. Статус задачи находится только в SYSTEM_PLAN.md. Разделы 1–11 — историческая подготовка E2-02. Фактический запуск и проверки E2-03 — раздел 12 и SYSTEM_STARTUP.md.

## 1. Владение файлами и каталоги

Путь `C:/Users/krolo/Documents/marketplace-workspace` перед созданием отсутствовал; существующие файлы не перезаписывались. Первоначально там было 15 перечисленных ниже файлов; текущий перечень — change-manifest.json E2-03. С 30.09.2026 документы плана/D1/E2-02 и действующий журнал находятся в `C:/Users/krolo/Documents/marketplace-workspace/`; это единственный актуальный комплект. История журнала в старом Finkos сохранена с указателем на новое место. D1 не менялось; его фразы «не создано» описывают момент принятия E2-01, нынешнюю подготовку фиксирует этот документ.

Серверная структура **будущая**, верхний каталог строго `/home/adm_user/marketplace-workspace/`, внутри `beta/` и `production/`. Для каждого окружения:

| Путь относительно окружения | Назначение и владелец |
| --- | --- |
| app/frontend/, app/backend/ | Код и статический dist проверенной сборки; deployment owner, приложение только читает. Сейчас отсутствуют |
| deploy/ | Неактивные шаблоны Compose/Caddy; deployment owner, без секретов |
| config/environment.policy.json, config/runtime.env | Только своя конфигурация, вне Git; каталог 0700, файлы 0600; доступ администратора конкретной среды |
| config/secrets/ | Разные DB passwords, Django secret, позднее TOTP encryption/recovery keys; сейчас отсутствует. Точечная выдача process UID, не chmod 777 |
| data/postgres/ | Bind mount только PostgreSQL данного окружения; UID образа уточняется после выбора digest, не UID web |
| data/exports/, data/mail/ | Временные экспорты и файловый приёмник тестовых писем; UID 10001 приложения, вне web root |
| logs/web/, logs/worker/ | Журналы только этой среды, без request payload, ключей, получателей и персональных данных |
| backups/ | Локальные штатные pg_dump/basebackup перед внешним переносом; закрытый доступ, имена включают среду, дату и версию; ключи отдельно |

Локально та же принадлежность внутри `C:/Users/krolo/Documents/marketplace-workspace/local/`, дополнительно `data/postgres-test/` для отдельного тестового экземпляра. Локальные Windows ACL проверяются отдельно; Linux chmod не является их проверкой. Рабочие data/config/logs/backups не включаются в сборку. Новый `.gitignore` исключает runtime config, app (пока только резерв будущего размещения), data/logs/backups; перед E2-03 исключение app пересмотреть под фактическую структуру исходников с журналом. Секреты не создавались. Docker images и container stdout находятся в системном каталоге Engine, Caddy и внешние копии — согласованные исключения из одной верхней папки D1.

## 2. Имена, сети и адреса

| Среда | Compose project | Сервисы | Сети | БД / роли |
| --- | --- | --- | --- | --- |
| local development | marketplace-local | postgres, web, worker | marketplace-local-private (internal) | mw_local; mw_local_bootstrap, mw_local_migrator, mw_local_web, mw_local_worker |
| local test | тот же marketplace-local, отдельный экземпляр | postgres-test; тестовый runner пока не создаётся | marketplace-local-test-private (internal), без подключения development web/worker | mw_local_test; mw_local_test_bootstrap, mw_local_test_runner |
| beta | marketplace-beta | postgres, web, worker | marketplace-beta-private (internal), marketplace-beta-ingress (external) | mw_beta; mw_beta_bootstrap, mw_beta_migrator, mw_beta_web, mw_beta_worker |
| production | marketplace-production | postgres, web, worker | marketplace-production-private (internal), marketplace-production-ingress (external) | mw_production; mw_production_bootstrap, mw_production_migrator, mw_production_web, mw_production_worker |

Имена контейнеров назначает Compose с префиксом project; `container_name` не задаётся. Имена проектов и сетей не переопределять через `-p`/COMPOSE_PROJECT_NAME без новой проверки. Сети не делятся между beta/production, нет общей ingress-сети для двух web. Worker/PostgreSQL только в своей private. Caddy + соответствующий web — единственные участники каждой ingress; aliases `marketplace-beta-web` и `marketplace-production-web`. `external` означает предварительное отдельное создание сети, не интернет-доступ. Не подключать приложения к fbs_net/Airflow/WB.

Локальные кандидаты: Vite `http://127.0.0.1:5173` (proxy /api, /auth, /admin → `127.0.0.1:8100`), Django `127.0.0.1:8100`, development PostgreSQL `127.0.0.1:55440`, test PostgreSQL `127.0.0.1:55441`. В контейнерах DB `postgres:5432`, API 8000. Vite/proxy только описаны, конфигурация запуска не реализована. По netstat TCP LISTENING на четырёх кандидатных портах не обнаружены; Get-NetTCPConnection получил отказ доступа, использован netstat. Будущая доступность и bind не гарантируются; не использовать bind 0.0.0.0.

Серверные кандидаты D1: `https://beta-analytics.158-160-30-90.sslip.io` и `https://analytics.158-160-30-90.sslip.io`. IP взят из принятого документа, актуальность не подтверждена. DNS/HTTPS не запрашивались. На сервере web/DB не публикуют host ports, только имеющийся Caddy 80/443. Нет второго Caddy/Node-сервера. Cookie host-only (`Domain` отсутствует), разные имена mw_beta_session/mw_production_session, Secure + точный CSRF origin; нельзя Domain=.sslip.io. Для local Secure=false допустимо только loopback. Реализация этих настроек и личного входа — последующие задачи, beta до этого не открывать наружу.

## 3. Точные подготовленные файлы

Все пути ниже относительно **`C:/Users/krolo/Documents/marketplace-workspace/`**, состав исчерпывающий:

1. `.gitignore`
2. `README.md`
3. `local/deploy/compose.template.json`
4. `local/config/runtime.env.example`
5. `local/config/environment.policy.json.example`
6. `beta/deploy/compose.template.json`
7. `beta/deploy/Caddyfile.fragment.example`
8. `beta/config/runtime.env.example`
9. `beta/config/environment.policy.json.example`
10. `production/deploy/compose.template.json`
11. `production/deploy/Caddyfile.fragment.example`
12. `production/config/runtime.env.example`
13. `production/config/environment.policy.json.example`
14. `docs/ROLE_CONTRACT.md`
15. `docs/ISOLATION_ACCEPTANCE.md`

Compose использует JSON, совместимый с представлением YAML, для проверки встроенным Python без установки YAML-пакета. Это не заменяет `docker compose config`. Все сервисы имеют профиль design-only, restart=no, образы требуют явного immutable digest через BACKEND_IMAGE/POSTGRES_IMAGE; сами значения/версии сборок не выбраны. Команды, Dockerfile, entrypoints и сервис миграций отсутствуют. runtime.env и secret files отсутствуют, шаблон нельзя считать готовым запуском. PostgreSQL 17 по D1: digest/поддерживаемое исправление согласуются перед установкой. Один backend digest для web/worker; команды их исполнения определяются только в E2-03/E2-13. Frontend dist фиксируется checksum рядом с версией backend, не пересобирается при переносе в production.

## 4. Защита от рабочей БД и внешних действий

Конфигурационный контракт: точное ENVIRONMENT → точный project, каталог, host/name/role своей DB и свой hostname. Нет DATABASE_URL и произвольного DB endpoint; нет адресов WB/SMTP, токенов источников, bootstrap/migrator паролей у web/worker. Секреты разных сред уникальны, production config не монтируется в beta/local. Роли приложения NOSUPERUSER/NOBYPASSRLS, не владельцы таблиц; требования grants/RLS в ROLE_CONTRACT.md, фактические роли ещё не созданы. Локальный test имеет свой экземпляр, не право CREATE DATABASE в development.

Все среды, включая будущую production, начинают с `external_reads=false`, `external_writes=false`, `real_messages=false`, пустых source_connections/scheduled_jobs. Worker concurrency=1. Никаких cron, host timers, Airflow DAG или активных автоматических расписаний. Файловый приёмник вместо SMTP, без реальных адресатов. Будущие задания/lease/idempotency — E2-13, не сделаны здесь.

Обязательный будущий startup guard **до сетевого подключения** отвергает неизвестную/пустую среду, несовпадение DB/project/path, production host/name/role в local/beta, произвольные источники/SMTP, включённые реальные операции или расписания; производственные разрешения не наследуются через env-файл. Валидировать эффективную конфигурацию, а не только example. Внешний адаптер дополнительно проверяет разрешение при исполнении. Флаги пока контракт, код guard не создавался.

Сетевой барьер: internal private у worker/DB; отсутствуют host/privileged/docker socket и mounts чужих папок. **Web подключён к ingress, поэтому internal private не запрещает его исходящий интернет.** До публикации beta обязательна отдельно разрешённая host firewall/egress policy для обеих её сетей: разрешить только ответы established/related, собственную DB и необходимый внутренний DNS; новые исходящие соединения к интернету, IP сервера/host gateway, RFC1918 других сред, WB/FBS/SMTP и другим источникам запретить, включая IPv6 и прямой IP. Caddy инициирует входящие запросы к web; web не должен инициировать новые соединения к Caddy/его соседним сетям. Конкретные CIDR/interfaces и правила DOCKER-USER/nftables определяются после разрешённого обследования Docker, не угадываются. До действующего deny и отрицательного теста запрещено считать beta безопасной для внешних подключений. Shared Caddy/Docker admin остаются общей границей доверия; компрометация host/root не покрывается контейнерной изоляцией.

## 5. Данные, временные файлы, логи и копии

Beta/local по умолчанию только синтетические: минимум две организации и два кабинета, отдельные fake users/идентификаторы, никаких персональных данных/токенов. Fixtures сейчас не созданы. Для обезличенного набора Олег отдельно разрешает источник, поля, период, обезличивание и срок; до передачи исключить пользователей/сессии/MFA/секреты, адресатов, outbox/jobs, внешние ссылки экспортов, произвольные подключения. Полный dump production в beta не переносится; агрегаты обследования не считаются готовыми fixtures. Не допускается общая папка imports/exports/mail между средами.

Экспорты имеют уникальные имена в своей data/exports, не раздаются file_server; доступ только через будущий авторизованный API, срок предложения beta/local 24 часа. Mail-файлы только синтетические, срок предложения 24 часа. Файловые logs без payload, предложение beta 7 дней с отдельным максимумом 100 MiB на сервис; container stdout 10 MiB × 3 на контейнер в шаблоне. Локальный тестовый результат не отправляется внешнему получателю. Автоочистка сейчас не реализуется и позже требует проверок области пути; production retention/RPO/RTO определяется D4.

Beta PostgreSQL и файлы: предварительный общий бюджет 2 GiB данных, 512 MiB exports/mail, 200 MiB app logs, 2 GiB временных копий, плюс образы/системные логи отдельно. Bind mounts не обеспечивают дисковую квоту: перед запуском нужны отдельно разрешённые quota/мониторинг и stop-on-low-space. Копии beta отдельно от production, без общих ключей, отдельные каталоги внешнего хранения после разрешения. Не копировать живой data/postgres; штатное резервирование/restore относятся к E2-15/D4. Обновление сборки не удаляет data/config/backups; никакого общего down -v или удаления верхней папки.

## 6. Общий Caddy и ресурсы

Фрагменты Caddy не применены. Перед изменением общий Caddyfile/Compose сохранить отдельно, проверить действующие FBS host/сети/сертификаты и способ reload/отката. Подключить Caddy к двум отдельным ingress, никогда к private; дать ему read-only только app/frontend/dist каждого окружения в `/srv/marketplace/beta/frontend` и `/srv/marketplace/production/frontend`. Не монтировать верхний каталог/config/data. Handle /api, /auth, /admin включая точные пути направляет backend, fallback SPA только оставшиеся пути. Нет shared frontend каталога, debug/default hostname/wildcard. Предусмотреть закрытый доступ к beta (согласованный VPN/IP allowlist либо эквивалент) и личный вход; фрагмент сам это не реализует. До их проверки не публиковать маршрут beta.

Предварительные лимиты beta в Compose: PostgreSQL 0.50 CPU / 512 MiB / 128 PID; web 0.25 CPU / 384 MiB / 64 PID; worker 0.25 CPU / 256 MiB / 64 PID. Всего до 1 CPU и 1152 MiB плюс Engine/Caddy/cache, без гарантии резерва. Контейнеры read_only/cap_drop у приложений, /tmp tmpfs 64 MiB. Production/local значения в шаблонах также предварительные (DB 1 CPU/1 GiB, web/worker по 0.50 CPU); это не утверждённый capacity plan. До запуска измерить остаток ресурсов относительно FBS/ETL, выбрать окончательные лимиты, проверить swap/OOM и диск. Нагрузочные испытания на общем сервере — только отдельно разрешённые. Общий сервер/proxy не обеспечивают отдельный SLA.

## 7. Первичная локальная проверка и её границы (до обследования сервера)

Проверены Git main / HEAD fadbd979ec4862232d264dd53f83ed7973b3398a и исходные местные изменения. Node v26.7.0, npm 11.19.0, Python 3.14.7, Git 2.55.0 доступны. Docker, psql, Caddy и WSL не найдены в PATH; стандартные каталоги Docker/PostgreSQL не найдены. Это проверка обнаружения, не исчерпывающий поиск всех установок. Django/DRF/psycopg/PyYAML не найдены в текущем Python; совместимость выбранного Python с будущими зависимостями не проверена.

Локальный протокол `SYSTEM_ENVIRONMENTS_CHECKS.json`: JSON разбирается; project/network/db/role имена согласованы, пути mounts/secrets остаются внутри среды, нет shared data/ports у серверных сред, worker/DB отсутствуют в ingress, все внешние действия/расписания отключены. Проверены ограничения beta, профиль неактивных шаблонов и отсутствие runtime secrets/app. Исходные копии плана/журнала побайтно сверены, позднее сравнение 101 строки задач показывает только статус E2-02; D1–D8 и критерии/зависимости сохранены. Это статическая проверка, не проверка Compose schema, DB grants, firewall, работающего guard, отправок, DNS/TLS или Caddy.

Критерий «тестовая среда не может случайно писать в рабочие сервисы или отправлять реальные сообщения» ещё не доказан: работающих сред нет. Полный порядок проверки — `C:/Users/krolo/Documents/marketplace-workspace/docs/ISOLATION_ACCEPTANCE.md`. Проверки реальных внешних адресов сейчас запрещены; будущие отрицательные тесты используют специально разрешённые заглушки, не рабочую БД.

## 8. Ещё необходимые решения/разрешения

1. Конкретная установка локальных компонентов/версий: Docker/WSL2 либо native PostgreSQL, Python venv/Django/DRF/psycopg и dev packages. Ничего не устанавливалось.
2. Отдельное задание E2-03 и разрешённый локальный запуск для Compose schema/runtime/startup guard; E2-03 сейчас не начинается. Полный auth/roles/worker выполняются в своих задачах.
3. Read-only обследование выполнено (раздел 10). Последующим сообщением разрешены контролируемые изменения только нового проекта, без изменения других проектов. Пустые каталоги и две beta-сети подготовлены (раздел 11). Общий Caddy/FBS, существующие сети/настройки других проектов не входят в это разрешение; E2-03 требует отдельного задания.
4. Точные hostnames, закрытый доступ beta, правка общего Caddy с backup/validate и отдельно reload; проверка FBS до/после, TLS и отрицательные тесты изоляции на согласованных endpoint.
5. Любой обезличенный набор и его передача; подключения WB/БД/API, копии во внешнее хранилище и реальные отправки требуют отдельных разрешений. D4/D6/D7 не приняты.
6. Production deployment — отдельное разрешение на ту же проверенную immutable сборку, свои настройки и резервирование. Принятие beta не разрешает production.

## 9. Безопасный откат этой подготовки

Исходные SYSTEM_PLAN.md и CHANGELOG.md: `C:/Users/krolo/Documents/marketplace-workspace/.change-backups/2026-09-30/E2-02-20260930-134024/`. Там же manifest.json с исходными SHA-256 и точными 15 новыми путями/хешами; после проверки добавлен final-manifest.json с хешами результата.

Сначала сравнить нынешние файлы с сохранёнными версиями/хешами и сохранить поздние правки. В плане вернуть только статус/текущий рубеж/следующий шаг E2-02 и убрать добавленные строки его журналов; целый файл восстанавливать только без поздней работы. CHANGELOG не перезаписывать — добавить запись об отмене. SYSTEM_ENVIRONMENTS.md и SYSTEM_ENVIRONMENTS_CHECKS.json удалять лишь если они совпадают с подготовленным результатом и больше не нужны.

Новые 15 файлов удалять по manifest только при совпадении хеша и отсутствии последующей полезной работы; удалять каталоги только после проверки, что они пусты. Верхний marketplace-workspace не удалять рекурсивно. Копии/manifest хранить до завершения всех нужных откатов; серверного отката нет — сервер не менялся.


## 10. Разрешённое серверное обследование и проверка шаблонов — 30.09.2026

Выполнено после текущего разрешения Олега «на сервере ничего не меняй но читать можешь». Отдельно получено разрешение передать пять подготовленных шаблонов через SSH/stdin исключительно для Compose config/Caddy adapt; первоначально auto-review отклонил эту передачу как не покрытую разрешением чтения. После отдельного согласия та же проверка выполнена. Установок и изменений сервера не было; подключений к БД/WB/API, чтения содержимого runtime-секретов/журналов/персональных данных не выполнялось.

Протокол: `C:/Users/krolo/Documents/marketplace-workspace/SYSTEM_ENVIRONMENTS_SERVER_CHECKS.json`. SSH wb-prod действительно вернул результаты команд; ssh -G показывает adm_user@158.160.30.90:22. Это подтверждает адрес назначения SSH, а не независимую проверку публичного IP/sslip.io. Снимки ресурсов: 30.09.2026 13:53:37 и 13:57:15 +03:00.

| Проверка | Фактический результат | Значение для E2-02 |
| --- | --- | --- |
| CPU/RAM | 4 CPU, 7940 MiB RAM, доступно 5178–5205 MiB, swap отсутствует; load 0.70/0.78/0.87 | Лимиты beta 1 CPU / 1152 MiB арифметически помещаются в текущем снимке. Пиковая нагрузка и capacity не подтверждены |
| Диск | / и /home/adm_user на одном /dev/vda1, 70% занято, свободно 10472856–10473344 KiB (около 10 GiB); Docker /var/lib/docker | beta/production/FBS/ETL делят диск; образы, копии и рост БД требуют бюджета/квот до запуска |
| Инструменты | Docker 29.1.3, Compose v5.1.3, Caddy v2.11.4 | Доступны на сервере, локально не установлены |
| Существующие сети | wbtopostgre_airflow_network 172.18.0.0/16; fbs-app_fbs_net 172.19.0.0/16; bridge 172.17.0.0/16; internal=false, IPv6=false | Имена marketplace-* не заняты; новые CIDR выбирать без пересечения после проверки маршрутов/VPN |
| Caddy/FBS | fbs_caddy и fbs_app running/healthy, Caddy только в fbs-app_fbs_net; опубликованы 80/443 на IPv4/IPv6 | Текущие ingress beta/production отсутствуют. Добавление сетей/маршрутов требует изменений, сейчас запрещено |
| Caddy mounts | /home/adm_user/fbs-app/deploy/Caddyfile → /etc/caddy/Caddyfile read-only; volumes fbs-app_caddy_config и fbs-app_caddy_data | Подтверждён путь будущей отдельной копии/правки; содержимое активного Caddyfile и TLS не читались |
| Другие опубликованные порты | API 8000 и Airflow 8081 на IPv4/IPv6; PostgreSQL только 127.0.0.1:5433/5434 | Не использовать существующие БД/порты/сети для собственной beta; доступность извне/cloud firewall не проверялась |
| Каталог | /home/adm_user существует, marketplace-workspace отсутствует | Серверный путь пока свободен, каталог не создавался |
| Firewall | sudo -n iptables -S DOCKER-USER: только -N DOCKER-USER (0 правил), IPv4 forwarding=1; nft ip/ip6 таблицы присутствуют | Нельзя считать egress-защиту выполненной. Полный ruleset/cloud policy не проверены; из пустой цепочки не выводится политика всего firewall |

В текущем снимке FBS ограничен 1 CPU/512 MiB, основные WB/Airflow/PostgreSQL и Caddy не имеют container CPU/RAM лимитов. Поэтому свободная память сейчас не является резервом для новой системы; чужие лимиты этим заданием не меняются. Предварительные лимиты и дисковые бюджеты E2-02 сохранены как предложения, D1 не менялось.

Три Compose-шаблона прошли Docker Compose schema/consistency validation (exit 0) 30.09.2026 13:58:01 +03:00: `docker compose --env-file /dev/null --project-directory /home/adm_user -f - config --no-env-resolution --no-path-resolution --quiet`. Input — только шаблон через stdin, variables — синтетические immutable image references, без build/pull/run. Файлы runtime.env/secrets и bind paths намеренно не разрешались/не создавались; проверка их наличия не выполнена.

Два фрагмента Caddy прошли `docker exec -i fbs_caddy caddy adapt --config /dev/stdin --adapter caddyfile` (exit 0, корректный adapted JSON). Предупреждение: шаблоны не отформатированы по caddy fmt; это не ошибка синтаксиса, форматирование на сервере не выполнялось. Это **не** caddy validate полной конфигурации, проверка закрытого доступа beta, маршрутов, DNS, TLS/upstream, reload или приёмка работающей среды. Caddy продолжает использовать свою прежнюю конфигурацию.

Сети/БД/контейнеры marketplace не созданы; защитный startup guard, фактические ограниченные роли, запрет реальных отправок и egress beta отсутствуют как работающие механизмы. Критерий E2-02 пока не доказан. Следующие разрешения: конкретные локальные компоненты/отдельное задание E2-03; отдельно серверные изменения beta/firewall/квоты/Caddy, закрытый доступ и runtime проверки на согласованных заглушках. Production, любые реальные данные и внешние подключения отдельно.


## 11. Контролируемая подготовка только новой beta — 30.09.2026 14:24:07 +03:00

Текущее разрешение Олега: «если ты не будешь трогать и изменять другие проекты на сервере ... только все максимально подконтрольно». Оно заменяет прежний запрет любых серверных изменений только в пределах новой системы. Общий Caddy принадлежит fbs-app: его файл/сети/контейнер не меняются этим разрешением. Production не создаётся. Установки, механизм запуска, приложение и следующие задачи не выполняются.

Перед записью подтверждено отсутствие верхнего marketplace-workspace и обеих network names; путь parent проверен канонически. Созданы только 12 пустых каталогов с правами 0700: верхний `/home/adm_user/marketplace-workspace/`, `beta/`, `beta/deploy/`, `beta/config/`, `beta/data/`, `beta/data/postgres/`, `beta/data/exports/`, `beta/data/mail/`, `beta/logs/`, `beta/logs/web/`, `beta/logs/worker/`, `beta/backups/`. Файлы/содержимое/секреты туда не записывались; права будущих process UID пока не назначались.

Созданы `marketplace-beta-private` (172.20.0.0/16) и `marketplace-beta-ingress` (172.21.0.0/16), обе internal=true, IPv6=false, без участников. Docker выделил CIDR автоматически. Метки: `io.marketplace.owner=marketplace-workspace`, `io.marketplace.environment=beta`, `io.marketplace.change=E2-02-20260930T112407Z`. Compose ingress остаётся external=true: сеть управляется отдельно; это совместимо с internal=true самой сети. Internal ingress сужает прежнее предложение; будущий Caddy с отдельным подключением может инициировать входящие соединения, но его подключение сейчас запрещено условием не менять другой проект.

Read-back подтвердил права каталогов, internal/IPv6/empty endpoints; ID, internal и участники всех прежних сетей совпали до/после, ID/имена прежних контейнеров тоже. Это не проверка полной конфигурации чужих проектов или их UI. Создание bridge-сетей добавляет собственные host routes/правила Docker; глобальные правила вручную не редактировались. Существующие сети/контейнеры/порты других проектов не изменялись командами этого шага.

Протокол: `C:/Users/krolo/Documents/marketplace-workspace/SYSTEM_ENVIRONMENTS_BETA_PREPARATION.json`. Не запущено ни одного нового контейнера, опубликовано 0 портов; PostgreSQL/роли/guard/сообщения/egress на работающих процессах не проверены. Сама internal-сеть не является полным доказательством блокировки host gateway/чужой БД. E2-02 остаётся на проверке, E2-03 не начата. Полноценные runtime проверки требуют реализации соответствующих задач; не создавать фиктивные web/worker ради отметки готовности.

Откат серверных объектов: сверить **точные ID и метки** из протокола, отсутствие участников сети; только тогда точечно удалить обе новые сети. Затем проверить канонические пути, владельца, отсутствие более поздних файлов/работы и удалить только пустые каталоги через rmdir в обратном порядке. Не удалять верхнюю папку рекурсивно, не применять compose down к FBS/WB и не трогать существующие сети. При появлении последующей полезной работы автоматический откат прекращается.

## 12. Фактическая проверка после разрешённой E2-03
Действующий compose: C:/Users/krolo/Documents/marketplace-workspace/beta/deploy/compose.json; guard: backend/config/guard.py; provisioning: backend/tools/bootstrap_roles.py. Точные пути/роли/лимиты/доказательства — SYSTEM_STARTUP.md и SYSTEM_STARTUP_CHECKS.json. Старые templates исторические, production не применена. Main/test PostgreSQL раздельны, internal сети, ingress пустая; реальные отправки, production и source URL запрещены до подключения. Только синтетические данные. Web не достигает собственного test PostgreSQL, не имеет DDL/admin/system DB доступа. Опубликованных портов нет; предложенный 18100 не используется. Caddy/HTTPS, полный firewall и пиковые нагрузки не проверены. D1 и SYSTEM_ARCHITECTURE.md не менялись. Дальнейшие конкретные разрешения нужны для публичного маршрута/Caddy, production, реальных источников и новых задач.

