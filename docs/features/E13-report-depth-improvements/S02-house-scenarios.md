# S02 — House Scenario Interpreter

Статус: ⬜ Не начато
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

- [ ] В отчёте есть сценарные описания ключевых домов/положений.
- [ ] Каждый сценарий содержит manifestation и shadow/risk.
- [ ] Сценарии основаны на реальных placements из chart snapshot.
- [ ] Нет raw enum leak (`Sun`, `Virgo`, `conjunction`) в пользовательском тексте.
- [ ] PDF содержит тот же блок.
- [ ] Regression check ловит отсутствие house scenarios.

## Проверка

```bash
cd frontend
node scripts/check-report-ux.mjs
npx tsc --noEmit --pretty false
```
