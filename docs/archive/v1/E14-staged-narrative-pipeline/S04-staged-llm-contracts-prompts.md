# S04 — Staged LLM Contracts and Prompt Family

> Статус: ✅ Готово
> Коммит: `617b5aa`

## Контекст

E14 replaces one giant `self_story_v3` request with a prompt family. Each stage should have a smaller schema, narrower context and stricter evidence discipline.

## Что сделано

1. Определены stage output schemas:
   - `NarrativePlan`;
   - `IdentitySectionOutput`;
   - `EmotionalSectionOutput`;
   - `RelationshipSectionOutput`;
   - `DevelopmentSectionOutput`;
   - `HouseScenariosSectionOutput`;
   - `AssemblyCheck`.
2. Созданы file-backed prompt files:
   - `self_plan_v1.md`;
   - `self_section_identity_v1.md`;
   - `self_section_emotional_v1.md`;
   - `self_section_relationships_v1.md`;
   - `self_section_development_v1.md`;
   - `self_section_house_scenarios_v1.md`;
   - `self_assemble_v1.md`.
3. Prompt guardrails зафиксированы в файлах и loader constants.
4. Добавлены tests, что prompts не теряют evidence discipline и Self/Career boundary.

## Затрагиваемые файлы

| Файл                                                               | Действие                        |
| ------------------------------------------------------------------ | ------------------------------- |
| `backend/app/modules/report_narratives/prompts/`                   | New prompt files                |
| `backend/app/modules/report_narratives/prompts/__init__.py`        | Prompt version constants/loader |
| `backend/app/modules/report_narratives/schemas.py`                 | Stage schemas                   |
| `backend/tests/unit/test_report_narratives/test_staged_prompts.py` | Prompt contract tests           |

## Acceptance criteria

- [x] Each stage has a strict schema.
- [x] Prompt files are versioned and file-backed.
- [x] Tests fail if evidence discipline or Self/Career boundary disappears.
- [x] Stage prompts are defined around relevant synthesis slices and stage-specific output contracts.
- [x] No stage asks LLM to calculate astrology or invent facts.

## Verification

- `pytest tests/unit/test_report_narratives/test_staged_prompts.py -q`
- `pytest tests/unit/test_report_narratives -q`
- `ruff check app/modules/report_narratives/prompts/__init__.py app/modules/report_narratives/schemas.py tests/unit/test_report_narratives/test_staged_prompts.py`
- `mypy app/modules/report_narratives/prompts/__init__.py app/modules/report_narratives/schemas.py tests/unit/test_report_narratives/test_staged_prompts.py`
