# Feature E10: Report UX Redesign — понятный self-report

## Цель

Перестроить страницу self-report из набора технических графиков в понятный продуктовый отчёт: пользователь сначала видит смысловой итог, астрологическую основу, жизненные проявления и практические рекомендации, и только потом — архетипы, соционику и раскрываемые технические детали расчёта.

Фича опирается на design direction: [`docs/design/report-ux-redesign.md`](report-ux-redesign.md).

## Проблема

Текущая report page показывает данные, но слишком рано выводит сложные элементы: chart wheel, таблицы планет/домов/аспектов, function radar, Model A, проценты confidence/scores и соционические аббревиатуры. Для обычного пользователя это выглядит как debug view и плохо отвечает на вопрос: «что это значит для меня?».

Новый отчёт должен идти от понятного к сложному:

1. Header с данными рождения и качеством расчёта.
2. Executive summary — 3–5 выводов простым языком.
3. Астрологическая основа как источник интерпретации.
4. Жизненные проявления.
5. Практические рекомендации.
6. Архетипический профиль.
7. Соционический профиль.
8. Технические детали / evidence trail в collapsed advanced section.

## Зависимости

- `E3 Chart Engine` ✅ — расчёт натальной карты, планет, домов, аспектов и normalized features.
- `E4 Rules & Content` 🟡 — правила/шаблоны для текстовых интерпретаций и socionics/archetype outputs.
- `E5 Products & Reports` 🟡 — report API и структура данных отчёта.
- `E9 Frontend Self Report` 🟡 — существующая report page, `NatalChart`, `SocionicsResult`, auth/dashboard shell.
- `docs/design/report-ux-redesign.md` — утверждённое направление UX.

## Scope

### Входит

- Narrative-first layout страницы `/report/[profileId]`.
- Executive summary и прикладные текстовые блоки до графиков.
- Астрологическая основа как первый source/domain layer.
- Отдельные summary-компоненты для архетипов и соционики.
- Progressive disclosure для raw math, full chart wheel, radar, Model A breakdown и evidence.
- Подсказки для терминов через modal/drawer/popover.
- Mobile-first layout без соседних сложных диаграмм.
- Regression checks на порядок секций, glossary markers и advanced-only технические компоненты.

### Не входит

- Изменение формул расчёта натальной карты, архетипов или соционики.
- Удаление debug/evidence данных из API.
- Полный редактор контента/CMS.
- Платные отчёты Love/Child/Career — только Self-report.

## UX-принципы

- Первый экран — summary, не chart wheel/radar/raw scores.
- Астрология идёт раньше архетипов и соционики, потому что это source layer расчёта.
- Практические выводы расположены выше типологических и технических блоков.
- Любой график имеет пояснение «как читать» или находится в technical details.
- Scores/confidence показываются с человеческой меткой: «высокая уверенность», «средняя выраженность», а не только `78.4%`.
- Термины не используются без подсказки: натальная карта, Солнце, Луна, Асцендент, дом, аспект, орб, стихия, модальность, архетип, соционический тип, Model A, confidence, evidence trail.
- Математика не удаляется, а переносится в advanced disclosure.

## Критерии приёмки фичи

- [x] `/report/[profileId]` открывается для авторизованного пользователя и использует реальные данные API, а не placeholder.
- [x] Первый viewport содержит header + human-readable executive summary без chart wheel, radar, Model A и raw scores.
- [x] Порядок основных секций: summary → astrology foundation → life manifestations → practical recommendations → archetype → socionics → technical details.
- [x] Астрологическая основа объясняет Солнце/Луну/ASC, стихии, модальности и ключевые факторы до любых derived typology-блоков.
- [x] Жизненные проявления показывают минимум 4 области: мышление/решения, эмоции/восстановление, общение/отношения, работа/фокус.
- [x] Практические рекомендации включают «что усилить», «что беречь», «что не делать через силу» и мини-чеклист на неделю.
- [x] Архетипический профиль показывает primary archetype, human-readable description, light/shadow и confidence label; raw scores скрыты в details.
- [x] Соционический профиль показывает probable type, нормальное название, простое объяснение и 3–5 прикладных выводов; Top-3/Model A/function radar скрыты в details.
- [x] Technical details collapsed по умолчанию и содержит full chart wheel, tables, aspects, function strengths, radar, scores, confidence и evidence trail.
- [x] Все обязательные термины имеют `TermHelp`/`GlossaryModal` с определением, значением в отчёте и примером.
- [x] Каждый видимый график имеет текст «как читать»; графики без пояснения находятся только в advanced section.
- [x] Для unknown/approximate birth time показан quality warning о влиянии времени рождения на дома/ASC и часть выводов.
- [x] Mobile layout одноколоночный и не требует сравнения двух сложных диаграмм рядом.
- [x] Добавлен deterministic regression check на порядок секций, glossary markers и advanced-only технические компоненты.
- [x] `npx eslint .`, `npx prettier --check .`, `npx tsc --noEmit --pretty false` и `npm test` проходят без ошибок.

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Report data contract и placeholders removal](S01-report-data-contract.md) | ✅ Готово |
| S02 | [Header и executive summary first viewport](S02-header-executive-summary.md) | ✅ Готово |
| S03 | [Астрологическая основа перед derived layers](S03-astrology-overview.md) | ✅ Готово |
| S04 | [Жизненные проявления и практические рекомендации](S04-manifestations-recommendations.md) | ✅ Готово |
| S05 | [Упрощённые archetype/socionics summary-блоки](S05-derived-profile-summaries.md) | ✅ Готово |
| S06 | [Technical details accordion и progressive disclosure](S06-technical-details-progressive-disclosure.md) | ✅ Готово |
| S07 | [Glossary / term help для терминов отчёта](S07-glossary-term-help.md) | ✅ Готово |
| S08 | [Mobile layout и UX regression checks](S08-mobile-regression-checks.md) | ✅ Готово |

## Проверка закрытия фичи

Минимальная проверка перед закрытием фичи:

```bash
cd frontend
npx eslint .
npx prettier --check .
npx tsc --noEmit --pretty false
npm test
```

Если полного test runner ещё нет, deterministic script обязателен: он должен проверять наличие обязательных секций, их порядок, glossary markers и то, что `NatalChart`, `FunctionRadar`, Model A/raw scores появляются только после секции «Технические детали расчёта».
