# SRS-E19: Astrotype Career Report

Статус: целевой контракт; реализация не начата

Feature: `docs/features/E19-career-report/FEATURE.md`

Design source: `docs/design/astrotype_career_report.md`

## 1. Назначение

Career Report должен объяснять профессиональную механику пользователя на основе уже рассчитанной Astrotype v2 натальной карты и versioned контрольных ответов. Система должна переходить от evidence-backed факторов к измерениям, среде, ролям и траекториям до LLM-генерации текста.

## 2. Принципы

1. Один астрологический фактор не назначает качество, роль или профессию.
2. Все основные выводы вычисляются детерминированно и версионируются.
3. Score и confidence — разные величины.
4. Ответы пользователя уточняют применение склонностей, но не переписывают натальную карту.
5. Противоречие capability/preference является результатом, а не ошибкой.
6. LLM пишет только по curated interpretation facts.
7. Роли идут раньше профессий; профессии являются примерами.
8. Рекомендации условны и не обещают доход/найм/успех.
9. Deterministic report доступен раньше полного narrative.
10. Старые карты, ответы и Career-версии не перезаписываются.

## 3. Текущее состояние и migration boundary

Current code имеет legacy `product='career'`, `career_full`, v1 rules engine и synchronous UI timeout 30 секунд. Target E19 использует новые storage/API/contracts. Legacy output не считается target Career и не должен автоматически подмешиваться в новый payload.

До implementation S01 обязан решить:

- canonical report identifier;
- active Plus vs legacy one-time entitlement;
- grandfathering существующих покупок;
- период совместного чтения legacy и target artifacts;
- дату выключения legacy generation.

## 4. Входные данные

### 4.1 Обязательные

- `user_id`, `profile_id`, `chart_id`;
- normalized planets/houses/aspects/balances/patterns;
- persisted natal facts/evidence;
- engine/reference/scoring versions;
- completed questionnaire session и answers.

### 4.2 Запрещённые в MVP

- соционика/MBTI/Model A;
- скрытый scraping CV/social accounts;
- транзиты и career timing;
- client-calculated scores;
- raw natal chart как LLM prompt input.

## 5. Career Dimension contract

MVP dimensions:

| Key                   | Пользовательский смысл                                 |
| --------------------- | ------------------------------------------------------ |
| `leadership`          | Ответственность, направление, решения, влияние         |
| `analytical_thinking` | Факты, детали, закономерности, декомпозиция            |
| `systems_thinking`    | Взаимосвязи, причинность, архитектура сложного         |
| `communication`       | Объяснение, переговоры, передача знаний                |
| `creativity`          | Новизна, концепции, нестандартные решения              |
| `structure`           | Правила, процессы, планирование, предсказуемость       |
| `autonomy`            | Самостоятельность и пространство решений               |
| `risk_tolerance`      | Неопределённость, эксперимент, ответственность за риск |
| `people_orientation`  | Команды, поддержка, развитие других                    |
| `innovation`          | Технологии, изменения, альтернативные подходы          |
| `long_term_focus`     | Длинный горизонт и сохранение направления              |
| `execution`           | Темп, системность, доведение до результата             |

Каждая запись обязана содержать:

```json
{
  "dimension": "systems_thinking",
  "score": 91,
  "confidence": 0.84,
  "scoring_version": "career-mvp-1",
  "evidence": [
    {
      "source_type": "natal_fact",
      "source_id": "uuid",
      "contribution": 0.18,
      "direction": "supports"
    }
  ]
}
```

## 6. Scoring и confidence

```text
raw_score = Σ(normalized_factor × weight)
score = calibrated normalization to 0..100
confidence = independent evidence coverage × agreement × source quality
```

Требования:

- weight/config версионируется;
- positive, counter и missing signals учитываются явно;
- коррелированные факторы имеют cap/grouping;
- неизвестное время рождения не создаёт вымышленные houses/angles;
- calibration fixtures фиксируют ожидаемые ranges, не только exact snapshots;
- LLM не участвует в вычислении.

## 7. Questionnaire и Profile Resolver

MVP: 8–12 вопросов по leadership/people management, autonomy, risk, expert/manager/entrepreneur preference, текущей деятельности, опыту и цели.

Хранилище обязано сохранять questionnaire version, draft/completed state, answers, timestamps и consent/context version.

Resolver формирует:

- `confirmed_traits`;
- `contradictions`;
- `preferences`;
- `context_constraints`;
- `unresolved_ambiguities`.

Высокий leadership + нежелание управлять людьми должно вести к expert leadership scenarios, а не к игнорированию ответа или снижению capability score.

## 8. Archetypes и environment

Система возвращает Top-3 versioned archetypes с score/confidence/evidence.

MVP catalog может включать Strategist, Builder, Analyst, Architect, Operator, Leader, Entrepreneur, Creator, Communicator, Advisor, Researcher, Coordinator, Specialist; окончательный набор/локализация фиксируются versioned seed data.

Environment axes:

- structured ↔ flexible;
- stable ↔ dynamic;
- individual ↔ collaborative;
- expert ↔ managerial;
- operational ↔ strategic;
- predictable ↔ experimental;
- supportive ↔ competitive;
- small team ↔ large organization;
- local ↔ global;
- execution ↔ ownership.

Anti-environment описывает условия и компенсации, а не категорические запреты.

## 9. Role matching и paths

Role match обязан использовать несколько dimensions, environment, preferences и context. Ответ содержит match category, score, confidence, reasons, tensions и requirements.

Категории:

- `strong_match`;
- `possible_match`;
- `context_dependent`.

Profession examples прикрепляются к role family и не являются предписанием. Career paths строятся из versioned graph/catalog. LLM не может добавлять отсутствующие nodes/edges.

## 10. Interpretation Facts и LLM boundary

`CareerInterpretationFacts` — единственный content input narrative pipeline. Он включает только curated dimensions, resolver output, archetypes, environment, role matches, paths и evidence refs.

LLM разрешено:

- писать связный текст;
- объяснять механизмы и противоречия;
- давать примеры только из разрешённого catalog result;
- менять категоричность согласно confidence.

LLM запрещено:

- считать карту/scores/matches;
- придумывать profession/path;
- игнорировать contradictions;
- давать диагнозы или гарантии;
- делать direct planet-to-profession claim.

## 11. Report sections

Порядок MVP:

1. professional_summary;
2. work_style;
3. strengths;
4. decision_making;
5. leadership_and_influence;
6. optimal_environment;
7. risk_environment;
8. career_archetypes;
9. role_families;
10. career_paths.

Для каждой секции фиксируются owned/reference/forbidden fact keys. Web и PDF используют один assembled persisted payload.

Канонический визуальный контракт: `docs/design/astrotype-career-report-sample.html`. Он задаёт широкий standalone reader, narrative-first порядок, тёмные полноразмерные секции, сдержанную золотую палитру и поддерживающий расчётный слой после основного отчёта. Текущий legacy dashboard reader не является визуальной целью.

## 12. Lifecycle

```text
questionnaire_draft
→ questionnaire_completed
→ queued
→ calculating_dimensions
→ deterministic_ready
→ generating_sections
→ ready | narrative_failed | failed
```

- `deterministic_ready` должен быть полезен пользователю.
- Narrative failure сохраняет deterministic result.
- Section retry не пересчитывает chart/dimensions.
- Natal chart пересчитывается только при изменении birth data/engine version.

## 13. API

| Method | Path                                          | Назначение                   |
| ------ | --------------------------------------------- | ---------------------------- |
| GET    | `/api/v1/career/questionnaires/current`       | Получить version/draft       |
| PUT    | `/api/v1/career/questionnaires/{id}/answers`  | Сохранить draft              |
| POST   | `/api/v1/career/questionnaires/{id}/complete` | Зафиксировать answers        |
| POST   | `/api/v1/career/reports`                      | Создать generation           |
| GET    | `/api/v1/career/generations/{id}`             | Получить progress/result IDs |
| GET    | `/api/v1/career/reports/{id}`                 | Прочитать progressive report |
| GET    | `/api/v1/career/reports/{id}/sections`        | Состояние секций             |
| POST   | `/api/v1/career/reports/{id}/regenerate`      | Retry narrative scope        |
| GET    | `/api/v1/career/reports/{id}/pdf`             | Скачать PDF                  |

Create/complete/regenerate требуют idempotency. Все маршруты требуют ownership и target access policy. Locked responses не содержат protected content.

## 14. Data model

Минимальные сущности:

- `career_profiles`;
- `career_dimension_scores`;
- `career_dimension_evidence`;
- `career_questionnaire_sessions`;
- `career_answers`;
- `career_resolutions`;
- `career_archetype_scores`;
- `career_environment_axes`;
- `career_role_matches`;
- `career_path_steps`;
- `career_interpretation_facts`;
- `career_segment_generations`;
- `career_reports`.

Конкретная нормализация может объединять малые child structures в JSONB, но root lineage, scores/evidence, questionnaire/answers, segment statuses и report versions должны оставаться независимо queryable/auditable.

## 15. Non-functional requirements

| ID         | Требование                                                                |
| ---------- | ------------------------------------------------------------------------- |
| NFR-E19.1  | Deterministic engine воспроизводим без LLM/network.                       |
| NFR-E19.2  | Durable source of truth — PostgreSQL; Redis не хранит единственную копию. |
| NFR-E19.3  | Ownership/access fail closed на каждом endpoint/artifact.                 |
| NFR-E19.4  | Generation idempotent и retry-safe.                                       |
| NFR-E19.5  | Existing charts/reports/payments не удаляются миграциями.                 |
| NFR-E19.6  | Raw answers и персональные payloads не попадают в logs/metrics labels.    |
| NFR-E19.7  | Reader mobile-first, keyboard accessible и пригоден для PDF/print.        |
| NFR-E19.8  | Provider timeout/failure сохраняет deterministic report.                  |
| NFR-E19.9  | Scoring/reference/prompt/model versions доступны для аудита.              |
| NFR-E19.10 | Latency/cost budgets измеряются на staging до rollout.                    |

## 16. Quality gates

- score/confidence/evidence completeness;
- correlated-evidence control;
- contradiction retention;
- direct planet-to-profession ban;
- unsupported role/path ban;
- generic prose/duplication check;
- low-confidence conditional language;
- no diagnosis/income/employment guarantees;
- one source payload for web/PDF;
- no socionics/MBTI fields/imports;
- locked response leakage tests.

## 17. Verification

1. Unit tests каждого deterministic builder.
2. Golden fixtures и property/boundary tests.
3. PostgreSQL repository/migration/idempotency tests.
4. Questionnaire/resolver contradiction fixtures.
5. Mock и real-provider schema/quality tests.
6. Async API lifecycle + ownership/access tests.
7. Frontend questionnaire, polling, reader and accessibility tests.
8. PDF parity tests.
9. Staging end-to-end на реальном профиле.
10. Legacy/grandfather/locked account smoke.
11. Production canary, metrics и rollback proof.

## 18. Data safety и rollout

- Additive migrations only.
- Backup/restore rehearsal на staging dump.
- Row counts/checksums legacy reports/payments/entitlements.
- Feature flag off по умолчанию.
- Нет автоматического mutable backfill legacy Career.
- Rollback прекращает новые generation, но сохраняет artifacts.
- Parent Feature нельзя закрывать, пока хотя бы одна Story не имеет code/test/runtime evidence.
