# S04 — Staged LLM Contracts and Prompt Family

> Статус: ⬜ Не начато

## Контекст

E14 replaces one giant `self_story_v3` request with a prompt family. Each stage should have a smaller schema, narrower context and stricter evidence discipline.

## Что сделать

1. Define stage output schemas:
   - `NarrativePlan`;
   - `IdentitySectionOutput`;
   - `EmotionalSectionOutput`;
   - `RelationshipSectionOutput`;
   - `DevelopmentSectionOutput`;
   - `HouseScenariosSectionOutput`;
   - `AssemblyCheck`.
2. Create prompt files:
   - `self_plan_v1.md`;
   - `self_section_identity_v1.md`;
   - `self_section_emotional_v1.md`;
   - `self_section_relationships_v1.md`;
   - `self_section_development_v1.md`;
   - `self_section_house_scenarios_v1.md`;
   - `self_assemble_v1.md`.
3. Each prompt must state:
   - LLM is renderer/synthesizer, not calculator;
   - use only provided evidence ids;
   - no Markdown;
   - no unsupported aspects;
   - no Career deep dive;
   - no diagnostic/fatalistic language.
4. Add tests that prompt files contain required guardrails.

## Затрагиваемые файлы

| Файл                                                               | Действие                        |
| ------------------------------------------------------------------ | ------------------------------- |
| `backend/app/modules/report_narratives/prompts/`                   | New prompt files                |
| `backend/app/modules/report_narratives/prompts/__init__.py`        | Prompt version constants/loader |
| `backend/app/modules/report_narratives/schemas.py`                 | Stage schemas                   |
| `backend/tests/unit/test_report_narratives/test_staged_prompts.py` | Prompt contract tests           |

## Acceptance criteria

- [ ] Each stage has a strict schema.
- [ ] Prompt files are versioned and file-backed.
- [ ] Tests fail if evidence discipline or Self/Career boundary disappears.
- [ ] Stage prompts receive only relevant synthesis slices.
- [ ] No stage asks LLM to calculate astrology or invent facts.
