# Story E4.S05: Локализация

**Feature:** [Rules & Content](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Поддержка locale в правилах и шаблонах. Fallback на `ru-RU` при отсутствии запрошенного locale.

## Что сделать

- `RuleSet.locale` — поле в dataclass
- API `InterpretRequest.locale` — параметр запроса
- Default `ru-RU` в service

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/rules/types.py` | `RuleSet.locale` field |
| `backend/app/modules/rules/service.py` | `locale` parameter in `interpret_chart()` |
| `backend/app/modules/rules/schemas.py` | `InterpretRequest.locale` |

## Критерии приёмки

- [x] `RuleSet.locale` поле (default `ru-RU`)
- [x] API принимает `locale` параметр
- [x] Fallback на `ru-RU`
- [x] ruff, mypy — 0 ошибок

## Примечания

Текущая реализация: locale передаётся через API, но evidence templates пока не дифференцированы по locale. Для полной поддержки нужно:
- `backend/rules/{product}/evidence_templates_{version}_{locale}.yaml`
- Fallback chain: `{locale}` → `ru-RU` → default
