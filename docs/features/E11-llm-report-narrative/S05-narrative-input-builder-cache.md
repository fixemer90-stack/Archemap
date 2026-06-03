# Story E11.S05: NarrativeInput builder, hashing and cache lookup

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ⬜ Не начато

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
| `backend/app/modules/report_narratives/service.py` | Cache lookup usage |
| `backend/app/chart_engine/socionics.py` | Только если нужны existing RU labels/helpers |
| `backend/tests/unit/test_report_narratives/test_input_builder.py` | Builder tests |
| `backend/tests/unit/test_report_narratives/fixtures/` | Report fixtures |

## Критерии приёмки

- [ ] Builder не передаёт LLM raw `report_data` целиком.
- [ ] Каждый важный claim имеет stable fact/evidence id.
- [ ] Missing ASC/houses/aspects/socionics не ломают builder и отражаются в `calculation_quality`.
- [ ] `input_hash` одинаков для одинакового semantic input и меняется при изменении facts/claims/product boundaries.
- [ ] Cache lookup предотвращает повторную генерацию для идентичного input/model/prompt_version.
- [ ] Unit tests покрывают exact birth time, unknown birth time, missing optional blocks, duplicate generation.
