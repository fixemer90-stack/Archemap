# S01: Product, access, privacy и safety contract

## Статус

✅ Завершено — backend-owned product/access, privacy/deletion и child-safety boundaries закреплены исполняемыми контрактами

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

- [x] Один target identifier используется backend и clients.
- [x] Frontend не является источником доступа.
- [x] Foreign/locked response contract не раскрывает child data.
- [x] Удаление child data не удаляет parent account/billing/other children.
- [x] Feature flag выключен по умолчанию; rollback non-destructive.
- [x] Негативный safety contract утверждён до prompt/LLM реализации.

## Зафиксированные решения

- Канонический target identifier: `child`; отдельный `child_v2` alias не вводится.
- Access class: `plus_only`. Разрешён активный account-wide Plus или текущий прямой product-scoped grant `child`; direct grant не повышает весь аккаунт до Plus.
- Read-after-expiry: protected Child artifacts блокируются без удаления и снова открываются после восстановления валидного доступа.
- Legacy/placeholder payload не может быть target fallback: `LEGACY_PAYLOAD_FALLBACK_ALLOWED=False`.
- Locked metadata ограничено безопасным allowlist; имя, birth data, answers, scores, facts, narrative и artifact URL являются protected.
- Удаление может каскадировать только внутри root `child_profile`; user, parent profile, billing, entitlements и другие children запрещены как cascade targets.
- Обычное скрытие использует `archived`; hard delete выполняет `purge_child_domain` от внешних/leaf artifacts к root: provider payloads → PDF → age guidance/reports/segments → Guidance Facts/context/answers/sessions → interaction/synastry/need/parent scores → age snapshots → chart versions → child profile.
- Retention: artifacts хранятся до явного owner hard-delete; privacy-safe audit event сохраняет только event/owner/child ID/time/result и запрещает имя, birth data, answers и narrative.
- Owner export включает archived records, все 14 child-domain persisted entity groups и PDF artifacts; export содержит персональные данные только после owner authorization и требует encrypted delivery, при этом provider credentials исключаются.
- Foreign resource contract возвращает неразличимый `404 Child resource not found` до загрузки protected payload.
- Feature flag `CHILD_REPORT_ENABLED=False` по умолчанию; выключение не удаляет persisted artifacts.
- Rollback contract запрещает новые writes при flag-off, сохраняет существующие artifacts и оставляет read path доступным для уже созданных объектов при валидном access.
- Негативный safety contract запрещает диагнозы, attachment labels, fatal/adult-outcome predictions, ability ranking, fixed traits, blame, medical/legal advice, unsafe discipline, age-inappropriate и unsupported recommendations.

## Evidence

- `backend/app/modules/child/contracts.py`
- `backend/app/modules/child/access.py`
- `backend/app/config.py`
- `backend/tests/unit/test_child/test_product_access_privacy_contract.py`
- RED: `uv run pytest tests/unit/test_child/test_product_access_privacy_contract.py -q` → `5 failed` (`app.modules.child` отсутствовал).
- Review RED: после независимого spec review добавлены исполняемые foreign-resource, retention/delete-order/audit и rollback contracts; targeted suite показал `3 failed, 3 passed` до реализации.
- Second review RED: complete delete ordering и owner export scope → `2 failed, 5 passed` до реализации.
- GREEN: `uv run pytest tests/unit/test_child/test_product_access_privacy_contract.py -q` → `7 passed`.

## Verification

- Targeted unit contract suite выполнен.
- Repo-native lint/type и соседняя authorization/catalog regression выполняются перед commit.
- Runtime routes появятся в S12; S01 фиксирует fail-closed operation matrix до создания handlers.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
