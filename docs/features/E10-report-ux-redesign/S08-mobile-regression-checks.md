# Story E10.S08: Mobile layout и UX regression checks

**Feature:** [Report UX Redesign — понятный self-report](FEATURE.md)  
**Статус:** ✅ Готово

## Контекст

Даже если layout собрать правильно один раз, его легко сломать последующими изменениями. Эта story фиксирует mobile UX и добавляет deterministic regression check на информационную архитектуру.

## Что сделать

1. Проверить mobile layout: одна колонка, без соседних сложных диаграмм.
2. Убедиться, что accordion/touch targets удобны на mobile.
3. Расширить deterministic script/test `check-report-ux.mjs`.
4. Проверять наличие обязательных headings.
5. Проверять порядок headings.
6. Проверять glossary markers для ключевых терминов.
7. Проверять, что advanced-only markers (`NatalChart`, `FunctionRadar`, `Model A`, raw scores/evidence markers) появляются только после heading «Технические детали расчёта».
8. Проверять отсутствие старого chaotic first-screen layout marker, если он был в коде.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Проверить responsive layout markers/classes |
| `frontend/scripts/check-report-ux.mjs` | Расширить deterministic regression script |
| `frontend/package.json` | Добавить script command, если принято в проекте |
| `frontend/src/components/report/*` | Добавить stable headings/test markers при необходимости |

## Критерии приёмки

- [x] Mobile layout одноколоночный.
- [x] На mobile нет двух сложных диаграмм рядом.
- [x] Technical accordion usable на touch.
- [x] Regression check проверяет обязательные headings.
- [x] Regression check проверяет порядок секций.
- [x] Regression check проверяет glossary markers.
- [x] Regression check падает, если advanced-only components появляются до technical details.
- [x] Команда проверки задокументирована и выполняется.
- [x] `npx eslint .`, `npx prettier --check .` и `npx tsc --noEmit --pretty false` проходят без ошибок.
- [x] `npm test` (`node scripts/check-report-ux.mjs`) проходит.
