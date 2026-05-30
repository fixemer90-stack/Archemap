# Feature E9: Frontend — Self Report

## Цель

Первая кликабельная страница продукта: пользователь регистрируется с полными данными рождения, получает натальную карту и соционический тип. Это MVP-путь "зарегистрировался → увидел результат".

## Зависимости

- `E3` (Chart Engine) ✅ — карта считается
- `E4` (Rules & Content) 🟡 — socionics.py с Model A готов, YAML-правила и шаблоны待定
- `E2` (Identity) 🟡 — авторизация через JWT

## Критерии приёмки

- [ ] Регистрация собирает всё: email, password, дата, время, место рождения
- [ ] OAuth через Яндекс с получением birthday
- [ ] Карта отображается: планеты в знаках/домах, аспекты
- [ ] Соционический тип: топ-3 с scores и Model A breakdown
- [ ] Функциональный профиль: 8 функций (Se/Si/Ne/Ni/Fe/Fi/Te/Ti) с визуализацией
- [ ] Адаптивный дизайн (mobile-first)

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Auth Screens: login, register с birth data, OAuth callback, geocoding](S01-auth-screens.md) | ⬜ Не начато |
| S02 | [Chart Visualization: отображение натальной карты (планеты, дома, аспекты)](S02-chart-visualization.md) | ⬜ Не начато |
| S03 | [Socionics Result: топ-3 типа, scores, Model A breakdown, функциональный профиль](S03-socionics-result.md) | ⬜ Не начато |
| S04 | [Report Page: сборка страницы отчёта из компонентов карты и результата](S04-report-page.md) | ⬜ Не начато |

## Архитектура

```mermaid
flowchart TD
    A[Register с birth data] -->|POST /auth/register| B[Backend API]
    B -->|User + PersonProfile| C[Auto Chart Computation]
    C -->|chart + socionics| D[Report Page]
    D --> E[Chart Visualization]
    D --> F[Socionics Result]
    
    G[OAuth Яндекс] -->|GET /auth/callback| H{needs_profile?}
    H -->|yes| A
    H -->|no| D
```

## Технологический стек

- Next.js 15 + React 19
- Tailwind CSS 4 + shadcn/ui
- TanStack Query для API calls
- Zustand для состояния формы
- Recharts или custom SVG для визуализации функций
