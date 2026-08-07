# Story E9.S03: Socionics Result

**Feature:** [Frontend Self Report](Archemap/docs/features/v1/E9-frontend-self-report/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Отображение результата соционического анализа: топ-3 типа с scores, Model A breakdown и функциональный профиль. Это ключевая ценность продукта — "кто ты по соционике".

## Что сделать

1. **Компонент топ-3 типов** (`components/socionics-top-types.tsx`):
   - Карточки для топ-3 типов
   - Название типа (ILE, LSI, EIE, etc.)
   - Имя типа (Искатель, Инспектор, Наставник)
   - Score (0.0–1.0) с progress bar
   - Confidence score
   - Подсветка #1 как основного типа

2. **Компонент Model A breakdown** (`components/model-a-breakdown.tsx`):
   - 8 функций типа: base, creative, role, pain, suggestive, activation, restrictive, background
   - Для каждой: название функции, значение strengths, цветовая кодировка
   - Блоки: Ego (base+creative), Super-ego (role+pain), Super-id (suggestive+activation), Id (restrictive+background)

3. **Компонент функционального профиля** (`components/function-profile.tsx`):
   - Radar chart или bar chart для 8 функций (Se/Si/Ne/Ni/Fe/Fi/Te/Ti)
   - Нормализованные значения (0.0–1.0)
   - Цветовая кодировка: сильные=зелёный, слабые=красный
   - Интерактивность: hover показывает breakdown

4. **Компонент evidence trail** (`components/evidence-trail.tsx`):
   - Таблица вкладов: планета → функция → вес
   - Фильтр по функции (показать все вклады в Ti)
   - Сортировка по весу

5. **API client**:
   - `GET /api/v1/profiles/{id}/socionics` — получить результат
   - Response: `{type, top3, function_strengths, model_a_fit, evidence}`

## Затрагиваемые файлы

- `frontend/src/components/socionics-top-types.tsx` — новый
- `frontend/src/components/model-a-breakdown.tsx` — новый
- `frontend/src/components/function-profile.tsx` — новый
- `frontend/src/components/evidence-trail.tsx` — новый
- `frontend/src/lib/api/socionics.ts` — новый
- `frontend/src/types/socionics.ts` — новый

## Критерии приёмки

- [ ] Топ-3 типа отображаются с scores и confidence
- [ ] Model A breakdown показывает 8 функций по блокам
- [ ] Radar/bar chart визуализирует функциональный профиль
- [ ] Evidence trail показывает вклады планет
- [ ] Mobile responsive
- [ ] ruff, mypy, eslint — 0 ошибок

## Примечания

- Model A блоки: Ego (1-2), Super-ego (3-4), Super-id (5-6), Id (7-8)
- Функции: Se (extraverted sensing), Si (introverted sensing), Ne (extraverted intuition), Ni (introverted intuition), Fe (extraverted feeling), Fi (introverted feeling), Te (extraverted thinking), Ti (introverted thinking)
- Evidence trail — это explainability: пользователь видит, ПОЧЕМУ система определила именно этот тип
