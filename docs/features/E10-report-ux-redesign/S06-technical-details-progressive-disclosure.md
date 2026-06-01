# Story E10.S06: Technical details accordion и progressive disclosure

**Feature:** [Report UX Redesign — понятный self-report](FEATURE.md)  
**Статус:** ⬜ Не начато

## Контекст

Математику, evidence и debug-графики нельзя удалять: они нужны для доверия, проверки и advanced users. Но они не должны быть основным интерфейсом.

## Что сделать

1. Создать `TechnicalDetailsAccordion` collapsed по умолчанию.
2. Перенести внутрь full chart wheel, planets/houses/aspects tables, function strengths, function radar, Model A breakdown, Top-3 socionics, scores/confidence, evidence trail.
3. Оставить существующие `NatalChart` и `SocionicsResult` как advanced components.
4. Добавить пояснение «как это читать» для графиков, если они видимы внутри advanced section.
5. Убедиться, что technical details идут последней крупной секцией.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/components/report/technical-details-accordion.tsx` | Создать |
| `frontend/src/components/chart/natal-chart.tsx` | Использовать/адаптировать для advanced section |
| `frontend/src/components/chart/socionics-result.tsx` | Использовать/адаптировать для advanced section |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Переместить technical UI в конец |

## Критерии приёмки

- [ ] Technical details collapsed по умолчанию.
- [ ] Full chart wheel, raw tables, radar, Model A, Top-3, raw scores и evidence находятся только внутри technical details.
- [ ] Основной report flow читается без открытия technical details.
- [ ] Графики внутри advanced имеют пояснение «как читать».
- [ ] `NatalChart` и `SocionicsResult` не используются как первый экран.
- [ ] `pnpm lint` проходит.
