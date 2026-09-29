# S02: Отключить legacy Career write/generation paths

## Статус

⬜ Не начато

## Контекст

Пока generic `/reports/generate` принимает `career`, в системе существуют два параллельных генератора с разными access, payload и lifecycle контрактами.

## Что сделать

1. Добавить product-scoped guard до создания/поиска/архивации `Report` row.
2. Для `product="career"` возвращать `410 Gone` с кодом `legacy_career_generation_retired` и target URL `/products/career`.
3. Гарантировать отсутствие DB mutation, version increment и ruleset invocation.
4. Запретить любые generic regeneration paths для legacy Career.
5. Оставить Self Report generation/narrative без изменений.

## Файлы

| Файл                                     | Действие                                |
| ---------------------------------------- | --------------------------------------- |
| `backend/app/modules/reports/router.py`  | Retirement response до service write    |
| `backend/app/modules/reports/schemas.py` | Stable error contract при необходимости |
| `backend/app/modules/reports/service.py` | Defense-in-depth product guard          |
| `backend/tests/unit/test_reports/*`      | RED/GREEN mutation и regression tests   |
| API/OpenAPI docs                         | Зафиксировать retirement behavior       |

## Критерии приёмки

- [ ] Career request получает стабильный `410` contract.
- [ ] До и после запроса одинаковы row count, payload, status и version существующего legacy report.
- [ ] `load_ruleset("career", "v1")` не вызывается.
- [ ] Нельзя обойти guard прямым вызовом service.
- [ ] Self Report generation, narrative и PDF regression suites зелёные.
- [ ] OpenAPI отражает retirement response.
