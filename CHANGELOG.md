# Журнал изменений и отката

Обязательный журнал проекта по требованию Олега от 30.09.2026. Каждое изменение: дата/время и зона, причина, точный состав, проверка, порядок отката. Записи добавляются; секреты и персональные данные не включаются. Время старых действий, не зафиксированное надёжно, не выдумывается.

## 2026-09-30 — E1: первоначальное обследование

Время: точное время отдельных правок не фиксировалось; локальный/Sheets срез отчёта — до 11:20 МСК (UTC+3). Запись внесена ретроспективно 30.09.2026 после требования журнала.

Что сделано: прочитаны инструкции и план, проверены текущие рабочие копии/Git, доступные материалы WB и ограниченные диапазоны Sheets. Создан `SYSTEM_DISCOVERY.md`; в существующем `SYSTEM_PLAN.md` обновлены статусы E1-01–E1-03, блокировки оставшихся задач и журнал проверок. Недоступные книги не объявлены обследованными. Код приложений не менялся.

Проверка: конкретные источники/измерения — разделы 1–11 отчёта; критерии и зависимости 101 задачи сохранены, этапы 2–8 и D1–D8 не изменены.

Откат: исходный план сохранён в `.change-backups/2026-09-30/SYSTEM_PLAN.before-E1.md`. Чтобы отменить всё обследование, сначала сравнить текущий план с результатом E1 и сохранить последующие правки; затем восстановить только затронутые записи/статусы из этой копии. Если последующих изменений нет, можно восстановить файл целиком. Новый `SYSTEM_DISCOVERY.md` удалять только после проверки отсутствия последующей полезной работы; нынешний файл уже включает продолжение ниже. Исходный `.codebase-memory/` и другие существовавшие файлы не затрагивать.

## 2026-09-30 — E1: завершение после разрешения на чтение

Время: live срезы 11:42–11:56 МСК; последнее сохранение плана 12:05:05 МСК, отчёта 12:10:42 МСК по метаданным файлов, прочитанным перед введением журнала. Это времена снимков/сохранения, а не точное время каждого действия. Запись ретроспективная.

Основание: разрешение Олега «если только на чтение я даю разрешение». Выполнены только SELECT/GET и чтение текущих файлов/состояний. Что сделано: проверены рабочая БД, Airflow и прямой WB API, измерены качество/история/поздние изменения; выбран WB-02 за 29.09.2026; завершены E1-04–E1-10. Обновлены `SYSTEM_PLAN.md`, `SYSTEM_DISCOVERY.md`, добавлен документ запросов `SYSTEM_DISCOVERY_READONLY_CHECKS.sql` и следующие обезличенные артефакты:

- `SYSTEM_DISCOVERY_AIRFLOW.json`
- `SYSTEM_DISCOVERY_DB_ADDITIONAL.jsonseq`
- `SYSTEM_DISCOVERY_DB_CHECKS.jsonseq`
- `SYSTEM_DISCOVERY_DB_METADATA.json`
- `SYSTEM_DISCOVERY_DB_PERIOD_QUALITY.jsonseq`
- `SYSTEM_DISCOVERY_DB_QUALITY.jsonseq`
- `SYSTEM_DISCOVERY_DEPLOYED_CODE.jsonseq`
- `SYSTEM_DISCOVERY_DOMAIN_DETAILS.json`
- `SYSTEM_DISCOVERY_FINANCE_PERIODS.jsonseq`
- `SYSTEM_DISCOVERY_PILOT_CHECK.json`
- `SYSTEM_DISCOVERY_PILOT_REPEAT.json`
- `SYSTEM_DISCOVERY_VARIANTS.json`

Проверка: раздел 15 отчёта и названные агрегаты; JSON-артефакты прочитаны обратно; 101 задача и прежние критерии/зависимости проверены сравнением; этапы 2–8 и D1–D8 сохранены. wbToPostgre/wb-reports остались без местных изменений. Рабочая БД, загрузчики, расписания и приложения не менялись; commit/push, деплой, перезапуск, отправки и этап 2 не выполнялись.

Откат только продолжения: использовать `.change-backups/2026-09-30/SYSTEM_PLAN.before-readonly.md` и `SYSTEM_DISCOVERY.before-readonly.md`, сохраняя любые более поздние изменения. При отсутствии последующих правок восстановить эти два файла из копий; удалить только перечисленные 12 созданных артефактов и новый SQL-документ, если они больше не нужны. Отмена всего E1 описана выше. Серверный откат не требуется: на сервере изменение состояния не выполнялось.

## 2026-09-30, 12:15 МСК (UTC+3) — введён обязательный журнал

Что и зачем: по прямому требованию Олега создан этот `CHANGELOG.md`; в `AGENTS.md` закреплена обязательная запись каждого изменения с проверкой и откатом. `CLAUDE.md` уже ссылается на `AGENTS.md` и не изменён. В `.gitignore` добавлено исключение `/.change-backups/`. Пять исходных снимков перенесены/скопированы в постоянный локальный каталог `.change-backups/2026-09-30/`; добавлен `manifest.json` с SHA-256. Временные оригиналы сохранены. Исходная следующая работа/код не затронуты.

Проверка: пять копий совпали с источниками побайтно; контрольные SHA-256 в manifest. Правило читается через AGENTS/CLAUDE; исключение резервных копий проверено через git check-ignore. В журнал включён весь известный состав уже выполненных изменений обследования; неизвестное точное время явно отмечено.

Откат: исходные `AGENTS.md` и `.gitignore` находятся в `.change-backups/2026-09-30/AGENTS.before-journal.md` и `gitignore.before-journal`. После сравнения и сохранения более поздних правок убрать только добавленные правило/исключение; при отсутствии последующих правок восстановить файлы из этих копий. Сам журнал не стирать: добавить запись об отмене. Резервные копии оставить до завершения всех необходимых откатов. Отмена правила требует явного изменения требования Олегом.

## 2026-09-30, 12:29 МСК (UTC+3) — E2-01: предложение D1

Что и зачем: подготовлено самостоятельное техническое решение для операционного пилота WB-02/29.09.2026 и постепенной замены Sheets. Создан `C:/Users/krolo/Documents/finkos-analytics/SYSTEM_ARCHITECTURE.md`: отдельный будущий репозиторий, Django/PostgreSQL, вход/MFA, среды, организации/юрлица/кабинеты/права, чтение источников, provenance/версии, корректировка −162,24 ₽, ограничения истории, зависимости, бюджет, альтернативы и список решений. В `C:/Users/krolo/Documents/finkos-analytics/SYSTEM_PLAN.md` E2-01 переведена в «На проверке», обновлены текущий/следующий шаг, добавлены запись выполнения и история плана. Уточнено: ранее названный «Т1 достигнут» означал обследование, формальный Т1 раздела 7 ещё требует технической версии. D1 не принято, E2-02 и далее не выполнялись. Этот `C:/Users/krolo/Documents/finkos-analytics/CHANGELOG.md` дополнен данной записью.

Копии до изменения: `.change-backups/2026-09-30/E2-01-20260930-122222/SYSTEM_PLAN.before-D1.md` (SHA-256 FD726C2913646A4FD92A8C686213B741E6B58639A8739D2AE357FD58A3D965CC) и `CHANGELOG.before-D1.md` (SHA-256 F3D710274D1EAE777DC9C1D592D81AD2B0519C5517170EF9479773435EE5B8C4). Созданы только эти два резервных файла и новый SYSTEM_ARCHITECTURE.md; каталог резервов проверен git check-ignore, не коммитится.

Проверка: актуальные инструкции/план/обследование/журнал прочитаны; исходный Git main/HEAD fadbd979ec4862232d264dd53f83ed7973b3398a и местная работа сохранены. Сравнение с копией: ровно 101 строка задач, все критерии/зависимости неизменны; только статус E2-01 изменён, остальные строки задач и D1–D8 совпадают. Цифры пилота и поздняя коррекция сверены по PILOT_CHECK/PILOT_REPEAT. Документы прочитаны обратно, ссылки на локальные материалы и добавление без перезаписи прежнего журнала проверены. Публичные официальные документы Django/PostgreSQL/Docker использованы для актуальности LTS/RLS/лицензии без передачи проектных данных. Запуск/совместимость/скорость/тариф конкретного провайдера не проверялись: это предложение, не реализация. Новых запросов на прод, установок, изменений приложений/БД/загрузчиков/расписаний, commit/push, деплоя, перезапусков и внешних отправок не было.

Откат: сначала сравнить нынешние SYSTEM_PLAN.md/SYSTEM_ARCHITECTURE.md/CHANGELOG.md с данной версией и сохранить поздние/посторонние правки. В плане вернуть только заменённые текущий/следующий шаг и статус E2-01 по SYSTEM_PLAN.before-D1.md; убрать только добавленные строки E2-01 из журналов. Целый план восстанавливать из копии лишь при отсутствии поздних правок. Новый `C:/Users/krolo/Documents/finkos-analytics/SYSTEM_ARCHITECTURE.md` удалять только если он всё ещё является исключительно этим предложением и последующей работы/принятого D1 нет. Журнал не восстанавливать поверх более поздних записей и не стирать данную историю: добавить запись об отмене; CHANGELOG.before-D1.md служит контрольным исходным содержимым. Две копии оставить до завершения отката; их удаление допустимо лишь после проверки, что они больше не нужны и исходные документы сохранены. Откат будущего marketplace-workspace/сервера не нужен: они не создавались/не менялись. Общие git reset/clean не применять.

## 2026-09-30 12:49:45 +03:00 — D1: размещение по схеме FBS

Основание: уточнение Олега о размещении на имеющемся облачном сервере и временном домене по аналогии с FBS. Обновлены только SYSTEM_ARCHITECTURE.md (состав инфраструктуры/рабочая среда/расходы/вопросы, добавлен раздел 2.1) и SYSTEM_PLAN.md (добавлены записи выполнения и истории); CHANGELOG.md дополнен этой записью. Новый VPS/покупка домена больше не обязательны: предложены отдельный Compose project/БД, имя analytics.158-160-30-90.sslip.io как непроверенный кандидат и существующий Caddy с отдельным маршрутом. Учтены занятые host-порты 80/443 и влияние общего proxy на FBS. Дополнительные расходы условны, свободные ресурсы не подтверждены.

До правок сохранены три исходных файла: .change-backups/2026-09-30/D1-hosting-20260930-124653/SYSTEM_ARCHITECTURE.md, .change-backups/2026-09-30/D1-hosting-20260930-124653/SYSTEM_PLAN.md, .change-backups/2026-09-30/D1-hosting-20260930-124653/CHANGELOG.md. Это единственные новые файлы этой правки; каталог исключён Git. Новых конфигураций/приложений не создавалось.

Проверка: схема FBS прочитана в локальных deploy/compose.yml, deploy/Caddyfile и docs/deploy.md, файлы FBS не изменены. Возможность имён sslip.io и HTTPS Caddy уточнена по публичным официальным материалам; конкретный DNS/сертификат/сервер не проверены. Сравнение плана с копией: все 101 строки задач и D1–D8 полностью совпадают; E2-01 на проверке, D1 в целом не принято. Документ прочитан обратно: отдельный VPS оставлен альтернативой, расходы обновлены, доступ/деплой требуют отдельного разрешения. История журнала сохранена. Никаких обращений к серверу, установок, изменений источников/расписаний, commit/push, перезапусков или отправок не выполнялось.

Откат: сравнить текущие документы с тремя копиями .change-backups/2026-09-30/D1-hosting-20260930-124653 и сохранить более поздние изменения. Вернуть только заменённые фрагменты SYSTEM_ARCHITECTURE.md и убрать раздел 2.1; в SYSTEM_PLAN.md убрать только две добавленные записи этого уточнения. Целые файлы восстанавливать из копий лишь при отсутствии последующих правок. CHANGELOG.md не перезаписывать/не удалять историю: добавить запись об отмене; его копия предназначена для сравнения. Копии удалять лишь после завершения необходимого отката и проверки сохранности документов. Серверный откат не требуется: сервер не менялся.

## 2026-09-30 13:00:06 +03:00 — D1: одна папка системы на сервере

По требованию Олега в SYSTEM_ARCHITECTURE.md, раздел 2.1, закреплён единый верхний каталог /home/adm_user/marketplace-workspace/ с app/deploy/config/data/logs/backups внутри. Данные собственной БД предлагаются bind mount внутри этой папки; описано сохранение данных при обновлении кода. Объяснены исключения: системные файлы Docker, существующий общий Caddy и внешние резервные копии. SYSTEM_PLAN.md дополнен записью истории; CHANGELOG.md дополнен этой записью. Существующие папки FBS не затрагиваются.

До изменения сохранены .change-backups/2026-09-30/D1-single-folder-20260930-130006/SYSTEM_ARCHITECTURE.md, .change-backups/2026-09-30/D1-single-folder-20260930-130006/SYSTEM_PLAN.md, .change-backups/2026-09-30/D1-single-folder-20260930-130006/CHANGELOG.md — единственные новые файлы этого уточнения; каталог исключён Git. Проверка: прочитан уточнённый фрагмент, сравнение с копией подтверждает сохранность всех 101 строки задач и D1–D8, история CHANGELOG сохранена добавлением. E2-01 на проверке, D1 в целом не принято. На сервер обращений/записей нет, установок/реализации E2-02/commit/push/деплоя/перезапусков/отправок нет.

Откат: сравнить текущие документы с копиями .change-backups/2026-09-30/D1-single-folder-20260930-130006 и сохранить поздние изменения; убрать только добавленные абзацы структуры/исключений в SYSTEM_ARCHITECTURE.md и последнюю запись этого уточнения в SYSTEM_PLAN.md. Целые файлы восстановить из копий лишь если поздних изменений нет. CHANGELOG не перезаписывать: добавить запись об отмене. Копии оставить до завершения отката; удалить их можно только когда они больше не нужны и документы сохранены. Серверный откат не требуется.

## 2026-09-30 13:10:31 +03:00 — D1: основа для множества сложных сценариев

Основание: Олег подтвердил ожидаемые сложные сценарии и множество будущих правок. В SYSTEM_ARCHITECTURE.md пересмотрена рекомендация: React/TypeScript/Vite frontend + Django/DRF API + PostgreSQL/worker; серверные страницы оставлены альтернативой и допускаются для стандартного входа/MFA. Добавлен раздел 2.2 о модулях, OpenAPI/типах, server/UI state, области кэша, деньгах/ID, optimistic concurrency, массовых командах и проверках. Уточнены runtime/dev-зависимости, единая серверная папка, статическая сборка без Node-сервера, оценка сопровождения 6–12 ч/месяц. SYSTEM_PLAN.md дополнен записью истории, CHANGELOG.md — этой записью. Множество сценариев не означает реализацию будущих редакторов в E2-01.

Копии до правки: .change-backups/2026-09-30/D1-ui-20260930-130725/SYSTEM_ARCHITECTURE.md, .change-backups/2026-09-30/D1-ui-20260930-130725/SYSTEM_PLAN.md, .change-backups/2026-09-30/D1-ui-20260930-130725/CHANGELOG.md — единственные созданные файлы; каталог исключён Git. Проверка: локальное чтение инструкций/Git и обратное чтение изменённого решения, сохранность всех 101 строки задач/критериев/зависимостей и D1–D8 сравнением с копией, история CHANGELOG сохранена. Публичные официальные React/DRF материалы проверены без передачи проектных данных. Совместимость пакетов/запуск/производительность не проверены; зависимости не установлены. E2-01 на проверке, D1 не принято, сервер/приложения/источники/E2-02 не менялись; commit/push/деплой/перезапуски/отправки не выполнялись.

Откат: сначала сравнить текущие документы с .change-backups/2026-09-30/D1-ui-20260930-130725 и сохранить поздние правки; вернуть только заменённые рекомендации/строки зависимостей/оценку/пункт решения и убрать раздел 2.2 из SYSTEM_ARCHITECTURE.md; убрать только последнюю запись этой правки из SYSTEM_PLAN.md. Если последующих изменений нет, эти два файла можно восстановить полностью из копий. CHANGELOG не перезаписывать, добавить запись об отмене; его копия — контроль исходной истории. Копии сохранять до завершения отката, удалять лишь если больше не нужны и документы сохранены. Серверный откат не нужен.

## 2026-09-30 13:31:21 +03:00 — D1 принято, включена beta

Основание: Олег согласился с общей архитектурой и после предложения отдельной beta ответил «да, меня устраивает». В SYSTEM_ARCHITECTURE.md зафиксировано принятие D1, добавлен раздел 3.1: production/beta внутри одной серверной папки, независимые контейнеры/БД/ключи/данные, кандидаты адресов, синтетические/разрешённые обезличенные данные, отключённые внешние операции, порядок локально → beta → отдельно разрешённый production, лимиты общего сервера. Уточнены структура папки, среды и оставшиеся конкретные разрешения. В SYSTEM_PLAN.md D1 принято, E2-01 готова как подготовка/принятие решения; обновлены текущий/следующий шаг и журналы. CHANGELOG дополнен этой записью. Принятие архитектуры не является разрешением установок, новых серверных обращений/изменений или начала E2-02.

Копии до изменений: .change-backups/2026-09-30/D1-accepted-20260930-132838/SYSTEM_ARCHITECTURE.md, .change-backups/2026-09-30/D1-accepted-20260930-132838/SYSTEM_PLAN.md, .change-backups/2026-09-30/D1-accepted-20260930-132838/CHANGELOG.md. Это единственные новые файлы, каталог исключён Git. Проверка: 101 задача сохранена, критерии/зависимости совпадают с копией, изменён только статус E2-01; D2–D8 неизменны. D1 принят со ссылкой на документ и сообщение Олега; beta-структура и границы проверены обратным чтением, прежняя история журнала сохранена. Каталоги сервера/окружения не созданы; приложения/БД/загрузчики/расписания не менялись, установки/commit/push/деплой/перезапуски/отправки не выполнялись. Фактическая изоляция/ресурсы/запуск будут проверены в следующих разрешённых задачах.

Откат документов: сравнить с копиями .change-backups/2026-09-30/D1-accepted-20260930-132838, сохранить поздние правки; вернуть только изменённые абзацы/таблицу сред/раздел решения, убрать 3.1 в SYSTEM_ARCHITECTURE.md; вернуть текущий/следующий шаг и статусы E2-01/D1, убрать только добавленные строки журналов этого шага в SYSTEM_PLAN.md. Полное восстановление этих двух файлов из копий допустимо лишь без поздних правок. Принятое решение отменять только по новому указанию Олега; технический откат документа сам по себе не отменяет его согласие. CHANGELOG не перезаписывать: добавить запись об отмене. Копии хранить до завершения отката; удалить только если больше не нужны и документы сохранены. Серверный откат не требуется.

## 2026-09-30 13:47:42 +03:00 — E2-02: конфигурация разделения сред

По текущему заданию Олега подготовлены только локальные неактивные конфигурации local/beta/production; D1 не менялось. Перед созданием C:/Users/krolo/Documents/marketplace-workspace проверен абсолютный путь и отсутствие содержимого. Установки/сервер/источники/приложения/расписания/commit/push/деплой/перезапуски/отправки отсутствуют. E2-03 не начата.

Изменён C:/Users/krolo/Documents/finkos-analytics/SYSTEM_PLAN.md: только статус E2-02 на «На проверке», текущие сводные абзацы и две записи журналов. Дополнен C:/Users/krolo/Documents/finkos-analytics/CHANGELOG.md. Созданы C:/Users/krolo/Documents/finkos-analytics/SYSTEM_ENVIRONMENTS.md и SYSTEM_ENVIRONMENTS_CHECKS.json. Артефакты нового проекта (точный состав):

- `C:/Users/krolo/Documents/marketplace-workspace/.gitignore`
- `C:/Users/krolo/Documents/marketplace-workspace/README.md`
- `C:/Users/krolo/Documents/marketplace-workspace/local/config/environment.policy.json.example`
- `C:/Users/krolo/Documents/marketplace-workspace/local/config/runtime.env.example`
- `C:/Users/krolo/Documents/marketplace-workspace/local/deploy/compose.template.json`
- `C:/Users/krolo/Documents/marketplace-workspace/beta/config/environment.policy.json.example`
- `C:/Users/krolo/Documents/marketplace-workspace/beta/config/runtime.env.example`
- `C:/Users/krolo/Documents/marketplace-workspace/beta/deploy/compose.template.json`
- `C:/Users/krolo/Documents/marketplace-workspace/beta/deploy/Caddyfile.fragment.example`
- `C:/Users/krolo/Documents/marketplace-workspace/production/config/environment.policy.json.example`
- `C:/Users/krolo/Documents/marketplace-workspace/production/config/runtime.env.example`
- `C:/Users/krolo/Documents/marketplace-workspace/production/deploy/compose.template.json`
- `C:/Users/krolo/Documents/marketplace-workspace/production/deploy/Caddyfile.fragment.example`
- `C:/Users/krolo/Documents/marketplace-workspace/docs/ROLE_CONTRACT.md`
- `C:/Users/krolo/Documents/marketplace-workspace/docs/ISOLATION_ACCEPTANCE.md`

Исходные SYSTEM_PLAN.md и CHANGELOG.md сохранены и побайтно проверены в C:/Users/krolo/Documents/finkos-analytics/.change-backups/2026-09-30/E2-02-20260930-134024/; manifest.json содержит исходные root hashes и 15 новых путей/хешей. Перед уточнением протокола сохранён SYSTEM_ENVIRONMENTS.before-check-detail.md в той же папке. final-manifest.json — хеши подготовленного результата. Полный состав копий/контроля в этой папке: SYSTEM_PLAN.md, CHANGELOG.md, manifest.json, SYSTEM_ENVIRONMENTS.before-check-detail.md, final-manifest.json, CHANGELOG.before-final-detail.md (копия перед уточнением количества проверок и перечня backup-файлов). Папка исключена Git, не коммитить.

Проверка: JSON parsing и 97 статических инвариантов (все успешны); 101 строка задач сохранена, отличается только статус E2-02; критерии/зависимости и D1–D8 неизменны; исходные посторонние root файлы совпадают по SHA-256. Node/npm/Python/Git найдены; Docker/psql/Caddy/WSL не обнаружены в PATH, Django/DRF/psycopg/PyYAML в текущем Python отсутствуют. Get-NetTCPConnection отказал в доступе, netstat LISTENING проверен: 5173/8100/55440/55441 не слушаются. Порты лишь кандидаты; Compose schema, DB grants, guard, firewall, отправки, DNS/TLS/Caddy и ресурсы/изоляция работающих сред НЕ проверены. Подробный протокол — SYSTEM_ENVIRONMENTS_CHECKS.json; E2-02 не объявлена готовой.

Откат: сначала сравнить текущие файлы с копиями/manifest и сохранить позднюю работу. В SYSTEM_PLAN.md вернуть только изменения E2-02 по исходной копии; целиком восстанавливать только без последующих правок. CHANGELOG не перезаписывать, добавить запись об отмене. Два новых SYSTEM_ENVIRONMENTS-файла и 15 файлов нового проекта удалять по final-manifest только если хеши совпадают и нет дальнейшей полезной работы; каталоги удалять лишь пустые, без рекурсивного удаления marketplace-workspace. Backup-файлы сохранить до завершения нужных откатов; удалить лишь если больше не нужны. Серверного отката нет.

## 2026-09-30 14:02:46 +0300 (Europe/Moscow, UTC+3) — E2-02: read-only сервер и проверка схемы

Основание: текущее разрешение Олега «на сервере ничего не меняй но читать можешь» и отдельное разрешение передачи трёх Compose/two Caddy шаблонов через SSH/stdin только для config/adapt. Первичная передача отклонена auto-review (чтение не разрешает отправку файлов); после отдельного согласия проверка прошла. На сервере не создавались/не менялись файлы, сети, контейнеры, правила или данные; нет установки/build/pull/deploy/reload/restart/DB/API/отправок, E2-03 не начата. Чтение metadata и запуск диагностических процессов могут отражаться в штатных SSH/sudo/Docker журналах; это не изменение конфигурации.

Локально изменены C:/Users/krolo/Documents/finkos-analytics/SYSTEM_ENVIRONMENTS.md (исходную проверку обозначили историческим снимком, добавили раздел 10 и актуальную границу разрешений), SYSTEM_PLAN.md (следующий шаг и записи двух журналов, статусы/критерии/зависимости/D1–D8 без изменений), CHANGELOG.md (добавлена эта запись). Создан только один новый артефакт C:/Users/krolo/Documents/finkos-analytics/SYSTEM_ENVIRONMENTS_SERVER_CHECKS.json. 15 артефактов C:/Users/krolo/Documents/marketplace-workspace не менялись, совпали по исходным SHA-256.

Исходные три изменяемых файла сохранены побайтно в C:/Users/krolo/Documents/finkos-analytics/.change-backups/2026-09-30/E2-02-server-readonly-20260930-140246/SYSTEM_ENVIRONMENTS.md, C:/Users/krolo/Documents/finkos-analytics/.change-backups/2026-09-30/E2-02-server-readonly-20260930-140246/SYSTEM_PLAN.md, C:/Users/krolo/Documents/finkos-analytics/.change-backups/2026-09-30/E2-02-server-readonly-20260930-140246/CHANGELOG.md. В этой же исключённой Git папке создан manifest.json с хешами исходных копий и конечных четырёх файлов; это четвёртый новый файл каталога копий. SYSTEM_ENVIRONMENTS_CHECKS.json и SYSTEM_ARCHITECTURE.md не менялись.

Проверка: SSH дал реальные результаты (13:53:37–13:58:01 +03:00); 4 CPU/7940 MiB RAM/около 10 GiB диска, сети и Caddy mounts/ports проверены, DOCKER-USER пустая, marketplace path отсутствует. Три docker compose config прошли (exit 0, env/path resolution отключены), два caddy adapt прошли (exit 0, только предупреждение форматирования). Ни TLS, полный Caddy validate, runtime роли/guard/egress/отправки/изоляция, ни пиковый capacity не подтверждены; E2-02 остаётся «На проверке». JSON протокол прочитан обратно; 101 строка задач и D1–D8 совпадают с копией; исходная локальная работа сохранена по SHA-256.

Безопасный откат: сначала сравнить текущие три документа с исходными копиями и конечными хешами manifest, сохранить поздние правки. Убрать только изменения этой записи из SYSTEM_ENVIRONMENTS.md и два добавленных журнальных фрагмента/следующий шаг SYSTEM_PLAN.md; полное восстановление этих двух файлов допустимо лишь при отсутствии дальнейшей работы. CHANGELOG не перезаписывать, добавить запись об отмене. SYSTEM_ENVIRONMENTS_SERVER_CHECKS.json удалять только если совпадает с конечным хешем и нет последующей полезной работы. Копии/manifest хранить до завершения необходимых откатов, удалять лишь после проверки, что они больше не нужны. Серверного отката нет: серверная конфигурация не менялась.

## 2026-09-30 14:27:25 +0300 (Europe/Moscow, UTC+3) — E2-02: пустая инфраструктура beta

Основание: текущее условное разрешение Олега менять только новый проект, без изменения других проектов на сервере, максимально подконтрольно. Перед записью target path и имена сетей отсутствовали, parent проверен канонически. В 14:24:07 +03:00 созданы 12 пустых каталогов 0700 и две internal beta сети с ownership/change labels; подробные точные пути/ID/метки — новый C:/Users/krolo/Documents/finkos-analytics/SYSTEM_ENVIRONMENTS_BETA_PREPARATION.json. Приложения/БД/секреты/запуск/порты/установки/production/Caddy/FBS/WB/Airflow/commit/push не менялись или не создавались. Docker создал собственные routes/правила для двух новых bridge сетей; вручную firewall не менялся.

Изменены только C:/Users/krolo/Documents/finkos-analytics/SYSTEM_ENVIRONMENTS.md (актуальные границы разрешения и раздел 11), SYSTEM_PLAN.md (следующий шаг и журналы), CHANGELOG.md (добавление этой записи), C:/Users/krolo/Documents/marketplace-workspace/README.md (актуальное состояние серверных каталогов). До изменений четыре копии сохранены побайтно в C:/Users/krolo/Documents/finkos-analytics/.change-backups/2026-09-30/E2-02-beta-preparation-20260930-142725/SYSTEM_ENVIRONMENTS.md, SYSTEM_PLAN.md, CHANGELOG.md и README.md. В этой папке дополнительно создан manifest.json с before/after SHA-256; каталог исключён Git.

Проверка: read-back каталогов/сетей, обе сети internal=true/IPv6=false/endpoints пусты; ID/internal/member lists прежних сетей и ID/names прежних контейнеров совпали до/после. Новых контейнеров 0, опубликованных портов 0, новых серверных файлов 0. Локальный JSON прочитан обратно, все 101 task rows/D1–D8 совпали с копией. Runtime guard/grants/egress/изоляция/отправки не подтверждены; E2-02 на проверке, E2-03 не начата.

Откат сервера: сверить точные ID/ownership/change labels двух сетей с протоколом и убедиться в нулевых endpoints, затем только точечный docker network rm этих сетей. Проверить канонические paths/пустоту и отсутствие поздней работы, удалить 12 каталогов лишь rmdir в обратном порядке, без рекурсивного удаления. Если позже появились файлы/участники, остановить откат и сохранить их. Локальный откат: сравнить копии/хеши, вернуть лишь изменения этой записи в SYSTEM_ENVIRONMENTS.md, SYSTEM_PLAN.md и README.md; целиком восстанавливать только без дальнейших правок. CHANGELOG не перезаписывать, добавить запись об отмене. Новый JSON удалять только при совпадении хеша и отсутствии последующей полезной работы; backups/manifest хранить до завершения нужных откатов.

## 2026-09-30T16:55:51+03:00 (Europe/Moscow) — E2-03: разрешённая техническая основа и завершение проверки E2-02

Основание: Олег отдельно разрешил зависимости нового проекта и запуск изолированной beta после просьбы двигаться дальше. D1 сохранено, E2-04 не начата. Изменены только новый marketplace-workspace и перечисленные документы finkos. Установлены Python venv и frontend node_modules; серверные base images закреплены digest, backend/frontend собраны. Git нового проекта codex/e2-03 без commit/push/remotes. На сервере только marketplace-beta: main/test PostgreSQL, web, отдельные internal сети и машинные секреты; значения секретов не сохранены в документах/копиях/манифесте. Нет внешних запросов к источникам, production, Caddy, worker, расписаний, бизнес-моделей.

Новые исходники, отчёты и архивы (точные пути):
- C:\Users\krolo\Documents\finkos-analytics\SYSTEM_STARTUP.md
- C:\Users\krolo\Documents\finkos-analytics\SYSTEM_STARTUP_CHECKS.json
- C:\Users\krolo\Documents\marketplace-workspace\artifacts\e2-03-0210f27a7ab1.tar
- C:\Users\krolo\Documents\marketplace-workspace\artifacts\e2-03-2b9b080278b8.tar
- C:\Users\krolo\Documents\marketplace-workspace\artifacts\e2-03-30b23567ac62.tar
- C:\Users\krolo\Documents\marketplace-workspace\artifacts\e2-03-3aba3a4d506d.tar
- C:\Users\krolo\Documents\marketplace-workspace\artifacts\e2-03-f12881b6d066.tar
- C:\Users\krolo\Documents\marketplace-workspace\artifacts\e2-03-fece93126054.tar
- C:\Users\krolo\Documents\marketplace-workspace\backend\.dockerignore
- C:\Users\krolo\Documents\marketplace-workspace\backend\config\__init__.py
- C:\Users\krolo\Documents\marketplace-workspace\backend\config\guard.py
- C:\Users\krolo\Documents\marketplace-workspace\backend\config\settings.py
- C:\Users\krolo\Documents\marketplace-workspace\backend\config\urls.py
- C:\Users\krolo\Documents\marketplace-workspace\backend\config\wsgi.py
- C:\Users\krolo\Documents\marketplace-workspace\backend\Dockerfile
- C:\Users\krolo\Documents\marketplace-workspace\backend\manage.py
- C:\Users\krolo\Documents\marketplace-workspace\backend\requirements.in
- C:\Users\krolo\Documents\marketplace-workspace\backend\requirements.lock
- C:\Users\krolo\Documents\marketplace-workspace\backend\tests\__init__.py
- C:\Users\krolo\Documents\marketplace-workspace\backend\tests\test_guard.py
- C:\Users\krolo\Documents\marketplace-workspace\backend\tests\test_runtime.py
- C:\Users\krolo\Documents\marketplace-workspace\backend\tools\bootstrap_roles.py
- C:\Users\krolo\Documents\marketplace-workspace\backend\tools\verify_web_role.py
- C:\Users\krolo\Documents\marketplace-workspace\beta\deploy\beta.py
- C:\Users\krolo\Documents\marketplace-workspace\beta\deploy\Caddyfile.fragment.example
- C:\Users\krolo\Documents\marketplace-workspace\beta\deploy\compose.json
- C:\Users\krolo\Documents\marketplace-workspace\beta\deploy\compose.template.json
- C:\Users\krolo\Documents\marketplace-workspace\beta\deploy\images.lock.json
- C:\Users\krolo\Documents\marketplace-workspace\beta\deploy\reproduce.py
- C:\Users\krolo\Documents\marketplace-workspace\beta\deploy\verify_isolation.py
- C:\Users\krolo\Documents\marketplace-workspace\beta\deploy\verify_migrations.py
- C:\Users\krolo\Documents\marketplace-workspace\frontend\.dockerignore
- C:\Users\krolo\Documents\marketplace-workspace\frontend\Dockerfile
- C:\Users\krolo\Documents\marketplace-workspace\frontend\index.html
- C:\Users\krolo\Documents\marketplace-workspace\frontend\package-lock.json
- C:\Users\krolo\Documents\marketplace-workspace\frontend\package.json
- C:\Users\krolo\Documents\marketplace-workspace\frontend\src\main.tsx
- C:\Users\krolo\Documents\marketplace-workspace\frontend\src\style.css
- C:\Users\krolo\Documents\marketplace-workspace\frontend\tsconfig.json
- C:\Users\krolo\Documents\marketplace-workspace\frontend\vite.config.ts
- C:\Users\krolo\Documents\marketplace-workspace\tools\package_beta.py

Изменённые существующие файлы:
- C:\Users\krolo\Documents\finkos-analytics\SYSTEM_PLAN.md
- C:\Users\krolo\Documents\finkos-analytics\SYSTEM_ENVIRONMENTS.md
- C:\Users\krolo\Documents\finkos-analytics\CHANGELOG.md
- C:\Users\krolo\Documents\marketplace-workspace\README.md
- C:\Users\krolo\Documents\marketplace-workspace\.gitignore
- C:\Users\krolo\Documents\marketplace-workspace\docs\ROLE_CONTRACT.md
- C:\Users\krolo\Documents\marketplace-workspace\docs\RUNBOOK.md

Перед изменениями сохранены копии в C:\Users\krolo\Documents\finkos-analytics\.change-backups\2026-09-30\E2-03-20260930-153934; полный список копий и hashes — change-manifest.json. Вспомогательный finish_manifest.py и change-manifest.json также созданы здесь. Генерируемые каталоги нового проекта: backend/.venv/, frontend/node_modules/, frontend/dist/, backend/**/__pycache__/, .git/; зависимости/артефакты исключены Git согласно .gitignore. Посторонние .playwright-cli/ и output/ сохранены и не включены в наш перечень.

Серверные точные пути и ID: SYSTEM_STARTUP_CHECKS.json и SYSTEM_STARTUP.md. Источники /home/adm_user/marketplace-workspace/beta/app/backend/, app/frontend/, deploy/; config/source-manifest.json отсутствует — фактический манифест deploy/source-manifest.json. Runtime markers/config: beta/config/provisioned.json, bootstrap.done, bootstrap-test.done, migration-checks.json, e2-03-checks.json, prestart-projects.json; secrets только beta/config/secrets/ (шесть имён в SYSTEM_STARTUP.md, без значений/хешей). Данные beta/data/postgres/ и postgres-test/, копия beta/backups/test/migrations-before.dump, тестовая restore БД mw_beta_test_restore. Source copies: beta/.change-backups/e2-03-prelaunch-project-guard/, e2-03-test-maintenance/, e2-03-runtime-verification/, e2-03-migration-script-syntax/. Конкретная финальная сборка e2-03-0210f27a7ab1; промежуточные архивы/образы сохранены, общий Docker cache/prune не менялся.

Проверки: локальные два guard tests, pip check, TypeScript/Vite build; Linux пять Django tests с полным teardown; чистый временный PostgreSQL/network с provisioning/миграциями/tests/teardown; шесть неверных startup конфигураций отклонены; web DDL/admin/system DB запрещены; web TCP к собственному test PostgreSQL в другой сети запрещён; rollback/forward contenttypes и восстановление синтетического dump в отдельную test DB прошли. 30 исходников и три frontend build-файла совпали по SHA-256. Во время разработки исправлены POSIX путь, Gunicorn control socket, test maintenance CONNECT, module invocation и синтаксис checker, итоговые проверки прошли. FBS перезапускался Олегом параллельно (его подтверждение), наши команды FBS не меняли; остальные семь сравниваемых контейнеров включая Caddy без metadata изменений. HTTPS/общий firewall/пиковая нагрузка/полный Windows Docker запуск не проверены. Детальный результат: SYSTEM_STARTUP_CHECKS.json.

Автопроверка отклонила удаление ошибочно созданного мной корневого ROLE_CONTRACT.md без собственной копии. Затем файл сохранён в accidental-root-ROLE_CONTRACT.md, hash и ожидаемое содержимое сверены; дополнение перенесено в существующий docs/ROLE_CONTRACT.md с предварительной копией, дубликат удалён. Длинная команда финализации ранее не исполнилась из-за Windows error 206, после чего операции разделены.

Откат: сначала сравнить текущие hashes с change-manifest.json, сохранить позднюю/постороннюю работу. Вернуть только свои изменения существующих документов из соответствующих копий, CHANGELOG не перезаписывать — добавить отмену. Новые source/archives и генерируемые каталоги удалять только после проверки принадлежности и отсутствия поздней работы; output/.playwright-cli не трогать. Серверный откат требует конкретного разрешения: сверить labels/IDs/mounts и остановить только marketplace-beta, данные/secrets/dump автоматически не удалять; source вернуть из собственных beta/.change-backups/. Не применять git reset/clean, Docker prune или рекурсивное удаление корня. Протоколы/копии сохранять до завершения необходимых откатов.

Финальный read-back 2026-09-30T16:56:48.8695170+03:00: проверены 101 строка плана, изменились только статусы E2-02/E2-03; история CHANGELOG сохранена побайтным префиксом. Git check-ignore подтвердил, что backend/config/settings.py отслеживаемый источник, а venv/node_modules исключены. Проверка Git sibling потребовала только одноразовый -c safe.directory из-за разных Windows SID; глобальные настройки не менялись. Добавлены имена secret-файлов без значений в SYSTEM_STARTUP.md с предварительной копией before-secret-names-SYSTEM_STARTUP.md. Временный ошибочный дубликат ROLE_CONTRACT удалён после сохранения и hash-проверки; незавершённых отклонённых действий нет.


## 2026-09-30T17:16:44+03:00 (Europe/Moscow) — документы перенесены в marketplace-workspace

По текущему запросу Олега комплект нового проекта собран в его отдельной папке. Перенесены 22 корневых SYSTEM_* и 62 файла из девяти подпапок D1/E2 в .change-backups/2026-09-30/. В новый проект скопированы прежний CHANGELOG.md целиком и шесть общих исходных копий с manifest.json; их экземпляры в Finkos сохранены для истории и отката правил старого приложения. Старый журнал дополнен указателем на новое место. Единственный рабочий план находится здесь.

Обновлены README.md, docs/RUNBOOK.md, docs/SYSTEM_DESIGN.md, docs/design/guide.html, docs/design/CHANGELOG.md, docs/design/checksums.sha256, SYSTEM_PLAN.md, SYSTEM_ARCHITECTURE.md, SYSTEM_ENVIRONMENTS.md и SYSTEM_STARTUP.md. Созданы AGENTS.md с перенесённым правилом журнала и CLAUDE.md; правило Next.js осталось только у старого приложения. Старые JSON/SQL-протоколы, история журнала и исторические манифесты сохранены побайтно. Их абсолютные старые пути — исторические: для перенесённых файлов соответствие старого и нового места записано в манифесте переноса; перед будущим откатом пользоваться этим соответствием, старые вспомогательные скрипты автоматически не запускать.

Копии до правок: .change-backups/2026-09-30/workspace-migration/before/old/ и before/new/. Полный точный перечень источников, назначений, размеров и SHA-256: .change-backups/2026-09-30/workspace-migration/manifest.json; состояние до переноса: baseline.json. Служебные файлы этой операции: migrate.py, finalize.ps1, verify.py, manifest.json, baseline.json, verification.json и перечисленные в manifest.json artifact_files исходные копии в этой же папке. Все резервные копии исключены Git. Файлы с жёсткими ссылками заменяются атомарно, чтобы не менять связанные архивные экземпляры.

Проверка: SHA-256 каждого копирования до удаления старого пути, повторная проверка всех файлов после переноса, неизменность всех 101 строк задач и D1–D8, побайтный префикс прежнего журнала в обеих папках, целостность восьми контрольных сумм дизайна, существование исправленных ссылок и неизменность посторонних файлов. Результат фиксируется в verification.json после завершения; до его успешного результата перенос не считается проверенным. Сервер, зависимости и работающие приложения в этой операции не проверялись и не менялись. Commit/push не выполнялись.

Откат: сначала сравнить текущие SHA-256 с manifest.json и сохранить поздние правки. Вернуть каждый отсутствующий старый путь action=move из before/old (для SYSTEM_*) или его destination (для неизменяемых копий D1/E2), сверив sha256_before; существующее содержимое не перезаписывать. Восстановить только правки ссылок по before/new и before/old. Журналы не сокращать, добавить запись об отмене. Новые файлы назначения и инструкции удалять только по точному перечню после восстановления источников, проверки SHA-256 и отсутствия поздней работы. Служебную папку и общие копии сохранять до завершения всех нужных откатов. Общие git reset/clean и рекурсивное удаление корней запрещены.


## 2026-09-30T17:46:14+03:00 (Europe/Moscow, UTC+3) — E2-04: локальная модель владения

Причина: текущий запрос Олега реализовать только E2-04 согласно принятому D1 §4. Добавлены UUID-пользователь без глобальных прав, организация, независимое членство/шаблон роли, юрлицо, бренд, кабинет и метаданные технического подключения. История связи кабинета с юрлицом фиксируется с момента наблюдения, без предположений о прошлом; ротация ссылки на секрет не создаёт кабинет. Архивирование сохраняет строки/связи. На PostgreSQL предусмотрены составные FK, неизменность organization_id/исторического приписывания и запрет физического DELETE. Роли не подменяют будущие кабинетные grant/RBAC/RLS. D1 не изменено.

Изменённые существующие файлы и исходные копии:
- `backend/config/settings.py` → `.change-backups/2026-09-30/E2-04/settings.py`.
- `SYSTEM_PLAN.md` → `.change-backups/2026-09-30/E2-04/SYSTEM_PLAN.md`.
- `docs/RUNBOOK.md` → `.change-backups/2026-09-30/E2-04/RUNBOOK.md`.
- `CHANGELOG.md` → `.change-backups/2026-09-30/E2-04/CHANGELOG.md`.

Новые точные пути (относительно C:/Users/krolo/Documents/marketplace-workspace):
- `backend/config/ownership_local_checks.py`.
- `backend/ownership/__init__.py`.
- `backend/ownership/apps.py`.
- `backend/ownership/models.py`.
- `backend/ownership/services.py`.
- `backend/ownership/migration_operations.py`.
- `backend/ownership/migrations/__init__.py`.
- `backend/ownership/migrations/0001_initial.py`.
- `backend/ownership/migrations/0002_postgresql_ownership_guards.py`.
- `backend/tests/test_ownership.py`.
- `backend/tests/test_ownership_migrations.py`.
- `backend/tools/verify_ownership_recovery.py`.
- `docs/E2-04_OWNERSHIP.md`.
- `SYSTEM_OWNERSHIP_CHECKS.json`.

Служебные копии промежуточных новых файлов перед правками: `.change-backups/2026-09-30/E2-04/iteration-1/{models.py,services.py,test_ownership.py,test_ownership.before-pg-test-fix.py,test_ownership_migrations.py,verify_ownership_recovery.py,E2-04_OWNERSHIP.md}`. Манифест файлов/копий с SHA-256: `.change-backups/2026-09-30/E2-04/manifest.json`. Генерируемый Python __pycache__ исключён Git, новых установок/сборочных архивов нет. Журнал и документы сохранены атомарной заменой, исторические hardlink-экземпляры не перезаписаны.

Проверки: 14 тестов обнаружено, 11 успешных, 3 явно пропущены (PostgreSQL FK, триггеры истории/удаления и конкуренция). Две синтетические организации и два кабинета; разные роли одного пользователя, допустимые/чужие связи, сохранение версий и архивов. SQLite: forward, 0002 reverse/forward с сохранением строки, 0001 zero/forward только пустой одноразовой схемы. Django check, migration drift check, pip check и AST 13 исходников прошли. Первоначальный отдельный запуск guard из корня имел ModuleNotFoundError config; корректный запуск из backend и итоговый объединённый тестовый запуск прошли. В промежуточном тесте PostgreSQL-only assertion ошибочно стоял в SQLite-тесте; перенесён в соответствующий PostgreSQL-тест, итоговый набор успешен. Recovery probe проверен только синтаксически, PostgreSQL/dump/restore не запускались. Протокол: SYSTEM_OWNERSHIP_CHECKS.json.

Git: ветка codex/e2-03, исходный комплект untracked; чужие файлы, index/refs, output/.playwright-cli сохранены, commit/push не было. Серверы, Caddy/FBS/WB API/Finkos/production не читались и не менялись; реальные источники/секреты/персональные данные не читались. Старые вспомогательные скрипты не запускались. Исторические абсолютные пути сверены с workspace-migration/manifest.json, копии доступны в marketplace-workspace. E2-04 оставлена «На проверке»: необходимы реальные PostgreSQL FK/триггеры/конкуренция, миграции/откат и новый синтетический dump/restore, затем отдельно согласованная проверка схемы beta. Вход, приглашения, RBAC/RLS, UI, worker и следующие задачи не реализованы.

Безопасный откат: сравнить текущие SHA-256 с manifest.json, сохранить поздние/посторонние правки; вернуть только изменения E2-04 из указанных исходных копий settings/плана/RUNBOOK. CHANGELOG не сокращать, добавить отмену. Новые файлы удалять только по точному перечню при совпадении hash и отсутствии поздней работы, предварительно убрать регистрацию ownership/AUTH_USER_MODEL и ссылки на документы. Промежуточные/исходные копии сохранять до завершения отката. Не использовать reset/clean или рекурсивное удаление корня. На заполненной БД zero удаляет историю: не применять; серверный откат отдельно разрешать через совместимый код/сохранение схемы или проверенный dump в новую собственную БД, без перезаписи живой БД/секретов/данных.


## 2026-09-30T17:58:20+03:00 (Europe/Moscow, UTC+3) — локальные ветки main и beta

По текущему запросу Олега: main предназначена для принятых production-релизов, beta — для проверок beta. Принят цикл: локальные коммиты создаёт помощник; Олег проверяет сообщения и содержимое и сам делает push; сервер получает код только из соответствующей Git-ветки после отдельного разрешения. Передача исходников архивами и прямая правка серверных исходников не используются.

Проверка до операции: репозиторий без коммитов, HEAD refs/heads/codex/e2-03, index пуст; весь текущий код/документы untracked. Для создания двух реальных веток предусмотрен один пустой стартовый коммит без исходников, автор Oleg, email oleg@localhost — технический адрес для этого пустого коммита, явно выбранный Олегом в текущем чате; постоянный Git email не настроен. Обе ветки указывают на него, рабочая ветка beta. Код E2-04 не включается в main и не коммитится этой операцией. Hooks и подпись отключены только на команду стартового коммита; глобальная конфигурация не меняется. Push, remote, серверы, миграции и перезапуски не выполняются. После операций проверить обе ссылки, одинаковый commit ID, пустое дерево, текущую beta и неизменность index/рабочих файлов.

Изменённый файл: CHANGELOG.md (только добавление записи). Копия исходного журнала: .change-backups/2026-09-30/git-main-beta/CHANGELOG.md; исходный символический HEAD: .change-backups/2026-09-30/git-main-beta/HEAD.before. Новые служебные файлы: .git/refs/heads/main, .git/refs/heads/beta, Git object пустого стартового коммита и штатные reflogs; резервные копии исключены Git.

Откат: сначала сверить main/beta с пустым стартовым коммитом и убедиться, что нет поздних коммитов/чужой работы или публикации. Только при этих условиях вернуть символический HEAD refs/heads/codex/e2-03 и удалить исключительно созданные main/beta refs через git update-ref с ожидаемым commit ID. Объекты/reflogs автоматически не удалять. CHANGELOG не сокращать, добавить отмену. Рабочие файлы/index не трогать; git reset/clean не применять. Если ветки уже продвинулись или опубликованы, согласовать отдельный откат.

Уточнение перед Git-операцией: копия журнала перед исправлением записи об авторе — .change-backups/2026-09-30/git-main-beta/CHANGELOG.before-author-correction.md. Подтверждена неизменность 17 файлов результата E2-04 и префикса прежнего журнала.

Проверка 2026-09-30T18:01:31+03:00: main и beta указывают на a0463985eea5b02c1c5f1878e261b8422c1a4662, текущая ветка beta, дерево стартового коммита и index пусты. Код не добавлялся в коммит. Read-back выявил нормализацию переводов строк в старом префиксе журнала при уточнении автора; исходные байты восстановлены из собственной копии, новые записи сохранены. Копия до исправления: .change-backups/2026-09-30/git-main-beta/CHANGELOG.before-line-ending-repair.md. Префикс прежнего журнала побайтно сверён. Push/remote/серверных действий не было.


## 2026-10-01T10:08:31+03:00 (Europe/Moscow, UTC+3) — локальный коммит технической основы и E2-04

По текущему разрешению Олега создаётся первый локальный коммит файлов на beta. Включены существующая техническая основа E2-01–03 и локальная модель владения E2-04; main не меняется. Сообщение: «Добавлены техническая основа проекта и модель владения E2-04». Автор Oleg; использован ранее выбранный технический локальный адрес oleg@localhost только параметром команды, постоянная Git-конфигурация не меняется. Hooks/подпись отключены только на команду; push, remote, серверные действия отсутствуют.

Полный точный состав коммита:
- `.gitignore`.
- `AGENTS.md`.
- `CHANGELOG.md`.
- `CLAUDE.md`.
- `README.md`.
- `SYSTEM_ARCHITECTURE.md`.
- `SYSTEM_ENVIRONMENTS.md`.
- `SYSTEM_OWNERSHIP_CHECKS.json`.
- `SYSTEM_PLAN.md`.
- `SYSTEM_STARTUP.md`.
- `backend/.dockerignore`.
- `backend/Dockerfile`.
- `backend/config/__init__.py`.
- `backend/config/guard.py`.
- `backend/config/ownership_local_checks.py`.
- `backend/config/settings.py`.
- `backend/config/urls.py`.
- `backend/config/wsgi.py`.
- `backend/manage.py`.
- `backend/ownership/__init__.py`.
- `backend/ownership/apps.py`.
- `backend/ownership/migration_operations.py`.
- `backend/ownership/migrations/0001_initial.py`.
- `backend/ownership/migrations/0002_postgresql_ownership_guards.py`.
- `backend/ownership/migrations/__init__.py`.
- `backend/ownership/models.py`.
- `backend/ownership/services.py`.
- `backend/requirements.in`.
- `backend/requirements.lock`.
- `backend/tests/__init__.py`.
- `backend/tests/test_guard.py`.
- `backend/tests/test_ownership.py`.
- `backend/tests/test_ownership_migrations.py`.
- `backend/tests/test_runtime.py`.
- `backend/tools/bootstrap_roles.py`.
- `backend/tools/verify_ownership_recovery.py`.
- `backend/tools/verify_web_role.py`.
- `beta/config/environment.policy.json.example`.
- `beta/config/runtime.env.example`.
- `beta/deploy/Caddyfile.fragment.example`.
- `beta/deploy/beta.py`.
- `beta/deploy/compose.json`.
- `beta/deploy/compose.template.json`.
- `beta/deploy/images.lock.json`.
- `beta/deploy/reproduce.py`.
- `beta/deploy/verify_isolation.py`.
- `beta/deploy/verify_migrations.py`.
- `docs/E2-04_OWNERSHIP.md`.
- `docs/ISOLATION_ACCEPTANCE.md`.
- `docs/ROLE_CONTRACT.md`.
- `docs/RUNBOOK.md`.
- `docs/SYSTEM_DESIGN.md`.
- `frontend/.dockerignore`.
- `frontend/Dockerfile`.
- `frontend/index.html`.
- `frontend/package-lock.json`.
- `frontend/package.json`.
- `frontend/src/main.tsx`.
- `frontend/src/style.css`.
- `frontend/tsconfig.json`.
- `frontend/vite.config.ts`.
- `local/config/environment.policy.json.example`.
- `local/config/runtime.env.example`.
- `local/deploy/compose.template.json`.
- `production/config/environment.policy.json.example`.
- `production/config/runtime.env.example`.
- `production/deploy/Caddyfile.fragment.example`.
- `production/deploy/compose.template.json`.
- `tools/package_beta.py`.

Изменён только CHANGELOG.md (добавление записи); его исходная копия: .change-backups/2026-10-01/local-commit-20261001-100830/CHANGELOG.md. Служебный манифест состава и SHA-256: .change-backups/2026-10-01/local-commit-20261001-100830/manifest.json, исключён Git. Сами исходники/шаблоны не изменены. Протоколы реальных источников SYSTEM_DISCOVERY*, остальные исторические JSON/JSONSEQ-проверки, docs/design/, output/, .playwright-cli/, runtime-файлы/секреты, venv/node_modules, dist, data и резервные копии не включены, не удалялись.

Повторная проверка: 14 локальных тестов, 11 успешных, 3 PostgreSQL-пропуска; Django system check и проверка отсутствия migration drift прошли. E2-04 остаётся «На проверке», PostgreSQL/beta/restore не проверены. До commit проверить точный index, неизменность source hashes, отсутствие секретных/runtime-путей и правильную ветку; после commit — состав/tree, отсутствие staged changes и неизменность main.

Откат: сохранять рабочие файлы и поздние изменения. Если требуется отмена опубликованного/продвинутого коммита, отдельный обратный коммит с сохранением исходников; git revert коммита первого добавления файлов удалит их из дерева и рабочего каталога, поэтому автоматически его не запускать. Изменение ссылки beta назад допустимо только по отдельному запросу и после проверки отсутствия поздних коммитов/публикации, без reset --hard/clean и без удаления файлов. CHANGELOG не сокращать, добавить отмену.


## 2026-10-01T10:20:28+03:00 (Europe/Moscow, UTC+3) — исключены локальные протоколы из списка Git

По запросу Олега о многочисленных U-файлах добавлены точные корневые исключения в .gitignore для 18 существующих локальных документов/протоколов обследования и исторических проверок, а также .playwright-cli/ и output/. Эти файлы ранее сознательно не включались в первый коммит, но исключений для них не было. Файлы не удалены и не изменены. docs/design/ содержит исходники макета и не скрывается; SYSTEM_OWNERSHIP_CHECKS.json и рабочие SYSTEM_PLAN/ARCHITECTURE/ENVIRONMENTS/STARTUP продолжают отслеживаться.

Изменены только .gitignore и CHANGELOG.md. Исходные копии: .change-backups/2026-10-01/gitignore-102028/.gitignore и .change-backups/2026-10-01/gitignore-102028/CHANGELOG.md. Новые правила:
- `/SYSTEM_DISCOVERY.md`.
- `/SYSTEM_DISCOVERY_AIRFLOW.json`.
- `/SYSTEM_DISCOVERY_DB_ADDITIONAL.jsonseq`.
- `/SYSTEM_DISCOVERY_DB_CHECKS.jsonseq`.
- `/SYSTEM_DISCOVERY_DB_METADATA.json`.
- `/SYSTEM_DISCOVERY_DB_PERIOD_QUALITY.jsonseq`.
- `/SYSTEM_DISCOVERY_DB_QUALITY.jsonseq`.
- `/SYSTEM_DISCOVERY_DEPLOYED_CODE.jsonseq`.
- `/SYSTEM_DISCOVERY_DOMAIN_DETAILS.json`.
- `/SYSTEM_DISCOVERY_FINANCE_PERIODS.jsonseq`.
- `/SYSTEM_DISCOVERY_PILOT_CHECK.json`.
- `/SYSTEM_DISCOVERY_PILOT_REPEAT.json`.
- `/SYSTEM_DISCOVERY_READONLY_CHECKS.sql`.
- `/SYSTEM_DISCOVERY_VARIANTS.json`.
- `/SYSTEM_ENVIRONMENTS_BETA_PREPARATION.json`.
- `/SYSTEM_ENVIRONMENTS_CHECKS.json`.
- `/SYSTEM_ENVIRONMENTS_SERVER_CHECKS.json`.
- `/SYSTEM_STARTUP_CHECKS.json`.
- `/.playwright-cli/`.
- `/output/`.

Проверка: git check-ignore для всех перечисленных путей; git status и diff — только .gitignore/CHANGELOG и ранее неотслеживаемые исходники docs/design. Содержимое локальных протоколов/секретов не читалось, сервер/другие проекты не затрагивались. Изменение оформляется отдельным локальным коммитом beta без push.

Откат: после сравнения текущего diff и сохранения поздних правок удалить только добавленный блок исключений либо вернуть .gitignore из копии, если поздних изменений нет. CHANGELOG не сокращать, добавить отмену. Исходные документы/артефакты не удалять. Общие reset/clean не использовать.


## 2026-10-01T10:23:07+03:00 (Europe/Moscow, UTC+3) — макет интерфейса сохранён в Git

По текущему запросу Олега восемь существующих файлов docs/design добавляются отдельным локальным коммитом beta как дизайн-документация на синтетических данных, без включения в рабочий frontend/backend или изменения D1/объёма задач. Сообщение: «Добавлены макет интерфейса и документация дизайна». Файлы макета не изменялись:
- `docs/design/CHANGELOG.md`.
- `docs/design/README.md`.
- `docs/design/checksums.sha256`.
- `docs/design/grid-app.js`.
- `docs/design/grid-engine.js`.
- `docs/design/grid-style.css`.
- `docs/design/guide.html`.
- `docs/design/prototype.html`.

Изменён только корневой CHANGELOG.md добавлением этой записи; исходная копия: .change-backups/2026-10-01/design-commit-102307/CHANGELOG.md. Проверены восемь файлов, контрольные суммы checksums.sha256, текущая beta и отсутствие прежних tracked/staged изменений. После коммита проверить состав девяти файлов и чистоту рабочего дерева; main не меняется. Push, сервер, зависимости, реальные источники и данные не затрагиваются.

Откат: сохранить поздние изменения, затем при необходимости отдельным обратным коммитом убрать только добавление макета, предварительно сохранив его локальную копию; CHANGELOG не сокращать, добавить запись об отмене. Не удалять позднюю работу и не применять reset --hard/clean.


## 2026-10-01T10:40:34+03:00 (Europe/Moscow, UTC+3) — настроен origin GitHub

По переданному Олегом адресу локальному репозиторию назначается origin https://github.com/olegnikitov062/marketplace-workspace.git. До операции remotes отсутствуют, рабочая beta, index и tracked файлы чисты. Изменяется только локальная Git-конфигурация origin и добавляется эта запись в CHANGELOG.md; настройка оформляется отдельным локальным коммитом журнала. Исходная копия журнала: .change-backups/2026-10-01/origin-104034/CHANGELOG.md. Секреты/credentials из .git/config не читаются и не копируются.

Проверка: git remote get-url origin должен вернуть ровно согласованный HTTPS-адрес; main/beta refs не изменяются настройкой remote, git status после локального коммита чист. Запросов к GitHub, fetch, push, установки upstream и серверных действий нет; существование/доступность удалённого репозитория этой локальной настройкой не подтверждается. Олег публикует ветки самостоятельно после проверки коммитов.

Откат: сверить текущий URL origin с указанным и убедиться, что remote не изменён позднее; удалить только созданный origin через git remote remove origin при согласованном откате. Журнал не сокращать, добавить отмену. Рабочие файлы/ветки и чужую Git-конфигурацию не менять, reset/clean не применять.


## 2026-10-01T10:46:04+03:00 (Europe/Moscow, UTC+3) — начаты PostgreSQL-проверки E2-04 на beta

Текущее разрешение Олега «тогда делай» относится к завершению E2-04 на beta после публикации. Локальная/опубликованная beta e077a7a5aed263b50d1212176806220a7ca4f971 совпадают, сервер имеет Git и доступ к этому публичному HTTPS-репозиторию. На beta работает прежний web E2-03; его не заменяем/не перезапускаем в ходе тестов. Код на сервер получает только через Git: новая отдельная копия /home/adm_user/marketplace-workspace/beta/app/repository из ветки beta, с проверкой точной ревизии. Старые app/backend, app/frontend, deploy, secrets/data и copy E2-03 сохраняются. Никаких прямых правок серверных исходников или передачи архивов.

План разрешённых действий: clone новой Git-копии; сборка отдельного образа из существующего Dockerfile/lock; одноразовые контейнеры только тестовой сети marketplace-beta, свои PostgreSQL-тесты, создание двух фиксированных синтетических recovery БД, новый dump/restore с запретом перезаписи. Перед изменениями проверить отсутствие занятых имён/пользовательской модели и mounts; не применять prepare/start/bootstrap или прежние destructive scripts. Главную mw_beta и работающий web пока не менять; необходимость последующего применения оценить по результату.

Локально изменён пока только CHANGELOG.md добавлением этой записи. Исходные копии документов/протокола до обновления: .change-backups/2026-10-01/E2-04-beta-104604/CHANGELOG.md, SYSTEM_PLAN.md, SYSTEM_OWNERSHIP_CHECKS.json, docs/E2-04_OWNERSHIP.md и docs/RUNBOOK.md. Новая серверная Git-копия удаляется при откате только после проверки canonical path, отсутствия поздней работы и принадлежности clone; никаких общих reset/clean/prune. Новые БД/копии/образы сохранять до проверки результата и отдельного решения очистки. Серверные source исправления при выявлении ошибки — только локальный commit → push Олега → Git на сервере.


## 2026-10-01T10:53:21+03:00 (Europe/Moscow, UTC+3) — E2-04 подтверждена на PostgreSQL beta

Причина: завершение текущей E2-04 по разрешению Олега. Через Git clone получена опубликованная beta e077a7a в /home/adm_user/marketplace-workspace/beta/app/repository, без прямого изменения app/backend/frontend/deploy и без архивов. Offline Docker build нового образа e2-04-e077a7a не прошла: pip-layer не кэширован, сеть отключена, новые зависимости/образы не установлены. Проверки продолжены существующим образом E2-03 с совпадающим lock и read-only Git source mount; прямых серверных source-исправлений нет.

Проверки выполнены, реальные результаты SSH: PostgreSQL 17.11; 17 Django tests успешно без пропусков, включая две организации/права одного пользователя, смешанные FK/raw UPDATE/DELETE, архивы/историю, конкуренцию, 0002 reverse/forward с сохранением строки и 0001 zero/forward на пустой одноразовой схеме. Test DB test_mw_beta_test и одноразовые test/web контейнеры удалены штатным teardown. Seed/dump/restore/verify двух новых собственных синтетических БД прошли, данные/миграции совпадают; повторно проверены FK/история/DELETE. В restore: 3 validated composite FK, 15 triggers, 2 организации/2 членства/2 версии. Web role DDL/system DB CONNECT denied, admin/migration privileges отсутствуют. Старый dump E2-03 SHA-256 неизменен. Работающий web ID/image/StartedAt неизменны; главная mw_beta не мигрировалась, web не пересоздавался. Это не деплой нового работающего web.

Изменены только локальные CHANGELOG.md, SYSTEM_PLAN.md (единственный статус E2-04 → Готово, остальные задачи/критерии неизменны), SYSTEM_OWNERSHIP_CHECKS.json, docs/E2-04_OWNERSHIP.md, docs/RUNBOOK.md. Исходные копии перед этой операцией: .change-backups/2026-10-01/E2-04-beta-104604/ с сохранением относительных путей пяти файлов. Протокол результата с ревизией, image ID, mounts, dump paths/hashes и границами: SYSTEM_OWNERSHIP_CHECKS.json. Манифест локальных файлов и hashes: .change-backups/2026-10-01/E2-04-beta-104604/manifest.json. Изменения оформляются локальным commit beta, push выполняет Олег.

Новые серверные артефакты: Git clone beta/app/repository/ (с .git и точной ревизией), две БД mw_beta_test_e2_04_recovery/mw_beta_test_e2_04_restore в только postgres-test, beta/backups/test/e2-04-20261001T074853Z.dump, SHA-256 9be0c324e2b8a0ed291ad71e9b07965ddac2f5a7f4fe836251726eac22fc22be. Они сохранены, не удалялись. Незавершённая offline build могла создать промежуточные Docker cache layers; prune не выполнялся. Старые restore DB/dump, runtime secrets/data и текущий web сохранены. Production/Caddy/FBS/WB API/Finkos, реальные источники/персональные данные, внешние сообщения и следующие задачи не затрагивались. Служебные DB credentials потреблялись внутри собственных контейнеров, значения не выводились/не экспортировались.

Откат: сначала сравнить текущие hashes с manifest.json, сохранить позднюю работу; применить только обратные правки плана/документов/протокола из пяти исходных копий. CHANGELOG не сокращать, добавить отмену. На главной beta нет миграций/перезапусков для отката. Новую Git-копию и синтетические БД/dump удалять только по отдельному решению после проверки canonical path/ревизии/имён/отсутствия поздней работы; существующие данные/копии E2-03 не трогать. Не применять reset --hard/clean, root deletion, Docker prune или восстановление dump поверх живой БД.


## 2026-10-01T11:24:21+03:00 (Europe/Moscow, UTC+3) — подготовлен локальный жизненный цикл аккаунта E2-05

Основание: текущий запрос Олега только на E2-05, локальные коммиты beta разрешены; push выполняет Олег. До работы beta/HEAD 2cfec7e, дерево чистое. Read-only git ls-remote подтвердил remote beta e077a7a5aed263b50d1212176806220a7ca4f971: 2cfec7e на момент проверки не опубликован. Первоначальный сетевой отказ обходился разрешённым read-only запросом с расширенным сетевым доступом; сервер проекта не опрашивался. Состояние web/главной beta E2-03 взято из исходного протокола, не из новой live-проверки.

Добавлены accounts: отдельный синтетический контакт, приглашение с SHA-256/сроком/снимком области, атомарное принятие/повтор/отзыв, штатные Django password forms/session login/logout/reset, операторская глобальная блокировка с инвалидацией старого пароля/session/reset, locmem-only доставка, CSRF и счётчики попыток/категории отказов. Схема владения и миграции E2-04 не менялись. Граница E2-06 заранее обозначена: только сессия входа и блокировка; TOTP/полное управление сессиями/экспорты не реализованы. Олег подтвердил предварительные 24 часа invitation/30 минут recovery, pending-only повтор той же области и операторскую блокировку без обхода приглашением; прочие лимиты/срок сессии и ограничения выдачи owner/присоединения существующей личности остаются консервативной тестовой конфигурацией, не принятой D3/D7.

Точный состав связанного изменения (пути относительно C:/Users/krolo/Documents/marketplace-workspace):
- `CHANGELOG.md`.
- `SYSTEM_ACCOUNT_CHECKS.json`.
- `SYSTEM_PLAN.md`.
- `backend/accounts/__init__.py`.
- `backend/accounts/apps.py`.
- `backend/accounts/backends.py`.
- `backend/accounts/delivery.py`.
- `backend/accounts/limits.py`.
- `backend/accounts/management/__init__.py`.
- `backend/accounts/management/commands/__init__.py`.
- `backend/accounts/management/commands/block_personal_account.py`.
- `backend/accounts/migrations/0001_initial.py`.
- `backend/accounts/migrations/0002_immutable_invitation.py`.
- `backend/accounts/migrations/__init__.py`.
- `backend/accounts/models.py`.
- `backend/accounts/policy.py`.
- `backend/accounts/services.py`.
- `backend/accounts/urls.py`.
- `backend/accounts/views.py`.
- `backend/config/accounts_local_checks.py`.
- `backend/config/settings.py`.
- `backend/config/urls.py`.
- `backend/tests/test_account_transactions.py`.
- `backend/tests/test_accounts.py`.
- `backend/tests/test_runtime.py`.
- `backend/tools/check_accounts_postgresql.py`.
- `backend/tools/verify_account_recovery.py`.
- `docs/E2-05_ACCOUNTS.md`.
- `docs/RUNBOOK.md`.

Исходные копии шести существующих файлов сохранены до изменения в `.change-backups/2026-10-01/E2-05-local/` с теми же относительными путями: backend/config/settings.py, backend/config/urls.py, backend/tests/test_runtime.py, SYSTEM_PLAN.md, docs/RUNBOOK.md, CHANGELOG.md. Существующие CRLF settings.py сохранены. Служебный manifest.json в этой папке хранит точные новые/изменённые пути и hashes; копии исключены Git. Новые файлы — все пути в составе, кроме этих шести. Генерируемые Python caches исключены Git; SQLite test schema была только в памяти и удалена тестовым runner.

Проверки: существующий Python 3.14.7/Django 5.2.17, pip check без ошибок. 63 теста SQLite in-memory: 51 успешно, 12 явных skips (8 E2-05 PostgreSQL, 3 E2-04 PostgreSQL, 1 PostgreSQL runtime). Проверены действующий/истёкший/использованный/отозванный токены, замена, правильный/неправильный пароль, блокировка/старые сессии/reset, recovery одноразовость/истечение, две организации/запрет повышения и чужих связей, CSRF включая anonymous и Origin, отсутствие SMTP, лимиты, offline миграции/возврат. Django check, migration drift check, AST 24 Python-файлов и whitespace check с учётом CRLF прошли. Первые HTTP-тесты выявили отсутствие Origin у HTTPS test client и обработку пустого POST без Content-Type; исправлены тестовый запрос same-origin и допустимость пустого тела операций без полей, CSRF не отключался. Последний полный прогон успешен.

E2-05 оставлена «На проверке»: PostgreSQL/конкуренция/триггеры/реальные миграции/restore и ограниченная web-role HTTP проверка не выполнялись. SYSTEM_PLAN обновлён по этому результату, протокол SYSTEM_ACCOUNT_CHECKS.json и docs/E2-05_ACCOUNTS.md содержат факты, ограничения и точный A/B план серверных проверок. Новые guarded scripts заранее отказываются от занятых тестовых БД; любые skips PostgreSQL-приёмки считаются ошибкой. Текущая web-роль SELECT-only недостаточна для lifecycle, её DML grants/backup/обновление web требуют отдельной подготовки и разрешения. Никаких установок, SSH, серверных миграций/перезапусков, push, production/main/Caddy/FBS/WB/Finkos, реальных источников, адресатов или данных.

Изменение оформляется одним локальным коммитом beta автора Oleg: «Добавлен жизненный цикл личного аккаунта E2-05». Перед commit проверить точный index, hashes, отсутствие runtime/secret/backup-путей; после — автор, состав, чистоту дерева и неизменность main. Значения паролей/токенов/писем/секретов в журнал или протокол не включены.

Откат: сначала сравнить текущие hashes с manifest.json и сохранить позднюю работу. Применять только обратный diff этого изменения, цельные шесть исходных копий — исключительно без поздних правок; CHANGELOG не сокращать, добавить отмену. Новые файлы удалять только по манифесту при совпадении hashes и отсутствии поздней работы/потребителей, сначала убрать регистрацию accounts/URL. Локальный commit отменять отдельным согласованным обратным изменением, не reset --hard/clean. accounts 0002 reverse/forward сохраняет строки, но временно снимает защиту; accounts zero удаляет свои таблицы и допустим только на пустой одноразовой схеме. Заполненную БД восстанавливать только в отдельную новую БД из проверенного dump; главная beta этим изменением не затронута. Будущие A/B БД/dump не удалять автоматически, старые E2-03/E2-04 артефакты сохранять.


## 2026-10-01T11:43:44+03:00 (Europe/Moscow, UTC+3) — E2-05 проверена на PostgreSQL, выполнены A/B

Основание: текущее «да разрешаю» Олега на Git pull beta, изолированные PostgreSQL-тесты и синтетический dump/restore; главная БД и работающий web исключены. Публикация beta 342192b4296c84152f3da0934715816562c9fe9f подтверждена; серверный чистый checkout /home/adm_user/marketplace-workspace/beta/app/repository обновлён с e077a7a только Git pull --ff-only. Никаких source-архивов/ручных server source правок. Совпали image E2-03 sha256:eade0170f4aaf5984fc22664d479f30bfc8dac085c9d31b78e70190aeb810e4b и requirements.lock SHA-256 c037270b5ef4e3d83696959bbf7d62eee9021e122877a28efdb2b975020efd21. Новая сборка/установка не выполнялась. Git backend фактически монтировался /workspace:ro, test-контейнер подключён только test-private.

Реальные результаты SSH: PostgreSQL 17.11, 63 tests за 75.687 s, все успешны без skips; concurrent accept/recovery/reinvite/block/counters, immutable raw SQL, forward/reverse/forward и пустая accounts zero/forward, regression E2-04. Django check и migration drift check прошли. Django test_mw_beta_test и одноразовые контейнеры удалены штатно. Новый guarded seed/dump/restore/verify прошёл: обе БД равны по ownership/accounts/sessions/миграциям, поведенческие проверки входа/восстановления/блокировки/повтора и SQL-ограничения после restore успешны, их транзакции откачены. В restore 2 организации, 5 synthetic User, 6 Membership, 4 контакта, 4 приглашения, 0 сессий и 2 новых защитных триггера.

Новые серверные артефакты: БД mw_beta_test_e2_05_recovery и mw_beta_test_e2_05_restore только в postgres-test, owner mw_beta_test_runner; /home/adm_user/marketplace-workspace/beta/backups/test/e2-05-20261001T083919Z.dump, mode 0600, SHA-256 4d5aa823d68bf109f1b8801bad893ee50f07e0966e7c1ebac69b1cbac93063d8. Пустота restore до восстановления проверена. БД/dump сохранены; seed повторно не запускать, имена заняты. Dump не экспортирован. Старые E2-03/E2-04 dumps сохранили SHA-256. Permission denied при checksum E2-04 от SSH-пользователя решён чтением внутри своего postgres-test без смены прав; ошибка последнего CRLF после /dev/null остановила одну shell-команду до запуска контейнера, исправлена передача команды. Source-исправлений не требовалось.

Главная mw_beta до/после: только contenttypes:2. Web ID 78a7513c20dc2d851d80c60b055cb337f02f03aa024b96ebca573e2f696f2141, StartedAt 2026-09-30T13:13:33.547827254Z и image неизменны; ready успешен. Оба постоянных PostgreSQL контейнера также сохранили ID/image/StartedAt. Read-only SQL подтвердил web без superuser/CREATEDB/CREATEROLE/BYPASSRLS, SELECT=true и UPDATE=false на django_migrations. Grants не менялись. Главная beta не мигрировалась и web не перезапускался; это не новый работающий web.

Изменены только локальные файлы:
- `CHANGELOG.md`.
- `SYSTEM_PLAN.md`.
- `SYSTEM_ACCOUNT_CHECKS.json`.
- `docs/E2-05_ACCOUNTS.md`.
- `docs/RUNBOOK.md`.

Причина: сохранить фактические результаты A/B и оставшийся разрыв. Исходные копии пяти файлов до правок: .change-backups/2026-10-01/E2-05-beta/ с исходными относительными путями; manifest.json там содержит исходные/итоговые hashes. E2-05 оставлена «На проверке»: lifecycle под ограниченной web-ролью и необходимые DML/column grants ещё не проверены; test_runner их не заменяет. Пункт C требует отдельного плана/разрешения. Локальный коммит автора Oleg: «Подтверждены PostgreSQL-проверки и восстановление E2-05». Push выполняет Олег, агент push не выполнял. Код E2-05 не менялся; статусы/критерии остальных задач сохранены. Production/main/Caddy/FBS/WB/Finkos, реальные источники/данные/отправки, E2-06 и зависимости не затрагивались.

Откат: сначала сравнить hashes и сохранить позднюю работу; вернуть только обратные изменения документов/протокола из этих копий, CHANGELOG не сокращать, добавить отмену. Главная beta не требует миграционного отката. Обновлённую серверную Git-копию не откатывать автоматически; возврат ревизии только после проверки чистоты/поздних коммитов и отдельного решения, без reset --hard/clean. Новые две БД/dump сохранять до отдельного решения очистки; перед удалением проверить точные имена/canonical path/принадлежность и отсутствие поздней работы. Старые БД/dump/config/secrets/data не трогать, общий prune не применять, поверх живой БД не восстанавливать.


## 2026-10-01T12:14:52+03:00 (Europe/Moscow, UTC+3) — подготовлены права web и проверка E2-05 под ограниченной ролью

Основание: «делай» после предложения подготовить конкретные DML-права/проверку; только локальная подготовка C, серверное применение отдельно. Публикация предыдущего 7ad6b67 подтверждена read-only ls-remote; агент push не выполнял. Причина: успешные A/B под test_runner не доказывают достаточность/ограниченность web-привилегий.

Подготовлен точный column INSERT/UPDATE и DELETE только sessions, без blanket DML/sequence grants/GRANT OPTION/DDL/членства в миграторе. Apply/revoke проверяют beta/роль/миграции/ACL и работают транзакционно, отказываются при позднем расширении прав. PostgreSQL row locks требуют UPDATE колонки: явно предложены два SECURITY INVOKER BEFORE UPDATE OF id guards на Organization/Membership, запрещающие web менять id даже на прежний. Поля/связи/миграции E2-04 не менялись; guards применяются/отзываются вместе с SQL-привилегиями. Это не RBAC/RLS и не защита от произвольного SQL с INSERT membership: области и роли пользователя проверяет сервис E2-05.

C1 probe создаёт только новую синтетическую БД/LOGIN-роль mw_beta_test_e2_05_web, отказывает при занятых именах, проверяет grant/revoke/reapply, настоящий limited LOGIN session_user, HTTP/CSRF lifecycle, SQL-отказы и невозможность RESET/SET ROLE эскалации. Callback блокировки отдельно выполняется runner. Пароль только в памяти; statement/error statement logging административного соединения отключён на создание verifier; finally отключает новую роль и удаляет verifier, БД сохраняется. Обрыв процесса требует отдельного readback/отключения своей роли. C2 пока лишь конкретный план backup/restore, Git worktree и read-only overlay существующего образа, main migration/grant и web-only update с откатом. Новых зависимостей/публичной доставки/сессий E2-06/дальнейших задач нет.

Точный состав изменения (пять существующих и десять новых файлов):
- `CHANGELOG.md`.
- `SYSTEM_PLAN.md`.
- `SYSTEM_ACCOUNT_CHECKS.json`.
- `docs/E2-05_ACCOUNTS.md`.
- `docs/RUNBOOK.md`.
- `backend/tools/account_web_grants.py`.
- `backend/tools/manage_account_web_grants.py`.
- `backend/tools/account_role_scenario.py`.
- `backend/tools/verify_account_web_role.py`.
- `backend/tools/verify_account_web_runtime.py`.
- `backend/tests/test_account_role_preparation.py`.
- `beta/deploy/compose.accounts-check.json`.
- `beta/deploy/compose.accounts-web.json`.
- `beta/deploy/e2_05_main_before_checks.sql`.
- `docs/E2-05_WEB_ROLE.md`.

Первые пять исходных файлов сохранены до правок в `.change-backups/2026-10-01/E2-05-web-role/` с исходными относительными путями. Служебный manifest.json содержит исходные/итоговые SHA-256 и список новых файлов, каталог исключён Git. Параллельные изменения docs/SYSTEM_DESIGN.md и docs/design/{grid-app.js,grid-style.css,guide.html,prototype.html} сохранены вне этого изменения/коммита.

Проверки: 67 SQLite in-memory tests — 55 успешно, 12 прежних PostgreSQL/runtime skips; четыре новых теста повторно успешны после уточнений. Django check, makemigrations --check --dry-run, pip check, AST шести новых Python-файлов, JSON overlays/границы сервисов и whitespace прошли. Default SQL plan не делает Django setup/подключение. Проверены неизменность всех 101 строк задач, автор/состав commit и отсутствие посторонних путей в index. Новые PostgreSQL grants/guards/identity и Docker Compose runtime ещё не проверены. Прежние A/B: 63 PostgreSQL-теста и synthetic dump/restore на 342192b; это отдельное доказательство, не проверка новой подготовки.

Сервер в этом изменении не опрашивался/не менялся: нет новых серверных БД/ролей/GRANT/миграций/рестартов. E2-05 «На проверке», точные C1/C2 требуют push Олега и отдельных разрешений. Последний подтверждённый web/главная БД остаются E2-03. Локальный коммит автора Oleg: «Подготовлены права web и проверка E2-05 под ограниченной ролью». Production/main/Caddy/FBS/WB/Finkos, реальные данные/источники/отправки не затронуты; токены/пароли/ссылки/персональные данные не включены в отчёты.

Безопасный откат: сравнить hashes manifest с текущими файлами, сохранить позднюю работу; применять только обратный diff, CHANGELOG не сокращать, добавить отмену. Цельные пять копий возвращать только при отсутствии поздних изменений. Десять новых файлов удалять только при совпадении hashes и отсутствии поздних потребителей; отдельный согласованный reverse commit, без reset --hard/clean. Серверного отката сейчас нет. После будущего C1 сохранять новую БД/NOLOGIN роль; после будущего C2 сначала вернуть только web на исходный base compose/E2-03 image, затем guarded revoke точных DML/guards. Добавочные таблицы/данные/worktree/dumps сохранять; zero/live restore/общий prune запрещены.

Уточнение 2026-10-01T12:16:29+03:00: перед окончательным оформлением того же локального коммита восстановлен исходный LF в SYSTEM_PLAN.md и SYSTEM_ACCOUNT_CHECKS.json, чтобы diff не содержал массовой смены окончаний строк. Промежуточные копии этих двух файлов и CHANGELOG сохранены в .change-backups/2026-10-01/E2-05-web-role/before-eol-normalization/. Семантика неизменна; повторно проверены hashes, состав и whitespace. Коммит не публиковался агентом.


## 2026-10-01 12:21:48 МСК (UTC+3) — светлая и тёмная темы локального дизайна

По запросу пользователя добавлены две темы с переключателем в шапке и настройках. Светлая остаётся начальной. Выбор хранится в настройках каждого демо-профиля, не меняет черновики и сохранённые виды и восстанавливается до запуска интерфейса. Цвета колонок и правил адаптируются к тёмному фону с сохранением исходных значений; все настройки таблицы доступны в обеих темах. Печать использует светлую палитру. Описание системы синхронизировано.

Изменённые файлы:

- `docs/design/prototype.html`.
- `docs/design/grid-app.js`.
- `docs/design/grid-style.css`.
- `docs/SYSTEM_DESIGN.md`.
- `docs/design/guide.html`.
- `docs/design/README.md`.
- `docs/design/checksums.sha256`.
- `CHANGELOG.md`.

До правок сохранены и сверены SHA256 копии восьми существовавших файлов в `.change-backups/2026-10-01/design-themes-1209/` с теми же относительными путями. Каталог исключён Git; `qa-before.json` в нём содержит исходный список проверочных артефактов. Перед добавлением записи журнал уже содержал более поздние изменения; дополнительно сохранён CHANGELOG.before-append.md в той же папке.

Новые проверочные файлы:

- `.playwright-cli/page-2026-10-01T09-12-02-197Z.yml`.
- `output/playwright/themes-20261001/dark-card.png`.
- `output/playwright/themes-20261001/dark-groups.png`.
- `output/playwright/themes-20261001/dark-mobile.png`.
- `output/playwright/themes-20261001/dark-settings.png`.
- `output/playwright/themes-20261001/dark.png`.
- `output/playwright/themes-20261001/light-mobile.png`.
- `output/playwright/themes-20261001/light.png`.
- `output/playwright/themes-20261001/server.stderr.log`.
- `output/playwright/themes-20261001/server.stdout.log`.

Проверка: node --check; git diff --check с cr-at-eol; реальный Edge, 1440/1024/768/390/360 px. Проверены переключатель/Space/настройки, сохранение после reload, изоляция профилей, неизменность черновика при смене темы, группы, цветные колонки, правила, карточка, пустой результат и мобильное меню. Отдельно до grid-app.js при загруженном CSS подтверждён тёмный фон rgb(23,26,32). В print media фон белый. Для восьми оттенков измерены 16 сочетаний текста/единицы с фоном: минимум 5,32:1. Завершающие сценарии без ошибок JS и console warnings/errors. Исправлены обнаруженные при проверке white-space и фон выбора профиля; CSS обновлён без кэша. В документах сверены 514 текстовых блоков/ячеек, структура и локальные ссылки. Это проверка макета в Edge, не полный аудит доступности; другие браузеры, fallback старых браузеров и физическая печать не проверялись.

Откат: сначала сравнить текущие файлы с выдаваемыми hashes в docs/design/checksums.sha256 и учесть более позднюю/постороннюю работу. Если файлы не менялись после этой выдачи, восстановить только семь изменённых файлов дизайна из указанной копии; при поздних изменениях применить только обратные изменения темы вручную. CHANGELOG.md целиком не восстанавливать: сохранить его историю и добавить запись об откате. Новые проверочные файлы удалять только по точному списку выше после сверки, что они всё ещё относятся к этой проверке и не содержат более поздней работы. Общие каталоги и остальные файлы не удалять; git reset/clean не использовать.

Изменение ограничено локальным дизайном. Frontend/backend, незавершённая работа E2-05, основной план, production/beta и finkos-analytics не изменялись в этой задаче; зависимости не устанавливались, commit/push/deploy не выполнялись. Собственный Edge-сеанс и локальный сервер 127.0.0.1:18767 остановлены после проверки личности процесса.


### 2026-10-01 12:34:00 МСК (UTC+3) — подготовка авторизованного коммита темы

По явному запросу пользователя подготовлен локальный коммит в beta: «Добавлены светлая и тёмная темы макета». Состав — те же восемь файлов дизайна и журнала из записи выше; резервные копии и снимки не включаются. Перед коммитом восстановлен исходный LF в docs/design/grid-style.css и docs/design/checksums.sha256, обновлён SHA256 CSS; смысл и проверенное поведение не изменены. Промежуточные версии этих двух файлов и CHANGELOG.md сохранены в `.change-backups/2026-10-01/design-themes-commit-123400/` с теми же относительными путями. Проверены все восемь hashes, node --check и whitespace с cr-at-eol; индекс перед подготовкой пуст. Коммит выполняется под именем Oleg без публикации.

Откат подготовки: сначала сравнить более поздние изменения; восстановить только окончания строк и контрольную сумму из указанных копий, не сокращая журнал. Откат коммита — отдельное обратное изменение только этого коммита после проверки его состава, с сохранением последующих правок и новой записью в CHANGELOG; без reset/clean.


## 2026-10-01T12:52:24+03:00 (Europe/Moscow, UTC+3) — выполнен C1, исправлена проверка прав последовательностей

Основание: Олег сообщил «залил и даю разрешение» на C1. Публикация 3f4a5b052acce7233d2484c6c039f788900fc1d8 подтверждена ls-remote; включает подготовку 06d4728 и отдельный коммит макета. Серверный чистый beta checkout /home/adm_user/marketplace-workspace/beta/app/repository обновлён Git pull --ff-only с 342192b. Исходники переданы только Git; макет не развёртывался. Существующий E2-03 image/lock совпали; новая сборка/установка не выполнялась. Compose overlay config --quiet прошёл.

Запущен разрешённый account-role-check, PostgreSQL 17.11. Новые собственные БД/роль mw_beta_test_e2_05_web; owner mw_beta_test_runner, marker проверен. Миграции accounts:2/auth:12/contenttypes:2/ownership:2/sessions:1, синтетические Organization=2/User=1/Membership=2/Contact=0/Invitation=0/AuthDenial=0. C1 FAIL до HTTP: has_sequence_privilege вызвана на TOAST-таблице, поскольку WHERE не гарантирует порядок вычисления. Причина воспроизведена read-only SQL. Транзакция подготовки ACL откатилась: guard=0, SELECT User/UPDATE password=false. Finally и SQL readback подтвердили NOLOGIN/PASSWORD NULL и отсутствие опасных атрибутов. Одноразовый контейнер удалён; БД/роль сохранены. Grant/revoke/reapply и lifecycle под limited LOGIN ещё не доказаны.

После отказа main beta contenttypes:2 и web SELECT-only на django_migrations неизменны; ID/image/StartedAt web и двух PostgreSQL контейнеров совпали, readiness 200. Два SSH banner timeout не дали результатов, readback получен следующим подключением. Шаблоны Docker inspect сначала ошиблись на отсутствующем Health/экранировании; отдельного runtime mount/network inspect краткоживущего контейнера нет. Первый inline docker exec без закрытого stdin поглотил оставшуюся часть SSH-скрипта; SQL-проверки выполнены отдельно и подтверждены выводом. Серверные source/конфигурации вручную не редактировались, C2/main migrations/grants/restart/другие проекты не выполнялись.

Исправлены локально CASE-ограждение sequence privilege function, безопасная диагностика класса/SQLSTATE без текста ошибки и фиксированные новые имена mw_beta_test_e2_05_web_v2 для будущего повтора. Первые объекты не переиспользуются/не удаляются; новое имя ещё требует разрешения. Добавлен PostgreSQL regression test. Точный исправленный SQL реально проверен read-only на PostgreSQL: 0 доступных sequences для disabled probe role, 6 для bootstrap, 84 pg_toast-объекта; ошибки нет. Это не полный повтор C1. Локально 68 тестов за 13.004 s, 55 успешно и 13 skips (12 прежних и новый PostgreSQL test); AST/JSON/whitespace и 101 неизменная строка задач проверены. Действия PostgreSQL A/B на 342192b остаются отдельным прежним доказательством.

Точные локальные файлы:
- `backend/tools/account_web_grants.py`.
- `backend/tools/verify_account_web_role.py`.
- `backend/tests/test_account_role_preparation.py`.
- `CHANGELOG.md`.
- `SYSTEM_PLAN.md`.
- `SYSTEM_ACCOUNT_CHECKS.json`.
- `docs/E2-05_WEB_ROLE.md`.

Все семь исходных файлов сохранены до изменения в .change-backups/2026-10-01/E2-05-C1-fix/ с теми же путями; manifest.json хранит исходные/итоговые SHA-256. Новых tracked файлов нет. Исходные окончания строк сохранены; журнал дополнен, чужой коммит дизайна сохранён. E2-05 остаётся «На проверке», C2 не разрешён. Коммит автора Oleg: «Исправлена проверка прав последовательностей после C1». Push делает Олег; агент push не выполняет. Пароли/токены/письма/персональные данные не записаны в отчёт.

Откат: сверить manifest и поздние правки, сохранить текущую работу; применить только обратный diff к шести файлам кроме журнала, CHANGELOG дополнить отменой. Цельные копии использовать только при отсутствии поздней работы; не reset/clean. Серверную Git-копию автоматически не откатывать. Сохранить БД/NOLOGIN роль первой попытки и старые A/B/dumps; очистка только по отдельному решению после сверки точных имён/owner/меток/поздней работы. Главная beta не требует отката. Повтор v2 только из опубликованного Git после разрешения новой БД/роли; никаких ручных исправлений исходников или live restore.


## 2026-10-01T13:37:23+03:00 (Europe/Moscow, UTC+3) — подтверждён C1 E2-05 под ограниченной LOGIN-ролью

Основание: явное «разрешаю» Олега на повтор C1 с mw_beta_test_e2_05_web_v2 после проверки push 82b200465e15b447a43ed3d36d4522f11742bee1. Две попытки SSH banner timeout не выполняли команд; связь восстановлена. Чистый серверный beta checkout /home/adm_user/marketplace-workspace/beta/app/repository обновлён только Git pull --ff-only с 3f4a5b0 до 82b2004. requirements.lock совпал с исходным E2-03, существующий image sha256:eade0170f4aaf5984fc22664d479f30bfc8dac085c9d31b78e70190aeb810e4b, без build/install. Compose config --quiet успешен. Runtime inspect краткоживущего контейнера подтвердил read-only Git backend /workspace и единственную marketplace-beta-test-private сеть.

C1 PASS/exit 0 на PostgreSQL 17.11: создана только новая синтетическая БД/LOGIN-роль mw_beta_test_e2_05_web_v2, owner mw_beta_test_runner, фиксированные метки проверены. Миграции accounts:2/auth:12/contenttypes:2/ownership:2/sessions:1. Успешны точный ACL/guards audit, grant/revoke/reapply, настоящий limited LOGIN session_user=current_user, весь подготовленный HTTP lifecycle/CSRF scenario, 13 SQLSTATE 42501 отрицательных операций, чужих CONNECT=0 и отсутствие RESET ROLE эскалации. Callback доверенной блокировки отдельно runner; запросы после него limited LOGIN. Locmem/example.invalid, без реальной доставки/данных/источников, без вывода credential/token/link/email contents.

Последующий readback: новая роль NOLOGIN/PASSWORD NULL, опасные атрибуты=false; Org=2/User=2/Membership=3/Invitation=2/Contact=1/AuthDenial=7, web guards=2. UPDATE User.password=true, is_active/Membership.role/migration UPDATE=false. Контейнер удалён, БД/роль сохранены. Первая БД/роль без _v2 сохранены с прежними 2/1/2/0 org/user/member/invite, guards=0, NOLOGIN/PASSWORD NULL. Старые A/B/dumps не использовались/не изменялись операциями этого запуска; их hashes повторно не читались.

Main beta до/после contenttypes:2, main web SELECT-only на django_migrations и опасные атрибуты=false; ID/image/StartedAt web и двух PostgreSQL контейнеров совпали, readiness 200. Главные grants/migrations/restart/C2 не выполнялись. Полный 68 unittest-набор не повторялся: отдельный C1 дополняет прежние A/B 63/63 и dump/restore на 342192b. UI/browser/TLS/полный RBAC/E2-06 не проверялись и не реализовывались. E2-05 остаётся «На проверке» до main beta C2.

Изменены только шесть локальных документов/протокол:
- `CHANGELOG.md`.
- `SYSTEM_PLAN.md`.
- `SYSTEM_ACCOUNT_CHECKS.json`.
- `docs/E2-05_WEB_ROLE.md`.
- `docs/E2-05_ACCOUNTS.md`.
- `docs/RUNBOOK.md`.

Причина: сохранить действительные результаты C1 и убрать его из недостающих проверок. Для C2 явно закреплена проверенная кодовая ревизия 82b2004 вместо позднего отчётного коммита. Исходные шесть файлов сохранены до изменения в .change-backups/2026-10-01/E2-05-C1-v2/ с теми же относительными путями; manifest.json хранит исходные/итоговые hashes. Новых tracked файлов нет, код/зависимости/ownership migrations не менялись. Проверены JSON, whitespace, неизменность всех 101 строк задач и append-only журнала. Локальный commit автора Oleg: «Подтверждён C1 E2-05 под ограниченной ролью». Push делает Олег; агент push не выполняет. Production/main/Caddy/FBS/WB/Finkos и прочие проекты не затронуты.

Откат: сверить hashes и позднюю работу, сохранить текущие файлы, применить только обратный diff документов; CHANGELOG не сокращать, дополнить отменой. Цельные копии возвращать только при отсутствии поздних правок, без reset/clean. Серверный checkout/две C1 БД/NOLOGIN роли/dumps автоматически не откатывать и не удалять. Их очистка только по отдельному решению после проверки точных имён/меток/owner/поздней работы. Главная beta отката не требует. C2 требует отдельного разрешения: новый main dump/restore, main migrations/grants, Git worktree 82b2004, web-only restart и smoke; безопасный откат описан в E2-05_WEB_ROLE.md §4.


## 2026-10-01T13:55:12+03:00 (Europe/Moscow, UTC+3) — выполнен C2 и завершена E2-05

Основание: явное разрешение Олега на C2 («я разрешаю») и последующая публикация b1a9450, подтверждённая ls-remote. Серверный чистый beta checkout обновлён Git pull --ff-only до b1a9450; проверенный C1 код 82b200465e15b447a43ed3d36d4522f11742bee1 закреплён отдельным detached worktree `/home/adm_user/marketplace-workspace/beta/app/releases/82b200465e15b447a43ed3d36d4522f11742bee1`. Backend/deploy совпали, lock совпал с исходным image E2-03. Источники получены только Git, без архивов/ручных серверных source/config правок, новых зависимостей или image build.

Перед изменением main БД strict проверка подтвердила только django_content_type/django_migrations. Сохранены новые `/home/adm_user/marketplace-workspace/beta/backups/database/e2-05-main-before-20261001T104501Z.dump` и `.acl.json`, оба mode 0600/noclobber. Dump SHA-256 f907f239df68cac7024187119deeea9c6b06097f7e1b618a2371d2d3557d77f9; ACL snapshot SHA-256 956cb7dd4fa981aac9dc48ab2856242ad178dbfd1aea71411b60667a4c1d0653. Snapshot — технические ACL/role flags без credentials. Restore выполнен только в новую mw_beta_test_e2_05_main_before (owner runner, PUBLIC CONNECT=false), --no-owner/--no-acl, сравнение fingerprints прошло: contenttypes 1/b2b3bb1ab957a0ae8833982992db0dd6, migrations 2/aa0f915a312d92d1509a616fd09894a2. Hashes файлов повторно совпали после применения; артефакты сохранены/не экспортированы, старые backups не перезаписывались.

Django check, migration plan и forward sqlmigrate ownership/accounts 0001/0002 проверены; применены 17 новых миграций (итого accounts2/auth12/contenttypes2/ownership2/sessions1). Guarded exact main DML apply с pre/post ACL проверкой завершён транзакционно. Пересоздан только web через Git overlay, PostgreSQL контейнеры не перезапускались. C2 PASS: actual mw_beta_web, exact ACL/guards, live/ready200, session401/login GET405. Новый web ID b2d0be7a01c46d46d584b247394fca7e56021ef797d26840cbf75d355614faf8, StartedAt 2026-10-01T10:47:55.161037866Z; image sha256:eade0170f4aaf5984fc22664d479f30bfc8dac085c9d31b78e70190aeb810e4b, backend read-only 82b2004, сеть только private, host ports отсутствуют. Base compose hash неизменен ed9da6bed25a22bf4c0cec2cc31c3d9df8a684bef2b395ce6e8f1d57b61e072a.

Финальный readback: PostgreSQL17.11, 15 ownership guards/3 composite FK/2 account immutable guards/2 web guards; users/org/member/contact/invite/session main=0. Main TEMPORARY=true было и сохранено по плану, schema/DB CREATE и чужой CONNECT запрещены; это не main TEMP denial/RLS/полный RBAC. Обе C1 роли NOLOGIN/PASSWORD NULL, old C1 БД сохраняются. Одноразовые migrate-контейнеры удалены, checkout/worktree чистые. Два SSH banner timeout финального чтения не выполнили команд, результат подтверждён следующим соединением. C2 не повторяет 68 unittest-тестов: A/B63/63 и dump/restore на342192b, C1 limited LOGIN на82b2004, C2 actual runtime — отдельные доказательства.

Локально изменены только документы/протокол:
- `CHANGELOG.md`.
- `SYSTEM_PLAN.md`.
- `SYSTEM_ACCOUNT_CHECKS.json`.
- `SYSTEM_STARTUP.md`.
- `SYSTEM_ENVIRONMENTS.md`.
- `docs/E2-05_WEB_ROLE.md`.
- `docs/E2-05_ACCOUNTS.md`.
- `docs/RUNBOOK.md`.

Все восемь исходных файлов до правок сохранены в .change-backups/2026-10-01/E2-05-C2/ с прежними относительными путями; manifest.json содержит исходные/итоговые SHA-256. Новых tracked файлов нет, исходные окончания строк сохранены, журнал append-only. SYSTEM_PLAN: изменён только статус E2-05 на «Готово», остальные 100 строк/критерии/зависимости неизменны. Startup/runbook/env явно отделяют текущий Git overlay от исторического E2-03 base-only запуска. JSON/whitespace/состав и status-only изменение строки E2-05 проверены. Локальный коммит Oleg: «Завершена E2-05 и обновлена основная beta». Push не выполнялся; Олег публикует сам.

Сохраняются границы: предварительные сроки/правила не окончательные бизнес-решения; нет реальных аккаунтов/данных/источников/писем, TOTP/полных сессий E2-06/RBAC/RLS/UI/worker/следующих задач. Production/main/Caddy/FBS/WB/Finkos/другие проекты не менялись. Дополнительных серверных действий для завершения E2-05 не требуется.

Откат локальных документов: сравнить hashes/поздние правки, сохранить текущую работу, применить только обратный diff; цельные копии — лишь без поздних правок. CHANGELOG не сокращать, добавить отмену. Серверный откат только после сверки позднего состояния: base-only web up --no-deps --force-recreate на прежнем image E2-03, smoke старого web, затем guarded revoke из fixed worktree, сохраняющий первоначальный SELECT; добавочную схему/данные/dumps сохранять. Accounts zero и restore поверх живой БД запрещены. Для восстановления — новая отдельная БД из проверенного dump; ACL отдельно из snapshot/контракта. Не удалять mounted release, C1/recovery/restore БД или backups без отдельного решения, сверки точных путей/принадлежности/поздней работы. Никаких reset/clean/prune/удалений корня.

Уточнение 2026-10-01T13:56:27+03:00: при финальном review сохранены исходные смешанные LF/CRLF неизменённых строк в SYSTEM_STARTUP.md, SYSTEM_ENVIRONMENTS.md, docs/RUNBOOK.md. Промежуточные копии этих файлов и CHANGELOG находятся в .change-backups/2026-10-01/E2-05-C2/before-ending-readback/. Содержание не менялось, diff освобождён от случайной смены окончаний строк.


## 2026-10-01T14:38:29+03:00 (Europe/Moscow, UTC+3) — подготовлено решение E2-06 до реализации

Основание: текущее задание только E2-06 с обязательным уточнением политики/зависимостей до выбора решения и запретом серверных действий. Причина: определить реальную интеграцию с E2-05 и исключить фиктивное закрытие MFA/экспорта/прав. Исходная beta чистая, HEAD f6c64d31ceb9c4c3ff057d3990455b1aaad4c8b4; публикация подтверждена read-only git ls-remote. Первая sandbox-сетевая попытка не соединилась; повтор с разрешённым сетевым доступом успешно вернул SHA. SSH к серверу проекта отсутствует.

Изменены только существующие `SYSTEM_PLAN.md`, `SYSTEM_ARCHITECTURE.md`, `CHANGELOG.md`; новый файл `docs/E2-06_PREPARATION.md`. Полный корень путей: `C:/Users/krolo/Documents/marketplace-workspace/`. План отражает подготовку/открытые вопросы; критерии/зависимости и остальные задачи сохранены. Архитектура явно исправляет ошибочную ссылку E2-12: после ответа Олега «давай» проверка копии ключа шифрования TOTP относится к E2-06, общая — E2-15/D4; резервные коды пользователя отдельно.

Документ содержит обследование User/Membership/login/reset/block/session/SQL, предложения и ответы Олега, конкретные девять пакетов/версий, ограничения штатного plaintext хранения, необходимость защищать wizard-session, узкие стыки прав/синтетической ссылки, матрицу проверок и план S0/S1/S2 с backup/restore/минимальными правами/откатом. Работающего механизма E2-06/новых тестов/SQL grants нет. Подтверждено MFA обязательно owner/добровольно остальным, правила подключения/замены и узкие страницы; сроки/отзыв, оператор/проверка личности и место/хранитель копии ключа ещё уточняются. Возврат web к E2-05 после включения MFA прямо запрещён как обход фактора; нужен проверенный deny-auth/maintenance план.

Исходные копии трёх документов до правок: `.change-backups/2026-10-01/E2-06-preparation-143251/` с исходными именами; побайтное соответствие проверено. Промежуточная версия нового документа до ответов пользователя: `before-user-answers/E2-06_PREPARATION.md` в той же папке. `manifest.json` содержит исходные/итоговые SHA-256 и новый путь; каталог исключён Git.

Проверки подготовки: существующий pip check успешен; CPython 3.14.7/Django 5.2.17 и состав venv подтверждены, MFA/cryptography отсутствуют; Docker/PostgreSQL tools не найдены в PATH. Публичные release source/PyPI metadata проверены без установки: версии/ограничения Python/Django/wheels, imports/runtime новых пакетов не проверены. Проверяются narrow diff/whitespace, сохранность прежнего журнала, 101 строка задач с единственным изменением статуса E2-06, неизменность backend/deploy/locks, исключение backups и состав commit. PostgreSQL/beta/MFA/экспорт/SQL/restore тесты новой реализации не выполнялись; результаты E2-05 не используются как их доказательство.

Безопасный откат: сравнить текущие hashes и сохранить позднюю работу; применить только обратный diff SYSTEM_PLAN/SYSTEM_ARCHITECTURE этой подготовки. CHANGELOG не сокращать, добавить запись отмены. Новый `C:/Users/krolo/Documents/marketplace-workspace/docs/E2-06_PREPARATION.md` удалять только при совпадении manifest hash, отсутствии поздних правок/потребителей и после удаления собственных ссылок. Никакого reset --hard/clean. Серверного отката нет, сервер не менялся. Локальный commit автора Oleg разрешён текущим заданием; push выполняет Олег. Finkos/main/production/Caddy/FBS/WB/другие проекты и зависимости не менялись.


## 2026-10-01T15:36:06+03:00 (Europe/Moscow, UTC+3) — добавлена локальная реализация E2-06

Основание: текущее задание только E2-06 и последующие явные ответы Олега: правила MFA/сессий/30-дневного доверия, отдельный аварийный секрет оператора, зашифрованная копия ключа у Олега и локальная установка ровно девяти согласованных пакетов. Серверные действия и push не разрешались и не выполнялись. Причина изменения — действующее управление сессиями/MFA и восстановление без расширения владения/прав.

Добавлены библиотечный TOTP, зашифрованные Authenticator и Django/wizard sessions, ограниченная стадия MFA, серверный реестр/отзыв сессий и доверия, одноразовые PBKDF2-коды, owner-bound операторское разрешение только на повторное подключение, живые проверки Membership и действующее синтетическое HTTP-скачивание с отзывом. Старый password-only вход в runtime закрыт. Пароль/reset/block/замена или восстановление MFA отзывают доступ и доверие; парольное восстановление MFA не отключает. Добавлены миграции/точный SQL delta, новые изолированные проверки и deploy/deny-auth overlays, но PostgreSQL и Compose не запускались.

Политика: owner обязательно, остальные добровольно; сессия 24 часа, простой 1 час, MFA/подтверждение 5 минут, доверие 30 дней. Предыдущий документ подготовки явно обозначен историческим снимком; актуальные правила/ограничения/серверные этапы — docs/E2-06_SESSIONS_MFA.md. SYSTEM_PLAN оставлен «На проверке», все 101 строки/критерии задач сохранены. Расхождение E2-12 явно исправлено ранее в 5eb4b42, повторно смысл не менялся.

Изменённые существующие файлы (корень C:/Users/krolo/Documents/marketplace-workspace/):
- `CHANGELOG.md`.
- `SYSTEM_PLAN.md`.
- `backend/accounts/services.py`.
- `backend/accounts/views.py`.
- `backend/config/settings.py`.
- `backend/config/urls.py`.
- `backend/requirements.in`.
- `backend/requirements.lock`.
- `docs/E2-06_PREPARATION.md`.
- `docs/RUNBOOK.md`.

Новые файлы:
- `SYSTEM_SECURITY_CHECKS.json`.
- `backend/account_security/__init__.py`.
- `backend/account_security/apps.py`.
- `backend/account_security/configuration.py`.
- `backend/account_security/crypto.py`.
- `backend/account_security/forms.py`.
- `backend/account_security/key_backup.py`.
- `backend/account_security/maintenance.py`.
- `backend/account_security/management/__init__.py`.
- `backend/account_security/management/commands/__init__.py`.
- `backend/account_security/management/commands/issue_owner_recovery.py`.
- `backend/account_security/management/commands/prepare_owner_recovery.py`.
- `backend/account_security/middleware.py`.
- `backend/account_security/migration_guards.py`.
- `backend/account_security/migrations/0001_initial.py`.
- `backend/account_security/migrations/0002_revocation_guards.py`.
- `backend/account_security/migrations/__init__.py`.
- `backend/account_security/models.py`.
- `backend/account_security/operator.py`.
- `backend/account_security/policy.py`.
- `backend/account_security/services.py`.
- `backend/account_security/session_backend.py`.
- `backend/account_security/signals.py`.
- `backend/account_security/templates/account_security/codes.html`.
- `backend/account_security/templates/account_security/form.html`.
- `backend/account_security/templates/account_security/panel.html`.
- `backend/account_security/templates/account_security/wizard.html`.
- `backend/account_security/tests/__init__.py`.
- `backend/account_security/tests/test_http.py`.
- `backend/account_security/tests/test_migrations.py`.
- `backend/account_security/tests/test_operator.py`.
- `backend/account_security/tests/test_role_scenario.py`.
- `backend/account_security/tests/test_transactions.py`.
- `backend/account_security/urls.py`.
- `backend/account_security/views.py`.
- `backend/config/security_local_checks.py`.
- `backend/tools/check_security_postgresql.py`.
- `backend/tools/manage_security_web_grants.py`.
- `backend/tools/mfa_key_backup.py`.
- `backend/tools/security_role_scenario.py`.
- `backend/tools/security_web_grants.py`.
- `backend/tools/verify_security_recovery.py`.
- `backend/tools/verify_security_web_role.py`.
- `backend/tools/verify_security_web_runtime.py`.
- `beta/deploy/compose.security-check.json`.
- `beta/deploy/compose.security-maintenance.json`.
- `beta/deploy/compose.security-web.json`.
- `docs/E2-06_SESSIONS_MFA.md`.

Исходные копии всех изменённых существующих файлов сохранены до правок в `.change-backups/2026-10-01/E2-06-implementation/` с исходными относительными путями. manifest.json содержит before/after SHA-256 и полный список новых файлов; дополнительно сохранены installed-before.json, installed-after.json (package RECORD paths), dependency-review.json и девять проверенных wheel в wheels/. Промежуточная подготовка: `.change-backups/2026-10-01/E2-06-policy-144041/`. Каталоги/venv исключены из Git. Исходные смешанные окончания строк неизменённых строк сохранены; новые строки LF.

Локально установлены только django-two-factor-auth 1.18.1, django-otp 1.7.3, cryptography 50.0.2, django-formtools 2.7, django-phonenumber-field 8.5.0, qrcode 8.2, cffi 2.1.1, pycparser 3.0, colorama 0.4.6 (Windows). Release SHA-256 и LICENSE сверены, resolver dry-run и установка only-binary/require-hashes без дополнительных пакетов и смены прежних pins, pip check успешен. Никаких plugins/глобальных установок/нативной сборки.

Проверки: final security+ownership/guard 61 тест, 52 выполнены успешно, 9 PostgreSQL-only пропущены, 81.695 с; из них шесть новых конкурентных проверок пока не выполнены. Отдельный legacy accounts_local_checks: 68 тестов, 55 pass, 13 skips, 16.151 с; это регрессия E2-05, не приёмка E2-06. Focused QR/operator: 7 pass, включены в final 61, не суммируются. Django check и makemigrations --check --dry-run успешны; pip check, AST, JSON, соответствие новых ACL колонкам моделей и неизменность 101 строк задач проверены. Новые локальные тесты используют SQLite и синтетические значения/example.invalid, locmem. Тесты проверяют секреты boolean-утверждениями, без вывода значений; QR проверен как HTTP SVG, не скриншотом. Ошибки промежуточных тестов (formtools 2.7 form-list cache) устранены до финального прогона.

Ограничения: нет новых PostgreSQL/limited LOGIN/17 SQL-denial/grant/revoke/reapply/dump-restore, реального восстановления файловой копии ключа, operator CLI под настоящей ролью, Linux image/Compose/браузера/Gunicorn maintenance и основной beta smoke. Docker/PostgreSQL tools локально отсутствуют; не устанавливались. SQL-plan/static/SQLite и старые E2-05 результаты не выдаются за новую приёмку. Полные RBAC/Grant/RLS и рабочий экспорт не реализованы; синтетический download действует, но критерий будущего рабочего экспорта зависит от E2-07/E2-08/E5-07 и остаётся на проверке. S0/S1/S2 имеют отдельные разрешения; до S2 обязательно завершить ключевой restore и maintenance протокол.

Git: live ls-remote перед коммитом подтвердил опубликованную beta f6c64d31ceb9c4c3ff057d3990455b1aaad4c8b4; локальная подготовка 5eb4b42 не опубликована. Планируется локальный commit Oleg «Добавлены сессии и двухфакторная защита E2-06». Push выполняет сам Олег. Main, Finkos, production, Caddy, FBS, WB и прочие проекты не менялись. Сервер не опрашивался; работающая E2-05 по прежнему протоколу не объявляется заново проверенной.

Безопасный откат локально: сравнить manifest/current hashes и поздние правки, сохранить текущую работу, применить только обратный diff этого коммита; CHANGELOG не сокращать, дополнить отменой. Новые перечисленные файлы удалять только при совпадении recorded hash и отсутствии поздних изменений/потребителей. Девять новых пакетов удалять только после проверки новых потребителей и возврата прежнего lock; исходный состав в installed-before.json, автоматического удаления нет. Никаких git reset --hard/clean. Серверный откат сейчас не нужен. После будущего включения E2-06 обычный E2-05/base-only вход небезопасен: использовать отдельно проверенный maintenance overlay (503 auth/business) либо остановить только beta web. Схему/ключи/данные/dumps сохранить, zero/restore поверх живой БД не выполнять; revoke только нового delta после остановки потребителя. Restore в новую БД с карантином доступа и отдельной сверкой полномочий.


## 2026-10-01T17:09:19+03:00 (Europe/Moscow, UTC+3) — проверены S0/S1 и исправлено удержание блокировки восстановления E2-06

Основание: после публикации 3db1c0c Олег явно разрешил S0/S1 (SSH/preflight/Git/сборка/только изолированные тесты/ключи/БД/роль/dump-restore); затем подтвердил продолжение. S2/main deployment и push не разрешались. Цель: проверить опубликованный E2-06 на настоящем PostgreSQL и устранить обнаруженную ошибку без ослабления защиты.

Точные изменённые локальные файлы (корень C:/Users/krolo/Documents/marketplace-workspace/):
- `CHANGELOG.md`.
- `SYSTEM_PLAN.md`.
- `SYSTEM_SECURITY_CHECKS.json`.
- `docs/E2-06_SESSIONS_MFA.md`.
- `backend/account_security/services.py`.
- `backend/account_security/tests/test_transactions.py`.

Исходные копии всех шести существующих файлов перед изменением: `.change-backups/2026-10-01/E2-06-S0-S1/<relative-path>`. `manifest.json` содержит before/after SHA-256; новые локальные игнорируемые evidence: `baseline.json`, `final-containers.json`, `progress.json` и `manifest.json` в той же папке. Новых tracked файлов нет. Неизменённые строки/окончания сохранены, журнал append-only.

S0 PASS: Git remote подтвердил опубликованный 3db1c0c64880985489b86b52aa725e0c839ca001; серверный beta checkout fast-forward b1a9450→3db1c0c, detached release `/home/adm_user/marketplace-workspace/beta/app/releases/3db1c0c64880985489b86b52aa725e0c839ca001`. Image `marketplace-workspace/backend:e2-06-3db1c0c64880985489b86b52aa725e0c839ca001`, ID `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`, собран из опубликованного Git с разрешённой загрузкой только lock-wheels/hashes; lock внутри image совпал, pip check успешен. Старый image сохранён. Compose 5.1.3: read-only source/UID10001/256MiB/0.25CPU/test-private/no ports; bootstrap test secret только ACL probe, основных секретов нет.

PostgreSQL suite на 17.11 НЕ ПРИНЯТ: 61 тест, 60 pass, 1 error, 0 skips, 493.226 с. Ошибка `test_same_recovery_code_has_one_successful_consumer`: lock_timeout=2000ms, ownership_user. PBKDF2 пароля/кода удерживал User row lock при 0.25 CPU. Новая disposable `mw_beta_test_e2_06_suite` удалена штатным Django runner после завершения; старые E2-05 БД не тронуты. Локальное исправление выносит дорогую проверку до lock, затем атомарно заново проверяет активность, прежний password hash, verifier и used_at=NULL; расходует код только под User/RecoveryCode locks. Хеширование/итерации/сроки/ресурсы не ослаблены, таймауты не увеличены. Добавлены регрессии отсутствия atomic во время PBKDF2 и отказа при смене пароля между доказательством и lock.

Независимые S1 проверки опубликованного 3db1c0c: PASS под настоящим ограниченным LOGIN — точные column DML, grant/revoke/reapply, HTTP/MFA/CSRF lifecycle, 17 SQL-отказов. Новая `mw_beta_test_e2_06_web` БД и одноимённая роль сохранены; readback NOLOGIN/PASSWORD NULL подтверждён. Повтор probes с занятыми именами запрещён.

Backup/restore PASS: новые `mw_beta_test_e2_06_recovery`/`mw_beta_test_e2_06_restore`, владелец mw_beta_test_runner; сохранён `/home/adm_user/marketplace-workspace/beta/backups/test/e2-06-synthetic-20261001T135847Z.dump` (222907 bytes, 0600) и соседние `.mw_beta_test_e2_06_recovery.acl.json`/`.mw_beta_test_e2_06_restore.acl.json` (0600). Проверены ciphertext/строки/миграции, TOTP/replay/wrong-key, quarantine без изменения Membership; проверки в rollback-транзакциях, snapshots сохранены. Restored ACL apply/revoke/reapply проверен транзакционно с сохранённой NOLOGIN-ролью: временные CONNECT/права полностью откатились, равенство исходному snapshot подтверждено, LOGIN не включался.

Созданы только синтетические закрытые файлы вне Git/БД: `/home/adm_user/marketplace-workspace/beta/config/secrets/e2_06_test_encryption_key`; `/home/adm_user/marketplace-workspace/beta/config/e2-06-test-key-recovery/backup-passphrase`; `/home/adm_user/marketplace-workspace/beta/backups/test/e2-06-key-envelope/envelope.json`; `/home/adm_user/marketplace-workspace/beta/config/e2-06-test-key-restored/key` (0600, UID/GID10001). Новые родительские каталоги 0700. Восстановление envelope выполнялось без mount исходного ключа, сравнение только boolean; затем DB verifier использовал именно восстановленный файл и не монтировал оригинал. Ключа основной beta/реального аварийного секрета владельца/Telegram-передачи нет. Секреты/пароли/коды/cookies/ссылки/персональные данные не включены в журнал, отчёт и commit.

Maintenance PASS в реальном Gunicorn старого image `sha256:eade0170f4aaf5984fc22664d479f30bfc8dac085c9d31b78e70190aeb810e4b` с новым Git source: network none, без БД/ключа/портов, live 200, auth/business/ready 503, no-store. Одноразовый контейнер удалён. Final readback: основной web и оба PostgreSQL сохранили ID/image/StartedAt/mounts/networks/ports; E2-05 restricted SQL/runtime smoke успешен. Основной web по-прежнему использует 82b2004, аккаунты/организации/членства до проверки 0/0/0; основных миграций/прав/перезапуска не было. Все одноразовые S1 контейнеры удалены; исторические releases/БД/dumps сохранены.

Промежуточные операционные ошибки: preflight сначала запросил отсутствующий Health у web (команда read-only); два SSH banner timeout команд не выполнили. Compose mem_limit выдаёт строку — checker исправлен на int без изменения ресурсов. При первом блоке backup docker exec поглотил следующие команды из SSH stdin; readback подтвердил существующий dump и пустую restore-цель. Продолжение восстановило тот же dump только в пустую цель; seed/создание БД/dump повторно не выполнялись. Рецепт в docs дополнен </dev/null.

Проверки локального исправления: 34 затронутых теста PASS, 0 skips, 73.747 с (32 HTTP + 2 новые транзакционные регрессии); Django check и makemigrations --check --dry-run PASS/no changes; JSON/AST/diff/сохранность 101 строк задач проверяются перед commit. PostgreSQL-исправление ЕЩЁ НЕ ПРОВЕРЕНО: сервер получает код только после публикации Олегом. Ожидается full suite 63 теста с тем же lock/image и новым read-only Git release; существующие role/seed probes не повторять. Реальный браузер, полный operator CLI с доверенной фактической ролью/секретом и S2/main E2-06 остаются открыты. E2-06 — «На проверке»; RBAC/RLS/рабочий экспорт/следующие задачи не реализованы.

Безопасный откат: локально сверить manifest/поздние правки и применить только обратный diff исправления/документации, журнал дополнить отменой; не reset --hard/clean. Серверу откат web/БД не нужен — они не менялись. Новые image/release/test DB/роль/dump/ACL/key/envelope/passphrase сохранять до отдельного решения; автоматического удаления/повтора нет. Для возможной последующей очистки сначала подтвердить принадлежность точных путей/объектов, отсутствие mounted release/подключений/поздней работы и независимых копий; не удалять корневые каталоги или старые probes. NOLOGIN/PASSWORD NULL оставить. S2 возможен только после успешной повторной проверки и отдельного разрешения; после MFA обычный E2-05 fallback запрещён, доступен проверенный deny-auth maintenance.

Локальный commit Oleg: «Исправлена блокировка восстановления и записаны результаты S0/S1». Push выполняет Олег; main/production/Caddy/FBS/WB/Finkos/другие проекты не менялись, сотрудники/агенты не привлекались.


## 2026-10-01T17:31:37+03:00 — Подтверждено конкурентное восстановление E2-06 на PostgreSQL

Причина: после публикации Олегом 19a6d6a завершена повторная PostgreSQL-проверка исправления в рамках уже разрешённого S1. Изменены только `CHANGELOG.md`, `SYSTEM_PLAN.md`, `SYSTEM_SECURITY_CHECKS.json`, `docs/E2-06_SESSIONS_MFA.md`: сохранены предыдущие результаты/ошибка, добавлено успешное подтверждение и актуальные ограничения. Код/зависимости/схема/права в этом коммите не менялись.

Резервные копии этих четырёх файлов: `.change-backups/2026-10-01/E2-06-S1-retest/<relative-path>`. Новые игнорируемые артефакты в этой же папке: `manifest.json` (before/after SHA-256), `baseline.json`, `unchanged-contract.json`, `final-containers.json`, `final-readback.txt`, `result.json`. Новых tracked файлов нет.

Remote beta=19a6d6a9bbdd06c683f68f438215dd99cba6204e подтверждён, серверный checkout fast-forward только Git; создан detached release `/home/adm_user/marketplace-workspace/beta/app/releases/19a6d6a9bbdd06c683f68f438215dd99cba6204e`. Новый read-only source использовал прежний dependency image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`; lock, модели/миграции, SQL-контракт, role/restore tools и Compose сверены с 3db1c0c без изменений. Установок/сборок не было.

PostgreSQL 17.11 full suite: 63/63 PASS, 0 failures/errors/skips, 493.704 с, exit 0. Проверены гонка одного восстановительного кода и смена password hash между доказательством и lock; сохранены CPU 0.25, память 256MiB и lock_timeout 2000ms. Свободность disposable suite DB проверена runner до создания; после штатного удаления SELECT подтвердил отсутствие. Три прежние E2-06 БД сохранены, роль NOLOGIN/PASSWORD NULL. Занятые role/seed probes не запускались; их исходные 17 SQL-отказов/LOGIN/restore относятся к 3db1c0c, а не объявляются новым прогоном.

Основной web и оба PostgreSQL сохранили ID/image/StartedAt/mounts/networks/ports; mounts сравнивались после нормализации порядка Docker, первоначальное сравнение списков дало ложное различие только порядка. Старый E2-05 restricted SQL/runtime smoke PASS; Git чистый, одноразовых контейнеров нет. Один SSH banner timeout команд не выполнил; повторное чтение успешно. Первый SQL readback не передал stdin psql без docker exec -i и не исполнил SELECT; после явного -i получены и проверены все три ожидаемых результата, мутаций не было.

S2/основной ключ/миграции/права/перезапуск web не выполнялись, основной source по-прежнему 82b2004. Реальные аккаунты/отправки/секреты/Telegram не использовались. Браузер, полная operator CLI, фактическое хранение ключа, S2 и рабочий экспорт остаются открыты; E2-06 «На проверке», 101 строка задач без изменения критериев. JSON, append-only журнал, task-row invariant, git diff --check и manifest проверяются перед локальным commit Oleg «Подтверждено конкурентное восстановление на PostgreSQL». Push выполняет Олег.

Безопасный откат: сравнить before/after manifest и поздние правки, применить только обратный diff трёх актуализированных документов, в CHANGELOG дописать отмену; не reset --hard/clean. Серверный откат не требуется — runtime основной beta не менялся. Сохранить release/image/БД/роль/dump/ключи; удаление только после отдельного решения и проверки отсутствия ссылок/mounts. Новые локальные evidence можно удалить только после переноса нужного протокола и сверки принадлежности точной папки; резервные копии существующих файлов сохранить. Production/main/Caddy/FBS/WB/Finkos/другие проекты не затронуты.


## 2026-10-01T17:59:51+03:00 — Обновлена основная beta до E2-06 после разрешения S2

Причина: Олег опубликовал f4f6059 и отдельно разрешил S2 в текущем чате. Выполнены main backup/restore, отдельный ключ/зашифрованная копия, maintenance, миграции/минимальный delta прав и обновление только web. Полная E2-06 не объявляется завершённой. Изменены только документы: `CHANGELOG.md`, `SYSTEM_PLAN.md`, `SYSTEM_SECURITY_CHECKS.json`, `docs/E2-06_SESSIONS_MFA.md`, `SYSTEM_STARTUP.md`, `SYSTEM_STARTUP_CHECKS.json`, `docs/RUNBOOK.md`. Код, зависимости и общий deploy/compose.json не менялись.

Перед изменением всех семи файлов сохранены исходные копии `.change-backups/2026-10-01/E2-06-S2/<relative-path>`. Before/after SHA-256 и перечень новых игнорируемых артефактов — `manifest.json`. Точные новые файлы в этой папке: `apply-result.txt`, `apply.sh`, `backup-restore.json`, `baseline.json`, `browser-config.json`, `browser-smoke.txt`, `final-containers.json`, `final-readback.json`, `key-recovery.json`, `manifest.json`, `preapply-final.txt`, `preapply-verified.txt`, `preapply.sh`, `preapply.txt`, `s2-result.json`. Браузерные артефакты только пустых анонимных форм/ожидаемых 401/403: `output/playwright/e2-06-s2/console-2026-10-01T14-50-41-744Z.log`, `output/playwright/e2-06-s2/page-2026-10-01T14-50-42-094Z.yml`, `output/playwright/e2-06-s2/page-2026-10-01T14-51-06-404Z.yml`, `output/playwright/e2-06-s2/page-2026-10-01T14-51-08-177Z.yml`. Скриншоты QR, network/storage dumps, trace, ввод/вывод секретов не выполнялись. CLI создал только собственную временную isolated session e206-s2; она закрыта, существующие сессии не трогались.

S2 preflight: опубликованная beta f4f6059 подтверждена, server repository fast-forward 19a6d6a→f4f6059 только Git; runtime source остаётся проверенным read-only release 19a6d6a9bbdd06c683f68f438215dd99cba6204e. Existing image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`, lock равен Git, новая сборка/установка не выполнялась. Compose effective source/UID10001/read-only/private/no host ports сверены. Основная БД до применения accounts:2/auth:12/contenttypes:2/ownership:2/sessions:1, users/org/memberships=0/0/0.

Новый dump `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-before-20261001T144009Z.dump` (75491 bytes,0600), соседние `.acl.json` и `.snapshot.json` без role passwords/pg_authid значений сохранены. Restore --no-owner/--no-acl в новую `mw_beta_test_e2_06_main_before` с owner mw_beta_test_runner/REVOKE PUBLIC прошёл; все 18 таблиц совпали по count/упорядоченному fingerprint, основной ACL и данные до применения не изменились. Это точная копия состояния E2-05 перед обновлением, не повтор S1 security restore. Target/dump/ACL сохранить; имя занято, не создавать повторно.

Отдельный ключ `/home/adm_user/marketplace-workspace/beta/config/secrets/mfa_encryption_key`, envelope `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-main-key-envelope/envelope.json`, отдельный пароль `/home/adm_user/marketplace-workspace/beta/config/e2-06-main-key-recovery/backup-passphrase`, восстановленный файл `/home/adm_user/marketplace-workspace/beta/config/e2-06-main-key-restored/key` созданы без перезаписи: mode0600/UID:GID10001:10001, новые родительские каталоги0700. Envelope восстановлена без mount оригинального ключа, равенство проверено без значений/fingerprints. Это закрытая серверная копия, не независимое владение копией Олегом. Передачи в Telegram/владельцу не было, реальный emergency proof/verifier/permit не создавался. Эти файлы нельзя удалять вместе с временными тестовыми артефактами.

Django check и additive migration plan/forward SQL/RunPython guards/column-grant delta проверены. Maintenance основного web: live200, auth/business/ready503, no-store. Затем 9 операций миграций завершились, delta ACL проверен и закоммичен guarded migrator. Django recorder добавил 17 записей, всего36: two_factor squash сохраняет 8 заменённых и свою запись; это не 9 отдельных операций two_factor. Новый web `42ea5c212f1fc3062df51214ca97428e4613741adb8fac7897e494faaeb8e106`, StartedAt `2026-10-01T14:48:24.953976075Z`, source/key mounts read-only. Runtime PASS: actual mw_beta_web, exact ACL/guards, live/ready200, anonymous session401, legacy login GET405, MFA login GET200. Оба PostgreSQL сохранили ID/image/StartedAt/mounts/networks/ports; старые образы/releases сохранены.

Browser smoke существующими Playwright CLI0.1.18/Chromium через временный localhost18766 SSH tunnel: форма входа, переход восстановления, 3 обязательных поля, empty-form rejection, session401/CSRF403, формы login/operator-recovery200 и no-store. Console содержит только ожидаемые401/403. Browser/tunnel закрыты, host ports/Caddy/TLS не добавлены. Это анонимная проверка страниц, не полный browser MFA lifecycle. Оба операторских CLI из настоящей web-роли отказаны до выдачи файлов/секретов; положительное восстановление через migrator не выполнялось.

Финальный readback: users/org/memberships/factors/recovery permits/codes=0; две анонимные wizard sessions с encrypted prefix mfa1; plaintext OTP таблицы пусты; locmem, все external flags=false и SECURITY_DOWNLOAD_PROBE=false подтверждены. Oneoff контейнеров нет; server Git чистый. 63/63 PostgreSQL-suite на том же коде из предыдущего S1 не повторялся и не выдаётся за новый прогон.

Промежуточные ошибки проверок, без скрытого обхода: первая команда backup остановилась локальным SyntaxError до SSH; исправлена кавычка. Два SSH banner timeout не выполнили key/preapply команды; guard свободных путей/проверки повторены, существующие ключи/dump не перегенерированы. Compose config сначала не включал profile maintenance и не показывал migrator; добавлен profile только при проверке. Авто-review отклонил Playwright wrapper из-за предполагаемого npx: read-only чтение доказало прямой запуск установленного JS через node, повтор разрешён с выключенными update/download; компонентов не установлено. PowerShell/CMD исказил кавычки одного browser eval; повтор прямого установленного entrypoint с argv проверил ожидаемые результаты. Финальный assertion сначала ожидал одну запись two_factor вместо9; сверены локальный migration.replaces и реальные записи, исправлена только проверка, схема/код не менялись.

Проверки документов перед коммитом: JSON, неизменность всех101 task rows/критериев, append-only CHANGELOG, before/after hashes, git diff --check. План и startup отражают E2-06 runtime, но статус остаётся «На проверке»: полный browser MFA, положительный operator CLI, фактическая независимая копия ключа у Олега и полный экспорт не закрыты. RBAC/RLS/рабочий экспорт и следующие задачи не реализованы. Новых разрешений на реальные аккаунты/секреты/передачу/production эта запись не даёт.

Безопасный откат: проверить поздние правки и применить только обратный diff документов, CHANGELOG дополнить отменой; не reset --hard/clean. После MFA base-only/E2-05/accounts-overlay web запрещены. Серверный fallback — опубликованный compose.security-maintenance.json с E2-06 read-only source и проверенным старым image либо остановка только web; новая схема/ключи/права/данные сохраняются, исправление вперёд предпочтительно. Revoke только нового delta и только при отключённом потребителе; zero/live restore недопустимы. Резервный dump/restored DB/ключи/envelope/passphrase/releases не удалять. Локальные новые evidence можно убрать только после переноса нужного протокола и сверки точных путей с manifest; существующие backup/позднюю работу сохранить.

Локальный commit Oleg: «Обновлена основная beta до E2-06 и записаны проверки S2». Push выполняет Олег. Production/main/Caddy/FBS/WB/Finkos/другие проекты/сотрудники не затронуты.

Уточнение состава commit: SYSTEM_STARTUP_CHECKS.json сохранён локально под существующим правилом .gitignore:44, принудительно не добавлялся; коммит содержит шесть tracked документов. Его новый current_beta_e206 согласован с публикуемым SYSTEM_SECURITY_CHECKS.json/s2. Локальный исторический snapshot E2-03 сохранён.


## 2026-10-02T11:34:43+03:00 — Подготовлена изолированная проверка восстановления владельца E2-06

Причина: после S2 остаются полный браузерный MFA lifecycle и положительный operator CLI. По запросу «давай дальше» подготовлен конкретный дополнительный стенд для отдельного согласования; новое серверное окружение не запускается по старым разрешениям. Git beta чистая на старте, публикация e3e538370b7dcebd590528bb62c3a9d035cab6c6 подтверждена ls-remote. SSH, основная beta и старые probes в этом шаге не опрашивались/не менялись; состояние S2 приводится как ранее проверенное.

Изменены: `CHANGELOG.md`, `SYSTEM_PLAN.md`, `SYSTEM_SECURITY_CHECKS.json`, `docs/E2-06_SESSIONS_MFA.md`. Исходные копии четырёх файлов сохранены перед редактированием в `.change-backups/2026-10-02/E2-06-owner-rehearsal/<relative-path>`; before/after SHA-256 — `manifest.json`. Новые tracked файлы: `backend/tools/owner_rehearsal.py`, `backend/tools/owner_rehearsal_bootstrap.py`, `beta/deploy/compose.owner-rehearsal.json`, `beta/deploy/prepare_owner_rehearsal.py`, `scripts/e2_06_owner_browser.cjs`, `docs/E2-06_OWNER_REHEARSAL.md`. Новые игнорируемые артефакты: `.change-backups/2026-10-02/E2-06-owner-rehearsal/manifest.json` и `local-checks.json`.

План задаёт только новый Compose project marketplace-e206-owner-check, внутреннюю сеть, один volume и PostgreSQL/web/controller/issuer плюс одноразовый bootstrap; root /home/adm_user/marketplace-workspace/beta/rehearsals/e2-06-owner-20261002. Guard требует новый marker, настоящий cluster_name, прежнюю реальную mw_beta/mw_beta_migrator identity; operator guard и runtime auth код не менялись. Скрипт подготовки по умолчанию только печатает план, --apply запрещён на Windows и требует published detached release/свободных имён/диска/памяти. Старые БД/роли/ключи не переиспользуются. Main container baseline сверяется отдельно; никаких новых host ports/ingress.

Fixture — 4 синтетических аккаунта/2 организации, адреса только example.invalid. Два владельца разделяют этапы, чтобы уложиться в исходные ограничения попыток: лимиты/clock/last_t не подменяются и buckets не сбрасываются. Только библиотечные TOTP по реальному времени; пароль/код/proof/permit проходят через закрытый SSH→Node pipe в памяти, не через аргументы/env/логи. Proof вводится настоящей CLI в PTY с выключенным echo; неверный proof, чужой владелец, не-владелец и блокировка должны отказать. Web имеет только 3 необходимых secrets; controller/issuer не монтируют bootstrap/web credentials, все runtime-ключи read-only. HTTP тестовых hooks/обхода MFA нет.

Browser runner использует существующую библиотеку Playwright/Chromium без npm/npx/установки; импорт и наличие browser проверены. Для секретных шагов нет CLI-снимков/trace/video/storage dumps/скриншотов и raw error output. Предусмотрены enrollment/QR load, неверный/просроченный/верный/replay TOTP, одноразовые коды и permit, реальные CLI, выборочный/общий logout, trusted device/reauth, парольная смена, блокировка и отсутствие повышения прав. Это подготовленный сценарий, **не результат его исполнения**. Существующие SQL/concurrency/export-probe доказательства S1 не считаются повторёнными.

Локальные проверки: AST 3 новых Python модулей, node --check, JSON/изоляция/secret mount whitelist, безопасный plan без мутаций; ожидаемый отказ Windows --apply, private-pipe без rehearsal marker, bootstrap без разрешённой среды и browser runner без обязательных аргументов. Runtime auth/ownership/accounts/settings/requirements не изменены. Полного browser-run, Linux PTY, нового PostgreSQL/Compose/SQL не было; новые зависимости/плагины не устанавливались, сотрудники/агенты не привлекались. JSON/101 неизменная строка задач/append-only журнал/diff/manifest проверяются перед commit.

При подготовке исправлены ошибки самого сценария: формы mutation принимают application/x-www-form-urlencoded, поэтому fetch использует URLSearchParams; mount bootstrap credentials удалён из operator процессов; полные container IDs сравниваются с --no-trunc. Одна начальная локальная команда не создалась из-за Windows CreateProcessWithLogonW 1056, повторилась чтением без побочных действий. Серверные результаты из этих проверок не выводятся. E2-06 остаётся «На проверке».

Безопасный откат: сверить manifest/поздние изменения, обратный diff только четырёх изменённых документов, в CHANGELOG дописать отмену. Новые шесть файлов можно удалить только при совпадении hashes и отсутствии поздних ссылок/публикации/использования; локальные evidence сохранять до фиксации нужного протокола. Не reset --hard/clean. На сервере этим изменением откатывать нечего. Для будущего стенда предусмотрена остановка только нового проекта с сохранением volume/secret/fixture/proof/verifier/permit; down -v/prune/старые probes запрещены, удаление отдельным решением.

Локальный commit Oleg «Подготовлена изолированная проверка восстановления владельца». Push выполняет Олег; затем отдельно согласуется точный docs/E2-06_OWNER_REHEARSAL.md. Основной ключ/передача его envelope и пароля/реальный emergency secret/Telegram/RBAC/RLS/рабочий экспорт/следующие задачи не входят в это разрешение. Main/production/Caddy/FBS/WB/Finkos/другие проекты не менялись.


## 2026-10-02T12:12:30+03:00 — Проверен отдельный стенд E2-06 и исправлен браузерный CSRF-отказ

Причина: Олег опубликовал 6ec715f и отдельно разрешил конкретный docs/E2-06_OWNER_REHEARSAL.md. В начале beta на 6ec715f, существующее изменение docs/SYSTEM_DESIGN.md сохранено; во время работы появились дополнительные посторонние изменения docs/design/*, они не редактируются и не включаются в E2-06 commit. Публикация 6ec715f5a1343ef7cccc5f89beea606433f31d03 подтверждена ls-remote. Серверный repository обновлён fast-forward с f4f6059; новый detached release получен только Git, ручной правки исходников/архивов/push не было.

Изменены ровно: `backend/account_security/middleware.py`, `backend/account_security/tests/test_http.py`, `backend/tools/owner_rehearsal.py`, `scripts/e2_06_owner_browser.cjs`, `docs/E2-06_OWNER_REHEARSAL.md`, `docs/E2-06_SESSIONS_MFA.md`, `SYSTEM_PLAN.md`, `SYSTEM_SECURITY_CHECKS.json`, `CHANGELOG.md`. Исходные девять файлов сохранены перед изменением в `.change-backups/2026-10-02/E2-06-owner-run/before/<relative-path>`; manifest.json содержит before/after hashes. Новые tracked файлы: `backend/tools/check_security_browser_referrer.py`, `scripts/e2_06_referrer_browser.cjs`. Новые локальные evidence в том же `.change-backups/2026-10-02/E2-06-owner-run/`: `manifest.json`, `prepare.txt`, `start.txt`, `isolation.txt`, `browser.txt`, `browser-state.txt`, `login-diagnostic.json`, `header-diagnostic.json`, `stop.txt`, `http-tests.txt`, `local-checks.json`, `result.json`. Только безопасные статусы/булевы признаки/счётчики; значений credentials/ключей/QR/URI/cookies/codes/permit нет.

Серверные новые ресурсы строго по согласованному плану: project marketplace-e206-owner-check, internal network marketplace-e206-owner-check-private, volume marketplace-e206-owner-check-data, postgres/web/controller/issuer и одноразовый bootstrap. Каталог /home/adm_user/marketplace-workspace/beta/rehearsals/e2-06-owner-20261002 и его secrets/state/operator-output созданы закрытыми; только новые синтетические ключи/пароли. Existing immutable backend image 86f9cac63025 и PostgreSQL image 248efd5e58cd, lock совпал, без install/build/pull. Фактический PostgreSQL 17.11, DB mw_beta и LOGIN mw_beta_migrator/mw_beta_web находятся только в новом кластере. Новый restricted SQL/runtime PASS; 36 записей миграций (accounts2/account_security2/auth12/contenttypes2/otp_static3/otp_totp3/ownership2/sessions1/two_factor9). UID/mounts/capabilities/limits/logging none/private network/no ports/locmem/600-файлы проверены. Четыре synthetic аккаунта, две организации, пять членств; адреса только example.invalid.

Настоящий prepare_owner_recovery под реальным migrator LOGIN прошёл: owner-bound proof/verifier созданы в закрытых файлах, обычному участнику отказано без файлов; пароли/владение/права не изменены. Положительный issue_owner_recovery, getpass/PTTY и browser MFA lifecycle не пройдены: Chromium остановился до входа. GET login200, native POST403; cookie/CSRF-поле присутствуют, но Referrer-Policy:no-referrer вызывает Origin:null. Узкий повтор одного password POST подтвердил403; отдельный header-only POST перехвачен и отменён до сервера, значения заголовков не выводились. Пароли fixture проверены в памяти. Контроль до остановки: authenticators/account sessions/codes/permits/challenges/attempt buckets=0, users4/org2/memberships5 и владение прежние, proof/verifier сохранены, owner-permit отсутствует. Повторного init/configure/prepare и сброса buckets не было.

Все четыре новых контейнера остановлены, volume/network/файлы сохранены; browser/tunnel localhost18767 закрыты. Основной web и оба PostgreSQL сохранили ID/image/StartedAt/mounts/networks/ports; основной SQL/runtime smoke PASS. Основной source19a6d6a не менялся и сохраняет обнаруженный браузерный дефект. Ранее сохранённые S1/S2/E2-05 БД/dumps/ключи не использовались для нового fixture и не удалялись. Реальные аккаунты/внешние отправки/Telegram/production/main/Caddy/FBS/WB/Finkos не затронуты.

Локальное исправление заменило no-referrer на same-origin в обоих ответах SessionGate; no-store, secure cookies и штатные CSRF/Origin проверки сохранены. Отдельный настоящий Chromium + Django LiveServer test воспроизводит проблему с прежним заголовком (ожидаемый FAIL2.621s) и проходит с исправлением (1/1 PASS3.106s): native password POST, ограниченный MFA этап, отсутствие полноценной сессии, отказ без CSRF, разрешённый CSRF logout, отсутствие внешнего Referer при перехваченном переходе example.invalid. Новый HTTP-тест отвергает null/foreign Origin даже с корректным токеном и пропускает свой Origin. Все 33 HTTP-теста PASS, 0 skips, 62.345s. Это локальная SQLite/Chromium проверка, не новый PostgreSQL результат и не полный MFA acceptance. AST/Node syntax/check/makemigrations --check PASS. Guard pre_browser отказывает вне rehearsal; положительный Linux guard ещё не выполнялся. Owner runner теперь проверяет policy до пароля и явно ожидает завершение form navigation.

Ошибки самой диагностики/проверок не скрыты: первый read-only SELECT использовал несуществующее поле scope вместо level и не выполнил мутаций; исправленная диагностика успешна. Локальный новый browser harness сначала отказал по SETTINGS_MODULE и отсутствующему STATIC_URL; исправлены только его guard/параметры LiveServer до контрольного прогона. Первая static-check команда не нашла относительный venv executable с cwd backend; повтор с абсолютным путём успешен. Общий git diff --check выявил whitespace только в посторонних design-файлах, они не исправлялись; проверка точных E2-06 файлов проходит.

Продолжение подробно записано в docs/E2-06_OWNER_REHEARSAL.md: после push Олега получить исправление Git в новый release; тот же сохранённый postgres и новые source mounts только controller/issuer/web; без --apply/bootstrap/configure/init/operator_prepare. Read-only pre_browser требует сохранённое состояние до первого входа и не чинит/не сбрасывает его. Затем полный browser/operator run и остановка только стенда. Это продолжение уже разрешённого изолированного этапа, не новое разрешение на основную beta. Её обновление исправлением, real-owner proof и передача независимой encrypted key backup требуют отдельных конкретных разрешений. E2-06 остаётся «На проверке», 101 строка/критерии плана сохранены; полный экспорт/RBAC/RLS не реализованы.

Безопасный откат: сравнить hashes и поздние изменения, применить только обратный diff нужных E2-06 файлов; CHANGELOG дополнить отменой. Не reset --hard/clean. Два новых тестовых файла удалять только после проверки их hash/ссылок/отсутствия поздней работы; evidence сохранять до переноса нужного протокола. Возвращение старого no-referrer снова ломает native формы, это не исправление сервера. На сервере новый стенд уже остановлен; не удалять volume/ключи/fixture/proof/releases, не запускать занятые probes. Основную beta этим шагом откатывать не нужно; прежний MFA maintenance/stop-only fallback сохраняется, password-only/base-only запрещён.

Локальный commit Oleg: «Исправлен CSRF-отказ браузерных форм MFA и сохранён результат проверки». Push выполняет Олег. Новых зависимостей/плагинов и привлечения сотрудников/агентов не было.


## 2026-10-02T12:19:52+03:00 — Спроектировано личное рабочее место v3 и расширен интерактивный макет

По ответам Олега 1–16 подготовлена модель: готовые рабочие таблицы, индивидуальные виды и поля, отдельные личные расчёты, один редактор общей таблицы, явный черновик и согласование руководителем. Добавлены разделы «Закупки» и «Моё рабочее место», формы, личные/общие заметки, безопасные формулы, атомарная вставка TSV, канбан/календарь/сводная, виджеты, личные задачи и ограниченное правило просрочки. Светлая/тёмная темы и прежний товарный модуль сохранены. Подробный документ отделяет принятые решения от предлагаемой реализации; статусы SYSTEM_PLAN.md не менялись.

Изменены: `docs/SYSTEM_DESIGN.md`, `docs/design/prototype.html`, `docs/design/grid-app.js`, `docs/design/guide.html`, `docs/design/README.md`, `docs/design/checksums.sha256`, `CHANGELOG.md`. Новые файлы: `docs/design/workbench-app.js`, `docs/design/workbench-engine.js`, `docs/design/workbench-style.css`, `docs/design/WORKSPACE_V3.md`, `docs/design/workspace-v3-guide.html`. Исходные копии существующих файлов до правки — `.change-backups/2026-10-02/workspace-v3-114310/<relative-path>`, SHA-256 — `manifest.json`. Во время работы другая задача дополнила корневой CHANGELOG; её записи сохранены, актуальная копия непосредственно перед нашим добавлением — `.change-backups/2026-10-02/workspace-v3-114310/CHANGELOG.before-v3-append.md`. Поздние сторонние коммиты/файлы не откатывались и не редактировались.

Локальные артефакты: `output/playwright/workspace-v3-20261002/qa-results.json`, синтетический `demo-invoice.txt`, снимки экранов, журналы временного HTTP-сервера и `server-identity.json`; новый снимок CLI `.playwright-cli/page-2026-10-02T09-05-57-644Z.yml`. Их точные пути и SHA-256 перечислены в `.change-backups/2026-10-02/workspace-v3-114310/after-manifest.json`; новые служебные `qa-before.json`, `manifest.json`, `after-manifest.json` относятся только к локальному откату и не коммитятся.

Проверка: Node --check для новых JS и изменённого grid-app; 52 проверки движка (блокировка, атомарность, ревизии/согласование, формулы/циклы/недопустимый код). В настоящем Edge через существующий Playwright CLI пройдены: блокировка и чтение/комментарии вторым профилем, неизменность общей версии до решения, запрет manager approve, возврат с причиной, сохранение/возобновление черновика, согласование правки и полной новой записи (ревизии 7→8→9), TSV в визуальном порядке групп и отклонение всего ошибочного диапазона, undo/redo, соседний фокус после ввода, личные расчёты и их перенос, циклы/очистка формул, изоляция личных полей/заметок/листа, формы/метаданные, календарь вне месяца, канбан/сводная, фильтр/цвет/личный вид, виджеты и личные задачи. Финальный проход не дал pageerror. Снимки desktop 1536×960 и mobile390×844 в обеих темах просмотрены; горизонтального переполнения страницы нет. HTML-документ: проверены 13 якорей, локальные ссылки и desktop/mobile. Исходный текст старого guide сохранён. SHA-256 и diff --check с core.whitespace=cr-at-eol проверены; CRLF исходных файлов не считается ошибкой.

В ходе проверки исправлены: порядок вставки при группах, имя операции notEmpty, полное отображение новых полей на согласовании, причина возврата, фокус/отмена в полях ввода и синхронизация формул, стили сетки/форм/мобильного вида. Две ошибки harness (неоднозначный close locator и недоступный Buffer) исправлены в проверочных командах; синтетические данные не выходили за локальный браузер.

Границы: это локальный демонстрационный макет с localStorage, не реальная серверная изоляция, блокировка или сохранение рабочих данных. Личный лист A1:H10 с ограниченным языком формул; совместимость с Google Sheets/XLSX не заявлена. Вложения — только личные имена/размеры, содержимое не читается/не загружается. После inline правки сортировка/фильтры обновляются при следующей перерисовке, чтобы не сдвигать курсор. file:// автоматизированно не проверялся; HTTP-проверка выполнена. Runtime frontend/backend, зависимости, серверы проекта, production и интеграции не менялись; коммит/push/deploy не выполнялись. Созданные только для QA Edge session mw-v3-20261002 и Python PID5880 остановлены после проверки PID/start/command; порт18768 закрыт.

Безопасный откат: сначала сравнить текущие файлы с after-manifest и проверить позднюю работу; применить только обратные изменения v3 из сохранённых копий к шести изменённым design-файлам, корневой CHANGELOG дополнить записью отмены, не заменять весь журнал. Пять новых исходных файлов и перечисленные локальные артефакты удалять только при совпадении SHA-256 и отсутствии поздних изменений/ссылок; при расхождении сохранить их и разбирать diff. Для собственных демо-данных можно удалить только ключи mw-workbench-v3:shared/owner/manager, предварительно сохранив нужные личные настройки; mw-grid-v2 не затрагивать. Не использовать reset --hard, clean, рекурсивное удаление общей output или откат чужой работы.


## 2026-10-02T12:39:19+03:00 — Проверено восстановление владельца E2-06 через браузер и операторскую команду

Причина: после push Олега продолжен уже явно разрешённый изолированный owner rehearsal. Опубликованный 14d9f48cee6eb2a9d7eca9f029770af51c45b6d9 проверен ls-remote; серверный repository fast-forward, новый detached Git release. Основной web не переключался. Посторонняя работа docs/design/* и docs/SYSTEM_DESIGN.md сохранена; во время выполнения появилась чужая запись CHANGELOG о v3, она сохраняется в рабочем файле и не включается в E2-06 commit. Копия непосредственно перед добавлением нашей записи — `.change-backups/2026-10-02/E2-06-owner-retry/CHANGELOG.before-e206-append.md`; отдельный `commit-changelog.md` содержит только HEAD-журнал плюс эту запись для выборочного index, рабочий журнал не перезаписывается.

Изменены ровно: `backend/tools/owner_rehearsal.py`, `scripts/e2_06_owner_browser.cjs`, `docs/E2-06_OWNER_REHEARSAL.md`, `docs/E2-06_SESSIONS_MFA.md`, `SYSTEM_PLAN.md`, `SYSTEM_SECURITY_CHECKS.json`, `CHANGELOG.md`. До изменения семь файлов сохранены в `.change-backups/2026-10-02/E2-06-owner-retry/before/<relative-path>`; before/after hashes в manifest.json. Новый tracked файл: `docs/E2-06_WEB_FIX_ROLLOUT.md`. Новые локальные evidence в том же каталоге retry: `manifest.json`, `start.txt`, `browser.txt`, `state-diagnostic.json`, `final-state.json`, `stop.txt`, `main-counts.json`, `local-checks.json`, `result.json`, `CHANGELOG.before-e206-append.md`, `commit-changelog.md`. Значений секретов/кодов/cookies/паролей/provisioning URI/личных данных нет; приватный транспорт браузера остаётся в памяти.

Сервер: возобновлён только сохранённый marketplace-e206-owner-check. Preflight подтвердил принадлежность остановленных четырёх контейнеров/network/volume и прежний source6ec715f; три основных контейнера совпали с baseline. Существующий PostgreSQL17.11 запущен; только controller/issuer/web получили RO source14d9f48. Lock совпал с прежним image86f9cac63025, effective Compose/SQL runtime/изоляция PASS. Read-only pre_browser проверил состояние до первого входа (4 users/2 org/5 memberships; нулевые factors/sessions/codes/permits/challenges/buckets/trust), прежние пароли/владение и proof/verifier. Никаких --apply/bootstrap/configure/init/operator_prepare/сброса counters/новых ключей/ролей/БД/зависимостей/сборок не выполнялось.

Реальный Chromium прошёл 8 функциональных этапов: invalid/expired/valid enrollment и однократный показ кодов; replay TOTP, запрет disable владельцу, CSRF; current/selected/all sessions, trusted device и reauth; однократный recovery code и отзыв старой сессии; настоящая issue_owner_recovery под mw_beta_migrator с getpass/PTY без echo, неверным proof/чужим владельцем, one-use permit и limited reenrollment; password change с сохранением MFA и отзывом trust; block/session/code/operator denial; добровольный password-only вход не подключавшего MFA участника. Корректный новый пароль был проверен реальным входом до блокировки. Основная модель владения/права сохранены. Не заявляется повтор S1 concurrency/17SQLdenials/export-probe/dump-restore: это прежние доказательства.

Сводный runner exit1 не скрыт: последняя helper-проверка ожидала next_password после block_account, но E2-05 штатно устанавливает unusable password. Повторный read-only finish воспроизвёл этот отказ, диагностика обнаружила только неверное ожидание. Правильный финал независимо проверен прямым read-only чтением PostgreSQL: active=false, has_usable_password=false, оба пароля отвергаются; все сессии/trust отозваны, единственный permit used, 4/2/5 и владение неизменны, приглашений0. Закрытые operator outputs0600 присутствуют только для успешных команд; файлы отказов отсутствуют. Session payloads/TOTP зашифрованы, recovery verifiers PBKDF2, plaintext OTP tables пусты, locmem. Глобальный pageerror counter не дошёл до проверки после failed RPC; zero pageerrors и чистый aggregate PASS не заявляются.

Локально исправлен только helper finish на проверку unusable password, а runner теперь явно обозначает final-state и проверяет pageerrors до финального RPC. Runtime auth/accounts/ownership/миграции/SQL/lock в этом commit не меняются. Существующие локальные регрессии E2-05 block и MFA block пройдены отдельно (1/1 за2.199s и1/1 за4.539s, SQLite; не новый PostgreSQL-suite). AST/Node syntax PASS. Исправленный helper ещё не запускался на сервере из нового опубликованного Git revision. Полный сценарий на использованном fixture не повторялся; владелец остаётся заблокированным, permit использован.

Четыре новых контейнера остановлены, volume/network/закрытые keys/fixture/proof/verifier/permit/releases сохранены. Browser/tunnel18767 закрыты. Основной web/оба PostgreSQL сохранили ID/image/StartedAt/mounts/networks/ports до и после остановки; restricted runtime SQL PASS. Итог main SELECT: users/org/memberships/authenticators/codes/permits/account sessions=0, четыре анонимные encrypted Django sessions. GET login smoke может создать анонимную wizard session; это не полноценный вход и не доказательство побайтовой неизменности DB. Source основной beta остаётся19a6d6a с дефектом no-referrer; никаких реальных аккаунтов/ключевых передач/Telegram/production/main/Caddy/FBS/WB/Finkos/посторонних проектов не меняли.

Подготовлен конкретный docs/E2-06_WEB_FIX_ROLLOUT.md для отдельного разрешения: только основной web на уже опубликованный/проверенный14d9f48, прежний image/lock/ключ/SQL; закрытый metadata backup, сохранённые прежние DB/key backups с явными историческими ограничениями, без миграций/DBrestore/новых DB/ролей/ключей. Анонимный browser header/Origin probe отменяет POST до сервера. Fallback — проверенный MFA maintenance или stop только web. Этот этап не запускался и не разрешён текущим owner rehearsal. E2-06 «На проверке»; 101 строка и критерии плана прежние, independent key custody/полный экспорт и оговорённые ограничения итогового runner остаются открыты.

Безопасный откат: проверить hashes и поздние изменения, применить только обратный diff семи E2-06 файлов; CHANGELOG дополнить отменой, чужую запись v3 не удалять. Новый rollout-plan удалять только при совпадении hash/отсутствии поздних ссылок и разрешений; evidence сохранять до переноса протокола. Не reset --hard/clean. Серверный стенд уже остановлен, его volume/файлы сохраняются; не разблокировать/пересоздавать fixture, не запускать старые probes. Основную beta откатывать не нужно, она не обновлялась. Локальный commit Oleg «Проверено восстановление владельца и исправлена итоговая проверка блокировки»; push выполняет Олег.


## 2026-10-02T12:59:24+03:00 — Подготовлен локальный коммит макета рабочего места v3

По явному запросу Олега «коммить» в ветке beta фиксируется только подготовленный дизайн v3: корневой CHANGELOG.md, docs/SYSTEM_DESIGN.md, docs/design/README.md, docs/design/checksums.sha256, docs/design/grid-app.js, docs/design/guide.html, docs/design/prototype.html, docs/design/WORKSPACE_V3.md, docs/design/workbench-app.js, docs/design/workbench-engine.js, docs/design/workbench-style.css, docs/design/workspace-v3-guide.html. Название коммита: «Добавлены личное рабочее место и управляемые таблицы в макет v3». Автор и коммитер — Oleg, существующая Git identity из истории; внешняя отправка не запрашивалась и не выполняется.

Повторно проверены Node --check трёх JS, diff --check с учётом CRLF, 13 SHA-256 дизайн-файлов и 5 SHA-256 новых исходников из after-manifest.json. Рабочие файлы совпадают с ранее проверенным макетом; повтор браузерных сценариев не требовался. Staging перед операцией пуст, runtime frontend/backend не включаются. Результаты предыдущей UI-проверки и её ограничения сохранены в записи v3 выше. Локальные output, .playwright-cli, .change-backups остаются вне коммита.

Перед добавлением этой записи журнал сохранён в `.change-backups/2026-10-02/workspace-v3-commit-125924/CHANGELOG.md`; SHA-256 и исходный HEAD — в соседнем manifest.json. Журнал дополняется в конце, чужие записи не заменяются. Откат после проверки поздних изменений: применить обратный diff только v3-файлов (либо отдельный git revert этого коммита после проверки конфликтов); журнал дополнить записью отмены, не восстанавливать его целиком. Без reset --hard/clean; новые локальные копии журнала и manifest удалять лишь после проверки их SHA-256 и ненужности для отката.


## 2026-10-02T13:41:10+03:00 — Обновлён основной beta web и проверены браузерные заголовки MFA

Причина: применено исправление Referrer-Policy после успешных функциональных этапов отдельного owner rehearsal, строго по явному разрешению Олега на docs/E2-06_WEB_FIX_ROLLOUT.md. Публикация beta 91b079a30569b6fc38997b47fe18d6af723b9321 подтверждена; сервер получил код только Git fast-forward, использован существующий read-only release 14d9f48cee6eb2a9d7eca9f029770af51c45b6d9. Пересоздан только marketplace-beta web. Исполняемое приложение отличается от 19a6d6a только same-origin вместо no-referrer; CSRF не ослаблен, существующий image/lock/ключи/миграции/SQL-права сохранены. Новых установок/сборок/ролей/БД/ключей/миграций/GRANT/restore нет.

Изменены точные файлы: CHANGELOG.md, SYSTEM_PLAN.md, SYSTEM_SECURITY_CHECKS.json, SYSTEM_STARTUP.md, docs/RUNBOOK.md, docs/E2-06_SESSIONS_MFA.md, docs/E2-06_WEB_FIX_ROLLOUT.md, SYSTEM_STARTUP_CHECKS.json. SYSTEM_STARTUP_CHECKS.json локальный ignored, в коммит не включается; исправлено также испорченное старое отображение task_status. Исходные копии каждого файла: `.change-backups/2026-10-02/E2-06-main-web-fix/before/<тот же относительный путь>`, исходные SHA-256 в manifest.json и startup-before.json. Новые локальные артефакты внутри `.change-backups/2026-10-02/E2-06-main-web-fix/`: manifest.json, startup-before.json, preflight.txt, checkpoint.json, switch.txt, browser.json, final-state.jsonl, result.json, local-checks.json. Содержат только разрешённые metadata/счётчики/результаты, без секретных значений/токенов/cookies/provisioning URI; каталог не коммитится. Код приложения и посторонние файлы не изменены.

Новый серверный файл: `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-referrer-before-20261002T102702Z.metadata.json` (0600, no-overwrite, fsync/read-back equal). Проверены наличие/0600 прежних e2-06-before-20261001T144009Z.dump, его .acl.json/.snapshot.json, e2-06-main-key-envelope/envelope.json и отдельных runtime key/passphrase; значения не выводились. Это metadata checkpoint переключения, не новый dump/restore; S1/S2 остаются историческими доказательствами. Первый локальный Python wrapper остановился с SyntaxError до SSH/создания checkpoint; quoting исправлен, повторная подготовка прошла.

Новый основной web ID `53dd81f2850521138b9596d1aa5f910f7889785d8836329efbbfb0f7b57654c5`, StartedAt `2026-10-02T10:28:21.386899228Z`, source `/home/adm_user/marketplace-workspace/beta/app/releases/14d9f48cee6eb2a9d7eca9f029770af51c45b6d9/backend`. Image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`, RO mounts, UID10001:10001, 384MiB/0.25CPU, private network/no ports прежние. Оба PostgreSQL сохранили ID/image/StartedAt/mounts/networks/ports. Сохранённые четыре контейнера owner rehearsal не запускались; его baseline не переписывался.

Проверки: фактическая mw_beta_web / exact column ACL / guards PASS до и после; 36 записей миграций прежние. Runtime PASS: live/ready200, session401, legacy login GET405, MFA login GET200. Chromium: same-origin/no-store, Secure cookies/CSRF поле, native POST с корректным Origin; POST отменён до сервера, credentials не отправлялись, pageerrors0 только для этой анонимной проверки. Browser/tunnel закрыты. Итоговые users/org/memberships/authenticators/recovery codes/permits/account sessions/attempt buckets/auth denials=0; encrypted anonymous Django sessions4→6 от GET login. Locmem/внешние flags off/public probe off, runtime key0600 UID10001 и server Git clean подтверждены. Полный S1 suite/owner browser не повторялись; публичный TLS не проверен.

Локальная проверка перед коммитом: JSON/read-back/backup hashes, append-only CHANGELOG, сохранность 101 строки и критериев плана, git diff --check и точный состав изменений; результат в local-checks.json. План/протокол сохраняют «На проверке»: исправленный helper опубликован, но не запускался на Linux; общий pageerror counter и чистый итог полного runner, независимая копия ключа у Олега и рабочий экспорт остаются незакрытыми. Real owner proof/передача envelope/пароля/Telegram не выполнялись; будущие конкретные операции с ними требуют отдельного разрешения. E2-07/E2-08/E5-07, production/main/Caddy/FBS/WB/Finkos/worker/UI не менялись.

Безопасный откат: сначала сравнить текущие файлы и исходные hashes, затем отменить только этот документальный diff, сохранив позднюю/постороннюю работу; запись журнала не удалять. Локальные новые артефакты удалять только после проверки отсутствия потребителей и сохранения нужного доказательства. Серверный checkpoint сохранять до окончания приёмки, удаление — отдельное явное действие после сверки пути/ссылок. Рабочий fallback — согласованный MFA deny-auth maintenance либо stop только основного web; base-only/accounts overlay, обратные миграции, удаление ключей/занятых БД/release и restore поверх живой БД запрещены. Fallback здесь не применялся. Локальный коммит автора Oleg, push выполняет Олег.


## 2026-10-02T13:41:23+03:00 — Выполнена независимая проверка макета v3

По запросу беспристрастной обратной связи проверен commit91b079a: исходники, описание, восемь разделов, светлая/тёмная темы, ноутбук1366×768, телефон360×800 и1000 синтетических строк. Три независимых read-only оценки дополнены воспроизведением в Edge. Найдены6 групп проблем: устаревший черновик без доступного сравнения/переноса;8 видимых строк против7 в счётчике после inline-фильтра; ложные пустые результаты фильтров по датам и текстовым формулам; общая панель настроек меняет скрытый товарный вид вместо закупок; потеря несохранённого оформления вида; потеря фокуса при последовательном вводе личных ячеек. Статические рекомендации отдельно: единый договор настроек, массовый ввод/жизненный цикл личных полей, полноценные таблицы рядом, сокращение верхних панелей. Сбоя мобильного закрепления не обнаружено;1000 строк открылись за694мс и выбор всех занял261мс в одном прогоне — не нагрузочная проверка продукта.

Код не исправлялся. Новый локальный отчёт `output/playwright/workspace-v3-review-20261002/review-results.json`, снимки и журналы в той же папке; точный перечень/SHA-256 — `.change-backups/2026-10-02/workspace-v3-review/manifest.json`. Исходный журнал сохранён рядом как CHANGELOG.md. Собственные Edge-session mw-review-20261002 и Python PID22420 закрыты после сверки идентичности, порт18769 закрыт. Прод/рабочие данные не затрагивались, коммит не выполнялся. Откат: после сравнения hashes удалить только новые неизменённые артефакты из manifest, журнал дополнить отменой, не заменять историю и не удалять общие output/.playwright-cli каталоги.


## 2026-10-02T13:43:20+03:00 — Сохранены параллельные изменения при фиксации результата E2-06

Во время проверки документации в CHANGELOG.md появилась чужая запись о проверке макета v3, а в docs/design — новый APPEARANCE_PRESETS.md. Они сохранены без правок и не включаются в коммит E2-06. Общий git diff --check обнаружил CRLF-пробелы только в чужой записи; проверяется точный staged diff E2-06, чужое форматирование не исправляется. Исходный журнал перед этим дополнением сохранён в `.change-backups/2026-10-02/E2-06-main-web-fix/concurrent-CHANGELOG.md`, SHA-256 — в новом concurrent-check.json того же каталога. Для точечного staging подготовлен новый index-CHANGELOG.md (HEAD + только две записи E2-06), рабочий журнал не заменяется. Проверки/перечень staged файлов сохраняются в local-checks.json. Эти локальные артефакты не коммитятся; удаление допустимо только после сверки hashes/отсутствия потребителей и сохранения доказательства. Откат этой записи — новым дополнением, без удаления истории или чужой работы.


## 2026-10-02T13:54:53+03:00 — Добавлены личные и общие пресеты оформления таблиц

Во время ревью Олег запросил общие/личные пресеты визуала и подтвердил: общий набор доступен команде, каждый применяет его сам. Добавлена библиотека для «Товары → Оформление → Пресеты оформления» и «Закупки → Цвет → Пресеты оформления». Автор сохраняет текущее оформление с названием и областью «Только мне»/«Для команды», может обновить, переименовать или удалить свой набор; чужой общий набор доступен для применения. Применение сохраняет копию оформления в текущем личном виде и его сохранённой версии. Изменения/удаление оригинала не перезаписывают уже применённые копии.

В состав входят цвета колонок, поддерживаемые условные правила/подсветка, плотность, зебра, линии и формат чисел. Данные, черновики закупки, фильтры, поиск, сортировки, группы, видимость, порядок, ширина и закрепление колонок не переносятся. Общие наборы исключают личные поля и зависимые правила. При применении общего оформления собственные цвета/правила по личным полям сохраняются; личные правила идут перед общими. Настройки недоступных столбцов пропускаются. Запись проверяется до изменения применённого состояния; отказ localStorage возвращает false без ложного success и с восстановлением прежнего состояния.

Изменены `docs/design/grid-app.js`, `docs/design/workbench-app.js`, `docs/design/prototype.html`, `docs/design/README.md`, `docs/design/checksums.sha256`, `CHANGELOG.md`. Новые файлы: `docs/design/appearance-presets.js`, `docs/design/appearance-presets.css`, `docs/design/APPEARANCE_PRESETS.md`. Бэкапы до правок и SHA-256 — `.change-backups/2026-10-02/appearance-presets/<relative-path>` и `before-manifest.json`. Перед этой записью актуальный журнал с параллельными записями другой задачи дополнительно сохранён как `.change-backups/2026-10-02/appearance-presets/CHANGELOG.before-presets-append.md`; журнал дописан без замены истории. Изменения другой задачи в SYSTEM_PLAN/SYSTEM_SECURITY_CHECKS/SYSTEM_STARTUP/E2-06/RUNBOOK не редактировались, не откатывались и не включались в эту работу.

Проверка: Node --check трёх JS;18 проверок модуля,10 проверок протокола и7 проверок отказов хранения/сохранности личных правил. В Edge подтверждены личное/командное создание, разделение областей и таблиц, авторские update/rename/delete, отсутствие принудительного применения, добровольное повторное применение, сохранность фильтра/данных и сохранённого личного вида, перенос условного правила товаров, независимость применённого оформления после обновления/удаления. Светлая/тёмная темы и диалог360px просмотрены. Синтаксис, дизайн-SHA-256 и diff --check с учётом CRLF проверены; исходные окончания строк prototype сохранены. Артефакты/снимки/qa-results.json — `output/playwright/appearance-presets-20261002/`; точные пути и hashes, включая новый CLI snapshot, перечислены в `.change-backups/2026-10-02/appearance-presets/after-manifest.json`. Проверочный Edge session mw-presets-20261002 и Python PID13576 закрыты после сверки идентичности; порт18770 закрыт.

Границы: только localStorage `mw-appearance-v1` и два демонстрационных профиля; настоящие серверные ACL/библиотека команды не реализованы. Пресеты относятся к конкретной готовой таблице, тема остаётся личной. Замечания независимого ревью исходного commit91b079a сохранены отдельно и этим дополнением не объявляются исправленными. Новых зависимостей, плагинов, внешних отправок, production-операций и коммита не было.

Откат: сравнить before/after manifests и текущие файлы с поздней работой; применить только обратный diff этого дополнения к пяти существующим design-файлам, журнал дополнить записью отмены. Три новых файла/локальные артефакты удалять только при совпадении hashes и отсутствии поздних изменений/использования. Собственные демо-пресеты при необходимости предварительно экспортировать и удалить только ключ mw-appearance-v1; остальные localStorage namespace не трогать. Не использовать reset --hard/clean или рекурсивное удаление общих каталогов. Бэкапы/QA остаются локальными и не коммитятся.


## 2026-10-02T13:58:37+03:00 — Проверен исправленный finish на сохранённом PostgreSQL-стенде E2-06

Причина: закрыта отдельная Linux/PostgreSQL-проверка исправленного завершающего helper, по текущему явному разрешению Олега только на запуск сохранённых postgres/controller, read-only finish и остановку. Подтверждён опубликованный dd9803597941e9516676e8f03aa0cb6f48f1eb92; серверный repository обновлён Git fast-forward, создан detached release `/home/adm_user/marketplace-workspace/beta/app/releases/dd9803597941e9516676e8f03aa0cb6f48f1eb92`, source backend read-only у controller. Исполняемый auth-код/lock/Compose не изменены; backend diff к14d9f48 только tools/owner_rehearsal.py.

Изменены точные локальные файлы: CHANGELOG.md, SYSTEM_PLAN.md, SYSTEM_SECURITY_CHECKS.json, docs/E2-06_OWNER_REHEARSAL.md, docs/E2-06_SESSIONS_MFA.md. Исходные копии каждого в `.change-backups/2026-10-02/E2-06-finish-readonly/before/<тот же относительный путь>`, SHA-256 в manifest.json. Перед дополнением общий журнал сохранён также в concurrent-CHANGELOG.md, hash в journal-before.json. Новые артефакты в том же каталоге: manifest.json, run_finish.py, server-result.json, concurrent-CHANGELOG.md, journal-before.json, index-CHANGELOG.md, local-checks.json. Код wrapper проверен AST до SSH; серверный Python выполнялся как кратковременная диагностика через stdin, исходники приложения получены только Git. Сохранены исключительно allowlisted metadata/счётчики/результаты без секретных значений или key fingerprints. Каталог не коммитится.

Сервер: существующий PostgreSQL marketplace-e206-owner-check-postgres ID `3bd4dae16b095ffa63fe40bc7b384e2c27efb1bae8cc2afc5bcc91d035a38ea7` запущен без пересоздания; controller на прежнем image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72` пересоздан с новым RO source. Новый controller `6a6602e6b86644bae7614e8f7bb2194c578984883c8d8c8482143d79f3feaf1b`, StartedAt `2026-10-02T10:54:52.361712667Z`. Сеть internal/no host ports, UID10001/read-only/256MiB/0.25CPU/logging none и secret boundaries проверены; web/issuer не запускались. Минимальная роль для неизменённого operator guard — mw_beta_migrator только отдельного кластера; SQL-сессия дополнительно ограничена default_transaction_read_only=on с подключения. SHOW default/transaction_read_only, фактическая DB/роль, marker/cluster_name/locmem пройдены. Новых DB/ролей/ключей/прав/миграций/установок/сборок нет.

Finish PASS: active=false, unusable password, sessions/trusted=0, used_permits=1, invitations=0, ownership unchanged. Подтверждённый фактор1 сохраняется у заблокированного аккаунта, recovery_required=false; это не восстановленный доступ. Private state/output/secret файлы до/после совпали побайтово и по metadata, без вывода значений. Все четыре контейнера стенда остановлены; volume/network/файлы сохранены. Основной web и оба PostgreSQL основной beta совпали по ID/image/StartedAt/mounts/networks/ports, старый baseline не переписывался. Основной source14d9f48 сохранён; runtime/auth smoke и полный browser не повторялись.

Нового backup/dump/restore не было: SQL только чтение, прежний синтетический volume и закрытые файлы сохранены; S1/S2 restore не выдаётся за новую проверку. Полный aggregate runner всё ещё имеет исторический exit1, итоговый pageerror counter не доказан; отдельный finish не подменяет их. E2-06 остаётся «На проверке»; 101 строка и критерии плана сохранены. Независимое хранение ключа у Олега/реальный owner proof/Telegram/рабочий экспорт не выполнены; соседние E2-07/E2-08/E5-07 не реализуются. Production/main/Caddy/FBS/WB/Finkos/UI не менялись.

Локальная проверка: JSON/read-back, backup hashes, 101 неизменная строка, append-only CHANGELOG и точный staged diff; отчёт local-checks.json. Параллельная работа docs/design и чужая запись журнала сохранены, в коммит E2-06 не включаются; index-CHANGELOG.md содержит HEAD и только это дополнение. Автор локального коммита Oleg; push делает Олег.

Безопасный откат: остановка двух запущенных тестовых контейнеров уже выполнена; основная beta не менялась, SQL-откат не нужен. Не удалять занятые volume/DB/ключи/release и не сбрасывать fixture. Для локальных документов сначала сравнить текущие файлы с backups, затем отменить только этот diff с сохранением поздней/чужой работы; журнал дополнять, не переписывать. Новые локальные артефакты удалять только после сверки hashes/потребителей и сохранения доказательства. Серверный Git release и контейнеры сохранять до отдельного решения. Без reset --hard/clean, live restore или старых probes.


## 2026-10-02T14:03:59+03:00 — Подготовлен локальный коммит пресетов оформления

По текущему явному запросу Олега «делай коммит» фиксируются личные и добровольно применяемые общие пресеты оформления и ранее записанные результаты ревью. Точный состав: CHANGELOG.md, docs/design/README.md, docs/design/checksums.sha256, docs/design/grid-app.js, docs/design/prototype.html, docs/design/workbench-app.js, docs/design/APPEARANCE_PRESETS.md, docs/design/appearance-presets.css, docs/design/appearance-presets.js. Название: «Добавлены личные и общие пресеты оформления таблиц». Автор и коммитер — Oleg. Публикация не выполняется.

Проверены синтаксис трёх JS, 16 SHA-256 дизайн-файлов, diff --check с учётом CRLF и независимая сверка состава. Код совпадает с ранее проверенной в Edge версией; повтор браузерных сценариев не требовался. Runtime и чужие изменения не включены, исходный индекс пуст. Ограничения макета и открытые замечания ревью сохранены в предыдущих записях.

Перед дополнением журнал сохранён в .change-backups/2026-10-02/appearance-presets-commit-140359/CHANGELOG.md; исходный HEAD, SHA-256 и перечень файлов — .change-backups/2026-10-02/appearance-presets-commit-140359/manifest.json. Журнал дополнен без перезаписи истории. Откат: сначала сравнить поздние изменения, затем применить обратный diff только этого коммита к дизайн-файлам, журнал дополнить записью отмены; не заменять журнал целиком. Новые локальные backup/manifest удалять только после сверки hashes и подтверждения ненужности для отката. Без reset --hard/clean. Бэкапы и QA-артефакты остаются локальными.


## 2026-10-02T14:31:59+03:00 — Подготовлен отдельный полный браузерный прогон E2-06 R2

Причина: старый fixture терминальный, исправленный finish отдельно прошёл, но чистый сводный browser exit/pageerror counter ещё не подтверждены. После общего «разрешаю» уточнён объём будущих серверных действий; ответ на уточнение пока не получен. Выполнена только разрешённая локальная подготовка конкретного проверяемого плана. SSH/серверные ресурсы/секреты/миграции/перезапуски не выполнялись.

Изменены точные существующие файлы: CHANGELOG.md, SYSTEM_PLAN.md, SYSTEM_SECURITY_CHECKS.json, docs/E2-06_OWNER_REHEARSAL.md, backend/tools/owner_rehearsal.py, backend/tools/owner_rehearsal_bootstrap.py, beta/deploy/prepare_owner_rehearsal.py, scripts/e2_06_owner_browser.cjs. Исходные копии находятся в `.change-backups/2026-10-02/E2-06-browser-r2-preparation/before/<тот же относительный путь>`, SHA-256 в manifest.json. Перед дополнением общий журнал также сохранён в journal-before.md, hash в journal-before.json. Новые файлы проекта: beta/deploy/compose.owner-rehearsal-r2.json, docs/E2-06_BROWSER_R2.md. Новые локальные артефакты в том же каталоге backups: manifest.json, local-preparation-checks.json, journal-before.md, journal-before.json, index-CHANGELOG.md, local-checks.json; вне Git, без секретов.

Выделен фиксированный профиль marketplace-e206-owner-check-r2 с root /home/adm_user/marketplace-workspace/beta/rehearsals/e2-06-owner-r2-20261002. Новый Compose отличается от старого только именами/путями. Helper/bootstrap/browser разрешают только original/R2; marker, реальный cluster_name, DB/роль operator guard сохранены. Подготовка принимает --project из двух фиксированных вариантов, отказывает на занятых ресурсах и сохраняет metadata основной beta плюс остановленного первого стенда в отдельный preserved-rehearsal.json; исходный baseline не перезаписывается. Browser дополнительно проверяет Compose project controller/issuer. Runtime auth/accounts/ownership/config/migrations/SQL grants/requirements.lock не менялись.

Локальные проверки: 3 Python AST, Node --check; исходный профиль по умолчанию и точные R2 plan paths; отказы неизвестному project, --apply на Windows, helper/bootstrap без нужной среды и browser до SSH при неверных аргументах; сравнение двух Compose после обратной замены идентификаторов; internal/no ports, secret mounts и прежние limits/images/logging none; backup hashes. Итоговый JSON/read-back, неизменные 101 строки/критерии плана, append-only журнал и staged diff проверяются перед коммитом; local-checks.json. Установленные Node/npx/Playwright API/Chromium найдены, установки не выполнялись. Чтение существующего Playwright SKILL.md сначала ограничено sandbox, повторное разрешённое read-only чтение успешно; это не отказ пользовательского approval. Используется прежний приватный API runner без snapshots/traces/вывода секретов, согласно прямому условию Олега.

Документ задаёт новую пустую синтетическую БД/роли, отдельные ключи, 4 пользователя example.invalid/2 организации/5 членств, actual operator CLI и 10 итоговых отметок браузера. Основные S1/S2 backups и первый стенд неприкосновенны; новые R2 volume/закрытые файлы сохраняются после остановки, автоматического restore/reseed нет. Effective Compose/Linux/PostgreSQL/browser не выполнены и не объявляются PASS. E2-06 «На проверке»; публикацию выполняет Олег, запуск требует конкретного согласования плана. Передача основного ключа/реальный proof/Telegram/RBAC/RLS/рабочий экспорт не включены.

Безопасный откат локальной подготовки: сверить текущие файлы и backups, отменить только этот diff, сохранив чужую/более позднюю работу. Новые compose/doc можно удалить только если не изменены и не используются опубликованным серверным этапом; локальные артефакты — после проверки hashes/потребителей и сохранения доказательства. Журнал не удалять, отмену добавлять. После будущего запуска безопасный fallback только stop новых R2 containers с сохранением volume/network/files; без down -v/DROP/prune/live restore/сброса counters или изменений старого стенда/main beta. Production/main/Caddy/FBS/WB/Finkos/другие проекты не затронуты. Локальный коммит автора Oleg, push не выполняется агентом.


## 2026-10-02T14:49:58+03:00 — Подготовлена передача копии ключа E2-06 и создан отдельный файл пароля

Получено явное уточнение Олега: полный browser на отдельном синтетическом стенде и подготовка передачи ключа. Авторизация R2 зафиксирована, его запуск ожидает публикации 400f462 самим Олегом; SSH/серверные действия в этом шаге не выполнялись. Подготовка передачи не объявляется разрешением фактического чтения/обёртки/скачивания основного key. Затем Олег отдельно попросил файл пароля и подтвердил хранение обоих файлов в Telegram после объяснения общего риска доступа. Это явное изменение прежнего решения, а не молчаливое ослабление условий.

Изменены: CHANGELOG.md, SYSTEM_PLAN.md, SYSTEM_SECURITY_CHECKS.json, docs/E2-06_BROWSER_R2.md, docs/E2-06_SESSIONS_MFA.md. Исходные копии каждого в `.change-backups/2026-10-02/E2-06-key-handoff-preparation/before/<тот же относительный путь>`, hashes в manifest.json; журнал перед дополнением также сохранён в journal-before.md. Новые отслеживаемые файлы: docs/E2-06_KEY_HANDOFF.md, backend/tools/check_mfa_key_envelope.py, backend/account_security/tests/test_key_envelope_check.py. Новые локальные артефакты в указанном backups каталоге: manifest.json, prepare_owner_passphrase.ps1, passphrase-file-result.json, journal-before.md, index-CHANGELOG.md, local-checks.json. Они содержат только код/безопасные metadata, без значений/fingerprints секретов; каталог не коммитится.

По прямому запросу Олега создана новая закрытая папка C:/Users/krolo/Documents/marketplace-recovery и её beta, файл C:/Users/krolo/Documents/marketplace-recovery/beta/e2-06-backup-passphrase-20261002.txt. Проверены отсутствие занятых путей/reparse points, Windows ACL текущего пользователя и SYSTEM без широких правил, отключение наследования у обоих каталогов, ACL файла, эксклюзивное создание и read-back. Пароль создан криптографическим RNG, в stdout/отчёт/Git/clipboard не попадал; fingerprints не сохранялись. Это новый пароль будущего envelope, не пароль старого S2 и не TOTP key. SSH/чтения ключа/нового envelope/Telegram/отправок не было.

План K1/K2/K3 предлагает новый envelope того же RO runtime key с этим паролем через штатный Linux wrap/getpass; отдельный приватный локальный файл ciphertext вне Git, сверку передачи без раскрытия, локальную проверку в памяти и ручную загрузку/скачивание Олегом. Runtime key, БД, основной web, существующие S2 backups и реальный owner proof не изменяются. Фактические server wrap/download и независимая копия остаются отдельным разрешением и проверкой. Совместное Telegram-хранение не выдаётся за независимый канал пароля.

Новая утилита check_mfa_key_envelope только читает ограниченный обычный envelope-файл, вызывает существующий unwrap и не возвращает/не пишет plaintext key. CLI требует интерактивный stdin/stdout, getpass fallback с echo превращается в отказ; ошибки без данных. Существующий запрет plaintext restore на Windows в mfa_key_backup.py сохранён. Три синтетических теста SimpleTestCase прошли без БД за1.084s, 0 skips: верный/неверный пароль и повреждённый envelope без plaintext/new files; отказ до prompt без TTY; отказ getpass echo fallback. Это не реальный owner terminal/SQL/передача. PowerShell AST создания приватного файла проверен до исполнения, ACL/read-back подтверждены фактически. Новых зависимостей нет.

Локальные JSON/AST/backup hashes, 101 неизменная строка плана, append-only CHANGELOG и staged diff проверяются перед коммитом; local-checks.json. Статус E2-06 «На проверке»: R2/независимая копия ключа/рабочий экспорт не закрыты. Production/main/Caddy/FBS/WB/Finkos/другие проекты не менялись. Локальные коммиты автора Oleg, push выполняет Олег.

Безопасный откат: локальные документы/утилиту отменять только точечным обратным diff после сравнения текущих файлов и backups, с сохранением чужой/поздней работы; запись журнала не удалять. Новые исходники удалять только если не изменены/не используются. Файл пароля и каталоги сохранять до решения Олега; удаление допустимо только по отдельному указанию после подтверждения, что этот пароль не используется ни одним envelope и файл не изменён, с проверкой точного абсолютного пути; рекурсивное удаление общей папки запрещено. Локальные evidence удалять после сверки и сохранения нужного доказательства. Серверного отката нет, поскольку server key/копии/контейнеры не менялись.


## 2026-10-02T15:23:05+03:00 — Пройден полный браузерный прогон E2-06 R2

Причина: закрыть чистый aggregate exit и pageerror counter после исправления финального helper, не сбрасывая старый терминальный fixture. Олег явно разрешил полный браузерный прогон и подготовку передачи ключа, затем сообщил о публикации. origin/beta проверена на 2c2f8f737262267d29d06ab40d7bef3571693745, локальная и серверная beta чистые; сервер получил код только Git fast-forward/new detached release. Push агентом не выполнялся.

Точные изменённые локальные файлы: CHANGELOG.md, SYSTEM_PLAN.md, SYSTEM_SECURITY_CHECKS.json, docs/E2-06_BROWSER_R2.md, docs/E2-06_OWNER_REHEARSAL.md, docs/E2-06_SESSIONS_MFA.md. Исходные копии: .change-backups/2026-10-02/E2-06-browser-r2-run/before/<тот же относительный путь>, hashes в backup-manifest.json; журнал непосредственно перед дополнением — journal-before.md. Новые локальные артефакты в том же каталоге: run_r2.py, record_result.py, setup-result.json, browser-result.json, final-result.json, backup-manifest.json, journal-before.md, journal-entry.md, local-checks.json, index-CHANGELOG.md, check_terminal_readonly.py, terminal-readonly-result.json; исходный record_result.py перед коррекцией сохранён в before-audit-correction/record_result.py. Только безопасные metadata/счётчики/код, без секретов и key fingerprints; вне Git.

Созданы ровно новые R2 ресурсы из опубликованного docs/E2-06_BROWSER_R2.md: project marketplace-e206-owner-check-r2; containers с суффиксами postgres/web/controller/issuer; private internal network, data volume; root /home/adm_user/marketplace-workspace/beta/rehearsals/e2-06-owner-r2-20261002 с новыми 0600 secrets/state/operator-output и baseline.json/preserved-rehearsal.json. Новые БД/роли mw_beta/mw_beta_bootstrap/mw_beta_migrator/mw_beta_web принадлежат только отдельному PostgreSQL-кластеру. Fixture 4 example.invalid пользователя/2 организации/5 членств. Код RO из beta/app/releases/2c2f8f737262267d29d06ab40d7bef3571693745/backend. Существующие pinned images, без pull/build/install; PG/web/controller/issuer 384/384/256/256MiB, CPU0.25, logging none. Выполнены одноразовые UID/secret/bootstrap контейнеры в пределах плана; они завершены/удалены штатным --rm.

Проверки: effective Compose и фактические limits/mounts/UID/read-only/internal/no host ports; lock с image совпал, рабочий runtime auth/settings/ownership/migrations/SQL grants неизменен. Миграций 36 на PostgreSQL17.11; точный restricted web LOGIN/SQL-контракт и HTTP runtime smoke до браузера PASS. Полный Chromium: 10 PASS, result=PASS, exit0, actualOperatorCli=true, pageerrors0. TOTP wrong/expired/valid/replay, ограниченная стадия до MFA, CSRF, сессии/trust/reauth, одноразовые коды, реальная CLI proof/owner-binding/permit, смена пароля с сохранением MFA, блокировка/code/operator denial и добровольный member login. Настоящее время/штатные throttles, без сбросов counters/last_t. Финальный SQL read-only PASS: owner inactive/unusable password, sessions/trust0, used permit1, invitations0, ownership unchanged; factor1 остаётся заблокированным состоянием аккаунта. Файлы0600/содержимое/metadata неизменны при итоговом чтении; только locmem.

Tunnel закрыт, все четыре R2 контейнера остановлены; volume/network/files/release сохранены. ID/image/StartedAt/mounts/networks/ports основных трёх beta контейнеров и четырёх остановленных старого стенда совпали до/после. Основной web остаётся14d9f48; основной key, БД, права, backups и старый fixture не менялись. Исторический browser exit1 не переписан; новый R2 дал независимый полный PASS. Конкурентность/17 SQL-отказов/export link/dump/restore/maintenance — прежнее S1, не выданы за повтор. K1/K2/K3 не выполнены; основной key не читался и envelope не создавался/не скачивался. Telegram/реальный owner proof/production/main/Caddy/FBS/WB/Finkos/соседние задачи не затронуты.

SYSTEM_PLAN.md сохранён «На проверке»: независимая копия ключа владельца и рабочий экспорт ещё не закрыты; 101 строка/критерии неизменны. JSON/read-back/backup hashes/append-only журнала и точный staged diff проверяются перед коммитом, local-checks.json. Код приложения не менялся, повтор локальных MFA тестов не требуется. Внешний итоговый audit сначала отказал из-за обращения к User.email вместо AccountContact.email; browser exit0 уже был подтверждён. Сохранены первый FAIL/остановка, затем исправленный SQL read-only PASS через временный старт только тех же postgres/controller и повторную остановку; web/issuer не запускались, browser не повторялся. Локальный коммит автора/коммитера Oleg; публикация только Олегом.

Безопасный откат server run уже выполнен остановкой только R2. Не down -v/DROP/prune/live restore/reseed/сброс buckets, не перезапускать старый fixture. Новые занятые ресурсы/закрытые файлы/release сохранять до отдельного решения; удаление только по точному плану после подтверждения ненужности. Локальные документы откатывать обратным diff после сравнения с backups, сохраняя позднюю/чужую работу; журнал дополнять, не стирать. Локальные артефакты удалять лишь после сверки и сохранения доказательства. Без reset --hard/clean. Следующее отдельное разрешение — конкретные K1/K2 в docs/E2-06_KEY_HANDOFF.md с вводом пароля владельцем; K3 выполняет Олег вручную.


## 2026-10-02T15:44:49+03:00 — Подготовлено разрешённое получение копии ключа E2-06 K1/K2

Олег отдельно разрешил конкретные K1/K2 после итогового R2. Проверена публикация b3c50f7034bd454ea8066c6f194010d91ca9068a, локальная beta чистая. Выполнена серверная подготовка по docs/E2-06_KEY_HANDOFF.md, фактический wrap/transfer ожидает скрытого ввода владельца. Повторное согласование K1/K2 не требуется; секреты не запрашиваются в чате.

Изменены точные файлы: CHANGELOG.md, SYSTEM_PLAN.md, SYSTEM_SECURITY_CHECKS.json, docs/E2-06_KEY_HANDOFF.md, docs/E2-06_SESSIONS_MFA.md. Исходные копии `.change-backups/2026-10-02/E2-06-key-handoff-k1-k2/before/<тот же относительный путь>`, SHA-256 в backup-manifest.json; журнал непосредственно перед дополнением — journal-before.md. Новые локальные артефакты в том же каталоге: server_step.py, prepare-result.json, owner-key-handoff.ps1, owner_wrap_console.py, download_envelope.py, check_owner_argv.py, check_owner_argv.ps1, backup-manifest.json, journal-before.md, journal-entry.md, local-checks.json. Перед коррекцией launcher сохранён в before-terminal-compatibility/owner-key-handoff.ps1. Эти скрипты/metadata не коммитятся и не содержат значений секретов/ciphertext/key fingerprints. Будущие owner-wrap-result.json, verify-result.json, download-result.pending/download-result.json и owner-verify-result.json пока отсутствуют, их наличие и PASS не предполагаются.

Сервер: используется существующий published RO release2c2f8f7 и прежний pinned image sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72; backup/crypto/operator/lock неизменны относительно main14d9f48, lock совпал с image. Main RO key mount/source сверены. ID/image/StartedAt/mounts/networks/ports основной beta и обоих остановленных rehearsal сверены до/после. Существующие runtime key/S2 envelope/passphrase проверены только stat metadata (0600/UID10001/size/mtime/inode), содержимое/fingerprints не читались. После проверки отсутствия создан только `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-owner-key-envelope-20261002`, mode0700/UID10001. UID установлен одноразовым network-none/readonly/logging-none контейнером с CHOWN и mount только нового каталога. Проверочные one-off контейнеры завершены с --rm. Никаких web/PG restart, SQL/roles/migrations, новых ключей, envelope или копирования пока нет.

Локально read-only проверены ACL существующего marketplace-recovery/beta и файла пароля (владелец/SYSTEM), отсутствие целевого envelope; пароль не прочитан. Подготовленный launcher требует собственный TTY Олега; агент не получает его stdout/stdin или пароль. После actual wrap агент выполнит только приватное получение ciphertext/ACL/readback/byte equality; затем launcher вызовет прежний read-only verifier с вводом Олега. Значения не попадут в argv/ENV/Git/логи, plaintext key не скачивается/не создаётся. Telegram и реальные owner proofs не затрагиваются.

Проверки: Python local/remote AST, PowerShell parser, ciphertext tool --check; локальная проверка прямой передачи длинного SSH argv через старый PowerShell отказала до SSH, вызов заменён Python subprocess с наследованием приватного терминала. Исправленный Windows argv roundtrip PASS, неинтерактивный вызов отвергнут до SSH. Одна первоначальная попытка генерации launcher остановилась локальным PowerShell parser до исполнения, затем файл создан и синтаксис проверен. Это статическая проверка транспорта, не реальный getpass/wrap/decrypt. JSON/readback, backup hashes, 101 неизменная строка/критерии плана, append-only журнал и diff --check проверяются перед локальным коммитом. E2-06 «На проверке»: actual K1/K2/K3 и рабочий экспорт не закрыты.

Откат: сохранить новый закрытый пустой каталог и подготовленные скрипты до завершения handoff; не перезапускать prepare/wrap и не перезаписывать output. Основной web/БД/key/старые копии не менялись, runtime откат не нужен. Любое удаление нового/частичного output — только отдельное решение после сверки точного абсолютного пути и отсутствия использования; старые key/envelope/passphrase сохранять. Локальные документы отменять только обратным diff после сравнения backups с текущим состоянием, сохраняя чужую/позднюю работу; журнал дополнять. Новые локальные служебные артефакты удалять после завершения процесса и сохранения нужного доказательства, не во время ожидания launcher. Без reset --hard/clean/рекурсивного удаления. Push выполняет Олег, автор/коммитер локального коммита Oleg. Production/main/Caddy/FBS/WB/Finkos/другие проекты не менялись.


## 2026-10-02T15:47:25+03:00 — Уточнён запуск закрытого терминала K1/K2 на Windows

По сообщению Олега штатная ExecutionPolicy отказала в запуске owner-key-handoff.ps1 до исполнения. Передана команда powershell.exe -NoProfile -ExecutionPolicy Bypass -File с точным локальным launcher; разрешение только для нового процесса, настройки пользователя/компьютера не меняются. Секреты/скриншоты приватного ввода не запрашивались. Дополнены только docs/E2-06_KEY_HANDOFF.md и CHANGELOG.md; исходные текущие копии в .change-backups/2026-10-02/E2-06-key-handoff-k1-k2/before-terminal-policy/<тот же относительный путь>. Runtime/сервер не менялся этим уточнением; фактический wrap ещё ожидается. Проверка — чтение сообщения PowerShell и ранее выполненные parser/TTY/argv checks; успешный пользовательский запуск не предполагается. Откат — после сравнения текущих файлов убрать только добавленную инструкцию при необходимости, запись журнала сохранить; системную ExecutionPolicy откатывать не требуется. Локальные копии удалять только после сохранения доказательств и завершения процесса.


## 2026-10-02T15:56:18+03:00 — Зафиксирован отказ первого интерактивного K1 без создания копии

Владелец обошёл ExecutionPolicy только для запущенного процесса; достигнуто штатное приглашение getpass, что видно на предоставленном screenshot без секретов. После сообщения о проблеме вставки даны инструкции скрытого ввода. Launcher записал owner-wrap-result.json с exit1 в 2026-10-02T15:50:17.0879930+03:00. Текст причины пока не получен; ввод/stdout частного терминала не захватывались. Не считаем причиной ошибку пароля/crypto без подтверждения. Значения пароля/ключа агент не читал и не выводил. Возможное чтение ключа внутри разрешённого CLI в памяти не определено.

Первый metadata verify по сообщению «запустил, ожидаю» был выполнен до завершения owner wrapper и отказал; verify-result.json сохранён. После фактического exit1 отдельный одноразовый readonly/network-none/logging-none контейнер с единственным mount нового output подтвердил directory_empty=true, envelope_exists=false; failed-wrap-output-check.json. Download и локальная расшифровка не запускались, повтор wrap не выполнялся. В server_step.py и download_envelope.py добавлен gate owner-wrap-result exit0, отдельный путь verify-after-owner-result.json для будущего чтения; исходные версии сохранены в before-owner-completion-gate/. Проверка Python AST успешна; это не новый серверный wrap и не установка компонентов.

Изменены те же пять документов: CHANGELOG.md, SYSTEM_PLAN.md, SYSTEM_SECURITY_CHECKS.json, docs/E2-06_KEY_HANDOFF.md, docs/E2-06_SESSIONS_MFA.md. Их промежуточные исходные копии — .change-backups/2026-10-02/E2-06-key-handoff-k1-k2/before-owner-attempt-result/<тот же относительный путь>. Новые локальные evidence в том же корне: owner-wrap-result.json, verify-result.json, failed-wrap-output-check.json, before-owner-completion-gate/server_step.py, before-owner-completion-gate/download_envelope.py. Старые protocol files не перезаписаны. SYSTEM_PLAN сохранён «На проверке»; R2 PASS не меняется, K1 attempted/failed, K2/K3 не выполнены. Требуется только уточнение владельца по терминалу; согласование K1/K2 сохраняется.

Откат/продолжение: сохранить пустой новый output и evidence, существующие key/S2 envelope/passphrase не трогать. Launcher блокирует повтор по owner-wrap-result.json; не удалять маркер и не перезапускать вслепую. После определения причины и новой проверки пустого output подготовить ограниченное продолжение в пределах разрешённого K1/K2, не заявляя успешный wrap заранее. Локальные документы отменять обратным diff после сравнения с backups, сохраняя посторонние изменения; журнал дополнять. Новые локальные evidence удалять только после сохранения доказательств и отсутствия потребителей, отдельным решением; никаких server runtime/SQL откатов не требуется. Значений секретов и key fingerprints в файлах/выводе/Git нет.


## 2026-10-02T16:13:47+03:00 — Получена и проверена зашифрованная копия ключа E2-06 K1/K2

После проблемы вставки Олег повторно запустил первый launcher и получил ожидаемый запрет по сохранённому маркеру. Перед отдельной второй попыткой fresh read-only preflight подтвердил пустой output, отсутствие активного writer и неизменность beta/старых ключевых metadata; подготовлен отдельный owner-key-handoff-retry.ps1 без стирания первого отказа. Вторая попытка остановлена владельцем Ctrl+C, exit130. Затем он явно разрешил автоматическое чтение пароля из уже существующего закрытого файла. Этот новый способ был объяснён заранее; прежний ручной getpass не выдаётся за успешный. Автоматический precheck подтвердил 0 активных output writers.

Первый автоматический запуск остановился на local-preconditions до чтения пароля/SSH: в дочернем Windows PowerShell5 отсутствовал Get-Acl. Диагностика выводила только безопасные признаки ACL, имя cmdlet и тип исключения. Права владельца/SYSTEM подтверждены отдельно. После перевода локального вызова на уже установленный PowerShell7.6.5 ACL PASS; новых компонентов и системной смены ExecutionPolicy нет. Исходные скрипты и automatic-result FAIL сохранены. Published локальный backup/verifier побайтово совпал с2c2f8f7.

Фактически выполнено K1/K2: существующий password-файл прочитан только приватным автоматическим процессом в память; передача серверному одноразовому контейнеру только SSH stdin, без argv/ENV/echo/логов/печати. Использованы неизменённые wrap/write_private_new из published RO source2c2f8f7, существующий pinned dependency image, network none/logging none/readonly/UID10001/cap-drop ALL/256MiB/0.25CPU; mounts только source RO, основной key RO, новый output RW. Создан новый `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-owner-key-envelope-20261002/envelope.json`,0600/UID10001,O_EXCL. Ciphertext получен приватным pipe в новый `C:/Users/krolo/Documents/marketplace-recovery/beta/e2-06-key-envelope-20261002.json` вне Git; эксклюзивная запись, ACL владельца/SYSTEM, regular/size/format/mode, read-back и повторное байтовое равенство серверу PASS. С тем же паролем из файла опубликованный verifier расшифровал копию в памяти и проверил Fernet key. Plaintext key на диск не писался/с сервера не скачивался; значения/ciphertext/fingerprints в протокол не попадали.

Итог automatic-after-acl-result.json: PASS, wrap/download/decrypt=true. Password-файл не изменился и теперь используется новым envelope; это уже не неиспользуемый подготовленный пароль. Метаданные основной beta и обоих остановленных rehearsal до/после равны; old runtime key/S2 envelope/passphrase mode/UID/size/mtime/inode прежние, старые копии сохранены. Web/PG/SQL/роли/миграции/сессии не менялись, новые runtime key/owner emergency proof не создавались. Одноразовые контейнеры завершены с --rm. Source сервера оставался published Git release, manual patches/archives не применялись. Telegram агентом не использовался; K3 и рабочий экспорт остаются незакрытыми, E2-06 «На проверке».

Точные изменённые документы: CHANGELOG.md, SYSTEM_PLAN.md, SYSTEM_SECURITY_CHECKS.json, docs/E2-06_KEY_HANDOFF.md, docs/E2-06_SESSIONS_MFA.md. Их промежуточные копии перед этим дополнением: .change-backups/2026-10-02/E2-06-key-handoff-k1-k2/before-completion/<тот же относительный путь>; исходные до всей работы — before/, hashes в backup-manifest.json. Новые локальные служебные файлы/evidence (включая копии исправляемых вспомогательных скриптов) перечислены относительно этого каталога: automatic-after-acl-result.json, automatic-precheck.json, automatic-result.json, auto_common.json, backup-manifest.json, check_owner_argv.ps1, check_owner_argv.py, download_envelope.py, failed-wrap-output-check.json, handoff_from_private_file.py, journal-before.md, journal-entry.md, local-checks.json, owner-key-handoff-retry.ps1, owner-key-handoff.ps1, owner-wrap-result.json, owner-wrap-retry-result.json, owner_wrap_console.py, prepare-result.json, retry-preflight-result.json, retry_preflight.py, server_step.py, verify-result.json, before-completion/CHANGELOG.md, before-completion/SYSTEM_PLAN.md, before-completion/SYSTEM_SECURITY_CHECKS.json, before-existing-powershell/download_envelope.py, before-existing-powershell/handoff_from_private_file.py, before-owner-attempt-result/CHANGELOG.md, before-owner-attempt-result/SYSTEM_PLAN.md, before-owner-attempt-result/SYSTEM_SECURITY_CHECKS.json, before-owner-completion-gate/download_envelope.py, before-owner-completion-gate/server_step.py, before-owner-retry/download_envelope.py, before-owner-retry/server_step.py, before-terminal-compatibility/owner-key-handoff.ps1, before-terminal-policy/CHANGELOG.md, before-terminal-policy/docs/E2-06_KEY_HANDOFF.md, before-owner-attempt-result/docs/E2-06_KEY_HANDOFF.md, before-owner-attempt-result/docs/E2-06_SESSIONS_MFA.md, before-completion/docs/E2-06_KEY_HANDOFF.md, before-completion/docs/E2-06_SESSIONS_MFA.md. Дополнительно создаётся completion-checks.json с итоговыми JSON/AST/hash/read-back/101-row/append-only/diff checks. Никакие эти локальные артефакты или приватные envelope/password не коммитятся. В Git только пять документов, автор/коммитер Oleg; push выполняет Олег.

Проверки: фактические K1/K2 PASS выше; неизменность данных парольного файла и защищаемых metadata; syntax PowerShell/Python, byte equality published verifier, JSON/read-back, исходные backup hashes, 101 строка/критерии плана неизменны, журнал append-only, git diff --check. Код приложения не менялся, повтор Django/MFA suite не требуется. Первый отказ, преждевременный metadata verify и остановленная попытка сохранены отдельно и не объявляются PASS.

Безопасный откат: runtime неизменен, серверный откат не нужен. Сохранить новый server/local envelope, используемый password и старые S2 копии; не повторять wrap/launcher на занятых путях, не регенерировать key/пароль и не перезаписывать ciphertext. Удаление копий только по отдельному решению владельца после проверки восстановимости/точных путей, без рекурсивного удаления общей папки. Для документов сравнить с backups и применить только обратный diff, сохранив позднюю/постороннюю работу; журнал не стирать. Служебные артефакты удалять после завершения процессов и сохранения нужного доказательства. Нет изменений production/main/Caddy/FBS/WB/Finkos/следующих задач и нет секретов в Git/выводе.


## 2026-10-02T16:22:32+03:00 — Зафиксировано подтверждение скачивания копий и отменена дополнительная проверка K3

Олег сообщил «все скачал все норм», затем на уточнение путей прямо указал «не надо проверять». Дополнительные проверки прекращены. До указания выполнен только поиск имён в согласованной закрытой папке и Downloads; sandbox отказал в перечислении закрытой папки, разрешённое чтение только имён/metadata прошло. Обнаружены прежние два имени в marketplace-recovery/beta; возвращённые копии не идентифицированы. Содержимое любых key/password/envelope в этом шаге не читалось, сравнение/расшифрование/изменение ACL/файлов не выполнялись. Сервер/SSH/Telegram не использовались, прошлые probes не повторялись.

Точные изменённые файлы: CHANGELOG.md, SYSTEM_PLAN.md, SYSTEM_SECURITY_CHECKS.json, docs/E2-06_KEY_HANDOFF.md, docs/E2-06_SESSIONS_MFA.md. Исходные копии `.change-backups/2026-10-02/E2-06-key-handoff-k3/before/<тот же относительный путь>`, hashes в backup-manifest.json; журнал непосредственно перед дополнением — journal-before.md. Новые локальные артефакты в этом каталоге: backup-manifest.json, owner-report.json, journal-before.md, journal-entry.md, local-checks.json; только безопасные сведения о результате/ограничении, без секретов/ciphertext/fingerprints. В Git не включаются.

K3 отмечен как owner-reported download, повторная техническая проверка отменена владельцем. Не выдаётся за новый технический PASS; K1/K2 и R2 PASS сохраняются как прежние доказательства. Повторно запрашивать пути/читать копии без нового указания Олега не планируется. E2-06 оставлен «На проверке»: полный критерий рабочего экспорта зависит от E2-07/E2-08/E5-07, синтетический действующий механизм и S1 не подменяют рабочий экспорт. Реальный owner proof не создавался, синтетическая процедура проверена ранее; соседние задачи не начаты.

Проверки только документов: JSON/read-back, исходные backup hashes, 101 неизменная строка/критерии плана, append-only журнала и diff --check. Новых MFA/SQL/browser/crypto тестов нет и PASS не приписывается. Локальный коммит автора/коммитера Oleg, push выполняет Олег. Основная beta/production/main/Caddy/FBS/WB/Finkos и другие проекты не менялись.

Безопасный откат: ключевые файлы и runtime не менялись, откат для них не нужен. Для документов сначала сравнить текущие файлы и backups, затем отменить только этот diff, сохранив позднюю/постороннюю работу; журнал дополнить, не стирать. Новые локальные evidence удалять только после сохранения нужного доказательства и проверки отсутствия потребителей. Отказ владельца от дополнительной проверки сохранять как действующее указание, пока он сам его не изменит. Не удалять/перезаписывать/перегенерировать ключевые файлы, не reset --hard/clean.


## 2026-10-05T11:26:24+03:00 (Europe/Moscow) — Спроектирована системная роль технического администратора

По запросу Олега продумано расширение модели доступа: `platform_admin` отделён от владельца организации и предусматривает обслуживание всех организаций, системную диагностику, логи/аудит, управление доступами, загрузками, интеграциями и состоянием резервирования. Описаны отдельный личный служебный аккаунт, серверные права и RLS без обхода, временная область поддержки, отзыв сессий/ссылок, MFA для чувствительных действий, точная область блокировки, защита последнего администратора/владельца и независимое операторское восстановление. Сроки административной сессии и поддержки записаны как предварительные параметры. Конкретные люди, постоянный финансовый доступ и право назначения остаются D3; роль/панель не реализованы, реальные доступы не выданы.

Изменены только `C:/Users/krolo/Documents/marketplace-workspace/SYSTEM_ARCHITECTURE.md` (модель назначения и раздел 4.1, уточнение административной проверки области), `C:/Users/krolo/Documents/marketplace-workspace/SYSTEM_PLAN.md` (связь предложения с будущими задачами и состав D3) и `C:/Users/krolo/Documents/marketplace-workspace/CHANGELOG.md` (эта добавленная запись). Статусы, зависимости и исходные критерии всех 101 задачи сохранены; D3 остаётся «Не принято». Код, UI, зависимости и сервер не менялись; commit/push не выполнялись.

До редактирования сохранены побайтовые копии с проверенными SHA256: `.change-backups/2026-10-05/platform-admin-design-112054/SYSTEM_ARCHITECTURE.md`, `.change-backups/2026-10-05/platform-admin-design-112054/SYSTEM_PLAN.md`, `.change-backups/2026-10-05/platform-admin-design-112054/CHANGELOG.md`. Новые локальные файлы дополнительно: `.change-backups/2026-10-05/platform-admin-design-112054/backup-manifest.json` и `.change-backups/2026-10-05/platform-admin-design-112054/documentation-checks.json`. Все пять путей находятся внутри `C:/Users/krolo/Documents/marketplace-workspace/`; каталог исключён из Git действующим `.gitignore`.

Проверка документов: сверены актуальные User/Membership и проверка владельца; проверены исходные backup SHA256, read-back добавленного раздела и ссылки на него, структура Markdown-таблиц, побайтовое сохранение всех 101 строки задач и исходных CRLF, неизменный статус D3, append-only журнала и `git diff --check`. Итоговый протокол — `documentation-checks.json`. Runtime/MFA/RBAC/RLS/UI-проверки нового администратора не выполнялись: изменены только документы.

Безопасный откат: сначала сравнить текущие документы с указанными копиями, затем убрать только добавленную модель/раздел 4.1, уточнение проверки административной области, заметку плана и дополнение формулировки D3, сохранив любые поздние/посторонние изменения. CHANGELOG не перезаписывать: добавить запись об откате. Пять новых локальных файлов можно удалить только после проверки точных путей, отсутствия потребителей и сохранения нужного доказательства/возможности отката; не удалять общий каталог `.change-backups/`, не применять reset --hard/clean. Серверный откат не требуется.


## 2026-10-05T12:29:58+03:00 (Europe/Moscow) — Реализованы локальные разрешения E2-07 и ограниченный системный администратор

По согласованной матрице добавлены Grant, серверные потребители приглашений/синтетических данных, четыре независимых действия, организационные и кабинетные области, отзыв без восстановления старой ссылки, шаблоны и ограничения выдачи, обязательный MFA при повышении, platform_admin с отдельным назначением и временной поддержкой. Подготовлены PostgreSQL guards, минимальный SQL-контракт web, отдельный серверный план и инертные средства нового синтетического стенда. Новых зависимостей/плагинов нет. Сервер/основная beta/production/main/Caddy/FBS/WB/Finkos не менялись, push не выполнялся, реальные ключи/пароли и K3 не открывались.

Точные файлы относительно C:/Users/krolo/Documents/marketplace-workspace/:

- `CHANGELOG.md`
- `SYSTEM_GRANT_CHECKS.json`
- `SYSTEM_PLAN.md`
- `backend/access_control/__init__.py`
- `backend/access_control/apps.py`
- `backend/access_control/management/__init__.py`
- `backend/access_control/management/commands/__init__.py`
- `backend/access_control/management/commands/manage_access_operator.py`
- `backend/access_control/migration_guards.py`
- `backend/access_control/migrations/0001_initial.py`
- `backend/access_control/migrations/0002_access_guards.py`
- `backend/access_control/migrations/__init__.py`
- `backend/access_control/models.py`
- `backend/access_control/operator.py`
- `backend/access_control/services.py`
- `backend/access_control/tests/__init__.py`
- `backend/access_control/tests/test_http.py`
- `backend/access_control/tests/test_migrations.py`
- `backend/access_control/tests/test_platform.py`
- `backend/access_control/tests/test_preparation.py`
- `backend/access_control/tests/test_role_contract.py`
- `backend/access_control/tests/test_transactions.py`
- `backend/access_control/urls.py`
- `backend/access_control/views.py`
- `backend/account_security/management/commands/prepare_owner_recovery.py`
- `backend/account_security/services.py`
- `backend/account_security/tests/test_http.py`
- `backend/accounts/services.py`
- `backend/config/access_local_checks.py`
- `backend/config/settings.py`
- `backend/config/urls.py`
- `backend/tools/access_rehearsal.py`
- `backend/tools/access_restore_check.py`
- `backend/tools/access_web_grants.py`
- `backend/tools/verify_access_web_runtime.py`
- `beta/deploy/compose.access-rehearsal.json`
- `beta/deploy/prepare_access_rehearsal.py`
- `docs/E2-07_GRANTS.md`
- `docs/E2-07_SERVER_PLAN.md`

Проверки: основной E2-07/E2-06 HTTP-набор 68 обнаружено, 63 PASS, 5 PostgreSQL-пропусков; ещё четыре новые HTTP/подготовительные проверки PASS. E2-04/E2-05 legacy: 58 обнаружено, 47 PASS, 11 PostgreSQL-пропусков. Полный локальный E2-06 набор: 53 обнаружено, 44 PASS, 6 пропусков, три ошибки недоступного Windows TEMP; эти три синтетических файловых теста успешно повторены с TEMP внутри проекта (вместе с новым recovery-тестом: 4 PASS). Исходные ошибки не скрыты; это не K3 и не работа с реальными ключами. Django check, migration drift, pip check, AST 26 файлов, безопасные dry-plan/Windows refusal и diff --check успешны. Два shell-блока серверного плана прошли bash -n без исполнения команд; запуск Git Bash для синтаксической проверки потребовал локального выхода из sandbox. Протокол SYSTEM_GRANT_CHECKS.json содержит команды/ограничения. PostgreSQL/реальный SQL LOGIN/сетевой web/новый dump-restore не выполнены; E2-07 «На проверке», E2-06 статус не закрыт.

Исходные копии существующих файлов до редактирования — `.change-backups/E2-07-20261005-115038/` с теми же относительными путями; manifest.json содержит исходные SHA256, preexisting.patch сохраняет прежний diff трёх документов. Дополнительно локальные e207-files.json, plan-addition.txt, changelog-addition.txt, SYSTEM_PLAN.md.index, CHANGELOG.md.index и пустой после тестов test-temp/ находятся в этой исключённой из Git папке. SYSTEM_ARCHITECTURE.md не редактировался; прежние правки SYSTEM_PLAN/CHANGELOG сохранены и не включаются в коммит E2-07. Автор/коммитер локального коммита — Oleg, без Co-Authored-By.

Откат: сначала сравнить текущие файлы с копиями и поздними изменениями, затем применить только обратный diff E2-07. Новые файлы перечислены выше и в e207-files.json; удалять только если после этой работы не появились потребители/чужие изменения, сверив каждый точный путь. CHANGELOG дополнять, историю не стирать; reset --hard/clean не применять. Серверного отката сейчас нет. Будущий стенд при отказе только остановить, сохранить новые volume/БД/секреты/dump; не down -v/DROP/prune и не restore поверх живой БД. После внедрения нельзя возвращать обычный E2-06 код, обходящий Grant: нужен закрытый maintenance/отдельный план.


## 2026-10-05T12:48:49+03:00 (Europe/Moscow) — Подготовлено коммитирование проекта системной роли

По текущему запросу Олега «сделай коммит» к локальному коммиту в ветке `beta` подготовлены только `SYSTEM_ARCHITECTURE.md`, `SYSTEM_PLAN.md` и `CHANGELOG.md`. Планируемое сообщение: «Проектирование системной роли технического администратора»; автор и коммитер Oleg, `oleg@localhost`, задаются только для команды без изменения глобальной конфигурации Git. Push не входит в запрос.

Перед коммитом найдена уже сохранённая в `10c2af0` последующая локальная реализация ограниченного `platform_admin`. Уточнены только три устаревшие фразы нашего проектного описания: отделены целевая полная панель/логи от уже реализованных назначения, технического обзора, административной сессии и поддержки на чтение. E2-07 сохраняет «На проверке»; его код, критерии, статус и чужие записи журнала не изменяются. Историческая запись проектирования от 11:26 сохранена.

Побайтовые копии перед уточнением: `.change-backups/2026-10-05/platform-admin-commit-124849/SYSTEM_ARCHITECTURE.md`, `.change-backups/2026-10-05/platform-admin-commit-124849/SYSTEM_PLAN.md`, `.change-backups/2026-10-05/platform-admin-commit-124849/CHANGELOG.md`; SHA256 — `.change-backups/2026-10-05/platform-admin-commit-124849/backup-manifest.json`. Это четыре новых локальных файла внутри `C:/Users/krolo/Documents/marketplace-workspace/`, исключённые из Git. Проверки: Git diff/status, сравнение с текущим HEAD, 101 неизменная строка задач, исходные backup hashes, журнал дополняется, `git diff --check`; после коммита проверяются состав файлов, авторство и чистота рабочей копии. Runtime-тесты не повторяются для изменений только документов.

Безопасный откат: сначала сравнить актуальные документы с указанными копиями и отменить только уточнение статуса/проектный diff, сохранив последующие и чужие изменения. Журнал дополнять записью, не стирать. При необходимости отмены коммита сначала проверить его состав и поздние коммиты, затем применить обратное изменение только этих документов; без reset --hard/clean. Четыре локальных файла можно удалить после проверки точных путей и сохранения нужных доказательств/возможности отката; общий `.change-backups/` не удалять. Серверный откат не нужен.
