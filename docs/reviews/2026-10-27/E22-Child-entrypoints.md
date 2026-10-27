# E22 — Child entrypoint remediation

Дата: 2026-10-27.
Статус: COMPLETE для дефекта пользовательского входа; исправление опубликовано и выложено на isolated staging. Не означает полную приёмку S15/S16.

## Пользовательский дефект и причина

На staging Child нельзя было открыть обычным путём из кабинета: sidebar содержал `disabled: true`, карточка «Ребёнок» имела `coming_soon`. Прямые переходы на `/products/child` в предыдущих functional smoke не проверяли обнаружимость раздела. Предыдущее подтверждение работы страницы не являлось подтверждением пользовательского входа из меню.

Реальное воспроизведение BEFORE без API mocks: desktop 1440×1000 и mobile 390×844, gateway Basic Auth и native cookie строго синтетического staging actor. В обоих случаях sidebar имел `href="#"`, `aria-disabled="true"`, карточка — disabled «В планах». В старом billing response отсутствовало поле доступности. У этого actor нет активного paid Child access; это отдельно от дефекта скрытого входа.

## Исправление

- Backend-owned `child_enabled` в существующем billing access response отражает `CHILD_REPORT_ENABLED`, не подменяет paid entitlement и не меняет admission.
- Sidebar и карточка используют только явное `true`; false, старый backend без поля и ошибка первоначальной загрузки не открывают раздел.
- При включённом продукте и paid Child access карточка открывает Child. Без paid access карточка сохраняет CTA Plus, а меню открывает страницу с действующим backend paid gate.
- Нет нового публичного frontend env switch, изменений цен, платежей, DB schema, генерации или провайдера.

## Проверки и публикация

- [x] RED: новый browser test не находит «Открыть» на Child-карточке старого UI.
- [x] GREEN: 10 новых desktop/mobile browser cases — карточка и меню, flag-off, legacy response, failed metadata, доступность без paid entitlement; overflow assertion.
- [x] Реальный staging BEFORE без API mocks воспроизводит дефект в обоих viewport.
- [x] Backend: 3 RED→GREEN availability regressions; 31 payments/reconciliation tests, 1166 full unit tests; global Ruff/format/mypy green.
- [x] Frontend lint (2 pre-existing auth-page warnings), repo-wide Prettier, TypeScript и 15 UX contracts green.
- [x] Полный browser suite: финальный serial run — 83 PASS / 1 existing skip, без failures. Два предшествующих запуска по 82 PASS / 1 skip / 1 failure диагностированы: Next.js dev indicator, затем auth-guard readiness race. Для guard добавлено ожидание завершения, без изменения golden/tolerance; 16 entrypoint + всех theme visual cases PASS.
- [x] Независимый code review `deleg_c436318d`: passed, без security/logic findings. Необязательный unpaid sidebar click дополнительно выполнен на native staging с реальным 402. Delayed initial metadata остаётся необязательным расширением coverage; null initial access и strict `=== true` fail closed.
- [x] Опубликованы `e8229dd` (backend availability), `b7c7ff7` (entrypoints), `562de0a` (snapshot readiness). Release source `562de0a979fcb39ca1e3f662300ce0614201a84b`, exact CI `40564647794`: 8/8 jobs success. Отдельный Build & Push `40564647942` не являлся deployment proof.
- [x] Off-host build и изолированный staging rollout только API/frontend; 270 API Python source files сверены с exact archive.
- [x] Native staging AFTER desktop/mobile: `child_enabled=true`, Child виден и кликабелен в обоих меню; карточка «Ребёнок» больше не coming-soon, без paid access показывает Plus CTA. Обычный sidebar click приводит на Child, реальный children API возвращает ожидаемый 402, форма создания не раскрывается. Нет API mocks, overflow и page errors. Paid card→Child branch покрыт локальным browser test; новый paid native generation здесь не заявлен и test entitlements не изменялись.
- [x] Final readback: все 66 public tables и schema без изменений; fresh backup checksum valid; 17 остальных containers, production и deployment markers не изменились.

## Rollout identity и evidence

API/frontend source: `562de0a979fcb39ca1e3f662300ce0614201a84b`. Workers остались на `06b72c0f06c6f50a1831d407ec1350eb2f9e7bf8`, alert infra — на `40f3fb1b4aca2f39a48553689feaca893c2ceb2c`; они не перезапускались. Child core/workers/migrations не отличаются от предыдущего app release. Migration revision осталась `a8b9c0d1e2f3`.

Private evidence: `/opt/astrotype-staging/evidence/562de0a979fcb39ca1e3f662300ce0614201a84b/`: actual CI responses, image manifest/checksums, source archive, preflight, full before manifest, fresh custom-format backup + TOC/checksum proof, rollout result, native before/after JSON, `final-proof.json`. Новый independent restore не заявлен: новый backup проверен по TOC/checksum, прежнее restore evidence сохраняется отдельно.

Local private screenshots: `/home/balthier/.hermes/cache/scratch/e22-child-entrypoints-20261027/after-menu-desktop.png`, `after-menu-mobile.png`, `after-child-desktop.png`, `after-child-mobile.png`; показаны только synthetic fixture identities. Визуально проверены enabled Child в desktop/mobile меню и отсутствие coming-soon у карточки.

## Безопасность процедуры и найденные ошибки

На общем VPS недостаточно свободной RAM для безопасной сборки Next.js рядом с production. Образы фактически собраны вне VPS из `git archive` проверенного SHA с revision labels и сохранением frontend refinement flag `true`; на VPS выполнены только image load и `--no-build` recreate API/frontend. Running image IDs сверены с manifest; protected containers/markers проверены до и после.

`deleg_a4bd23e3` выявил два блокера только в приватной rollout-процедуре: отсутствие parity baked/current/Compose refinement flag и сравнения фактически запущенных/восстановленных image IDs плюс frontend readiness. Исправлены до выполнения rollout. `deleg_cb5e768c` подтвердил устранение обоих, security/logic findings пусты; 10 offline AST/handler guard probes PASS. Runtime-state helper сверяется с exact source archive перед импортом. Rollback guard tests не означают новый live rollback drill этого slice.

Первая off-host попытка через Windows Docker CLI stdin неправильно интерпретировала tar как Dockerfile; образ не был собран, staging не изменён. Исправленная успешная попытка использовала извлечённый git-archive context и Windows UNC path. Это инфраструктурная ошибка процедуры, не ошибка приложения. Оба exported image archive entries проверены до загрузки; built backend schema/service imports проверены offline с `--network none`.

## Границы

Не закрывает S15/S16, formal budgets, full independent operator execution, real-provider cost/quality или production/canary. `LLM_PROVIDER=mock`, платных provider calls не было. Accepted staging marker не продвигался.

Связанная Story: [S13](../../features/E22-child-report/S13-child-management-questionnaire-ux.md).
