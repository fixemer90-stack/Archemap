# E19 Career Report — аудит расхождений 2026-09-26

## Назначение

Документ консолидирует расхождения между acceptance criteria E19, текущей реализацией, автоматизированными проверками и live runtime. Он является рабочим списком закрытия Feature и не заменяет критерии в `FEATURE.md` и Story-файлах.

## Проверенная база

- Exact stage revision: `4c1423ccd10a9b4d1cf9a95fac5885dbde75e73a`.
- Exact-HEAD CI: run `36510730869`, семь jobs завершены `success`.
- Stage marker прочитан обратно из runtime и совпадает с exact revision.
- Stage migration current/head: `b7c8d9e0f1a2`.
- Production после stage publication проверена только на non-regression: API health и frontend вернули HTTP `200`; Career rollout в production не выполнялся.
- Обновление 2026-09-30: в production выкачен релиз `7fc40de9822f15691ff44d7c2c3ac02c3a07213a` и Career включён (`CAREER_REPORT_ENABLED=true`); runtime-проверки и границы подтверждения — в разделе 2.

## Сводный статус

Полностью закрыты по текущему локальному evidence:

- S03 — factor/dimension engine;
- S04 — questionnaire/resolver domain;
- S05 — archetypes/environment;
- S06 — role matching/career paths;
- S01 — executable route/access matrix и versions API;
- S02 — generation-aware immutable history и concurrency guards;
- S07 — precise provenance, low-confidence и contradiction gates;
- S08 — duplicate/near-duplicate regressions и active worker wiring;
- S09 — canonical OpenAPI, entitlement matrix и lifecycle/concurrency API tests;
- S10 — questionnaire/product UX, active `self` и grandfathered `career` live Chromium flow;
- S11 — shared web/PDF presentation contract и exact-SHA Chromium sample evidence;
- S13 — готовность документа rollout/rollback runbook, но не его live-исполнение.

Остаются частично закрытыми:

- S12 — legacy readability, canary и production evidence;

S14 полностью закрыта: stage publication, live browser/entitlement matrix, dashboard, zero-stuck и rollback evidence записаны.

Все implementation/test-contract расхождения раздела 1 закрыты commits текущей серии. Таблица ниже сохранена как исторический перечень причин изменений; актуальные открытые gaps перечислены в разделах 2 и 4.

## 1. Закрытые implementation и test-contract gaps

| Story   | Расхождение                                                                                                                                                                            | Влияние                                                                                                                                       | Что должно закрыть пункт                                                                                                             |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| S01     | `CAREER_ACCESS_MATRIX` проверяется как декларативная константа, но не сопоставляется со всеми зарегистрированными routes. В матрице есть `versions`, отдельного versions endpoint нет. | Нельзя утверждать, что access policy полностью покрывает заявленную API surface.                                                              | Параметризованный route-level test всех Career операций и явное решение по versions API.                                             |
| S02     | Dimension, archetype, environment, resolution и role rows имеют unique keys относительно `career_profile_id`, но не полного generation/report lineage.                                 | Повторный полный пересчёт может получить unique conflict вместо immutable новой версии.                                                       | Version-aware schema/repository contract и regression повторной генерации без overwrite/conflict.                                    |
| S02     | Idempotency доказана для последовательного retry, но не для конкурентного create/regenerate.                                                                                           | Два одновременных запроса могут столкнуться между check и insert и завершиться `IntegrityError`.                                              | Конкурентный PostgreSQL integration test и atomic conflict handling/readback.                                                        |
| S07     | Roles, paths и contradictions не всегда содержат конкретные evidence source IDs; используется fallback `chart:{id}`.                                                                   | Provenance части выводов недостаточно точен для заявленного evidence-backed контракта.                                                        | Явные evidence refs для каждого публикуемого вывода и negative tests на fallback там, где он запрещён.                               |
| S07     | Low-confidence marker передаётся в prompt, но output validator не проверяет условность итоговой формулировки.                                                                          | Модель может вернуть категоричный текст при низкой confidence.                                                                                | Output quality gate и RED/GREEN fixtures для conditional language.                                                                   |
| S07     | Citation contradiction key не доказывает, что смысл contradiction сохранён в body.                                                                                                     | Формально валидная секция может потерять значимое противоречие.                                                                               | Semantic contradiction-retention regression либо ограниченный deterministic phrase contract.                                         |
| S08     | Duplicate validator реализован, но отдельный RED/GREEN regression дублирующихся секций не найден.                                                                                      | Критерий полного набора narrative validators преждевременно считался закрытым.                                                                | Отдельный rejection test для semantic/structural duplication.                                                                        |
| S09     | FastAPI-generated schema содержит Career API, но канонический `contracts/openapi.yaml` не содержит `/career/*`.                                                                        | CI-канонический контракт и фактический API расходятся; generated clients не имеют Career surface.                                             | Обновлённый canonical OpenAPI и contract validation в CI.                                                                            |
| S09     | Нет одной параметризованной проверки ownership/access для каждого Career route.                                                                                                        | Общий dependency виден в source, но полнота policy surface не доказана автоматически.                                                         | Route matrix test для questionnaire/create/status/read/sections/regenerate/PDF и будущих versions routes.                            |
| S09     | Free/expired access и locked lifecycle частично проверяются через подменённый denial.                                                                                                  | Реальный entitlement lifecycle на Career routes покрыт не полностью.                                                                          | Integration fixtures active Plus, grandfathered, expired/free/locked без monkeypatched policy result.                                |
| S09     | Нет конкурентного idempotency test и отдельного terminal generation `failed` API case.                                                                                                 | Не закрыты race safety и полный lifecycle contract.                                                                                           | DB-backed concurrent test и terminal-failed response regression.                                                                     |
| S11     | Web и backend PDF имеют отдельные view-model/rendering paths.                                                                                                                          | Один persisted payload не гарантирует одинаковый порядок и представление данных.                                                              | Cross-render fixture test из одного payload с сопоставлением section order, labels, contradictions и context.                        |
| S11     | Playwright snapshots сравнивают reader с собственными baselines, а не с canonical sample.                                                                                              | Заявленная visual parity относительно sample невоспроизводима.                                                                                | Зафиксированный sample-comparison protocol: image diff с допуском либо документированный human-review checklist и evidence artifact. |
| S12/S13 | `career.monitor_pipeline` объявлен в Celery schedule, но local/staging/production Compose запускают только worker без Beat.                                                            | Stuck/validator monitor task фактически не запускается в deploy runtime.                                                                      | Отдельный scheduler service или approved scheduler, readiness и управляемый alert-path smoke.                                        |
| S10     | Career product page сопоставляла любой `404` от `GET /career/questionnaires/current` с отсутствием натальной карты.                                                                    | На production с `CAREER_REPORT_ENABLED=false` каждый пользователь получал инструкцию «постройте основной отчёт», которая не открывает Career. | Разделить причины `404` по detail и закрепить copy-контракт статической UX-проверкой.                                                |

## 2. Live и rollout evidence gaps

### S10 — questionnaire/product UX

Story закрыта. Через deployed backend доказаны active Plus flow, grandfathered Career entitlement, locked/expired denial без protected payload и idempotent create против реальной PostgreSQL state.

Live Chromium evidence 2026-09-28:

- active `self`: page `200`, create `202`, generation `58673ea9-08ee-40e5-93d9-3d887d194e11`, reader report `241306e3-d334-4fdb-87a4-ce816d88f71f` HTTP `200`, PDF `200` / `32760` bytes / `%PDF`;
- grandfathered `career`: page `200`, create `202`, generation `08d6b11c-2fc7-44bf-b1c0-928ca21c3674`, reader report `b3de9e3e-6831-4964-b1f8-42c9b04af3c0` HTTP `200`, PDF `200` / `32617` bytes / `%PDF`;
- failed Career/API responses и page errors отсутствовали.

### S11 — reader/PDF

До полного закрытия требуются:

- общий web/PDF presentation contract, deterministic/narrative-failed cases и semantic fixture parity реализованы;
- contradictions/context constraints сопоставляются одним manifest;
- exact SHA `3fbd11948a9676d440915cd5abcd50dbbf7aa3c5` прошёл CI run `36285160532` с desktop/mobile Chromium sample evidence.

### S12 — QA/observability/rollout

На stage закрыты mock-provider report, structural human review, работающий scheduler, OTLP export и zero-stuck observation window. За окно наблюдения выполнены четыре запуска `career.monitor_pipeline`: stuck deterministic `0`, stuck narrative `0`, validator failures `0`, alerts `[]`; collector принял 16 Career metric batches.

Открыты:

- canary cohort, real-provider quality/cost evidence и полный observation window;
- targeted regression/live proof читаемости legacy Career reader/PDF после target migrations: на stage нет legacy report rows;
- production Career report/PDF IDs.

### S12 — production enablement 2026-09-30

Career включён в production на revision `7fc40de9822f15691ff44d7c2c3ac02c3a07213a` — той же, что и на stage.

- `.env.production` переведён в `CAREER_REPORT_ENABLED=true`, backup сохранён как `.env.production.bak-pre-career-enable`; backend и worker пересозданы.
- Runtime читает флаг включённым в обоих процессах: api `CAREER_REPORT_ENABLED=True LLM_PROVIDER=deepseek`, worker `CAREER_REPORT_ENABLED=True`.
- `LLM_ENABLED=true`, `LLM_PROVIDER=deepseek`, `LLM_MODEL=deepseek-v4-flash` — production-генерация идёт на реальный provider, а не на mock.
- Singleton scheduler запущен; за 20 минут наблюдения `career.monitor_pipeline` отправлен 4 раза (период 5 минут), `KeyError`/`Traceback` в worker за окно — `0`.
- Public smoke: `https://astrotype.ru/api/v1/health` `200`, `/` `200`, `/products/career` `200`.
- Career-таблицы production до включения пусты (`career_generations`, `career_profiles`, `career_questionnaire_sessions`, `career_reports`, `career_interpretation_facts`, `career_role_matches` — `0`). `career_interpretation_facts` и `career_role_matches` являются per-generation артефактами, поэтому обязательного сидирования нет.
- Доступ: активных `self` (Plus) — `5`, grandfathered `career` — `0`, то есть фактическая аудитория включения ограничена Plus-подписчиками.

Вместе с включением закрыт ранее зафиксированный gap «`career.monitor_pipeline` объявлен в schedule, но Compose запускает только worker без Beat»: singleton scheduler входит в deploy-path и production, и stage.

Остаются открытыми (границы подтверждения):

- production report/PDF ID: end-to-end генерация живым пользователем после включения не выполнялась;
- canary cost/latency: `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` в production не задан, поэтому Career-метрики (duration, tokens, cost) в production не экспортируются — сравнение outcomes/latency/cost возможно только по БД и логам scheduler (`career_pipeline_alert`).

### S14 — stage publication

На stage опубликован exact SHA `20dcfbfce5ed1e2cb540261e4a1223683b89d7a7`; marker прочитан обратно. Backend, worker, singleton scheduler, frontend и OTEL collector запущены. Runtime использует `CAREER_REPORT_ENABLED=true`, `LLM_ENABLED=true`, `LLM_PROVIDER=mock`; в live OpenAPI присутствуют все 10 Career routes.

Собрано evidence:

- backup `/opt/astrotype/backups/career-preflight-20260927T022749Z.dump`, `291542` bytes, SHA-256 `1c3ef7d540927a313475d55e708722f1ac77c4428477381b1ac38ca4fd710e49`, restore в отдельную БД успешен;
- pre/post protected-table counts/checksums совпали: profiles `6`, legacy reports `0`, payments `1`, entitlements `1`;
- generation `d98e0b57-b67c-4b1b-8f8b-54c87b4eef4e`, report `c84bfae8-6ed3-4a92-b841-733cbf0c59fb`, version `6`, `10/10` sections ready;
- PDF `32760` bytes, SHA-256 `1e48f17ba7e7475a3e4e261fecbe7d24aaa3760ec6de3fd05f18fc1d6b8e4c0d`;
- generation duration `1.892 s`, estimated mock usage `23066` input / `9063` output tokens, configured cost `$0`;
- active Plus и grandfathered Career access разрешены; повторный create с тем же idempotency key вернул тот же generation;
- locked matrix для create/generation/read/sections/regenerate/PDF вернула `402` без protected payload;
- rollback rehearsal: при `CAREER_REPORT_ENABLED=false` новый create вернул `404`, существующий report остался доступен с `200`, counts `7/4/40/0` не изменились; flag возвращён в `true`;
- без Basic Auth stage health вернул `401`, с Basic Auth — `200`, `X-Robots-Tag: noindex, nofollow, noarchive` присутствует;
- production API health и frontend после stage publication вернули `200`.

Expired matrix повторена корректно: все активные grants `self`, `plus`, `career` временно истекли; create/generation/read/sections/regenerate/PDF вернули `402` без protected payload, после чего исходные entitlement восстановлены. Active `self` и grandfathered `career` также прошли полный публичный Chromium flow.

Dashboard gap закрыт 29 сентября 2026 года revision `4c1423ccd10a9b4d1cf9a95fac5885dbde75e73a` (CI `36510730869`, 7/7 success). Basic Auth boundary вернул `401/308/401` для unauthenticated root/authenticated root/unauthenticated dashboard; authenticated targets вернул `200`. Prometheus target `otel-collector:9464` — `up`; доступны operation, duration, token и cost series. Production API health/frontend после изменения остались `200`.

## 3. Исправленный documentation drift

В ходе аудита документация синхронизирована:

- S14 переведена из `⬜ Не начато` в `🟡 В работе`;
- exact green browser-smoke revision отмечен выполненным в S12 и S14;
- S01, S02, S07, S08, S09 и S11 возвращены в `🟡` из-за неподтверждённых или отсутствующих контрактов;
- верхнеуровневые Feature criteria по history, access matrix, quality gates и web/PDF parity снова открыты;
- в S12 добавлены отдельные gates для legacy readability и canary evidence;
- в S13 добавлены acceptance criteria готовности самого runbook;
- SRS status синхронизирован с актуальной Story topology.

## 4. Порядок закрытия

1. Получить legacy Career fixture либо отдельное regression evidence читаемости старого reader/PDF после target migrations.
2. Выполнить S12 real-provider canary и production report/PDF smoke.

## 5. Правило закрытия

Критерий отмечается `[x]` только после появления проверяемого evidence требуемого уровня:

- source/unit evidence не заменяет integration race/access proof;
- mocked browser flow не заменяет live entitlement/backend smoke;
- объявленный schedule не заменяет работающий scheduler;
- persisted payload не заменяет web/PDF cross-render parity;
- stage feature flag не заменяет exact revision, routes, provider, telemetry и completed report artifact;
- green local test не считается exact-SHA CI evidence до commit/push и завершения всех обязательных jobs.

## 6. Что остаётся открытым после stage publication 2026-09-27

- Staging содержит `0` legacy report rows, поэтому live readability старого Career reader/PDF проверить не на чем.
- Отдельный synthetic alert-trigger test не выполнен; штатный scheduler/monitor, OTLP export и zero-stuck path подтверждены.
- Canary и production Career report/PDF rollout не выполнялись; production проверялась только на non-regression health/frontend.
- Production Career rollout выполнен 2026-09-30: флаг включён, runtime и scheduler подтверждены. Открыто: report/PDF ID живого пользователя и canary cost/latency (на production не задан OTLP endpoint).
- Career product page больше не трактует выключенный Career как отсутствие натальной карты: причины `404` разведены по detail, copy закреплён статической UX-проверкой.
