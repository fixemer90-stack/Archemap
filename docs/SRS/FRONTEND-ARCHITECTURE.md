# Archemap — Архитектура фронтенда

## Содержание

1. [Обзор](#1-обзор)
2. [Стек технологий](#2-стек-технологий)
3. [Структура проекта](#3-структура-проекта)
4. [Роутинг](#4-роутинг)
5. [Управление состоянием](#5-управление-состоянием)
6. [API-интеграция](#6-api-интеграция)
7. [Дизайн-система](#7-дизайн-система)
8. [Конвенции](#8-конвенции)

---

## 1. Обзор

Archemap — астрологическая платформа, предоставляющая пользователям натальные карты, совместимость, транзиты и персональные прогнозы. Фронтенд построен как одностраничное приложение на базе Next.js с серверным рендерингом.

### Принципы

- **Server-first** — компоненты по умолчанию серверные; `'use client'` добавляется только при необходимости (интерактивность, хуки, контекст).
- **Минимализм зависимостей** — каждый пакет оправдан; не используются тяжёлые UI-фреймворки поверх shadcn/ui.
- **Типобезопасность** — строгий TypeScript без `any`, общие типы в `types/`, API-ответы типизированы насквозь.
- **Мобильный приоритет (mobile-first)** — все компоненты проектируются для 320px и расширяются через Tailwind breakpoints.
- **Производительность** — lazy-загрузка тяжёлых модулей (натальные карты, библиотеки расчётов), ISR/SSG где возможно.
- **Доступность** — соблюдение WCAG 2.1 AA: семантический HTML, ARIA-атрибуты, фокус-менеджмент.

---

## 2. Стек технологий

| Технология | Версия | Назначение |
|---|---|---|
| Next.js | 15 (App Router) | Фреймворк, роутинг, SSR/SSG, API-proxy |
| React | 19 | UI-библиотека, Server Components |
| TypeScript | 5.x | Статическая типизация |
| Tailwind CSS | 4 | Утилитарный CSS, дизайн-токены |
| shadcn/ui | latest | Переиспользуемые UI-компоненты (Radix + Tailwind) |
| Zustand | 5.x | Клиентское состояние (auth, UI) |
| TanStack Query | 5.x | Серверное состояние, кеширование, мутации |
| next-themes | latest | Переключение темы (dark/light) |
| Zod | 3.x | Валидация форм и API-ответов |

### devDependencies

| Пакет | Назначение |
|---|---|
| ESLint + eslint-config-next | Линтинг |
| Prettier | Форматирование |
| Husky + lint-staged | Pre-commit хуки |

---

## 3. Структура проекта

```
frontend/src/
├── app/                            # Next.js App Router — роуты и layouts
│   ├── layout.tsx                  # Корневой layout: шрифт Inter, ThemeProvider, QueryProvider
│   ├── page.tsx                    # Лендинг-страница (/)
│   ├── globals.css                 # Глобальные стили, CSS-переменные дизайн-токенов
│   ├── (auth)/                     # Route group — авторизация (без общего sidebar)
│   │   ├── layout.tsx              # Layout для auth-страниц (центрированная карточка)
│   │   ├── login/page.tsx          # Вход
│   │   ├── register/page.tsx       # Регистрация
│   │   ├── verify/page.tsx         # Подтверждение email
│   │   └── auth/callback/page.tsx  # OAuth callback (Google и др.)
│   └── (dashboard)/                # Route group — авторизованная зона
│       ├── layout.tsx              # Sidebar + Header + main area
│       ├── dashboard/page.tsx      # Главная панель (сводка, транзиты)
│       ├── settings/page.tsx       # Настройки профиля
│       ├── billing/page.tsx        # Управление подпиской, оплата
│       └── subscriptions/page.tsx  # История подписок и платежей
├── components/
│   ├── layout/                     # Компоненты раскладки
│   │   ├── header.tsx              # Верхняя навигация (аватар, уведомления)
│   │   ├── sidebar.tsx             # Боковая навигация (Collapsible)
│   │   └── footer.tsx              # Подвал (лендинг)
│   └── ui/                         # Базовые UI-компоненты (shadcn/ui)
│       ├── button.tsx
│       ├── card.tsx
│       ├── input.tsx
│       └── skeleton.tsx
├── hooks/                          # Переиспользуемые хуки
│   ├── use-api.ts                  # useApiQuery / useApiMutation (обёртки над TanStack Query)
│   └── use-auth.ts                 # useAuth — удобный доступ к auth-store
├── lib/                            # Утилиты и конфигурация
│   ├── api-client.ts               # Axios/fetch-инстанс с interceptors
│   ├── cookies.ts                  # Работа с httpOnly cookies (серверная сторона)
│   └── utils.ts                    # cn(), форматирование дат и пр.
├── providers/                      # React Context Providers
│   ├── query-provider.tsx          # QueryClientProvider с дефолтными опциями
│   └── theme-provider.tsx          # ThemeProvider (next-themes)
├── stores/                         # Zustand stores
│   ├── auth-store.ts               # user, token, isAuthenticated, login/logout
│   └── ui-store.ts                 # sidebarOpen, theme
└── types/                          # Общие TypeScript-типы
    ├── api.ts                      # ApiResponse<T>, PaginatedResponse<T>
    ├── user.ts                     # User, UserProfile
    ├── chart.ts                    # NatalChart, Transit, Aspect
    └── subscription.ts             # Plan, Subscription, Invoice
```

### Назначение директорий

| Директория | Ответственность |
|---|---|
| `app/` | Страницы, layouts, route groups. Только компоненты верхнего уровня. |
| `components/layout/` | Структурные компоненты (header, sidebar, footer). |
| `components/ui/` | Атомарные UI-компоненты из shadcn/ui. Не содержат бизнес-логики. |
| `hooks/` | Переиспользуемые хуки. Не содержат JSX. |
| `lib/` | Утилиты без React-зависимостей (API-клиент, форматирование). |
| `providers/` | Context Providers, оборачивающие приложение в `layout.tsx`. |
| `stores/` | Zustand stores для клиентского состояния. |
| `types/` | Глобальные типы, используемые в нескольких модулях. |

---

## 4. Роутинг

### Route Groups

Next.js App Router использует **route groups** — папки в скобках `(groupName)` не влияют на URL, но позволяют задать общий layout.

#### `(auth)` — `/login`, `/register`, `/verify`, `/auth/callback`

```
(app)/
├── layout.tsx    →  Центрированная карточка, без sidebar
├── login/page.tsx
├── register/page.tsx
├── verify/page.tsx
└── auth/callback/page.tsx
```

- Layout: минималистичный, без навигации. Logo сверху, форма по центру.
- Гостевой доступ: если пользователь авторизован — redirect на `/dashboard`.

#### `(dashboard)` — `/dashboard`, `/settings`, `/billing`, `/subscriptions`

```
(dashboard)/
├── layout.tsx    →  Sidebar + Header + <main>{children}</main>
├── dashboard/page.tsx
├── settings/page.tsx
├── billing/page.tsx
└── subscriptions/page.tsx
```

- Layout: полноценная оболочка с `Sidebar` слева и `Header` сверху.
- Protected: если пользователь не авторизован — redirect на `/login`.
- Sidebar управляется через `ui-store.sidebarOpen` (collapsible на мобильных).

### Middleware

`middleware.ts` на корневом уровне проверяет наличие auth-токена и перенаправляет:

```
Неавторизованный → /login  (для /dashboard/*)
Авторизованный   → /dashboard (для /login, /register)
```

---

## 5. Управление состоянием

### Zustand — клиентское состояние

Zustand используется для состояния, которое не приходит с сервера и не требует кеширования.

#### `auth-store`

```typescript
interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean

  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  setUser: (user: User) => void
  setTokens: (accessToken: string, refreshToken: string) => void
}
```

- Токены хранятся в httpOnly cookies (серверная запись), в store — только для клиентской логики.
- `isAuthenticated` — computed из наличия `user`.
- `logout` — очищает store + удаляет cookies через API.

#### `ui-store`

```typescript
interface UIState {
  sidebarOpen: boolean
  theme: 'dark' | 'light' | 'system'

  toggleSidebar: () => void
  setTheme: (theme: 'dark' | 'light' | 'system') => void
}
```

### TanStack Query — серверное состояние

Все данные с бэкенда управляются через TanStack Query. Прямые fetch-вызовы в компонентах запрещены.

**Конфигурация QueryClient (query-provider.tsx):**

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,       // 5 минут
      gcTime: 10 * 60 * 1000,          // 10 минут (бывший cacheTime)
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
})
```

**Паттерн:**

```typescript
// Запросы — через useApiQuery
const { data: chart, isLoading } = useApiQuery(
  ['natal-chart', userId],
  () => apiClient.get(`/api/v1/charts/${userId}`)
)

// Мутации — через useApiMutation
const updateProfile = useApiMutation(
  (data: UpdateProfileDTO) => apiClient.patch('/api/v1/users/me', data),
  { onSuccess: () => queryClient.invalidateQueries({ queryKey: ['user'] }) }
)
```

---

## 6. API-интеграция

### API-клиент (`lib/api-client.ts`)

Базовый HTTP-клиент (на `fetch` или `axios`) с:

- **Base URL** — относительные пути `/api/v1/*`
- **Authorization header** — автоматическая подстановка Bearer-токена из cookies
- **Interceptors** — обработка 401 (redirect на login), 403, 500
- **Типизация** — generic-методы `get<T>`, `post<T>`, `patch<T>`, `delete<T>`

### Next.js Rewrites (proxy)

Все запросы к `/api/v1/*` проксируются на бэкенд через `next.config.js`:

```javascript
// next.config.js
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${process.env.BACKEND_URL}/api/v1/:path*`,
      },
    ]
  },
}
```

Преимущества:
- Нет CORS-проблем (Same-Origin).
- Единая точка входа для API.
- Можно добавить rate-limiting на уровне Next.js middleware.

### Хуки API (`hooks/use-api.ts`)

Тонкие обёртки над TanStack Query:

```typescript
export function useApiQuery<T>(
  key: QueryKey,
  fetcher: () => Promise<T>,
  options?: UseQueryOptions<T>
) {
  return useQuery({ queryKey: key, queryFn: fetcher, ...options })
}

export function useApiMutation<TData, TVariables>(
  mutator: (variables: TVariables) => Promise<TData>,
  options?: UseMutationOptions<TData, Error, TVariables>
) {
  return useMutation({ mutationFn: mutator, ...options })
}
```

---

## 7. Дизайн-система

### Цветовые токены

Все цвета задаются как CSS-переменные в `globals.css` и мапятся в Tailwind через `tailwind.config`.

#### Основная палитра

| Токен | Назначение | Значение |
|---|---|---|
| `--deep-space` | Основной фон (dark) | `#17142A` |
| `--royal-violet` | Первичный акцент | `#5B3FD6` |
| `--soft-gold` | Премиум-акцент | `#D8B45A` |
| `--moon-silver` | Вторичный текст | `#D8DCE8` |
| `--mist-blue` | Интерактивные элементы (hover, link) | `#8DA8FF` |
| `--warm-ivory` | Основной текст | `#F6F1E8` |

#### Вертикальные акценты

Каждая вертикаль (раздел приложения) имеет свой цветовой акцент:

| Вертикаль | Цвет | Применение |
|---|---|---|
| **Я (Self)** | Violet `#5B3FD6` + Gold `#D8B45A` | Натальная карта, профиль |
| **Любовь (Love)** | `#B84A6B` | Совместимость, отношения |
| **Ребёнок (Child)** | `#6BAFBD` | Детские карты |
| **Карьера (Career)** | `#C28A2E` | Профессиональная астрология |

### Типографика

| Элемент | Шрифт | Размер | Вес |
|---|---|---|---|
| Заголовки (h1–h3) | Cormorant Garamond | 32–48px / 24–32px | 600–700 |
| Тело текста | Inter | 16px | 400 |
| Мелкий текст | Inter | 14px | 400 |
| Кнопки / Labels | Inter | 14px | 500–600 |

Подключение в `layout.tsx`:
```typescript
import { Cormorant_Garamond, Inter } from 'next/font/google'

const cormorant = Cormorant_Garamond({ subsets: ['latin', 'cyrillic'], variable: '--font-heading' })
const inter = Inter({ subsets: ['latin', 'cyrillic'], variable: '--font-body' })
```

### Tailwind-токены

Цвета пробрасываются в Tailwind через кастомную тему:

```javascript
// tailwind.config.js (фрагмент)
theme: {
  extend: {
    colors: {
      'deep-space': 'var(--deep-space)',
      'royal-violet': 'var(--royal-violet)',
      'soft-gold': 'var(--soft-gold)',
      'moon-silver': 'var(--moon-silver)',
      'mist-blue': 'var(--mist-blue)',
      'warm-ivory': 'var(--warm-ivory)',
    },
    fontFamily: {
      heading: ['var(--font-heading)', 'serif'],
      body: ['var(--font-body)', 'sans-serif'],
    },
  },
}
```

### Семантические цвета

Вместо хардкода hex-значений используются семантические токены:

| Семантика | Dark mode | Light mode |
|---|---|---|
| `background` | `--deep-space` | `--warm-ivory` |
| `foreground` | `--warm-ivory` | `--deep-space` |
| `primary` | `--royal-violet` | `--royal-violet` |
| `primary-foreground` | `--warm-ivory` | `--warm-ivory` |
| `secondary` | `--moon-silver` | `--deep-space` |
| `muted` | `#2A2545` | `#E8E4DC` |
| `accent` | `--mist-blue` | `--mist-blue` |

---

## 8. Конвенции

### Компоненты

- **Server Components по умолчанию.** Все компоненты в `app/` и `components/` — серверные, пока не потребуется клиентский код.
- **`'use client'` только при необходимости:** формы, хуки (useState, useEffect, useContext), обработчики событий, браузерные API.
- **Именование:** PascalCase для файлов компонентов (`NatalChart.tsx`), kebab-case для route-папок (`dashboard/`).
- **Экспорт:** default export для page-компонентов, именованный export для переиспользуемых компонентов.
- **Размер:** один компонент — одна ответственность. Если файл > 200 строк — разбить.

### Стили

- **Tailwind CSS** — единственный способ стилизации. Inline-styles и CSS-модули не используются (кроме `globals.css`).
- **`cn()` утилита** — для условного объединения классов (clsx + tailwind-merge).
- **Семантические цвета** — никогда не писать `bg-[#5B3FD6]`, только `bg-primary` или `bg-royal-violet`.
- **Mobile-first** — стили по умолчанию для мобильных, расширение через `md:`, `lg:`, `xl:`.

### Формы

- **Zod-схемы** для валидации на клиенте и сервере.
- **React Hook Form** (если подключён) или контролируемые компоненты.
- Ошибки валидации отображаются под полями, не через alert.

### Код

- **TypeScript strict mode** — нет `any`, нет неявных `undefined`.
- **Импорты:** абсолютные пути через `@/` (alias в `tsconfig.json`).
- **Порядок импортов:** React → внешние библиотеки → внутренние модули → типы → стили.
- **Комментарии:** на русском языке для бизнес-логики, на английском для технических пояснений.

### Git

- Ветки: `feature/`, `fix/`, `refactor/`, `docs/`.
- Commits: Conventional Commits (`feat:`, `fix:`, `chore:`).
- Pre-commit: lint-staged запускает ESLint + Prettier на staged-файлах.

---

## Приложение A: Пример структуры защищённой страницы

```typescript
// app/(dashboard)/dashboard/page.tsx
import { Metadata } from 'next'
import { redirect } from 'next/navigation'
import { getServerSession } from '@/lib/auth'
import { DashboardContent } from '@/components/dashboard/dashboard-content'

export const metadata: Metadata = {
  title: 'Панель управления — Archemap',
}

export default async function DashboardPage() {
  const session = await getServerSession()

  if (!session) {
    redirect('/login')
  }

  return <DashboardContent user={session.user} />
}
```

```typescript
// components/dashboard/dashboard-content.tsx
'use client'

import { useApiQuery } from '@/hooks/use-api'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function DashboardContent({ user }) {
  const { data: transits, isLoading } = useApiQuery(
    ['transits', user.id],
    () => apiClient.get(`/api/v1/charts/${user.id}/transits`)
  )

  if (isLoading) return <Skeleton className="h-64 w-full" />

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {/* Карточки транзитов */}
    </div>
  )
}
```

---

## Приложение B: Карта потока данных

```
┌─────────────────────────────────────────────────┐
│                    Browser                       │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Pages   │  │ Components│  │   Hooks      │  │
│  │ (app/)   │──│(layout/ui)│──│(use-api,     │  │
│  │          │  │          │  │ use-auth)     │  │
│  └──────────┘  └──────────┘  └──────┬───────┘  │
│                                      │           │
│  ┌──────────────────────────────────┐│           │
│  │        Zustand Stores           ││           │
│  │  auth-store  │  ui-store        ││           │
│  └──────────────────────────────────┘│           │
│                                      │           │
│  ┌──────────────────────────────────┐│           │
│  │      TanStack Query Cache       ││           │
│  │  queries / mutations / invalid. ││           │
│  └──────────────────────────────────┘│           │
│                                      │           │
│  ┌──────────────────────────────────┐│           │
│  │         API Client              │◄┘          │
│  │  fetch/axios + interceptors      │            │
│  └───────────────┬──────────────────┘            │
└──────────────────┼──────────────────────────────┘
                   │ /api/v1/*
                   ▼
┌──────────────────────────────────────────────────┐
│           Next.js rewrites (proxy)                │
│           /api/v1/* → BACKEND_URL/api/v1/*       │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│              Backend (FastAPI)                     │
│              /api/v1/*                            │
└──────────────────────────────────────────────────┘
```
