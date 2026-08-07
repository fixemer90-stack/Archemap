# Story E12.S06: Failure triage and launch readiness checklist

**Feature:** [LLM Report Runtime Readiness](Archemap/docs/features/v1/E12-llm-report-runtime-readiness/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

После S05 у команды уже есть пошаговый runbook. Но для реального запуска этого недостаточно: в момент сбоя нужен короткий operational triage, а до старта — однозначный launch-readiness checklist. Иначе одинаково выглядят очень разные проблемы: нет worker, выключен provider, сломан bucket bootstrap, застрял narrative task или сломался только PDF upload.

Дополнительно эта story была сверена живым локальным smoke 2026-06-07:

- `register -> verify -> login -> generate -> poll -> pdf` реально выполнен;
- controlled fallback path дошёл до `report.status=ready`;
- worker подтвердил `used_fallback=True`;
- PDF path дошёл до `pdf_generated=true` и `/pdf -> 307`.

Это даёт не только теоретический triage, но и фактическую опорную точку для readiness.

## Triage matrix: symptom -> probable cause -> next check

| Симптом | Вероятная причина | Что проверить первым | Что считается подтверждением |
|---|---|---|---|
| `POST /api/v1/reports/generate` возвращает `500` | bug в API path, stale ORM object, commit/refresh ordering, enqueue-side effect до commit | backend logs, `backend/app/modules/reports/router.py`, unit regressions на route | request снова даёт `200`, report row создан, worker получает task |
| report застрял в `generating_narrative` | worker не запущен, worker умер, queue/broker mismatch, task never consumed | `docker compose ps worker`, `docker compose logs worker`, broker env | в логах нет `Task reports.generate_report_narrative received` |
| report быстро приходит в `ready`, но narrative выглядит как fallback | provider intentionally disabled или degraded path | worker logs around `report_narrative_generation_degraded` | лог содержит `LLM narrative generation is disabled` и затем `used_fallback=True` |
| report приходит в `narrative_failed` | provider misconfigured, real API key invalid, unhandled runtime exception внутри narrative path | worker logs, `LLM_*` env, error_message в report | `error_message` и worker traceback указывают на provider/runtime failure |
| narrative task падает сразу на import/ORM exception | worker не импортировал все SQLAlchemy модели / metadata | worker traceback, task import path | ошибки вида `NoReferencedTableError`, import-time failure |
| narrative task падает на `Future attached to a different loop` | новый event loop на каждый sync Celery task | worker traceback, task helper implementation | traceback содержит cross-loop/future mismatch |
| fallback path падает на `IndexError` или похожей ошибке на пустых списках | deterministic fallback не выдерживает sparse input | worker traceback, tests for `fallback.py` | traceback указывает на `_section_notes` / пустой source list |
| `pdf_generated=false` спустя успешный narrative | PDF task не стартовал или упал после narrative success | worker logs для `reports.generate_pdf` | нет `pdf_task_success`, либо есть `pdf_task_failed` |
| `/api/v1/reports/{id}/pdf` возвращает `404` | PDF ещё не готов или upload/signing path сломан | detail endpoint (`pdf_generated`, `pdf_url`), worker logs | `pdf_generated=false` или storage error в worker logs |
| `/api/v1/reports/{id}/pdf` возвращает `307`, но скачивание с хоста не работает | signed URL указывает на internal compose host (`minio:9000`) и недоступен вне docker network | redirect `Location`, topology between host/container/minio | API path рабочий, но внешний download topology требует отдельной host-facing стратегии |
| regenerate endpoint не возвращает report в `generating_narrative` | enqueue failure / guard clause / wrong report state | response от `/narrative/regenerate`, worker logs | backend даёт 503 enqueue failure или не меняет state |

## Ключевые runtime-классы проблем

### 1. Narrative runtime failure

Сюда относятся:

- worker не запущен;
- queue/broker mismatch;
- provider misconfiguration;
- task import/runtime exception;
- loop management bug;
- fallback builder crash.

Последствия:

- report может остаться в `generating_narrative`;
- или перейти в `narrative_failed`;
- или не получить narrative payload.

### 2. Controlled degraded success

Это не failure, а допустимое состояние для local/dev smoke, если:

- provider intentionally disabled;
- worker всё равно завершает task;
- report доходит до `ready`;
- narrative payload читаемый и помечен как fallback/degraded deliverable.

Именно это состояние было live-подтверждено 2026-06-07.

### 3. Artifact publication failure

Сюда относятся:

- bucket missing;
- bad S3 credentials/endpoint;
- upload/signing failure;
- PDF task enqueue failure.

Важно: это может не ломать сам narrative-ready report, но ломает финальную PDF deliverable-цепочку.

## Что считать acceptable для local smoke

Допустимо:

- стартовый `generate` возвращает `generating_narrative`;
- provider intentionally disabled, но report потом доходит до `ready`;
- narrative строится через deterministic fallback;
- PDF формируется и `/pdf` отдаёт `307`.

Недопустимо:

- report навсегда остаётся в `generating_narrative`;
- report приходит в `narrative_failed` без понятной диагностики;
- narrative отсутствует после supposedly successful completion;
- `pdf_generated=false` при nominally successful flow;
- `/pdf` не выдаёт usable backend redirect path.

## Что блокирует rollout, а что нет

### Не блокирует локальный/dev runtime-readiness

- intentional disabled-provider fallback, если deliverable остаётся читаемым;
- использование `mock` provider вместо real provider для orchestration smoke;
- internal `minio:9000` signed URL в redirect, если задача — именно backend/runtime smoke внутри compose-контура.

### Блокирует локальный/dev runtime-readiness

- отсутствие worker service;
- непроходимый `generate` endpoint;
- narrative task crash без fallback;
- report stuck in `generating_narrative`;
- непроходимый PDF upload/signing path;
- отсутствие documented bucket bootstrap.

### Блокирует product/staging real-provider rollout

- invalid/absent `openrouter` credentials для real smoke;
- недоступность provider из backend/worker runtime;
- реальный provider path не доходит до `ready`;
- внешняя topology скачивания PDF не решена для пользовательского хоста/домена.

## Launch-readiness checklist

### A. Stack and config

- [x] Подняты `postgres`, `redis`, `minio`, `backend`, `frontend`, `worker`.
- [x] `/api/v1/health` отвечает.
- [x] Backend и worker используют согласованные `CELERY_*`, `S3_*`, `LLM_*` env.

### B. Storage bootstrap

- [x] bucket `astrotype` существует.
- [x] bucket bootstrap можно выполнить через backend runtime (`S3Storage().ensure_bucket()`).
- [x] bucket existence задокументирован как обязательное предусловие.

### C. Auth/report prerequisites

- [x] Есть path `register -> verify -> login` для нового пользователя.
- [x] Reports API реально требует verified user.
- [x] `profile_id` получается из register response или profiles API.

### D. Controlled fallback smoke

- [x] `POST /api/v1/reports/generate` возвращает `200`.
- [x] Стартовый report state наблюдается как `generating_narrative`.
- [x] Worker получает `reports.generate_report_narrative`.
- [x] Disabled-provider path не падает, а доходит до `ready` через fallback.
- [x] `narrative.status=ready` и payload читаемый.

### E. PDF artifact path

- [x] Worker получает `reports.generate_pdf`.
- [x] `pdf_generated=true`.
- [x] `pdf_url` заполнен.
- [x] `GET /api/v1/reports/{id}/pdf` отдаёт `307`.

### F. Remaining non-E12-local items

- [ ] Отдельно прогнать real-provider smoke c валидным `openrouter` key.
- [ ] Отдельно решить host-facing topology для скачивания signed URL вне compose network, если это требуется для пользовательского окружения, а не только для backend runtime smoke.

## Live readiness conclusion

Фактический вывод по состоянию на 2026-06-07:

1. E12 как local/dev runtime-readiness feature можно считать закрытой.
2. Controlled fallback smoke больше не блокируется narrative runtime дефектами:
   - API generate path проходит;
   - worker path проходит;
   - fallback path проходит;
   - PDF path проходит.
3. S06 можно считать начатой и завершённой на основании реального smoke и документированного triage/checklist.
4. Для следующего этапа допустимо идти дальше, потому что блокеров уровня «стек не поднимается / report не собирается / PDF не публикуется» больше не осталось.
5. Остающиеся задачи относятся уже не к базовой локальной runtime-readiness E12, а к отдельной real-provider/product verification.

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `docs/features/E12-llm-report-runtime-readiness/S06-failure-triage-launch-checklist.md` | Основной triage/checklist doc |
| `docs/features/E12-llm-report-runtime-readiness/S05-local-runbook-start-logs-smoke.md` | Ссылка на live-verified smoke и runbook |
| `docs/SRS/SRS-E12-llm-report-runtime-readiness.md` | Синхронизированные verification notes |

## Критерии приёмки

- [x] Есть короткий triage по основным runtime-сбоям narrative workflow.
- [x] Есть финальный checklist «готовы запускать LLM-report».
- [x] Команда понимает, какие проблемы относятся к E11 logic, а какие — к E12 runtime enablement.
