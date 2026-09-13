# S02: Career storage и versioned domain schemas

## Статус

⬜ Не начато

## Контекст

Career Dimensions, ответы, contradictions, role matches и narrative должны быть воспроизводимыми и версионированными. Хранить их одним mutable JSON без provenance недостаточно.

## Что сделать

Добавить additive storage для:

- `career_profiles` — root artifact: user/profile/chart, lifecycle, versions;
- `career_dimension_scores` — dimension, score, confidence, scoring version;
- `career_dimension_evidence` — source fact/entity, contribution, direction;
- `career_questionnaire_sessions` и `career_answers` — versioned questions/answers;
- `career_resolutions` — confirmations, contradictions, preferences;
- `career_archetype_scores`;
- `career_environment_axes` и anti-environment conditions;
- `career_role_matches` и `career_path_steps`;
- `career_interpretation_facts`;
- `career_segment_generations`;
- `career_reports` — immutable versioned assembled artifacts.

DTO должны отделять persisted deterministic contracts от LLM responses и client view models.

## Инварианты

- Все rows связаны с конкретным `chart_id` и версией правил.
- Score хранится в диапазоне `0..100`, confidence — `0..1`.
- Evidence ссылается только на реально существующий chart/fact source.
- Questionnaire version и scoring/prompt/reference versions сохраняются в artifact lineage.
- Новый пересчёт создаёт новую версию, а не перезаписывает готовую.
- Raw answers не передаются LLM без resolver/curation.

## Критерии приёмки

- [ ] Миграции additive и reversible без удаления существующих reports/charts.
- [ ] Pydantic/ORM schemas фиксируют ranges, enums и version fields.
- [ ] Career artifact можно восстановить из PostgreSQL без Redis/LLM cache.
- [ ] Каждый dimension имеет evidence и scoring version.
- [ ] Answers, resolver output и report versions имеют явный lineage.
- [ ] Повторная генерация не создаёт дубликаты при одном idempotency key/generation ID.
- [ ] Repository tests доказывают ownership и immutable history.
