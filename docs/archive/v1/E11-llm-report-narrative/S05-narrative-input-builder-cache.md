# Story E11.S05: NarrativeInput builder, hashing and cache lookup

**Feature:** [LLM Report Narrative](Archemap/docs/features/v1/E11-llm-report-narrative/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

LLM должна получать не весь raw `report_data`, а специально собранный `NarrativeInput`: только разрешённые факты, claims, evidence, quality warnings и product boundaries. Для защиты от повторных кликов и дублей нужен `input_hash`.

## Что сделать

1. Реализовать `build_narrative_input(report)` для Self.
2. Преобразовать deterministic report data в evidence-backed facts and claims.
3. Нормализовать labels на русском: planet/sign/aspect/type names не должны протекать raw English enum-ами в prompt.
4. Добавить `ProductBoundaries` для Self.
5. Реализовать stable `compute_input_hash(narrative_input)` через sorted JSON dump + sha256.
6. Реализовать cache lookup existing narrative по `report_id + product + prompt_version + input_hash + model_name`.
7. Добавить fixtures для report_data с missing optional fields.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/report_narratives/input_builder.py` | Новый builder |
| `backend/app/modules/report_narratives/hash.py` | Stable input hash |
| `backend/app/modules/report_narratives/service.py` | Cache lookup helper |
| `backend/app/modules/report_narratives/__init__.py` | Экспорт builder/hash/cache helpers |
| `backend/tests/unit/test_report_narratives/test_input_builder.py` | Builder/hash/cache tests |

## Критерии приёмки

- [x] Builder не передаёт LLM raw `report_data` целиком.
- [x] Каждый важный claim имеет stable fact/evidence id.
- [x] Missing ASC/houses/aspects/socionics не ломают builder и отражаются в `calculation_quality`.
- [x] `input_hash` одинаков для одинакового semantic input и меняется при изменении facts/claims/product boundaries.
- [x] Cache lookup предотвращает повторную генерацию для идентичного input/model/prompt_version.
- [x] Unit tests покрывают exact birth time, unknown birth time, missing optional blocks, duplicate generation.

## Реализация

Добавлены:

- `backend/app/modules/report_narratives/input_builder.py` — `build_narrative_input(report)` и helper-ы локализации/claim grouping
- `backend/app/modules/report_narratives/hash.py` — `compute_input_hash(...)`
- `backend/app/modules/report_narratives/service.py` — `find_cached_narrative(...)`
- `backend/app/modules/report_narratives/__init__.py` — экспорт builder/hash/cache helpers
- `backend/tests/unit/test_report_narratives/test_input_builder.py` — TDD-покрытие story

Что зафиксировано в builder-е:

- собирается curated `NarrativeInput`, а не прокидывается весь `report.report_data`
- planet/sign/aspect labels переводятся в русский для prompt-safe входа
- claims группируются в:
  - `strengths`
  - `risks`
  - `relationship_patterns`
  - `sexuality_patterns`
  - `development_recommendations`
- `evidence_ids` строятся из deterministic `basis[*].rule_id`
- при отсутствии optional blocks builder не падает:
  - пустые `key_facts` / `key_aspects`
  - fallback `socionics`
  - `calculation_quality` отражает unknown birth time и `quality_warning`

Что зафиксировано в hashing/cache:

- `input_hash` строится через canonical JSON normalization + `sha256`
- для семантически одинакового input hash стабилен даже при другом порядке claims
- cache lookup использует ключ:
  - `report_id + product + prompt_version + input_hash + model_name`
- cached narrative возвращается только для `status="ready"`

## Верификация

Проверено в backend container:

```bash
cd /app
python -m pytest tests/unit/test_report_narratives/test_input_builder.py -q
python -m ruff check app/modules/report_narratives tests/unit/test_report_narratives
python -m ruff format --check app/modules/report_narratives tests/unit/test_report_narratives
python -m mypy app/modules/report_narratives tests/unit/test_report_narratives
python -m pytest tests/unit/test_report_narratives -q
```
