# Story E10.S02: Header и executive summary first viewport

**Feature:** [Report UX Redesign — понятный self-report](FEATURE.md)  
**Статус:** ⬜ Не начато

## Контекст

Первый экран должен отвечать на вопрос «это мой отчёт и что главное?», а не показывать сложные диаграммы. Эта story ограничена header и executive summary.

## Что сделать

1. Создать/обновить `ReportHeader`.
2. Показать имя/название профиля, дату, время и место рождения.
3. Показать quality notice для exact/approximate/unknown birth time.
4. Создать `ReportExecutiveSummary`.
5. Вывести 3–5 тезисов, главную тему карты, силу и зону внимания.
6. Убедиться, что в first viewport нет chart wheel, radar, Model A, raw scores.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Разместить header + summary первым viewport |
| `frontend/src/components/report/report-header.tsx` | Создать/обновить |
| `frontend/src/components/report/report-executive-summary.tsx` | Создать |
| `frontend/src/lib/report/*` | При необходимости добавить helpers для summary data |

## Критерии приёмки

- [ ] Первый viewport содержит header и executive summary.
- [ ] Birth data и quality notice видны до любых графиков.
- [ ] Summary содержит 3–5 понятных тезисов.
- [ ] Нет мистического тумана; формулировки конкретные и прикладные.
- [ ] Chart wheel/radar/Model A/raw scores не рендерятся в первом viewport.
- [ ] `pnpm lint` проходит.
