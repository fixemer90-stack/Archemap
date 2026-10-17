# S05: Parent Style engine

## Статус

✅ Завершено

## Контекст

Нужно детерминированно описать естественный стиль взрослого, используя persisted v2 facts, не превращая пол или одно положение карты в parenting label.

## Что сделать

1. Зафиксированы ровно восемь MVP Parent Style dimensions, двусторонняя семантика шкал и versioned scoring/reference config.
2. Pure deterministic engine собирает support/counter/missing evidence только из persisted Astrotype v2 natal facts и связанных evidence rows.
3. Для результата требуются одновременно минимум две независимые signal families и две разные canonical persisted source lineages. При непустом `source_key` lineage всегда выводится из `(source_table, source_key)`, даже если строка также содержит `source_id`; `(source_table, source_id)` используется только при отсутствии key. Строки без обоих идентификаторов не считаются evidence. Дубликаты одной source lineage дедуплицируются внутри и между facts, включая mixed ID+key/key-only представления одного источника, а breakdown сохраняет canonical lineage refs/count. Иначе score остаётся нейтральным `50`, а confidence — `0`.
4. Placement rules учитывают конкретный знак, aspect rules — тип аспекта, а balance rules — persisted долю; универсальные planet-presence сигналы не используются. Fact weight/confidence и evidence source quality принимаются только как finite `0..1`, без clamp; знак направления задаёт rule weight. Time-sensitive houses/angles fail-closed исключаются без непротиворечивого persisted proof точного пользовательского времени, включая malformed recognized provenance blocks.
5. Builder создаёт все восемь строк в каноническом порядке со стабильными IDs, полным breakdown, evidence refs и source-lineage refs. Repository запрашивает только текущую scoring version, не скрывает unknown/duplicate dimensions до validation и проверяет current-version семантику при reload: точные reference/scale/policy values, непустые уникальные nested refs, канонические evidence/source-lineage unions, family totals и missing families, raw delta, threshold-dependent score и confidence components.
6. Advisory lock и version-aware database uniqueness `(generation_id, dimension, scoring_version)` обеспечивают concurrent replay текущего профиля, сохраняя рядом historical scoring versions. Additive migration имеет условный downgrade: он возвращает старую uniqueness только когда `(generation_id, dimension)` снова уникален, иначе отказывает до DDL/data changes. Ошибки ownership/lineage происходят до writes и безопасны даже при последующем `commit()` вызывающей стороны.
7. Engine не зависит от пола, mutable Self narrative, report payload, LLM или network.

## Затрагиваемые файлы

| Область                                                                        | Действие  |
| ------------------------------------------------------------------------------ | --------- |
| `backend/app/modules/child/parent_style.py`                                    | Добавлен  |
| `backend/app/modules/child/scoring/*`                                          | Добавлены |
| `backend/app/modules/child/models.py`                                          | Изменён   |
| `backend/app/modules/child/repository.py`                                      | Изменён   |
| `backend/alembic/versions/c4d5e6f7a8b9_version_child_parent_style_profiles.py` | Добавлен  |
| `backend/app/reference_data/child/*`                                           | Добавлены |
| `backend/app/modules/astrotype_v2/chart_adapter.py`                            | Изменён   |
| `backend/workers/tasks/astrotype_v2.py`                                        | Изменён   |
| `backend/tests/unit/test_child/test_parent_style_engine.py`                    | Добавлен  |
| `backend/tests/unit/test_child/fixtures/parent_style_golden.json`              | Добавлен  |
| `backend/tests/unit/test_astrotype_v2/test_chart_adapter.py`                   | Изменён   |
| `backend/tests/unit/test_astrotype_v2/test_worker_runtime.py`                  | Изменён   |
| `backend/tests/integration/test_child_parent_style.py`                         | Добавлен  |

## Критерии приёмки

- [x] Все восемь dimensions воспроизводимы без LLM/network и имеют явную семантику `0/50/100`.
- [x] Каждый score имеет version, evidence refs, support/counter/missing evidence, confidence и breakdown.
- [x] Нет gender weights, mutable narrative inputs, universal planet-presence rules и single-family/single-source-lineage conclusions.
- [x] Correlated facts ограничены family cap и не раздувают score.
- [x] Golden fixture проверяет deterministic sign-sensitive output; adversarial tests покрывают shared Moon/Venus source, duplicate/null evidence, distinct source lineages, invalid/NaN/inf numbers и exact-time gate.
- [x] Astrotype v2 adapter сохраняет canonical `birth_time_proof`; worker выводит его только из persisted `birth_time_accuracy` и реального source time. Все присутствующие recognized provenance blocks должны быть dict и непротиворечиво подтверждать exact/non-synthetic/user-supplied timing. Engine/cache version `0.1.6` не переиспользует legacy `0.1.5` charts; история не backfill-ится.
- [x] Output сохраняется versioned в PostgreSQL всеми восемью строками атомарно, owner-scoped, idempotent и concurrency-safe; old/current profiles сосуществуют, current reload фильтруется по scoring version, invalid numeric input не оставляет score rows, а shape-valid, но семантически противоречивые current-version scale/count/ref/family/raw-delta/score/confidence payloads fail-closed отклоняются при reload.
- [x] Migration upgrade/downgrade/re-upgrade проверен на PostgreSQL; downgrade при нескольких scoring versions одной dimension отказывает до изменений и сохраняет revision, rows и новый constraint.

## Verification

- Focused unit: `uv run pytest tests/unit/test_child/test_parent_style_engine.py -q` → `37 passed`, включая direct semantic-integrity counterexamples для current scale/policy, nested/canonical refs, family totals/missing families, raw delta, threshold score и confidence.
- Child unit regression: `uv run pytest tests/unit/test_child -q` → `80 passed`.
- Astrotype chart adapter/worker regression: `uv run pytest tests/unit/test_astrotype_v2/test_chart_adapter.py tests/unit/test_astrotype_v2/test_chart_persistence.py tests/unit/test_astrotype_v2/test_worker_runtime.py -q` → `16 passed`.
- Career + Astrotype fact regression: `uv run pytest tests/unit/test_career tests/unit/test_astrotype_v2/test_*fact*.py -q` → `127 passed`, `1` dependency deprecation warning.
- Disposable PostgreSQL 16 integration: `TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55435/archemap_test uv run pytest tests/integration/test_child_parent_style.py -q` → `1 passed`; test performs real Alembic upgrade/downgrade/re-upgrade, seeds eight old-version rows before current creation/reload, proves lossy downgrade refusal preserves revision/all 16 rows/new constraint, and rejects malformed shape plus arbitrary scale, contradictory policy count, duplicate lineage and empty nested evidence refs.
- Quality: changed-path Ruff check and format check passed; strict mypy passed for the validator and affected unit/integration tests with the existing unused-config note only.
- Docs: exact-path Prettier and `git diff --check` passed.
- Frontend tests are not applicable: S05 adds no route or UI surface; reader/API work remains in S12–S14.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
