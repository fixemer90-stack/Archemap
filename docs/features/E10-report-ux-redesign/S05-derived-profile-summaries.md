# Story E10.S05: Упрощённые archetype/socionics summary-блоки

**Feature:** [Report UX Redesign — понятный self-report](FEATURE.md)  
**Статус:** ⬜ Не начато

## Контекст

Архетипы и соционика остаются важными, но должны быть дополнительными interpretation layers после summary, astrology и практических блоков. Эта story создаёт простые summary-представления без raw percentages и Model A в основном потоке.

## Что сделать

1. Создать `ArchetypeProfileSummary`.
2. Показать primary archetype, human-readable description, 2–3 проявления, light/shadow, textual confidence label.
3. Создать `SocionicsProfileSimple`.
4. Показать probable type, нормальное название, простое объяснение и 3–5 прикладных выводов.
5. Raw scores, Top-3 types, Model A и function radar не показывать в этих summary-компонентах.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/components/report/archetype-profile-summary.tsx` | Создать |
| `frontend/src/components/report/socionics-profile-simple.tsx` | Создать |
| `frontend/src/lib/report/score-labels.ts` | Helper для labels confidence/scores |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Разместить после рекомендаций |

## Критерии приёмки

- [ ] Archetype summary показывает primary archetype без таблицы raw scores.
- [ ] Confidence отображается как текстовая метка, не голый процент.
- [ ] Socionics summary объясняет тип простыми словами.
- [ ] Top-3, Model A и function radar не отображаются в основном socionics summary.
- [ ] Archetype/socionics расположены после рекомендаций.
- [ ] Helper score labels покрыт тестом или deterministic check.
- [ ] `pnpm lint` проходит.
