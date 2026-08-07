# S02 — House Scenario Interpreter

Статус: ✅ Готово
Эпик: `E13-report-depth-improvements`

## Контекст

Текущий отчёт часто читает дома как короткие ярлыки: “Солнце в 9 доме — масштабные идеи”. Для Astrotype этого мало. Дома должны давать жизненные сценарии: потребность, проявление, тень, зрелая форма.

## Целевой пример

```text
Солнце в 9 доме:
- потребность иметь мировоззрение, а не просто набор фактов;
- интерес к системам объяснения: философия, методологии, теория, образование, типологии;
- внутренний авторитет строится через понимание “как устроен мир”;
- тень: можно застревать в поиске правильной системы и откладывать действие.
```

## Что сделать

1. Создать mapping для house scenario templates.
2. Учитывать не только дом, но и планету + знак + сила/контекст.
3. Сформировать `house_scenarios[]` в narrative input или deterministic report data.
4. Убедиться, что сценарии не дублируют техническую таблицу домов.
5. Добавить fallback wording для самых важных положений:
   - Sun;
   - Moon;
   - Mercury;
   - Venus;
   - Mars;
   - high-emphasis houses;
   - stellium houses.

## Затрагиваемые файлы

| Файл | Изменение |
|---|---|
| `backend/app/chart_engine/features.py` | house emphasis / placement signals при необходимости |
| `backend/app/modules/report_narratives/input_builder.py` | house scenario extraction |
| `backend/app/modules/report_narratives/schemas.py` | `HouseScenario` schema |
| `backend/app/modules/report_narratives/fallback.py` | deterministic scenario text |
| `frontend/src/components/report/` | rendering сценариев |
| `backend/app/modules/reports/templates/report.html` | PDF parity |

## Критерии приёмки

- [x] В отчёте есть сценарные описания ключевых домов/положений.
- [x] Каждый сценарий содержит manifestation и shadow/risk.
- [x] Сценарии основаны на реальных placements из chart snapshot.
- [x] Нет raw enum leak (`Sun`, `Virgo`, `conjunction`) в пользовательском тексте.
- [x] PDF содержит тот же блок.
- [x] Regression check ловит отсутствие house scenarios.

## Реализация

- Добавлен `HouseScenario` и обязательный `SelfNarrative.house_scenarios`.
- `NarrativeInput.house_scenarios` строится из реальных `chart.planets` placements: планета + знак + дом + evidence id.
- В `input_builder.py` добавлены house scenario templates для 1–12 домов и приоритет Sun → Moon → Mercury → Venus → Mars → outer planets.
- Fallback и mock provider возвращают тот же блок, чтобы degraded mode не терял semantic layer.
- Validator проверяет наличие scenarios, `manifestation`, `shadow` и evidence refs.
- API response, frontend view-model, `HouseScenariosSection`, PDF template и `check-report-ux.mjs` расширены под web/PDF parity.
- Prompt contract поднят до `self_story_v3`.

## Проверка

```bash
# Backend container
python -m ruff check app/modules/report_narratives app/modules/llm/providers/mock.py app/modules/reports tests/unit/test_report_narratives tests/unit/test_reports
python -m ruff format --check app/modules/report_narratives app/modules/llm/providers/mock.py app/modules/reports tests/unit/test_report_narratives tests/unit/test_reports
python -m mypy app/modules/report_narratives app/modules/llm/providers/mock.py app/modules/reports
python -m pytest tests/unit/test_report_narratives tests/unit/test_reports -q
python -m pytest tests/unit -q

# Frontend
node scripts/check-report-ux.mjs
npm test
npx tsc --noEmit --pretty false
npx prettier --check .
npx eslint .
```
