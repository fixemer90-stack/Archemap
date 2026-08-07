# Story E10.S03: Астрологическая основа перед derived layers

**Feature:** [Report UX Redesign — понятный self-report](Archemap/docs/features/v1/E10-report-ux-redesign/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Астрология — source layer self-report. Пользователь должен сначала понять, из чего следует интерпретация, и только потом видеть архетипы/соционику.

## Что сделать

1. Создать `AstrologyOverview`.
2. Показать Солнце, Луну и ASC, если ASC доступен.
3. Показать доминирующие стихии и модальности.
4. Показать 2–4 ключевых аспекта/фактора только если они реально используются в тексте.
5. Для каждого фактора дать короткое «что это значит».
6. Для approximate/unknown birth time явно пометить, какие выводы менее точны.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/components/report/astrology-overview.tsx` | Создать |
| `frontend/src/lib/report/*` | Helpers/adapters для astrology overview |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Разместить section после summary и до archetype/socionics |

## Критерии приёмки

- [x] `AstrologyOverview` идёт сразу после executive summary.
- [x] Солнце/Луна/ASC отображаются с человеческим объяснением.
- [x] Стихии и модальности объяснены без сырых таблиц.
- [x] Неиспользуемые в тексте аспекты не засоряют основной блок.
- [x] ASC/дома корректно помечены как менее точные при unknown/approximate birth time.
- [x] Архетипы и соционика расположены ниже astrology overview.
- [x] `npx eslint .`, `npx prettier --check .` и `npx tsc --noEmit --pretty false` проходят без ошибок.
