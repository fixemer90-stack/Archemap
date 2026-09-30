# S12: QA, observability, migration и rollout

## Статус

🟡 Stage mock rollout, observability и dashboard evidence собраны; production Career включён 2026-09-30; legacy readability, real-provider canary cost/latency и production report/PDF IDs остаются открытыми

## Контекст

Career объединяет deterministic scoring, пользовательские ответы, LLM, access policy и long-running runtime. Закрытие по unit tests одного слоя недостаточно.

## Что сделать

### Quality suites

- Golden natal fixtures с ожидаемыми dimension ranges/evidence.
- Разные answers при одной карте: manager vs expert leader vs entrepreneur preference.
- Missing/unknown birth time без invented houses/ASC.
- Contradiction retention и low-confidence wording.
- Role/path catalog integrity.
- Prompt/input snapshots и LLM schema validation.
- Anti-generic, duplication, overclaim, diagnosis и direct profession validators.
- API ownership/access/idempotency/concurrency.
- Web/PDF parity.

### Наблюдаемость

- generation duration по deterministic/narrative stage;
- failure/retry/stuck counts по безопасному error code;
- dimension/role catalog version adoption;
- questionnaire completion/drop-off без хранения ответов в labels;
- provider cost/token metrics без персонального payload;
- alert на stuck generation и массовый validator failure.

### Rollout

1. Migration + feature flag off.
2. Backfill не выполняется автоматически для legacy Career.
3. Staging с mock provider; real-provider quality/cost gate выполняется отдельно перед production rollout.
4. Проверить active Plus, grandfathered legacy и locked account.
5. Проверить deterministic-first reader, PDF, section retry и provider failure.
6. Canary cohort; сравнить outcomes/latency/cost.
7. Включить target UI; legacy route оставить только на ограниченное migration window.
8. Отключить legacy generation после доказанного переноса доступа/истории.

## Data safety

- Backup/restore rehearsal перед production migration.
- Row counts/checksums для profiles, legacy reports, payments, entitlements.
- Additive tables/columns only.
- Никакого drop/truncate/mutable backfill существующих Career payloads.
- Rollback выключает новые writes, но сохраняет все новые artifacts.

Операторский порядок, бюджеты, метрики, backup/checksum preflight, staging matrix и rollback: [`S13-rollout-runbook.md`](S13-rollout-runbook.md). Исполнение stage-публикации и сбор live evidence: [`S14-stage-publication-live-evidence.md`](S14-stage-publication-live-evidence.md).

## Реализация

- Полный Career unit suite покрывает golden dimensions, missing houses, low confidence, contradictions, manager/expert leader/entrepreneur divergence, catalogs, schema/prompt validation, anti-generic/duplication/overclaim/diagnosis/profession gates и web/PDF contract.
- DB-backed integration suite проверяет durable lifecycle, progressive deterministic-first read, partial failure, ownership-bound read, idempotent create и отсутствие protected payload в locked response.
- `app.modules.career.observability` создаёт low-cardinality OpenTelemetry metrics без ответов, prompt/report payload и UUID в labels.
- API экспортирует метрики через OTLP только при заданном `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`; без endpoint поведение явно выключено.
- Worker измеряет deterministic/narrative duration, safe failures/retries, scoring/catalog adoption и section outcomes.
- Local/staging/production Compose запускают отдельный singleton Celery Beat scheduler; topology regression запрещает отсутствие scheduler и `worker --beat`. Live alert path всё ещё требует stage readback/observation evidence.
- Provider token/cost telemetry использует явно помеченную оценку по размеру текста и настраиваемым ставкам; authoritative billing остаётся внешней сверкой провайдера.
- `CAREER_REPORT_ENABLED=False` остаётся default rollback gate; rollback не удаляет target/legacy artifacts.

## Локальное evidence

- `uv run pytest tests/unit/test_career -q` → `64 passed`.
- `uv run pytest tests/unit -q` → `526 passed`.
- isolated PostgreSQL `uv run pytest tests/integration -q` → `2 passed`.
- `node scripts/check-career-product-ux.mjs` → passed.
- `node scripts/check-career-report-reader.mjs` → passed.
- Playwright Career browser suite → `5 passed, 1 skipped`: desktop/mobile questionnaire, reader, Axe, screenshots, print и browser PDF.
- Browser smoke включён в GitHub Actions `test-frontend`; failure artifacts сохраняют `playwright-report` и `test-results`.
- Career rollout/OTEL settings добавлены в local/staging/production env examples; local Compose передаёт одинаковые settings API и worker.
- Repo-wide ruff/mypy, frontend test/type/lint/build и docs Prettier выполняются повторно после последнего edit; точный текущий SHA записывается после commit/CI.
- GitHub Actions `CI` для exact browser-smoke/docs HEAD `a821404d0b010fc9f1f1cd04d01170a825dc29b8` → success; run `36210137484`, все семь jobs завершены успешно, включая frontend Playwright smoke.

## Критерии приёмки

- [x] Все deterministic, resolver, role/path, LLM, API и UI suites зелёные локально.
- [x] Staging mock-provider report проходит structural/human product review по design-документу; real-provider prose quality проверяется до production rollout.
- [x] Locked/expired аккаунт не получает protected Career data в policy/API regression suites.
- [x] Grandfathered legacy владелец сохраняет policy access; production matrix остаётся в runbook.
- [x] Старые Career reports/PDF не мигрируются и не используются target API по explicit migration boundary.
- [ ] Legacy Career reader/PDF readability после target migrations подтверждена отдельным regression/live matrix evidence.
- [x] Метрики/alerts доказывают отсутствие stuck pipeline.
- [x] Cost/latency budgets зафиксированы в runbook.
- [x] Staging latency/token/cost measurement и dashboard links записаны как rollout evidence.
- [x] Rollback feature flag покрыт contract test и не выполняет destructive migration/backfill.
- [x] Точный зелёный SHA текущего browser-smoke изменения и CI run записаны в Story.
- [ ] Canary cohort/result и полный observation window записаны как rollout evidence.
- [ ] Production smoke report/PDF IDs записаны в Story перед `✅`.

## Аудит 2026-09-26

- Exact green Career revision: `3fbd11948a9676d440915cd5abcd50dbbf7aa3c5`; CI run `36285160532`, семь jobs `success`, включая обновлённый desktop/mobile Chromium sample-parity smoke.
- Scheduler implementation gap закрыт dedicated Beat services и regression tests; stage zero-stuck/alert-path evidence остаётся открытым до deploy.
- Stage остаётся на marker `3462865ed1a7158023c99bc491044dcea048ad23`, target Career routes в running backend отсутствуют, `LLM_ENABLED=false`, `LLM_PROVIDER=mock`, OTLP endpoint пуст. По решению владельца продукта от 27 сентября 2026 года mock LLM достаточен для S14; требуется включить и проверить именно mock runtime, routes, worker/scheduler и OTLP.

## Stage evidence 2026-09-27

- Опубликован exact SHA `20dcfbfce5ed1e2cb540261e4a1223683b89d7a7`; CI run `36308536986`, семь jobs `success`.
- Mock-provider report `c84bfae8-6ed3-4a92-b841-733cbf0c59fb` содержит 10 секций в каноническом порядке, claims/citations и assembled payload; exact duplicates, diagnosis, guaranteed outcomes и profession prescription не обнаружены.
- Generation duration `1.892 s`; estimated mock usage `23066` input / `9063` output tokens; configured cost `$0`. Эти значения не заменяют real-provider canary measurements.
- Backend и worker экспортируют Career metrics в `http://otel-collector:4318/v1/metrics`; collector принял 16 Career metric batches.
- За observation window scheduler четыре раза выполнил `career.monitor_pipeline`: stuck deterministic `0`, stuck narrative `0`, validator failures `0`, alerts `[]`.
- Dashboard опубликован 29 сентября 2026 года на `https://staging.astrotype.ru/career-metrics/graph`; targets/status доступны на `/career-metrics/targets`. Без Basic Auth оба пути возвращают `401`.
- Stage marker `4c1423ccd10a9b4d1cf9a95fac5885dbde75e73a`; CI run `36510730869`, все семь jobs `success`.
- Prometheus target `http://otel-collector:9464/metrics` имеет health `up`. Live readback: `career_operations_total` — 14 series; `career_operation_duration_seconds_count` — 2 series; `career_provider_tokens_token_total` — 2 series со значениями `144297`/`52443`; `career_provider_cost_usd_USD_count` — 1 series со значением `60`.
- На stage `0` legacy Career report rows; live readability старого reader/PDF не может быть доказана без fixture или отдельного regression evidence.
- Canary и production Career report/PDF rollout не выполнялись.

## Production evidence 2026-09-30

- В production выкачен релиз `7fc40de9822f15691ff44d7c2c3ac02c3a07213a` (та же revision, что и на stage).
- Career включён: `.env.production` → `CAREER_REPORT_ENABLED=true` (backup `.env.production.bak-pre-career-enable`), backend и worker пересозданы.
- Runtime readback: api `CAREER_REPORT_ENABLED=True`, `LLM_PROVIDER=deepseek`; worker `CAREER_REPORT_ENABLED=True`; `LLM_MODEL=deepseek-v4-flash`.
- Singleton scheduler отправляет `career.monitor_pipeline` каждые 5 минут (4 отправки за 20 минут наблюдения); `KeyError`/`Traceback` в worker за окно — `0`.
- Public smoke: `/api/v1/health` `200`, `/` `200`, `/products/career` `200`.
- Аудитория включения — только активный Plus: `self` active `5`, grandfathered `career` `0`.
- Career-таблицы production пусты до первой генерации; `career_interpretation_facts`/`career_role_matches` создаются генерацией, сидирование не требуется.
- Границы подтверждения: real-provider canary cost/latency в production не измерены — `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` не задан, метрики не экспортируются; production report/PDF ID живого пользователя пока не записаны. Поэтому критерии `Canary cohort/result...` и `Production smoke report/PDF IDs...` остаются открытыми.

## Production defects and fixes 2026-09-30 → 10-01

Три дефекта обнаружены при первой живой генерации на реальном provider после включения Career. Все три закрыты отдельными коммитами, каждый со regression-тестом, гейтами на чистом worktree и проверкой внутри развёрнутого образа.

### 1. Evidence collide внутри одной размерности — `e0aa84c`

- Симптом: `IntegrityError UniqueViolationError` на `uq_career_dimension_evidence_source`, обе генерации упали, `career_reports` пуст.
- Корень: `FACTOR_RULES` матчатся подстрокой, поэтому факт `placement:saturn:capricorn:house_2` матчил сразу два правила одной размерности (`"placement:saturn:"` вес 0.12 и `"house_2"` вес 0.08) → две строки evidence с одинаковым `(dimension_score_id, source_type, source_id)`.
- Фикс: `_merge_rule_matches` агрегирует совпавшие по факту правила в одну строку (веса суммируются, скор и confidence не меняются).
- Evidence: RED-тест падал 38/37 и 10/8; golden-снимок изменил только счётчик evidence `people_orientation` 4→3 при неизменных score 68.0 / confidence 1.0; реплей на реальных 104 фактах прод-карты — 3 коллизии до фикса (88→85 строк, включая `source_id=6b1bb5b1…` из прод-лога) и 0 после.

### 2. Ответ живого provider не проходил контракт секции — `b448b61`

- Симптом: все 10 секций `career_provider_failure`, отчёт `narrative_failed`, при этом 10× `200 OK` от `api.deepseek.com` и пустой `output_payload` у секции.
- Диагностика: реплей внутри прод-контейнера на сохранённом `input_payload`. Модель возвращала валидный JSON, но с другими именами полей: `section_title` вместо `title`, `claims[].claim` вместо `claims[].text`, одиночный `fact_key` вместо `fact_keys`, без `cited_fact_keys`. Схема объявлена `extra="forbid"`, поэтому каждый ответ отвергался; исключение провайдера проглатывалось в `career_provider_failure` с пустым payload — отсюда «тишина» в логах.
- Корень: промпт требовал «JSON matching career_segment_output_v2», не перечисляя полей.
- Фикс: промпт перечисляет точный контракт (`career-segment-prompt-3`); провайдер нормализует живой дрейф имён на каноническую схему; падение провайдера пишет безопасную диагностику (`error_code`, `error_type`, детали без прозы модели).
- Evidence: RED на коде без фикса (та же ошибка схемы, что в проде); живой реплей после фикса — сырой ответ содержит `title`/`cited_fact_keys`/`claims[].text`/`claims[].fact_keys` и валидируется **без** нормализации (10 claims, 12 cited); 597 unit-тестов; CI `36776789117` и `Build & Push Images` `36776789507` — success.

### 3. Секция губилась без повтора — `4bd31a4`

- Симптом: после фикса №2 генерация `a552e1c4-045c-4412-9909-a6741e2c1681` (отчёт `65c46588-c7b0-4088-a45c-acbf0f99a6de`) дошла до 8/10 секций и осталась в `generating_sections`; две секции — `professional_summary` и `leadership_and_influence` — `career_validation_failure`.
- Диагностика: 3 живых прогона каждой упавшей секции. `leadership_and_influence` — 3/3 pass; `professional_summary` — 2/3 pass, одно падение по правилу `career overclaim` (в теле встречается `гарантирует`). То есть вердикт гейта зависит от конкретного ответа, а пайплайн спрашивал секцию ровно один раз.
- Фикс: пайплайн переспрашивает секцию, если её вердикт — `career_provider_failure` или `career_validation_failure` (до 2 попыток, персистится только финальная строка); в промпт добавлен явный список запрещённых формулировок (`career-segment-prompt-4`). Гейты не ослаблены.
- Evidence: 601 unit-тест, включая два новых теста пайплайна (переспрос при провале гейта и отсутствие переспроса при другой причине); живая генерация `ffac0556-ac76-4083-ba3b-3c5890596b3f` → отчёт `2b7e4d6f-6ff5-439c-9422-f9ef500d9e8e` со статусом `ready` и 10/10 секций `ready` на `career-segment-prompt-4`.

### Что остаётся открытым после этих фиксов

- Повторный прогон **той же** генерации не идемпотентен: детерминированная стадия вставляет `career_dimension_scores` заново и падает на `uq_career_dimension_scores_generation_dimension`. Первичной генерации это не мешает (каждое действие пользователя создаёт новую), но ломает ручной повтор и возможный редиспат beat-монитором.
- Строки `14fa7536-4400-4856-88d0-232f1922532b` и `a552e1c4-045c-4412-9909-a6741e2c1681` остаются в нетерминальных статусах (`failed`, `generating_sections`) как след ретраев; продовые данные при диагностике не удалялись.
- Canary cost/latency и production report/PDF ID живого пользователя по-прежнему не подтверждены (OTLP endpoint в production не задан).
