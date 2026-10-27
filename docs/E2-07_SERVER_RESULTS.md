# E2-07 — результаты отдельного серверного стенда

05.10.2026, Europe/Moscow. Проверен опубликованный `3369e3196753804655a7ae0cc9a845395545036e`, включающий реализацию `10c2af059abd2dedd17785c44c67dfb143e085ed`. Олег выполнил push; опубликованная beta проверена напрямую через `git ls-remote --heads origin beta`, затем получено отдельное разрешение на серверный план. Статус E2-07 — **На проверке**: изолированный стенд проверен, основная beta ещё не обновлена.

## Область и исходники

- Project: `marketplace-e207-20261005-01a10b2d`.
- Корень: `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-07-20261005-01a10b2d`.
- Release: `/home/adm_user/marketplace-workspace/beta/app/releases/3369e3196753804655a7ae0cc9a845395545036e`.
- Источник получен только через Git: чистый серверный repository fast-forward с `2c2f8f737262267d29d06ab40d7bef3571693745`, новый detached worktree. Перед завершением release чистый; ручных изменений/загрузки исходников не было.
- PostgreSQL 17.11 (Debian 17.11-1.pgdg12+2), закреплённый существующий образ; установки, pull/build образов не выполнялись.
- Новые БД `mw_beta`, `test_mw_beta`, `mw_e207_01a10b2d_restore` существуют только внутри нового изолированного кластера. Все прежние БД/роли/restore сохранены.
- Внешних портов/доставки нет, сеть internal. Только синтетические аккаунты/example.invalid, locmem, новые синтетические секреты. Реальные ключи/пароли и K3 не читались и не передавались.

## Проверки

| Проверка | Факт |
| --- | --- |
| Preflight | Опубликованный SHA, чистота Git, requirements.lock, закреплённые образы, свободные имена, минимум 2 GiB памяти/диска — PASS |
| Миграции и ACL | Применены в новой пустой БД; точный поколоночный SQL-контракт web и запрет наследования/DDL проверены |
| PostgreSQL suite | 72 теста, 70 PASS, 2 ошибки статических файловых тестов, 0 пропусков, 0 assertion failures; 703.878 s, exit 1 |
| Пять гонок | Все PASS: взаимное приостановление владельцев; выдача против приостановления выдающего; конкурентный отзыв последнего владельца; скачивание против отзыва; два операторских отзыва администраторов |
| Миграционный откат | PASS: `0002 → 0001 → 0002` сохраняет отозванные Grant; `zero` только на пустой access-схеме сохраняет ownership |
| Два статических теста отдельно | PASS, 0.012 s, exit 0; тот же release read-only, без сети/секретов/БД |
| Реальный SQL LOGIN | `session_user=current_user=mw_beta_web`, HTTP через Django client — PASS |
| Синтетическая ссылка | Выдана, использована, отозвана вместе с Grant; повторная выдача права не оживила старую ссылку — PASS |
| Поддержка администратора | Явный операторский Grant, окно поддержки, запрет прямого export, закрытие окна закрывает чтение — PASS |
| Operator CLI | Настоящие guarded `assign-platform` и `grant-platform` под migrator — PASS |
| Отрицательный SQL | 10 команд сценария и 2 дополнительных platform-subject пробы отклонены, SQLSTATE `42501` |
| Сетевой Gunicorn | Дважды PASS: live/ready, anonymous session 401, GET login 405, MFA login page 200, точные SQL ACL/guards |
| Backup/restore | Новый custom dump, restore в отдельную новую БД с exit 0; сравнение всех public-строк в памяти — PASS |
| После restore | Снять отзыв Grant нельзя; восстановленные сессии/ссылки переведены в карантин E2-06 — PASS |
| Изоляция | Сверены source RO mount, SQL-secret mounts, UID, read-only rootfs, сеть и отсутствие портов; metadata основной beta и двух старых owner rehearsal неизменны |

В PostgreSQL suite вошли реальные middleware/CSRF, default deny и независимость действий, две организации/несколько кабинетов/двойное членство, подмена ID, шаблоны и будущие кабинеты, живые сессии после отзыва/изменения, блокировка/архив, MFA владельца и смена роли, ограничения platform_admin. Это новые результаты E2-07, не перенос старых результатов E2-06.

### Первоначальные ошибки и отдельный повтор

Полная команда в controller: `python manage.py test access_control.tests account_security.tests.test_http --keepdb --noinput --verbosity=1` с `config.settings` и настоящим PostgreSQL. `test_preparation` ожидает полное дерево репозитория, тогда как штатный `/workspace` содержит только backend. Два `FileNotFoundError` относятся к `/beta/deploy/compose.access-rehearsal.json` и `/beta/deploy/prepare_access_rehearsal.py`; это не пропуски и не PASS. Новый PostgreSQL был остановлен после отказа; исходная тестовая БД сохранена.

Точный отдельный повтор двух проверок структуры:

```sh
release=/home/adm_user/marketplace-workspace/beta/app/releases/3369e3196753804655a7ae0cc9a845395545036e
docker run --rm --pull never --network none --read-only --user 10001:10001 \
  --memory 256m --cpus 0.25 --pids-limit 96 --log-driver none \
  --cap-drop ALL --security-opt no-new-privileges:true \
  --mount "type=bind,src=$release,dst=/source,readonly" --workdir /source/backend \
  --env PYTHONDONTWRITEBYTECODE=1 \
  sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72 \
  python manage.py test access_control.tests.test_preparation \
  --settings=config.access_local_checks --verbosity=1 </dev/null
```

Это статический PASS, не PostgreSQL-проверка. Перед успешной командой попытка `python -m unittest ...` отказала до тестов: offline settings допускают только штатные команды Django test/check. Защита не отключалась. Полного повторного прогона 72 тестов не было, первоначальный exit 1 сохраняется в отчёте.

Технические поправки запуска: фактическое имя основного web — `marketplace-beta-web-1`; первое обращение без суффикса вернуло «no such object», после чего проверен правильный контейнер. Передача PowerShell-скрипта через SSH потребовала удаления CR на входе bash; незавершённый `if` не создал release. Контейнерный stdin затем явно отделён от SSH через `</dev/null`: первоначальный bootstrap потребил остаток входа, `configure` был запущен отдельно и впервые. Повторного bootstrap/provisioning не было.

Два предупреждения Django сохранены как ограничения: запрос идентичности кластера в `AppConfig.ready()`; fallback инициализации test DB через новую изолированную `mw_beta`, поскольку migrator не имеет CONNECT к служебной `postgres`. Привилегии для подавления предупреждений не расширялись.

### SQL и нагрузка

Сценарий отклонил: CREATE TABLE, CREATE TEMP TABLE, UPDATE активности User, UPDATE области Membership, UPDATE действия Grant, UPDATE PlatformRoleAssignment, DELETE Grant, TRUNCATE, UPDATE django_migrations, SET ROLE migrator. Дополнительно под настоящим web LOGIN проверены INSERT Grant с platform subject и UPDATE его revoked_at. Дополнительные пробы выполнялись прямыми диагностическими SQL-командами внутри транзакций с обязательным rollback даже при неожиданном успехе; файлов исходников/SQL-полномочий не меняли. Оба отказа — `42501`, данные не изменились.

Лимиты не менялись: PostgreSQL/web по 384 MiB, controller 256 MiB, по 0.25 CPU. Замер во время suite: PostgreSQL 65.55 MiB, controller 70.62 MiB; CPU controller 25.58%. Все контейнеры завершены без OOM. Медленный прогон связан с обычными хешерами паролей/MFA и ограничением CPU; тестовые упрощения runtime не применялись.

## Сохранённые ресурсы и завершение

Dump: `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-07-20261005-01a10b2d/backups/access-after.dump`.
SHA256: `0410d3a91c47d559491a6483e7c2628ae825c7da284e0327941a7e0b00d7fc16`.
Исходная БД не заменялась восстановленной. Секреты и строки БД в отчёт не копировались.

| Ресурс | ID/имя |
| --- | --- |
| postgres | `05bb79ce05c893d41719493eb83e5c61b58df80ccf8cd3acc887e587666929b3` |
| web | `cefb655163f711ef12326d3d5af6e54fd01cdf1c083fab3c1c3cf195592ca5fc` |
| controller | `059c33fc04e8800c1af39fafe9d760687dffc366bbc98a09eaa8d9f0025ac742` |
| internal network | `390ab14bb1a57c718096c8ce4d377988581f5cc767731c542a29b9e28b3145f8` |
| volume | `marketplace-e207-20261005-01a10b2d-data`, создан 2026-10-05T10:01:52Z |

Финальная проверка 2026-10-05T10:24:29+00:00: все новые процессы остановлены. PostgreSQL/web exit 0; ожидающий controller завершён Compose с exit 137, `OOMKilled=false`. Это остановка `time.sleep`, не код выхода suite. Контейнеры, volume, network, все три новые БД, dump, новые синтетические секреты и metadata сохранены. Повторное использование занятых имён/provisioning без проверки состояния запрещено.

Основной web продолжает использовать `/home/adm_user/marketplace-workspace/beta/app/releases/14d9f48cee6eb2a9d7eca9f029770af51c45b6d9/backend`, RW=false. Контейнеры основной beta и оба старых owner rehearsal сохранили ID, образы, время старта, mounts, сети и порты. E2-06 остаётся «На проверке», K3 не возобновлялся.

## Ограничения и следующий допуск

Аутентифицированные запросы проверены через Django HTTP client с настоящей ограниченной SQL-ролью. Сетевые проверки — Gunicorn health/auth без входа; браузер/TLS в этом прогоне не проверялись. Рабочего экспорта, RLS E2-08, финансовой фильтрации E2-09, UI/worker/интеграций, окончательной D3 и полной панели администратора нет.

Для внедрения E2-07 в основную beta нужен новый конкретный план: актуальный опубликованный SHA, backup/ACL/maintenance, bootstrap существующих владельцев с MFA, штатный security overlay, проверки под web LOGIN и безопасный отказ без возврата к role-only проверкам E2-06. Исполнение — только по отдельному разрешению. Очистка сохранённого стенда также требует отдельного разрешения и точного перечня ресурсов; `down -v`, DROP и prune не выполнялись.

Откат этой документальной фиксации: сравнить текущие файлы с `.change-backups/E2-07-server-20261005-130657/`, отменить только её diff, сохранив позднюю работу; CHANGELOG дополнить. Новый этот файл удалять только при отсутствии поздних изменений/потребителей и после сохранения доказательств. Серверный безопасный отказ уже выполнен остановкой только новых сервисов; ресурсы не удалять и живую БД не восстанавливать поверх.
