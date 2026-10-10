# E21.S06: Visual/accessibility gates и безопасный rollout

**Feature:** [E21 Цельная светлая тема Astrotype](./FEATURE.md)

**Статус:** 🟡 Локальные gates завершены, staging rollout ожидается

## Контекст

Тема считается готовой не по наличию CSS-переменных, а по реальному виду всех активных маршрутов. Нужна воспроизводимая матрица и fail-closed rollout.

## Что сделать

1. Создать browser matrix для 390, 820 и 1440 px в light/dark.
2. Сохранить screenshot baselines ключевых маршрутов и состояний.
3. Добавить axe/contrast checks и ручной checklist для charts, overlays, disabled, focus, hover и errors.
4. Проверять `scrollWidth <= clientWidth` на каждой viewport/theme комбинации.
5. Добавить completeness gate, блокирующий включение switcher при missing route/state.
6. Развернуть на staging сначала с dark lock и новыми токенами, затем включить selector.
7. Выполнить authenticated staging smoke и записать evidence.
8. Сохранить простой rollback к dark lock.

## Обязательная visual matrix

| Поверхность                   | Light    | Dark     | 390      | 820      | 1440     |
| ----------------------------- | -------- | -------- | -------- | -------- | -------- |
| Homepage                      | required | required | required | required | required |
| Login/register                | required | required | required | required | required |
| Dashboard + shell             | required | required | required | required | required |
| Settings                      | required | required | required | required | required |
| Billing/subscriptions         | required | required | required | required | required |
| Product pages                 | required | required | required | required | required |
| V2 report ready/loading/error | required | required | required | required | required |
| Career report                 | required | required | required | required | required |
| Modal/popover/tooltip         | required | required | required | required | required |

## Затрагиваемые файлы

| Файл/каталог                                                        | Действие              |
| ------------------------------------------------------------------- | --------------------- |
| `frontend/tests/e2e/theme.spec.ts`                                  | Theme behavior        |
| `frontend/tests/e2e/theme-visual.spec.ts`                           | Screenshot matrix     |
| `frontend/tests/e2e/theme-accessibility.spec.ts`                    | axe/contrast/overflow |
| `frontend/scripts/check-theme-contract.mjs`                         | Completeness gate     |
| `docs/features/E21-light-theme/FEATURE.md`                          | Status/evidence sync  |
| `docs/features/E21-light-theme/S06-visual-accessibility-rollout.md` | Staging evidence      |

## Критерии приёмки

- [x] Все visual matrix cells пройдены.
- [x] Нет serious/critical axe violations.
- [x] Contrast exceptions отсутствуют; semantic contrast pairs закреплены source contract.
- [x] Нет horizontal overflow на обязательных viewport.
- [ ] CI блокирует theme regressions.
- [ ] Staging smoke выполнен в authenticated session.
- [x] Switcher включён только после green локального completeness gate.
- [ ] Rollback к dark lock проверен.
- [x] Feature/story/SRS статусы и evidence синхронизированы с локальным состоянием; rollout gaps оставлены открытыми.

## Локальное evidence

- Commit: `2a24bd1 test(e21): add visual accessibility matrix`.
- Viewports: Playwright projects `390×844`, `820×1180`, `1440×1100`.
- Themes: `light`, `dark`; preference behavior отдельно покрыт `theme.spec.ts`.
- Visual baselines: 66 screenshots — 11 surfaces/states × 2 themes × 3 viewport classes.
- States: homepage, login, dashboard shell, settings, billing, Career product, V2 ready/loading/error, Career reader, keyboard tooltip.
- `npx playwright test tests/e2e/theme-visual.spec.ts` — `6 passed`.
- `npx playwright test tests/e2e/theme-accessibility.spec.ts` — `6 passed`; serious/critical axe violations отсутствуют, overflow assertions прошли на каждой route/theme/viewport комбинации.
- Ручная contact-sheet проверка выполнена для desktop/mobile в обеих темах; mixed-theme islands, clipping и незапланированные error states не обнаружены.
- V2 generation copy дополнительно очищен от raw status values; loading и error baselines используют пользовательские формулировки.
- CI evidence, staging authenticated smoke и rollback drill будут записаны после push/rollout.

## Проверка

```bash
cd frontend
npm test
npx eslint .
npx prettier --check .
npx tsc --noEmit --pretty false
npm run build
npx playwright test tests/e2e/theme.spec.ts
npx playwright test tests/e2e/theme-visual.spec.ts
npx playwright test tests/e2e/theme-accessibility.spec.ts
```

## Rollout evidence template

- Commit SHA:
- CI run:
- Staging marker:
- Routes checked:
- Viewports checked:
- Themes checked:
- axe result:
- Overflow result:
- Authenticated smoke result:
- Rollback drill result:
- Remaining blockers:
