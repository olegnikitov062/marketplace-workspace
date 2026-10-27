# E2-06: новый полный браузерный прогон R2

02.10.2026, Europe/Moscow. **R2 выполнен на опубликованном 2c2f8f737262267d29d06ab40d7bef3571693745: 10 PASS, exit 0, pageerrors=0; реальная operator CLI, SQL/runtime и итоговое состояние PASS.** Все четыре новых контейнера остановлены, данные сохранены; основная beta и первый стенд неизменны. Ниже сохранён согласованный план, фактический результат — в конце. Имена/fixture теперь заняты: повторять команды создания или полный browser запрещено. Фактическая передача основного ключа остаётся отдельным этапом docs/E2-06_KEY_HANDOFF.md.

## Что должен закрыть прогон

Первый стенд прошёл восемь функциональных этапов настоящего Chromium и операторскую CLI, но полный runner завершился exit 1 из-за неверного ожидания пароля после блокировки. Исправленный `finish` отдельно прошёл на PostgreSQL с SQL только для чтения. R2 должен подтвердить единый полный прогон с exit 0, итоговым отсутствием browser pageerrors и правильным конечным состоянием. Исторические результаты не заменяются и не суммируются с R2.

Используется тот же сценарий: подтверждённое подключение TOTP; неправильный/просроченный/повторный код; ограниченный доступ до MFA; CSRF; текущий/выборочный/общий отзыв сессий; доверенное устройство; повторное подтверждение; восстановительный код и его повторный отказ; настоящая operator CLI с неверным proof/чужим владельцем и одноразовым permit; повторное подключение; смена пароля с сохранением MFA; блокировка; добровольный MFA участника. В конце — 10 отметок PASS, JSON result=PASS и exit 0. Секреты находятся только в закрытых серверных файлах или памяти процессов.

Конкурентные запросы, точная матрица SQL-отказов, синтетическая экспортная ссылка и dump/restore остаются отдельными доказательствами S1; этот browser runner их заново не проверяет. R2 не создаёт рабочий экспорт/RBAC/RLS, публичный TLS, реального владельца или независимую копию основного ключа у Олега.

## Фиксированные новые ресурсы

| Ресурс | Имя / значение |
| --- | --- |
| Compose project и cluster_name | `marketplace-e206-owner-check-r2` |
| Контейнеры | `marketplace-e206-owner-check-r2-postgres`, `marketplace-e206-owner-check-r2-web`, `marketplace-e206-owner-check-r2-controller`, `marketplace-e206-owner-check-r2-issuer` |
| Внутренняя сеть | `marketplace-e206-owner-check-r2-private`, internal, без ingress/host ports |
| Volume | `marketplace-e206-owner-check-r2-data` |
| Каталог | `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-06-owner-r2-20261002` |
| Файлы резервных metadata | `baseline.json` для основной beta и `preserved-rehearsal.json` для первого стенда, 0600/no-overwrite |
| Закрытые каталоги | `secrets/`, `state/`, `operator-output/`, 0700; файлы 0600 |
| Новая БД / роли только внутри R2 | `mw_beta`; `mw_beta_bootstrap`, `mw_beta_migrator`, `mw_beta_web` |
| Fixture | 4 синтетических пользователя `example.invalid`, 2 организации, 5 членств |
| Backend image | `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72` |
| PostgreSQL image | `sha256:248efd5e58cd743f2a0e0daec8ea4649e5580145ec2a12e2345bc710d4a77201` |
| Временный browser tunnel | `127.0.0.1:18767` → private IP только R2 web:8000 |

PostgreSQL/web/controller/issuer: 384/384/256/256 MiB и 0.25 CPU. Допустимы существующие образы без pull/build/install, кратковременный контейнер для определения UID postgres, закрытая генерация синтетических secrets без сети и одноразовый bootstrap только R2. Веб-процесс получает точные E2-06 DML-права; migrator нужен исключительно controller/issuer по неизменённому operator guard. Bootstrap пароль не монтируется в них или web. Предварительно нужны минимум 2 GiB MemAvailable и свободного диска.

Имена БД совпадают с контрактом operator CLI, но это отдельный PostgreSQL-кластер с новым cluster_name, сетью, volume и ключами. `E206_REHEARSAL` допускает только исходный профиль и фиксированный R2; marker и реальный cluster_name должны совпасть с профилем. `require_operator_process`, пароль/TOTP/CSRF/блокировки и модель владения не менялись. Исходная Compose-конфигурация сохранена; новая `compose.owner-rehearsal-r2.json` отличается только идентификаторами ресурсов/путями.

## Сохранность и preflight

1. Сверить Git beta, публикацию выбранного полного REV и чистоту server repository. Получать код только Git fast-forward. Новый immutable release — `/home/adm_user/marketplace-workspace/beta/app/releases/<REV>`; занятый путь не перезаписывать. Проверить неизменный requirements.lock с существующим image и отсутствие изменений runtime auth/settings/ownership/migrations/SQL grants.
2. Основная beta должна оставаться на source `14d9f48cee6eb2a9d7eca9f029770af51c45b6d9`; сравнить web ID `53dd81f2850521138b9596d1aa5f910f7889785d8836329efbbfb0f7b57654c5` и оба PostgreSQL с текущим протоколом. Снимок основных ID/image/StartedAt/mounts/networks/ports хранится только с безопасными metadata, без Config.Env или содержимого секретов.
3. У первого стенда все четыре контейнера должны быть остановлены; его controller после проверки finish использует dd98035, web/issuer — 14d9f48. Сохранить новый снимок его metadata в R2 `preserved-rehearsal.json`, не переписывая старый baseline. Старые volumes, keys, fixture, proof/verifier/permit, S1/S2/C1/A/B/restore не читать для нового fixture, не импортировать и не переиспользовать.
4. R2 root/containers/project/network/volume должны отсутствовать. При занятом имени, расхождении основного состояния или частичных файлах остановиться до provisioning; не выбирать новый суффикс автоматически.

До создания R2 в его БД нет пользовательских данных. Резерв для сохранения синтетического результата — собственные volume, закрытые файлы и оба metadata-снимка; после сценария они сохраняются. Основные S1/S2 dump/key envelope остаются неприкосновенными. Новый dump/restore основной beta или восстановление в R2 не входит в этап. При сбое сохранить остановленный R2 и подготовить отдельное продолжение; восстановление допускается только по новому конкретному плану в новый ресурс, без live restore/сброса fixture.

## Порядок после публикации и согласования

Команды выполняются через существующее SSH-подключение исключительно внутри beta. REV — проверенный полный SHA с этой подготовкой, не автоматически latest. Во всём блоке использовать только R2 project/Compose. Команды provisioning одноразовые; не выполнять их повторно после частичного успеха.

```sh
set -euo pipefail
base=/home/adm_user/marketplace-workspace/beta
repo="$base/app/repository"
project=marketplace-e206-owner-check-r2
: "${REV:?reviewed published full SHA required}"
test -z "$(git -C "$repo" status --porcelain)"
git -C "$repo" fetch origin beta </dev/null
git -C "$repo" merge-base --is-ancestor "$REV" origin/beta
git -C "$repo" pull --ff-only origin beta </dev/null
release="$base/app/releases/$REV"
test ! -e "$release"
git -C "$repo" worktree add --detach "$release" "$REV"
export REHEARSAL_SOURCE="$release/backend"
dc() { docker compose --project-name "$project" --env-file /dev/null -f "$release/beta/deploy/compose.owner-rehearsal-r2.json" --profile operator "$@"; }
dc config --quiet </dev/null
docker run --rm --pull never --network none --read-only --cap-drop ALL --user 10001:10001 --mount "type=bind,src=$REHEARSAL_SOURCE/requirements.lock,dst=/expected.lock,readonly" sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72 python -c 'from pathlib import Path; assert Path("/expected.lock").read_bytes()==Path("/workspace/requirements.lock").read_bytes(); print("lock equal")' </dev/null
python3 "$release/beta/deploy/prepare_owner_rehearsal.py" --project "$project" --revision "$REV" --apply </dev/null
dc up -d --no-deps postgres </dev/null
healthy=false
for attempt in {1..20}; do
  if test "$(docker inspect --format '{{.State.Health.Status}}' marketplace-e206-owner-check-r2-postgres)" = healthy; then healthy=true; break; fi
  sleep 3
done
test "$healthy" = true
dc run --rm --no-deps -T bootstrap </dev/null
dc up -d --no-deps controller </dev/null
dc exec -T controller python -m tools.owner_rehearsal configure </dev/null
dc exec -T controller python -m tools.owner_rehearsal init </dev/null
dc exec -T controller python -m tools.owner_rehearsal operator_prepare </dev/null
dc up -d --no-deps issuer web </dev/null
dc exec -T controller python -m tools.owner_rehearsal pre_browser </dev/null
dc exec -T web python -m tools.verify_security_web_runtime </dev/null
python3 "$release/beta/deploy/prepare_owner_rehearsal.py" --project "$project" --revision "$REV" --verify </dev/null
```

Перед стартом браузера проверить effective Compose/mounts/limits/roles/private network, свободный localhost:18767 и принадлежность private IP именно R2 web. Открыть SSH tunnel без публичного bind. В Windows использовать уже установленную библиотеку и Chromium, без npx/download:

```powershell
$env:E206_REHEARSAL = 'marketplace-e206-owner-check-r2'
$env:E206_PLAYWRIGHT_MODULE = 'C:/Users/krolo/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright'
$env:E206_CHROMIUM = 'C:/Users/krolo/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe'
node scripts/e2_06_owner_browser.cjs $revision
```

`$revision` равен серверному REV; локальный runner должен соответствовать тому же опубликованному коду. DEBUG/PWDEBUG не заданы. Browser runner проверяет Compose project и RO source controller/issuer. Не сохранять trace, screenshot, storage state, тело ответов, QR/коды, cookies или raw exceptions. Приватный SSH pipe с credentials/token/permit доступен только памяти процесса runner. В отчёт попадают названия этапов, PASS/FAIL и разрешённые счётчики. Нельзя вручную запускать private-pipe команды в вывод инструмента.

## Завершение при любом исходе

Закрыть собственные browser contexts и tunnel. Пока R2 запущен, выполнить `--verify` с R2 project и сравнить metadata обоих защищаемых проектов; сделать allowlisted проверку конечного состояния без вывода строк/секретов. Затем `dc stop web controller issuer postgres </dev/null` только R2. Проверить остановку всех четырёх, сохранность volume/закрытых файлов и неизменность основной beta/первого стенда. При отказе оставить FAIL с точным этапом, не выполнять второй browser run автоматически.

Безопасный откат — остановка только новых контейнеров с сохранением volume/network/файлов. Основная beta и первый стенд не меняются. Не выполнять down -v, DROP, prune, общий restart, старые probes, снятие блокировки, сброс buckets/last_t, повторную генерацию secrets или restore поверх БД. Удаление сохранённых ресурсов требует отдельного решения.

После результата дополнить SYSTEM_SECURITY_CHECKS.json, SYSTEM_PLAN.md и CHANGELOG.md с точной ревизией и границами доказательства; автор локального коммита Oleg, push выполняет Олег. Даже успешный R2 не закрывает независимое хранение ключа владельцем или рабочий экспорт; E2-06 остаётся «На проверке» до фактического закрытия соответствующих критериев.


## E2-06: полный браузерный R2 пройден — 2026-10-02T15:23:05+03:00

После явного разрешения полного отдельного браузерного прогона и сообщения Олега о публикации проверена origin/beta `2c2f8f737262267d29d06ab40d7bef3571693745`. Сервер получил эту ревизию только Git fast-forward и новый detached release; requirements.lock совпал с существующим image. Runtime auth/accounts/ownership/config/migrations/SQL grants по сравнению с основной 14d9f48 не изменены. Новых зависимостей/сборок нет.

Создан только фиксированный `marketplace-e206-owner-check-r2`: отдельный PostgreSQL 17.11, internal network без host ports, новый volume, закрытые синтетические secrets и fixture 4 example.invalid пользователя / 2 организации / 5 членств. Миграций 36; точный SQL-контракт настоящего mw_beta_web и runtime smoke прошли до браузера. Controller/issuer использовали настоящую mw_beta_migrator; bootstrap-права web не передавались. Effective Compose и фактические mounts/UID/read-only/limits/logging none проверены.

Полный runner настоящего Chromium на этой ревизии: **10 PASS, result=PASS, exit 0**, actualOperatorCli=true. Проверены неправильный/просроченный/верный TOTP и подтверждённое подключение, показ одноразовых кодов только один раз, отказ повторного TOTP и доступа до MFA, запрет отключения владельцу и CSRF; текущий/выборочный/общий отзыв сессий, доверенное устройство и свежая проверка; одноразовый восстановительный код с обязательным подключением нового фактора; настоящая operator CLI с отказом неверному proof/чужому владельцу, одноразовым permit и сохранением прав; смена пароля с сохранением MFA и отзывом доверия; блокировка и отказ code/operator восстановления; вход участника без добровольно подключённого MFA. Глобальный pageerror counter достигнут и равен 0. TOTP использовал настоящее время и штатные throttles, без сброса buckets/last_t или подмены часов.

Дополнительный внешний audit сначала завершился отказом: проверка домена обращалась к User.email, хотя адреса находятся в AccountContact. Полный browser к этому моменту уже завершился exit 0, включая свой finish. Первый отказ и остановка сохранены в протоколе. Для исправленного чтения временно запущены только сохранённые R2 postgres/controller с теми же ID/source, web/issuer остались остановлены; SQL с начала подключения read-only, browser не повторялся. Итог дополнительно прочитан в SQL read-only: владелец неактивен, пароль unusable, действующих сессий/доверенных устройств=0, использованный permit=1, приглашений=0, организации/членства неизменны. Один подтверждённый фактор остаётся у заблокированного аккаунта; блокировка запрещает доступ. Закрытые файлы имеют 0600 и не изменились при итоговой проверке. Только locmem; секреты/QR/cookies/ссылки/тела ответов/трассы/скриншоты не сохранялись в отчёт.

Tunnel закрыт, все четыре R2 контейнера остановлены; volume/network/закрытые файлы и новый release сохранены. Основной web остался на 14d9f48, ID/image/StartedAt/mounts/networks/ports основной beta и остановленного первого стенда совпали до/после. Их ключи/данные/старые baseline не использовались как fixture и не изменялись. R2 root: `/home/adm_user/marketplace-workspace/beta/rehearsals/e2-06-owner-r2-20261002`; ресурсы теперь заняты, повтор provisioning/init/full browser на этом fixture запрещён.

Исторический первый aggregate exit 1 сохранён как факт; новый R2 независимо закрыл чистый полный exit и pageerror counter. Конкурентность, 17 SQL-отказов, синтетическая экспортная ссылка, dump/restore и maintenance остаются доказательствами S1, здесь повторно не запускались. Основной ключ не читался/не передавался; K1/K2/K3 по docs/E2-06_KEY_HANDOFF.md и рабочий экспорт/RBAC/RLS остаются за границами этого прогона. E2-06 **На проверке** до оставшихся критериев; E2-07 и далее не начаты.

Безопасный откат запуска уже выполнен: stop только R2 с сохранением volume/network/files; не down -v, DROP, prune, live restore, reseed или сброс counters. Новый запуск/удаление ресурсов — отдельный конкретный план и разрешение. Подробный протокол: SYSTEM_SECURITY_CHECKS.json/browser_r2_run.
