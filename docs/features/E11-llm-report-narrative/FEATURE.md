# Feature E11: LLM Report Narrative — управляемый сторителлинг отчётов

## Цель

Добавить поверх детерминированного Astrotype report engine контролируемый LLM narrative layer: система продолжает считать карту, соционику, архетипы, evidence и confidence детерминированно, а LLM превращает уже рассчитанные факты в мягкий структурированный narrative JSON для UI и PDF.

Фича опирается на technical design: [`docs/design/llm-report-narrative-architecture.md`](../../design/llm-report-narrative-architecture.md).

## Проблема

Текущий deterministic report может быть проверяемым, но сложный живой сторителлинг трудно качественно собрать только шаблонами. Нужны связность, переходы, индивидуальные формулировки, взрослый и неграфичный блок близости/сексуальности, а также строгие границы между Self и Career.

При этом LLM нельзя делать источником истины: она не должна рассчитывать карту, придумывать аспекты, дома, типы, диагнозы или новые факты. Поэтому разработка должна быть разбита на атомарные части: контракт входа, контракт выхода, хранение, provider abstraction, prompt contract, validation, async task, API, frontend, PDF и regression gates.

## Главный принцип

> LLM — не источник истины. LLM — редактор и рассказчик поверх проверяемого deterministic report data.

## Зависимости

- `E3 Chart Engine` ✅ — chart snapshot, features, socionics.
- `E4 Rules & Content` ✅/🟡 — rules, claims, evidence trail, product boundaries.
- `E5 Products & Reports` 🟡 — report model/API/PDF foundation.
- `E10 Report UX Redesign` ✅ — narrative-first UI direction and technical details disclosure.
- `docs/design/llm-report-narrative-architecture.md` — исходный architecture contract.

## Scope

### Входит

- `NarrativeInput` DTO: очищенный evidence-backed вход для LLM.
- `SelfNarrative` structured output schema: JSON, не Markdown.
- `report_narratives` storage с prompt/model/input hash/version/status.
- `LLMProvider` abstraction и `MockLLMProvider` для dev/test.
- Prompt version `self_story_v1` с product boundaries и антигаллюцинационными правилами.
- Deterministic validators: schema, required sections, evidence refs, forbidden language, Self-vs-Career boundary, sexuality safety.
- Celery generation task с timeout/retry/failure statuses.
- API: report status/narrative in `GET /reports/{id}`, narrative regeneration endpoint.
- Frontend: polling, timeout UI, retry, deterministic fallback, narrative-first rendering.
- PDF: rendering из того же narrative JSON.
- Unit/integration/regression tests без реального network LLM call.

### Не входит

- Замена chart/rules/socionics engine на LLM.
- Свободный Markdown от LLM без schema validation.
- LLM-вызовы из frontend.
- Несколько пользовательских стилей/длин отчёта в MVP.
- LLM-as-judge в MVP.
- Полная реализация Career/Love narrative prompts, кроме расширяемого контракта.
- Медицинские, предсказательные, фаталистичные или графичные сексуальные интерпретации.

## Архитектурный target state

```text
POST /api/v1/reports/generate
  -> deterministic report_data saved
  -> Report.status = generating_narrative
  -> Celery generate_report_narrative(report_id)
       -> build NarrativeInput
       -> compute input_hash
       -> load self_story_v1 prompt
       -> LLMProvider.generate_structured(..., schema=SelfNarrative)
       -> validate SelfNarrative
       -> save ReportNarrative
       -> Report.status = ready
  -> Frontend polls GET /api/v1/reports/{id}
  -> UI/PDF render the same narrative JSON
```

## Критерии приёмки фичи

- [ ] Детерминированный расчёт отчёта остаётся source of truth; LLM не получает raw birth data как единственную основу и не рассчитывает карту.
- [ ] `NarrativeInput` и `SelfNarrative` зафиксированы в backend schemas и покрыты unit tests.
- [ ] LLM output сохраняется отдельно от `reports.report_data` и версионируется через `prompt_version`, `model_name`, `input_hash`.
- [ ] `MockLLMProvider` позволяет запускать все tests без внешней сети и API key.
- [ ] Prompt `self_story_v1` запрещает новые факты, фатализм, диагнозы, карьерный deep dive в Self и графичную сексуальность.
- [ ] Validator отклоняет unknown `evidence_refs`, отсутствующие обязательные секции, forbidden terms и Self/Career boundary violations.
- [ ] Narrative generation идёт асинхронно через Celery; HTTP request не ждёт LLM.
- [ ] Статусы `generating_narrative`, `ready`, `narrative_failed` не дают бесконечного spinner на frontend.
- [ ] `POST /api/v1/reports/{report_id}/narrative/regenerate` регенерирует только narrative layer и не пересчитывает chart/rules.
- [ ] Frontend показывает narrative-first report, polling/timeout state, retry action и deterministic fallback.
- [ ] PDF строится из сохранённого narrative JSON, без второго LLM-вызова.
- [ ] Backend gates (`ruff`, `format`, `mypy`, `pytest`) и frontend gates (`npm test`, `tsc`, `prettier`, `eslint`) проходят.

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Narrative contracts: input/output schemas](S01-narrative-contracts.md) | ✅ Готово |
| S02 | [Storage: report_narratives model and migration](S02-report-narratives-storage.md) | ✅ Готово |
| S03 | [LLM provider abstraction and settings](S03-llm-provider-abstraction.md) | ✅ Готово |
| S04 | [Prompt contract self_story_v1](S04-prompt-contract-self-story-v1.md) | ✅ Готово |
| S05 | [NarrativeInput builder, hashing and cache lookup](S05-narrative-input-builder-cache.md) | ✅ Готово |
| S06 | [Narrative validation, repair and fallback policy](S06-narrative-validation-fallback.md) | ✅ Готово |
| S07 | [Celery generation task, statuses and retry](S07-celery-generation-statuses.md) | ✅ Готово |
| S08 | [Report API integration and regenerate endpoint](S08-report-api-narrative-endpoints.md) | ✅ Готово |
| S09 | [Frontend status polling, timeout, retry and fallback](S09-frontend-status-polling-fallback.md) | ✅ Готово |
| S10 | [Frontend narrative rendering components](S10-frontend-narrative-rendering.md) | ✅ Готово |
| S11 | [PDF rendering from narrative JSON](S11-pdf-from-narrative-json.md) | ✅ Готово |
| S12 | [Quality gates, tests and observability](S12-quality-gates-observability.md) | ✅ Готово |

## Минимальный порядок разработки

1. S01 → S02: сначала contracts и storage.
2. S03 → S04: provider abstraction и prompt contract.
3. S05 → S06: входные данные, hash/cache, validation/fallback.
4. S07 → S08: async generation и API surface.
5. S09 → S10: frontend state и rendering.
6. S11: PDF из уже сохранённого JSON.
7. S12: финальные gates, regression checks, observability.

## Проверка закрытия фичи

Backend:

```bash
cd backend
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m mypy .
python3 -m pytest tests/unit -q
```

Frontend:

```bash
cd frontend
npm test
npx tsc --noEmit --pretty false
npx prettier --check .
npx eslint .
```

Network LLM calls в тестах запрещены. Все automated tests должны работать через `MockLLMProvider` или fake provider fixture.
