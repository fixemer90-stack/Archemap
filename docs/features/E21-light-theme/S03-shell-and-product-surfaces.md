# E21.S03: Shell и продуктовые поверхности

**Feature:** [E21 Цельная светлая тема Astrotype](./FEATURE.md)

**Статус:** ⬜ Не начато

## Контекст

Header, sidebar и крупные продуктовые страницы формируют основное впечатление. Частично светлый canvas при тёмном shell был одной из главных причин визуального распада.

## Что сделать

1. Перевести header, desktop sidebar, tablet rail, mobile drawer и overlays на tokens.
2. Проверить active/hover/disabled navigation states.
3. Перевести homepage, dashboard, settings, billing, subscriptions и product landing pages.
4. Сохранить product accents Self/Love/Child/Career без снижения контраста.
5. Проверить loading, empty, locked и API error states на каждой поверхности.
6. Сохранить трёхрежимную responsive shell-модель без overflow.

## Затрагиваемые файлы

| Файл/каталог                                          | Действие                        |
| ----------------------------------------------------- | ------------------------------- |
| `frontend/src/components/layout/`                     | Theme migration shell           |
| `frontend/src/components/product-surface/`            | Theme migration shared surfaces |
| `frontend/src/app/page.tsx`                           | Public homepage                 |
| `frontend/src/app/(dashboard)/dashboard/page.tsx`     | Dashboard                       |
| `frontend/src/app/(dashboard)/settings/page.tsx`      | Settings                        |
| `frontend/src/app/(dashboard)/billing/page.tsx`       | Billing                         |
| `frontend/src/app/(dashboard)/subscriptions/page.tsx` | Subscriptions                   |
| `frontend/src/app/(dashboard)/products/`              | Product surfaces                |
| `frontend/scripts/check-dashboard-shell-ux.mjs`       | Расширить contract checks       |

## Критерии приёмки

- [ ] Shell целиком использует одну тему; тёмные islands на светлом canvas отсутствуют.
- [ ] Активный пункт меню различим без зависимости только от цвета.
- [ ] Homepage/dashboard/settings/billing/subscriptions/products проверены в обеих темах.
- [ ] Empty/loading/error/locked states покрыты.
- [ ] На 390, 820 и 1440 px нет горизонтального overflow.
- [ ] Product accents сохраняют узнаваемость и AA-контраст.
- [ ] Root lock остаётся тёмным; пользовательский switcher ещё не возвращён.

## Проверка

```bash
cd frontend
node scripts/check-dashboard-shell-ux.mjs
node scripts/check-product-surface-redesign.mjs
npm test
npx tsc --noEmit --pretty false
```
