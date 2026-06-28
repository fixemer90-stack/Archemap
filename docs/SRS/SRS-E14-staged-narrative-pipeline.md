# SRS-E14 — Staged Narrative Pipeline

> Эпик: E14 Staged Narrative Pipeline
> Статус: 🟡 В процессе
> Дата: 2026-06-27
> Последняя синхронизация с кодом: 2026-06-28

## 1. Введение

### 1.1 Назначение

Документ определяет требования к staged pipeline для Self narrative generation. Цель — повысить глубину отчёта за счёт deterministic deep natal synthesis, staged LLM generation и stage-level validation/retry.

### 1.2 Область действия

SRS покрывает backend contracts, LLM stage schemas, storage, orchestration, API progress, frontend rendering, PDF parity, observability and quality gates.

### 1.3 Термины

- `DeepNatalSynthesis` — deterministic слой, который превращает карту в смысловые паттерны до LLM.
- `NarrativePlan` — общий LLM-план отчёта, который задаёт tone, hierarchy and central thesis.
- `Stage artifact` — сохранённый результат одного этапа generation.
- `AspectPattern` — кластер аспектов, объясняющий psychological mechanism, risk and mature expression.

## 2. Общее описание

### 2.1 Текущая проблема

Single-shot LLM generation создаёт приемлемый structured report, но отчёт может оставаться поверхностным: аспекты и нюансы карты есть во входе, но не всегда превращаются в глубокий механизм.

### 2.2 Целевое состояние

Система должна сначала строить deterministic synthesis карты, затем генерировать narrative по стадиям, валидировать каждую стадию и собирать финальный Self report без generic horoscope prose.

### 2.3 Реальный статус внедрения

Уже реализовано в backend:

- deterministic `DeepNatalSynthesis`;
- aspect ranking / pattern clustering;
- chart dynamics / contradictions / maturity / calibration synthesis;
- staged schemas и prompt family;
- baseline helpers для stage artifacts, cache/retry и progress snapshot;
- baseline deterministic assembler и assembled quality gates.

Ещё не реализовано end-to-end:

- staged generation flow в реальном runtime вместо single-shot narrative path;
- worker stage lifecycle и полноценные runtime logs;
- frontend/PDF integration и user-visible progress flow;
- live staged runtime smoke.

## 3. Функциональные требования

### FR-1. Deep natal synthesis

Система должна создавать `DeepNatalSynthesis` из deterministic report data без LLM.

Статус: реализовано.

### FR-2. Aspect ranking

Система должна ранжировать аспекты по orb, типу аспекта, важности планет, personal relevance and section relevance.

Статус: реализовано.

### FR-3. Aspect pattern clustering

Система должна группировать связанные аспекты в `AspectPattern`, включая mechanism, manifestation, risk and mature expression.

Статус: реализовано.

### FR-4. Chart dynamics

Система должна выделять central contradictions, compensations, house-axis patterns, maturity levels and calibration hypotheses.

Статус: реализовано.

### FR-5. Narrative planning

Система должна выполнять отдельный `NarrativePlan` stage перед section generation.

Статус: contract/prompt level реализовано, runtime wiring pending.

### FR-6. Parallel section generation

Система должна поддерживать параллельную генерацию независимых секций после готового plan stage.

Статус: gating/helpers реализованы, runtime wiring pending.

### FR-7. Stage storage and cache

Система должна сохранять stage artifacts with prompt_version, model, input_hash, status, attempts and errors.

Статус: baseline metadata contract реализован; отдельная persisted table всё ещё open decision.

### FR-8. Stage retry

Система должна поддерживать retry failed/invalid stages без удаления ready stages.

Статус: helper-level реализовано, runtime wiring pending.

### FR-9. Assembly and final validation

Система должна собирать final narrative only from valid stages and reject duplicate, contradictory, ungrounded or horoscope-generic prose.

Статус: baseline assembler + generic/fatalist/repetition checks реализованы; full contradiction/tone consistency enforcement pending.

### FR-10. API progress

`GET /reports/{id}` должен отдавать safe progress metadata while report is generating.

Статус: schema-level baseline реализован, router/frontend integration pending.

### FR-11. Web/PDF parity

Web and PDF must render the same assembled staged narrative content.

Статус: pending.

## 4. Нефункциональные требования

- Reliability: failure in one section must not corrupt other ready stages.
- Performance: section stages should run in parallel after planning.
- Observability: logs must include stage_id, duration_ms, failure_kind and recovery_action.
- Safety: no diagnosis, fatalism, medical claims or explicit sexuality.
- Privacy: no prompt bodies, API keys or raw provider payloads in logs.
- Testability: deterministic synthesis and validators must be unit-testable without network.

## 5. Модель данных

### 5.1 DeepNatalSynthesis

```ts
interface DeepNatalSynthesis {
  contract_version: string;
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

### 5.2 StageArtifact

```ts
interface NarrativeStageArtifact {
  stage_id: NarrativeStageId;
  status: "pending" | "running" | "ready" | "failed";
  prompt_version: string;
  model_name: string;
  input_hash: string;
  attempt_count: number;
  error_message: string | null;
  artifact: object | null;
}
```

## 6. Архитектура

```text
ReportService
  → deterministic report_data
  → DeepNatalSynthesisBuilder
  → staged plan/section/assembly contracts
  → stage artifact/cache/progress helpers
  → deterministic assembled quality gates
  → (pending) runtime staged orchestration in worker/service flow
  → ReportNarrative ready
```

## 7. API

No new public endpoint is required for MVP. Existing report endpoints are extended with progress metadata. See `docs/features/E14-staged-narrative-pipeline/API.md`.

Current reality:

- progress/artifact schemas are present in backend contracts;
- full runtime exposure through router/frontend remains pending.

## 8. Prompt contracts

Prompts are file-backed and versioned:

- `self_plan_v1.md`
- `self_section_identity_v1.md`
- `self_section_emotional_v1.md`
- `self_section_relationships_v1.md`
- `self_section_development_v1.md`
- `self_section_house_scenarios_v1.md`
- `self_assemble_v1.md`

## 9. Frontend integration

Frontend should show progress labels but not raw stage JSON. Final report remains narrative-first:

1. Hero / recognition.
2. Main formula.
3. Dominants and aspect patterns.
4. Inner mechanism.
5. Life/house scenarios.
6. Relationships/closeness/sexuality.
7. Development/maturity.
8. Calibration questions.
9. Career CTA.
10. Technical details collapsed.

Current status: target only, not yet implemented end-to-end for staged pipeline.

## 10. Verification criteria

Backend:

```bash
python -m ruff check app/modules/report_narratives app/modules/reports tests/unit/test_report_narratives tests/unit/test_reports
python -m ruff format --check app/modules/report_narratives app/modules/reports tests/unit/test_report_narratives tests/unit/test_reports
python -m mypy app/modules/report_narratives app/modules/reports
python -m pytest tests/unit/test_report_narratives tests/unit/test_reports -q
```

Frontend:

```bash
node scripts/check-report-ux.mjs
npm test
npx tsc --noEmit --pretty false
npx prettier --check .
npx eslint .
```

Runtime:

- generate fresh Self report;
- verify staged progress;
- verify final `report.status=ready` and `narrative.status=ready`;
- verify worker logs stage success and `used_fallback=False`;
- verify web/PDF parity.

## 11. Свежая verification evidence

- `pytest tests/unit/test_report_narratives tests/unit/test_reports -q` → `119 passed`
- `pytest tests/unit/test_report_narratives -q` → `88 passed`
- staged service slice → `20 passed`
- staged assembly slice → `37 passed`
- `ruff check ...` по затронутым narrative/reports backend файлам → `All checks passed!`
- `mypy ...` по затронутым narrative/reports backend файлам → `Success: no issues found`

## 12. Зависимости

- E3 Profile & Chart Engine.
- E4 Rules & Content.
- E11 LLM Report Narrative.
- E12 Runtime Readiness.
- E13 Report Depth Improvements.

## 13. Риски

- More LLM calls can increase cost.
- Parallel generation can create tone drift.
- Stage storage adds schema/migration complexity.
- Anti-horoscope validators can be too strict if not calibrated with real examples.
- Existing report pages must remain backward compatible with old narrative rows.
