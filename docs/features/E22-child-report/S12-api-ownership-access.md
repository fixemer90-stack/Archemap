# S12: API, ownership и access enforcement

## Статус

🟡 Реализовано и независимо одобрено — R1–R6 закрыты; полный backend 1276 passed, повторный real API/worker/browser smoke зелёный. Backend commit `f02b23b`. Ожидается публикация и exact-SHA CI.

## Контекст

Все routes работают с чувствительными данными несовершеннолетнего, поэтому ownership/access/idempotency должны быть доказаны на каждой операции, включая прямые status, versions и PDF URLs.

## Что сделать

1. Реализовать API из `API.md` и OpenAPI schemas.
2. Применить owner/access guard к каждому nested/root resource.
3. Cross-validate child, session, generation, report и age snapshot IDs.
4. Реализовать indistinguishable 404 и locked redaction.
5. Добавить executable route-to-operation access matrix.

## Затрагиваемые файлы

| Область                                       | Действие          |
| --------------------------------------------- | ----------------- |
| `backend/app/modules/child/router.py`         | Изменить/добавить |
| `backend/app/modules/child/access.py`         | Изменить/добавить |
| `backend/app/modules/child/api_schemas.py`    | Изменить/добавить |
| `contracts/openapi.yaml`                      | Изменить/добавить |
| `backend/tests/integration/test_child_api.py` | Изменить/добавить |

## Критерии приёмки

- [x] Все documented routes зарегистрированы и покрыты.
- [x] Owner/Plus/expired/foreign/deleted/mismatch matrix зелёная.
- [x] Locked payload не содержит protected fields/URLs.
- [x] Idempotency headers исполняются server-side.
- [x] Foreign resources не различимы по status/body/timing class.
- [x] OpenAPI соответствует runtime schemas.

## Verification

Текущие review findings, выполненные проверки и незакрытые gates: [единый evidence report](../../reviews/2026-10-25/E22-S12-S16.md). Операционные процедуры: [rollout/rollback runbook](../../deployment/child-report-rollout.md). Локальные PASS не закрывают staging budgets, live telemetry, deployed SHA или canary.

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
