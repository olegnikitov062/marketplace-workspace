# E2-08 — локальная изоляция и граница доверия

06.10.2026, Europe/Moscow. **На проверке. PostgreSQL, реальный web LOGIN,
серверный HTTP и backup/restore этой реализации ещё не выполнены.**
E2-06 остаётся «На проверке», E2-07 — «Готово» в своём прежнем объёме.

Исходная чистая локальная beta и live `git ls-remote --heads origin beta`:
`1b765629badd6fe70f605fd9f6d504954e44d618`. Первая попытка из sandbox
получила DNS-отказ; повторная разрешённая read-only проверка GitHub успешна.
Последний подтверждённый runtime из задания и документов —
`cf6f4ccd48106d9a44a64703bcfd79e49513ec3e`; сервер сейчас не опрашивался.
Публикация документации не означает смену runtime.

## Ограниченный объём

Существующие Django HTTP-потребители аккаунтов, MFA, Grant, поддержки,
синтетической записи и синтетического CSV; обязательная PostgreSQL-граница;
узкий синтетический список/поиск по UUID внутри одного кабинета. SQL-контракт
E2-07 сохраняется, добавляются только закрытая схема проверки capability и
EXECUTE трёх конкретных функций. Новых библиотек и расширений PostgreSQL нет.

Брендовая область не добавляется. Финансовые поля/агрегаты — E2-09, рабочий
экспорт — E5-07, реальные сотрудники/D3 — E6-03. UI, worker, интеграции,
production и другие проекты не входят в изменение. K3 отменена и не повторяется.
Новых бизнес-решений для этого ограниченного объёма не требуется.

## Карта моделей и таблиц

Инвентаризация сделана по актуальным моделям и `apps.get_models`, включая
автоматическую таблицу Group.permissions. Это карта исходников, не новый снимок БД.

| Область | Модели / SQL-таблицы | Действующий потребитель и предлагаемая защита |
| --- | --- | --- |
| Общая техническая | `django_migrations` | Readiness и оператор; web только SELECT, без бизнес-строк; без RLS |
| Общая неиспользуемая | `django_content_type`, `auth_permission`, `auth_group`, `auth_group_permissions` | Нет пользовательского PermissionsMixin/потребителей; web ACL не выдаются |
| Неиспользуемое хранение OTP библиотеки | `otp_totp_totpdevice`, `otp_static_staticdevice`, `otp_static_statictoken` | Собственный Authenticator вместо plaintext-хранилища; web ACL не выдаются |
| Общая техническая с чувствительными селекторами | `accounts_attemptbucket`, `accounts_authdenial` | Ограничение попыток/категории отказа; подписанный точный SQL, существующие column ACL; не tenant-кэш |
| Персональная | `ownership_user`, `accounts_accountcontact` | Вход, приглашение, восстановление; подписанный точный SQL текущего серверного потребителя |
| Персональная | `account_security_accountsecurity`, `account_security_loginchallenge`, `account_security_authenticator`, `account_security_trusteddevice`, `account_security_accountsession`, `account_security_recoverycode`, `account_security_recoverypermit`, `account_security_securityevent` | E2-06, тот же барьер точного SQL; web не получает INSERT RecoveryPermit; существующая проверка текущей личности/сессии сохраняется |
| Персональная/до входа | `django_session` | Зашифрованный payload мастера и сессий; подписанный SQL до AuthenticationMiddleware и при сохранении ответа |
| Организационная | `ownership_organization`, `ownership_membership` | Авторизация, MFA владельца, приглашения, список членств; signed SQL + URL organization; собственные членства доступны проверке обязательности MFA до/независимо от выбора организации |
| Организационная | `ownership_legalentity`, `ownership_brand` | HTTP/Grant-потребителей нет; RLS default deny для web плюс отсутствие ACL. Операторские модели/история сохранены |
| Кабинетная | `ownership_cabinet` | Разрешение области SyntheticRecord/Grant; signed SQL + organization; кабинетная авторизация данных отдельна |
| Кабинетная | `ownership_sourceconnection`, `ownership_cabinetlegalentity` | Нет HTTP, worker или реального чтения secret_reference; default deny web + отсутствие ACL; `observe_legal_entity` остаётся доверенной операторской функцией |
| Организационная через FK | `accounts_invitation` | Приглашение/reinvite/revoke/accept; organization выводится из Membership, сохраняется scope_digest и одноразовость |
| Организационная/кабинетная | `access_control_grant` | Разрешение resource/action/scope; signed SQL + organization; свежие права и делегирование проверяются существующими сервисами, не копируются в cookie |
| Кабинетная | `access_control_syntheticrecord` | Подписанный SQL **и** независимый RLS-предикат живой сессии, организации, кабинета, действия, Grant/членства/поддержки |
| Персональная системная | `access_control_platformroleassignment` | Технический обзор и операторское назначение; только SELECT web, назначение не становится Membership |
| Системная + организационная через Grant | `access_control_supportwindow` | Открытие/закрытие окна по текущей сессии; signed SQL + organization; чтение SyntheticRecord независимо проверяет живое окно в RLS |
| Персональная + организационная | `account_security_exportpermit` | Синтетическая ссылка, привязанная к сессии/организации; signed SQL + organization и существующие необратимые отзывы |
| Кабинетная через Record, организационная через Permit | `access_control_exportbinding` | Неизменяемая привязка к конкретному Grant и Record; signed SQL + organization; скачивание повторно проверяет исходный Grant |

RLS ENABLE + FORCE применяется к **27 таблицам** из `data_isolation.sql.TABLES`.
Четыре справочника без web-потребителей получают только операторскую policy.
Их отсутствие в READ_TABLES дополнительно закрывает даже SELECT.

## Карта операций и проверок

| Операция | Реальный путь | Область/действие и граница проверки |
| --- | --- | --- |
| Вход/сессия/MFA/recovery | `accounts`, `account_security`, SessionGate, encrypted SessionStore | Личность, version, блокировка, фактор, сроки и повторное подтверждение E2-05/06; подписанные точные ORM-запросы до выбора организации |
| Членства | GET organizations/org/memberships | `memberships/view`, организация из URL, живой Grant; безопасные id/role/state, без контактов |
| Приглашение/reinvite/revoke | `/auth/invitations…` | Действующий `memberships/manage_access`, владелец/ограниченный platform_admin, fresh MFA; исходная область из Membership/Invitation |
| Выдача/отзыв/шаблон/suspend | `/api/v1/access/organizations/org/…` | Существующие независимые действия и ограничения делегирования; self-elevation запрещена |
| Детализация/изменение | synthetic/record, change | Сначала Cabinet и authorize, затем record_scope и запрос; RLS дополнительно проверяет живую область/действие; UPDATE обязан затронуть одну строку |
| Список/поиск, новый стенд | cabinets/cab/synthetic/?record_id=UUID | Только `view`; максимум 100 строк; UUID-поиск в том же кабинете; чужой UUID даёт пустой список, неизвестный/повторный фильтр отвергается |
| Выдача ссылки/скачивание | synthetic/record/export; `/auth/security/probe/permit/` | Независимый `export`; Grant/Binding/Permit/session проверяются заново; сначала узкая SQL-проекция cabinet UUID, затем RLS-чтение Record |
| Поддержка/технический обзор | support/open/close; platform/status | Прежние операторское назначение, 30 минут, сессия 15 минут idle/4 часа, только view; обзор возвращает только org UUID/archive и count активных аккаунтов |
| Файлы | MFA QR и фиксированный синтетический CSV | QR остаётся персональным MFA-путём; CSV действительно обслуживается существующим HTTP-механизмом, но не является рабочим экспортом |
| Кэш | Предметного кэша нет | Нет Redis/queryset/result-cache consumer; ответы границы no-store/no-cache/private; проверяется повторный HTTP после отзыва, cache-hit не заявляется |
| Фоновые задания | Не реализованы | Нет worker/очереди/потребителей; контекст Python и параллельные SQL-соединения не выдаются за worker-проверку; критерий переносится на появление слоя |
| Интеграции/файловое хранилище | Не реализованы | Никаких фиктивных разрешений/адаптеров; остаются непокрытыми отсутствующие слои, не объявляются защищёнными helper-ом |

## Конкретная модель доверенного контекста

Обычный SET user_id/organization_id/action не доверен. Любая пользовательская
GUC изменяема web SQL-login, поэтому одна такая переменная не является доказательством.
В `mw_isolation` находится новый независимый 32-byte HMAC key. Его читает только
владелец схемы/фиксированные SECURITY DEFINER-функции; web не имеет SELECT,
записи, владения, CREATE или EXECUTE функции HMAC. Тот же ключ отдельно
монтируется RO доверенному Django-процессу. Это **не** Django SECRET_KEY и не ключ MFA.

`StatementSigner` внутри одного HTTP-запроса использует штатный ClientCursor
mogrify: значения параметров адаптируются один раз; подписывается и исполняется
одна и та же точная SQL-строка. Envelope содержит её SHA256, request nonce,
backend PID, transaction ID, database, session_user, срок 10 секунд и контекст.
Он передаётся параметризованным SET LOCAL. PostgreSQL сверяет подпись, текущий
SQL через current_query(), транзакцию/соединение/роль/БД и срок. Ни hash SQL,
ни envelope/подпись, ни параметры не выводятся.

Два уровня контекста:

1. **Control plane** — точный SQL существующих проверенных серверных auth/Grant
   потребителей. Это позволяет выполнить вход, SessionGate, MFA, recovery и
   определить собственные членства до выбора организации без общей `auth=true`
   политики. Изменённый/дополнительный SQL не совпадает с подписанным statement.
   После SessionGate ActorContext добавляет фактического пользователя/сессию и
   organization из разрешённого URL; организационные таблицы дополнительно
   ограничиваются этим organization. Query string область не задаёт.
2. **Record plane** — конкретные user/session/org/cabinet/resource/action после
   сервисного authorize. Помимо подписи SQL, RLS независимо читает текущие
   Membership, Grant, архивы, AccountSecurity/AccountSession, MFA/TrustedDevice,
   PlatformRoleAssignment/SupportWindow. Export/change допускают необходимое
   внутреннее SELECT, но не создают HTTP-права view; SQL UPDATE требует change.

**Явная граница:** доверенными остаются Python-код signer и существующие
серверные auth/управляющие сервисы. RLS control plane не является самостоятельной
реализацией проверки пароля/TOTP/делегирования в SQL. Доверенный Python с ключом
может подписать произвольный control-запрос; полный захват этого процесса/ключа
не покрывается. Поэтому нельзя добавлять endpoint произвольного SQL, подписания
capability или новый непроверенный control-consumer. Защита направлена на
подмену HTTP-области и использование SQL web-credential/подменённого контекста,
а не на заявление о защите от полного захвата приложения/оператора.

Все обращения к данным остаются параметризованными. Нельзя переносить
SQL-конкатенацию клиентского ввода перед signer и ожидать, что подпись исправит
SQL injection. Слой точного statement — существенное допущение этой реализации,
которое необходимо проверить на реальном psycopg/PostgreSQL, а не считать
доказанным по Python HMAC-тестам.

## Транзакции, отзыв и SQL-роли

IsolationBoundary установлен до SessionMiddleware, ActorContext — после
SessionGate. Одна atomic-транзакция охватывает чтение и сохранение Django session.
Каждый запрос получает новую подпись; кэш полномочий отсутствует. ContextVar
всегда reset в finally. SET LOCAL исчезает при commit/rollback; оставшийся или
восстановленный после savepoint envelope дополнительно не подходит другой
SQL-строке/транзакции. Фиксированные Django SAVEPOINT/ROLLBACK TO/RELEASE не
требуют подписи и не делают SELECT в уже aborted transaction. Streaming-ответ
запрещён: после выхода из транзакции данные не читаются. Ответы 5xx откатываются.

Сохраняется порядок E2-07 organization → users по UUID → связанные строки.
Grant/членство/поддержка повторно читаются; завершившийся до отзыва запрос
не отзывается ретроспективно. Новый запрос после committed revoke должен отказать.
Конкуренция PostgreSQL ещё не проверена этой реализацией.

Миграционная роль владеет объектами и имеет явную operator-policy; web не
владелец, не superuser/BYPASSRLS и не член migrator. Bootstrap/operator остаются
отдельными доверенными процедурами. `platform_admin` — пользователь приложения,
не SQL-владелец и не исключение из RLS.

11 существующих фиксированных trigger-only функций проверки последнего владельца,
блокировки org и каскадного отзыва переведены в SECURITY DEFINER с фиксированным
search_path и отозванным PUBLIC EXECUTE. Они должны видеть все строки инварианта,
в том числе на deferred COMMIT. `accounts_web_lock_only` и `access_web_subject`
**остаются SECURITY INVOKER**: их проверка фактического web-login сохраняется.
Произвольного SQL в этих trigger-функциях нет. Прямого SQL/HTTP API для вызова
каскада или изменения операторских назначений не добавлено.

## Миграция и отказ

`data_isolation.0001_statement_and_row_policies` создаёт закрытую схему,
пустую key-таблицу, функции и policies; не переписывает предметные строки,
Grant/Membership или истории. Ключ и EXECUTE provisioning — отдельный явный
операторский шаг. Без него web закрыт; startup требует отдельный RO key mount,
readiness проверяет валидную подпись и ENABLE/FORCE всех 27 таблиц.

Обратная миграция на заполненной области отказывается. Reverse/forward
предусмотрен только для пустого изолированного теста. Заполненные данные
восстанавливаются в **новую закрытую БД**, затем проверяются и карантинируются
сессии/ссылки; актуальные отзывы сверяются отдельно. После включения RLS безопасный
fallback — остановка web. Возврат обычного E2-07 runtime или отключение RLS ради
работоспособности запрещены. Штатный security overlay обязателен; старые
base-only/accounts overlay не становятся допустимыми.

## Доказательства и оставшееся

Команды/числа записаны в `SYSTEM_ISOLATION_CHECKS.json`. Первый локальный
HTTP/regression запуск: 91 тест, PASS, SQLite; последующие изменения контекста
проверяются отдельным итоговым прогоном. Это новый запуск, но большая часть
assertions — регрессия E2-05/06/07, а не самостоятельное доказательство RLS.

Подготовлены новый именованный rehearsal, настоящий web LOGIN HTTP/SQL probe,
отказы подделки/прямого доступа к key/DDL/SET ROLE, scoped SELECT/UPDATE без WHERE,
rollback/savepoint/reuse, два конкурентных соединения, SQL после отзыва Grant,
reverse/refusal/forward и restore/quarantine helper. **Ни один из этих
PostgreSQL-прогонов ещё не выполнен.** Старые E2-07 результаты к ним не относятся.
Browser/TLS-проверки, рабочие файлы, cache-hit и worker не заявляются.

До закрытия E2-08 нужны фактические PostgreSQL/limited-role результаты всех
подготовленных сценариев; отдельная проверка сохранения данных/SQL-политик при
restore; гонки отзыва, последнего владельца и архива; затем отдельный план и
разрешение основной beta. Отсутствующие слои остаются явными ограничениями.

Основание SQL-модели: [PostgreSQL 17 RLS](https://www.postgresql.org/docs/17/ddl-rowsecurity.html),
[SECURITY DEFINER](https://www.postgresql.org/docs/17/sql-createfunction.html),
[встроенные bytea/SHA256 функции](https://www.postgresql.org/docs/17/functions-binarystring.html).
FORCE, ограничения владельца и особые права TRUNCATE/REFERENCES учтены отдельно
от политики строк; существующий минимальный column ACL не заменён GRANT ALL.
