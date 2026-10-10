# E21.S04: Auth, отчёты, charts и граничные состояния

**Feature:** [E21 Цельная светлая тема Astrotype](./FEATURE.md)

**Статус:** ⬜ Не начато

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

- [ ] Все auth routes целиком оформлены в light и dark.
- [ ] V2 и Career readers сохраняют читаемую narrative hierarchy.
- [ ] Chart grid, labels, series и tooltip читаемы в обеих темах.
- [ ] Статусы charts различаются не только цветом.
- [ ] Loading/locked/error/retry/not-found states не содержат mixed-theme surfaces.
- [ ] Длинные отчёты не дают белых разрывов и неверных sticky/overlay backgrounds.
- [ ] Root lock остаётся тёмным до S06.

## Проверка

```bash
cd frontend
node scripts/check-report-ux.mjs
node scripts/check-career-report-reader.mjs
npm test
npx eslint src/app/'(auth)' src/components/chart src/components/report
npx tsc --noEmit --pretty false
```
