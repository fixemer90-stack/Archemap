# S05: Parent Style engine

## Статус

✅ Завершено

## Контекст

Нужно детерминированно описать естественный стиль взрослого, используя persisted v2 facts, не превращая пол или одно положение карты в parenting label.

## Что сделать

1. Зафиксированы ровно восемь MVP Parent Style dimensions, двусторонняя семантика шкал и versioned scoring/reference config.
2. Pure deterministic engine собирает support/counter/missing evidence только из persisted Astrotype v2 natal facts и связанных evidence rows.
3. Для результата требуется минимум две независимые signal families; иначе score остаётся нейтральным `50`, а confidence — `0`. Вклад одной correlation family ограничен, confidence отдельно объясняется coverage, agreement и source quality.
4. Time-sensitive houses/angles fail-closed исключаются без явного persisted proof точного пользовательского времени.
5. Builder создаёт все восемь строк в каноническом порядке со стабильными IDs, полным breakdown и evidence refs; repository атомарно сохраняет и без пересчёта перезагружает profile с owner/generation/parent-chart lineage validation.
6. Advisory lock и database uniqueness обеспечивают concurrent replay: один writer создаёт profile, остальные получают те же восемь persisted rows. Ошибки ownership/lineage происходят до writes и безопасны даже при последующем `commit()` вызывающей стороны.
7. Engine не зависит от пола, mutable Self narrative, report payload, LLM или network.

## Затрагиваемые файлы

| Область                                                           | Действие  |
| ----------------------------------------------------------------- | --------- |
| `backend/app/modules/child/parent_style.py`                       | Добавлен  |
| `backend/app/modules/child/scoring/*`                             | Добавлены |
| `backend/app/modules/child/repository.py`                         | Изменён   |
| `backend/app/reference_data/child/*`                              | Добавлены |
| `backend/tests/unit/test_child/test_parent_style_engine.py`       | Добавлен  |
| `backend/tests/unit/test_child/fixtures/parent_style_golden.json` | Добавлен  |
| `backend/tests/integration/test_child_parent_style.py`            | Добавлен  |

## Критерии приёмки

- [x] Все восемь dimensions воспроизводимы без LLM/network и имеют явную семантику `0/50/100`.
- [x] Каждый score имеет version, evidence refs, support/counter/missing evidence, confidence и breakdown.
- [x] Нет gender weights, mutable narrative inputs и single-family conclusions.
- [x] Correlated facts ограничены family cap и не раздувают score.
- [x] Golden fixture проверяет deterministic output; отдельные tests покрывают ranges, low-evidence neutral fail-closed, confidence components и exact-time gate.
- [x] Output сохраняется versioned в PostgreSQL всеми восемью строками атомарно, owner-scoped, idempotent и concurrency-safe.

## Verification

- Focused unit: `uv run pytest tests/unit/test_child/test_parent_style_engine.py -q` → `9 passed`.
- Child unit regression: `uv run pytest tests/unit/test_child -q` → `51 passed`.
- Career + Astrotype fact regression: `uv run pytest tests/unit/test_career tests/unit/test_astrotype_v2/test_*fact*.py -q` → `127 passed`, `1` dependency deprecation warning.
- Disposable PostgreSQL 16 integration: `TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55435/archemap_test uv run pytest tests/integration/test_child_parent_style.py -q` → `1 passed`; test proves owner/parent-chart rejection with caught-error commit and zero writes, two-transaction concurrent create/replay, exactly eight rows, stable IDs/order, exact payload reload and foreign-owner denial.
- Quality: changed-path Ruff check passed; Ruff format check passed; mypy passed with the existing unused-config note only.
- Docs: exact-path Prettier and `git diff --check` passed.
- Frontend tests are not applicable: S05 adds no route or UI surface; reader/API work remains in S12–S14.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
