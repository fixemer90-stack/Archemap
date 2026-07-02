# S02 — Staged Prompt Family v2

Статус: ⬜ Не начато
Эпик: `E15-self-report-human-storytelling`

## Контекст

E14 shipped staged prompts, but current v1 section prompts are too terse. They mostly ask the model to “render section JSON” and protect evidence/safety, but they do not strongly ask for human storytelling.

## Что сделать

1. Add v2 prompt files:
   - `self_plan_v2.md` if plan needs tone metadata;
   - `self_section_identity_v2.md`;
   - `self_section_emotional_v2.md`;
   - `self_section_relationships_v2.md`;
   - `self_section_development_v2.md`;
   - `self_section_house_scenarios_v2.md`;
   - `self_assemble_v2.md`.
2. Update `STAGED_SELF_PROMPT_VERSIONS` only after tests exist.
3. Each section prompt must require:
   - 2–3 paragraphs when evidence supports it;
   - at least one lived manifestation;
   - no raw placement opening unless the section is technical;
   - no generic “у вас есть потенциал” prose;
   - evidence ids for interpretive claims.
4. Add tests that fail if prompts lose human tone guardrails.

## Затрагиваемые файлы

| Файл                                                                 | Изменение                   |
| -------------------------------------------------------------------- | --------------------------- |
| `backend/app/modules/report_narratives/prompts/self_section_*_v2.md` | New section prompts         |
| `backend/app/modules/report_narratives/prompts/self_assemble_v2.md`  | Final assembly prompt/check |
| `backend/app/modules/report_narratives/prompts/__init__.py`          | Prompt version constants    |
| `backend/tests/unit/test_report_narratives/test_staged_prompts.py`   | Prompt contract tests       |

## Acceptance criteria

- [ ] v2 staged prompt family is file-backed and does not mutate v1 silently.
- [ ] Prompt tests assert recognition-first, lived-manifestation and anti-kanzelyarit rules.
- [ ] Prompt tests still assert evidence discipline and Self/Career boundary.
- [ ] Prompt contract includes output length/rhythm expectations without allowing unbounded text.
- [ ] Existing providers still receive JSON-only instructions.

## Verification

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives/test_staged_prompts.py -q'
docker compose exec -T backend sh -lc 'cd /app && python -m ruff check app/modules/report_narratives/prompts tests/unit/test_report_narratives/test_staged_prompts.py'
```
