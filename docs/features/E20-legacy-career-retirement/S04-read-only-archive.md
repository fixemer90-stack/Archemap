# S04: Read-only compatibility для старых rows и PDF

## Статус

⬜ Не начато

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

- [ ] GET legacy report возвращает исходный persisted payload владельцу.
- [ ] GET/HEAD PDF возвращает валидный PDF без DB mutation.
- [ ] Before/after DB snapshot подтверждает неизменность version/status/payload.
- [ ] Старые допустимые fixture shapes читаются без 500.
- [ ] Target Career endpoint возвращает `404` для legacy report ID.
- [ ] Чужой пользователь получает ownership-safe denial без content leak.
