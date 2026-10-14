# S02: Storage, lineage и multiple children

## Статус

⬜ Не начато

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

- [ ] Миграции additive/reversible и не затрагивают существующие user/profile/report/payment rows.
- [ ] Два ребёнка одного owner имеют независимые artifacts.
- [ ] Core/history и age snapshots immutable.
- [ ] Artifact восстанавливается из PostgreSQL без Redis/LLM cache.
- [ ] Concurrent одинаковый idempotency key не создаёт дубликаты.
- [ ] Archive/delete contract доказан integration tests.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
