# Story E4.S03: Rule Engine

**Feature:** [Rules & Content](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Детерминированный rule engine: YAML-условия → match score → weighted contributions → aggregate scores → confidence.

## Что сделать

- Condition evaluation: `gte`, `lte`, `gt`, `lt`, `eq`, `neq`, `in`, `not_in`, `between`
- Condition groups: `all` (min), `any` (max), `not` (1-max)
- Weighted scoring с counter-rules (lambda penalty)
- 4-factor confidence model (q_input, q_coverage, q_margin, q_consistency)
- Evidence trail: basis + counter-evidence для каждого claim

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/rules/engine.py` | `interpret()`, `_evaluate_rule()`, `_aggregate_scores()`, `_compute_confidence()` |
| `backend/app/modules/rules/types.py` | `ConditionOp(StrEnum)`, `RuleEvaluation`, `ConfidenceResult`, `Claim`, `InterpretationResult` |
| `backend/tests/unit/test_rules/test_engine.py` | 20 unit-тестов |

## Формулы

Scoring:
```
contrib_r = w_r * match_r * q_input * q_rule
score_k = clamp((bias_k + Σsupport - λ * Σcounter) / max_possible, 0, 1)
```

Confidence:
```
confidence = 0.35*q_input + 0.30*q_coverage + 0.20*q_margin + 0.15*q_consistency
```

## Критерии приёмки

- [x] 9 операторов условий работают
- [x] Группы all/any/not
- [x] Weighted scoring с counter-rules
- [x] 4-factor confidence с reason codes
- [x] Evidence trail (basis + counter_evidence)
- [x] mode="preview" ограничивает до 3 claims
- [x] 20 unit-тестов pass
- [x] ruff, mypy — 0 ошибок

## Примечания

- `ConditionOp` — `StrEnum` для сериализации в YAML/JSON
- `_build_facts()` маппит `FeatureVector` → flat dict с dotted keys (`feature.fire`, `house_emphasis.1`)
- Quality warning при отсутствии времени рождения
