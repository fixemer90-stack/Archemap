# S06 — Assembly, Consistency and Anti-Horoscope Quality Gates

> Статус: 🟡 Частично готово
> Базовый backend commit: `4ce5175`
> Последняя синхронизация с кодом: 2026-06-29

## Контекст

Parallel section generation can create repetition, tone drift and contradictions. The final report must feel like one reading, not five generated blocks.

## Что уже сделано

1. Добавлен deterministic assembler из ready stage outputs.
2. Добавлен assembled `SelfNarrative` contract with Self-first section order.
3. Добавлена проверка сохранения evidence refs из staged outputs.
4. Добавлены anti-generic checks:
   - `duplicate_paragraph`;
   - `generic_horoscope_prose`;
   - `fatalistic_language`;
   - `missing_mechanism_risk_mature_chain`.
5. Добавлены RED/fixture-style tests на good/bad assembled outputs.

## Что уже закрыто поверх baseline

1. Assembler и assembled validators уже встроены в реальный staged runtime flow.
2. Финальный `SelfNarrative` собирается только после `assembly` stage и затем валидируется перед `ready`.
3. Baseline anti-generic quality gates реально защищают от duplicate paragraphs, horoscope-generic prose, fatalistic language и missing mechanism/risk/mature chain.

## Что ещё осталось

1. Добавить full contradiction checks между central claims секций.
2. Добавить stronger consistency / tone-drift validation beyond current baseline gates.
3. При необходимости подключить optional final consistency pass behind feature flag.
4. При желании вынести richer staged fixtures в отдельный `fixtures/` каталог.

## Затрагиваемые файлы

| Файл                                                                | Действие                                |
| ------------------------------------------------------------------- | --------------------------------------- |
| `backend/app/modules/report_narratives/assembler.py`                | New assembler                           |
| `backend/app/modules/report_narratives/validators.py`               | Stage/final quality validators          |
| `backend/tests/unit/test_report_narratives/test_staged_assembly.py` | Assembly tests                          |
| `backend/app/modules/report_narratives/service.py`                  | Runtime assembly + validation wiring    |
| `backend/tests/unit/test_report_narratives/fixtures/`               | Пока не создано, fixtures зашиты в тест |

## Acceptance criteria

- [ ] Final report cannot pass if sections contradict each other on a central claim.
- [x] Final report cannot pass if it contains mostly generic horoscope language.
- [x] Final report preserves evidence refs from staged outputs.
- [x] Final report keeps Self narrative-first order.
- [x] Final report has no obvious repeated paragraphs.
- [ ] Final report voice consistency is fully enforced beyond current baseline checks.

## Verification

- `pytest tests/unit/test_report_narratives/test_staged_assembly.py tests/unit/test_report_narratives/test_staged_service.py tests/unit/test_report_narratives/test_staged_prompts.py tests/unit/test_report_narratives/test_validators.py tests/unit/test_report_narratives/test_input_builder.py -q` → `37 passed`
- `pytest tests/unit/test_report_narratives -q` → `88 passed`
- `ruff check app/modules/report_narratives/assembler.py app/modules/report_narratives/validators.py tests/unit/test_report_narratives/test_staged_assembly.py`
- `mypy app/modules/report_narratives/assembler.py app/modules/report_narratives/validators.py tests/unit/test_report_narratives/test_staged_assembly.py`
