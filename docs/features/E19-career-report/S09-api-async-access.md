# S09: Async Career API и access enforcement

## Статус

🟡 Частично — target API работает; canonical OpenAPI и полная route/access/idempotency matrix не закрыты

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

- [ ] Канонический `contracts/openapi.yaml` фиксирует Career request/response/error schemas и statuses.
- [x] Create не блокируется до полного LLM completion.
- [x] Generation status отражает deterministic и narrative progress отдельно.
- [ ] Все endpoints покрыты параметризованным route-level ownership/access test.
- [ ] Free/expired direct requests проверены через реальный entitlement lifecycle без подмены policy denial.
- [ ] Последовательные и конкурентные idempotent retries не создают второй отчёт/provider calls.
- [x] Legacy `/reports/generate product=career` не используется новым client flow.
- [ ] API integration tests покрывают queued, deterministic_ready, ready, partial failure, terminal failed и locked states.

## Реализация и проверка

- Отдельный `/api/v1/career` namespace зарегистрирован в FastAPI; legacy `/reports/generate` не импортируется.
- `career_generations` хранит durable create/regenerate jobs и уникальный `(user_id, operation, idempotency_key)`.
- Worker сохраняет `deterministic_ready` до provider calls и не пересчитывает deterministic artifacts при regenerate.
- Locked payload не содержит scores, facts, answers, sections, report IDs или artifact URLs.
- `uv run pytest tests/unit/test_career -q` — 64 passed в closing S12 verification.
- Isolated PostgreSQL `uv run pytest tests/integration/test_career_api.py -q` — 1 passed.
- `uv run ruff check app/api/v1/__init__.py app/modules/career workers/tasks/career.py tests/unit/test_career` — passed.
- `uv run mypy app/modules/career/api_runtime.py app/modules/career/api_schemas.py app/modules/career/repository.py app/modules/career/router.py workers/tasks/career.py` — passed.

DB-backed suite использует реальную PostgreSQL transaction/schema и подменяет только enqueue transport, чтобы детерминированно доказать idempotency без внешнего broker.

## Аудит 2026-09-26

FastAPI-generated OpenAPI содержит Career routes, но CI-канонический `contracts/openapi.yaml` не содержит `/career/*`. Source audit подтверждает access dependency на routes, однако полной параметризованной route matrix нет. Integration suite проверяет последовательный retry и основные progressive states, но не конкурентный race и отдельный terminal `failed` case.
