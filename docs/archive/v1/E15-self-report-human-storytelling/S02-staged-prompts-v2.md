# S02 — Staged Prompt Family v2

Статус: ✅ Готово
Эпик: `E15-self-report-human-storytelling`

## Контекст

E14 shipped staged prompts, but current v1 section prompts are too terse. They mostly ask the model to “render section JSON” and protect evidence/safety, but they do not strongly ask for human storytelling.

S02 uses the S01 contract from `backend/app/modules/report_narratives/human_storytelling.py` (`self_human_storytelling_v1`) as the source for tone requirements: recognition-first opening, lived manifestation, inner tension/protection, mature expression, soft question, and progressive evidence disclosure.

## Что сделано

1. Добавлена file-backed staged prompt family v2:
   - `self_plan_v2.md`;
   - `self_section_identity_v2.md`;
   - `self_section_emotional_v2.md`;
   - `self_section_relationships_v2.md`;
   - `self_section_development_v2.md`;
   - `self_section_house_scenarios_v2.md`;
   - `self_assemble_v2.md`.
2. `STAGED_SELF_PROMPT_VERSIONS` переключён на v2.
3. v1 prompt files оставлены на месте и не мутированы silent edit-ом.
4. Prompt tests теперь требуют human tone guardrails:
   - `self_human_storytelling_v1`;
   - `recognition-first`;
   - `lived manifestation`;
   - `inner tension`;
   - `protective strategy`;
   - `mature expression`;
   - `progressive evidence`;
   - `no bureaucratic abstraction`;
   - `no generic horoscope prose`.
5. Базовые E11/E14 guardrails сохранены:
   - renderer/synthesizer, not calculator;
   - use only provided evidence ids;
   - no Markdown;
   - no unsupported aspects;
   - no Career deep dive;
   - no diagnostic/fatalistic language.

## Затрагиваемые файлы

| Файл                                                                        | Изменение                     |
| --------------------------------------------------------------------------- | ----------------------------- |
| `backend/app/modules/report_narratives/prompts/self_plan_v2.md`             | New staged plan prompt        |
| `backend/app/modules/report_narratives/prompts/self_section_*_v2.md`        | New humanized section prompts |
| `backend/app/modules/report_narratives/prompts/self_assemble_v2.md`         | New final assembly prompt     |
| `backend/app/modules/report_narratives/prompts/__init__.py`                 | Prompt version constants      |
| `backend/tests/unit/test_report_narratives/test_staged_prompts.py`          | Prompt contract tests         |
| `docs/features/E15-self-report-human-storytelling/S02-staged-prompts-v2.md` | Story status/details          |
| `docs/features/E15-self-report-human-storytelling/FEATURE.md`               | Story status                  |

## Acceptance criteria

- [x] v2 staged prompt family is file-backed and does not mutate v1 silently.
- [x] Prompt tests assert recognition-first, lived-manifestation and anti-kanzelyarit rules.
- [x] Prompt tests still assert evidence discipline and Self/Career boundary.
- [x] Prompt contract includes output length/rhythm expectations without allowing unbounded text.
- [x] Existing providers still receive JSON-only instructions.

## Verification

```bash
docker compose run --rm backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives/test_staged_prompts.py -q'
# 3 passed
```
