# Story E11.S10: Frontend narrative rendering components

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ✅ Завершено

## Контекст

Когда narrative JSON готов, frontend должен рендерить controlled narrative-first report, а не Markdown blob и не debug view. Дизайн должен сохранить E10 порядок: мягкий summary → смысловые разделы → CTA → типология/технические details collapsed.

## Что сделать

1. Создать `ReportNarrativePage` или adapter в existing report page.
2. Добавить components: Hero, NarrativeSection, EvidenceNotes disclosure, CareerCTA, FinalSummary.
3. Рендерить только разрешённые `section.id` и fallback для неизвестной секции.
4. Evidence notes показывать мягко/свернуто, не как debug block первого экрана.
5. TechnicalDetails и deterministic chart/radar/Model A оставить collapsed ниже narrative.
6. Сохранить glossary help для терминов.
7. Добавить mobile-first layout и regression checks на порядок секций.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/components/report/report-narrative-page.tsx` | New narrative page/root component |
| `frontend/src/components/report/narrative-section.tsx` | Generic section component |
| `frontend/src/components/report/career-cta.tsx` | Career CTA component |
| `frontend/src/components/report/evidence-notes.tsx` | Collapsed evidence notes |
| `frontend/src/lib/report/view-model.ts` | Narrative view model/normalizer |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Render narrative when present |
| `frontend/scripts/check-report-ux.mjs` | Order/technical disclosure checks |

## Критерии приёмки

- [x] Ready report renders `narrative.hero` before chart wheel, radar, Model A and raw scores.
- [x] Required Self sections appear in narrative-first order.
- [x] Career CTA appears after development section and does not replace Self content.
- [x] Evidence notes are visible via disclosure/details but not dominant in first viewport.
- [x] Unknown section id does not crash page and is logged/ignored with safe fallback.
- [x] Mobile layout is single-column and readable.
- [x] Frontend checks (`npm test`, `tsc`, `prettier`, `eslint`) pass.
