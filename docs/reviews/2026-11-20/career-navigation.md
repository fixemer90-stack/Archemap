# Career: заметный возврат в личный кабинет

Статус: локально исправлено и проверено, независимый review пройден; публикация, CI и production-приёмка ещё не завершены.

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
- [ ] Публикация и exact-SHA CI завершены.
- [ ] Только frontend пересоздан; остальные контейнеры и конфигурация сохранены.
- [ ] Native production-переход в кабинет проверен на mobile/tablet/desktop без mocks; сохранённые отчёты не изменились.

Платные генерации, анкеты или entitlements на production оператором не создаются и не переписываются ради проверки навигации.
