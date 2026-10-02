# E2-06: полный браузерный сценарий и операторское восстановление

02.10.2026, Europe/Moscow. **Подготовлено локально, серверный запуск ещё не разрешён и не выполнен.** Это дополнительный синтетический стенд после S2; работающий E2-06 web остаётся на 19a6d6a. Публикация e3e5383 проверена. Наличие скриптов не закрывает оставшиеся критерии.

Цель: пройти настоящие страницы в Chromium и настоящие `prepare_owner_recovery`/`issue_owner_recovery` с PostgreSQL LOGIN `mw_beta_migrator`. Проверка `require_operator_process` не меняется. Положительный сценарий нельзя проводить в старой test-БД с другим именем/ролью или считать выполненным через mock. Реального владельца, его proof и ключ основной beta этот стенд не использует.

## Точный объём отдельного разрешения

| Ресурс | Новое фиксированное имя / путь |
| --- | --- |
| Compose project | `marketplace-e206-owner-check` |
| Внутренняя сеть | `marketplace-e206-owner-check-private`, internal, без ingress |
| Контейнеры | `marketplace-e206-owner-check-postgres`, `marketplace-e206-owner-check-web`, `marketplace-e206-owner-check-controller`, `marketplace-e206-owner-check-issuer` |
| Volume PostgreSQL | `marketplace-e206-owner-check-data` |
| Каталог | `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-06-owner-20261002` |
| Подкаталоги | `secrets/`, `state/`, `operator-output/`, mode 0700; создать родительский `rehearsals/`, только если отсутствует |
| БД и LOGIN-роли внутри нового PostgreSQL | `mw_beta`, `mw_beta_bootstrap`, `mw_beta_migrator`, `mw_beta_web`; имена совпадают с контрактом, **это другой кластер** |
| Признак кластера | PostgreSQL `cluster_name=marketplace-e206-owner-check` и приватный marker-файл |
| Исходники | Новый detached worktree **опубликованной beta**, `/beta/app/releases/<REV>/backend`, read-only |
| Образ backend | Уже существующий `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`; lock должен совпасть |
| Образ PostgreSQL | Уже существующий `sha256:248efd5e58cd743f2a0e0daec8ea4649e5580145ec2a12e2345bc710d4a77201` |
| Browser | Существующие локальные Playwright/Chromium; временный SSH tunnel `127.0.0.1:18767` → IP нового web:8000, без host ports Docker |

Никаких загрузок образов/пакетов: `pull_policy=never`, подготовительный `docker run --pull never`. PostgreSQL/web/controller/issuer ограничены памятью 384/384/256/256 MiB и CPU 0.25 каждый; bootstrap одноразовый 256 MiB. Перед созданием нужны ≥2 GiB свободного диска и ≥2 GiB MemAvailable. Никакой SSH/install/создание этих ресурсов не считаются разрешёнными прежними S0/S1/S2.

Секреты только новые синтетические, случайные: отдельные bootstrap/migrator/web пароли, Django key и MFA key. Postgres получает свою закрытую копию bootstrap-файла под фактический UID postgres; bootstrap-контейнер — только три пароля provisioning. Web монтирует только свой DB пароль, Django key и MFA key. Controller/issuer получают migrator пароль и два ключа read-only, **не bootstrap/web пароли**. Proof/verifier/permit создаёт штатная CLI в `operator-output/`; issuer подключается только после появления verifier и получает его read-only в штатном пути. Ключи не помещаются в ENV/argv/stdout/репозиторий.

`prepare_owner_rehearsal.py --apply` отказывается при занятом пути/имени/volume/network, чужом release, непубликованном origin/beta ancestry или недостатке ресурсов. Повтор/автовыбор имени/перезапись/удаление старых probes запрещены. Bootstrap дополнительно проверяет пустую схему, отсутствие ролей и реальный cluster_name до DDL. Существующие `marketplace-beta` и `postgres-test` не используются для fixture или новых прав.

## Подготовленные файлы и критерии

- `beta/deploy/compose.owner-rehearsal.json` — отдельный полный Compose, не overlay основной beta.
- `beta/deploy/prepare_owner_rehearsal.py` — по умолчанию только план; `--apply` создаёт новые закрытые файлы и baseline трёх основных контейнеров; `--verify` сверяет изоляцию и неизменность этих контейнеров.
- `backend/tools/owner_rehearsal_bootstrap.py` — свежие ограниченные роли только в новом кластере.
- `backend/tools/owner_rehearsal.py` — защищённый служебный процесс для синтетического fixture, реальных CLI и проверок состояния; HTTP endpoint отсутствует.
- `scripts/e2_06_owner_browser.cjs` — настоящий Chromium через установленную библиотеку Playwright, без CLI-снимков секретных страниц, trace/video/скриншотов/storage dumps и raw exception output.

Fixture: четыре личных синтетических аккаунта и две организации, только `example.invalid`. Два владельца разделяют сценарии восстановления и управления сессиями, третий владелец проверяет привязку proof к нужному аккаунту; четвёртый — добровольность MFA. Существующие лимиты 5 попыток principal/30 peer за 15 минут считаются и для успешных входов; сценарий не сбрасывает buckets, не поднимает лимиты, не меняет часы/last_t. Библиотека django-otp генерирует тестовые коды по реальному времени, секрет TOTP не покидает серверный процесс.

Проверяются: ограниченная стадия до MFA; неправильный/просроченный/верный код подключения; реальная загрузка QR без его сохранения; одноразовый показ кодов; replay при входе; обязательность MFA владельцу; обычный выход только из текущей сессии; второе устройство; доверенный вход после пароля; свежее подтверждение для отзыва выбранной сессии; выход везде отзывает доверие. Затем восстановительный код, его повторный отказ, ограниченное переподключение и отзыв старой сессии; настоящая operator CLI с отказом неверного proof, чужого владельца и не-владельца; однократный permit; повторное подключение; смена пароля сохраняет MFA и отзывает доверие; блокировка закрывает текущую сессию, резервный код и operator CLI. Права/организации/членства сверяются до/после CLI, пароль CLI не меняет. Невключённый MFA обычного участника не препятствует личному входу по паролю.

Конкурентные гонки, полная матрица SQL-отказов и синтетический export revocation уже проверялись отдельным S1 и здесь не объявляются повторёнными. Полный бизнес-экспорт/RBAC/RLS не добавляются. Браузерный blocked-login не выдаётся за новую проверку причины отказа после исчерпания login bucket: отдельное доказательство этого критерия остаётся в S1. Реальное восстановление владельца и независимое хранение его ключа также не закрываются синтетическим стендом.

## Команды после push Олега и отдельного разрешения

Сначала получить опубликованный commit обычным Git fast-forward в серверном `beta/app/repository`, проверить чистоту и `origin/beta`. Выбрать полный SHA с этими файлами как REV и создать **новый** detached worktree. Старые releases не менять. Если имя release уже занято — остановиться и проверить происхождение/содержимое, не перезаписывать.

```sh
set -euo pipefail
base=/home/adm_user/marketplace-workspace/beta
repo="$base/app/repository"
: "${REV:?reviewed published full SHA required}"
test -z "$(git -C "$repo" status --porcelain)"
git -C "$repo" fetch origin beta </dev/null
git -C "$repo" merge-base --is-ancestor "$REV" origin/beta
git -C "$repo" pull --ff-only origin beta </dev/null
release="$base/app/releases/$REV"
test ! -e "$release"
git -C "$repo" worktree add --detach "$release" "$REV"
export REHEARSAL_SOURCE="$release/backend"
python3 "$release/beta/deploy/prepare_owner_rehearsal.py" --revision "$REV" --apply
dc() { docker compose --project-name marketplace-e206-owner-check --env-file /dev/null -f "$release/beta/deploy/compose.owner-rehearsal.json" "$@"; }
dc --profile operator config --quiet
docker run --rm --pull never --network none --read-only --cap-drop ALL --user 10001:10001 --mount "type=bind,src=$REHEARSAL_SOURCE/requirements.lock,dst=/expected.lock,readonly" sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72 python -c 'from pathlib import Path; assert Path("/expected.lock").read_bytes()==Path("/workspace/requirements.lock").read_bytes(); print("lock equal")' </dev/null
dc up -d --no-deps postgres </dev/null
healthy=false
for attempt in {1..20}; do
  if test "$(docker inspect --format '{{.State.Health.Status}}' marketplace-e206-owner-check-postgres)" = healthy; then healthy=true; break; fi
  sleep 3
done
test "$healthy" = true
dc run --rm --no-deps -T bootstrap </dev/null
dc --profile operator up -d --no-deps controller </dev/null
dc exec -T controller python -m tools.owner_rehearsal configure </dev/null
dc exec -T controller python -m tools.owner_rehearsal init </dev/null
dc exec -T controller python -m tools.owner_rehearsal operator_prepare </dev/null
dc --profile operator up -d --no-deps issuer </dev/null
dc up -d --no-deps web </dev/null
sleep 2
dc exec -T web python -m tools.verify_security_web_runtime </dev/null
python3 "$release/beta/deploy/prepare_owner_rehearsal.py" --revision "$REV" --verify
```

До fixture и перед browser сверить requirements.lock с существующим image, реальный effective Compose и UID/mounts/networks: JSON-проверка на Windows их не доказывает. Ни один шаг `configure/init/operator_prepare` не повторять автоматически после ошибки; сохранить частичный результат и выяснить этап. `operator_prepare` создаёт только синтетический proof, не доказательство личности Олега.

Открыть отдельный SSH tunnel на ноутбуке к IP **нового** `marketplace-e206-owner-check-web`, привязка строго 127.0.0.1:18767; exit-on-forward-failure. Не использовать старый IP основной beta. Туннель закрывается при любом завершении сценария.

```powershell
$env:E206_PLAYWRIGHT_MODULE='C:/Users/krolo/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright'
$env:E206_CHROMIUM='C:/Users/krolo/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe'
node scripts/e2_06_owner_browser.cjs $REV
```

Версии и пути установленного browser проверяются перед запуском; отсутствие компонента — остановка, не автоматическая установка. DEBUG/PWDEBUG запрещены. Не запускать secret-bearing `credentials/token/operator_issue --private-pipe` из обычного терминала/через инструменты с выводом: их stdout является **внутренним транспортом** SSH→Node в памяти. Runner не пересылает его в логи. Команды SSH содержат только фиксированные имена операций, никогда пароль/код/cookie/permit. Настоящая management CLI получает proof через PTY с проверенным отключённым echo, без env/argv.

После сценария выполнить `--verify`, сохранить только allowlisted PASS/FAIL и counts без секретов; проверить основной `tools.verify_security_web_runtime` read-only в его отдельном контейнере и совпадение metadata baseline. При ошибке не запускать весь сценарий повторно на частично изменённом fixture: сохранить состояние и подготовить конкретное продолжение/новое имя.

## Остановка, сохранение и откат

Закрыть локальный browser/tunnel, затем `dc --profile operator stop web controller issuer postgres` **только нового проекта**, без down -v/rm/prune. Сохранить volume, закрытые secret/proof/verifier/fixture файлы и результаты; никаких автоматических DROP/reuse. Основной web/его Compose/ключи/права/БД не менялись — их откат не нужен. Если baseline отличается, остановить новую проверку и выяснить причину, не менять основную beta автоматически.

Это новая пустая БД с синтетическим наполнением: до создания пользовательские данные отсутствуют, recovery backup основной beta не нужен и её dump сюда не импортируется. Для продолжения после неуспеха сохраняется собственный volume; удаление ресурсов — отдельное решение после проверки принадлежности и отсутствия поздней работы. Прежний S1 dump/restore и S2 main backup остаются неприкосновенными.

## Локальные проверки и открытые пункты

Подтверждены только синтаксис Python/Node, чтение плана без мутаций, JSON-инварианты изоляции/secret mounts, отказ --apply на Windows и отказ служебных команд без rehearsal marker. Linux PTY/getpass, effective Compose, реальный новый PostgreSQL и полный browser-run **ещё не выполнены**. Это не дополнительные прошедшие MFA-тесты и не основание менять E2-06 на «Готово».

Нужны публикация локального коммита самим Олегом и отдельное разрешение ровно перечисленных новых ресурсов/синтетических секретов/fixture/CLI/browser/остановки. Передачу основного ключа, пароль к его envelope, реальный emergency secret и Telegram эта просьба не включает.
