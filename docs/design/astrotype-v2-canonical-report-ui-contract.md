# Astrotype v2 canonical report UI contract

Date: 2026-08-04

Canonical visual source:

- `docs/design/astrotype-v2-infographic-db-report-sample.html`

This sample overrides the existing product report/dashboard design for v2. Existing frontend files may be inspected for auth/session/API patterns, but they are not the visual target.

---

## Required page order

The v2 ready-state report reader must render in this order:

1. Hero cover
2. Narrative sections
3. Lower deterministic calculation layer

Do not start with dashboard metrics, side navigation, archetype cards, socionics result, or technical/debug accordion.

---

## Hero cover

Required traits from the sample:

- full-width dark report card;
- small gold eyebrow: `Astrotype v2 · натальный отчёт`;
- main title: `Натальный портрет личности` or report title from data;
- lead paragraph in large readable text;
- second explanatory paragraph;
- compact action pills/buttons:
  - readiness/state, e.g. `Полный отчёт готов` or deterministic/partial equivalent;
  - `Карта и расчёт ниже`;
  - PDF preview/download action.

The hero is a report cover, not a dashboard header.

---

## Narrative section cards

Required structure:

- large dark rounded card per section;
- section eyebrow with numeric order, e.g. `01 · ядро личности`;
- strong h2 heading;
- small right-aligned section tag/subtitle;
- main prose column with several paragraphs;
- right-side aside card with short bullets;
- on mobile, aside stacks below prose.

Current canonical sections in the sample:

1. `Ядро личности`
2. `Мышление и восприятие`
3. `Эмоциональная регуляция`
4. `Воля и действие`
5. `Близость и отношения`
6. `Вектор роста`

LLM progress/partial states may show missing sections as loading/queued cards, but the ready-state layout must remain the same.

---

## Lower deterministic calculation layer

This layer appears after the narrative prose. It is compact report support material, not a separate analytics dashboard.

Required visible blocks:

1. `Карта и ключевые показатели`
   - Асцендент
   - MC
   - Управитель ASC

2. `Положения планет`
   - planet
   - sign
   - house
   - degree
   - retrograde marker
   - key sampled aspects

3. `Баланс стихий` and `Баланс модальностей`
   - compact horizontal bars
   - percent values

4. `Акцент домов`
   - vertical house bars
   - labelled top house accent cards

5. `Сеть ключевых аспектов`
   - circular/network view
   - resource/tension styling

6. `Ключевые аспекты`
   - pair
   - aspect
   - orb
   - type pill

7. `Расчётные акценты карты`
   - house mode
   - hemispheres/orientation
   - quadrants
   - aspect profile

---

## Explicitly not v2 UI

Do not render these in the v2 MVP reader:

- socionics result;
- Model A;
- function-strength radar/profile;
- archetype profile summary;
- career CTA in Self report;
- theme maps;
- standalone “factual basis” dashboard/cards;
- most-aspected planet rankings;
- legacy `TechnicalDetailsAccordion` as the main calculation UX;
- existing `/report/[profileId]` layout as the visual target.

---

## Frontend implementation implications

When V2-E11 starts:

- create dedicated v2 report components instead of adapting legacy report components in place;
- reuse auth/session/API helpers only where neutral;
- add a visual/DOM regression script that checks for sample-specific markers:
  - hero eyebrow;
  - narrative section order;
  - calculation layer after narrative;
  - no `socionics`, `function_strengths`, `Model A` text;
  - no legacy dashboard metric/header layout.

Suggested component names:

- `V2ReportReader`
- `V2ReportHero`
- `V2NarrativeSectionCard`
- `V2CalculationLayer`
- `V2PlanetPositionsTable`
- `V2BalanceBars`
- `V2HouseEmphasis`
- `V2AspectNetwork`
- `V2KeyAspectsTable`
- `V2CalculationMatrix`
