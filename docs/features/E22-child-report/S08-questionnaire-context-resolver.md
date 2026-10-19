# S08: Questionnaire и Context Resolver

## Статус

✅ Завершено

## Контекст

Астрология не знает реальную семейную ситуацию. Versioned ответы уточняют применимость, приоритет и противоречия, но не переписывают chart-derived scores.

## Реализованный контракт

### Versioned backend catalog

- `QUESTIONNAIRE_VERSION = child-questionnaire-mvp-1`;
- `ANSWER_VERSION = child-answer-mvp-1`;
- `CONTEXT_VERSION = child-context-mvp-1`;
- `CONSENT_VERSION = child-consent-mvp-1`;
- `RESOLVER_VERSION = child-context-resolver-mvp-1`.

Backend владеет каталогом из десяти безопасных русскоязычных single-choice вопросов. Каждый вопрос имеет стабильный key, одну из четырёх категорий (`caregiver_context`, `observation`, `parent_preference`, `family_constraint`), bounded options, required marker и явный allowlist canonical age stages. Для каждого из семи stages backend выбирает 8–10 вопросов; младшие и старшие stages получают разные наборы, но каждый набор сохраняет все четыре context families. Catalog validator отклоняет duplicate/unknown keys, stages и options, unbounded labels, diagnosis, fixed-trait, fatalistic и gender-scoring framing.

Adaptive extension point типизирован как `disabled_deterministic`, `enabled = false`, `score_driven = false`. MVP не выбирает вопросы по scores. Compatibility map между версиями пуст: новая версия создаёт отдельный draft и не копирует ответы молча.

### Draft, resume, answer и complete

`ChildQuestionnaireRepository`:

- создаёт или возобновляет только exact draft для owner + child + age snapshot + questionnaire version;
- хранит backend-selected question keys и все pinned questionnaire/answer/context/consent versions;
- заменяет draft answers только после полной catalog/age/option validation;
- вычисляет canonical SHA-256 на сервере из session, child, age snapshot, versions и отсортированного answer set;
- проверяет required selected questions до completion;
- завершает session атомарно и idempotently; retry с тем же key и answer set возвращает существующий result, reuse key для другой session или другого answer set отклоняется до mutation;
- сериализует concurrent draft creation и completion PostgreSQL advisory/row locks;
- не смешивает детей, owners, snapshots или catalog versions.

Старый `ChildRepository.complete_questionnaire_idempotently(..., answers_hash=...)` удалён: completion доступен только через server-owned catalog validation и canonical hash. До transition заново проверяются exact selected keys, questionnaire/answer/context/consent versions и version каждой answer row. Schema заменяет старую уникальность `(child_profile_id, questionnaire_version)` partial unique index для одного current draft на exact child/snapshot/version. Completed history может сосуществовать с новым snapshot/version. Draft answers разрешено создавать, обновлять и удалять; после completion session и answer set защищены ORM guards и PostgreSQL triggers, включая запрет новых `INSERT` и переноса существующего answer из completed session в draft. Raw draft→completed переход требует transaction-local authorization, привязанную к UUID exact questionnaire session; repository устанавливает её только после полной проверки answers и hash и очищает сразу после authorized flush. Completion idempotency key сериализуется по owner + key, то есть в том же scope, что и database uniqueness. Answer guard читает parent status без дополнительного row lock: completion всегда lock'ит parent до answers и после ожидания заново валидирует locked answer set, поэтому mutation-before-completion учитывается, mutation-after-completion отклоняется, а обратный answer→parent lock order не создаёт deadlock. Privacy purge остаётся единственным разрешённым delete bypass внутри child aggregate.

### Context Resolver

`resolve_context()` принимает exact completed questionnaire, pinned age snapshot и ровно восемь `child-interaction-mvp-1` scores. Он не пересчитывает и не мутирует natal, Parent Style, Child Needs или Interaction rows.

Resolver детерминированно формирует все семь наборов:

- `natural_strengths`;
- `potential_friction`;
- `compensation_areas`;
- `age_relevant_guidance`;
- `confirmations`;
- `contradictions`;
- `unresolved_ambiguities`.

Каждый item содержит deterministic UUID, bounded topic/dimension, calibrated confidence, reason/action codes и versioned source refs. Raw option values и свободный текст не входят в resolver payload. Score-only strength/friction требуют declared thresholds `>=65` / `<=35` и confidence `>=0.4`. Questionnaire evidence может подтвердить, опровергнуть или сделать применение неоднозначным, но не меняет score. `depends`, missing и neutral evidence создают ambiguity. Contradiction сохраняет score и answer lineage и снижает confidence. Age guidance ссылается на exact snapshot/rules; family constraints меняют только priority/applicability.

`ChildContextResolutionRepository` locks owner child route, generation, completed questionnaire, age snapshot, answers и exact interaction rows, использует fresh reads, сохраняет input hash и full lineage, idempotently создаёт одну immutable current-version row и при reload семантически пересобирает expected payload. Перед create/reload заново проверяются pinned catalog/context/consent/answer versions, exact selected keys, полный required answer set, allowed options и canonical completion hash. Reload сверяет direct questionnaire/age/resolver/interaction-version metadata вместе с hash и семью payload families. Corrupt/stale current rows fail closed даже при ранее загруженной ORM identity; legacy resolver versions читаются без current reinterpretation, но проходят тот же owner/child/generation route gate.

### Migration

Migration `f7a8b9c0d1e2` после `e6f7a8b9c0d1`:

- добавляет owner, selected questions и answer version к questionnaire session;
- расширяет Context Resolution direct/composite questionnaire + age lineage, interaction version и input hash;
- добавляет partial draft uniqueness, indexes и FKs;
- заменяет global answer immutability на draft-aware trigger и добавляет session completion guard;
- отказывается от unsafe backfill existing context rows без явной lineage;
- выполняет downgrade preflight перед восстановлением старой lossy questionnaire uniqueness.

## Затронутые файлы

| Область            | Файл                                                                                |
| ------------------ | ----------------------------------------------------------------------------------- |
| Catalog/state/hash | `backend/app/modules/child/questionnaire.py`                                        |
| Reference data     | `backend/app/reference_data/child/questionnaire_v1.py`                              |
| Resolver           | `backend/app/modules/child/context_resolver.py`                                     |
| Persistence        | `backend/app/modules/child/questionnaire_persistence.py`                            |
| ORM                | `backend/app/modules/child/models.py`                                               |
| Migration          | `backend/alembic/versions/f7a8b9c0d1e2_add_child_questionnaire_context_resolver.py` |
| Unit tests         | `backend/tests/unit/test_child/test_context_resolver.py`                            |
| PostgreSQL tests   | `backend/tests/integration/test_child_questionnaire_context.py`                     |

## Критерии приёмки

- [x] Backend определяет age-filtered набор 8–12 вопросов для каждого canonical stage.
- [x] Completed answers immutable и versioned; draft answers редактируемы только до completion.
- [x] Contradictions сохраняются как first-class deterministic result с обеими evidence sides.
- [x] Answers не меняют natal/interaction scores.
- [x] Raw answers не входят в resolver contract или LLM input.
- [x] Draft одного ребёнка, owner, snapshot или version нельзя использовать для другого.
- [x] Completion hash server-owned, order-independent и idempotent.
- [x] Current resolver reload пересобирает expected result из fresh pinned sources и fail-closed отклоняет drift.
- [x] Migration upgrade → downgrade → re-upgrade выполнена на disposable PostgreSQL; Alembic имеет один head.

## Verification

Выполнены:

- `uv run pytest tests/unit/test_child/test_context_resolver.py -q` — 8 passed;
- `uv run pytest tests/unit/test_child -q` — 172 passed;
- `uv run pytest tests/integration/test_child_questionnaire_context.py -q` — 9 passed;
- `uv run pytest tests/integration/test_child_questionnaire_context.py tests/integration/test_child_storage_review.py -q` — 15 passed;
- все восемь Child PostgreSQL integration-файлов — 31 passed;
- migration-backed PostgreSQL trigger smoke для target-bound completion authorization, запрета raw completion, post-completion answer insert и переноса completed answer в draft — PASS;
- disposable PostgreSQL `upgrade e6 → f7`, `downgrade f7 → e6`, `upgrade e6 → f7` — PASS, current `f7a8b9c0d1e2 (head)`.
- `uv run mypy .` — 426 source files, no issues;
- scoped Ruff check/format — PASS.

Полные repo-native regression, Ruff, strict mypy, Prettier, one-head и diff checks записываются в commit evidence после финального запуска.

## Зависимости

S04 age snapshots и S07 exact eight-dimension Interaction profile являются pinned inputs. S09 получает только bounded resolver outputs, а не raw questionnaire answers.
