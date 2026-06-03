# Story E11.S01: Narrative contracts — input/output schemas

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ⬜ Не начато

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

- [ ] `NarrativeInput` не содержит инструкцию «проанализируй дату рождения» и не зависит от raw birth data как единственной основы.
- [ ] `SelfNarrative` валидируется как JSON structure: title, hero, sections, career_cta, final_summary.
- [ ] Section ids ограничены известным списком для Self.
- [ ] `evidence_notes[*].fact_ids` представлены явно и доступны validators.
- [ ] Pydantic tests покрывают happy path, missing required fields, invalid product, invalid section id.
- [ ] `python3 -m pytest tests/unit/test_report_narratives/test_schemas.py -q` проходит.
