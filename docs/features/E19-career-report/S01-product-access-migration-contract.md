# S01: Product, access и migration contract

## Статус

⬜ Не начато

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

## Затрагиваемые документы/файлы

| Область                              | Действие                           |
| ------------------------------------ | ---------------------------------- |
| `backend/app/modules/catalog/*`      | Канонический report/access catalog |
| `backend/app/modules/entitlements/*` | Plus/grandfather mapping           |
| `docs/features/E6-*`, `E8-*`         | Согласование доступа               |
| `contracts/openapi.yaml`             | Stable report type                 |
| migrations                           | Только additive mapping/flags      |

## Критерии приёмки

- [ ] Один канонический Career report type используется backend и всеми клиентами.
- [ ] Plus/grandfather policy не зависит только от frontend.
- [ ] Судьба `career_full` и существующих покупок описана без потери доступа.
- [ ] Legacy report rows/PDF не удаляются.
- [ ] Новый endpoint не возвращает legacy payload как успешный Career v2.
- [ ] Feature flag и rollback не требуют destructive migration.
- [ ] Access matrix покрыта contract tests.
