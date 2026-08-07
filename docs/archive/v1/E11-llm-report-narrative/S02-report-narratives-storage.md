# Story E11.S02: Storage — report_narratives model and migration

**Feature:** [LLM Report Narrative](Archemap/docs/features/v1/E11-llm-report-narrative/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Narrative text нужно хранить отдельно от deterministic report data, чтобы можно было регенерировать текст, версионировать prompt/model, сравнивать output, откатывать плохую генерацию и не пересчитывать chart/rules.

## Что сделать

1. Создать SQLAlchemy model `ReportNarrative`.
2. Добавить Alembic migration для таблицы `report_narratives`.
3. Связать `report_narratives.report_id` с `reports.id` через FK cascade.
4. Зафиксировать поля: `product`, `prompt_version`, `model_provider`, `model_name`, `status`, `content`, `input_hash`, `error_message`, `generation_started_at`, `generation_finished_at`, `generation_attempts`.
5. Добавить индексы для lookup по `report_id`, `status`, `input_hash`, `prompt_version`.
6. Добавить uniqueness policy для cache lookup: `report_id + product + prompt_version + input_hash + model_name`.
7. Добавить model tests или migration smoke tests.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/report_narratives/models.py` | Новый SQLAlchemy model |
| `backend/alembic/versions/*_add_report_narratives_table.py` | Migration |
| `backend/app/modules/reports/models.py` | Relationship при необходимости |
| `backend/tests/unit/test_report_narratives/test_models.py` | Model/migration-level tests |

## Критерии приёмки

- [x] Таблица `report_narratives` создаётся миграцией и откатывается downgrade-ом.
- [x] `content` хранит validated narrative JSON, а не Markdown string.
- [x] `input_hash` обязателен для completed narrative records.
- [x] Можно хранить несколько prompt versions для одного report.
- [x] При удалении report narrative записи удаляются cascade-ом.
- [x] `python -m ruff format --check alembic/versions/b8c9d0e1f2a3_add_report_narratives_table.py` проходит.
- [x] Backend unit/migration smoke tests проходят.

## Реализация

Добавлены:

- `backend/app/modules/report_narratives/models.py` — SQLAlchemy model `ReportNarrative`
- `backend/alembic/versions/b8c9d0e1f2a3_add_report_narratives_table.py` — Alembic migration
- `backend/tests/unit/test_report_narratives/test_models.py` — storage/model tests

В storage-контракте зафиксированы поля:

- `report_id`
- `product`
- `prompt_version`
- `model_provider`
- `model_name`
- `status`
- `content`
- `input_hash`
- `error_message`
- `generation_started_at`
- `generation_finished_at`
- `generation_attempts`

Миграция добавляет:

- FK `report_id -> reports.id` с `ON DELETE CASCADE`
- индексы по `report_id`, `product`, `prompt_version`, `status`, `input_hash`
- unique cache key constraint `uq_report_narratives_cache_key`

## Верификация

Проверено в backend container:

```bash
cd /app
python -m pytest tests/unit/test_report_narratives/test_models.py -q
python -m ruff check app/modules/report_narratives tests/unit/test_report_narratives alembic/versions/b8c9d0e1f2a3_add_report_narratives_table.py
python -m ruff format --check app/modules/report_narratives tests/unit/test_report_narratives alembic/versions/b8c9d0e1f2a3_add_report_narratives_table.py
python -m mypy app/modules/report_narratives tests/unit/test_report_narratives
alembic upgrade head
alembic downgrade a7b8c9d0e1f2
alembic upgrade head
```
