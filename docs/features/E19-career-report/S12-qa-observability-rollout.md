# S12: QA, observability, migration и rollout

## Статус

🟡 Реализовано локально — quality/observability/rollout contract закрыт; staging real-provider, canary и production evidence остаются открытыми

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
3. Staging с mock provider, затем real provider.
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

Операторский порядок, бюджеты, метрики, backup/checksum preflight, staging matrix и rollback: [`S12-rollout-runbook.md`](S13-rollout-runbook.md).

## Реализация

- Полный Career unit suite покрывает golden dimensions, missing houses, low confidence, contradictions, manager/expert leader/entrepreneur divergence, catalogs, schema/prompt validation, anti-generic/duplication/overclaim/diagnosis/profession gates и web/PDF contract.
- DB-backed integration suite проверяет durable lifecycle, progressive deterministic-first read, partial failure, ownership-bound read, idempotent create и отсутствие protected payload в locked response.
- `app.modules.career.observability` создаёт low-cardinality OpenTelemetry metrics без ответов, prompt/report payload и UUID в labels.
- API экспортирует метрики через OTLP только при заданном `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`; без endpoint поведение явно выключено.
- Worker измеряет deterministic/narrative duration, safe failures/retries, scoring/catalog adoption и section outcomes.
- Celery beat каждые 5 минут ищет stuck generations и spike `career_validation_failure`, пишет bounded `career_pipeline_alert`.
- Provider token/cost telemetry использует явно помеченную оценку по размеру текста и настраиваемым ставкам; authoritative billing остаётся внешней сверкой провайдера.
- `CAREER_REPORT_ENABLED=False` остаётся default rollback gate; rollback не удаляет target/legacy artifacts.

## Локальное evidence

- `uv run pytest tests/unit/test_career -q` → `64 passed`.
- `uv run pytest tests/unit -q` → `526 passed`.
- isolated PostgreSQL `uv run pytest tests/integration -q` → `2 passed`.
- `node scripts/check-career-product-ux.mjs` → passed.
- `node scripts/check-career-report-reader.mjs` → passed.
- Repo-wide ruff/mypy, frontend test/type/lint/build и docs Prettier выполняются повторно после последнего edit; точный SHA записывается после commit/CI.

## Критерии приёмки

- [x] Все deterministic, resolver, role/path, LLM, API и UI suites зелёные локально.
- [ ] Staging real-provider report проходит human quality review по design-документу.
- [x] Locked/expired аккаунт не получает protected Career data в policy/API regression suites.
- [x] Grandfathered legacy владелец сохраняет policy access; production matrix остаётся в runbook.
- [x] Старые Career reports/PDF не мигрируются и остаются читаемыми по explicit migration boundary.
- [ ] Метрики/alerts доказывают отсутствие stuck pipeline.
- [ ] Cost/latency budgets зафиксированы в runbook; staging measurement ещё не записан.
- [x] Rollback feature flag покрыт contract test и не выполняет destructive migration/backfill.
- [ ] Production smoke и точный CI SHA записаны в Story перед `✅`.
