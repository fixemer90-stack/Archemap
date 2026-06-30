# E14 — Staged Narrative Pipeline

> Статус: ✅ Готово
> Дата подготовки: 2026-06-27
> Последняя синхронизация с кодом: 2026-06-29
> Источник: пользовательский фидбек по Self report: “результат всё ещё похож на поверхностный гороскоп”
> Зависимости: E3 ✅, E4 ✅, E11 ✅, E12 ✅, E13 ✅

## Цель

Перевести Self narrative generation с одного большого LLM-запроса на staged pipeline, где глубокое прочтение натальной карты сначала собирается детерминированно, затем LLM генерирует отдельные смысловые блоки поверх проверяемого `DeepNatalSynthesis`.

Главная цель E14 — убрать ощущение “расширенного гороскопа”: отчёт должен объяснять не только “что в карте есть”, но и как разные части карты взаимодействуют между собой, где возникает внутренний механизм, напряжение, компенсация, повторяющийся сценарий, зрелая форма и проверяемая гипотеза о жизни пользователя.

## Проблема

Текущий E11/E13 single-shot подход уже умеет рендерить структурированный narrative JSON, но слабые места остаются:

- один большой LLM-запрос вынужден одновременно держать весь контекст, стиль, JSON-схему, safety и глубину;
- аспекты попадают во вход, но не проходят полноценный deterministic ranking/synthesis;
- дома, планеты, знаки и аспекты часто читаются параллельно, а не как единая динамическая система;
- напряжения карты могут появляться как отдельные факты, но не всегда становятся центральными противоречиями;
- гармоничные аспекты редко связываются с ресурсами и зрелой компенсацией;
- слабые/смешанные карты могут звучать общо, если нет слоя “что здесь главное, что вторично, что конфликтует”;
- schema drift одного блока может валить весь narrative;
- качество секций нельзя улучшать независимо: приходится регенерировать весь отчёт.

## Product principles

1. Deterministic-first: LLM не рассчитывает карту и не выбирает факты из воздуха.
2. Deep synthesis before prose: перед генерацией текста должен появиться структурированный слой `DeepNatalSynthesis`.
3. Аспекты — не приложение, а динамика карты: они должны объяснять связь функций, напряжения, компенсации и способы интеграции.
4. Staged, not fragmented: секции можно генерировать параллельно только после общего narrative plan, иначе отчёт станет набором несвязанных текстов.
5. Evidence-backed UX: каждый важный вывод должен иметь evidence refs, но доказательства остаются вторичным раскрытием, а не главным экраном.
6. Self не должен превращаться в Career/Love/therapy: работа и отношения раскрываются только в рамках Self-портрета.
7. Качество важнее объёма: отчёт должен быть плотным, а не просто длинным.

## Scope

### In scope

- Новый deterministic synthesis layer для глубокой карты:
  - aspect ranking;
  - aspect pattern clustering;
  - chart tension synthesis;
  - house axis synthesis;
  - planet role synthesis;
  - contradictions/failure modes/maturity levels;
  - calibration hypotheses.
- Staged LLM orchestration:
  - `NarrativePlan`;
  - parallel section generation;
  - final consistency/assembly pass;
  - per-stage validation, retry, caching and observability.
- Новый prompt family:
  - `self_plan_v1`;
  - `self_section_identity_v1`;
  - `self_section_emotional_v1`;
  - `self_section_relationships_v1`;
  - `self_section_development_v1`;
  - `self_assemble_v1`.
- Storage/versioning для staged artifacts.
- API/status contract for staged generation.
- Web/PDF parity for staged output.
- Regression checks against horoscope-like generic prose.

### Out of scope

- LLM as astrological calculator.
- Free-form Markdown report output.
- Medical/diagnostic/fatalistic psychological claims.
- Full Career/Love report inside Self.
- User feedback learning loop with persisted answers; E14 only prepares calibration questions/metadata.
- Manual one-off interpretation for a single chart.

## Текущий статус реализации

Реально реализовано и проверено:

- deterministic `DeepNatalSynthesis` contract и builder;
- aspect ranking + pattern clustering;
- chart dynamics / contradictions / maturity / calibration synthesis;
- staged schemas и file-backed prompt family;
- stage artifact / cache / retry / progress helpers;
- deterministic assembler и anti-generic quality gates;
- staged provider gating и межсессионная visibility progress snapshots для live polling path;
- live runtime `generate -> progress -> ready -> pdf` на реальном provider без fallback.

E14 закрыт как shipped staged Self pipeline:

- staged runtime активен вместо monolithic single-shot path для supported providers;
- API отдаёт `narrative`, `narrative_progress` и `narrative_stage_artifacts` уже во время `generating_narrative`;
- итоговый live smoke доходит до `report.status=ready`, `narrative.status=ready` и `POST /reports/{id}/pdf -> 200`.

Non-blocking deferred follow-up:

- текущий runtime генерирует section stages последовательно внутри общего staged flow; параллельное выполнение после `NarrativePlan` остаётся future optimization, а не blocker для закрытия E14.

## Stories

| Story | Название                                                       | Статус    | Документ                               |
| ----- | -------------------------------------------------------------- | --------- | -------------------------------------- |
| S01   | DeepNatalSynthesis contract                                    | ✅ Готово | `S01-deep-natal-synthesis-contract.md` |
| S02   | Aspect ranking and pattern clustering                          | ✅ Готово | `S02-aspect-ranking-patterns.md`       |
| S03   | Chart dynamics: contradictions, compensations, maturity        | ✅ Готово | `S03-chart-dynamics-synthesis.md`      |
| S04   | Staged LLM schemas and prompt family                           | ✅ Готово | `S04-staged-llm-contracts-prompts.md`  |
| S05   | Orchestration, cache, retry and statuses                       | ✅ Готово | `S05-orchestration-cache-statuses.md`  |
| S06   | Section assembly, consistency and anti-horoscope quality gates | ✅ Готово | `S06-assembly-quality-gates.md`        |
| S07   | API/frontend/PDF integration                                   | ✅ Готово | `S07-api-frontend-pdf-integration.md`  |

## Acceptance criteria

- [x] Self report generation no longer depends on one monolithic LLM call for the complete report.
- [x] `DeepNatalSynthesis` exists as a deterministic, testable contract before any LLM prose stage.
- [x] Top aspects are ranked by orb, planet importance, aspect type, personal relevance and section relevance.
- [x] Aspect patterns group related aspects into psychological mechanisms, not isolated aspect blurbs.
- [x] The report explains central contradictions and compensations using evidence-backed chart dynamics.
- [x] Section generation can run in parallel after a shared `NarrativePlan` stage.
- [x] Each staged artifact has stable `input_hash`, `prompt_version`, `model`, `status`, error and retry metadata.
- [x] Failed section generation does not corrupt ready sections and can be retried by stage.
- [x] Final assembled report has consistent tone, no duplicate paragraphs and no contradictory claims at the current shipped quality-gate baseline.
- [x] Validators reject unknown evidence refs, unsupported aspect claims, Career leakage and horoscope-generic fallback prose.
- [x] Web and PDF render the same staged narrative content at serializer/template regression level and fresh live smoke reaches PDF `200`.
- [x] Runtime logs expose true per-stage duration, model, failure_kind and recovery_action without logging prompt bodies or API keys.

## Data contract sketch

```ts
interface DeepNatalSynthesis {
  evidence_map: EvidenceMap;
  ranked_aspects: RankedAspect[];
  aspect_patterns: AspectPattern[];
  house_axis_patterns: HouseAxisPattern[];
  planet_roles: PlanetRole[];
  chart_dynamics: ChartDynamic[];
  contradictions: ContradictionInsight[];
  maturity_levels: MaturityLevelSet;
  calibration_hypotheses: CalibrationHypothesis[];
}
```

```ts
interface AspectPattern {
  id: string;
  title: string;
  aspect_ids: string[];
  planets: string[];
  type: "support" | "tension" | "mixed" | "integration";
  psychological_mechanism: string;
  life_manifestation: string;
  risk: string;
  mature_expression: string;
  section_targets: SelfSectionId[];
  evidence_ids: string[];
  weight: number;
}
```

## Verification plan

Backend:

```bash
cd backend
python -m ruff check app/modules/report_narratives app/modules/reports tests/unit/test_report_narratives tests/unit/test_reports
python -m ruff format --check app/modules/report_narratives app/modules/reports tests/unit/test_report_narratives tests/unit/test_reports
python -m mypy app/modules/report_narratives app/modules/reports
python -m pytest tests/unit/test_report_narratives tests/unit/test_reports -q
```

Frontend:

```bash
cd frontend
node scripts/check-report-ux.mjs
npm test
npx tsc --noEmit --pretty false
npx prettier --check .
npx eslint .
```

Runtime smoke:

```text
register -> verify -> login -> generate Self report -> staged statuses progress -> report ready -> narrative ready -> web report has staged sections -> PDF parity -> worker logs used_fallback=False
```

## Свежая verification evidence

Проверено на backend change sets E14 S01–S06:

- `pytest tests/unit/test_report_narratives tests/unit/test_reports -q` → `119 passed`
- `pytest tests/unit/test_report_narratives -q` → `88 passed`
- targeted staged assembly slice → `37 passed`
- targeted staged service slice → `20 passed`
- `ruff check ...` по затронутым backend narrative/reports модулям → `All checks passed!`
- `mypy ...` по затронутым backend narrative/reports модулям → `Success: no issues found`

Ключевые incremental commits:

- `92584af` — `feat(report): add deep natal synthesis contract`
- `193b605` — `feat(report): rank and cluster narrative aspects`
- `91b34fa` — `feat(report): synthesize chart dynamics`
- `617b5aa` — `feat(report): add staged prompt contracts`
- `e7528b8` — `feat(report): add staged narrative progress helpers`
- `4ce5175` — `feat(report): add staged assembly quality gates`
- `fd7dc6c` — `feat(report): add staged summary pdf parity`
- `252d7dc` — `feat(report): expose staged narrative progress in api`

Свежий runtime slice (2026-06-29):

- `pytest tests/unit/test_report_narratives/test_tasks.py tests/unit/test_report_narratives/test_api.py tests/unit/test_llm/test_provider_capabilities.py -q` → `28 passed`
- `mypy tests/unit/test_report_narratives/test_tasks.py tests/unit/test_report_narratives/test_api.py tests/unit/test_llm/test_provider_capabilities.py app/modules/report_narratives/service.py app/modules/llm/providers/deepseek.py app/modules/llm/providers/openrouter.py app/modules/llm/providers/mock.py` → `Success: no issues found in 7 source files`
- `ruff check app/modules/report_narratives/service.py app/modules/llm/providers/deepseek.py app/modules/llm/providers/openrouter.py app/modules/llm/providers/mock.py tests/unit/test_report_narratives/test_tasks.py tests/unit/test_report_narratives/test_api.py tests/unit/test_llm/test_provider_capabilities.py` → `All checks passed!`
- `pytest tests/unit/test_report_narratives/test_tasks.py -q && mypy app/modules/report_narratives/assembler.py tests/unit/test_report_narratives/test_tasks.py && ruff check app/modules/report_narratives/assembler.py tests/unit/test_report_narratives/test_tasks.py` → `22 passed`, `Success: no issues found in 2 source files`, `All checks passed!`
- live smoke after backend/worker restart confirms full staged path on real provider: `generate -> polling GET /reports/{id}` shows `narrative_status=generating`, затем `narrative_status=ready`, затем `report.status=ready`
- same fresh live smoke reaches `POST /reports/{id}/pdf -> 200 application/pdf` with `used_fallback=False` in worker logs.

## Risks

- Too many LLM calls can increase cost and queue time if not parallelized/cached correctly.
- Parallel sections can drift in tone without a shared `NarrativePlan`.
- Overweighting aspects can make the report feel deterministic-but-fragmented unless patterns are clustered.
- Excessive evidence display can make Self feel technical; evidence must remain secondary.
- Deep claims can become too psychological/diagnostic; validators must keep language bounded.

## Open decisions

- Whether staged artifacts live in a new `report_narrative_stages` table or inside `report_narratives.metadata` JSON. Baseline currently uses typed metadata contract; separate table is still open.
- Whether the final assembly uses no LLM or a small consistency LLM pass. Baseline currently ships deterministic assembler only.
- Whether E14 produces `SelfNarrativeV2` or extends current `SelfNarrative`. Current baseline extends current contract instead of introducing a vNext schema.
- Whether to support partial UI during generation. Preferred: no partial report content in main Self route until final ready; expose stage progress only.
