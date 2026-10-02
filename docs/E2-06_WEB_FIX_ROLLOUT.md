# E2-06: исправление браузерных форм основной beta

02.10.2026, Europe/Moscow. **План выполнен по отдельному явному разрешению Олега; результат зафиксирован 2026-10-02T13:41:10+03:00.** Основной web переведён на `14d9f48cee6eb2a9d7eca9f029770af51c45b6d9`; SQL/runtime и анонимная проверка Chromium прошли. Ниже сохранён согласованный объём и порядок; его повторный запуск этим протоколом не разрешается. Подробный результат — в конце документа.

## Основание и предел доказательств

Native HTML-формы с `Referrer-Policy: no-referrer` посылают из Chromium `Origin: null`; Django закономерно отказывает по CSRF. В 14d9f48 политика изменена на `same-origin`, без ослабления CSRF/secure cookies. На отдельном стенде пройдены восемь функциональных браузерных этапов, включая реальную `issue_owner_recovery` с migrator LOGIN, отрицательные proof/owner проверки, однократный permit и повторное подключение.

Сводный browser runner завершился exit 1 из-за ошибочного ожидания нового пароля **после** блокировки: E2-05 намеренно делает его unusable. Это не чистый PASS всего runner. Правильное конечное состояние отдельно проверено read-only на PostgreSQL: владелец заблокирован, оба пароля отвергнуты, все сессии/доверие отозваны, один permit использован, организации/членства неизменны. Финальный счётчик browser pageerrors не был проверен после прерванного RPC; его нулевое значение не заявляется. Исправление этой проверки опубликовано в aeb7842 и включено в проверенную beta 91b079a; helper на Linux ещё не запускался, runtime-логика аккаунтов не менялась.

## Точный объём нового разрешения

- Только основной `marketplace-beta` service `web`: source с `19a6d6a9bbdd06c683f68f438215dd99cba6204e/backend` на существующий Git release `14d9f48cee6eb2a9d7eca9f029770af51c45b6d9/backend`, read-only.
- Тот же dependency image `sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72`, тот же `requirements.lock`, UID/CPU/memory/private network/secrets/SQL web-role.
- Один закрытый снимок metadata трёх основных контейнеров и безопасных счётчиков в новом `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-referrer-before-<UTC>.metadata.json`, 0600, no-overwrite. Не сохранять Config.Env, credentials, session payloads или key fingerprints.
- Read-only SQL/runtime и узкая анонимная проверка Chromium по временному localhost:18767 SSH tunnel. Браузер проверяет заголовок и Origin native POST, **отменяя POST до сервера**; пароли/аккаунты в основной БД не создаются.
- При отказе — только уже проверенный MFA maintenance либо остановка основного web. Оба PostgreSQL, сохранённый owner rehearsal и прежние тестовые БД не перезапускаются/не переиспользуются.

Нет миграций, GRANT/REVOKE, новых DB/ролей/ключей, сборки/установки, передачи секретов, real-owner provisioning, production/Caddy/worker/UI/экспорта/RBAC/RLS.

## До переключения

1. Проверить опубликованную beta, чистый серверный repository и immutable release 14d9f48; исходники только Git. Сверить diff с основным 19a6d6a: исполняемое приложение отличается только Referrer-Policy; прочие изменения — tools/tests/docs. При другом runtime diff остановиться.
2. Проверить image ID/lock, текущие RO source/key mounts, UID/network/limits и три основных контейнера. Текущий web должен быть `42ea5c212f1fc3062df51214ca97428e4613741adb8fac7897e494faaeb8e106` с source19a6d6a; оба PostgreSQL должны совпасть с последним baseline. Не предполагать, что состояние не изменилось.
3. Через фактическую ограниченную `mw_beta_web` проверить SQL-контракт и миграции. Без вывода строк проверить, что основных users/organizations/memberships/authenticators/recovery permits/recovery codes по-прежнему нет. Если появились реальные данные или изменилась схема — остановиться до изменения web и уточнить план. Анонимные зашифрованные Django sessions допустимы.
4. Приватно сохранить новый metadata-снимок с no-overwrite и сверить read-back. Проверить наличие/режимы сохранённых S2 dump, ACL/snapshot и key envelope: `e2-06-before-20261001T144009Z.dump`, соседние `.acl.json`/`.snapshot.json`, `e2-06-main-key-envelope/envelope.json`; пароль отдельно в config. Не выводить содержимое/ключевые fingerprints.

## Backup/restore и откат

Переключение не меняет схему, права или данные БД; новым резервом для отката кода является metadata-снимок, а старый RO release19a6d6a и образы сохраняются. Новый dump/restore этим ограниченным этапом не планируется. S1 подтвердил синтетический E2-06 dump/restore с отдельным восстановлением ключа, S2 сохранил pre-migration main dump/restore; это исторические доказательства, не новый снимок текущей E2-06 БД. Нельзя выдавать старый dump за актуальный или восстанавливать его поверх используемой БД.

При отказе переключения не менять БД: включить `compose.security-maintenance.json` на проверенном старом dependency image + E2-06 source или остановить только web. Обычный base-only/E2-05/accounts-overlay запуск запрещён. Если когда-либо потребуется восстановление БД, оно проводится в отдельную новую БД по отдельному разрешению, с проверкой ключа/ACL/карантина отозванного доступа; этот план такого разрешения не запрашивает.

## Переключение после разрешения

```sh
base=/home/adm_user/marketplace-workspace/beta
release="$base/app/releases/14d9f48cee6eb2a9d7eca9f029770af51c45b6d9"
export BACKEND_IMAGE=marketplace-workspace/backend:e2-03-0210f27a7ab1
export SECURITY_IMAGE=sha256:86f9cac63025d6c6119d2f7e0b232004b3ebfe98a82800a672bef73fdd1fbe72
export SECURITY_SOURCE="$release/backend"
dc() { docker compose --project-name marketplace-beta --env-file /dev/null --project-directory "$base/deploy" -f "$base/deploy/compose.json" "$@"; }
dc -f "$release/beta/deploy/compose.security-web.json" config --quiet </dev/null
dc -f "$release/beta/deploy/compose.security-web.json" up -d --no-deps web </dev/null
dc -f "$release/beta/deploy/compose.security-web.json" exec -T web python -m tools.verify_security_web_runtime </dev/null
```

Затем фактически сверить новое RO source14d9f48, прежний image/key mounts/UID/limits/private network/no ports, неизменность обоих PostgreSQL, SQL и исходных счётчиков. Анонимный Chromium: GET login200, policy same-origin, cookie/CSRF-поле присутствуют, native POST Origin совпадает с localhost origin; POST отменить на стороне браузера до отправки. Никаких screenshots/traces/body/header dumps. Закрыть browser/tunnel при любом исходе.

При ошибке, с теми же base/release/env/dc:

```sh
dc -f "$release/beta/deploy/compose.security-maintenance.json" up -d --no-deps web </dev/null
# либо остановить только web, если maintenance не подтверждён:
dc -f "$release/beta/deploy/compose.security-web.json" stop web </dev/null
```

После выполнения записать новый web ID/StartedAt/source и точные проверки в SYSTEM_STARTUP.md, docs/RUNBOOK.md, SYSTEM_SECURITY_CHECKS.json и CHANGELOG.md с исходными копиями. E2-06 остаётся «На проверке»: независимое хранение ключа Олегом и полный экспорт не закрываются переключением web. Реальный аварийный секрет/передача envelope/пароля требуют отдельных конкретных решений.


## E2-06: основной web обновлён до 14d9f48 — 2026-10-02T13:41:10+03:00

По отдельному явному разрешению выполнен docs/E2-06_WEB_FIX_ROLLOUT.md. Публикация beta `91b079a30569b6fc38997b47fe18d6af723b9321` подтверждена, чистый серверный repository обновлён только Git fast-forward. Основной web использует существующий read-only release `14d9f48cee6eb2a9d7eca9f029770af51c45b6d9/backend` и прежний immutable dependency image. Исполняемое приложение изменилось только в Referrer-Policy: same-origin; CSRF, secure cookies, lock, схема, SQL-права и ключи сохранены. Пересоздан только web, оба PostgreSQL сохранили ID/image/StartedAt/mounts/networks/ports; четыре контейнера owner rehearsal остались остановленными.

Закрытый metadata checkpoint `/home/adm_user/marketplace-workspace/beta/backups/database/e2-06-referrer-before-20261002T102702Z.metadata.json` создан без перезаписи (0600), read-back совпал. Наличие и режимы прежних S2 dump/ACL/snapshot/key envelope и отдельных key/passphrase проверены без вывода содержимого. Новые dump/restore, миграции, GRANT/REVOKE, DB/роли/ключи, установки и сборки не выполнялись; S1/S2 backup/restore остаются историческими доказательствами.

Фактическая ограниченная mw_beta_web, точные SQL-права/guards и runtime smoke PASS: live/ready 200, session 401, legacy login GET 405, MFA login GET 200. В Chromium GET login 200, same-origin/no-store, secure cookie/CSRF-поле, корректный native POST Origin; POST отменён до сервера. Pageerrors=0 только в этой анонимной проверке; она не заменяет полный owner rehearsal и не подтверждает публичный TLS. Browser/tunnel закрыты. Основные users/org/memberships/authenticators/codes/permits/account sessions/attempt buckets/auth denials равны нулю; анонимные encrypted Django sessions выросли с 4 до 6 из-за GET login. Locmem/выключенные внешние flags и public export probe подтверждены.

E2-06 остаётся **На проверке**: чистый итог полного runner/его pageerror counter, запуск исправленного helper на Linux, независимая копия ключа у Олега и критерий рабочего экспорта ещё не закрыты. Реальные owner proof/передача envelope и отдельного пароля не выполнялись и требуют конкретного отдельного разрешения; E2-07/E2-08/E5-07 не реализуются здесь. Полные 63 PostgreSQL-теста S1 и восемь функциональных браузерных этапов прежнего стенда в этом переключении не повторялись.

Протокол: SYSTEM_SECURITY_CHECKS.json/main_web_referrer_rollout. Сохранённый baseline owner rehearsal относится к основному web до этого разрешённого обновления; его нельзя молча переписать или заново запускать pre_browser на уже использованном fixture. Безопасный fallback — согласованный MFA maintenance либо остановка только web, без base-only/accounts overlay и восстановления поверх живой БД.
