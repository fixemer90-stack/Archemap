# BUG-50: Child content quality — расследование и исправление

## Статус

В работе. GitHub: `fixemer90-stack/Archemap#50`, P1. В production работает content-v3 revision `e2a2f76`; дополнительная разрешённая полная real-DeepSeek генерация создала core version 4, но завершилась `narrative_failed`: раздел `praise_recognition` отклонён с `child_narrative_validation_failure`. В десяти сохранённых bodies нет повторяющихся полных предложений. Runtime, artifact/API/desktop/mobile/PDF и сохранность прежних данных проверены; родительский агент независимо повторил read-only проверку. Это доказательство безопасной деградации, не успешной полной генерации. BUG-50 не закрыт; новых платных попыток без отдельного разрешения нет.

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
- [x] Отдельный quality verdict обнаруживает повторяющиеся/неполезные результаты без произвольного требования заполнить все разделы. V3 регрессии проверяют повторяющиеся предложения и смысловые оговорки внутри разных claims; десять успешных production bodies не содержат повторяющихся полных предложений. Успешное завершение всей real-provider генерации остаётся отдельным открытым условием.
- [x] Reader и PDF честно показывают ограничения качества, не раскрывают внутренние reason codes и не запускают новые платные попытки автоматически.
- [x] Targeted и широкие unit/integration/static/browser проверки пройдены на свежем diff; DB tests используют только disposable PostgreSQL/Redis.
- [x] Независимые spec/security/code-quality reviews выполнены, замечания устранены.
- [x] Изменения опубликованы; точный CI проверен до runtime rollout.
- [x] После безопасного rollout проверен реальный восстановленный artifact/API/reader/PDF; новые provider-вызовы выполняются только в разрешённом объёме. Для V3 подтверждено чтение деградированного результата, не успешное завершение генерации.
- [ ] Полная real-provider генерация нового контракта завершается без failed sections; проверен окончательный сохранённый результат. Сейчас `praise_recognition` отклонён валидатором; новый платный retry не разрешён.

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

### Production repair и независимый readback — 2026-10-29

- Разрешение: после запроса на выкладку и одну полную платную регенерацию владелец поручил «заканчивай тогда S22 и проверяй баг»; в контексте это E22 Child. Выполнена **одна** принятая полная генерация, **11 real DeepSeek section calls**, по одной попытке. Дополнительных diagnostic/provider-generations не было.
- Exact source/runtime: `3e3ee67b68e9ea53cb6e467b5596d8a6c75781b9`, CI `40782166066` — **8/8 success** до упаковки. Образы из clean git archive, source identity **308 Python files** в каждом из четырёх consumers, migration delta **0**, head `a8b9c0d1e2f3`. API/worker/scheduler/frontend operational readiness и public HTTPS health — PASS.
- Production preflight, drain и frozen backup/restore: **66 public tables**, schema/rows равны, источник не изменён; временная restore DB удалена с identity guard и отсутствие прочитано обратно. Backup/rollback images сохранены. Остальные **17 containers**, PostgreSQL/Redis/Caddy и staging identities сохранены; maintenance снят, Caddy config равен baseline.
- Новый **core version 3**, `child-guidance-facts-v2` / `child_report_narrative_v2`, lifecycle `ready`, **39.120948 s**. **11/11 различных bodies**, **35/35 различных claims**, исходная одинаковая общая рекомендация исчезла. Четыре обоснованных пропуска: `natural_contact`, `friction_zones`, `conflict_cycle`, `not_personal`; failed/missing sections отсутствуют. Product quality честно `limited`, не безусловное принятие текста.
- Старые core versions 1/2 и все **109 preexisting owned Child rows** сохранили hashes/значения. Questionnaire предыдущей local date предварительно обновлён через канонические API с сохранением всех восьми structured answers, прежнего stage/question keys и immutable completed session. Первый admission 404 не создал generation; idempotency key сохранён до единственного 202.
- Public API, native browser **1440×1000 / 390×844**, без API mocks: 15 section headings, все 11 точных bodies, четыре пояснения omission, limited notice, отсутствие raw reason codes/безусловного ready/overflow/page errors и Child mutations. Нативная PDF-ссылка сработала в обоих viewports.
- API/browser PDF bytes совпали: **7 pages, 27,348 bytes**, SHA256 `1379394ce70802b331ad4f4b2083fa48dd15d949fac3e2f14650b34c671fdd53`. Все 11 bodies и 15 headings сохранены. PDF показывает общую limitation copy; индивидуальные fallback-пояснения четырёх пропусков, имеющиеся в web, в PDF отсутствуют. Это не потеря сохранённых bodies, но не следует объявлять идентичность всех fallback-надписей.
- Родительский агент выполнил свежий read-only `readback-v2.py`: **PASS**, заново проверены running source/images/provider/markers/readiness, backup, отсутствие restore DB, старые строки, точный repair key и paid accounting. Повторный независимый разбор полученного public payload подтвердил **11 уникальных bodies**, caveat **26 повторов**, middle-range uncertainty **18 повторов**. Representative reader/PDF screenshots осмотрены; текст не обрезан, но формульное повторение заметно.
- Private evidence: `/opt/astrotype-production/evidence/3e3ee67b68e9ea53cb6e467b5596d8a6c75781b9/`; active release выбран `.deploy-release`, observability overlays остаются под прежним `8869103` evidence, new images override — под `3e3ee67`. Полные идентификаторы/данные/токены не публикуются.

### Проверка исполняемых operator docs после runtime repair

Документационные commits `7fba4eb` / `3389441` уточнили реальное production evidence и drain/identity gates. CI `40800235098` на `3abeab2` выявил девять unit failures: тест извлекал первый Bash fence из backup SOP, которым после добавления drain стал inspection-пример. Это воспроизведено локально (**9 failed, 2 passed**), не failure production-пайплайна. Исправлен семантический выбор уникального backup lifecycle, harness использует отдельный `OPERATOR_SHA` и явный `DRAIN_CONFIRMED=true`. Добавлены три negative cases: отсутствующее/ложное/неверно-регистровое подтверждение не допускает ни одного внешнего действия. После последнего изменения полный backend unit suite — **1192 passed**, Ruff/format/mypy — PASS. Docs проверены Prettier, девять shell fences — `bash -n`, embedded Python — compile, три JSON-примера и пять локальных ссылок — PASS. Это проверка безопасности инструкции и тестового harness, не полное независимое live исполнение S16.

### Финальное content-v3 исправление — локальная проверка 2026-10-30

Backend candidate `7c154343cdabbae0cf215aa0fd287caf39fd4944` поверх numeric usage commit `b05c19d` вводит явные Guidance Facts/input/prompt/assembly v3. Общая методология размещена один раз в `how_to_use`, resource caveat — один раз в своём разделе. Каждый показатель сохраняет свою размерность, сторону взаимодействия, положение на шкале, локальную неопределённость и конкретный вопрос для наблюдения. Все 26 source dimensions и transitions сохранены; low-confidence extreme interaction indicators не пропадают. Это generation-time composition, не глобальная перезапись старого текста или косметическая ротация синонимов.

Семантика V1/V2 и frozen facts/input/prompt/assembly hashes остаются version-pinned; unsupported versions fail closed. Quality v3 проверяет повторяющиеся предложения и общие смысловые оговорки внутри разных claims, а не только целые bodies. PDF дополнительно показывает ту же `not_applicable` fallback-надпись, что и reader, без замены сохранённого body. Для V3 attempted calls сохраняются только численные request-scoped usage observations; отсутствующие токены не превращаются в нулевую стоимость, unknown-outcome intents могут законно не иметь usage.

Родительский агент после commit заново выполнил полный `pytest tests/unit -qq` — **1241 passed**, whole-backend Ruff/format/mypy — PASS; реальный disposable PostgreSQL versions/PDF batch — **4 passed** с включёнными durability settings. Отдельный implementer-прогон lifecycle/context/retry — **73 passed**, после чего disposable settings восстановлены и прочитаны `on/on/on`. Это SQL/lifecycle proof, не crash/power-loss qualification. Два независимых spec/security review запущены на точном `7c15434`; окончательные verdict и новые CI/runtime proof будут записаны после результатов. Новых provider-вызовов на этом этапе не было.

### Production content-v3 — 2026-10-30

- Два независимых review точного `7c15434` завершились **APPROVED**, без блокирующих замечаний; после review изменились только docs и объявленная PDF test dependency/lockfile. Exact release `e2a2f76a5e3aa2188da5828f54b7ff5e657d660f`, CI `40964497273` — восемь jobs success. Все пять application services работают на этом revision; source identity проверена по **312 Python files** в каждом Python consumer.
- Родительский агент повторно выполнил **1241 unit tests**, targeted V2/V3/usage batch — **70 passed**, whole-backend Ruff/format/mypy — PASS. Это локальные проверки с `LLM_ENABLED=false`, не дополнительные provider calls.
- Ровно одна дополнительно согласованная full real-DeepSeek генерация создала core version **4**: **10 ready**, **4 not_applicable**, **1 failed**. Раздел `praise_recognition` получил `child_narrative_validation_failure`; весь результат `narrative_failed`. Конкретный исходный validator predicate по сохранённой диагностике не установлен; raw response не сохранён. Ни второй full request, ни section retry не выполнены.
- Успешные bodies: **10/10 уникальны**, claims **34/34 уникальны**, повторяющихся полных нормализованных предложений нет. Общие методологические оговорки размещены не более одного раза. Это подтверждает устранение наблюдавшихся повторов в успешной части, но не полное содержательное принятие отчёта.
- Реальные public API/native desktop **1440×1000** и mobile **390×844**/PDF проверены без mocks. Все десять bodies сохранены; четыре evidence omissions и failed-section explanation показаны честно. Нет безусловного ready, raw reason codes, overflow, JS page errors или Child mutation requests; Retry не нажат. API/desktop/mobile PDF одинаковы: **7 pages, 27,547 bytes**, SHA256 `9722bfc7c32f393ec2bdd74021be7fccb9e02b6e7af189e73c76994b5fd0b189`.
- Backup/restore проверил все **66 public tables**; disposable restore DB удалена, отсутствие прочитано. Все **168 preexisting owned Child rows**, исторические versions **1–3**, **49 non-Child tables** и **17 protected containers** сохранены. Maintenance снят; production health/consumers/ingress проверены.
- Usage учтён для всех **11 HTTP attempts**, включая validation-failed section: prompt **13,943**, completion **6,397**, total **20,340 tokens**, одна попытка на раздел. Денежная стоимость и p95 не измерены.
- Родительский агент независимо выполнил remote `independent-readback-final.py`: exit **0**, `passed:true` только для runtime/readability/preservation/budget, **`real_provider_acceptance:false`**, `report_status:narrative_failed`; один durable repair key, ноль nonterminal generations и unknown-provider outcomes. Private evidence: `/opt/astrotype-production/evidence/e2a2f76a5e3aa2188da5828f54b7ff5e657d660f/`.

### Текущая граница закрытия

Повторяющиеся caveat-предложения устранены versioned V3 composition, а исторические V1/V2 остаются неизменными. Открыт конкретный blocker: validation-rejected `praise_recognition` и отсутствие успешного полного real-provider результата. Диагностика продолжается offline/read-only; нельзя объявлять неизвестный predicate установленным или ослаблять safety ради ready.

Обе согласованные full repair генерации израсходованы — одна для V2 и одна для V3. Новые provider calls требуют отдельного разрешения. BUG-50 и полный E22 остаются открытыми; statistical budget/load qualification не выполнена.
