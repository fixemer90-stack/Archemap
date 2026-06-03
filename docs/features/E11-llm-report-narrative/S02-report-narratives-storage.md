# Story E11.S02: Storage — report_narratives model and migration

**Feature:** [LLM Report Narrative](FEATURE.md)
**Статус:** ⬜ Не начато

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

- [ ] Таблица `report_narratives` создаётся миграцией и откатывается downgrade-ом.
- [ ] `content` хранит validated narrative JSON, а не Markdown string.
- [ ] `input_hash` обязателен для completed narrative records.
- [ ] Можно хранить несколько prompt versions для одного report.
- [ ] При удалении report narrative записи удаляются cascade-ом.
- [ ] `python3 -m ruff format alembic/versions/` применён к миграции.
- [ ] Backend unit/migration smoke tests проходят.
