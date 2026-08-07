# Story E5.S04: Career Profile

**Feature:** [Products & Reports](Archemap/docs/features/v1/E5-products-reports/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Career-отчёт: профессиональные архетипы, роли, рабочая среда, anti-patterns, карта роста.

## Что сделать

- Career rules (YAML): 8 архетипов (Лидер, Аналитик, Креатор, Дипломат, Исполнитель, Исследователь, Целитель, Инноватор)
- Evidence templates для каждого архетипа
- Frontend: career product page с генерацией отчёта
- API: POST /reports/generate с product=career

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/rules/career/archetypes_v1.yaml` | 8 карьерных архетипов |
| `backend/rules/career/evidence_templates_v1.yaml` | Шаблоны для рендеринга |
| `frontend/src/app/(dashboard)/products/career/page.tsx` | Career product page |

## Архетипы

| Архетип | Ключевые признаки |
|---|---|
| **Лидер** | fire ≥ 0.30, cardinal ≥ 0.25, house_10 ≥ 0.40 |
| **Аналитик** | earth ≥ 0.35, fixed ≥ 0.30 |
| **Креатор** | fire ≥ 0.30, mutable ≥ 0.25 |
| **Дипломат** | air ≥ 0.30, cardinal ≥ 0.25 |
| **Исполнитель** | earth ≥ 0.40, fixed ≥ 0.35 |
| **Исследователь** | air ≥ 0.30, mutable ≥ 0.25 |
| **Целитель** | water ≥ 0.30, mutable ≥ 0.25 |
| **Инноватор** | fire ≥ 0.30, mutable ≥ 0.30, house_11 ≥ 0.35 |

## Pipeline

```
POST /reports/generate { product: "career" }
  → load_ruleset("career", "v1")
  → interpret(features, ruleset)
  → render_full_report(result, features, "career", "v1")
  → Report с career-specific archetype scores
```

## Критерии приёмки

- [x] Career rules: 8 архетипов с условиями, эффектами, counter-rules
- [x] Evidence templates для каждого архетипа
- [x] Frontend: career product page с генерацией
- [x] API: POST /reports/generate с product=career работает
- [x] ruff check: 0 ошибок

## Примечания

- Career фокусируется на MC (10-й дом), Saturn, профессиональных архетипах
- Архетипы пересекаются с Self, но с акцентом на профессиональные роли
- Counter-rules создают баланс между противоположными стилями работы
