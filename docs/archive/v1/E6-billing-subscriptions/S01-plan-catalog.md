# Story E6.S01: Каталог планов и access matrix

Feature: [Billing & Subscriptions](Archemap/docs/features/v1/E6-billing-subscriptions/FEATURE.md)
Статус: ⬜ Не начато

## Контекст

Сейчас frontend billing page уже продаёт единый Plus за `999 ₽ / месяц`, но backend catalog пока описывает другие коммерческие сущности: `self_full` и `career_full`.

Пока этот разрыв не закрыт, невозможно корректно реализовать checkout, access policy и post-payment unlock, потому что разные части системы говорят о разных товарах.

Эта story фиксирует product truth-модель: что именно продаётся, по какому идентификатору, за какую цену и какие grants открывает.

## Что сделать

1. Определить единый server-owned identifier для коммерческого плана MVP.
2. Привести backend catalog к целевой модели Free vs Plus.
3. Описать access matrix по продуктам и режимам:
   - `self`: preview/full
   - `career`: locked/full
   - будущие verticals: locked до отдельного решения
4. Согласовать цену, интервал и copy с `/billing`.
5. Подготовить API shape для чтения каталога планов frontend'ом.

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/catalog/service.py` | Источник коммерческого каталога |
| `backend/app/modules/catalog/schemas.py` | Pydantic schema каталога/планов |
| `backend/app/modules/catalog/router.py` | `GET /api/v1/catalog/plans` |
| `frontend/src/app/(dashboard)/billing/page.tsx` | UI должен читать тот же плановый контракт |
| `docs/features/E6-billing-subscriptions/FEATURE.md` | Сводный feature contract |
| `docs/features/E6-billing-subscriptions/API.md` | Контракт каталога и access state |
| `docs/SRS/SRS-E6-billing-subscriptions.md` | Формальный SRS |

## Критерии приёмки

- [ ] В системе определён один MVP-план Plus с единым `plan_code/product_id`
- [ ] Цена, валюта и интервал в backend catalog совпадают с billing UI
- [ ] Catalog хранит не только цену, но и grants/access matrix
- [ ] Frontend больше не хардкодит коммерческую truth-модель отдельно от backend
- [ ] Есть контракт чтения каталога (`GET /api/v1/catalog/plans` или эквивалент)
- [ ] Тесты покрывают запрет неизвестного plan/product id
- [ ] Тесты написаны и проходят
- [ ] ruff, mypy, eslint — 0 ошибок
- [ ] Документация обновлена

## Примечания

Ключевое решение этой story: Astrotype продаёт не «случайные отдельные платные кнопки», а согласованную access model. Поэтому catalog обязан описывать не только стоимость, но и состав прав доступа.
