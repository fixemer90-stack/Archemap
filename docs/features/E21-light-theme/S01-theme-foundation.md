# E21.S01: Семантические токены и контрастный контракт

**Feature:** [E21 Цельная светлая тема Astrotype](./FEATURE.md)

**Статус:** ✅ Завершено

## Контекст

Текущие root-переменные недостаточны: компоненты используют много жёстких dark-only цветов. Сначала нужен полный семантический контракт, иначе миграция экранов снова даст частичную тему.

## Что сделать

1. Инвентаризировать theme-sensitive цвета и классы во всём `frontend/src`.
2. Зафиксировать пары light/dark для canvas, surfaces, overlays, typography, borders, controls, states, shadows и charts.
3. Развести брендовые product accents и theme-dependent presentation tokens.
4. Определить contrast rules для body text, muted text, links, focus, disabled и destructive states.
5. Добавить deterministic script, который проверяет наличие обязательных токенов и запрещённые новые hard-coded цвета.
6. Не снимать принудительную тёмную тему.

## Затрагиваемые файлы

| Файл                                        | Действие                                        |
| ------------------------------------------- | ----------------------------------------------- |
| `frontend/src/app/globals.css`              | Расширить semantic theme tokens                 |
| `frontend/scripts/check-theme-contract.mjs` | Создать static contract check                   |
| `frontend/package.json`                     | Подключить проверку в frontend tests            |
| `docs/SRS/SRS-E21-light-theme.md`           | Синхронизировать итоговые токены при изменениях |

## TDD

1. Написать failing-check на обязательные semantic tokens и forbidden hard-coded additions.
2. Запустить его и подтвердить ожидаемое падение на неполном контракте.
3. Добавить минимальный набор токенов.
4. Запустить check повторно до green.
5. Выполнить контрастные вычисления для каждой text/background пары.

## Критерии приёмки

- [x] Определены light/dark значения всех обязательных semantic tokens.
- [x] Canvas светлой темы не равен `#FFFFFF` и визуально отделён от surfaces.
- [x] Для обычного текста подтверждён contrast не ниже 4.5:1.
- [x] Для крупного текста и UI boundaries подтверждены применимые WCAG AA thresholds.
- [x] Product accents не используются напрямую как body text без contrast-safe варианта.
- [x] Static contract test сначала падает, затем проходит.
- [x] Root theme остаётся принудительно тёмной до S06.

## Evidence

- RED: `node scripts/check-theme-contract.mjs` — отсутствовал `--canvas`.
- GREEN: `node scripts/check-theme-contract.mjs` — semantic token и contrast contract пройден.
- Formatting: `npx prettier --check src/app/globals.css scripts/check-theme-contract.mjs`.

## Проверка

```bash
cd frontend
node scripts/check-theme-contract.mjs
npx prettier --check src/app/globals.css scripts/check-theme-contract.mjs
```
