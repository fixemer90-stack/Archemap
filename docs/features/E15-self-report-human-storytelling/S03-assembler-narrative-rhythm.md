# S03 — Assembler Expansion and Narrative Rhythm

Статус: ⬜ Не начато
Эпик: `E15-self-report-human-storytelling`

## Контекст

Current deterministic assembler often takes `paragraphs[0]` or `paragraphs[-1]`, which can compress a valid staged output into a thin report. E15 needs the assembler to preserve rhythm: enough prose to feel complete, but not a wall of text.

## Что сделать

1. Replace single-paragraph selection with section-aware composition.
2. Add paragraph budgeting rules:
   - hero: 1–2 compact paragraphs;
   - main formula / relationships / development: 2–3 paragraphs;
   - evidence notes: collapsed, not inline-heavy.
3. Add transition helpers so sections do not read like isolated cards.
4. Remove labels like `Механизм:`, `Риск:`, `Зрелая форма:` from user-facing prose unless rendered as UI subheadings.
5. Keep complete fallback behavior safe and structured.

## Затрагиваемые файлы

| Файл                                                                 | Изменение                            |
| -------------------------------------------------------------------- | ------------------------------------ |
| `backend/app/modules/report_narratives/assembler.py`                 | Composition rules                    |
| `backend/app/modules/report_narratives/schemas.py`                   | Only if paragraph metadata is needed |
| `backend/tests/unit/test_report_narratives/test_staged_assembler.py` | Rhythm/length/order tests            |
| `backend/tests/unit/test_report_narratives/test_validators.py`       | Compatibility with validation        |

## Acceptance criteria

- [ ] Assembler no longer drops useful second/third paragraphs by default.
- [ ] Hero remains compact and does not become a long technical essay.
- [ ] User-facing prose avoids mechanical prefixes like `Механизм:` unless rendered intentionally.
- [ ] Section order remains unchanged and frontend/API schemas stay backward-compatible.
- [ ] Fallback narrative remains safe and complete.

## Verification

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives/test_staged_assembler.py tests/unit/test_report_narratives/test_validators.py -q'
```
