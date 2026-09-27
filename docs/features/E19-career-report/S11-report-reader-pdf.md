# S11: Career report reader и PDF

## Статус

✅ Завершено — web/PDF presentation contract, semantic parity и Chromium sample evidence закрыты

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
- [x] Web/PDF читают один persisted source и имеют доказанный одинаковый порядок/представление секций.
- [x] Scores объяснены без good/bad ranking.
- [x] Profession examples сформулированы условно, без назначения.
- [x] Contradictions и context constraints не теряются между API, web view-model и PDF view-model.
- [x] Deterministic-ready reader полезен до завершения LLM.
- [x] Narrative failure не скрывает deterministic content.
- [x] Mobile, print/PDF, typography и whole-word tooltips проверены.
- [x] Canonical HTML sample и desktop/mobile previews созданы.
- [x] Реальный reader проходит воспроизводимый visual parity smoke относительно canonical sample.

## Реализация и проверка

- `/products/career/report/[reportId]` читает progressive persisted payload `/api/v1/career/reports/{report_id}` без legacy `generated_report`.
- Web и PDF получают один `career_report_read_v1`; backend нормализует десять секций в каноническом порядке.
- Deterministic dimensions, contradictions, context constraints и role matches остаются видимыми при `deterministic_ready` и `narrative_failed`.
- PDF endpoint генерирует artifact из того же payload; profession examples помечены как возможные, scores — как выраженность, не оценка.
- `uv run pytest tests/unit/test_career -q` — 64 passed; PDF начинается с `%PDF` и превышает 1000 bytes.
- `npm test` — reader contract script passed.
- `npx tsc --noEmit --pretty false` и exact-path ESLint — passed.
- Playwright Chromium проверяет desktop/mobile overflow, canonical section order, standalone reader shell, Axe, whole-word tooltip text и `aria-describedby`, print colors и browser PDF (`%PDF`, больше 10 KB).
- Desktop/mobile/print visual regression baselines сохранены в `frontend/tests/e2e/career-reader.spec.ts-snapshots/`; локальный общий Career browser suite: `5 passed, 1 skipped`.
- `contracts/fixtures/career-report-read-v1-parity.json` задаёт один semantic manifest; `backend/app/modules/career/presentation.py`, frontend view-model и PDF renderer обязаны воспроизводить его без собственного порядка/labels.
- `frontend/scripts/check-career-report-parity.mjs` и `check-career-sample-parity.mjs` прошли из repo root и frontend cwd; protocol фиксирует component/crop comparison вместо бессмысленного full-page pixel equality.
- Добавлены browser cases `deterministic_ready` и `narrative_failed`; точный SHA `3fbd11948a9676d440915cd5abcd50dbbf7aa3c5` прошёл GitHub Actions CI run `36285160532`, включая desktop/mobile Chromium smoke, canonical sample crops, screenshots, print и browser PDF.

Human visual review desktop/mobile/print снимков подтвердил отсутствие clipping/overflow, читаемый print и соответствие canonical sample как design direction. Reader получил standalone shell, hero summary cards с ведущим профилем/рабочим вектором и компактную навигационную сетку десяти разделов; pixel-perfect совпадение не является контрактом.

## Аудит 2026-09-26

- Cross-render implementation gaps и evidence gap закрыты общим presentation contract, fixture parity tests и зелёным exact-SHA Chromium run.
