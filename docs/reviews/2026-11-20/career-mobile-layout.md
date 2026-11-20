# Career: responsive reader layout repair

Статус: исправлено, опубликовано, exact-SHA CI и native production-приёмка завершены.

## Дефект и причина

На production заголовок, описание и профиль выходили за внутреннюю ширину hero. `overflow-hidden` скрывал ошибку: при ширине экрана 390px document overflow отсутствовал, но hero имел clientWidth 356px и scrollWidth 460px. Неявная grid-колонка сохраняла min-content ширину длинного слова. На desktop длинное слово тоже выходило за колонку; на 320px дополнительные переполнения создавали группа действий и заголовки разделов.

## Изменения

- Явная сжимаемая одноколоночная сетка до desktop; `min-w-0` на вложенных grid items, разделительный gap на узком экране.
- Адаптивный размер заголовка: 20px до 360px, 24px на обычном мобильном экране, 48px начиная со sm. Первое длинное слово сохраняется целиком во всей тестовой матрице.
- Перенос длинных слов в reader без удаления/обрезания содержимого; группа действий допускает перенос кнопок. Tooltip-термины остаются whole-word.
- Добавлена browser-регрессия по внутренней геометрии, текстовым Range, целостности слова и внешнему scrollWidth на ширинах 320/390/768/1024/1440px в обеих темах и обоих desktop/mobile browser contexts.
- Намеренно обновлены девять Career snapshots: reader desktop/mobile/print и шесть theme/viewport вариантов. Остальные snapshots не изменены.

## Выполненные локальные проверки

- RED: 390px, внешний overflow false, внутренний hero overflow true, заголовок/описание/карточки выходят за границы.
- Дополнительный RED: заголовок полностью помещается, но первое слово разорвано на две строки. После изменения типографики — одна строка для этого слова.
- GREEN: 20 layout-регрессий.
- Финальный запуск без обновления snapshots: 67 browser tests passed, 1 intentional skip (mobile print). Включает layout, reader/accessibility/print, theme visual matrix и Career resume.
- Repo-wide ESLint: 0 errors, 2 ранее существовавших warning в login/register. Prettier, TypeScript и `npm test` — PASS.
- Production `next build` — PASS. Linux scratch проверен byte-for-byte по всем 11 изменённым frontend paths; временный probe прерванного child удалён только из scratch.

## Критерии закрытия

- [x] Дефект воспроизведён до изменения production-кода.
- [x] Полный текст и профиль помещаются, не скрыты дополнительной обрезкой.
- [x] Регрессии desktop/mobile/tablet, обе темы, доступность и print проверены.
- [x] Независимый review и scope fingerprints подтверждены. Все 11 frontend paths и operational controller одобрены; тесты reviewer не запускал. После review усилен только тест (ожидание fonts.ready и вертикальные текстовые bounds), 20 регрессий повторно прошли; production-код/контроллер/snapshots не изменились.
- [x] Изменения опубликованы; exact-SHA CI завершён.
- [x] Обновлён только frontend; остальные семь контейнеров и приватная конфигурация сохранены.
- [x] Native production smoke без mocks подтвердил исправление; сохранённые отчёты не изменились, новых генераций нет.

## Production-приёмка

- Проверенный и развёрнутый code SHA: `66406822590d2dd9b3ce6b2fc5444102abd3108f`, tree `371b70d0e955492b50ec710e908d37066e034f38`. Перед сборкой проверены Git archive/commit/tree/manifest и SHA-256 на обеих сторонах; все 1319 tracked blobs проверены перед финальными маркерами.
- Exact-SHA CI `44836297294`: все восемь jobs success. В логе: 195 Career browser tests, 1594 backend unit, 246 integration passed; production build и Docker builds success. Отдельный registry workflow `44836297240`: preflight success, build/push/deploy jobs skipped; он не считается rollout-доказательством.
- Новый frontend image: `sha256:d7d1a76c4868b40987d4ce5ccff969708b52d3a15cff9e44e6deb595c03cb94f`. Пересоздан только frontend, остальные семь контейнеров сохранили IDs/images/config. Приватные dotenv, runtime environments, feature flags, restart policies и Caddy config не изменились; overlay изменил только frontend image/build label. API/DB/Redis health: `ok`.
- Native production reader без response mocks: 320/390/768/1440px, light и dark. Реальная тема проверена по HTML class с каноническим persisted key `astrotype-theme`. Во всех восьми случаях document width совпадает с scrollWidth, hero width совпадает с scrollWidth, текстовые bounds внутри hero, первое слово заголовка занимает одну строку. Скриншоты просмотрены; обрезания заголовка, описания, статусов или профильных карточек нет. На 320px кнопки переносятся.
- Ноль Career mutations, ноль page errors. Перед/после совпали полные saved-row hashes: Career 3 generations / 3 reports / 30 segments; Child 2 reports / 30 segments; Self 1 natal report. Новых платных генераций не запускалось, историческая partial_failure сохранена.
- Операторский native-доступ — короткоживущий штатный access JWT, не проверка пользовательского login-flow; токен не записан в исходники/отчёт/evidence. Приватные evidence: `/root/astrotype-recovery-evidence/career-mobile-release/`; controller: `/root/astrotype-recovery-evidence/career-mobile-rollout.py`. Он импортирует прежние проверенные helpers `/root/astrotype-recovery-evidence/career-resume-rollout.py` и `/root/astrotype-recovery-evidence/restore-child-test-config.py`; эти файлы нельзя удалять при операционном cleanup. Активационный overlay: `/opt/astrotype/recovery.compose.json`.
- `.deploy-sha` / `.deploy-source-tree` записаны и прочитаны обратно только после CI, native-приёмки, проверки сохранности отчётов и финального runtime readback.

Backend, API, генераторы, данные отчётов и провайдеры в этом исправлении не меняются. Новый платный LLM-прогон не требуется и не разрешался.
