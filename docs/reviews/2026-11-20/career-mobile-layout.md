# Career: responsive reader layout repair

Статус: локальное исправление и независимый review завершены; публикация, CI и production-приёмка ещё не завершены.

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
- [ ] Изменения опубликованы; exact-SHA CI завершён.
- [ ] Обновлён только frontend; остальные семь контейнеров и приватная конфигурация сохранены.
- [ ] Native production smoke без mocks подтвердил исправление; сохранённые отчёты не изменились, новых генераций нет.

Backend, API, генераторы, данные отчётов и провайдеры в этом исправлении не меняются. Новый платный LLM-прогон не требуется и не разрешался.
