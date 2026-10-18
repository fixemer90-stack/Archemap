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

- `child-synastry-reference-1` строит pair-bound cross-chart aspects только из канонических persisted longitudes и разрешённого каталога пар/orbs. Для `approximate/unknown` child chart cross-chart longitude evidence исключается fail-closed: sampled sign/aspect stability S03 не доказывает устойчивость pair aspect.
- House overlays рассчитываются только при exact timing proof обоих charts и полном наборе 12 persisted cusps; при ненадёжном времени они отсутствуют без fallback.
- Exact-time overlays versioned и bounded: используются как pair context с отдельными correlation families и не подменяют Parent Style/Child Needs fit.
- `child-interaction-mvp-1` возвращает ровно восемь dimensions в каноническом порядке. Ненейтральный score требует минимум две independent families, две persisted lineages и хотя бы один `fit:*` signal из Parent Style + Child Needs; pair-only и Saturn-only evidence остаются neutral.
- Correlated evidence capped; Saturn contribution дополнительно ограничен `0.08` и использует только безопасный label `structure_expectations_pressure_awareness`.
- `e6f7a8b9c0d1` добавляет pair chart lineage, version-aware uniqueness для scores/synastry evidence и fail-safe downgrade preflight до DDL.
- Repository использует PostgreSQL advisory lock, immutable replay, current-version reload и strict semantic validation score/confidence/pattern/evidence/pair lineage.

## Затрагиваемые файлы

| Область                                                    | Действие          |
| ---------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/synastry.py`                    | Изменить/добавить |
| `backend/app/modules/child/interaction.py`                 | Изменить/добавить |
| `backend/app/reference_data/child/*`                       | Изменить/добавить |
| `backend/tests/unit/test_child/test_interaction_engine.py` | Изменить/добавить |

## Критерии приёмки

- [x] Нет общего compatibility percentage.
- [x] House overlays отсутствуют при ненадёжном времени и появляются только для exact/exact пары с полными cusps.
- [x] Каждый interaction score multi-signal и evidence-backed; pair-only evidence не выводит score из neutral.
- [x] Saturn fixtures не создают blame/fatalism и не выводят score из neutral без fit evidence.
- [x] Correlated evidence capped.
- [x] Pair A/B и A/C не смешивают evidence/cache/UUID lineage.

## Verification

- RED: focused Interaction suite не собиралась до появления S07 modules/contracts.
- `uv run pytest tests/unit/test_child/test_parent_style_engine.py tests/unit/test_child/test_child_needs_engine.py tests/unit/test_child/test_interaction_engine.py -q` → `102 passed`.
- `uv run pytest tests/unit/test_child -q` → `145 passed`.
- Chart regressions → `31 passed`.
- Career/fact regressions → `127 passed`, одна dependency deprecation warning WeasyPrint.
- Disposable PostgreSQL 16: `TEST_DATABASE_URL=... uv run pytest tests/integration/test_child_interaction.py -q` → `1 passed`, включая concurrent replay, pair isolation, old/current coexistence, semantic corruption rejection и lossy downgrade refusal.
- Repository-wide Ruff format/check и strict mypy проходят после последнего изменения; exact-path Prettier и `git diff --check` входят в commit gate.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
