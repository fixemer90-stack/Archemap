# S04: Read-only compatibility для старых rows и PDF

## Статус

🟢 Local post-fix persisted compatibility verified, fresh SPEC/code-security PASS (`deleg_b016d85a`, `deleg_fdb0b999`). Production historical-shape census отсутствует, данные не удаляются; это не live acceptance.

## Контекст

Существующие Career v1 rows могут быть единственной копией ранее выданного пользователю результата. Read path должен сохранять bytes/semantics и не запускать retired generator.

## Что сделать

1. Определить legacy Career rows как immutable historical artifacts.
2. Отключить engine-version refresh, chart-based refresh, version archive и regeneration при чтении.
3. Сохранить ownership-protected JSON и PDF endpoints на переходный период.
4. Проверить старые payload shapes, missing optional fields и readable PDF.
5. Добавить явную archive/deprecation маркировку без подмены содержимого.

## Файлы

| Файл                                           | Действие                        |
| ---------------------------------------------- | ------------------------------- |
| `backend/app/modules/reports/service.py`       | No-refresh invariant для Career |
| `backend/app/modules/reports/router.py`        | Read-only API behavior          |
| `backend/app/modules/reports/pdf.py`           | Legacy fixture compatibility    |
| `backend/tests/integration/test_career_api.py` | Cross-boundary negative tests   |
| Legacy report/PDF tests                        | Persisted fixture readability   |

## Критерии приёмки

- [x] GET legacy report возвращает исходный persisted payload владельцу.
- [x] GET/HEAD PDF возвращает валидный PDF без DB mutation.
- [x] Before/after DB snapshot подтверждает неизменность version/status/payload.
- [x] Старые допустимые fixture shapes читаются без 500.
- [x] Target Career endpoint возвращает `404` для legacy report ID.
- [x] Чужой пользователь получает ownership-safe denial без content leak.

## Evidence

Parent post-fix full integration suite **230 passed**: fresh-session before/after snapshots для reports/versions/narratives/charts/grants, six historical statuses, stale engine/chart и minimal payloads, JSON/list/versions и GET/HEAD/POST real PDF. Empty archive честно unavailable, без переписывания saved status/payload. SPEC `deleg_644a7521`: PASS; independently mocked-persistence ASGI с real PDF подтвердил 6 JSON reads / 18 PDF requests и отсутствие flush/commit/refresh. Это independent rendering/source proof, не второй независимый persisted DB запуск и не production compatibility census.
