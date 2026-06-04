# Story E11.S06: Narrative validation, repair and fallback policy

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

LLM output нельзя сохранять сразу. Нужно детерминированно проверить структуру, product boundaries, evidence refs, forbidden terms, отсутствие новых астрологических/соционических фактов и safety сексуальности.

## Что сделано

1. Реализован `validate_self_narrative(narrative, narrative_input) -> list[NarrativeValidationError]`.
2. Добавлена проверка полного набора обязательных секций и их порядка.
3. Добавлена проверка `fact_ids` против deterministic input facts/aspects/evidence ids.
4. Добавлена проверка Self-vs-Career boundary для career deep dive language вне `career_cta`.
5. Добавлена проверка forbidden fatalistic/medical/diagnostic/graphic sexuality language.
6. Добавлена проверка unknown astrology/socionics terms, которых нет во входе.
7. Зафиксирована MVP policy: один repair attempt для recoverable validation failures, затем fallback; non-recoverable violations -> `narrative_failed`; LLM unavailable -> fallback.
8. Добавлен deterministic fallback template для degraded mode без LLM.

## Затронутые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/report_narratives/validators.py` | Deterministic validators + repair/fallback policy |
| `backend/app/modules/report_narratives/fallback.py` | Deterministic fallback narrative |
| `backend/app/modules/report_narratives/exceptions.py` | Validation error primitives |
| `backend/app/modules/report_narratives/__init__.py` | Public exports |
| `backend/tests/unit/test_report_narratives/test_validators.py` | Positive/negative validator tests |
| `backend/tests/unit/test_report_narratives/test_fallback.py` | Fallback tests |

## Критерии приёмки

- [x] Unknown evidence refs отклоняются.
- [x] Self без `career_cta` отклоняется.
- [x] Self с профессиями/денежной стратегией/карьерным планом отклоняется.
- [x] Диагнозы, фатализм, гарантии и графичная сексуальность отклоняются.
- [x] Output с новой планетой/аспектом/домом/type code, которых нет во входе, отклоняется или помечается validation error.
- [x] Fallback narrative строится без LLM и содержит явное сообщение о недоступности текстовой версии, если нужен degraded mode.
- [x] Tests покрывают positive и negative cases.

## Проверка

```bash
cd backend
docker compose exec -T backend python -m ruff check app/modules/report_narratives tests/unit/test_report_narratives
docker compose exec -T backend python -m ruff format --check app/modules/report_narratives tests/unit/test_report_narratives
docker compose exec -T backend python -m mypy app/modules/report_narratives tests/unit/test_report_narratives
docker compose exec -T backend python -m pytest tests/unit/test_report_narratives -q
```
