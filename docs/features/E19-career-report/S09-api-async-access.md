# S09: Async Career API и access enforcement

## Статус

⬜ Не начато

## Контекст

Текущий Career flow вызывает synchronous `/reports/generate` и ждёт `ready` до 30 секунд. Новый pipeline требует questionnaire state, durable generation ID, progressive report и единый Plus/ownership gate.

## Что сделать

Добавить отдельный Career API namespace, не маскируя его под legacy endpoint:

| Method | Path                                                  | Назначение                            |
| ------ | ----------------------------------------------------- | ------------------------------------- |
| GET    | `/api/v1/career/questionnaires/current?profile_id=`   | Текущая версия и draft                |
| PUT    | `/api/v1/career/questionnaires/{session_id}/answers`  | Сохранить draft                       |
| POST   | `/api/v1/career/questionnaires/{session_id}/complete` | Зафиксировать ответы                  |
| POST   | `/api/v1/career/reports`                              | Создать/вернуть idempotent generation |
| GET    | `/api/v1/career/generations/{generation_id}`          | Durable progress/status               |
| GET    | `/api/v1/career/reports/{report_id}`                  | Progressive assembled report          |
| GET    | `/api/v1/career/reports/{report_id}/sections`         | Section states/payloads               |
| POST   | `/api/v1/career/reports/{report_id}/regenerate`       | Safe section/full narrative retry     |
| GET    | `/api/v1/career/reports/{report_id}/pdf`              | Download artifact                     |

## Контракты

- Create возвращает `202` с `generation_id` и, когда доступно, `report_id`.
- `deterministic_ready` позволяет читать deterministic report до complete narrative.
- Frontend polling идёт по generation ID, не по profile ID и не по будущему report ID.
- Create/complete/regenerate требуют `Idempotency-Key`.
- Backend проверяет ownership, active Plus/grandfather entitlement и completed questionnaire.
- Locked responses не содержат Career scores, facts, sections или artifact URL.
- Unknown report IDs не должны раскрывать ownership/existence.

## Критерии приёмки

- [ ] OpenAPI фиксирует request/response/error schemas и statuses.
- [ ] Create не блокируется до полного LLM completion.
- [ ] Generation status отражает deterministic и narrative progress отдельно.
- [ ] Все endpoints имеют одинаковый ownership/access policy.
- [ ] Free/expired direct requests не получают protected payload.
- [ ] Idempotent retries не создают второй отчёт/provider calls.
- [ ] Legacy `/reports/generate product=career` не используется новым client flow.
- [ ] API integration tests покрывают queued, deterministic_ready, ready, partial/failure и locked states.
