# S05: Parent Style engine

## Статус

✅ Завершено

## Контекст

Нужно детерминированно описать естественный стиль взрослого, используя persisted v2 facts, не превращая пол или одно положение карты в parenting label.

## Что сделать

1. Зафиксированы ровно восемь MVP Parent Style dimensions, двусторонняя семантика шкал и versioned scoring/reference config.
2. Pure deterministic engine собирает support/counter/missing evidence только из persisted Astrotype v2 natal facts и связанных evidence rows.
3. Для результата требуются одновременно минимум две независимые signal families и две разные canonical persisted source lineages. Lineage выводится из `(source_table, source_id)`, либо консервативно из `(source_table, source_key)` при отсутствии `source_id`; строки без обоих идентификаторов не считаются evidence. Дубликаты одной source lineage дедуплицируются внутри и между facts, а breakdown сохраняет canonical lineage refs/count. Иначе score остаётся нейтральным `50`, а confidence — `0`.
4. Placement rules учитывают конкретный знак, aspect rules — тип аспекта, а balance rules — persisted долю; универсальные planet-presence сигналы не используются. Fact weight/confidence и evidence source quality принимаются только как finite `0..1`, без clamp; знак направления задаёт rule weight. Time-sensitive houses/angles fail-closed исключаются без непротиворечивого persisted proof точного пользовательского времени, включая malformed recognized provenance blocks.
5. Builder создаёт все восемь строк в каноническом порядке со стабильными IDs, полным breakdown, evidence refs и source-lineage refs. Repository запрашивает только текущую scoring version, не скрывает unknown/duplicate dimensions до validation и отклоняет повреждённые breakdown/evidence JSON при reload.
6. Advisory lock и database uniqueness обеспечивают concurrent replay: один writer создаёт profile, остальные получают те же восемь persisted rows. Ошибки ownership/lineage происходят до writes и безопасны даже при последующем `commit()` вызывающей стороны.
7. Engine не зависит от пола, mutable Self narrative, report payload, LLM или network.

## Затрагиваемые файлы

| Область                                                           | Действие  |
| ----------------------------------------------------------------- | --------- |
| `backend/app/modules/child/parent_style.py`                       | Добавлен  |
| `backend/app/modules/child/scoring/*`                             | Добавлены |
| `backend/app/modules/child/repository.py`                         | Изменён   |
| `backend/app/reference_data/child/*`                              | Добавлены |
| `backend/app/modules/astrotype_v2/chart_adapter.py`               | Изменён   |
| `backend/workers/tasks/astrotype_v2.py`                           | Изменён   |
| `backend/tests/unit/test_child/test_parent_style_engine.py`       | Добавлен  |
| `backend/tests/unit/test_child/fixtures/parent_style_golden.json` | Добавлен  |
| `backend/tests/unit/test_astrotype_v2/test_chart_adapter.py`      | Изменён   |
| `backend/tests/unit/test_astrotype_v2/test_worker_runtime.py`     | Изменён   |
| `backend/tests/integration/test_child_parent_style.py`            | Добавлен  |

## Критерии приёмки

- [x] Все восемь dimensions воспроизводимы без LLM/network и имеют явную семантику `0/50/100`.
- [x] Каждый score имеет version, evidence refs, support/counter/missing evidence, confidence и breakdown.
- [x] Нет gender weights, mutable narrative inputs, universal planet-presence rules и single-family/single-source-lineage conclusions.
- [x] Correlated facts ограничены family cap и не раздувают score.
- [x] Golden fixture проверяет deterministic sign-sensitive output; adversarial tests покрывают shared Moon/Venus source, duplicate/null evidence, distinct source lineages, invalid/NaN/inf numbers и exact-time gate.
- [x] Astrotype v2 adapter сохраняет canonical `birth_time_proof`; worker выводит его только из persisted `birth_time_accuracy` и реального source time. Все присутствующие recognized provenance blocks должны быть dict и непротиворечиво подтверждать exact/non-synthetic/user-supplied timing. Engine/cache version `0.1.6` не переиспользует legacy `0.1.5` charts; история не backfill-ится.
- [x] Output сохраняется versioned в PostgreSQL всеми восемью строками атомарно, owner-scoped, idempotent и concurrency-safe; invalid numeric input не оставляет score rows, а corrupted current-version dimension/breakdown fail-closed отклоняются при reload.

## Verification

- Focused unit: `uv run pytest tests/unit/test_child/test_parent_style_engine.py -q` → `32 passed`.
- Child unit regression: `uv run pytest tests/unit/test_child -q` → `74 passed`.
- Astrotype chart adapter/worker regression: `uv run pytest tests/unit/test_astrotype_v2/test_chart_adapter.py tests/unit/test_astrotype_v2/test_chart_persistence.py tests/unit/test_astrotype_v2/test_worker_runtime.py -q` → `16 passed`.
- Career + Astrotype fact regression: `uv run pytest tests/unit/test_career tests/unit/test_astrotype_v2/test_*fact*.py -q` → `127 passed`, `1` dependency deprecation warning.
- Disposable PostgreSQL 16 integration: `TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55435/archemap_test uv run pytest tests/integration/test_child_parent_style.py -q` → `1 passed`; test additionally proves invalid numeric evidence has no score-row side effect and corrupted current-version dimension/breakdown is rejected without mutating historical artifacts.
- Quality: changed-path Ruff check passed; Ruff format check passed; mypy passed with the existing unused-config note only.
- Docs: exact-path Prettier and `git diff --check` passed.
- Frontend tests are not applicable: S05 adds no route or UI surface; reader/API work remains in S12–S14.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
