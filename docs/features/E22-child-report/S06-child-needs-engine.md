# S06: Child Needs engine

## Статус

✅ Завершено

## Контекст

Child Needs описывают условия, в которых взаимодействие ребёнка со взрослым может быть легче, а не фиксированные traits, способности, диагнозы или возрастные рекомендации. Engine детерминированно читает только разрешённые факты pinned immutable `ChildChartVersion`; gender, caregiver context, questionnaire, Parent Style, narrative/report payload, LLM и network не являются входами.

## Что сделано

1. Зафиксированы ровно десять canonical MVP dimensions:
   - `reassurance`;
   - `predictability`;
   - `autonomy`;
   - `verbal_explanation`;
   - `physical_sensory_calm`;
   - `exploration`;
   - `recognition`;
   - `personal_space`;
   - `transition_time`;
   - `variety`.
2. Для каждой шкалы сохранены явные значения `0`, `50` и `100`; `50` означает balanced/insufficiently evidenced midpoint, а не label ребёнка.
3. `child-needs-mvp-1` использует только deterministic facts/evidence, построенные из persisted `ChildChartVersion.calculation_payload`, и `child-needs-reference-1` rules catalog.
4. Общий scoring engine переведён на generic dimension/fact/evidence contracts и сохраняет поведение/golden Parent Style S05.
5. Ненейтральный score требует минимум две независимые signal families и две canonical persisted source lineages. Mixed ID/key, duplicate и unidentified evidence дедуплицируются; correlated family contribution ограничен cap. Derived balance facts ссылаются только на реальные `planet_positions:*` lineages, а не на synthetic `derived_balance:*` source.
6. Confidence отдельно вычисляется из coverage, agreement и source quality. Low evidence всегда даёт `score=50`, `confidence=0`.
7. Rules зависят от конкретных sign/aspect/balance/house values; универсальное наличие тела не является сигналом. Supports, counters, missing families, evidence refs, lineage refs, family totals и ordering детерминированы.
8. Birth-time policy исполняется fail-closed:
   - `allowed_fact_families`, `uncertainty_reason` и canonical exclusions должны точно совпадать с `resolve_birth_time_policy(confidence)`; payload/persisted exclusions обязаны быть одним уникальным ordered списком, включающим все policy exclusions и ровно все unstable fact keys;
   - `exact` допускает persisted houses только при согласованном exact/user-supplied/non-synthetic provenance и не допускает exclusions;
   - `approximate` использует только факты, одинаковые во всех пяти declared samples pinned окна; aware UTC samples обязаны точно соответствовать technical center и canonical offsets;
   - `unknown` всегда исключает Moon и аспекты с Moon независимо от входного `stable=True`; три aware UTC samples обязаны иметь production order, technical reference совпадать со средним sample, каждый полу-дневный segment занимать `10h..14h`, а полный span — `22h..26h`, сохраняя normal и spring/fall DST production shape и отклоняя seconds/minutes counterexamples;
   - missing/malformed/contradictory provenance создаёт нейтральный профиль без time-sensitive evidence.
9. Planet positions сначала нормализуются в canonical body/sign rows, aspects — в canonical ordered body pair/code rows, и только затем дедуплицируются: case/order variant identical duplicate не меняет все десять результатов, conflicting duplicate fail-closed. Approximate stability lookup канонически разрешает production title-cased `planet_sign:*`/`aspect:*` keys. Balance появляется только из уникальных реальных placements.
10. Repository под PostgreSQL advisory lock создаёт ровно десять immutable `ChildNeedScore` rows, проверяет owner/generation/chart lineage и возвращает current scoring version без пересчёта.
11. Nested JSON проходит strict semantic validation: canonical dimensions/order, versions/scales, finite values, unique refs, family/lineage counts, missing families, raw delta, confidence components, score и confidence пересчитываются из leaf evidence. Один semantic rule leaf не может быть раздроблен на несколько строк с тем же fact/evidence/lineage ownership, включая split между supports/counters; multi-lineage balance leaf остаётся допустимым, а ownership проверяется отдельно внутри каждой dimension.
12. Unique identity расширена до `(generation_id, dimension, scoring_version)`, поэтому old/current версии сосуществуют. Migration `d5e6f7a8b9c0` отказывает downgrade до DDL, если старый uniqueness contract схлопнул бы valid version history.

## Затронутые файлы

| Область                                                                | Действие                                                              |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `backend/app/modules/child/child_needs.py`                             | Добавлен deterministic adapter/scorer/row builder                     |
| `backend/app/modules/child/scoring/{types,engine,validation}.py`       | Generic scoring contracts и persisted semantic validation             |
| `backend/app/reference_data/child/child_needs_v1.py`                   | Versioned 10-dimension rules/scales/policy                            |
| `backend/app/modules/child/{models,repository}.py`                     | Version-aware persistence, reload и validation                        |
| `backend/alembic/versions/d5e6f7a8b9c0_version_child_need_profiles.py` | Additive uniqueness migration с fail-safe downgrade                   |
| `backend/tests/unit/test_child/test_child_needs_engine.py`             | Golden/adversarial/unit/property-style coverage                       |
| `backend/tests/integration/test_child_needs.py`                        | Real PostgreSQL persistence/concurrency/migration/corruption coverage |

## Критерии приёмки

- [x] Ровно десять dimensions имеют score/confidence/evidence/scoring/reference/chart lineage.
- [x] Unknown-time exclusions сохраняются downstream и всегда удаляют Moon/Moon aspects; approximate использует только matching sampled-stability proof без unstable/house evidence.
- [x] Низкая evidence coverage даёт neutral score и нулевой confidence.
- [x] Ненейтральный score требует двух signal families и двух canonical source lineages.
- [x] Нет diagnosis, ability ranking, binary labels или child-trait mapping.
- [x] Engine не читает gender, caregiver context, questionnaire, Parent Style, prose/report payload, LLM/network.
- [x] Case/order-variant и conflicting positions/aspects, shared/mixed lineage, split duplicate evidence leaves, fabricated balance, invalid numbers, malformed timestamps, unknown-time seconds-span counterexample, normal/spring/fall full-day sample shapes, shuffled inputs и opposite signs покрыты fixtures.
- [x] Current/old scoring versions сосуществуют; corrupt persisted JSON отклоняется fail-closed.
- [x] Concurrent replay idempotent; caught/rolled-back invalid work не оставляет partial score rows.

## Verification

- Initial RED: новый focused suite → `19 failed` на отсутствующих Child Needs contracts/module/validator. Spec-blocker RED: focused S06 suite → `17 failed` на permissive policy/stability/duplicate/lineage paths; S03 canonical exclusion order → `1 failed`.
- `uv run pytest tests/unit/test_child/test_child_needs_engine.py tests/unit/test_child/test_parent_style_engine.py -q` → `90 passed`.
- `uv run pytest tests/unit/test_child -q` → `133 passed`.
- S03/chart regression: `uv run pytest tests/unit/test_astrotype_v2/test_chart_adapter.py tests/unit/test_astrotype_v2/test_chart_persistence.py tests/unit/test_astrotype_v2/test_chart_contract.py tests/chart/test_chart_engine.py -q` → `31 passed`.
- Career + Astrotype fact regression: `uv run pytest tests/unit/test_career tests/unit/test_astrotype_v2/test_*fact*.py -q` → `127 passed`, `1` dependency deprecation warning.
- Disposable PostgreSQL 16: `TEST_DATABASE_URL=... uv run pytest tests/integration/test_child_needs.py -q` → `1 passed`, включая owner/generation/chart lineage rejection, separate-transaction concurrent create, immutable exact reload, persisted balance lineage inspection (`planet_positions:*` only), current-version filtering, old/current coexistence, clean downgrade/re-upgrade, lossy downgrade refusal с сохранением revision/rows/current constraint, split duplicate leaf rejection, invalid numeric caught-error commit без score rows и corrupt JSON rejection без дополнительных writes.
- Scoring/reference/policy versions не изменены: canonical baseline output, row identities и valid persisted profile semantics остаются прежними; исправление только делает input normalization order-independent и отклоняет ранее невалидную duplicate-leaf corruption.
- Changed-path Ruff check/format, strict mypy, exact-path Prettier и `git diff --check` проходят после последнего изменения.

## Зависимости

S03 birth-time policy и pinned child chart lineage; S05 shared deterministic scoring/persistence patterns. См. граф в [`FEATURE.md`](./FEATURE.md).
