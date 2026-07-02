# S04 — Humanized Quality Gates

Статус: ⬜ Не начато
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

- [ ] Validator flags generic/soulless prose examples while allowing concrete human prose.
- [ ] Validator checks do not punish necessary technical terms inside collapsed evidence/technical sections.
- [ ] Tone failure is observable through structured logs with `failure_kind` / `recovery_action`.
- [ ] Tests cover Russian prose examples.
- [ ] Safety/evidence validators remain stricter than tone preferences.

## Verification

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives/test_validators.py -q'
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives -q'
```
