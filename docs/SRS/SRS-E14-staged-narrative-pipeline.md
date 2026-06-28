# SRS-E14 — Staged Narrative Pipeline

> Эпик: E14 Staged Narrative Pipeline
> Статус: ⬜ Не начато
> Дата: 2026-06-27

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

## 3. Функциональные требования

### FR-1. Deep natal synthesis

Система должна создавать `DeepNatalSynthesis` из deterministic report data без LLM.

### FR-2. Aspect ranking

Система должна ранжировать аспекты по orb, типу аспекта, важности планет, personal relevance and section relevance.

### FR-3. Aspect pattern clustering

Система должна группировать связанные аспекты в `AspectPattern`, включая mechanism, manifestation, risk and mature expression.

### FR-4. Chart dynamics

Система должна выделять central contradictions, compensations, house-axis patterns, maturity levels and calibration hypotheses.

### FR-5. Narrative planning

Система должна выполнять отдельный `NarrativePlan` stage перед section generation.

### FR-6. Parallel section generation

Система должна поддерживать параллельную генерацию независимых секций после готового plan stage.

### FR-7. Stage storage and cache

Система должна сохранять stage artifacts with prompt_version, model, input_hash, status, attempts and errors.

### FR-8. Stage retry

Система должна поддерживать retry failed/invalid stages без удаления ready stages.

### FR-9. Assembly and final validation

Система должна собирать final narrative only from valid stages and reject duplicate, contradictory, ungrounded or horoscope-generic prose.

### FR-10. API progress

`GET /reports/{id}` должен отдавать safe progress metadata while report is generating.

### FR-11. Web/PDF parity

Web and PDF must render the same assembled staged narrative content.

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
  id: string;
  report_id: string;
  stage_id: NarrativeStageId;
  prompt_version: string;
  model_provider: string;
  model_name: string;
  input_hash: string;
  status: "pending" | "running" | "ready" | "repairing" | "failed" | "skipped";
  content: object | null;
  error_message: string | null;
  generation_attempts: number;
  started_at: string | null;
  finished_at: string | null;
}
```

## 6. Архитектура

```text
ReportService
  → deterministic report_data
  → DeepNatalSynthesisBuilder
  → StagedNarrativeService
      → plan stage
      → parallel section stages
      → assembly stage
      → final validation
  → ReportNarrative ready
```

## 7. API

No new public endpoint is required for MVP. Existing report endpoints are extended with progress metadata. See `docs/features/E14-staged-narrative-pipeline/API.md`.

## 8. Prompt contracts

Prompts must be file-backed and versioned:

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

## 11. Зависимости

- E3 Profile & Chart Engine.
- E4 Rules & Content.
- E11 LLM Report Narrative.
- E12 Runtime Readiness.
- E13 Report Depth Improvements.

## 12. Риски

- More LLM calls can increase cost.
- Parallel generation can create tone drift.
- Stage storage adds schema/migration complexity.
- Anti-horoscope validators can be too strict if not calibrated with real examples.
- Existing report pages must remain backward compatible with old narrative rows.
