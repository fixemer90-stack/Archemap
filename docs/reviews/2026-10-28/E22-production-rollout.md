# E22 — production release

Дата: 2026-10-28 (+03:00).
Статус: DEPLOYED — глобальный production release, не процентный canary. Полная приёмка E22 не подменяется фактом выкладки.

## Разрешение и явное исключение

Владелец разрешил production («ну значит поехали на прод»), затем явно изменил budget STOP для этой выкладки: «выкладывай, лимиты решим потом». Исключение записано до переключения в private `owner-approval.json`. Численные latency/cost/stuck-job budgets не считаются утверждёнными или измеренными. Дополнительные платные тестовые генерации не запускались. Действующий реальный DeepSeek сохранён; production не переведён на mock.

## Release identity

- Предыдущий production marker: `9a7ca747fdd5acd26aab19de9e8a5bd83324a727`; три deployed source hashes совпали с ним.
- Новый source/image revision: `886910321d1efcb189b8a2296dd5c947146e8b4f`, exact CI `40568791382` — 8/8 success.
- Образы собраны off-host из `git archive`, не из dirty checkout; OCI revision, export manifest/checksums и фактические running image IDs проверены. Baked frontend refinement flag сохранён `true`.
- Активный release directory: `/opt/astrotype-production/releases/886910321d1efcb189b8a2296dd5c947146e8b4f`.
- После native smoke `.deploy-sha` записан и прочитан как новый SHA; `.deploy-release` записан и прочитан как active directory. Старый `/opt/astrotype` не является новым application checkout: он сохранён как прежний operator/source/ingress root, включая неизменённый Caddy bind.
- API, worker, scheduler и refinement-monitor: `CHILD_REPORT_ENABLED=true`, `APP_ENV=production`, реальный `deepseek` / `deepseek-v4-flash`. Python source identity проверена во всех четырёх consumers: 270 файлов в каждом.
- Backend, worker, scheduler, refinement-monitor и frontend пересозданы совместно по явному project `astrotype`; PostgreSQL, Redis, Caddy и staging не пересоздавались.

## Выполненные safety gates

- [x] Production baseline: healthy API, 49 public tables, ноль Child tables, revision `f1a2b3c4d5e6`; состояние/volumes/images сохранены приватно.
- [x] Native operational readiness исходных worker/refinement-monitor/scheduler проверена до переключения.
- [x] Краткий production-only maintenance через host-matched JSON route Caddy; staging virtual host не менялся. Scheduler остановлен, активные/reserved/scheduled jobs drained, writers остановлены до snapshot/backup.
- [x] Свежий private custom dump: 49 tables / 40 nonempty. Восстановление в уникальную disposable DB доказало schema/row equality и неизменность источника. Только созданная этим запуском DB с matching OID/owner/marker удалена; удаление прочитано обратно. Dump/checksum/evidence сохранены, application DB не восстанавливалась поверх данных.
- [x] Семь миграций `f1a2b3c4d5e6` → `a8b9c0d1e2f3` применены с Child flag off. Exact revision, фактический backend image и migration-file hashes проверены до включения.
- [x] Все 48 non-revision legacy tables сохранили данные; ни одна preexisting table не исчезла. Сравнение выполнено только при frozen writers, не после возврата живого трафика.
- [x] Новые consumers прошли operational readiness: backend health, frontend `/login` HTTP 200, exact-node Celery ping/queues/Child registry, beat PID/log/broker readiness. Защита применяется и к rollback.
- [x] Caddy original JSON config восстановлен и сопоставлен; maintenance снят, public HTTPS health 200.
- [x] Native desktop/mobile browser без API mocks: активный Child в меню, карточка «Ребёнок» больше не coming-soon, реальный sidebar click открывает Child, overflow/page errors отсутствуют.
- [x] Использован один новый synthetic Free adult: без child records, profiles, purchases, payment rows и paid grants; native children API даёт ожидаемый 402, форма создания не раскрывается, карточка показывает Plus CTA. Реальные customer accounts не изменялись этой fixture.
- [x] Финальный readback подтвердил runtime/markers, 15 Child API routes, source/provider flags, retained backup checksum, отсутствие disposable restore DB и сохранение 17 прочих container identities/staging markers.

## Production monitoring

Созданы отдельные private `otel-collector-prod`, `prometheus-child-prod`, `alertmanager-child-prod` только в `astrotype_default`, без опубликованных портов, nonroot/read-only/cap-drop. Конфигурация collector metrics-only без debug/traces; production-only state volumes, отдельный probe directory. Существующие Telegram secrets подключены только per-file read-only; значения не печатались и не копировались в app environment.

Native collector validation, Prometheus config + rule cases, amtool и Compose прошли. Две Child rules сохраняют исходные expressions/for durations с production labels и privacy-safe receiver allowlist. Реальный Prometheus → Alertmanager → Telegram probe наблюдал pending → firing после 60.325767 секунды → inactive, завершил firing/resolved: 2 notifications/completed/requests, 0 failures. Probe удалён, отсутствие прочитано обратно. Это alert-delivery proof, не измерение provider latency/cost.

Ошибки verifier до application rollout: promtool directory mount был недоступен nonroot из-за private umask; runtime/probe directories исправлены до 0755, configs до 0644. Promtool rule tests потребовали tmpfs для `/tmp` при read-only root. Первый runtime health verifier ошибочно ожидал несуществующий collector health extension; проверен фактически настроенный metrics listener, сервисы не пересоздавались для исправления проверки. Application/staging identities не изменились во время этих действий.

## Независимые reviews и rollback

- `deleg_f131d25e`: production compatibility одобрена для исходного нулевого Child schema. Все seven upgrades затрагивают Child tables/functions; это не общее разрешение для произвольной populated intermediate Child schema.
- `deleg_0bda5ba2` нашёл три safety defects приватной процедуры: отсутствие exact migration gate перед enable, frozen comparison после возобновления writers, readiness только по `Running`. Все исправлены до application mutation.
- `deleg_ab79d33c`: re-review passed, security/logic findings пусты; 13 offline guard checks и дополнительные ordering/readiness probes PASS.
- Private data helper: 15 offline tests PASS; native backup/restore выполнен отдельно и записан как live proof.

Rollback сохраняет expanded schema и artifacts, не делает downgrade/restore поверх application DB. Предыдущие образы сохранены; old backend должен запускаться с явным skip-Alembic command override, потому что старая версия не знает новый revision. Native rollback этого production release не запускался: после успешного переключения не имитировалась авария и не прерывались customer jobs.

## Операционная точка входа

Дальнейшие команды должны использовать active release, а не старый compose в `/opt/astrotype`:

```sh
RELEASE_DIR="$(cat /opt/astrotype/.deploy-release)"
EVIDENCE_DIR="/opt/astrotype-production/evidence/$(cat /opt/astrotype/.deploy-sha)"
docker compose -p astrotype --project-directory "$RELEASE_DIR" \
  --env-file "$RELEASE_DIR/.env.production" \
  -f "$RELEASE_DIR/docker-compose.prod.yml" \
  -f "$EVIDENCE_DIR/observability/compose.observability.json" \
  -f "$EVIDENCE_DIR/observability/app.telemetry.json" \
  -f "$EVIDENCE_DIR/images.override.json" ps
```

Private proof directory: `/opt/astrotype-production/evidence/886910321d1efcb189b8a2296dd5c947146e8b4f/`. В нём `owner-approval.json`, actual CI/image/source manifests, preflight, fresh dump/restore/cleanup proofs, frozen migration proof, runtime result, native browser result, production alert proof и `production-proof.json`. Не публиковать dump, credentials, полные manifests/data или tokens.

## Что не закрыто этим релизом

S15 budgets и проверка качества/стоимости реальной новой LLM-генерации не выполнены. Полное независимое исполнение S16 runbook новым оператором и формальная полнота всего acceptance остаются отдельными пунктами. Production release не выдаётся за canary, новый paid generation или полное закрытие E22.

Связано: [S15](../../features/E22-child-report/S15-qa-observability-data-safety.md), [S16](../../features/E22-child-report/S16-rollout-runbook-live-evidence.md), [runbook](../../deployment/child-report-rollout.md).
