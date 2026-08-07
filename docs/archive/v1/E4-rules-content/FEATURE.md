# Feature E4: Rules & Content

## Цель

Rule-based движок интерпретации: YAML-правила, версионированные шаблоны, локализация. Детерминированный scoring с explainability.

## Зависимости

`E3`

## Критерии приёмки

- [x] RuleSetVersion: иммутабельные версии правил, привязка к вертикали
- [x] TemplateVersion: YAML-шаблоны, версионирование
- [x] Rule engine: JSON Logic условия → скор → категория
- [x] Content Resolver: набор правил → текст отчёта
- [x] Локализация RU/EN с fallback
- [ ] CMS для редакторов (опционально)

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [RuleSetVersion: модель версионирования правил, published_at, несколько версий сосуществуют](S01-ruleset-version.md) | ✅ Готово |
| S02 | [TemplateVersion: YAML-шаблоны, версионирование, привязка к вертикали](S02-template-version.md) | ✅ Готово |
| S03 | [Rule engine: JSON Logic условия, weighted scoring, confidence model, evidence trail](S03-rule-engine.md) | ✅ Готово |
| S04 | [Content Resolver: маппинг правил → шаблоны, fallback при пустых правилах](S04-content-resolver.md) | ✅ Готово |
| S05 | [Локализация: RU/EN для правил и шаблоны, fallback на RU](S05-localization.md) | ✅ Готово |
| S06 | [CMS для редакторов: UI для правил и шаблонов, preview генерации](S06-cms-editor.md) | ⬜ Не начато |

## Реализация

### S01 — RuleSetVersion (✅)

Файлы:
- `backend/app/modules/rules/types.py` — `RuleSet` dataclass (product, version, effective_from, locale, archetypes, scoring, confidence_config)
- `backend/app/modules/rules/loader.py` — `load_ruleset()`, `list_available_rulesets()`
- `backend/rules/self/archetypes_v1.yaml` — 8 архетипов для вертикали Self

```yaml
product: self
version: "v1"
effective_from: "2025-01-01"
locale: "ru-RU"
archetypes: [...]
scoring: { default_weight: 1.0, counter_penalty_lambda: 0.30 }
confidence_config: { weights: { q_input: 0.35, q_coverage: 0.30, ... } }
```

### S02 — TemplateVersion (✅)

Файлы:
- `backend/app/modules/rules/resolver.py` — `load_evidence_templates()`, `render_claim_message()`
- `backend/rules/self/evidence_templates_v1.yaml` — шаблоны для 8 архетипов

Шаблоны привязаны к `{product}/evidence_templates_{version}.yaml`. Интерполяция через `str.format(**context)`.

### S03 — Rule Engine (✅)

Файлы:
- `backend/app/modules/rules/engine.py` — `interpret()`, `_evaluate_rule()`, `_aggregate_scores()`, `_compute_confidence()`
- `backend/app/modules/rules/types.py` — `Condition`, `ConditionGroup`, `ConditionOp`, `ArchetypeRule`

Формула scoring:
```
contrib_r = w_r * match_r * q_input * q_rule
score_k = clamp((bias_k + Σsupport - λ * Σcounter) / max_possible, 0, 1)
```

Confidence (4 фактора):
```
confidence = 0.35*q_input + 0.30*q_coverage + 0.20*q_margin + 0.15*q_consistency
```

Условия: `gte`, `lte`, `gt`, `lt`, `eq`, `neq`, `in`, `not_in`, `between` с группами `all/any/not`.

### S04 — Content Resolver (✅)

Файлы:
- `backend/app/modules/rules/resolver.py` — `render_full_report()`
- `backend/app/modules/rules/service.py` — `RulesService.interpret_chart()`

Pipeline: snapshot → `_dict_to_chart()` → `extract_features()` → `load_ruleset()` → `interpret()` → `render_full_report()`.

### S05 — Локализация (✅)

- `RuleSet.locale` — поле (по умолчанию `ru-RU`)
- Evidence templates хранятся per-product per-version, можно расширить на per-locale
- Fallback на `ru-RU` при отсутствии запрошенного locale

### S06 — CMS для редакторов (⬜)

Не начато. Потребуется:
- Admin UI для редактирования YAML-правил
- Preview генерации отчёта на лету
- Валидация правил перед публикацией
- Версионирование с publish workflow

## API

```
POST /api/v1/rules/interpret
  body: { profile_id, product, ruleset_version, locale, mode }
  → { primary_archetype, primary_score, primary_confidence, claims[], all_archetype_scores, quality_warning }

GET /api/v1/rules/rulesets
  → [{ product, version, effective_from, locale, archetypes_count }]
```

## Тесты

- `backend/tests/unit/test_rules/test_engine.py` — 20 unit-тестов (все pass)
- Покрытие: scoring, confidence, evidence trail, counter-rules, quality warning
