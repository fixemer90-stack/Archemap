# S01: Product, access и migration contract

## Статус

🟡 Частично — backend policy, retirement boundary, flag и access matrix реализованы; client/API enforcement остаётся в S09–S10

## Контекст

Текущий продукт `career` уже присутствует в UI/API и имеет one-time SKU `career_full`, тогда как целевая account-level policy относит специализированные отчёты к Plus. До реализации нового pipeline нужно снять конфликт идентификаторов, оплаты, entitlement и legacy маршрутов.

## Что сделать

1. Зафиксировать канонический `report_type` для нового Career и его `access_class=plus_only`.
2. Принять явное решение по `career_full`: legacy purchase mapping, grandfathering или controlled retirement.
3. Определить доступ для уже купивших legacy Career без удаления результата.
4. Зафиксировать ownership/access matrix для create, questionnaire, generate, read, regenerate, versions и PDF.
5. Определить migration boundary между legacy `reports.product='career'` и новым Career artifact.
6. Запретить silent fallback нового API на legacy rules/report payload.
7. Добавить feature flag и rollout/rollback semantics.

## Решение по умолчанию

```text
new Career access = active Plus OR explicit grandfathered legacy entitlement
```

`account_tier='plus'` без активного backend-подтверждения не является достаточным доказательством. Новый checkout не должен создавать одновременно monthly Plus и one-time Career без отдельного продуктового решения.

## Зафиксированное решение

- Канонический target `report_type`: `career`; отдельный alias `career_v2` не вводится.
- Target access: активный backend entitlement продукта `self` (текущий Plus grant) или активный legacy entitlement `career` для grandfathered-покупателя.
- `career_full` остаётся читаемым историческим SKU, но помечен `purchasable=False`; новый checkout его не продаёт.
- Legacy `reports.product='career'`, их payload и PDF остаются неизменными и не backfill-ятся в target tables.
- Новый target API обязан читать только `career_*` artifacts; silent fallback на legacy payload запрещён константой контракта и должен быть повторно доказан route tests в S09.
- `CAREER_REPORT_ENABLED=False` по умолчанию. Rollback выключает новые target generation без удаления target/legacy rows.
- Create/questionnaire/generate/read/regenerate/versions/PDF требуют одновременно ownership и target access.

## Затрагиваемые документы/файлы

| Область                              | Действие                           |
| ------------------------------------ | ---------------------------------- |
| `backend/app/modules/catalog/*`      | Канонический report/access catalog |
| `backend/app/modules/entitlements/*` | Plus/grandfather mapping           |
| `docs/features/E6-*`, `E8-*`         | Согласование доступа               |
| `contracts/openapi.yaml`             | Stable report type                 |
| migrations                           | Только additive mapping/flags      |

## Критерии приёмки

- [ ] Один канонический Career report type используется backend и всеми клиентами. Backend зафиксирован; client migration остаётся в S10–S11.
- [x] Plus/grandfather policy не зависит только от frontend.
- [x] Судьба `career_full` и существующих покупок описана без потери доступа.
- [x] Legacy report rows/PDF не удаляются.
- [ ] Новый endpoint не возвращает legacy payload как успешный Career v2.
- [x] Feature flag и rollback не требуют destructive migration.
- [x] Access matrix покрыта contract tests.

## Evidence

- `backend/app/modules/career/contracts.py`, `access.py`
- `backend/app/modules/catalog/service.py`, `backend/app/config.py`
- `backend/tests/unit/test_career/test_product_access_contract.py`
- `uv run pytest tests/unit/test_career/test_product_access_contract.py -q` → `4 passed`
- Local PostgreSQL upgrade/downgrade preserved legacy row counts exactly: `reports=3`, `chart_snapshots=45`, `payments=0`, `entitlements=0`, `users=41`.
