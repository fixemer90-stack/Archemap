# S02: Storage, lineage и multiple children

## Статус

✅ Завершено

## Контекст

Child Report требует durable раздельного хранения child records, deterministic scores/evidence, answers, generations, immutable core reports и age snapshots. Один mutable JSON создаст риск cross-child mixing и потери provenance.

## Что сделать

1. Добавить additive ORM/migrations для сущностей SRS E22.
2. Связать каждую строку с owner, child, parent chart, child chart, generation и version lineage.
3. Разделить core report version и age guidance snapshots.
4. Добавить repository guards против child/report/session mismatch и cross-owner access.
5. Реализовать idempotency/concurrency constraints и безопасный archive/delete flow.

## Затрагиваемые файлы

| Область                                                     | Действие          |
| ----------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/models.py`                       | Изменить/добавить |
| `backend/app/modules/child/schemas.py`                      | Изменить/добавить |
| `backend/app/modules/child/repository.py`                   | Изменить/добавить |
| `backend/alembic/versions/*_add_child_report_foundation.py` | Изменить/добавить |
| `backend/tests/unit/test_child/test_storage_contract.py`    | Изменить/добавить |

## Критерии приёмки

- [x] Миграции additive/reversible и не затрагивают существующие user/profile/report/payment rows.
- [x] Два ребёнка одного owner имеют независимые artifacts.
- [x] Core/history и age snapshots immutable.
- [x] Artifact восстанавливается из PostgreSQL без Redis/LLM cache.
- [x] Concurrent одинаковый idempotency key не создаёт дубликаты.
- [x] Archive/delete contract доказан integration tests.

## Реализация

- Добавлены 15 additive child-domain tables и revision `a2b3c4d5e6f7` поверх `f1a2b3c4d5e6`.
- Composite FK/unique lineage не допускает смешивание child, chart, generation, questionnaire, report и age snapshot; owner/profile/parent-chart связи дополнительно проверяет repository.
- PostgreSQL и ORM отклоняют update/direct delete immutable chart, snapshot, score/evidence, answers, facts, core report и age-guidance rows. Privacy purge разрешается только внутри owner-scoped `purge_child_domain` transaction.
- Реализованы conflict-safe idempotent операции для child create, generation/regeneration/age-update operations, questionnaire completion, core report и age guidance.
- Реализованы owner-scoped archive, hard delete полного child aggregate, privacy-safe `audit_log` event и rollback без частично удалённого graph.
- `load_report_graph` восстанавливает из PostgreSQL child chart, generation, scores/evidence, questionnaire/answers, context, guidance facts, segments, core report и pinned age guidance без Redis или LLM cache.

## Review

- Первый независимый spec review выявил пять gaps: lineage, immutability, idempotency, purge и PostgreSQL reconstruction.
- После remediation добавлены DB constraints, append-only guards, repository operations и PostgreSQL integration coverage.
- Повторный review запросил cross-owner regression, полный rollback graph/audit proof и синхронизацию документации; эти замечания закрыты отдельными regression assertions и этим status-sync.

## Verification

- `uv run pytest tests/unit/test_child -q` → `13 passed`.
- `uv run pytest tests/integration/test_child_storage.py tests/integration/test_child_storage_review.py -q` → PostgreSQL-backed suite, включая concurrency, lineage, immutability, full reconstruction, purge и rollback.
- `uv run pytest tests/unit -q` → `722 passed`, 5 pre-existing warnings.
- `uv run ruff check ...` → `All checks passed!`; `uv run ruff format --check ...` → все затронутые файлы отформатированы.
- `uv run mypy app/modules/child tests/unit/test_child tests/integration/test_child_storage.py tests/integration/test_child_storage_review.py` → `Success: no issues found in 10 source files`.
- На disposable PostgreSQL выполнен `upgrade f1a2b3c4d5e6 → a2b3c4d5e6f7 → downgrade → upgrade`; head/current = `a2b3c4d5e6f7`.
- Raw SQL smoke подтвердил: immutable trigger отклоняет update/direct delete, privacy purge удаляет child aggregate и сохраняет `users`, `person_profiles`, parent natal chart.
- `alembic check` не показывает drift по новым child tables; остаётся существовавший до E22 legacy metadata drift для старых reports/chart tables и subscription-plan index.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
