# Библиотека компонентов — Astrotype

## 1. Обзор

Astrotype — платформа для самопознания через натальную карту. Дизайн-система
выстроена вокруг принципа **спокойного премиального опыта**: пользователь
чувствует глубину и доверие, а не мистическую эзотерику.

Ключевые принципы:

- **Чистота и тишина** — минимум визуального шума, воздух между элементами
- **Глубина через типографику** — продуманные иерархии заголовков и текста
- **Тактильность** — мягкие тени, стеклянные карточки, плавные переходы
- **Доступность** — контраст ≥ 4.5:1, навигация с клавиатуры, ARIA-атрибуты

Техническая база: Next.js 14 (App Router), TypeScript, Tailwind CSS,
shadcn/ui. Все компоненты по умолчанию — React Server Components; клиентские
аннотируются `'use client'` только при необходимости (см. раздел 7).

---

## 2. UI компоненты

Каталог: `src/components/ui/`

### Button

Обёртка shadcn/ui `<Button>` с расширенными вариантами.

```tsx
import { Button } from "@/components/ui/button";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost" | "destructive";
  size?: "sm" | "default" | "lg";
  asChild?: boolean;
}
```

| variant       | Описание                                      |
|---------------|-----------------------------------------------|
| `default`     | Violet/gold gradient fill                     |
| `outline`     | Transparent, silver border                    |
| `ghost`       | Transparent, без рамки, hover — подсветка     |
| `destructive` | Red tint для опасных действий (удаление и пр.)|

| size     | Высота | Применение                |
|----------|--------|---------------------------|
| `sm`     | 32 px  | Компактные inline-действия|
| `default`| 40 px  | Основные кнопки форм      |
| `lg`     | 48 px  | CTA на лендингах          |

### Card

Набор компонентов shadcn/ui для карточек. Стилизация — стеклянная
полупрозрачность (glass morphism).

```tsx
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
```

Все подкомпоненты принимают стандартные `HTMLDivElement` атрибуты и `className`.

### Input

```tsx
import { Input } from "@/components/ui/input";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  // Все стандартные HTML-атрибуты <input>
  // + className для переопределения стилей
}
```

### Skeleton

Заглушка загрузки. Заменяет контент пока данные подгружаются.

```tsx
import { Skeleton } from "@/components/ui/skeleton";

interface SkeletonProps {
  className?: string;
}
```

### Планируемые UI-компоненты

#### ClaimCard

Карточка интерпретации с оценкой, уверенностью и доказательствами.

```tsx
interface ClaimCardProps {
  title: string;              // Заголовок интерпретации
  claim: string;              // Текст утверждения
  score: number;              // Оценка 0–100
  confidence: "low" | "medium" | "high";
  evidence: string[];         // Список обоснований
  source?: string;            // Источник знания
}
```

#### ArchetypePortrait

Визуализация архетипа пользователя.

```tsx
interface ArchetypePortraitProps {
  archetype: string;          // Название архетипа
  traits: string[];           // Ключевые черты
  element: "fire" | "earth" | "air" | "water";
  imageUrl?: string;          // Опциональное изображение
}
```

---

## 3. Layout компоненты

Каталог: `src/components/layout/`

### Header

Верхняя панель с пользовательским меню и переключателем темы.

```tsx
interface HeaderProps {
  user?: {
    name: string;
    email: string;
    avatarUrl?: string;
  };
}
```

### Sidebar

Боковая навигация. Ссылки: Dashboard, Profiles, Charts, Settings, Billing.

```tsx
interface SidebarProps {
  collapsed?: boolean;        // Свёрнутый режим (иконки)
  activePath: string;         // Текущий маршрут для подсветки
}

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}
```

### Footer

Нижний блок с копирайтом и ссылками.

```tsx
interface FooterProps {
  // Без пропсов — статический контент
}
```

---

## 4. Chart компоненты (планируются)

Каталог (будущий): `src/components/chart/`

### NatalChart

SVG-визуализация натальной карты. Центральный элемент приложения.

```tsx
interface NatalChartProps {
  planets: PlanetPosition[];  // Положения планет
  aspects: Aspect[];          // Аспекты между планетами
  houses: House[];            // Вершины домов
  size?: number;              // Размер SVG (по умолчанию 600)
  interactive?: boolean;      // Клик по планете → детали
  highlightPlanet?: string;   // Подсветить конкретную планету
}

interface PlanetPosition {
  name: string;               // "Sun", "Moon", "Mars" ...
  sign: string;               // "Aries", "Taurus" ...
  degree: number;             // 0–30 в знаке
  house: number;              // 1–12
  retrograde: boolean;
  longitude: number;          // 0–360 эклиптическая долгота
}

interface Aspect {
  planetA: string;
  planetB: string;
  type: "conjunction" | "opposition" | "trine" | "square" | "sextile";
  orb: number;                // Орбис в градусах
}

interface House {
  number: number;             // 1–12
  cuspLongitude: number;      // 0–360
  sign: string;
}
```

### PlanetCard

Карточка с данными одной планеты: знак, градус, дом, ретроградность.

```tsx
interface PlanetCardProps {
  planet: PlanetPosition;
  interpretation?: string;    // Краткая интерпретация
  onClick?: () => void;       // Открыть детали
}
```

### AspectTable

Таблица аспектов с орбисами.

```tsx
interface AspectTableProps {
  aspects: Aspect[];
  onSelect?: (aspect: Aspect) => void;
  maxRows?: number;           // Ограничение видимых строк
}
```

### ElementWheel

Колесо распределения стихий (Fire / Earth / Air / Water).

```tsx
interface ElementWheelProps {
  distribution: {
    fire: number;             // Количество планет в огненных знаках
    earth: number;
    air: number;
    water: number;
  };
  size?: number;              // Диаметр колеса в px
}
```

### ProfileForm

Форма ввода данных рождения (дата, время, место с геокодингом).

```tsx
interface ProfileFormProps {
  initialData?: {
    name: string;
    birthDate: string;        // ISO 8601
    birthTime: string;        // HH:mm
    birthPlace: string;       // Строка адреса
    latitude?: number;
    longitude?: number;
    timezone?: string;
  };
  onSubmit: (data: ProfileFormData) => Promise<void>;
  onCancel?: () => void;
}

interface ProfileFormData {
  name: string;
  birthDate: string;
  birthTime: string;
  birthPlace: string;
  latitude: number;
  longitude: number;
  timezone: string;
}
```

### ChartSnapshot

Полноэкранная карточка отображения натальной карты с метаданными.

```tsx
interface ChartSnapshotProps {
  profileId: string;
  planets: PlanetPosition[];
  aspects: Aspect[];
  houses: House[];
  profile: {
    name: string;
    birthDate: string;
    birthTime: string;
    birthPlace: string;
  };
}
```

---

## 5. Report компоненты (планируются)

Каталог (будущий): `src/components/report/`

Report-компоненты группируют итоговый отчёт для пользователя.
Используют `ClaimCard`, `PlanetCard`, `AspectTable` и `ArchetypePortrait`
как строительные блоки.

```tsx
interface ReportSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}

interface FullReportProps {
  profileId: string;
  claims: ClaimCardProps[];
  archetype: ArchetypePortraitProps;
  planets: PlanetPosition[];
  aspects: Aspect[];
  houses: House[];
  generatedAt: string;        // ISO 8601
}
```

---

## 6. Дизайн-токены

Определяются в `tailwind.config.ts` и глобальных CSS-переменных.

### Цвета

| Токен              | Значение                        | Применение              |
|--------------------|---------------------------------|-------------------------|
| `--background`     | `hsl(250 60% 5%)` — deep violet | Фон страницы            |
| `--background-end` | `hsl(220 50% 8%)` — navy        | Конец радиального град. |
| `--foreground`     | `hsl(0 0% 95%)`                 | Основной текст          |
| `--muted`          | `hsl(0 0% 50%)`                 | Вторичный текст         |
| `--primary`        | `hsl(270 70% 60%)` — violet     | Акцент                  |
| `--primary-gold`   | `hsl(45 80% 60%)` — gold        | Градиент кнопок         |
| `--border`         | `hsl(0 0% 20%)`                 | Рамки                   |
| `--card-bg`        | `hsla(0 0% 100% 0.05)`          | Glass-фон карточек      |
| `--card-border`    | `hsla(0 0% 100% 0.10)`          | Рамка карточек           |

Фон страницы: `radial-gradient(circle at 50% 0%, var(--background), var(--background-end))`.

### Скругления (Border Radius)

| Контекст    | Значение |
|-------------|----------|
| Карточки    | `20px`   |
| Кнопки      | `16px`   |
| Инпуты      | `12px`   |
| Бейджи      | `24px`   |

### Тени

```css
--shadow-card: 0 8px 32px hsla(0 0% 0% / 0.4);
--shadow-elevated: 0 16px 48px hsla(0 0% 0% / 0.6);
--shadow-glow: 0 0 24px hsla(270 70% 60% / 0.3);
```

### Отступы (Spacing)

Базовая единица — `4px`. Основные шаги: `4, 8, 12, 16, 20, 24, 32, 40, 48, 64`.

### Типографика

| Уровень      | Размер | Вес   | Высота строки |
|--------------|--------|-------|---------------|
| `h1`         | 32px   | 700   | 1.2           |
| `h2`         | 24px   | 600   | 1.3           |
| `h3`         | 20px   | 600   | 1.4           |
| `body`       | 16px   | 400   | 1.6           |
| `body-small` | 14px   | 400   | 1.5           |
| `caption`    | 12px   | 400   | 1.4           |

---

## 7. Паттерны

### Server Components по умолчанию

Все компоненты — React Server Components. Клиентская логика выделяется
явно через директиву `'use client'`:

```tsx
// По умолчанию — серверный компонент
export default function ProfilePage() {
  // Можно напрямую вызывать async-функции (БД, API)
  const profile = await getProfile(id);
  return <ProfileForm initialData={profile} />;
}
```

Клиентские компоненты — только для:
- Интерактивности (кнопки, формы, тогглы)
- Хуков состояния (`useState`, `useEffect`)
- Browser API (геолокация, localStorage)
- Сторонних клиентских библиотек (Recharts, framer-motion)

### Suspense-границы для useSearchParams

Next.js App Router требует `Suspense`-обёртку для компонентов,
использующих `useSearchParams()`:

```tsx
"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

function FilterContent() {
  const searchParams = useSearchParams();
  const element = searchParams.get("element");
  // ...
}

export function ElementFilter() {
  return (
    <Suspense fallback={<Skeleton className="h-10 w-48" />}>
      <FilterContent />
    </Suspense>
  );
}
```

### Fallback-паттерны

| Сценарий          | Fallback                  |
|-------------------|---------------------------|
| Данные загружаются| `<Skeleton />`            |
| Ошибка загрузки   | `<Alert variant="error">` |
| Пустой результат  | Пустое состояние с CTA    |

### Файловая структура

```
src/components/
├── ui/                  # Базовые UI-компоненты (shadcn/ui)
│   ├── button.tsx
│   ├── card.tsx
│   ├── input.tsx
│   └── skeleton.tsx
├── layout/              # Структурные компоненты
│   ├── header.tsx
│   ├── sidebar.tsx
│   └── footer.tsx
├── chart/               # (планируется) Натальная карта
│   ├── natal-chart.tsx
│   ├── planet-card.tsx
│   ├── aspect-table.tsx
│   ├── element-wheel.tsx
│   └── profile-form.tsx
└── report/              # (планируется) Отчёты
    ├── claim-card.tsx
    ├── archetype-portrait.tsx
    └── full-report.tsx
```

### Именование

- Файлы: `kebab-case.tsx`
- Компоненты: `PascalCase`
- Пропсы: `ComponentNameProps`
- Экспорт: именованный (`export function Button`) или default для страниц
