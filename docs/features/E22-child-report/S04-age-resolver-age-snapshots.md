# S04: Age Resolver и age snapshots

## Статус

✅ Завершено

## Контекст

Возраст влияет на вопросы, приоритет dimensions, примеры и рекомендации, но не должен молча переписывать исторический core report.

## Что сделать

1. Реализован календарный exact-age resolver и семь versioned age stages.
2. Snapshot хранит `as_of_date`, years/months/days, stage, rules version и канонический input hash.
3. Возраст всегда выводится backend из persisted DOB и серверного UTC clock, преобразованного в локальную дату persisted timezone ребёнка; future DOB и возраст `>=18` отклоняются fail-closed.
4. Immutable age snapshot и отдельный guidance artifact создаются owner-scoped и idempotent; correction DOB в тот же день создаёт новую lineage.
5. Общий pinned selector возвращает один persisted snapshot/guidance contract для будущих web/PDF consumers без реализации UI/PDF из S14.
6. Snapshot считается current только при точном совпадении local `as_of_date`, rules version и DOB-derived input hash; иначе age guidance stale.
7. Birth-data correction и snapshot creation используют один централизованный child-lineage advisory lock, поэтому snapshot со старой DOB не может зафиксироваться после correction.
8. Downgrade новой uniqueness выполняется только когда старая уникальность представима без потери данных; при same-day duplicate lineage migration отказывает до DDL и сохраняет revision, строки и новый constraint.

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
- [x] Public snapshot/update repository API не принимает caller-controlled дату; deterministic tests могут передать только timezone-aware internal `now`.
- [x] Core report payload/version/`updated_at` не меняются после age update.
- [x] Повторный и concurrent update на те же inputs idempotent; DOB correction меняет canonical input hash.
- [x] PostgreSQL race regression без timing sleeps доказывает общую блокировку correction и snapshot creation.
- [x] Downgrade пустой/одиночной lineage проходит, duplicate lineage fail-safe отклоняется без удаления/merge history и без частично применённой schema revision.
- [x] Web и PDF получают одинаковый shared pinned snapshot read contract; renderer implementation остаётся в S14.

## Verification

- RED: новый unit test сначала завершился `ModuleNotFoundError: app.modules.child.age_resolver`; новый PostgreSQL integration slice сначала дал `3 failed` из-за отсутствующих repository methods; дополнительный leap-month test сначала дал `(1, 1, 1) != (1, 1, 0)`.
- Remediation RED: focused storage contract produced `2 failed, 6 passed` before implementation: public repository signatures still exposed `as_of`, and downgrade lacked duplicate-lineage refusal.
- Child unit regression: `uv run pytest tests/unit/test_child -q` → `42 passed in 2.76s`.
- PostgreSQL S04 + S03 chart regression: `TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55434/archemap_test uv run pytest tests/integration/test_child_age_snapshots.py tests/integration/test_child_chart_persistence.py -q` → `6 passed in 245.30s`.
- Existing concurrent guidance regression: targeted `test_child_storage_review.py::test_generation_questionnaire_report_and_age_guidance_are_concurrently_idempotent` → `1 passed in 36.95s`.
- Quality: Ruff check → `All checks passed!`; Ruff format → `4 files already formatted`; mypy → `Success: no issues found in 3 source files` (existing unused-config note only).
- Migration: disposable PostgreSQL 16 proved empty lineage `0→0` rows and single lineage `1→1` rows across downgrade `b3c4d5e6f7a8 → a2b3c4d5e6f7` and re-upgrade. Duplicate lineage downgrade exited `1` with `Refusing lossy downgrade`; revision remained `b3c4d5e6f7a8`, both rows remained, and `uq_child_age_snapshots_profile_date_rules_input` remained installed.
- Global `alembic check` still reports pre-existing non-child metadata drift for legacy `reports`, `report_versions`, `chart_snapshots`, `report_narratives` and `subscription_plans`; no child operation is reported.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
