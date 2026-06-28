# SRS-E13 — Report Depth Improvements

> Эпик: E13 Report Depth Improvements
> Статус: ✅ Готово
> Источник: `docs/Tips.md` / Obsidian `Archemap/docs/Tips`

## 1. Введение

### 1.1 Назначение

Документ описывает требования к улучшению глубины Self report в Astrotype. Цель — добавить аналитические слои, которые связывают астрологические данные, психологический механизм, жизненные сценарии, риски, зрелые формы и калибровочные вопросы.

### 1.2 Область действия

SRS покрывает backend contracts, LLM narrative prompt, validation, frontend rendering, PDF parity и quality gates для нового depth-layer отчёта.

## 2. Общее описание

### 2.1 Текущая проблема

Текущий отчёт технически корректен, но часто звучит как расширенный гороскоп: есть правильные элементы карты, но недостаточно объяснена причинно-смысловая цепочка от факта к выводу.

### 2.2 Целевое состояние

Отчёт должен читать карту через последовательность:

```text
факт → механизм → сценарий → риск → зрелая форма → проверочный вопрос
```

Пользователь должен узнавать не только качества, но и способ функционирования, противоречия, сбои и точки роста.

## 3. Функциональные требования

### FR-1. Ключевые доминанты

Система должна выделять и объяснять доминанты карты:

- стихии и модальности;
- ведущие знаки/планеты/дома;
- сильные повторяющиеся мотивы;
- напряжения, влияющие на общий паттерн.

Каждая доминанта должна иметь evidence refs.

### FR-2. Внутренний механизм личности

Система должна формировать 3–5 step-by-step механизмов поведения: как пользователь обрабатывает информацию, ищет опору, проявляется вовне и регулирует эмоции.

### FR-3. Сценарии домов

Система должна интерпретировать ключевые положения в домах как жизненные сценарии, включая manifestation и shadow/risk.

### FR-4. Центральные противоречия

Система должна выводить 3–5 центральных внутренних противоречий, основанных на карте и/или deterministic evidence.

### FR-5. Сбои системы

Система должна показывать failure modes: где сильный паттерн превращается в перегрузку, задержку действия, эмоциональную заморозку или другой риск.

### FR-6. Уровни зрелости

Система должна описывать low / medium / high expression паттерна.

### FR-7. Калибровочные вопросы

Self report должен показывать 5–7 вопросов для проверки модели пользователем. В MVP ответы не обязаны сохраняться.

### FR-8. Career teaser

Self report должен содержать содержательный, но ограниченный Career teaser. Он не должен заменять Career report.

### FR-9. Evidence tracing

Ключевые interpretive claims должны ссылаться на known evidence ids. Unknown evidence refs должны отклоняться validator-ом.

### FR-10. PDF parity

PDF должен содержать те же смысловые E13 blocks, что и web report.

## 4. Нефункциональные требования

- Narrative-first: технические детали не должны доминировать в начале Self report.
- Safety: запрещены медицинские, диагностические, фаталистичные формулировки.
- Determinism: LLM не является источником фактов, только renderer поверх structured input.
- Backward compatibility: старые отчёты не должны ломать frontend; новые поля должны иметь graceful fallback.
- Versioning: prompt must remain versioned (`self_story_v2+` prompt family, currently advanced beyond v2 without mutating v1 in place).

## 5. Модель данных

### 5.1 Suggested DTO

```ts
interface DeepSelfNarrative {
  dominants: EvidenceBackedInsight[];
  inner_mechanism: MechanismStep[];
  house_scenarios: HouseScenario[];
  contradictions: EvidenceBackedInsight[];
  system_failures: EvidenceBackedInsight[];
  life_manifestations: string[];
  maturity_levels: MaturityLevels;
  calibration_questions: CalibrationQuestion[];
  career_teaser: CareerTeaser;
}
```

### 5.2 Evidence-backed insight

```ts
interface EvidenceBackedInsight {
  title: string;
  body: string;
  evidence_refs: string[];
  limitation?: string;
}
```

### 5.3 Calibration question

```ts
interface CalibrationQuestion {
  id: string;
  question: string;
  evidence_refs: string[];
  answer_type: "yes_no" | "scale_1_5";
}
```

## 6. Архитектура

### 6.1 Backend

- deterministic chart/report data remains source of truth;
- input builder prepares evidence map and depth signals;
- prompt renders structured JSON;
- validator enforces section presence, safety and evidence refs;
- fallback generates complete safe narrative without LLM.

### 6.2 Frontend

- view-model normalizes optional E13 fields;
- UI renders blocks in narrative-first order;
- evidence remains collapsed or visually secondary;
- PDF/download actions stay below meaningful narrative blocks.

### 6.3 PDF

- template renders E13 blocks;
- calculation parameters and technical details remain near the end.

## 7. API

No new public endpoint is required for MVP.

Existing endpoints continue to serve reports:

- `POST /api/v1/reports/generate`
- `GET /api/v1/reports/{report_id}`
- `GET /api/v1/reports/{report_id}/pdf`
- `POST /api/v1/reports/{report_id}/narrative/regenerate`

If calibration answers are later persisted, add a separate endpoint such as:

```text
POST /api/v1/reports/{report_id}/calibration-answers
```

This is out of MVP scope.

## 8. Шаблоны и prompt contract

Preferred approach:

- create `self_story_v2.md`;
- do not silently mutate `self_story_v1`;
- require JSON-only output;
- require all new E13 sections;
- require evidence refs for interpretive claims;
- explicitly forbid Career deep dive in Self.

## 9. Frontend integration

Required rendering order:

1. Hero.
2. Main formula.
3. Dominants.
4. Inner mechanism.
5. House/life scenarios.
6. Strengths.
7. Contradictions.
8. System failures.
9. Relationships/closeness/sexuality.
10. Development and maturity levels.
11. Calibration questions.
12. Career teaser.
13. Final summary.
14. Save/PDF action block.
15. Calculation parameters.
16. Technical details.

## 10. Критерии верификации

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
- poll until ready;
- verify web sections;
- download PDF;
- verify PDF contains E13 sections and calculation parameters.

## 11. Зависимости

- E3 chart engine.
- E4 rules/content.
- E10 report UX redesign.
- E11 LLM narrative.
- E12 runtime readiness.

## 12. Риски

- Отчёт может стать слишком длинным: sections should be scannable and collapsible where needed.
- Evidence tracing может стать слишком техническим: keep it secondary.
- LLM может генерировать unsupported claims: validator must reject unknown refs.
- Career teaser может каннибализировать Career: strict boundary validation required.
