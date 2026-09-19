# S11: Career report reader и PDF

## Статус

🟡 Reader/PDF реализованы; visual parity browser smoke остаётся открытым

## Контекст

Текущий Career reader отражает legacy rules output. Target reader должен быть narrative-first, объяснять scores простым языком и сохранять одинаковую структуру web/PDF.

Канонический дизайн-образец: [`../../design/astrotype-career-report-sample.html`](../../design/astrotype-career-report-sample.html). Desktop и mobile PNG рядом с HTML используются как preview, но HTML остаётся источником визуального контракта.

## Что сделать

1. Создать Career-specific view model из persisted assembled payload.
2. Выстроить порядок: summary → work style → strengths → decisions → leadership → environment → risks → archetypes → role families → paths → technical basis.
3. Показать Top dimensions с коротким практическим объяснением; score не изображать как оценку «хорошо/плохо».
4. Confidence раскрывать через тон/подсказку, а не через псевдонаучную точность по умолчанию.
5. Contradictions показывать как полезные развилки, например capability vs motivation.
6. Роли/профессии снабдить уровнями strong/possible/context-dependent и основаниями.
7. Technical/evidence слой сделать вторичным и раскрываемым.
8. Сгенерировать PDF из того же report/view-model contract.
9. Поддержать loading секций, deterministic-only и narrative-failed состояния.

## Видимые секции MVP

1. Ваш профессиональный профиль
2. Как вы работаете
3. Сильные стороны
4. Стиль принятия решений
5. Лидерство и влияние
6. Оптимальная рабочая среда
7. Что может снижать эффективность
8. Профессиональные архетипы
9. Подходящие типы ролей
10. Возможные карьерные траектории

## Критерии приёмки

- [x] Reader не использует legacy `generated_report` payload.
- [x] Web/PDF читают один persisted source и имеют один порядок секций.
- [x] Scores объяснены без good/bad ranking.
- [x] Profession examples сформулированы условно, без назначения.
- [x] Contradictions и context constraints не теряются.
- [x] Deterministic-ready reader полезен до завершения LLM.
- [x] Narrative failure не скрывает deterministic content.
- [ ] Mobile, print/PDF, typography и whole-word tooltips проверены.
- [x] Canonical HTML sample и desktop/mobile previews созданы.
- [ ] Реальный reader проходит visual parity smoke относительно sample.

## Реализация и проверка

- `/products/career/report/[reportId]` читает progressive persisted payload `/api/v1/career/reports/{report_id}` без legacy `generated_report`.
- Web и PDF получают один `career_report_read_v1`; backend нормализует десять секций в каноническом порядке.
- Deterministic dimensions, contradictions, context constraints и role matches остаются видимыми при `deterministic_ready` и `narrative_failed`.
- PDF endpoint генерирует artifact из того же payload; profession examples помечены как возможные, scores — как выраженность, не оценка.
- `uv run pytest tests/unit/test_career -q` — 52 passed; PDF начинается с `%PDF` и превышает 1000 bytes.
- `npm test` — reader contract script passed.
- `npx tsc --noEmit --pretty false` и exact-path ESLint — passed.

Открытые пункты требуют реального desktop/mobile/print browser smoke и визуального сравнения с canonical HTML sample.
