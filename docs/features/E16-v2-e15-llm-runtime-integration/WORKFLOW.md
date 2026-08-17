# V2-E15 WORKFLOW: переход от deterministic-ready к LLM narrative

## Цель документа

Этот документ описывает практический workflow перехода Astrotype v2 к LLM-части отчёта.

Главный принцип: LLM подключается только после того, как deterministic foundation уже построен, сохранён и может быть показан пользователю. LLM не пересчитывает карту, не решает структуру отчёта и не придумывает факты.

## Product workflow

```text
Пользователь создаёт/открывает профиль
→ backend проверяет birth data
→ deterministic pipeline строит chart/facts/synthesis/outline/calculation_layer
→ API отдаёт deterministic_ready report
→ frontend показывает расчётную основу и skeleton narrative
→ worker генерирует LLM narrative sections по одной секции
→ backend сохраняет segment payloads + progress
→ frontend polling обновляет narrative sections
→ report становится narrative_ready или narrative_partial/narrative_failed
```

## Что пользователь должен видеть

| Состояние              | Что видно пользователю                                    | Что не должно происходить                                                |
| ---------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------ |
| `deterministic_ready`  | Карта, факты, расчётный слой, инфографика/таблицы         | Нельзя показывать пустой экран из-за LLM                                 |
| `narrative_generating` | Уже готовая deterministic часть + прогресс секций         | Нельзя блокировать весь отчёт                                            |
| `narrative_partial`    | Готовые narrative sections + прогресс/статус остальных    | Нельзя скрывать готовые секции                                           |
| `narrative_failed`     | Deterministic часть + честный retry/error banner          | Нельзя подменять real LLM failure deterministic prose и называть это LLM |
| `narrative_ready`      | Полный отчёт: narrative + deterministic calculation layer | Нельзя терять evidence/provenance                                        |

## Boundary: что делает deterministic слой

Deterministic слой делает и сохраняет:

- natal chart;
- planet positions;
- houses;
- aspects;
- balances;
- house emphasis;
- evidence-backed facts;
- deterministic synthesis;
- section outline;
- calculation layer / infographic payload;
- prompt input artifacts for LLM.

Deterministic слой не должен зависеть от LLM provider availability.

## Boundary: что получает LLM

LLM получает только curated JSON, собранный backend builder-ом.

Разрешённые входы:

- section id and section contract;
- owned theme ids;
- allowed reference theme ids;
- forbidden theme ids / forbidden expansions;
- compact profile context;
- chart/key indicators summary;
- relevant placements/aspects/houses/balances;
- evidence ids and evidence snippets;
- already explained summary to avoid repetition;
- style contract.

Запрещённые входы:

- raw database dump;
- secrets/tokens/user credentials;
- socionics/Model A/MBTI fields;
- legacy v1 report payloads;
- billing/auth internals;
- frontend-specific rendering instructions;
- permission to invent chart facts.

## Section generation order

MVP section order:

1. `core-pattern` — Ядро личности
2. `perception` — Мышление и восприятие
3. `emotions` — Эмоциональная регуляция
4. `agency` — Воля и действие
5. `relationships` — Близость и отношения
6. `growth` — Вектор роста

Each section is generated independently at segment boundary.

## Segment lifecycle

```text
pending
→ input_built
→ provider_requesting
→ provider_responded
→ validating
→ ready
```

Failure states:

```text
provider_timeout
provider_error
invalid_json
schema_error
business_validation_error
persistence_error
```

Rules:

- Failed section can be retried without recalculating deterministic foundation.
- Retry preserves source deterministic input hash unless birth/profile input changed.
- `force=false` must not duplicate report/chart rows.
- `force=true` may regenerate narrative segments, but must not recalculate chart/facts unless input hash changed.

## LLM output schema expectation

Each section payload must include:

```json
{
  "section_id": "core-pattern",
  "title": "Ядро личности",
  "eyebrow": "01 · ядро личности",
  "subtitle": "главная формула",
  "body": "...",
  "aside_title": "Как это может ощущаться",
  "aside_bullets": ["..."],
  "evidence_ids": ["fact:..."],
  "covered_theme_ids": ["theme:..."],
  "confidence": "medium|high",
  "warnings": []
}
```

## Validation gates

Provider response must pass all gates before being persisted as ready:

1. Transport succeeded.
2. JSON parsed.
3. Schema validates.
4. Required fields are present and non-empty.
5. `section_id` matches requested section.
6. `evidence_ids` exist in deterministic artifacts.
7. `covered_theme_ids` exist in deterministic synthesis/outline.
8. No forbidden theme ids are explained as owned themes.
9. No socionics/Model A/MBTI leakage.
10. No English astro labels in user-facing prose when Russian labels exist.
11. No explicit career upsell / obsolete product CTA.
12. Text is not generic horoscope filler.
13. Text follows Astrotype v2 tone: Russian soft narrative first, technical basis last.

## First implementation slice

Start with one vertical slice, not the whole report:

```text
core-pattern only
→ build input
→ call provider
→ validate payload
→ persist one segment
→ expose progress
→ render one real LLM section on report page
```

Only after this is green, expand to the remaining five sections.

## Operator workflow for local real-provider smoke

1. Start backend and worker with the same LLM env.
2. Confirm runtime env from the process that executes generation:
   - `LLM_ENABLED=true`
   - `LLM_PROVIDER=deepseek`
   - `LLM_MODEL=deepseek-v4-flash`
   - `LLM_TIMEOUT_SECONDS=180`
   - `LLM_MAX_RETRIES=2`
   - `LLM_API_KEY=[REDACTED]`
3. Send tiny provider request from the same runtime.
4. Generate one report.
5. Poll until terminal state.
6. Inspect segment rows/provider metadata.
7. Open `/report/v2/{profile_id}` and verify deterministic + narrative states.

## Implementation guardrails

- Do not put LLM keys in frontend.
- Do not let frontend call provider directly.
- Do not call LLM for calculation layer.
- Do not block deterministic report display on LLM.
- Do not silently downgrade real-provider failures to deterministic prose.
- Do not mark narrative ready unless every ready segment passed validators.
