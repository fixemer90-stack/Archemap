# S09: Async Career API и access enforcement

## Статус

🟡 Backend API и worker реализованы; DB-backed integration suite остаётся открытым

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

- [x] OpenAPI фиксирует request/response/error schemas и statuses.
- [x] Create не блокируется до полного LLM completion.
- [x] Generation status отражает deterministic и narrative progress отдельно.
- [x] Все endpoints имеют одинаковый ownership/access policy.
- [x] Free/expired direct requests не получают protected payload.
- [x] Idempotent retries не создают второй отчёт/provider calls.
- [x] Legacy `/reports/generate product=career` не используется новым client flow.
- [ ] API integration tests покрывают queued, deterministic_ready, ready, partial/failure и locked states.

## Реализация и проверка

- Отдельный `/api/v1/career` namespace зарегистрирован в FastAPI; legacy `/reports/generate` не импортируется.
- `career_generations` хранит durable create/regenerate jobs и уникальный `(user_id, operation, idempotency_key)`.
- Worker сохраняет `deterministic_ready` до provider calls и не пересчитывает deterministic artifacts при regenerate.
- Locked payload не содержит scores, facts, answers, sections, report IDs или artifact URLs.
- `uv run pytest tests/unit/test_career -q` — 51 passed.
- `uv run ruff check app/api/v1/__init__.py app/modules/career workers/tasks/career.py tests/unit/test_career` — passed.
- `uv run mypy app/modules/career/api_runtime.py app/modules/career/api_schemas.py app/modules/career/repository.py app/modules/career/router.py workers/tasks/career.py` — passed.

Открытый пункт: нужен DB-backed API integration suite с реальной транзакцией/очередью для всех lifecycle и locked states.
