# Story E4.S04: Content Resolver

**Feature:** [Rules & Content](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Content Resolver — оркестрация полного pipeline: chart snapshot → features → rules → interpretation → rendered report.

## Что сделать

- `RulesService.interpret_chart()` — полный pipeline
- `_dict_to_chart()` — конвертация dict из БД обратно в `ChartData`
- `render_full_report()` — рендер claims с evidence templates
- API endpoint `POST /api/v1/rules/interpret`

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/rules/service.py` | `RulesService`, `_dict_to_chart()` |
| `backend/app/modules/rules/resolver.py` | `render_full_report()` |
| `backend/app/modules/rules/router.py` | `POST /interpret`, `GET /rulesets` |
| `backend/app/modules/rules/schemas.py` | Pydantic schemas для API |

## Pipeline

```
snapshot.chart_data → _dict_to_chart() → extract_features() → load_ruleset() → interpret() → render_full_report()
```

## Критерии приёмки

- [x] Pipeline работает end-to-end
- [x] `_dict_to_chart()` парсит planets (longitude/sign_degree), houses, aspects
- [x] Access control: user_id фильтр на snapshot
- [x] Fallback на `claim.message` при отсутствии шаблона
- [x] API endpoint с auth
- [x] Тесты pass
- [x] ruff, mypy — 0 ошибок

## Примечания

- `_dict_to_chart()` обрабатывает оба формата: с `longitude` и без (вычисляет из `sign` + `degree`)
- `NotFoundError` при отсутствии snapshot для profile_id + user_id
