# SRS-E15 — Self Report Human Storytelling

> Эпик: E15 Self Report Human Storytelling
> Статус: ⬜ Не начато
> Дата: 2026-07-02

## 1. Введение

### 1.1 Назначение

Документ описывает требования к улучшению человеческого сторителлинга в Astrotype Self report. Цель — сохранить deterministic/evidence-backed основу E13/E14, но сделать пользовательский текст менее сухим, менее канцелярским и более узнаваемым.

### 1.2 Область действия

SRS покрывает staged prompt v2, assembler rhythm, tone/readability validators, frontend/PDF readability and live rollout verification.

## 2. Общее описание

### 2.1 Текущая проблема

Система уже генерирует структурированный staged narrative, но реальный отчёт может звучать как служебная аналитическая сводка. Пользователь получает корректные мысли, но мало живого “попадания”.

### 2.2 Целевое состояние

Self report должен читаться как персональный портрет:

```text
узнавание → личная формула → жизненная сцена → внутреннее напряжение → защитная стратегия → зрелая форма → мягкий вопрос
```

При этом все значимые claims остаются grounded in known evidence.

## 3. Функциональные требования

### FR-1. Recognition-first hero

Hero должен начинаться с человеческого узнавания и основной личной формулы, а не с raw placements, socionics labels, scores или technical evidence.

### FR-2. Lived manifestation per key section

Каждая ключевая секция Self должна содержать минимум одно конкретное жизненное проявление: как паттерн виден в реакции, выборе, контакте, близости, защите, принятии решения или развитии.

### FR-3. Narrative chain

Ключевые секции должны следовать смысловой цепочке:

```text
meaning -> scenario -> tension/risk -> mature expression
```

Порядок может быть естественным в прозе, но смысловые элементы должны присутствовать.

### FR-4. Staged prompt v2

Система должна использовать file-backed staged prompt family v2 для humanized Self generation and assembly. v1 prompts must not be silently mutated.

### FR-5. Assembler rhythm

Assembler должен сохранять достаточный объём секционных stage outputs и не сжимать по умолчанию каждую секцию до одного параграфа.

### FR-6. Tone quality gates

Validators должны обнаруживать:

- канцелярит и overly abstract prose;
- repeated service terms without concrete manifestation;
- generic horoscope prose;
- technical-first hero;
- unsupported therapy/diagnostic/fatalistic language.

### FR-7. Evidence discipline

Humanization must not weaken evidence validation. Unknown evidence refs, unsupported aspects and Self/Career boundary violations remain invalid.

### FR-8. Frontend/PDF readability

Web and PDF must preserve paragraph rhythm, narrative-first order and secondary evidence disclosure.

### FR-9. Runtime smoke

The reference local Self report must be regenerated and inspected before closing the feature.

## 4. Нефункциональные требования

- Safety: no medical, diagnostic, fatalistic or manipulative language.
- Readability: prose should be understandable without knowing astrology terms.
- Testability: prompt/tone rules must be covered by structural tests.
- Backward compatibility: old narrative rows should not break frontend.
- Observability: tone validation failures should be logged without prompt bodies or secrets.

## 5. Data / Contract

No mandatory public API schema change is required for MVP. Existing `SelfNarrative` can carry richer strings/paragraphs if current schema supports them.

If needed, section body may be normalized as:

```ts
type NarrativeBody = string | string[];
```

Frontend view-model must preserve paragraph boundaries regardless of storage shape.

## 6. Architecture

### Backend

- `prompts/` owns versioned humanized prompt files.
- `assembler.py` owns final section rhythm and composition.
- `validators.py` owns evidence/safety/tone gates.
- `service.py` owns generation, recovery and structured logging.

### Frontend

- view-model normalizes body paragraphs;
- report components render narrative first;
- evidence notes stay collapsed/secondary;
- PDF action does not dominate first screen.

### PDF

PDF template renders the same narrative content and preserves paragraph breaks.

## 7. API

No new endpoint is required.

Existing endpoints remain:

- `GET /api/v1/reports/{report_id}`;
- `POST /api/v1/reports/{report_id}/narrative/regenerate`;
- report PDF endpoint according to current route contract.

## 8. Frontend integration

Required first-read order:

1. Recognition-first hero.
2. Main formula.
3. Humanized sections with lived manifestations.
4. Relationships/closeness/development.
5. Career teaser if present, bounded.
6. Evidence/calculation/technical details.
7. PDF/save action below meaningful narrative blocks.

## 9. Verification criteria

Backend:

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives -q'
docker compose exec -T backend sh -lc 'cd /app && python -m ruff check app/modules/report_narratives tests/unit/test_report_narratives && python -m ruff format --check app/modules/report_narratives tests/unit/test_report_narratives'
docker compose exec -T backend sh -lc 'cd /app && python -m mypy app/modules/report_narratives'
```

Frontend:

```bash
cd frontend
node scripts/check-report-ux.mjs
npx tsc --noEmit --pretty false
npx prettier --check src/components/report src/lib/report scripts/check-report-ux.mjs
```

Runtime:

- regenerate the reference Self report;
- poll until ready;
- inspect web first screen;
- verify PDF 200 and content parity;
- compare before/after narrative quality notes.

## 10. Dependencies

- E11 LLM narrative storage/API.
- E12 runtime readiness.
- E13 semantic depth blocks.
- E14 staged narrative pipeline.

## 11. Risks

- Over-humanization may become vague or manipulative if evidence discipline weakens.
- Tone validator may reject acceptable prose too aggressively.
- Longer prose may hurt mobile/PDF readability.
- Model-specific style variance may require prompt examples and tests to be stronger than provider defaults.
