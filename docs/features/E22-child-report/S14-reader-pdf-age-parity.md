# S14: Reader, dynamic age block и PDF

## Статус

✅ Завершено — [BUG-50](../../reviews/2026-10-28/BUG-50-child-content-quality.md) принят в production 2026-10-31. На `cf3a4e6` сохранён core version 5: 11 ready sections, 0 failed/missing, 4 justified omissions. Native desktop/mobile и PDF содержат все exact bodies/omission explanations, честный limited notice и pinned age metadata; private reason codes не раскрываются. Parent read-only/visual acceptance подтверждена, legacy reports сохранены. Это не закрывает весь E22/S15–S16.

Дополнительные критерии BUG-50:

- [x] Ограниченный по качеству результат не показывает безусловное «Отчёт готов».
- [x] Reader/PDF используют один backend-owned quality verdict; внутренние reason codes не выводятся пользователю.
- [x] Legacy payload без quality остаётся совместимым; нет автоматической платной регенерации.
- [x] Browser desktop/mobile, accessibility и PDF parity проверены на ограниченном и полноценном состоянии.

## Контекст

Reader должен быть narrative-first, показывать progressive deterministic result и использовать тот же persisted presentation contract, что PDF. Возрастной блок нельзя пересчитывать незаметно во время экспорта.

## Что сделать

1. Создать report reader с пятнадцатью sections и progressive states.
2. Показать confidence/technical basis через progressive disclosure, не открывая отчёт raw scores.
3. Отдельно рендерить датированный Current Age block и stale/update state.
4. Создать presentation manifest как единый источник web/PDF.
5. Фиксировать `age_snapshot_id` при PDF generation.

## Затрагиваемые файлы

| Область                                        | Действие          |
| ---------------------------------------------- | ----------------- |
| `frontend/src/app/(dashboard)/reports/child/*` | Изменить/добавить |
| `frontend/src/components/child-report/*`       | Изменить/добавить |
| `backend/app/modules/child/presentation.py`    | Изменить/добавить |
| `backend/app/modules/child/pdf.py`             | Изменить/добавить |
| `frontend/tests/*child-report*`                | Изменить/добавить |

## Критерии приёмки

- [x] Порядок и content web/PDF совпадают.
- [x] PDF содержит core/report/age version metadata.
- [x] Reader полезен в deterministic_ready/narrative_failed.
- [x] Age stale state честно датирован.
- [x] Нет fixed labels/diagnostic language в UI chrome.
- [x] Mobile, print и accessibility verification проходят.

## Verification

Текущие review findings, выполненные проверки и незакрытые gates: [единый evidence report](../../reviews/2026-10-25/E22-S12-S16.md). Операционные процедуры: [rollout/rollback runbook](../../deployment/child-report-rollout.md). Локальные PASS не закрывают staging budgets, live telemetry, deployed SHA или canary.

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Production BUG-50 readback — 2026-10-29

На source `3e3ee67` public API, native desktop 1440×1000/mobile 390×844 без mocks и PDF проверили один сохранённый core v3: 15 headings, все 11 bodies совпадают, четыре evidence-based omissions, limited notice без raw reason codes, без overflow/page errors и Child mutations. Нативные PDF-downloads обоих viewports совпали с API: 7 pages/27,348 bytes, SHA256 `1379394ce70802b331ad4f4b2083fa48dd15d949fac3e2f14650b34c671fdd53`; body parity PASS. Индивидуальные web fallback-пояснения omissions в PDF отсутствуют; в нём есть global limitation copy, headings/confidence notes. Это явная граница copy parity, не потеря сохранённых bodies.

Upstream sentence-level boilerplate сохраняется; source-aware fix не является полным содержательным принятием. [BUG-50 evidence](../../reviews/2026-10-28/BUG-50-child-content-quality.md) остаётся открытым. Исторические immutable artifacts не переписаны.

## Production BUG-50 acceptance — 2026-10-31

Exact `cf3a4e6`, CI `41133238682` (8/8), immutable core version 5: **11 ready, 0 failed, 0 missing, 4 justified omissions**, включая accepted praise. Native desktop **1440×1000** и mobile **390×844** без mocks: all11 bodies/titles/confidence/age, limited notice и все четыре individual omission explanations совпали с persisted API. API/native PDFs одинаковы — **7 pages, 27,373 bytes**, SHA256 `588a42c85d46ca624c0d73c44fb9531b46af3ac4bafd01d0638bc02ade2ac3af`; PDF body и fallback parity PASS. Ноль page errors/overflow/Child mutations; private reasons не раскрыты, нет автоматической regeneration. Parent независимо прочитал API/PDF и осмотрел desktop/mobile praise и PDF page 5 без видимого clipping. Старые reports 1–4 и их PDFs доступны и не переинтерпретированы. [Финальное evidence](../../reviews/2026-10-28/BUG-50-child-content-quality.md) закрывает BUG-50, не весь E22.

## Отдельный продуктовый follow-up #51

Избыточное threshold-based отсечение тематических разделов при имеющихся средних/смешанных показателях зафиксировано к последующему исправлению в `fixemer90-stack/Archemap#51`. Порог должен влиять на уверенность/тип пояснения, а не автоматически исключать доступный тематический материал. Это отдельная версия content/ownership policy; старые артефакты не переписываются. Текущий закрытый Story проверен по прежним критериям и не объявляет follow-up выполненным. Подробности и границы: [PRODUCT-FOLLOW-UPS.md](./PRODUCT-FOLLOW-UPS.md).

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
