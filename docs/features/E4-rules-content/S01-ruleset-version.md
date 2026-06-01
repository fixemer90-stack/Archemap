# Story E4.S01: RuleSetVersion

**Feature:** [Rules & Content](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Модель версионирования правил: YAML-файлы на диске, привязка к вертикали (product), несколько версий сосуществуют.

## Что сделать

- RuleSet dataclass с полями: product, version, effective_from, locale, archetypes, scoring, confidence_config
- Loader для YAML-файлов из `backend/rules/{product}/archetypes_{version}.yaml`
- Функция `list_available_rulesets()` для сканирования доступных версий

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/rules/types.py` | `RuleSet`, `ArchetypeRule`, `Condition`, `ConditionGroup` dataclass'ы |
| `backend/app/modules/rules/loader.py` | `load_ruleset()`, `list_available_rulesets()` |
| `backend/rules/self/archetypes_v1.yaml` | 8 архетипов для вертикали Self |

## Критерии приёмки

- [x] RuleSet загружается из YAML
- [x] Несколько версий могут сосуществовать (v1, v2...)
- [x] Привязка к вертикали (product: self, love, child, career)
- [x] Тесты написаны и проходят (20 unit-тестов)
- [x] ruff, mypy, eslint — 0 ошибок

## Примечания

Формат YAML:
```yaml
product: self
version: "v1"
effective_from: "2025-01-01"
locale: "ru-RU"
archetypes:
  - archetype_id: "warrior"
    name: "Воин"
    description: "..."
    conditions: { conjunction: "all", conditions: [...] }
    effects: { "archetype.warrior": 1.0 }
scoring:
  default_weight: 1.0
  counter_penalty_lambda: 0.30
  max_possible_score: 1.0
confidence_config:
  weights: { q_input: 0.35, q_coverage: 0.30, q_margin: 0.20, q_consistency: 0.15 }
```
