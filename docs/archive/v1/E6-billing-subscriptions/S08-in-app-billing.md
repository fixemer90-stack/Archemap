# Story E6.S08: Frontend billing and upsell flow

Feature: [Billing & Subscriptions](Archemap/docs/features/v1/E6-billing-subscriptions/FEATURE.md)
Статус: ⬜ Не начато

## Контекст

После появления backend catalog, access state и report gating пользовательский сценарий всё ещё может быть сырым, если frontend не умеет красиво и однозначно проводить человека через upgrade.

Эта story собирает финальный UX-слой:

- `/billing` показывает не только маркетинговую витрину, но и текущий access state;
- report/product pages умеют показывать paywall и locked sections;
- после оплаты frontend корректно обновляется;
- пользователь понимает, что происходит при pending/failure/success.

Это финальная связка, которая превращает backend contract в понятный коммерческий опыт.

## Что сделать

1. Подключить `/billing` к реальным backend данным:
   - catalog plan
   - current access state
   - active/past payment summary
2. Реализовать checkout CTA и redirect flow из billing page.
3. Реализовать paywall/upsell блоки на report/product pages.
4. Реализовать post-payment UX:
   - refresh after return
   - waiting state
   - success unlock
   - retry after failure
5. Подготовить frontend regression checks на billing and paywall UX.

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `frontend/src/app/(dashboard)/billing/page.tsx` | Главная billing page |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Preview/locked/paywall states |
| `frontend/src/app/(dashboard)/products/self/page.tsx` | Upsell из Free Self flow |
| `frontend/src/app/(dashboard)/products/career/page.tsx` | Locked Career access и CTA |
| `frontend/src/lib/api/` | API helpers для billing/access/payment refresh |
| `frontend/scripts/check-billing-ux.mjs` | Regression checks для billing/paywall UX |
| `docs/features/E6-billing-subscriptions/API.md` | Frontend-consumed contracts |
| `docs/features/E6-billing-subscriptions/WORKFLOW.md` | User journey и ожидания UX |

## Критерии приёмки

- [ ] `/billing` показывает реальный access state пользователя, а не только статическую витрину
- [ ] Checkout CTA подключён к backend create-payment flow
- [ ] После return from payment frontend умеет отличать `checkout_pending`, `plus_active`, `payment_failed`
- [ ] Report/product pages показывают locked sections и upgrade CTA на основе backend contract
- [ ] Career-page не делает вид, что продукт полностью бесплатен, если нужен Plus
- [ ] Есть frontend regression checks на billing/paywall state
- [ ] Структурные проверки ловят отсутствие access-state UI и paywall-маркеров
- [ ] Тесты написаны и проходят
- [ ] ruff, mypy, eslint — 0 ошибок
- [ ] Документация обновлена

## Примечания

Эта story не должна сама изобретать коммерческую логику. Её задача — корректно отрендерить уже зафиксированный backend contract Free vs Plus и не испортить его optimistic-состояниями или случайным обходом paywall.