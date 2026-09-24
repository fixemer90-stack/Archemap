# S10: Questionnaire и product UX

## Статус

🟡 Реализовано; реальный browser smoke остаётся открытым

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
- [ ] Responsive/accessibility tests и реальный browser smoke проходят.

## Реализация и проверка

- `/products/career` использует только `/api/v1/career/*`: persisted draft, completion, async create и polling по `generation_id`.
- Вопросы, варианты, required-state и access-state приходят с backend; URL оплаты не используется как источник доступа.
- Idempotency keys переиспользуются при retry в рамках flow, а повторный submit блокируется.
- Deterministic-ready состояние даёт ссылку на progressive reader до завершения narrative.
- Self-report CTA использует `/products/career?profileId=...`; Career page читает deep link и открывает questionnaire нужного профиля без повторного ручного выбора.
- `npm test` — все UX contract scripts прошли, включая `check-career-product-ux.mjs`.
- `npx tsc --noEmit --pretty false` — passed.
- `npx eslint src/app/'(dashboard)'/products/career/page.tsx src/lib/api/career.ts` — passed после устранения hook warning.

Открытый пункт требует реального mobile/desktop browser smoke с backend и активной Plus/legacy entitlement. Попытка локального smoke 24 сентября 2026 года не считается evidence: запуск Windows Chrome был остановлен системным consent timeout до выполнения команды.
