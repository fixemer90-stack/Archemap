# Story E10.S08: Mobile layout и UX regression checks

**Feature:** [Report UX Redesign — понятный self-report](FEATURE.md)  
**Статус:** ⬜ Не начато

## Контекст

Даже если layout собрать правильно один раз, его легко сломать последующими изменениями. Эта story фиксирует mobile UX и добавляет deterministic regression check на информационную архитектуру.

## Что сделать

1. Проверить mobile layout: одна колонка, без соседних сложных диаграмм.
2. Убедиться, что accordion/touch targets удобны на mobile.
3. Добавить deterministic script/test `check-report-ux-order`.
4. Проверять наличие обязательных headings.
5. Проверять порядок headings.
6. Проверять glossary markers для ключевых терминов.
7. Проверять, что advanced-only markers (`NatalChart`, `FunctionRadar`, `Model A`, raw scores/evidence markers) появляются только после heading «Технические детали расчёта».
8. Проверять отсутствие старого chaotic first-screen layout marker, если он был в коде.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Проверить responsive layout markers/classes |
| `frontend/scripts/check-report-ux-order.ts` | Создать deterministic regression script |
| `frontend/package.json` | Добавить script command, если принято в проекте |
| `frontend/src/components/report/*` | Добавить stable headings/test markers при необходимости |

## Критерии приёмки

- [ ] Mobile layout одноколоночный.
- [ ] На mobile нет двух сложных диаграмм рядом.
- [ ] Technical accordion usable на touch.
- [ ] Regression check проверяет обязательные headings.
- [ ] Regression check проверяет порядок секций.
- [ ] Regression check проверяет glossary markers.
- [ ] Regression check падает, если advanced-only components появляются до technical details.
- [ ] Команда проверки задокументирована и выполняется.
- [ ] `pnpm lint` проходит.
- [ ] `pnpm exec tsx scripts/check-report-ux-order.ts` проходит.
