# Feature E10: Report UX Redesign — понятный self-report

## Цель

Перестроить страницу self-report из набора технических графиков в понятный продуктовый отчёт: пользователь сначала видит смысловой итог, астрологическую основу, жизненные проявления и практические рекомендации, и только потом — архетипы, соционику и раскрываемые технические детали расчёта.

Фича опирается на design direction: [`docs/design/report-ux-redesign.md`](../../design/report-ux-redesign.md).

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

- [ ] `/report/[profileId]` открывается для авторизованного пользователя и использует реальные данные API, а не placeholder.
- [ ] Первый viewport содержит header + human-readable executive summary без chart wheel, radar, Model A и raw scores.
- [ ] Порядок основных секций: summary → astrology foundation → life manifestations → practical recommendations → archetype → socionics → technical details.
- [ ] Астрологическая основа объясняет Солнце/Луну/ASC, стихии, модальности и ключевые факторы до любых derived typology-блоков.
- [ ] Жизненные проявления показывают минимум 4 области: мышление/решения, эмоции/восстановление, общение/отношения, работа/фокус.
- [ ] Практические рекомендации включают «что усилить», «что беречь», «что не делать через силу» и мини-чеклист на неделю.
- [ ] Архетипический профиль показывает primary archetype, human-readable description, light/shadow и confidence label; raw scores скрыты в details.
- [ ] Соционический профиль показывает probable type, нормальное название, простое объяснение и 3–5 прикладных выводов; Top-3/Model A/function radar скрыты в details.
- [ ] Technical details collapsed по умолчанию и содержит full chart wheel, tables, aspects, function strengths, radar, scores, confidence и evidence trail.
- [ ] Все обязательные термины имеют `TermHelp`/`GlossaryModal` с определением, значением в отчёте и примером.
- [ ] Каждый видимый график имеет текст «как читать»; графики без пояснения находятся только в advanced section.
- [ ] Для unknown/approximate birth time показан quality warning о влиянии времени рождения на дома/ASC и часть выводов.
- [ ] Mobile layout одноколоночный и не требует сравнения двух сложных диаграмм рядом.
- [ ] Добавлен deterministic regression check на порядок секций, glossary markers и advanced-only технические компоненты.
- [ ] `pnpm lint` и frontend checks проходят без ошибок.

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Report data contract и placeholders removal](S01-report-data-contract.md) | ⬜ Не начато |
| S02 | [Header и executive summary first viewport](S02-header-executive-summary.md) | ⬜ Не начато |
| S03 | [Астрологическая основа перед derived layers](S03-astrology-overview.md) | ⬜ Не начато |
| S04 | [Жизненные проявления и практические рекомендации](S04-manifestations-recommendations.md) | ⬜ Не начато |
| S05 | [Упрощённые archetype/socionics summary-блоки](S05-derived-profile-summaries.md) | ⬜ Не начато |
| S06 | [Technical details accordion и progressive disclosure](S06-technical-details-progressive-disclosure.md) | ⬜ Не начато |
| S07 | [Glossary / term help для терминов отчёта](S07-glossary-term-help.md) | ⬜ Не начато |
| S08 | [Mobile layout и UX regression checks](S08-mobile-regression-checks.md) | ⬜ Не начато |

## Проверка закрытия фичи

Минимальная проверка перед закрытием фичи:

```bash
cd frontend
pnpm lint
pnpm test
pnpm exec tsx scripts/check-report-ux-order.ts
```

Если полного test runner ещё нет, deterministic script обязателен: он должен проверять наличие обязательных секций, их порядок, glossary markers и то, что `NatalChart`, `FunctionRadar`, Model A/raw scores появляются только после секции «Технические детали расчёта».
