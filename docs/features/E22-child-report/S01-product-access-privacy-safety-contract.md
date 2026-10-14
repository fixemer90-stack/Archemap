# S01: Product, access, privacy и safety contract

## Статус

⬜ Не начато

## Контекст

До хранения данных несовершеннолетнего нужно зафиксировать продуктовый идентификатор, Plus-access, ownership, privacy/retention и обязательные safety boundaries. В catalog уже существует disabled `child` с `PLUS_ONLY`, но placeholder не является готовым target contract.

## Что сделать

1. Зафиксировать канонический `report_type=child` без нового alias и определить migration boundary с любыми legacy/placeholder artifacts.
2. Согласовать active Plus/grandfather/read-after-expiry policy с E6/E8.
3. Определить ownership matrix для child, questionnaire, generation, report, versions, age updates и PDF.
4. Зафиксировать data minimization, export, archive, hard-delete/anonymization и provider-retention policy.
5. Зафиксировать prohibited claims, adult-action framing, feature flag и rollback semantics.

## Затрагиваемые файлы

| Область                                  | Действие                                |
| ---------------------------------------- | --------------------------------------- |
| `backend/app/modules/catalog/*`          | product/access catalog                  |
| `backend/app/modules/entitlements/*`     | server-side access                      |
| `backend/app/modules/child/contracts.py` | новый target contract                   |
| `docs/architecture/*`                    | privacy/safety policy при необходимости |

## Критерии приёмки

- [ ] Один target identifier используется backend и clients.
- [ ] Frontend не является источником доступа.
- [ ] Foreign/locked response contract не раскрывает child data.
- [ ] Удаление child data не удаляет parent account/billing/other children.
- [ ] Feature flag выключен по умолчанию; rollback non-destructive.
- [ ] Негативный safety contract утверждён до prompt/LLM реализации.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
