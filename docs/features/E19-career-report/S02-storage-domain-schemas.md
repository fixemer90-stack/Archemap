# S02: Career storage и versioned domain schemas

## Статус

🟡 Частично — additive ORM/migration/DTO/repository foundation и PostgreSQL restore proof готовы; dimension-engine completeness остаётся открытой

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
- [ ] Каждый dimension имеет evidence и scoring version.
- [x] Answers, resolver output и report versions имеют явный lineage.
- [x] Повторная генерация не создаёт дубликаты при одном idempotency key/generation ID.
- [x] Repository tests доказывают ownership и immutable history.

## Evidence

- `backend/app/modules/career/models.py`, `schemas.py`, `repository.py`
- `backend/alembic/versions/e4f5a6b7c8d9_add_career_report_foundation.py`
- `backend/tests/unit/test_career/test_storage_contract.py`
- `uv run pytest tests/unit/test_career/test_storage_contract.py -q` → `4 passed`
- Local PostgreSQL: upgrade до `e4f5a6b7c8d9`, `13` Career tables; committed Career artifact восстановлен через repository только из PostgreSQL, затем smoke rows удалены.
- Reversibility smoke: downgrade до `d3e4f5a6b7c8` удалил только `career_*` tables, legacy row counts не изменились; повторный upgrade вернул DB на `e4f5a6b7c8d9 (head)`.
- Backup перед migration: `backend/backups/pre-e19-career-20260916T063852Z.dump`.

Открытый proof gate: S03 должен доказать, что все 12 dimensions реально сохраняются с непустым evidence.
