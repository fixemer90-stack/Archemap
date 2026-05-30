# Story E9.S02: Chart Visualization

**Feature:** [Frontend Self Report](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Визуализация натальной карты: планеты в знаках и домах, аспекты между планетами. Это core-компонент, который показывает "что вычислила система".

## Что сделать

1. **Компонент планет** (`components/chart-planets.tsx`):
   - Таблица/список 12 планет
   - Для каждой: название, знак, градус, дом, ретроgrade
   - Иконки/символы планет и знаков зодиака

2. **Компонент домов** (`components/chart-houses.tsx`):
   - Таблица 12 домов
   - Для каждого: номер, знак, градус куспиды

3. **Компонент аспектов** (`components/chart-aspects.tsx`):
   - Таблица аспектов
   - Для каждого: планета A, тип аспекта, планета B, orb, applying/separating
   - Цветовая кодировка по типу аспекта (conjunction=красный, trine=зелёный, etc.)

4. **Колесо карты** (`components/chart-wheel.tsx`):
   - SVG-визуализация натальной карты
   - 12 домов как секторы
   - Планеты positioned по долготе
   - Аспекты как линии между планетами
   - Responsive: desktop=полное колесо, mobile=список

5. **API client**:
   - `GET /api/v1/profiles/{id}/chart` — получить данные карты
   - TanStack Query с кешированием

## Затрагиваемые файлы

- `frontend/src/components/chart-planets.tsx` — новый
- `frontend/src/components/chart-houses.tsx` — новый
- `frontend/src/components/chart-aspects.tsx` — новый
- `frontend/src/components/chart-wheel.tsx` — новый
- `frontend/src/lib/api/charts.ts` — новый
- `frontend/src/types/chart.ts` — новый (TypeScript interfaces)

## Критерии приёмки

- [ ] Все 12 планет отображаются с правильными знаками/домами
- [ ] Аспекты отображаются с цветовой кодировкой
- [ ] SVG колесо рендерится на desktop
- [ ] Mobile fallback: компактный список вместо колеса
- [ ] Loading skeleton при загрузке данных
- [ ] ruff, mypy, eslint — 0 ошибок

## Примечания

- Символы планет: Unicode астрологические символы (☉☽☿♀♂♃♄♅♆♇)
- Символы знаков: Unicode зодиакальные символы (♈♉♊♋♌♍♎♏♐♑♒♓)
- Цвета аспектов: conjunction=красный, opposition=красный, trine=зелёный, sextile=синий, square=оранжевый, quincunx=серый
