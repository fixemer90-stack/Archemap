# S03: Сохранить grandfathered access к target E19

## Статус

🟢 Local access matrix и post-fix persisted regression verified; fresh SPEC/code-security PASS (`deleg_b016d85a`, `deleg_fdb0b999`). Canonical grant semantics сохранены без conversion в Plus. Publication/CI и live smoke учитываются в S07.

## Контекст

`product="career"` используется не только legacy reports, но и как законный grandfathered entitlement. Его нельзя удалить вместе с v1 generator.

## Что сделать

1. Сохранить canonical constant legacy Career entitlement в target access policy.
2. Покрыть create/questionnaire/generation/read/versions/PDF access matrix.
3. Проверить active, expired, revoked и duplicate entitlement rows.
4. Доказать, что доступ не зависит от наличия legacy `reports` row.
5. Доказать, что entitlement не разрешает читать чужой target или legacy report.

## Файлы

| Файл                                      | Действие                                |
| ----------------------------------------- | --------------------------------------- |
| `backend/app/modules/career/access.py`    | Сохранить policy                        |
| `backend/app/modules/career/contracts.py` | Canonical identifiers                   |
| Career integration/access tests           | Полная entitlement matrix               |
| E8/E19 docs                               | Синхронизировать compatibility contract |

## Критерии приёмки

- [x] Active Plus получает target Career access.
- [x] Active grandfathered Career entitlement получает тот же target access.
- [x] Expired/revoked entitlement получает locked response.
- [x] Legacy row без entitlement не открывает target E19.
- [x] Entitlement без legacy row позволяет создать target report.
- [x] Authentication и минимальная ownership metadata проверяются до protected payload; затем применяется access policy. Чужие/nonexistent artifact IDs дают одинаковый безопасный отказ, без чтения legacy/target содержимого.

## Evidence

SPEC `deleg_644a7521`: PASS по access/ownership ordering и expanded persisted matrix в `backend/tests/integration/test_career_api.py`; reviewer сам DB не запускал. Parent post-fix full integration suite **230 passed**, включая Plus/direct без legacy rows, expired/revoked/future/subscription-backed/duplicate grants, report-row-only denial, foreign/nonexistent и legacy-ID target negatives. Никакие customer grants не изменялись. Browser/stage/live smoke не заменён этим локальным API/DB evidence.

## Уточнение access order

Старая формулировка «ownership после access policy» не разрешает загружать protected payload до авторизации. E20 сохраняет действующий безопасный контракт E8/E19: authentication → ownership/existence metadata → access policy → payload. Исторический direct Career grant не превращается в account-wide Plus и не зависит от существования generic report row.
