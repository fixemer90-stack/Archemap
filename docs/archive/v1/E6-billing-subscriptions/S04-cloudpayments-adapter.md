# Story E6.S04: Checkout/session integration

Feature: [Billing & Subscriptions](Archemap/docs/features/v1/E6-billing-subscriptions/FEATURE.md)
Статус: ⬜ Не начато

## Контекст

После S01–S03 у системы уже есть базовый payment layer, но пользователю всё ещё не хватает рабочего мостика между billing UI и backend checkout.

Именно эта story превращает абстрактный payment API в реальный вход в платный flow:

- откуда запускается checkout;
- какой `return_url` использует frontend;
- как `/billing` и product pages узнают текущий access state;
- как пользователь понимает, что оплата ещё ожидает подтверждения, уже активирована или требует повторной попытки.

Без этой story кнопка «Оформить Plus» остаётся визуальной заглушкой, а access contract не доходит до UI.

## Что сделать

1. Определить frontend entrypoints для запуска оплаты:
   - `/billing`
   - locked CTA в report/product flow
2. Реализовать backend-friendly checkout initiation contract:
   - plan/product identifier
   - `return_url`
   - redirect to `confirmation_url`
3. Добавить endpoint или service-слой для account/billing summary:
   - current `access_status`
   - active grants
   - summary последнего/активного payment
4. Описать и реализовать post-payment refresh сценарий:
   - пользователь вернулся с PSP;
   - frontend перечитал access state;
   - UI различает `checkout_pending`, `plus_active`, `payment_failed`
5. Зафиксировать UX для retry/refresh без optimistic unlock.

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/billing/router.py` | Endpoint для billing/access summary |
| `backend/app/modules/billing/service.py` | Агрегация access state и payment summary |
| `backend/app/modules/billing/schemas.py` | Pydantic contract для `/billing/access` |
| `backend/app/modules/payments/router.py` | Checkout trigger contract |
| `frontend/src/app/(dashboard)/billing/page.tsx` | Подключение реального access state и checkout CTA |
| `frontend/src/app/(dashboard)/products/self/page.tsx` | Upgrade entrypoint из product page |
| `frontend/src/app/(dashboard)/products/career/page.tsx` | Upgrade entrypoint из locked paid flow |
| `docs/features/E6-billing-subscriptions/API.md` | Account/access endpoint contract |
| `docs/features/E6-billing-subscriptions/WORKFLOW.md` | Return-from-payment user flow |

## Критерии приёмки

- [ ] У `/billing` есть backend contract для чтения current access state
- [ ] Frontend запускает checkout только по server-owned identifier и `return_url`
- [ ] После возврата с PSP UI перечитывает backend access state, а не включает Plus локально сам
- [ ] Есть отдельные UX-состояния для `checkout_pending`, `plus_active`, `payment_failed`
- [ ] Кнопка оплаты на `/billing` перестаёт быть чисто декоративной заглушкой
- [ ] Report/product CTA могут переиспользовать тот же checkout flow
- [ ] Тесты покрывают summary/access endpoint и post-payment refresh path
- [ ] Тесты написаны и проходят
- [ ] ruff, mypy, eslint — 0 ошибок
- [ ] Документация обновлена

## Примечания

Суть этой story не в поддержке второго PSP. Её задача — дать пользователю и frontend один понятный маршрут: увидеть ценность, запустить оплату, вернуться в приложение и получить подтверждённый state доступа.