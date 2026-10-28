# BUG-50: Child content quality — расследование и исправление

## Статус

В работе. GitHub: `fixemer90-stack/Archemap#50`, P1. Пользователь разрешил исправление. Production-артефакты ещё не исправлены; исторические функциональные smoke не являются доказательством содержательной полезности отчёта.

Публичные сведения обезличены: идентификаторы владельца, ребёнка, отчётов, birth data, ответы анкеты и сырые payload не включены.

## Подтверждённый дефект

В production на application revision `886910321d1efcb189b8a2296dd5c947146e8b4f` сохранены два технически завершённых результата с одинаковыми narrative bodies. Публичный API возвращает `200` и `ready`.

- 15 предусмотренных разделов; 7 имеют narrative body, 8 — `not_applicable` без body.
- 21 claim содержит 3 уникальные фразы; одна общая рекомендация повторяется 15 раз.
- Расчёты родительского стиля, потребностей ребёнка и взаимодействия существуют, но содержательная проекция их обедняет.
- `how_to_use` и `child_interaction_needs` полностью совпадают; ownership раздела самостоятельности не использует имеющееся тематическое действие.
- Runtime настроен на включённый DeepSeek. Дословное копирование нельзя считать доказательством mock: его требуют prompt и validator.

Новых платных генераций во время расследования не выполняли. Браузерный screenshot-прогон расследования завершить не удалось по таймауту; он не засчитан как выполненная UI-проверка. Выводы подтверждены сохранёнными артефактами, публичным API, исходниками и независимым техническим аудитом.

## Первопричины

1. Средние оценки и разные наблюдения сводятся resolver-слоем к одному действию. Подготовка approved text теряет тему, измерение и причину.
2. Guidance Facts не используют сохранённые parent-style / child-needs scores как самостоятельный содержательный вход.
3. Prompt и validator требуют буквального копирования approved text и точного соединения claims, поэтому LLM не может восстановить потерянный контекст.
4. Широкие и пересекающиеся owned families дублируют разные разделы; тематические reference facts не заменяют отсутствующие owned facts.
5. `ready` проверяет завершение обработки, но не релевантность, межсекционные повторы и содержательное покрытие.

## Границы исправления

- Сохранять child-safety, caregiver-action framing, условия уверенности, privacy и authoritative lineage.
- Не понижать доказательные пороги ради заполнения всех разделов; обоснованные пропуски допустимы.
- Не исправлять качество минимальными word/sentence/token counts, длиной шаблонов или искусственными лимитами.
- Различимость должна происходить из поддержанных источниками тематических фактов, а не из косметического изменения одинаковых предложений.
- Новые семантики версионировать; чтение и replay неизменяемых исторических артефактов не должны применять к ним новый контракт задним числом.
- Продуктовое качество отделить от технического lifecycle. Ограниченный результат не должен выдавать безусловное сообщение о полноценной готовности; повторный платный вызов не является автоматическим обходом quality verdict.
- Не менять Plus, billing, pending payments, merchant credentials или чужие/соседние aggregates.

## Критерии завершения

- [x] RED-регрессия на обезличенный сценарий со средними оценками и различимыми наблюдениями воспроизведена до production-code изменения.
- [x] Поддержанные parent/child/interaction факты сохраняют содержательные различия до narrative output.
- [x] Ownership соответствует назначению разделов; нет потери тематического действия из-за несвязанного owned-family условия.
- [x] Сохранены отрицательные safety/privacy/lineage проверки и совместимость исторических контрактов.
- [x] Отдельный quality verdict обнаруживает повторяющиеся/неполезные результаты без произвольного требования заполнить все разделы.
- [x] Reader и PDF честно показывают ограничения качества, не раскрывают внутренние reason codes и не запускают новые платные попытки автоматически.
- [x] Targeted и широкие unit/integration/static/browser проверки пройдены на свежем diff; DB tests используют только disposable PostgreSQL/Redis.
- [x] Независимые spec/security/code-quality reviews выполнены, замечания устранены.
- [ ] Изменения опубликованы; точный CI проверен до runtime rollout.
- [ ] После безопасного rollout проверен реальный восстановленный artifact/API/reader/PDF; новые provider-вызовы выполняются только в разрешённом объёме.

## Проверки

### Reader: локальный verified slice (не production repair)

- RED: `npm exec playwright test tests/e2e/e22-child-quality.spec.ts -- --project=chromium-desktop --grep 'limited report quality'` — ожидаемая ошибка отсутствующего quality notice. DOM уже содержал сохранённый отчёт и безусловный статус «Отчёт готов», поэтому это не loading/auth ложноположительный результат.
- GREEN после последнего изменения тестов: `npm exec playwright -- test tests/e2e/e22-child-quality.spec.ts tests/e2e/e22-child-reader.spec.ts` — **24 passed**. Включены desktop/mobile, legacy quality absence, обычный `ready`, `limited`, отсутствие автоматической regenerate/payment операции и утечки raw reason code, overflow и Axe serious/critical. Дополнительно проверена ширина 820px; desktop/mobile/tablet screenshots осмотрены.
- Свежие scoped `eslint`, `tsc --noEmit --pretty false`, exact-path Prettier и `git diff --check` — PASS.
- `npm test` — все 15 существующих frontend UX/contract scripts PASS.
- Первый wrapper-run закончился на несуществующем `npm run test:ux`; реальный script обнаружен в package.json и выполнен как `npm test`. Эта ошибка команды не засчитана как дефект продукта.
- Это synthetic browser fixtures с реальными компонентами, не восстановленный пользовательский production-отчёт. Изменение сообщения не закрывает upstream дефект.
- Независимый frontend review `deleg_201e9156` — APPROVED, без блокирующих security/logic/spec замечаний. Неблокирующие рекомендации усилены: exact saved body/PDF href, отсутствие текстов из обоих technical section arrays, отсутствие create/retry в конце теста. После этого отдельный quality suite — **6 passed**, scoped ESLint/TypeScript/Prettier — PASS.
- Frontend-only slice сохранён отдельным commit `52f49262bb903e88996673d4181cc53df6fe03b0`; backend и docs этим commit не затрагивались. Push/deploy и закрытие issue на этом этапе не заявляются.

### Повторная проверка при продолжении исправления

- Рабочее дерево продолжено с frontend commit `52f49262bb903e88996673d4181cc53df6fe03b0`; backend-кандидат на этом этапе ещё не закоммичен. Удалённый `main` при проверке — `147b5ba270f6e4313689af832507ee2fdbce274d`, issue #50 открыт.
- Свежий browser-прогон: `npm exec playwright -- test tests/e2e/e22-child-quality.spec.ts tests/e2e/e22-child-reader.spec.ts` — **24 passed (3.9m)**, desktop и mobile. Это fixtures, не production artifact repair.
- Свежие `npm test` (15 UX/contract scripts), `npm exec tsc -- --noEmit --pretty false` и scoped ESLint четырёх frontend-файлов commit `52f4926` — PASS.
- Backend передан на повторную проверку исходников, broad unit/static и targeted persisted version/PDF checks; отдельный независимый spec/security reviewer работает без доступа к production данным. Результаты будут внесены после завершения, а не по handoff-заявлению.

### Backend: проверенный versioned repair

- Backend commit `594a1ce1c9f1d32f7e8ce62e4473244ee869ab74`: новые полные генерации используют Guidance Facts/input/prompt/assembly v2. Исторические v1 payload/hash/read/replay и narrative-only retry сохранены; исправление старого отчёта требует явной новой полной генерации, а не скрытой перезаписи.
- В содержательный вход включены сохранённые parent-style, child-needs и interaction indicators. Тематические действия и условия неопределённости сохраняются; средние interaction scores не объявляются сильными сторонами родителя.
- Дополнительный RED выявил потерю questionnaire-derived `transitions` actions в `conscious_adjustments`. Исправлены family-aware projection/citation/safety ownership; регрессии проверяют сохранённые evidence refs и отклонение unrelated-topic citations.
- Свежие backend-проверки после последнего изменения: `pytest tests/unit -q` — **1189 passed**; `pytest tests/unit/test_child/test_content_v2.py -q` — **22 passed**; persisted versions/PDF/source/lifecycle batch — **7 passed**. Только disposable PostgreSQL/Redis, `LLM_ENABLED=false`, synthetic/counting providers; полный исторический integration sweep не заявляется.
- Whole-backend `ruff check .`, `ruff format --check .` (**484 files**), `mypy .` (**483 source files**) — PASS. Существующие предупреждения WeasyPrint и AsyncMock не являются новыми ошибками.
- Независимый read-only spec/security/code review `deleg_f3a0619a`, task 2 — **APPROVED**, **57 passed** pure units и 18 граничных profile-сценариев без ошибок. Он предшествовал последнему точечному transition-исправлению; это изменение дополнительно проверено родительским агентом и persisted regression.
- Reader и PDF получают одинаковую quality-проекцию. Проверка повторов нормализует точные approved text/body повторы; универсальное распознавание парафраз не заявляется. Обоснованные пропуски остаются допустимыми и честно обозначаются.

CI и production repair будут дополнены фактическими результатами. Исправление всего BUG-50 пока не заявляется завершённым; новых production provider-вызовов и перезаписи исторических артефактов не было.
