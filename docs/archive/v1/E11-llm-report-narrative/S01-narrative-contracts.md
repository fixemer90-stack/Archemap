# Story E11.S01: Narrative contracts — input/output schemas

**Feature:** [LLM Report Narrative](Archemap/docs/features/v1/E11-llm-report-narrative/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

LLM нельзя кормить сырым `report_data` и нельзя принимать свободный Markdown. Сначала нужно зафиксировать строгие Pydantic schemas для очищенного входа (`NarrativeInput`) и structured output (`SelfNarrative`). Эти contracts станут основой prompt-а, provider-а, validators, API, frontend и PDF.

## Что сделать

1. Создать backend schemas для `NarrativeInput`, `NarrativeProfile`, `CalculationQuality`, `AstroFact`, `AspectFact`, `SocionicsSummary`, `ArchetypeSummary`, `EvidenceBackedClaim`, `ProductBoundaries`.
2. Создать output schemas: `EvidenceNote`, `NarrativeSection`, `CareerCTA`, `SelfNarrative`.
3. Зафиксировать allowed section ids для Self: `main_formula`, `world_perception`, `emotions_and_communication`, `strengths`, `vulnerabilities`, `relationships`, `sexuality`, `development`.
4. Ограничить `product` literal-ами `self`, `career`, `love`, но в MVP реализовать только `self`.
5. Добавить schema examples/fixtures для unit tests.
6. Обновить OpenAPI/contract docs только если response shape публичного API меняется в этой story.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/report_narratives/__init__.py` | Создать модуль |
| `backend/app/modules/report_narratives/schemas.py` | Добавить Pydantic schemas |
| `backend/tests/unit/test_report_narratives/test_schemas.py` | Unit tests для valid/invalid schema cases |
| `contracts/openapi.yaml` | Обновить позже/здесь, если API contract уже меняется |
| `docs/design/llm-report-narrative-architecture.md` | Сверить имена схем с design doc |

## Критерии приёмки

- [x] `NarrativeInput` не содержит инструкцию «проанализируй дату рождения» и не зависит от raw birth data как единственной основы.
- [x] `SelfNarrative` валидируется как JSON structure: title, hero, sections, career_cta, final_summary.
- [x] Section ids ограничены известным списком для Self.
- [x] `evidence_notes[*].fact_ids` представлены явно и доступны validators.
- [x] Pydantic tests покрывают happy path, missing required fields, invalid product, invalid section id.
- [x] `python -m pytest tests/unit/test_report_narratives/test_schemas.py -q` проходит.

## Реализация

Создан новый backend-модуль `backend/app/modules/report_narratives/` с экспортом narrative contracts.

Реализованы schema-контракты:

- `NarrativeInput`
- `NarrativeProfile`
- `CalculationQuality`
- `AstroFact`
- `AspectFact`
- `SocionicsSummary`
- `ArchetypeSummary`
- `EvidenceBackedClaim`
- `ProductBoundaries`
- `EvidenceNote`
- `HeroSection`
- `NarrativeSection`
- `CareerCTA`
- `SelfNarrative`

Зафиксированы literal-ограничения для:

- `product`: `self | career | love`
- `language`: `ru`
- `birth_time_quality`: `exact | approximate | unknown`
- `Self` section ids: `main_formula`, `world_perception`, `emotions_and_communication`, `strengths`, `vulnerabilities`, `relationships`, `sexuality`, `development`

## Верификация

Проверено в backend container:

```bash
cd /app
python -m pytest tests/unit/test_report_narratives/test_schemas.py -q
python -m ruff check app/modules/report_narratives tests/unit/test_report_narratives
python -m ruff format --check app/modules/report_narratives tests/unit/test_report_narratives
python -m mypy app/modules/report_narratives tests/unit/test_report_narratives
```
