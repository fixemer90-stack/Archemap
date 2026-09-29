# S10: Questionnaire и product UX

## Статус

✅ Завершено — automated browser suite и deployed-backend Chromium smoke active Plus/grandfathered entitlement зелёные

## Контекст

Пользовательский вход должен объяснять ценность отчёта, проверить доступ и собрать контекст до запуска дорогой генерации. Текущая страница сразу вызывает synchronous generation и не задаёт вопросов.

## Что сделать

1. Обновить `/products/career` под target flow.
2. Показать, что отчёт объясняет механику работы, а не обещает профессию.
3. Выбрать профиль и проверить наличие готовой натальной карты.
4. Показать access state и корректный Plus/legacy entitlement CTA.
5. Реализовать 8–12 вопросов с progress, autosave draft, back/forward и resume.
6. Разделить choice questions и ограниченный current-context input.
7. Перед completion показать consent/объяснение использования ответов.
8. После запуска перейти на generation progress и progressive report.
9. Обработать incomplete answers, auth expiry, locked, conflict, timeout и provider failure.

## UX-принципы

- Не показывать внутренние dimension keys и англоязычный жаргон без перевода.
- Не обещать «идеальную профессию» или гарантированный результат.
- Объяснить, что ответы уточняют применение склонностей, а не подгоняют карту.
- Не заставлять повторно отвечать при network retry.
- Mobile-first, keyboard navigation, accessible labels и сохраняемый прогресс.

## Критерии приёмки

- [x] Новый flow не вызывает legacy synchronous Career generation.
- [x] Draft восстанавливается после reload/session return.
- [x] Обязательные вопросы нельзя пропустить без понятной ошибки.
- [x] Profile/access states читаются с backend, не выводятся из checkout URL.
- [x] Один completion создаёт максимум одну generation.
- [x] UI показывает deterministic-ready результат до полного narrative.
- [x] Locked пользователь не видит protected preview payload.
- [x] Desktop/mobile responsive, keyboard и accessibility browser tests проходят.
- [x] Live browser smoke проходит с реальным backend и active Plus/legacy entitlement.

## Реализация и проверка

- `/products/career` использует только `/api/v1/career/*`: persisted draft, completion, async create и polling по `generation_id`.
- Вопросы, варианты, required-state и access-state приходят с backend; URL оплаты не используется как источник доступа.
- Idempotency keys переиспользуются при retry в рамках flow, а повторный submit блокируется.
- Deterministic-ready состояние даёт ссылку на progressive reader до завершения narrative.
- Self-report CTA использует `/products/career?profileId=...`; Career page читает deep link и открывает questionnaire нужного профиля без повторного ручного выбора.
- `npm test` — все UX contract scripts прошли, включая `check-career-product-ux.mjs`.
- `npx tsc --noEmit --pretty false` — passed.
- `npx eslint src/app/'(dashboard)'/products/career/page.tsx src/lib/api/career.ts` — passed после устранения hook warning.
- Playwright Chromium проходит полный keyboard questionnaire flow на desktop/mobile, проверяет required-state, autosave, idempotency, deterministic-ready transition, horizontal overflow и Axe serious/critical violations.
- Visual regression baselines сохранены в `frontend/tests/e2e/career-questionnaire.spec.ts-snapshots/`; локальный прогон общего Career browser suite: `5 passed, 1 skipped`.
- На stage active Plus прошёл questionnaire/create до `ready`; grandfathered Career entitlement получил questionnaire HTTP `200`; повторный create с тем же idempotency key вернул тот же generation ID.
- Locked matrix для create/generation/read/sections/regenerate/PDF вернула `402` без protected payload.
- Полный deployed-backend flow завершился report `c84bfae8-6ed3-4a92-b841-733cbf0c59fb`, version `6`, `10/10` ready sections и валидным PDF.

## Live Chromium evidence 2026-09-28

- Active Plus использовал канонический entitlement product `self`: Career page HTTP `200`, questionnaire API `200`, report create `202`, reader `200`, PDF `200` (`32760` bytes, `%PDF`). Generation `58673ea9-08ee-40e5-93d9-3d887d194e11`, report `241306e3-d334-4fdb-87a4-ce816d88f71f`.
- Grandfathered entitlement product `career`: Career page HTTP `200`, questionnaire API `200`, report create `202`, reader `200`, PDF `200` (`32617` bytes, `%PDF`). Generation `08d6b11c-2fc7-44bf-b1c0-928ca21c3674`, report `b3de9e3e-6831-4964-b1f8-42c9b04af3c0`.
- Оба Chromium-сеанса прошли через публичный staging gateway с Basic Auth и HttpOnly auth cookies; failed Career/API responses и page errors отсутствовали.
- Sessions уже были completed; draft autosave/reload/resume остаётся доказан committed desktop/mobile Chromium suite, а live smoke доказывает entitlement → target create → progressive reader → PDF path.
