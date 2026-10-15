# S03: Child chart и birth-time confidence

## Статус

✅ Завершено

## Контекст

Расчёт детской карты должен переиспользовать v2 natal engine, но явно ограничивать факты при приблизительном или неизвестном времени. Synthetic defaults нельзя выдавать за точные данные.

## Что сделать

1. Создать child chart adapter поверх v2 chart calculation/persistence.
2. Реализовать `exact|approximate|unknown` policy и versioned exclusions.
3. Для approximate времени оценивать устойчивость факта в заданном окне.
4. Исключать houses/angles/overlays/time-sensitive Moon signals при недостаточной уверенности.
5. При исправлении birth data создавать новую chart lineage без overwrite.

## Затрагиваемые файлы

| Область                                                       | Действие                          |
| ------------------------------------------------------------- | --------------------------------- |
| `backend/app/modules/child/chart_adapter.py`                  | Изменить/добавить                 |
| `backend/app/modules/child/birth_time_policy.py`              | Изменить/добавить                 |
| `backend/app/modules/astrotype_v2/*`                          | reuse, без ослабления v2 contract |
| `backend/tests/unit/test_child/test_birth_time_confidence.py` | Изменить/добавить                 |

## Критерии приёмки

- [x] Unknown time не создаёт houses, ASC, MC или house synastry.
- [x] Approximate facts имеют stability evidence и exclusions.
- [x] Confidence снижается объяснимо, а не случайно.
- [x] Gender не влияет на chart/scoring.
- [x] Golden fixtures покрывают exact/approximate/unknown и Moon sign boundary.
- [x] Birth-data correction сохраняет старую chart/report lineage.

## Реализация

- `child-birth-time-policy-v1` фиксирует `exact|approximate|unknown`, versioned `±60`-минутное окно approximate и offsets `[-60, -30, 0, 30, 60]`.
- Exact сохраняет полный chart payload. Approximate сохраняет только устойчивые planet-sign/aspect facts, обнуляет непроверенную числовую точность и всегда исключает houses, angles, assignments и overlays. Unknown использует local-noon только как technical reference, проверяет устойчивость по всему local birth date и fail-closed исключает houses/ASC/MC/overlays и Moon-dependent facts при смене знака.
- Для каждого sampled fact сохраняются observed values, sample count, детерминированный confidence и причина exclusion; аспекты с нестабильным телом также исключаются.
- `ChildChartInput` намеренно не содержит gender/caregiver role, поэтому эти поля не могут попасть в chart/scoring input.
- Repository append-only создаёт `ChildChartVersion` под PostgreSQL advisory lock, повторный/concurrent одинаковый input возвращает одну строку, а разные birth-data inputs получают последовательные immutable versions.
- Birth-data correction атомарно обновляет только текущий child profile и добавляет новую chart version; существующий report продолжает ссылаться на старый chart lineage.

## Verification

- RED: focused unknown policy завершился `ModuleNotFoundError: app.modules.child.chart_adapter`; focused approximate/exact завершились ожидаемыми `NotImplementedError`; Moon-dependent aspect assertions завершились RED, пока unstable Moon aspect сохранялся; PostgreSQL correction test завершился RED на отсутствующем `correct_birth_data_and_create_chart`.
- `uv run pytest tests/unit/test_child -q` → `19 passed`.
- `uv run pytest tests/unit/test_astrotype_v2/test_chart_adapter.py tests/unit/test_astrotype_v2/test_chart_persistence.py tests/unit/test_astrotype_v2/test_chart_contract.py tests/chart/test_chart_engine.py -q` → `29 passed`.
- Disposable PostgreSQL 16: `TEST_DATABASE_URL=... uv run pytest tests/integration/test_child_storage.py tests/integration/test_child_storage_review.py tests/integration/test_child_chart_persistence.py -q` → `8 passed`, включая separate-transaction concurrency, correction lineage и старый report FK.
- `uv run ruff check ...` → `All checks passed!`; `uv run ruff format --check ...` → все затронутые Python files отформатированы.
- `uv run mypy app/modules/child/birth_time_policy.py app/modules/child/chart_adapter.py app/modules/child/repository.py tests/unit/test_child/test_birth_time_confidence.py tests/integration/test_child_chart_persistence.py` → `Success: no issues found in 5 source files`.
- Golden JSON fixtures запускают real chart engine для exact, approximate Moon boundary и unknown Moon boundary.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
