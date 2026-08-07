# Astrotype v2 Derived Chart Calculations

## Цель

Этот каталог фиксирует текущие MVP-вычисления, которые Astrotype v2 строит из натальной карты без LLM. Изначальный список был top 10, но `Thematic indicator bundles` временно снят с актуального MVP/UI scope.

Эти расчёты нужны для трёх слоёв:

```text
1. deterministic synthesis для отчёта
2. lower deterministic calculation layer of the report
3. internal evidence/debug trail для проверки, почему report builder выбрал такие входы для LLM-секций
```

LLM не считает эти показатели и не рендерит нижнюю расчётную часть. Верх отчёта собирается через builder: он формирует JSON-входы для отдельных LLM-запросов по блокам личности. Most aspected planets и thematic indicator bundles пока не входят в текущий sample и не являются актуальными MVP UI-блоками.

---

## Current MVP calculations

| # | Calculation | Document | User-visible by default | Used by LLM synthesis |
|---:|---|---|---|---|
| 1 | Element balance | [01-element-balance.md](./01-element-balance.md) | Да | Да |
| 2 | Modality balance | [02-modality-balance.md](./02-modality-balance.md) | Да | Да |
| 3 | House emphasis | [03-house-emphasis.md](./03-house-emphasis.md) | Да | Да |
| 4 | Angular / succedent / cadent balance | [04-house-mode-balance.md](./04-house-mode-balance.md) | Да, в нижнем 2x2 | Да |
| 5 | Hemisphere balance | [05-hemisphere-balance.md](./05-hemisphere-balance.md) | Да, в нижнем 2x2 | Да |
| 6 | Quadrant balance | [06-quadrant-balance.md](./06-quadrant-balance.md) | Да, в нижнем 2x2 | Да |
| 7 | Chart ruler / ASC ruler | [07-chart-ruler.md](./07-chart-ruler.md) | Да, компактно | Да |
| 8 | Aspect profile | [08-aspect-profile.md](./08-aspect-profile.md) | Да, компактно в нижнем 2x2 | Да |
| 9 | Most aspected planets | [09-most-aspected-planets.md](./09-most-aspected-planets.md) | Неактуально сейчас | Отложено |
| 10 | Thematic indicator bundles | [10-thematic-indicator-bundles.md](./10-thematic-indicator-bundles.md) | Неактуально сейчас | Отложено |

---

## Canonical current sample layout

The current correct report sample is:

- `docs/design/astrotype-v2-infographic-db-report-sample.html`
- `docs/design/astrotype-v2-infographic-db-report-data.json`

UI order for derived/calculation outputs:

```text
1. Chart/key indicators: ASC, MC, ASC ruler
2. Planet positions table + element/modality balances
3. House emphasis + aspect network
4. Key aspects table
5. Bottom 2x2 compact derived accents:
   - house mode balance
   - hemisphere/orientation balance
   - quadrant balance
   - aspect profile
```

Do not reintroduce as MVP UI blocks:

- most aspected planets;
- thematic indicator bundles;
- separate “factual basis” / “calculation-to-section links” cards;
- archetypes, typology labels or dominant-planet personality rankings.

The lower layer is fully deterministic. The upper narrative sections are generated separately from builder-created JSON inputs for bounded LLM section requests.

---

## Shared principles

1. Расчёты строятся только из `NatalChartV2`, reference tables и deterministic rules.
2. LLM prose не является source of truth для вычислений.
3. Каждый показатель должен хранить:
   - method/version;
   - input facts/rows;
   - scores;
   - normalized UI values;
   - caveats.
4. Если расчёт является эвристикой, документация должна прямо говорить, что это эвристика продукта, а не универсальный астрологический канон.
5. Если расчёт влияет на LLM-секцию, он должен ссылаться на evidence ids.
6. Пользовательский UI должен оставаться компактным: не все derived calculations должны быть видимыми как отдельные карточки.

---

## Shared point weights

Element and modality balances use the same `weighted_chart_points_v1_personality_heuristic` point weights. See:

- [01-element-balance.md](./01-element-balance.md)
- [02-modality-balance.md](./02-modality-balance.md)
- `docs/architecture/astrotype-v2-balance-calculation.md`

Other calculations may use their own scoring rules when the measured concept differs. Example: aspect profile scores aspect exactness; house emphasis scores planets/angles in houses. Thematic indicators are deferred and must not be rendered in the current sample.

---

## Recommended storage

These calculations can be stored in a small set of normalized/cache tables:

```text
natal_chart_balances
natal_house_emphasis
natal_chart_rulers
natal_aspect_profiles
# natal_thematic_indicators  # deferred, not current MVP
```

Or as typed JSONB view-model rows if the canonical source facts are already normalized and reproducible.

The important rule: JSONB cache is allowed, but the underlying chart facts remain canonical in PostgreSQL tables.
