# E21.S02: Миграция UI primitives на семантические токены

**Feature:** [E21 Цельная светлая тема Astrotype](./FEATURE.md)

**Статус:** ✅ Завершено

## Контекст

Страницы нельзя надёжно переводить по одной, пока базовые Card, Button, Input и overlay-компоненты сами содержат dark-only значения.

## Что сделать

1. Перевести базовые UI primitives на semantic tokens.
2. Покрыть default, hover, active, focus-visible, disabled, loading, error и destructive states.
3. Унифицировать glass-эффект: в светлой теме это tinted translucent surface, а не белая карточка поверх белого canvas.
4. Проверить portal surfaces: dialog, popover, tooltip, select и toast не должны наследовать неверный фон.
5. Добавить component-level theme tests до изменения production styles.

## Затрагиваемые файлы

| Файл/каталог                                  | Действие                         |
| --------------------------------------------- | -------------------------------- |
| `frontend/src/components/ui/`                 | Мигрировать primitives           |
| `frontend/src/app/globals.css`                | Добавить/уточнить utility tokens |
| `frontend/scripts/check-theme-contract.mjs`   | Расширить component audit        |
| `frontend/tests/` или существующие UX scripts | Добавить light/dark state checks |

## TDD

Для каждого семейства компонентов:

1. Добавить failing assertion для light/dark styles и состояний.
2. Подтвердить падение на текущем hard-coded стиле.
3. Выполнить минимальную token migration.
4. Запустить targeted test.
5. После green перейти к следующему primitive.

## Критерии приёмки

- [x] Button, Input, Card и используемые overlays не зависят от dark-only literals.
- [x] Focus-visible различим на всех surfaces в обеих темах.
- [x] Disabled state остаётся читаемым и очевидно неактивным.
- [x] Error/destructive состояния не теряют смысл на светлом фоне.
- [x] Glass surfaces отделяются от canvas без чрезмерной белизны.
- [x] Component checks проходят в light и dark.
- [x] Принудительная тёмная тема пока сохранена.

## Evidence

- RED: `node scripts/check-theme-contract.mjs` — `button.tsx` содержал theme-sensitive literals.
- GREEN: semantic migration для Button/Input/Card/Skeleton и glass utilities.
- Checks: `node scripts/check-theme-contract.mjs`, `npx eslint src/components/ui scripts/check-theme-contract.mjs`, `npx tsc --noEmit --pretty false`, `npm test`.

## Проверка

```bash
cd frontend
npm test
npx eslint src/components/ui
npx tsc --noEmit --pretty false
```
