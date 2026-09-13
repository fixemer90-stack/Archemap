# S11: Career report reader и PDF

## Статус

⬜ Не начато

## Контекст

Текущий Career reader отражает legacy rules output. Target reader должен быть narrative-first, объяснять scores простым языком и сохранять одинаковую структуру web/PDF.

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

- [ ] Reader не использует legacy `generated_report` payload.
- [ ] Web/PDF читают один persisted source и имеют один порядок секций.
- [ ] Scores объяснены без good/bad ranking.
- [ ] Profession examples сформулированы условно, без назначения.
- [ ] Contradictions и context constraints не теряются.
- [ ] Deterministic-ready reader полезен до завершения LLM.
- [ ] Narrative failure не скрывает deterministic content.
- [ ] Mobile, print/PDF, typography и whole-word tooltips проверены.
- [ ] Canonical sample/screenshot и parity smoke приложены до закрытия Story.
