# Story E9.S04: Report Page

**Feature:** [Frontend Self Report](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Страница отчёта — сборка всех компонентов в единую страницу: форма ввода → карта → соционический результат. Это финальный продукт, который видит пользователь.

## Что сделать

1. **Страница отчёта** (`app/report/[profileId]/page.tsx`):
   - Header: имя профиля, дата рождения
   - Section 1: Натальная карта (Chart Visualization)
   - Section 2: Соционический тип (Socionics Result)
   - Section 3: Функциональный профиль (Function Profile)
   - Section 4: Evidence Trail (опционально, для авторизованных)

2. **Loading states**:
   - Skeleton для карты (пока загружается)
   - Skeleton для socionics (пока считается)
   - Progress indicator: "Считаем карту..." → "Анализируем тип..."

3. **Error handling**:
   - Ошибка API → показать сообщение + кнопку "Попробовать снова"
   - Неполные данные → показать что есть + предупреждение

4. **Responsive layout**:
   - Desktop: 2-колоночный layout (карта слева, тип справа)
   - Mobile: одноконочный, вертикальная прокрутка

5. **SEO/OG**:
   - Meta tags: title, description с именем типа
   - OG image: генерируется на backend (опционально)

## Затрагиваемые файлы

- `frontend/src/app/report/[profileId]/page.tsx` — новый
- `frontend/src/app/report/[profileId]/loading.tsx` — новый
- `frontend/src/components/report-layout.tsx` — новый

## Критерии приёмки

- [ ] Страница загружается по URL `/report/{profileId}`
- [ ] Все секции отображаются корректно
- [ ] Loading states работают
- [ ] Error handling работает
- [ ] Mobile responsive
- [ ] ruff, mypy, eslint — 0 ошибок

## Примечания

- ProfileId — UUID из backend
- Если профиль не найден → 404 page
- Если карта не вычислена → redirect на форму ввода
