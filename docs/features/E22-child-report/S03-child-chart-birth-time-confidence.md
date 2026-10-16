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

- `child-birth-time-policy-v3` фиксирует `exact|approximate|unknown`, versioned `±60`-минутное окно approximate и offsets `[-60, -30, 0, 30, 60]`. Переход с v2 меняет input hash из-за ужесточения persisted semantics: metadata unknown-time теперь разрешает только `stable_planet_signs|stable_aspects`, без удалённых numeric `planet_positions`.
- Exact сохраняет полный chart payload. Approximate сохраняет только устойчивые planet-sign/aspect facts, обнуляет непроверенную числовую точность и всегда исключает houses, angles, assignments и overlays. Unknown использует local-noon только как technical reference и fail-closed всегда исключает houses/ASC/MC/overlays, Moon и Moon-dependent aspects; остальные sign facts проходят только при согласии versioned samples.
- Exact/approximate принимают только offset-naive wall time. Для IANA timezone wall time должен однозначно round-trip преобразовываться в один UTC instant: DST gaps/folds отклоняются, а approximate fail-closed отклоняется, если любой sample в `±60`-минутном окне попадает в gap/fold или samples перестают быть различными instants.
- Для каждого sampled fact сохраняются observed values, sample count и детерминированный confidence. Fail-closed Moon и аспекты с нестабильным телом дополнительно сохраняют machine-readable причину exclusion.
- `ChildChartInput` намеренно не содержит gender/caregiver role, поэтому эти поля не могут попасть в chart/scoring input.
- `ChildChartBuild` несёт typed `source_input` и versioned `input_hash`. Persistence-only builders могут не задавать source metadata, но birth-data correction требует её и до любых mutation/persistence сверяет date, time, confidence, coordinates, timezone, house system и hash.
- Repository append-only создаёт `ChildChartVersion` под PostgreSQL advisory lock, повторный/concurrent одинаковый input возвращает одну строку, а разные birth-data inputs получают последовательные immutable versions.
- Birth-data correction сначала разрешает все domain mismatch/idempotency ошибки и только после успешного создания новой chart lineage меняет текущий child profile. Поэтому caller может поймать reused-chart mismatch и commit без скрытого изменения профиля; существующий report продолжает ссылаться на старый chart lineage.

## Verification

- RED remediation: focused child policy suite → `8 failed, 4 passed` на отсутствующих v3 metadata/source binding, DST gap/fold и offset-aware validations; focused PostgreSQL correction test → ожидаемый `TypeError` на отсутствующем `house_system` correction contract.
- `uv run pytest tests/unit/test_child -q` → `25 passed`.
- `uv run pytest tests/unit/test_astrotype_v2/test_chart_adapter.py tests/unit/test_astrotype_v2/test_chart_persistence.py tests/unit/test_astrotype_v2/test_chart_contract.py tests/chart/test_chart_engine.py -q` → `29 passed`.
- Disposable PostgreSQL 16: `TEST_DATABASE_URL=... uv run pytest tests/integration/test_child_storage.py tests/integration/test_child_storage_review.py tests/integration/test_child_chart_persistence.py -q` → `8 passed`, включая separate-transaction concurrency, correction lineage и старый report FK.
- `uv run ruff check ...` → `All checks passed!`; `uv run ruff format --check ...` → все затронутые Python files отформатированы.
- `uv run mypy app/modules/child/birth_time_policy.py app/modules/child/chart_adapter.py app/modules/child/repository.py tests/unit/test_child/test_birth_time_confidence.py tests/integration/test_child_chart_persistence.py` → `Success: no issues found in 5 source files`.
- Golden JSON fixtures запускают real chart engine для exact, approximate Moon boundary и unknown Moon boundary; regression tests доказывают fail-closed unknown-time Moon, v3 lineage hash, strict `America/New_York` DST handling, source-input/hash binding и отсутствие profile mutation после caught reused-chart mismatch + commit.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
