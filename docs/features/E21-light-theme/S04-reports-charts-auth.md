# E21.S04: Auth, отчёты, charts и граничные состояния

**Feature:** [E21 Цельная светлая тема Astrotype](./FEATURE.md)

**Статус:** 🟡 Реализовано, browser matrix в S06

## Контекст

Даже если dashboard выглядит корректно, тема остаётся незавершённой, если login, report reader, charts или loading/error состояния возвращают dark-only блоки. Эти поверхности должны проходить отдельный аудит из-за SVG, canvas, gradients и длинного контента.

## Что сделать

1. Перевести auth routes и формы на semantic tokens.
2. Перевести v2 report reader и Career report reader, не меняя narrative hierarchy.
3. Определить отдельные chart tokens для grid, labels, series, highlights, tooltip и selected state.
4. Проверить natal chart, infographics, progress indicators и активные legacy visuals.
5. Проверить loading, generation, locked, failed, retry и not-found states.
6. Убедиться, что смысл не кодируется только цветом.

## Затрагиваемые файлы

| Файл/каталог                                           | Действие                      |
| ------------------------------------------------------ | ----------------------------- |
| `frontend/src/app/(auth)/`                             | Auth theme migration          |
| `frontend/src/app/(dashboard)/report/`                 | Report route states           |
| `frontend/src/components/astrotype-v2/`                | V2 reader and infographics    |
| `frontend/src/app/(dashboard)/products/career/report/` | Career reader                 |
| `frontend/src/components/chart/`                       | Chart tokens and labels       |
| `frontend/src/components/report/`                      | Loading/progress/error states |
| `frontend/scripts/check-report-ux.mjs`                 | Theme coverage markers        |

## Критерии приёмки

- [x] Все auth routes используют semantic light/dark contract.
- [x] V2 и Career readers используют theme-aware hierarchy tokens.
- [x] Chart grid, labels, series и tooltip используют отдельные chart tokens.
- [x] Статусы charts имеют текстовые/структурные labels и не зависят только от цвета.
- [x] Loading/locked/error/retry/not-found states не содержат theme-sensitive literals.
- [ ] Длинные отчёты не дают разрывов и неверных sticky/overlay backgrounds — browser matrix S06.
- [x] Root lock остаётся тёмным до S06.

## Evidence

- RED: расширенный `node scripts/check-theme-contract.mjs` упал на `billing-checkout-button.tsx` и report/chart/auth literals.
- GREEN: все active auth/report/chart/glossary/loading/error surfaces переведены на semantic/chart/state tokens; raw HEX/RGBA в active TSX запрещены.
- Checks: `node scripts/check-auth-ux.mjs`, `node scripts/check-report-ux.mjs`, `node scripts/check-career-report-reader.mjs`, `npm test`, ESLint и TypeScript.

## Проверка

```bash
cd frontend
node scripts/check-report-ux.mjs
node scripts/check-career-report-reader.mjs
npm test
npx eslint src/app/'(auth)' src/components/chart src/components/report
npx tsc --noEmit --pretty false
```
