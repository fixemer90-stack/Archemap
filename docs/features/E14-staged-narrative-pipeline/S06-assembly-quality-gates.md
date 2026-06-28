# S06 — Assembly, Consistency and Anti-Horoscope Quality Gates

> Статус: ⬜ Не начато

## Контекст

Parallel section generation can create repetition, tone drift and contradictions. The final report must feel like one reading, not five generated blocks.

## Что сделать

1. Build deterministic assembler from ready stage outputs.
2. Add optional final consistency pass behind feature flag.
3. Validate:
   - no duplicate paragraphs;
   - no unsupported evidence refs;
   - no section contradictions;
   - no Career leakage;
   - no generic horoscope prose.
4. Add anti-horoscope checks:
   - forbidden vague fillers;
   - minimum density of evidence-backed statements;
   - required mechanism/risk/mature-expression chain;
   - no “all people with X are Y” fatalism.
5. Add snapshot/fixture tests with shallow bad examples.

## Затрагиваемые файлы

| Файл                                                                | Действие                       |
| ------------------------------------------------------------------- | ------------------------------ |
| `backend/app/modules/report_narratives/assembler.py`                | New assembler                  |
| `backend/app/modules/report_narratives/validators.py`               | Stage/final quality validators |
| `backend/tests/unit/test_report_narratives/test_staged_assembly.py` | Assembly tests                 |
| `backend/tests/unit/test_report_narratives/fixtures/`               | Good/bad staged outputs        |

## Acceptance criteria

- [ ] Final report cannot pass if sections contradict each other on a central claim.
- [ ] Final report cannot pass if it contains mostly generic horoscope language.
- [ ] Final report preserves evidence refs from staged outputs.
- [ ] Final report keeps Self narrative-first order.
- [ ] Final report has consistent voice and no obvious repeated paragraphs.
