# S03: Factor и Career Dimension engine

## Статус

✅ Завершено

## Контекст

Ключевой анти-гороскопный слой Career — детерминированное накопление нескольких астрологических сигналов. Один фактор не может напрямую назначить dimension или профессию.

## Что сделать

1. Определить versioned catalog астрологических факторов для Career.
2. Связать факторы с существующими v2 planet/house/aspect/balance/pattern/fact rows.
3. Реализовать 12 MVP dimensions из design-документа.
4. Для каждого dimension вычислять raw contribution, normalized score `0..100`, confidence `0..1` и evidence breakdown.
5. Учитывать positive/negative/counter-signals и cap одного семейства коррелированных факторов.
6. Сделать engine чистым, детерминированным и независимым от LLM.
7. Версионировать weights, normalization и confidence formula.

## Принцип

```text
raw_dimension = Σ(normalized_factor × weight)
score = calibrated_normalize(raw_dimension, scoring_version)
confidence = independent_evidence_coverage × agreement × source_quality
```

Одна и та же планета в знаке/доме/аспекте не должна искусственно считаться тремя независимыми подтверждениями без correlation control.

## MVP dimensions

Leadership, Analytical Thinking, Systems Thinking, Communication, Creativity, Structure, Autonomy, Risk Tolerance, People Orientation, Innovation, Long-Term Focus, Execution.

## Критерии приёмки

- [x] Ни один dimension не определяется одним фактором или одной прямой rule.
- [x] Все 12 dimensions возвращают score, confidence и evidence.
- [x] Формулы/weights находятся в versioned config/catalog, а не в prompt.
- [x] Correlated evidence не завышает confidence.
- [x] Missing houses/ASC при неизвестном времени обрабатываются без выдуманного сигнала.
- [x] Golden fixtures имеют воспроизводимый результат.
- [x] Boundary/property tests покрывают ranges, normalization и порядок evidence.
- [x] В модуле нет вызовов LLM и соционических данных.

## Реализация и evidence

- `backend/app/modules/career/factor_catalog.py` — versioned weights, normalization/confidence versions, correlation cap и минимум независимых families.
- `backend/app/modules/career/dimension_engine.py` — pure deterministic `NatalFact` → 12 dimension results; score/confidence разделены.
- `backend/app/modules/career/dimension_persistence.py` — side-effect-free adapter в `career_dimension_scores` и `career_dimension_evidence` с preassigned IDs.
- `backend/tests/unit/test_career/test_dimension_engine.py` — golden snapshot, one-factor neutralization, source-quality confidence, correlation cap, missing-house, persistence и stable-order contracts.
- `uv run pytest tests/unit/test_career/test_dimension_engine.py -q` → `6 passed`.
