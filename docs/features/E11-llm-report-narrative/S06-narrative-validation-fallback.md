# Story E11.S06: Narrative validation, repair and fallback policy

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

LLM output нельзя сохранять сразу. Нужно детерминированно проверить структуру, product boundaries, evidence refs, русский язык, forbidden terms, отсутствие новых астрологических/соционических фактов и safety сексуальности.

## Что сделать

1. Реализовать `validate_self_narrative(narrative, narrative_input) -> list[NarrativeValidationError]`.
2. Проверять обязательные секции и порядок.
3. Проверять, что все `fact_ids` существуют во входе.
4. Проверять запрещённые career deep dive markers для Self.
5. Проверять forbidden fatalistic/medical/diagnostic/graphic sexuality language.
6. Проверять, что output не вводит unknown astrology/socionics terms beyond allowed input facts.
7. Описать MVP policy: один repair attempt для recoverable validation failures или deterministic fallback/narrative_failed.
8. Добавить deterministic fallback template для случая, когда LLM недоступна или validation не прошла.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/report_narratives/validators.py` | Validators |
| `backend/app/modules/report_narratives/fallback.py` | Deterministic fallback narrative |
| `backend/app/modules/report_narratives/exceptions.py` | Validation exceptions |
| `backend/tests/unit/test_report_narratives/test_validators.py` | Validator tests |
| `backend/tests/unit/test_report_narratives/test_fallback.py` | Fallback tests |

## Критерии приёмки

- [ ] Unknown evidence refs отклоняются.
- [ ] Self без `career_cta` отклоняется.
- [ ] Self с профессиями/денежной стратегией/карьерным планом отклоняется.
- [ ] Диагнозы, фатализм, гарантии и графичная сексуальность отклоняются.
- [ ] Output с новой планетой/аспектом/домом/type code, которых нет во входе, отклоняется или помечается validation error.
- [ ] Fallback narrative строится без LLM и содержит явное сообщение о недоступности текстовой версии, если нужен degraded mode.
- [ ] Tests покрывают positive и negative cases.
