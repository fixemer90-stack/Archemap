# Career: заметный возврат в личный кабинет

Статус: исправлено, опубликовано, exact-SHA CI и native production-приёмка завершены.

## Причина

`/products/career` намеренно использует standalone layout без общего sidebar/header. Ссылка «К обзору продуктов» существовала только после всего содержимого страницы. Native production-проверка показала её верхнюю границу на 1178px при ширине 320px и viewport height 900px: на первом экране выхода не было. На широком экране нижняя ссылка могла быть видна, поэтому утверждение о полном отсутствии ссылки на всей странице было бы неточным.

## Исправление

В общей, безусловно отрисовываемой верхней части страницы добавлена navigation landmark «Навигация Career» с явной ссылкой «В личный кабинет» → `/dashboard`. Она не зависит от browser history, выбранного профиля, загрузки, ошибки, анкеты, Plus или состояния генерации. Нижняя ссылка сохранена. Изменены только навигационный JSX и верхние отступы; auth guard и бизнес-логика не затронуты.

## Локальная проверка

- RED: отсутствует верхний navigation/link на реальном компоненте, mobile Chromium.
- GREEN: 16 navigation tests — восемь состояний в desktop/mobile contexts. Ссылка полностью в первом viewport, href правильный, фокус доступен, Enter приводит в `/dashboard`, Career mutations отсутствуют.
- Повторный расширенный запуск без snapshot update: 85 passed, 1 intentional skip (mobile print). Включены navigation, questionnaire, resume, reader, внутренний overflow и обе темы.
- Восемь намеренно обновлённых product/questionnaire snapshots просмотрены. Reader snapshots не менялись.
- Repo-wide ESLint: 0 errors, 2 прежних warning в auth pages. Prettier, TypeScript, `npm test`, production `next build` — PASS.
- Все десять frontend changed/new paths byte-for-byte совпали между canonical checkout и Linux verification scratch.

## Приёмка

- [x] Отсутствие заметного верхнего выхода воспроизведено до исправления.
- [x] Общая navigation-ссылка работает во всех восьми UI-состояниях и с клавиатуры.
- [x] Визуальные, state-machine, responsive и build проверки выполнены после изменения.
- [x] Независимый review и 11/11 scope fingerprints подтверждены. Проверены десять frontend paths, snapshots и operational wrapper; reviewer не выполнял browser tests или deployment. Ширина 320px дополнительно проверяется native release smoke, а не текущим 390px mobile project.
- [x] Публикация и exact-SHA CI завершены.
- [x] Только frontend пересоздан; остальные контейнеры и конфигурация сохранены.
- [x] Native production-переход в кабинет проверен на mobile/tablet/desktop без mocks; сохранённые отчёты не изменились.

## Production-приёмка — 2026-11-21 UTC

- Развёрнутый и проверенный code SHA `02055c22aedba5bc8520b816c0d7e034481b7736`, tree `6197362121c4cd167cfb2f9bfbf0cdc0aed1ccf4`; все 1321 tracked blobs проверены по manifest. Commit/tree/archive и SHA-256 связаны до сборки и проверены после передачи.
- Exact-SHA CI `44875296678`: все восемь jobs success. Из terminal logs: 211 Career browser tests, 1594 backend unit и 246 integration passed; production build и Docker builds success. Отдельный registry workflow `44875296713`: preflight success, build/push/deploy jobs skipped; он не является deploy evidence.
- Frontend image `sha256:e669e10e87bc33f36134fb9aeb642eff9a475ea9e7d6add9f4414f218df48b1c`. Пересоздан только frontend; остальные семь контейнеров, их images/config, приватные dotenv, feature flags, environment values, restart policies и Caddy config сохранены. API/DB/Redis health `ok`.
- Native production, без response mocks: прямой `/products/career`, ожидаемый профильный экран, видимая верхняя ссылка, фактический click → `/dashboard`, видимые main/h1. PASS на 320/820/1440px. Верхняя кнопка на 320px занимает y16–56 и полностью видна без скролла; нижняя ссылка остаётся на y1266–1306. На tablet/desktop верхняя кнопка y24–64. Ноль horizontal overflow, Career mutations и page errors; реальные скриншоты просмотрены.
- Полные saved-row hashes до/после совпали: Career 3 generations / 3 reports / 30 segments; Child 2 reports / 30 segments; Self 1 natal report. Новые генерации и questionnaire mutations не выполнялись, исторические результаты сохранены.
- Использовался короткоживущий access JWT штатного issuer для авторизованного оператора; это не проверка login-flow. Токен не записывался в исходники/отчёт/evidence.
- Private evidence: `/root/astrotype-recovery-evidence/career-navigation-release/`; controller: `/root/astrotype-recovery-evidence/career-navigation-rollout.py`. Импортируемые helpers `/root/astrotype-recovery-evidence/career-mobile-rollout.py`, `/root/astrotype-recovery-evidence/career-resume-rollout.py` и `/root/astrotype-recovery-evidence/restore-child-test-config.py` остаются операционными зависимостями и не должны удаляться при cleanup. Overlay: `/opt/astrotype/recovery.compose.json`, с immutable image IDs.
- Deploy SHA/tree markers записаны и прочитаны обратно только после native acceptance, report preservation и runtime readback.

Платные генерации, анкеты или entitlements на production оператором не создаются и не переписываются ради проверки навигации.
