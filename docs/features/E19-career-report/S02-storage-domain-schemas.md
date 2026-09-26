# S02: Career storage и versioned domain schemas

## Статус

✅ Завершено — deterministic artifacts имеют generation lineage; конкурентная idempotency и immutable history доказаны

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

- [x] Миграции additive и reversible без удаления существующих reports/charts.
- [x] Pydantic/ORM schemas фиксируют ranges, enums и version fields.
- [x] Career artifact можно восстановить из PostgreSQL без Redis/LLM cache.
- [x] Каждый dimension имеет evidence и scoring version.
- [x] Answers, resolver output и report versions имеют явный lineage.
- [x] Повторная генерация и конкурентный retry не создают дубликаты при одном idempotency key/generation ID.
- [x] Repository tests доказывают ownership и immutable history всех deterministic artifacts.

## Evidence

- `backend/app/modules/career/models.py`, `schemas.py`, `repository.py`
- `backend/alembic/versions/e4f5a6b7c8d9_add_career_report_foundation.py`
- `backend/tests/unit/test_career/test_storage_contract.py`
- `uv run pytest tests/unit/test_career/test_storage_contract.py -q` → `4 passed`
- Local PostgreSQL: upgrade до `e4f5a6b7c8d9`, `13` Career tables; committed Career artifact восстановлен через repository только из PostgreSQL, затем smoke rows удалены.
- Reversibility smoke: downgrade до `d3e4f5a6b7c8` удалил только `career_*` tables, legacy row counts не изменились; повторный upgrade вернул DB на `e4f5a6b7c8d9 (head)`.
- Backup перед migration: `backend/backups/pre-e19-career-20260916T063852Z.dump`.
- Migration `b7c8d9e0f1a2` добавляет non-null `generation_id` и generation-scoped uniqueness для dimensions, resolution, archetypes, environment, roles и interpretation facts; upgrade/downgrade/re-upgrade проверены на disposable PostgreSQL.
- Atomic PostgreSQL `ON CONFLICT ... RETURNING`, profile-row version lock и queued-generation claim закрывают API/worker race; integration tests доказывают один generation, один enqueue/claim и две независимые immutable версии.

S03 adapter и golden contract доказали построение всех 12 persisted score rows с `scoring_version` и связанными evidence rows.

## Аудит 2026-09-26

- Оба расхождения закрыты migration/repository/worker contracts и PostgreSQL concurrency regressions; audit note сохранён как историческое основание изменений.
