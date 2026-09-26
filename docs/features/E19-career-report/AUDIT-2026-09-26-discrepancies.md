# E19 Career Report — аудит расхождений 2026-09-26

## Назначение

Документ консолидирует расхождения между acceptance criteria E19, текущей реализацией, автоматизированными проверками и live runtime. Он является рабочим списком закрытия Feature и не заменяет критерии в `FEATURE.md` и Story-файлах.

## Проверенная база

- Код и документация: `a821404d0b010fc9f1f1cd04d01170a825dc29b8`.
- Exact-HEAD CI: run `36210137484`, семь jobs завершены `success`.
- Документационный аудит: commit `1d8d49752eaaff3681caae2cf0cb68f6f798c940`, CI run `36226763083`, семь jobs завершены `success`.
- Live stage marker на момент аудита: `3462865ed1a7158023c99bc491044dcea048ad23`.
- Production проверялась только на regression health; Career rollout в production не выполнялся.

## Сводный статус

Полностью закрыты по текущему evidence:

- S03 — factor/dimension engine;
- S04 — questionnaire/resolver domain;
- S05 — archetypes/environment;
- S06 — role matching/career paths;
- S13 — готовность документа rollout/rollback runbook, но не его live-исполнение.

Остаются частично закрытыми:

- S01, S02, S07, S08, S09 — implementation/test contract gaps;
- S10, S11 — client/live/parity evidence gaps;
- S12, S14 — stage, observability, canary и production evidence.

## 1. Implementation и test-contract gaps

| Story   | Расхождение                                                                                                                                                                            | Влияние                                                                                           | Что должно закрыть пункт                                                                                                             |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| S01     | `CAREER_ACCESS_MATRIX` проверяется как декларативная константа, но не сопоставляется со всеми зарегистрированными routes. В матрице есть `versions`, отдельного versions endpoint нет. | Нельзя утверждать, что access policy полностью покрывает заявленную API surface.                  | Параметризованный route-level test всех Career операций и явное решение по versions API.                                             |
| S02     | Dimension, archetype, environment, resolution и role rows имеют unique keys относительно `career_profile_id`, но не полного generation/report lineage.                                 | Повторный полный пересчёт может получить unique conflict вместо immutable новой версии.           | Version-aware schema/repository contract и regression повторной генерации без overwrite/conflict.                                    |
| S02     | Idempotency доказана для последовательного retry, но не для конкурентного create/regenerate.                                                                                           | Два одновременных запроса могут столкнуться между check и insert и завершиться `IntegrityError`.  | Конкурентный PostgreSQL integration test и atomic conflict handling/readback.                                                        |
| S07     | Roles, paths и contradictions не всегда содержат конкретные evidence source IDs; используется fallback `chart:{id}`.                                                                   | Provenance части выводов недостаточно точен для заявленного evidence-backed контракта.            | Явные evidence refs для каждого публикуемого вывода и negative tests на fallback там, где он запрещён.                               |
| S07     | Low-confidence marker передаётся в prompt, но output validator не проверяет условность итоговой формулировки.                                                                          | Модель может вернуть категоричный текст при низкой confidence.                                    | Output quality gate и RED/GREEN fixtures для conditional language.                                                                   |
| S07     | Citation contradiction key не доказывает, что смысл contradiction сохранён в body.                                                                                                     | Формально валидная секция может потерять значимое противоречие.                                   | Semantic contradiction-retention regression либо ограниченный deterministic phrase contract.                                         |
| S08     | Duplicate validator реализован, но отдельный RED/GREEN regression дублирующихся секций не найден.                                                                                      | Критерий полного набора narrative validators преждевременно считался закрытым.                    | Отдельный rejection test для semantic/structural duplication.                                                                        |
| S09     | FastAPI-generated schema содержит Career API, но канонический `contracts/openapi.yaml` не содержит `/career/*`.                                                                        | CI-канонический контракт и фактический API расходятся; generated clients не имеют Career surface. | Обновлённый canonical OpenAPI и contract validation в CI.                                                                            |
| S09     | Нет одной параметризованной проверки ownership/access для каждого Career route.                                                                                                        | Общий dependency виден в source, но полнота policy surface не доказана автоматически.             | Route matrix test для questionnaire/create/status/read/sections/regenerate/PDF и будущих versions routes.                            |
| S09     | Free/expired access и locked lifecycle частично проверяются через подменённый denial.                                                                                                  | Реальный entitlement lifecycle на Career routes покрыт не полностью.                              | Integration fixtures active Plus, grandfathered, expired/free/locked без monkeypatched policy result.                                |
| S09     | Нет конкурентного idempotency test и отдельного terminal generation `failed` API case.                                                                                                 | Не закрыты race safety и полный lifecycle contract.                                               | DB-backed concurrent test и terminal-failed response regression.                                                                     |
| S11     | Web и backend PDF имеют отдельные view-model/rendering paths.                                                                                                                          | Один persisted payload не гарантирует одинаковый порядок и представление данных.                  | Cross-render fixture test из одного payload с сопоставлением section order, labels, contradictions и context.                        |
| S11     | Playwright snapshots сравнивают reader с собственными baselines, а не с canonical sample.                                                                                              | Заявленная visual parity относительно sample невоспроизводима.                                    | Зафиксированный sample-comparison protocol: image diff с допуском либо документированный human-review checklist и evidence artifact. |
| S12/S13 | `career.monitor_pipeline` объявлен в Celery schedule, но local/staging/production Compose запускают только worker без Beat.                                                            | Stuck/validator monitor task фактически не запускается в deploy runtime.                          | Отдельный scheduler service или approved scheduler, readiness и управляемый alert-path smoke.                                        |

## 2. Live и rollout evidence gaps

### S10 — questionnaire/product UX

Автоматизированный Chromium suite committed и зелёный, но все Career API calls в browser tests mocked. Остаётся доказать через deployed backend:

- active Plus questionnaire flow;
- grandfathered legacy entitlement;
- expired/free/locked denial без protected payload;
- persisted draft reload/resume;
- idempotent completion против реальной PostgreSQL state.

### S11 — reader/PDF

До полного закрытия требуются:

- cross-render web/PDF parity из одного persisted report;
- browser cases `deterministic_ready` и `narrative_failed`;
- воспроизводимое сравнение reader с canonical sample;
- отдельная проверка сохранения contradictions и context constraints в обоих renderer paths.

### S12 — QA/observability/rollout

Открыты:

- real-provider Career report и human quality review;
- работающий scheduler, metrics/alerts и zero-stuck observation window;
- staging latency/token/cost measurements и dashboard references;
- canary cohort, результаты и полный observation window;
- targeted regression/live proof читаемости legacy Career reader/PDF после target migrations;
- production Career report/PDF IDs.

### S14 — stage publication

На момент аудита stage не соответствует target revision:

- stage marker `3462865ed1a7158023c99bc491044dcea048ad23` не совпадает с target SHA;
- stage backend healthy, migration current/head `a6b7c8d9e0f1`, но `/api/v1/career/*` routes отсутствуют;
- `CAREER_REPORT_ENABLED=true`, при этом `LLM_ENABLED=false`, `LLM_PROVIDER=mock`;
- OTLP endpoint пуст;
- DB readback: `career_generations=2`, `career_reports=0`, `career_questionnaire_sessions=1`;
- Career preflight dump, restore proof и pre/post checksums не найдены;
- без Basic Auth stage health возвращает `401` и `X-Robots-Tag: noindex, nofollow, noarchive`;
- authenticated Basic Auth `200` не подтверждён;
- full questionnaire → deterministic → narrative → reader/PDF flow не выполнен;
- entitlement matrix, human review, dashboards, rollback rehearsal и production regression после target stage publication отсутствуют.

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

1. Закрыть storage/versioning и concurrent idempotency gaps S02.
2. Синхронизировать canonical OpenAPI и route-level access matrix S01/S09.
3. Усилить provenance, conditional wording, contradiction и duplication quality gates S07/S08.
4. Добавить cross-render web/PDF parity и canonical sample evidence S11.
5. Добавить Celery Beat/approved scheduler в deploy topology и проверить alert path.
6. Получить новый exact green SHA после исправлений.
7. Выполнить S14: backup/checksums → exact stage deploy → routes/settings/readiness → entitlement matrix → full real-provider flow → quality/metrics → rollback rehearsal.
8. Выполнить S12 canary и production report/PDF smoke.

## 5. Правило закрытия

Критерий отмечается `[x]` только после появления проверяемого evidence требуемого уровня:

- source/unit evidence не заменяет integration race/access proof;
- mocked browser flow не заменяет live entitlement/backend smoke;
- объявленный schedule не заменяет работающий scheduler;
- persisted payload не заменяет web/PDF cross-render parity;
- stage feature flag не заменяет exact revision, routes, provider, telemetry и completed report artifact;
- green local test не считается exact-SHA CI evidence до commit/push и завершения всех обязательных jobs.
