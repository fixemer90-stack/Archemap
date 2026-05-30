# Story E9.S01: Birth Data Form

**Feature:** [Frontend Self Report](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Форма ввода данных рождения — точка входа в продукт. Пользователь вводит дату, время и место рождения. Система геокодирует место, валидирует данные и отправляет на backend для расчёта карты.

## Что сделать

1. **Компонент формы** (`components/birth-data-form.tsx`):
   - Date picker (дата рождения)
   - Time picker (время рождения, опционально "точно не знаю")
   - Place autocomplete (место рождения с геокодингом через Nominatim)
   - Кнопка "Рассчитать"

2. **Геокодинг интеграция**:
   - Autocomplete по `/api/v1/profiles/geocode?q=...`
   - Debounce 300ms
   - Отображение результатов: город, регион, страна
   - Выбор → latitude, longitude, timezone

3. **Валидация**:
   - Дата: не в будущем, не раньше 1900
   - Время: 00:00–23:59 или null
   - Место: обязательное поле, должно быть из geocode результатов

4. **State management** (Zustand store):
   - `birthDate`, `birthTime`, `birthPlace`, `lat`, `lon`, `timezone`
   - `isSubmitting`, `error`

5. **API call**:
   - `POST /api/v1/profiles` с данными формы
   - `POST /api/v1/profiles/{id}/chart` для расчёта карты
   - Redirect на `/report/{profile_id}` после успеха

## Затрагиваемые файлы

- `frontend/src/components/birth-data-form.tsx` — новый
- `frontend/src/stores/birth-form-store.ts` — новый
- `frontend/src/lib/api/profiles.ts` — новый (API client)
- `frontend/src/app/page.tsx` — обновить (landing page с формой)

## Критерии приёмки

- [ ] Форма отображается на desktop и mobile
- [ ] Geocoding autocomplete работает с debounce
- [ ] Валидация показывает ошибки inline
- [ ] Успешная отправка → redirect на report page
- [ ] Ошибка API показывается пользователю
- [ ] ruff, mypy, eslint — 0 ошибок
- [ ] Компонент покрыт unit-тестами (React Testing Library)

## Примечания

- Geocoding через Nominatim (OpenStreetMap) — бесплатно, без API key
- Timezone определяется автоматически по координатам (timezonefinder)
- Если время неизвестно → использовать 12:00 как default
