# E13 — Report Depth Improvements

> Статус: ⬜ Не начато
> Источник: `docs/Tips.md` / Obsidian note `Archemap/docs/Tips`
> Дата подготовки: 2026-06-18

## Цель

Поднять Self report с уровня “корректный расширенный гороскоп” до продукта Astrotype: не увеличивать объём ради объёма, а добавить промежуточный аналитический слой между астрологическими фактами и пользовательским narrative.

Ключевая формула улучшения:

```text
астрологический факт → психологический механизм → жизненный сценарий → риск → зрелая форма → проверочный вопрос
```

Сейчас отчёт технически корректнее, но местами слишком быстро переходит от данных карты к общим формулировкам. E13 должен сделать выводы более плотными, доказательными и узнаваемыми в жизни.

## Проблема

Текущие слабые места отчёта:

- техническое приложение и narrative существуют рядом, но не всегда связаны через понятную трассировку;
- сильные положения карты используются поверхностно: знак/дом часто превращаются в одну фразу, а не в жизненный сценарий;
- пользователь видит “Дева / Козерог / Лев”, но не видит иерархию доминант и внутренний механизм личности;
- напряжения карты перечислены, но не собираются в 3–5 центральных внутренних противоречий;
- уязвимости описаны мягко, но не показывают, где система реально даёт сбой;
- Career CTA в Self должен быть содержательным teaser-слоем, но не превращаться в полноценный Career report;
- отчёт не задаёт калибровочные вопросы, поэтому пользователь не может подтвердить/скорректировать модель.

## Product principles

1. Narrative-first, но evidence-backed. Сначала живой смысл, затем основания по запросу.
2. Не публично “технический” Self. Raw calculations остаются в technical details, но выводы должны быть трассируемыми.
3. Дома = сценарии жизни, не просто “место проявления”.
4. Архетип/типаж = гипотеза поведения, а не ярлык.
5. Self не должен съедать Career: можно дать предварительный карьерный вектор, но роли, деньги, рабочая среда и стратегия роста остаются для Career.
6. Калибровка обязательна: пользователь должен видеть вопросы, по которым модель можно подтвердить или уточнить.

## Scope

### In scope

- Новый слой “Ключевые доминанты карты”.
- Новый слой “Внутренний механизм личности”.
- Блок “Главные внутренние противоречия”.
- Сценарная интерпретация домов и сильных положений.
- Claim-to-evidence трассировка в narrative и PDF.
- Блок “Где система даёт сбой”.
- Бытовые проявления: “как это видно в жизни”.
- Предварительный Career teaser внутри Self.
- Калибровочные вопросы.
- Уровни зрелости проявления паттерна.
- Backend contracts, frontend rendering, PDF parity, regression checks.

### Out of scope

- Полная Career-вертикаль внутри Self.
- Медицинские, диагностические, фаталистичные выводы.
- Свободный LLM markdown без структурированного контракта.
- Ручные one-off тексты под конкретную карту без обобщаемого механизма.
- Новый платёжный флоу.

## Target report structure

Для Self report итоговая смысловая структура должна стать такой:

1. Hero / recognition.
2. Main personality formula.
3. Key dominants.
4. Inner mechanism.
5. Life scenarios by houses/placements.
6. Strengths.
7. Contradictions and system failures.
8. Relationships / closeness / sexuality.
9. Maturity levels and development vector.
10. Calibration questions.
11. Career teaser.
12. Save/share/PDF actions.
13. Calculation parameters.
14. Technical details / evidence appendix.

## Stories

| Story | Название | Статус | Документ |
|---|---|---|---|
| S01 | Dominants and inner mechanism contract | ⬜ Не начато | `S01-dominants-inner-mechanism.md` |
| S02 | House scenario interpreter | ⬜ Не начато | `S02-house-scenarios.md` |
| S03 | Evidence tracing in narrative and PDF | ⬜ Не начато | `S03-evidence-tracing.md` |
| S04 | Contradictions, failures, maturity levels | ⬜ Не начато | `S04-contradictions-failures-maturity.md` |
| S05 | Calibration questions and feedback loop | ⬜ Не начато | `S05-calibration-questions.md` |
| S06 | Self-to-Career teaser | ⬜ Не начато | `S06-career-teaser.md` |
| S07 | Rendering, prompt contract, and quality gates | ⬜ Не начато | `S07-rendering-prompt-quality-gates.md` |

## Acceptance criteria

- [ ] Self report has a structured “Ключевые доминанты карты” block based on normalized chart features and important placements.
- [ ] Self report explains an “internal mechanism” as a step-by-step behavioral model, not only as traits.
- [ ] At least 3 central contradictions are generated from chart evidence and rendered in narrative/PDF.
- [ ] House interpretations are scenario-based and include manifestation + shadow/risk.
- [ ] Major claims can expose bases: astrological fact, psychological mechanism, limitation/counter-evidence.
- [ ] Vulnerability section includes concrete failure modes, not only soft generic advice.
- [ ] Self report includes “Как это видно в жизни” with practical recognisable patterns.
- [ ] Self report includes calibration questions; answers are not required for MVP, but the contract supports future feedback storage.
- [ ] Self report includes maturity levels: low / medium / high expression.
- [ ] Career teaser is useful but bounded; it does not list a full career plan or replace Career product.
- [ ] PDF contains the same new semantic blocks as web, with technical details still after narrative.
- [ ] Regression checks prevent raw English enum leaks, ungrounded LLM claims, missing required sections, and Self/Career boundary violations.

## Implementation notes

### Backend

Likely touched modules:

- `backend/app/modules/report_narratives/schemas.py`
- `backend/app/modules/report_narratives/input_builder.py`
- `backend/app/modules/report_narratives/prompts/self_story_v*.md`
- `backend/app/modules/report_narratives/validators.py`
- `backend/app/modules/report_narratives/fallback.py`
- `backend/app/modules/reports/pdf.py`
- `backend/app/modules/reports/templates/report.html`
- `backend/app/chart_engine/features.py`
- `backend/app/chart_engine/socionics.py` only if calibration answers later affect type weights

### Frontend

Likely touched modules:

- `frontend/src/lib/report/view-model.ts`
- `frontend/src/components/report/report-narrative-page.tsx`
- `frontend/src/components/report/narrative-section.tsx`
- `frontend/src/components/report/evidence-notes.tsx`
- new components if needed:
  - `dominants-section.tsx`
  - `inner-mechanism-section.tsx`
  - `calibration-questions.tsx`
  - `maturity-levels.tsx`
- `frontend/scripts/check-report-ux.mjs`

## Data contract sketch

```ts
interface DeepSelfNarrative {
  dominants: DominantInsight[];
  inner_mechanism: MechanismStep[];
  house_scenarios: HouseScenario[];
  contradictions: ContradictionInsight[];
  system_failures: FailureMode[];
  life_manifestations: string[];
  maturity_levels: {
    low: string;
    medium: string;
    high: string;
  };
  calibration_questions: CalibrationQuestion[];
  career_teaser: CareerTeaser;
}
```

Every item with interpretive weight should carry evidence refs:

```ts
interface EvidenceBackedInsight {
  title: string;
  body: string;
  evidence_refs: string[];
  limitation?: string;
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

```bash
docker compose ps
curl http://localhost:8000/api/v1/health
# register -> verify -> login -> generate self report -> poll ready -> open web report -> download PDF
```

## Risks

- LLM may hallucinate evidence if the prompt does not force evidence IDs.
- Report may become too long if every block is expanded by default.
- Career teaser may leak too much Career value into Self.
- Calibration answers can create product/legal expectations if treated as psychological diagnosis.
- Existing reports may need narrative prompt version bump and refresh policy.

## Open decisions

- Whether E13 should introduce `self_story_v2` or extend current `self_story_v1` with a strict migration note. Preferred: create `self_story_v2`.
- Whether calibration answers are stored immediately or only rendered as questions in MVP. Preferred: render-only in first iteration, storage in follow-up.
- Whether dominants are deterministic-only or LLM-rendered from deterministic input. Preferred: deterministic extraction + LLM wording.
- Whether maturity levels are generic by archetype or generated per chart. Preferred: generated from structured deterministic evidence with validator constraints.
