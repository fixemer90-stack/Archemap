# S04 — Humanized Quality Gates

Статус: ✅ Готово
Эпик: `E15-self-report-human-storytelling`

## Контекст

Existing validators protect evidence, safety and generic horoscope prose. E15 needs an additional readability/tone layer that catches technically valid but lifeless text.

## Что сделать

1. Add quality checks for канцелярит and over-abstract phrasing.
2. Detect repeated service words: `паттерн`, `динамика`, `формирует`, `обработка`, `механизм`, `идентичность` when overused without concrete behavior.
3. Require lived-manifestation markers per key section.
4. Add density checks: sections must not be only claims; they need scenario/risk/mature expression.
5. Make failures recoverable where possible: repair once, then regenerate/fail according to existing policy.

## Затрагиваемые файлы

| Файл                                                           | Изменение                                         |
| -------------------------------------------------------------- | ------------------------------------------------- |
| `backend/app/modules/report_narratives/validators.py`          | Tone/readability checks                           |
| `backend/app/modules/report_narratives/service.py`             | Recovery action if tone check fails               |
| `backend/tests/unit/test_report_narratives/test_validators.py` | New validator tests                               |
| `backend/tests/unit/test_report_narratives/fixtures/`          | Human/generic examples if fixture split is useful |

## Acceptance criteria

- [x] Validator flags generic/soulless prose examples while allowing concrete human prose.
- [x] Validator checks do not punish necessary technical terms inside collapsed evidence/technical sections.
- [x] Tone failure is observable through structured logs with `failure_kind` / `recovery_action`.
- [x] Tests cover Russian prose examples.
- [x] Safety/evidence validators remain stricter than tone preferences.

## Реализация

- `validate_assembled_self_narrative(...)` получил humanized quality gates поверх уже существующих safety/evidence validators.
- Добавлены recoverable errors:
  - `soulless_service_word_overuse` — чрезмерное повторение служебных слов (`паттерн`, `динамика`, `формирует`, `обработка`, `механизм`, `идентичность`) без живого поведения.
  - `missing_lived_manifestation` — ключевая Self-секция без конкретной жизненной сцены/проявления.
  - `thin_claim_density` — claim-heavy секция без цепочки scenario/risk/mature expression.
- Проверки применяются только к visible user prose (`hero.body`, `final_summary`, `sections[*].body`) и не штрафуют collapsed evidence/technical fields.
- Существующий staged validation path уже пишет structured log `report_narrative_stage_failed` с `failure_kind=staged_validation_failed` и `recovery_action`; новые ошибки recoverable и проходят через тот же наблюдаемый механизм.
- Добавлены русскоязычные regression tests в `backend/tests/unit/test_report_narratives/test_validators.py`.

## Verification evidence

```text
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives/test_validators.py::TestHumanizedQualityGates -q'
→ 4 passed

docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives/test_validators.py tests/unit/test_report_narratives/test_staged_assembler.py tests/unit/test_report_narratives/test_staged_assembly.py tests/unit/test_report_narratives/test_staged_service.py -q'
→ 40 passed

docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives -q'
→ 123 passed

docker compose exec -T backend sh -lc 'cd /app && python -m py_compile app/modules/report_narratives/validators.py tests/unit/test_report_narratives/test_validators.py && python -m ruff check app/modules/report_narratives/validators.py tests/unit/test_report_narratives/test_validators.py && python -m ruff format --check app/modules/report_narratives/validators.py tests/unit/test_report_narratives/test_validators.py && python -m mypy app/modules/report_narratives/validators.py'
→ py_compile passed; ruff passed; format passed; mypy passed
```

## Verification

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives/test_validators.py -q'
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives -q'
```
