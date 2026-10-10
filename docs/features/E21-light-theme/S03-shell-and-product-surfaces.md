# E21.S03: Shell и продуктовые поверхности

**Feature:** [E21 Цельная светлая тема Astrotype](./FEATURE.md)

**Статус:** ✅ Завершено

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

- [x] Shell целиком использует одну тему; тёмные islands на светлом canvas отсутствуют по semantic source contract.
- [x] Активный пункт меню различим через фон, border и icon treatment, а не только цвет.
- [x] Homepage/dashboard/settings/billing/subscriptions/products переведены на semantic tokens.
- [x] Empty/loading/error/locked states в этих поверхностях покрыты semantic tokens.
- [x] На 390, 820 и 1440 px нет горизонтального overflow по browser matrix S06.
- [x] Product accents используют отдельные contrast-safe light/dark tokens.
- [x] Dark root lock сохранялся до S05; selector включён только после green локального completeness gate.

## Evidence

- RED: `node scripts/check-theme-contract.mjs` — `src/components/layout/header.tsx` содержал dark-only literals.
- GREEN: shell/account/product source contract проходит; inert bell и decorative avatar удалены.
- Checks: `node scripts/check-dashboard-shell-ux.mjs`, `node scripts/check-product-surface-redesign.mjs`, `node scripts/check-billing-ux.mjs`, `node scripts/check-birth-data-settings-ux.mjs`, ESLint и TypeScript.
- Browser evidence: `npx playwright test tests/e2e/theme-visual.spec.ts` и `theme-accessibility.spec.ts` — по `6 passed`; shell/account/product surfaces проверены в light/dark на 390/820/1440 без overflow.

## Проверка

```bash
cd frontend
node scripts/check-dashboard-shell-ux.mjs
node scripts/check-product-surface-redesign.mjs
npm test
npx tsc --noEmit --pretty false
```
