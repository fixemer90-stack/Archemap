# S03: Сохранить grandfathered access к target E19

## Статус

⬜ Не начато

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

- [ ] Active Plus получает target Career access.
- [ ] Active grandfathered Career entitlement получает тот же target access.
- [ ] Expired/revoked entitlement получает locked response.
- [ ] Legacy row без entitlement не открывает target E19.
- [ ] Entitlement без legacy row позволяет создать target report.
- [ ] Ownership применяется после access policy на всех artifact endpoints.
