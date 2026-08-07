# Story E6.S06: Report/backend gating

Feature: [Billing & Subscriptions](Archemap/docs/features/v1/E6-billing-subscriptions/FEATURE.md)
Статус: ⬜ Не начато

## Контекст

Именно здесь E6 перестаёт быть feature про деньги и становится feature про доступ к продукту.

Сейчас самый опасный риск такой: backend может продолжать отдавать полный платный payload, а frontend просто будет пытаться спрятать его визуально. Это плохой контракт и прямой путь к утечке paid content.

Эта story вводит backend gating для reports и paid products:

- `self` должен различать `preview` и `full`;
- `career` должен различать `locked` и `full`;
- API должно возвращать paywall metadata для UX;
- direct route не должен обходить ограничения.

## Что сделать

1. Определить contract-level `access_mode` для report/product responses:
   - `preview`
   - `full`
   - `locked`
2. Зафиксировать состав preview для Self:
   - что доступно бесплатно;
   - какие sections locked;
   - какой CTA должен быть показан
3. Зафиксировать locked-flow для Career без Plus.
4. Обновить report/product response schemas:
   - `access_mode`
   - `upgrade_required`
   - `locked_sections`
   - `billing_cta`
5. Применить gating на backend до возврата payload, а не только в UI.

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/reports/service.py` | Формирование preview/full contract |
| `backend/app/modules/reports/router.py` | Возврат gated report responses |
| `backend/app/modules/reports/schemas.py` | Pydantic поля access metadata |
| `backend/app/modules/authorization/service.py` | Policy-check для access mode |
| `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Locked/preview rendering states |
| `frontend/src/app/(dashboard)/products/career/page.tsx` | Locked paid vertical UX |
| `docs/features/E6-billing-subscriptions/API.md` | Report access contract |
| `docs/features/E6-billing-subscriptions/WORKFLOW.md` | Direct-access and paywall behavior |

## Критерии приёмки

- [ ] Self-report может возвращаться как `preview` и как `full`
- [ ] Career без платного доступа возвращает `locked`, а не full payload
- [ ] API явно возвращает `access_mode`, `upgrade_required`, `locked_sections`, `billing_cta`
- [ ] Полный paid content не отдаётся бесплатно «под CSS/blur/accordion hiding»
- [ ] Direct navigation на `/report/...` и paid product routes не обходит gating
- [ ] Frontend умеет рендерить locked/preview state на основе backend contract
- [ ] Тесты покрывают preview/full/locked responses
- [ ] Тесты написаны и проходят
- [ ] ruff, mypy, eslint — 0 ошибок
- [ ] Документация обновлена

## Примечания

Это одна из самых продуктово-критичных stories E6. Если она не сделана, то даже корректная оплата и entitlement не гарантируют реального разделения Free и Plus.