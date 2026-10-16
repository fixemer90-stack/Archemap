# S04: Age Resolver и age snapshots

## Статус

✅ Завершено

## Контекст

Возраст влияет на вопросы, приоритет dimensions, примеры и рекомендации, но не должен молча переписывать исторический core report.

## Что сделать

1. Реализован календарный exact-age resolver и семь versioned age stages.
2. Snapshot хранит `as_of_date`, years/months/days, stage, rules version и канонический input hash.
3. Возраст всегда выводится backend из persisted DOB и локальной даты в timezone ребёнка; future DOB и возраст `>=18` отклоняются fail-closed.
4. Immutable age snapshot и отдельный guidance artifact создаются owner-scoped и idempotent; correction DOB в тот же день создаёт новую lineage.
5. Общий pinned selector возвращает один persisted snapshot/guidance contract для будущих web/PDF consumers без реализации UI/PDF из S14.
6. Snapshot считается current только при точном совпадении local `as_of_date`, rules version и DOB-derived input hash; иначе age guidance stale.

## Затрагиваемые файлы

| Область                                                 | Действие          |
| ------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/age_resolver.py`                                      | Добавлен          |
| `backend/app/modules/child/models.py`                                            | Изменён           |
| `backend/app/modules/child/repository.py`                                        | Изменён           |
| `backend/alembic/versions/b3c4d5e6f7a8_include_age_snapshot_input_hash.py`       | Добавлен          |
| `backend/tests/unit/test_child/test_age_resolver.py`                             | Добавлен          |
| `backend/tests/unit/test_child/test_storage_contract.py`                         | Изменён           |
| `backend/tests/integration/test_child_age_snapshots.py`                          | Добавлен          |

## Критерии приёмки

- [x] Future DOB и возраст `>=18` отклоняются.
- [x] Leap-day, month-end и timezone/local-date boundaries покрыты.
- [x] Возраст не принимается от клиента как source of truth; repository читает persisted DOB/timezone.
- [x] Core report payload/version/`updated_at` не меняются после age update.
- [x] Повторный и concurrent update на те же inputs idempotent; DOB correction меняет canonical input hash.
- [x] Web и PDF получают одинаковый shared pinned snapshot read contract; renderer implementation остаётся в S14.

## Verification

- RED: новый unit test сначала завершился `ModuleNotFoundError: app.modules.child.age_resolver`; новый PostgreSQL integration slice сначала дал `3 failed` из-за отсутствующих repository methods; дополнительный leap-month test сначала дал `(1, 1, 1) != (1, 1, 0)`.
- Child unit regression: `uv run pytest tests/unit/test_child -q` → `41 passed in 1.83s`.
- PostgreSQL S04 + S03 chart regression: `TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55434/archemap_test uv run pytest tests/integration/test_child_age_snapshots.py tests/integration/test_child_chart_persistence.py -q` → `4 passed in 176.38s`.
- Existing concurrent guidance regression: targeted `test_child_storage_review.py::test_generation_questionnaire_report_and_age_guidance_are_concurrently_idempotent` → `1 passed in 37.53s`.
- Quality: Ruff check → `All checks passed!`; Ruff format → `7 files already formatted`; mypy → `Success: no issues found in 6 source files` (existing unused-config note only).
- Migration: disposable PostgreSQL 16 upgrade to `b3c4d5e6f7a8`, downgrade to `a2b3c4d5e6f7`, re-upgrade; child table count remained `15`; final constraint is `(child_profile_id, as_of_date, age_rules_version, input_hash)`.
- Global `alembic check` still reports pre-existing non-child metadata drift for legacy `reports`, `report_versions`, `chart_snapshots`, `report_narratives` and `subscription_plans`; no child operation is reported.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
