# Story E8.S05: Load Testing

**Feature:** [Production & Scale](Archemap/docs/features/v1/E8-production-scale/FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Нагрузочное тестирование для определения capacity и bottlenecks перед production.

## Что сделать

- Выбрать инструмент (k6, Locust, Gatling)
- Написать сценарии тестов
- Запустить baseline тест
- Определить bottlenecks
- Оптимизировать

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `tests/load/` | Load test scripts |
| `tests/load/k6/` | k6 test scenarios |
| `tests/load/results/` | Test results |

## Сценарии тестов

| Сценарий | Описание | Целевые метрики |
|---|---|---|
| **Auth Flow** | Register → Login → Get profile | p95 < 500ms |
| **Chart Computation** | POST /chart → compute | p95 < 2s |
| **Report Generation** | POST /reports/generate | p95 < 5s |
| **API Read** | GET /profiles, GET /reports | p95 < 200ms |
| **Geocode** | GET /profiles/geocode?q= | p95 < 300ms |

## Нагрузочные профили

| Профиль | Пользователи | Duration | Описание |
|---|---|---|---|
| **Smoke** | 10 | 1 min | Базовая проверка |
| **Load** | 100 | 5 min | Нормальная нагрузка |
| **Stress** | 500 | 10 min | Пиковая нагрузка |
| **Soak** | 50 | 30 min | Длительная нагрузка |

## Критерии приёмки

- [ ] k6 или Locust установлен и настроен
- [ ] Сценарии для всех основных flows
- [ ] Baseline тест пройден
- [ ] p95 < 500ms для API endpoints
- [ ] p95 < 2s для chart computation
- [ ] p95 < 5s для report generation
- [ ] 500 concurrent users без ошибок
- [ ] Отчёт с метриками и bottlenecks

## Примечания

- k6 рекомендуется (JavaScript, легко писать сценарии)
- Locust альтернатива (Python, если команда не знает JS)
- Тестировать на staging environment, не на production
