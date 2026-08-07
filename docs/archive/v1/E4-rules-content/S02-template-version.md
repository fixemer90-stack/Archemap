# Story E4.S02: TemplateVersion

**Feature:** [Rules & Content](Archemap/docs/features/v1/E4-rules-content/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Evidence templates — YAML-шаблоны для рендеринга claims в человекочитаемый текст. Привязаны к product + version.

## Что сделать

- YAML-файл с шаблонами: `backend/rules/{product}/evidence_templates_{version}.yaml`
- `load_evidence_templates()` — загрузка шаблонов
- `render_claim_message()` — рендеринг claim через шаблон с интерполяцией
- `render_full_report()` — полный рендер всех claims

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/rules/resolver.py` | `load_evidence_templates()`, `render_claim_message()`, `render_full_report()` |
| `backend/rules/self/evidence_templates_v1.yaml` | Шаблоны для 8 архетипов |

## Критерии приёмки

- [x] Шаблоны загружаются из YAML
- [x] Интерполяция через `str.format(**context)` с `contextlib.suppress`
- [x] Fallback на `claim.message` при отсутствии шаблона
- [x] Тесты написаны и проходят
- [x] ruff, mypy, eslint — 0 ошибок

## Примечания

Формат шаблона:
```yaml
templates:
  warrior:
    title: "Воин"
    summary: "Ваша энергия направлена на действие и преодоление."
    evidence_text: "Огненная стихия ({fire:.0%}) подтверждает вашу активную натуру."
```
