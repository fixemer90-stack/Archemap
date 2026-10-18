# S07: Synastry и Interaction engine

## Статус

✅ Завершено

## Контекст

Главный deterministic слой должен объединять Parent Style, Child Needs и pair synastry, объясняя natural matches и friction без вредного compatibility score.

## Что сделать

1. Рассчитать разрешённые cross-chart aspects и overlays согласно confidence обоих charts.
2. Построить восемь MVP Interaction Dimensions.
3. Сохранять pair evidence, contribution, direction, caps и version.
4. Особо ограничить Saturn/pressure interpretations.
5. Сформировать patterns natural_match/moderate_tension/high_attention без verdict о совместимости.

## Реализация

- `child-synastry-reference-1` строит pair-bound cross-chart aspects только из канонических persisted longitudes и полного нормативного directional pair/orb catalog. Exact/exact пары дополнительно поддерживают persisted ASC/MC ↔ personal-planet contacts в обоих направлениях; missing/unreliable angles fail closed.
- Для `approximate/unknown` child chart cross-chart longitude и angle evidence исключается fail-closed: sampled sign/aspect stability S03 не доказывает устойчивость pair aspect. Malformed/NaN/out-of-range exact child longitude закрывает весь builder, а conflicting canonical duplicate reject без partial rows.
- House overlays рассчитываются только при exact timing proof обоих charts и ровно 12 input records, где каждый `house_number` встречается ровно один раз и cusps образуют один строго возрастающий cyclic zodiac обход. Identical/conflicting 13th duplicates, missing/malformed house records, repeated longitudes и zero-width/non-monotonic arcs fail closed для всей overlay-части. Валидный wraparound через `360° → 0°` поддерживается.
- Exact-time overlays versioned и bounded: используются как pair context с отдельными correlation families и не подменяют Parent Style/Child Needs fit.
- `child-interaction-mvp-1` возвращает ровно восемь dimensions в каноническом порядке. Fit evidence извлекает underlying canonical lineage refs из semantically validated current Parent Style/Child Needs breakdown. Derived score IDs не считаются независимыми sources; overlapping raw ownership canonicalizes/deduplicates correlated fit families. Ненейтральный score требует минимум две independent families, две independent persisted lineages и хотя бы один fit signal; pair-only, shared-lineage и Saturn-only evidence остаются neutral.
- Correlated evidence capped; все Saturn cross-aspects используют одну `pair:saturn-pressure` family. Positive и negative contradictory leaves capped пропорционально и сохраняются при exact cancellation (`+0.08/-0.08`), поэтому neutral final score не скрывает disagreement.
- `e6f7a8b9c0d1` добавляет pair chart lineage, version-aware uniqueness, прямой и composite FK к child chart, S07 metadata/schema parity и fail-safe downgrade preflight до DDL.
- Repository использует PostgreSQL advisory lock, current-version filtering и общий для create/reload pre-read source-snapshot helper. Под `READ COMMITTED` helper одной authoritative owner-scoped query сначала берёт transaction-scoped `FOR SHARE` lock на exact `ChildProfile` и только после этого читает mutable `parent_profile_id`; далее lock order одинаков для exact generation, current Parent Style rows, current Child Needs rows, parent chart root, child chart root, parent positions/angles и parent houses. Все authoritative reads используют fresh/`populate_existing` semantics. Raw concurrent `UPDATE/DELETE` source rows блокируется до конца loader transaction, а unrelated child row не блокируется. Persisted evidence и scores сравниваются с regenerated artifacts целиком, включая IDs, source contracts, payload, contributions, row refs, factor values/quality/weights, raw contribution, underlying lineage, canonical family grouping и leaf UUID. Изменение child route, timing proof или upstream rows делает stale persisted profile недействительным; identity-map preload не может скрыть committed изменения другой session.
- Deterministic interaction/synastry UUID namespaces и formulas вынесены в общий `interaction_identity.py`, используемый generator и validator.

## Затрагиваемые файлы

| Область                                                    | Действие          |
| ---------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/synastry.py`                    | Изменить/добавить |
| `backend/app/modules/child/interaction.py`                 | Изменить/добавить |
| `backend/app/modules/child/repository.py`                  | Изменить/добавить |
| `backend/app/reference_data/child/*`                       | Изменить/добавить |
| `backend/tests/unit/test_child/test_interaction_engine.py` | Изменить/добавить |
| `backend/tests/integration/test_child_interaction.py`      | Изменить/добавить |

## Критерии приёмки

- [x] Нет общего compatibility percentage.
- [x] House overlays отсутствуют при ненадёжном времени и появляются только для exact/exact пары с полными cusps.
- [x] Каждый interaction score multi-signal и evidence-backed; pair-only evidence не выводит score из neutral.
- [x] Saturn fixtures не создают blame/fatalism и не выводят score из neutral без fit evidence.
- [x] Correlated evidence capped; Saturn aggregate per dimension capped at `0.08`.
- [x] Fit independence основана на underlying raw lineage ownership, без double-count derived aggregates.
- [x] Normative reverse pairs и exact/exact angle contacts покрыты; unreliable/malformed child chart fail closed.
- [x] Pair A/B и A/C не смешивают evidence/cache/UUID lineage.
- [x] Fresh PostgreSQL reload отклоняет committed corruption после identity-map preload и stale exact overlays после смены timing proof на unknown.
- [x] Persisted fit leaves точно привязаны к ожидаемым Parent Style/Child Needs rows и recomputed catalog rule.
- [x] Create/reload блокируют exact owned `ChildProfile` до чтения `parent_profile_id`, не блокируют sibling row и после смены route отклоняют stale interaction.

## Verification

- RED review reproduction: `uv run pytest tests/unit/test_child/test_interaction_engine.py -q` → `7 failed, 13 passed` до production fixes (underlying lineage, reverse/angle catalog, malformed child longitude и strict persisted contract).
- Focused Interaction GREEN: `uv run pytest tests/unit/test_child/test_interaction_engine.py -q` → `31 passed`.
- `uv run pytest tests/unit/test_child/test_parent_style_engine.py tests/unit/test_child/test_child_needs_engine.py tests/unit/test_child/test_interaction_engine.py -q` → `121 passed`.
- `uv run pytest tests/unit/test_child -q` → `164 passed`.
- Chart regressions: `uv run pytest tests/chart -q` → `28 passed`.
- Career/fact regressions: `uv run pytest tests/unit/test_career tests/unit/test_astrotype_v2 -q` → `253 passed`, одна dependency deprecation warning WeasyPrint.
- PostgreSQL combined S05–S07: `uv run pytest tests/integration/test_child_parent_style.py tests/integration/test_child_needs.py tests/integration/test_child_interaction.py -q` → `8 passed`, включая fresh-state identity-map corruption rejection, exact→unknown timing invalidation, real Alembic `d5→e6→d5→e6`, S07 schema parity, concurrent replay, pair isolation, old/current coexistence и lossy downgrade refusal. Explicit locks: `uv run pytest tests/integration/test_child_interaction.py::test_reload_locks_exact_owned_child_route_before_reading_parent_profile tests/integration/test_child_interaction.py::test_reload_holds_shared_source_locks_until_validation_transaction_ends -q` → `2 passed`. Первый regression наблюдает raw `UPDATE child_profiles.parent_profile_id` exact child row, ожидающий loader через `pg_blocking_pids` под `lock_timeout`, одновременно подтверждает commit update другого child, затем после release подтверждает commit target update и rejection следующего reload. Второй сохраняет тот же proof для upstream Parent Style row.
- Repository-wide `ruff format --check . && ruff check .` → `420 files already formatted`, `All checks passed`; strict `mypy .` → `419 source files` без ошибок; exact-path Prettier проходит. `git diff --check` и single Alembic head входят в final commit gate.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
