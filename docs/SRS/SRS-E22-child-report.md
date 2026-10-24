# SRS-E22: Astrotype Child Report

Статус: целевой контракт готов; S01–S10 завершены, S11–S16 не начаты

Feature: `docs/features/E22-child-report/FEATURE.md`

Design source: `docs/design/astrotype_child_report_workflow (1).md`

Workflow: `docs/features/E22-child-report/WORKFLOW.md`

API: `docs/features/E22-child-report/API.md`

## 1. Назначение

Child Report должен помогать взрослому владельцу аккаунта выстраивать взаимодействие с конкретным ребёнком. Система объединяет существующую натальную карту взрослого, ограниченную по качеству времени карту ребёнка, pair synastry, текущий возраст, versioned ответы и семейный контекст. Результат описывает механизмы взаимодействия и действия взрослого, а не фиксированные качества или будущее ребёнка.

## 2. Принципы

1. Анализируется `parent/caregiver ↔ child`, а не ребёнок отдельно.
2. Один астрологический фактор не создаёт вывод.
3. Score, confidence и evidence являются разными сущностями.
4. Пол не используется в core scoring; caregiver role хранится отдельно.
5. Неизвестные данные не заменяются догадками.
6. Возраст вычисляется системой и привязан к `as_of_date`.
7. Ответы уточняют контекст, но не переписывают chart-derived signals.
8. Guidance Facts формируются до LLM и являются единственным content input narrative pipeline.
9. Core report immutable; возрастные обновления versioned отдельно.
10. Формулировки направлены на поддержку взрослого без labels, blame, diagnosis и fatalism.

## 3. Scope

### 3.1 MVP

- несколько child records на одного владельца;
- exact/approximate/unknown birth-time confidence;
- семь age stages: `0-1`, `1-3`, `3-6`, `6-9`, `9-12`, `12-15`, `15-18`;
- Parent Style, Child Needs и восемь MVP Interaction Dimensions;
- versioned age-filtered questionnaire;
- deterministic Guidance Facts;
- modular LLM narrative;
- async lifecycle с `deterministic_ready`;
- responsive reader и PDF;
- Plus access, ownership, privacy, export/delete и rollout controls.

### 3.2 Не входит

- co-parenting, sibling/family reports;
- transits и forecasting;
- medical/psychological diagnosis;
- compatibility percentage;
- child account/shared adult access;
- profession/ability/academic predictions;
- full adaptive questionnaire.

## 4. FR-E22.1 — Child identity и owner relation

Child record принадлежит одному account owner и содержит:

- `id`, `owner_user_id`;
- `display_name` или псевдоним;
- `relationship_type`;
- optional `child_gender`;
- birth data и confidence;
- caregiver context;
- lifecycle state: active/archived/deletion-pending/deleted;
- created/updated timestamps.

Требования:

- child record не создаёт user/login/profile account;
- `relationship_type` не выдаёт доступ другому взрослому;
- имя допускает псевдоним;
- gender не влияет на scoring;
- owner может иметь несколько child records без cross-child contamination.

## 5. FR-E22.2 — Birth-time confidence

Enum:

```text
exact | approximate | unknown
```

| Confidence    | Contract                                                        |
| ------------- | --------------------------------------------------------------- |
| `exact`       | Полный расчёт при валидном времени/месте                        |
| `approximate` | Только факты, устойчивые в versioned временном окне             |
| `unknown`     | Без houses, angles, house overlays и time-sensitive conclusions |

Каждый chart artifact содержит `allowed_fact_families`, `excluded_fact_families`, uncertainty reason и engine version. Нельзя сохранять synthetic noon chart как будто это точное время.

Birth-time uncertainty входит в MVP: design допускает `unknown` уже во входе первой версии, поэтому её нельзя откладывать без нарушения safety contract.

## 6. FR-E22.3 — Age Resolver

Age snapshot:

```json
{
  "as_of_date": "2026-10-14",
  "age_years": 5,
  "age_months": 5,
  "age_days": 2,
  "age_stage": "3-6",
  "age_rules_version": "child-age-mvp-1"
}
```

Требования:

- календарно корректный расчёт с leap-day и timezone boundary tests;
- future DOB отклоняется;
- возраст `>=18` отклоняется fail-closed;
- возраст не вводится вручную;
- effective instant принадлежит серверу; repository default использует timezone-aware UTC clock, а local `as_of_date` выводится из persisted timezone ребёнка;
- stage boundaries versioned;
- canonical input hash включает DOB, `as_of_date` и rules version;
- core report не мутирует;
- age update создаёт новый immutable snapshot;
- PDF и web фиксируют один `age_snapshot_id`.

Реализация S04: `child-age-mvp-1`, stages `[0,1)`, `[1,3)`, `[3,6)`, `[6,9)`, `[9,12)`, `[12,15)`, `[15,18)`; repository owner-scoped, concurrency-safe, использует server-owned UTC clock и выводит DOB/timezone только из persisted child profile. Birth correction и snapshot creation сериализуются одним child advisory-lock key. Migration `b3c4d5e6f7a8` additive расширяет snapshot identity полем `input_hash`, поэтому correction DOB в тот же local `as_of_date` не переиспользует старый artifact. Schema downgrade условно обратим: при данных, совместимых со старой уникальностью, он проходит; при нескольких valid immutable rows для одной `(child, date, rules)` группы fail-safe отказывает до DDL, не удаляя и не объединяя history.

## 7. FR-E22.4 — Parent Style Profile

MVP dimensions:

- emotional_responsiveness;
- structure;
- control_tendency;
- flexibility;
- communication_style;
- protection;
- autonomy_support;
- consistency.

Каждый score имеет диапазон `0..100`, confidence `0..1`, evidence, counter-evidence, scoring version и chart lineage. Engine переиспользует persisted v2 facts, но не mutable prose Self report.

Реализация S05: `parent-style-mvp-2` возвращает ровно восемь dimensions в каноническом порядке и хранит явную семантику концов шкалы и нейтральной точки. Persisted evidence сохраняет contribution без потери float precision, чтобы generated profile round-trip проходил строгую semantic validation; агрегаты остаются округлёнными по контракту. Reference catalog остаётся `parent-style-reference-1`, поскольку правила и шкалы не менялись. Score смещается от `50` только при evidence минимум из двух независимых signal families и двух canonical persisted source lineages. Непустой `source_key` каноничен даже при наличии `source_id`; ID используется только без key, поэтому mixed ID+key/key-only строки одного persisted source дедуплицируются. Duplicate/unidentified evidence не повышает independence или source quality; breakdown хранит canonical lineage refs/count. Fact weight/confidence/source quality обязаны быть finite `0..1`, а malformed recognized timing provenance исключает time-sensitive evidence. Chart engine `0.1.6` создаёт новую canonical-proof chart вместо reuse legacy `0.1.5`, без backfill истории. Reload запрашивает только текущую scoring version и fail-closed отклоняет unknown/duplicate dimensions, stale reference version, malformed evidence objects/directions/ranges/refs, confidence components, counts, raw delta, correlation totals и scale strings. Placement rules зависят от конкретного знака, aspect rules — от типа аспекта, balance rules — от persisted веса; универсальное наличие планеты не является сигналом. Correlation-family cap предотвращает раздувание повторяющимися сигналами, а confidence отдельно складывается из coverage, agreement и source quality. Houses/angles исключаются без canonical persisted proof точного пользовательского времени; все распознанные provenance blocks должны одновременно подтверждать `exact`, user-supplied и non-synthetic timing, поэтому историческое отсутствие или противоречивый synthetic-noon block fail-closed. Production Astrotype v2 chart adapter сохраняет canonical proof, а worker выводит его из persisted `birth_time_accuracy` и source time без догадок. Pure builder создаёт стабильные IDs и полный JSONB breakdown; owner-scoped repository проверяет child/generation/parent-chart lineage, атомарно сохраняет все восемь строк и возвращает тот же persisted profile при последовательном или concurrent replay без пересчёта mutable inputs. Uniqueness `(generation_id, dimension, scoring_version)` позволяет old/current profiles сосуществовать; additive migration downgrade возвращает старый key только при совместимых данных и иначе отказывает до DDL/data changes, сохраняя revision, rows и новый constraint.

## 8. FR-E22.5 — Child Needs Profile

MVP dimensions:

- reassurance;
- predictability;
- autonomy;
- verbal_explanation;
- physical_sensory_calm;
- exploration;
- recognition;
- personal_space;
- transition_time;
- variety.

Эти значения описывают условия, в которых взаимодействие может быть легче. API и narrative не называют их personality traits, diagnoses или fixed capacities.

Реализация S06: `child-needs-mvp-1` возвращает ровно десять dimensions в каноническом порядке и хранит explicit `0/50/100` semantics из `child-needs-reference-1`. Единственный вход — persisted immutable `ChildChartVersion` с policy `child-birth-time-policy-v3`: gender, caregiver context, questionnaire, Parent Style, prose/report payload, LLM и network не читаются. `allowed_fact_families`, uncertainty reason и ordered exclusions должны точно совпадать с `resolve_birth_time_policy(confidence)`; дополнительные exclusions равны ровно unstable keys из stability proof, а exact exclusions запрещены. Approximate proof принимает только aware UTC samples, точно соответствующие technical center, canonical offsets и окну; planet-sign observations обязаны совпадать с persisted sign во всех samples, aspect observations — быть `true`, sample count — точным, stable confidence — `1.0`. Это доказательство устойчивости на declared samples, а не утверждение о непрерывном окне. Unknown использует ordered production samples, всегда исключает Moon и аспекты с Moon независимо от входного `stable=true`; UTC segments вокруг technical noon обязаны занимать `10h..14h` каждый, а полный local-day span — `22h..26h`, чтобы принимать normal и DST production shape, но не seconds/minutes counterexamples. Planet positions нормализуются в canonical body/sign rows, aspects — в canonical ordered pair/code rows, затем дедуплицируются; case/order-variant identical duplicate не меняет score независимо от позиции во входе, production title-cased stability keys разрешаются канонически, conflicting duplicate fail-closed, а balance нельзя создать повторением одной placement. Derived balances ссылаются на реальные `planet_positions:*` lineages всех underlying placements и не создают synthetic independence. Missing/malformed/contradictory provenance fail-closed создаёт neutral profile. Ненейтральный score требует минимум две independent signal families и две canonical source lineages; mixed ID/key, shared, duplicate и unidentified evidence дедуплицируются, correlation family capped, numeric values обязаны быть finite. Sign/aspect/balance/house-sensitive rules не используют простое наличие тела. Confidence независимо складывается из coverage, agreement и source quality; insufficient evidence даёт `score=50`, `confidence=0`. PostgreSQL repository под advisory lock создаёт ровно десять immutable rows, проверяет owner/generation/child-chart lineage, загружает только current scoring version без recalculation и строго пересчитывает nested JSON semantics из leaf evidence и запрещает split одного semantic rule leaf на несколько supports/counters с тем же fact/evidence/lineage ownership внутри dimension, сохраняя допустимый multi-lineage balance leaf и независимую validation разных dimensions. Unique key `(generation_id, dimension, scoring_version)` допускает old/current coexistence; migration `d5e6f7a8b9c0` fail-safe отказывает downgrade до DDL, если старый key схлопнул бы valid version history.

## 9. FR-E22.6 — Synastry и Interaction Profile

MVP dimensions:

- emotional_attunement;
- boundary_fit;
- autonomy_balance;
- communication_fit;
- tempo_fit;
- conflict_pattern;
- soothing_compatibility;
- learning_interaction.

Контракт:

```json
{
  "dimension": "autonomy_balance",
  "score": 64,
  "confidence": 0.78,
  "pattern": "moderate_tension",
  "scoring_version": "child-interaction-mvp-1",
  "evidence": []
}
```

Запрещены общий compatibility percentage, binary labels, single-factor conclusion, correlated evidence double-counting и gender weights.

Реализация S07: `child-interaction-mvp-1` возвращает восемь canonical dimensions и patterns `natural_match/moderate_tension/high_attention` без общего compatibility verdict. `child-synastry-reference-1` использует versioned pair/orb catalog, включая normative reverse directions и exact/exact angle ↔ personal-planet contacts; cross-chart longitude и angle evidence для non-exact child chart отсутствуют fail-closed. House overlays создаются только при exact timing proof обоих charts и 12 distinct persisted cusps, образующих один строго возрастающий cyclic zodiac обход; duplicates, non-monotonic/zero-width arcs и malformed values исключают overlay-часть, valid wraparound разрешён. Fit leaves ссылаются на exact current Parent Style/Child Needs rows той же generation и recomputed canonical underlying lineages, а не доверяют persisted numbers или IDs derived score rows; overlapping raw ownership canonicalizes correlated fit families и не создаёт ложную независимость. Ненейтральный score требует двух independent families, двух canonical persisted lineages и минимум одного fit signal. Все Saturn contacts принадлежат одной family; positive/negative sides capped пропорционально до `0.08`, сохраняя explanatory contradiction при exact cancellation. Create/reload после advisory lock использует authoritative fresh reads, заново строит expected synastry из pinned raw charts/timing и exact fit artifacts из upstream score rows, затем сравнивает persisted rows целиком. Поэтому committed corruption, stale identity-map state и exact evidence после смены timing proof на unknown fail closed. Shared UUID helpers являются единым источником formulas generator/validator. Migration `e6f7a8b9c0d1` сохраняет version-aware history, direct/composite child-chart FKs, real `d5→e6` schema parity и lossy-downgrade preflight.

## 10. FR-E22.7 — Questionnaire и Context Resolver

MVP использует 8–12 versioned вопросов, фильтруемых backend по age stage. Отдельно хранятся:

- caregiver role/context;
- observed behavior;
- parent preference/style;
- family constraints;
- question/answer version;
- completion timestamp.

Resolver формирует:

- `natural_strengths`;
- `potential_friction`;
- `compensation_areas`;
- `age_relevant_guidance`;
- `confirmations`;
- `contradictions`;
- `unresolved_ambiguities`.

Ответы не изменяют исходные chart scores. Они уточняют применение и приоритет guidance.

Реализация S08: `child-questionnaire-mvp-1` содержит десять backend-owned bounded single-choice вопросов и выбирает 8–10 вопросов для каждого canonical age stage с обязательным присутствием caregiver context, observations, parent preferences и family constraints. Session pins owner, child, exact age snapshot, selected keys и questionnaire/answer/context/consent versions; partial unique current-draft identity допускает immutable completed history и новый draft для следующего snapshot/version. Draft answers редактируемы только до completion. Completion проверяет required questions, сервером пересчитывает order-independent canonical hash и сериализуется advisory/row locks; completed session и answers защищены ORM и PostgreSQL raw-SQL guards. `child-context-resolver-mvp-1` принимает только completed questionnaire, pinned age snapshot и exact восемь `child-interaction-mvp-1` scores, сохраняет все семь output families как deterministic adult-action codes с confidence и versioned score/answer/age lineage. Confirmation, contradiction и ambiguity не меняют score; raw answer values не входят в resolver payload. Current resolver reload заново строит expected payload из fresh locked sources и fail-closed отклоняет corruption, а legacy resolver versions могут сосуществовать без reinterpretation. Migration `f7a8b9c0d1e2` проверена real PostgreSQL циклом `e6→f7→e6→f7`.

## 11. FR-E22.8 — Guidance Facts

`ChildGuidanceFacts` является единственным content input LLM:

```json
{
  "contract_version": "child-guidance-facts-v1",
  "parent_profile_id": "uuid",
  "child_id": "uuid",
  "core_report_version": 1,
  "age_snapshot_id": "uuid",
  "strong_matches": [],
  "friction_points": [],
  "parent_strengths": [],
  "compensation_areas": [],
  "recommended_actions": [],
  "avoid_patterns": [],
  "confidence_markers": [],
  "evidence_registry": {}
}
```

Raw chart, unrestricted answers, unnecessary names и provider secrets не входят в prompt payload.

## 12. FR-E22.9 — Child-safety policy

До и после LLM обязательны validators:

- no diagnosis/attachment labels;
- no prediction of violence, depression, failure or adult outcome;
- no intellectual or academic ranking;
- no fixed personality labels;
- no blame toward child or caregiver;
- no medical/legal intervention based on astrology;
- no unsafe discipline advice;
- no age-inappropriate recommendation;
- no unsupported recommendation;
- conditional language for low confidence;
- adult-action framing;
- no direct planet-to-child-trait sentence.

Safety failure не публикует section. Retry использует исправленный bounded input/prompt; deterministic facts сохраняются.

## 13. FR-E22.10 — Report composition

Core sections идут в порядке из FEATURE. Каждая section contract содержит owned/reference/forbidden facts, required safety markers, minimum evidence и confidence behavior.

`Guidance for Current Age` является отдельным artifact, связанным с core report и age snapshot. Presentation manifest задаёт единый порядок для web и PDF.

## 14. FR-E22.11 — Lifecycle

```text
questionnaire_draft
→ questionnaire_completed
→ queued
→ calculating_pair
→ deterministic_ready
→ generating_sections
→ ready | narrative_failed | failed
```

Age lifecycle:

```text
age_snapshot_current
→ age_snapshot_stale
→ age_update_queued
→ age_update_ready | age_update_failed
```

- retry narrative не пересчитывает deterministic foundation;
- age update не мутирует core report;
- provider failure сохраняет deterministic result; transient failure использует durable exponential backoff в `narrative_retry_waiting`, не скрывая опубликованный report;
- provider intent фиксируется до external call; outcome-unknown после crash не вызывается повторно;
- отключённый LLM сохраняет sections как unavailable/failed (`child_narrative_disabled`), без mock-ready prose и автоматического retry loop;
- status transitions durable и auditable.

## 15. FR-E22.12 — API, ownership и access

API surface определена в `docs/features/E22-child-report/API.md`.

Требования:

- active backend entitlement по E8;
- ownership на каждом child/questionnaire/generation/report/versions/PDF endpoint;
- foreign resource → indistinguishable `404`;
- locked response без protected content;
- idempotency для create/complete/regenerate/age update;
- child/report/session IDs cross-validated;
- no frontend-only access decisions.

## 16. Data model

Минимальные сущности:

- `child_profiles`;
- `child_chart_versions`;
- `child_age_snapshots`;
- `child_parent_style_scores`;
- `child_need_scores`;
- `child_synastry_evidence`;
- `child_interaction_scores`;
- `child_questionnaire_sessions`;
- `child_answers`;
- `child_context_resolutions`;
- `child_guidance_facts`;
- `child_segment_generations`;
- `child_reports`;
- `child_report_age_guidance`.

Root lineage, answers, scores/evidence, generation statuses, core versions и age snapshots должны быть independently queryable. Малые вложенные структуры могут использовать JSONB при сохранении schema/version validation.

## 17. Non-functional requirements

| ID         | Требование                                                                 |
| ---------- | -------------------------------------------------------------------------- |
| NFR-E22.1  | Deterministic engines воспроизводимы без LLM/network.                      |
| NFR-E22.2  | PostgreSQL — durable source of truth; Redis не хранит единственную копию.  |
| NFR-E22.3  | Data minimization для данных несовершеннолетнего.                          |
| NFR-E22.4  | Имя, DOB, answers и report prose не попадают в logs/metric labels.         |
| NFR-E22.5  | Миграции additive; parent/profile/report/payment data не удаляются.        |
| NFR-E22.6  | Generation idempotent, retry-safe и concurrency-safe.                      |
| NFR-E22.7  | Core history и age snapshots immutable/auditable.                          |
| NFR-E22.8  | Scoring/reference/questionnaire/prompt/model versions доступны для аудита. |
| NFR-E22.9  | Provider failure не блокирует deterministic report.                        |
| NFR-E22.10 | Reader mobile-first, accessible и пригоден для print/PDF.                  |
| NFR-E22.11 | Export/delete/retention policy исполняется и тестируется.                  |
| NFR-E22.12 | Latency/cost budgets измеряются на staging до rollout.                     |

## 18. Verification

1. Unit и property tests deterministic builders.
2. Golden fixtures exact/approximate/unknown birth time.
3. Age boundary, leap-day и future-DOB tests.
4. Correlated evidence и confidence tests.
5. Questionnaire/resolver contradiction fixtures.
6. Negative child-safety corpus до и после LLM.
7. PostgreSQL migration/repository/idempotency/concurrency tests.
8. Route-level ownership/access/leakage matrix.
9. Multiple-child isolation tests.
10. Mock и real-provider section/schema tests.
11. Frontend create/edit/questionnaire/polling/reader/accessibility tests.
12. Web/PDF presentation и pinned-age parity tests.
13. Backup/restore, export/delete и rollback rehearsal.
14. Staging E2E на exact и unknown time profiles.
15. Production canary только после safety/ownership gates.

## 19. Data safety и rollout

- backup/snapshot до migration на real-user storage;
- additive migrations; schema downgrade только когда он lossless, иначе fail-safe refusal без удаления/merge history;
- row counts/checksums parent profiles, natal charts, reports, payments и entitlements до/после;
- feature flag off по умолчанию;
- no mutable backfill старых placeholder `child` artifacts;
- no deletion cascade из child domain в parent account/billing;
- rollback прекращает новые generation, сохраняя artifacts;
- rollout запрещён без negative safety fixtures, foreign-owner tests и exact/unknown-time staging smoke.

## 20. Риски

- стигматизация ребёнка из-за слишком прямых формулировок;
- скрытое использование ненадёжного времени рождения;
- drift между core report и возрастным блоком;
- cross-child data mixing;
- утечка данных несовершеннолетнего через logs, locked payload или PDF URL;
- provider-generated diagnosis/labels;
- ложная точность scores/confidence;
- незаметная мутация исторического отчёта;
- неявное предоставление доступа второму взрослому через relationship field.
