# SRS: Frontend — Archemap Web Application

**Версия:** 1.0
**Дата:** 2026-05-30
**Статус:** In Progress
**Автор:** Archemap Team

---

## 1. Введение

### 1.1 Назначение

Документ описывает программные требования к frontend-приложению Archemap — веб-интерфейсу для пользователей и администраторов. Приложение обеспечивает ввод натальных данных, просмотр карт, чтение отчётов, управление подписками и аккаунтом.

### 1.2 Область применения

Frontend — это клиентский слой платформы, взаимодействующий с backend API:

```
Пользователь  →  Frontend (Next.js)  →  Backend API (FastAPI)
                     │
                     ├── Аутентификация (login/register/OAuth)
                     ├── Профили (создание/редактирование)
                     ├── Карты (вычисление/просмотр)
                     ├── Отчёты (чтение/PDF)
                     ├── Подписки (оплата/управление)
                     └── Настройки (аккаунт/тема)
```

### 1.3 Определения

| Термин | Определение |
|---|---|
| **RSC** | React Server Component — компонент, рендерящийся на сервере |
| **RCC** | React Client Component — компонент с `'use client'`, рендерящийся в браузере |
| **App Router** | Система маршрутизации Next.js 15 (file-based) |
| **Route Group** | Логическая группа маршрутов `(auth)`, `(dashboard)` без влияния на URL |
| **shadcn/ui** | Коллекция переиспользуемых UI-компонентов на Radix + Tailwind |
| **Zustand** | Лёгкий state manager для клиентского состояния |
| **TanStack Query** | Библиотека для управления серверным состоянием (кэш, мутации) |

### 1.4 Ссылки

| Документ | Путь |
|---|---|
| Frontend Architecture | `docs/FRONTEND-ARCHITECTURE.md` |
| Component Library | `docs/COMPONENT-LIBRARY.md` |
| Design Code | `docs/archemap_design_code.md` |
| Backend SRS E3 | `docs/SRS-E3-chart-engine.md` |
| Backend SRS E4 | `docs/SRS-E4-rules-content.md` |
| MVP Status | `docs/MVP-STATUS.md` |

---

## 2. Общее описание

### 2.1 Перспектива продукта

Frontend не содержит бизнес-логики. Вся логика — на backend. Frontend отвечает за:
- UX: ввод данных, навигация, визуализация
- Presentation: рендеринг карт, отчётов, профилей
- State: клиентское состояние (auth, UI) + серверное (кэш API)

### 2.2 Пользовательские роли

| Роль | Описание | Доступ |
|---|---|---|
| **Guest** | Неаутентифицированный посетитель | Landing, login, register |
| **User** | Зарегистрированный пользователь | Dashboard, profiles, charts, reports |
| **Subscriber** | Пользователь с активной подпиской | Full reports, PDF, history |
| **Admin** | Администратор | Admin panel, CMS, user management |

### 2.3 Ограничения

| Ограничение | Описание |
|---|---|
| **C1** | SSR-first: Server Components по умолчанию |
| **C2** | `'use client'` только когда нужен доступ к browser API или React hooks |
| **C3** | Нет хранения sensetive данных в localStorage (только httpOnly cookies) |
| **C4** | Mobile-first responsive design |
| **C5** | Нет прямых вызовов к внешним API — всё через backend proxy |

---

## 3. Функциональные требования

### 3.1 Аутентификация (FR-F.1)

**FR-F.1.1** Система ДОЛЖНА предоставлять страницу входа по email/password.

**FR-F.1.2** Система ДОЛЖНА предоставлять страницу регистрации.

**FR-F.1.3** Система ДОЛЖНА поддерживать OAuth callback (Yandex, VK).

**FR-F.1.4** Система ДОЛЖНА хранить JWT токены в httpOnly cookies.

**FR-F.1.5** Система ДОЛЖНА автоматически перенаправлять на login при истёкшем токене.

**FR-F.1.6** Система ДОЛЖНА предоставлять страницу верификации email.

### 3.2 Профили (FR-F.2)

**FR-F.2.1** Система ДОЛЖНА предоставлять форму создания профиля рождения:
- Имя (текст, 1-120 символов)
- Дата рождения (date picker, 1900-2100)
- Время рождения (time picker, optional)
- Точность времени (exact/approximate/unknown)
- Место рождения (текст с autocomplete через geocode API)

**FR-F.2.2** Система ДОЛЖНА автозаполнять координаты и timezone при выборе места.

**FR-F.2.3** Система ДОЛЖНА предоставлять список профилей пользователя.

**FR-F.2.4** Система ДОЛЖНА позволять редактирование профиля.

**FR-F.2.5** Система ДОЛЖНА позволять удаление профиля.

### 3.3 Карты (FR-F.3)

**FR-F.3.1** Система ДОЛЖНА предоставлять страницу вычисления натальной карты.

**FR-F.3.2** Система ДОЛЖНА отображать позиции планет (знак, градус, дом, ретроградность).

**FR-F.3.3** Система ДОЛЖНА отображать дома (номер, знак, кусп).

**FR-F.3.4** Система ДОЛЖНА отображать аспекты (тип, орб, applying/separating).

**FR-F.3.5** Система ДОЛЖНА визуализировать распределение стихий (fire/earth/air/water).

**FR-F.3.6** Система ДОЛЖНА визуализировать распределение модальностей (cardinal/fixed/mutable).

**FR-F.3.7** Система ДОЛЖНА предоставлять SVG-визуализацию натальной карты (колесо).

### 3.4 Отчёты (FR-F.4, planned)

**FR-F.4.1** Система ДОЛЖНА отображать preview-отчёт (free tier: 2-3 claim'а).

**FR-F.4.2** Система ДОЛЖНА отображать полный отчёт (paid tier: все claim'ы + evidence).

**FR-F.4.3** Система ДОЛЖНА отображать архетипический портрет с score и confidence.

**FR-F.4.4** Система ДОЛЖНА предоставлять evidence trail для каждого claim'а.

**FR-F.4.5** Система ДОЛЖНА позволять скачивание PDF.

### 3.5 Подписки (FR-F.5, planned)

**FR-F.5.1** Система ДОЛЖНА отображать каталог планов.

**FR-F.5.2** Система ДОЛЖНА инициировать checkout через PSP.

**FR-F.5.3** Система ДОЛЖНА отображать статус подписки.

**FR-F.5.4** Система ДОЛЖНА позволять отмену подписки.

### 3.6 Настройки (FR-F.6)

**FR-F.6.1** Система ДОЛЖНА предоставлять страницу настроек аккаунта.

**FR-F.6.2** Система ДОЛЖНА позволять смену темы (light/dark/system).

**FR-F.6.3** Система ДОЛЖНА позволять выход из аккаунта.

---

## 4. Нефункциональные требования

### 4.1 Производительность

| Требование | Значение |
|---|---|
| **NFR-F.4.1.1** | First Contentful Paint < 1.5 сек |
| **NFR-F.4.1.2** | Largest Contentful Paint < 2.5 сек |
| **NFR-F.4.1.3** | Cumulative Layout Shift < 0.1 |
| **NFR-F.4.1.4** | Bundle size < 200KB (gzipped, excluding node_modules) |

### 4.2 Доступность

| Требование | Значение |
|---|---|
| **NFR-F.4.2.1** | WCAG 2.1 AA compliance |
| **NFR-F.4.2.2** | Keyboard navigation для всех интерактивных элементов |
| **NFR-F.4.2.3** | Screen reader support (ARIA labels) |
| **NFR-F.4.2.4** | Color contrast ratio ≥ 4.5:1 для текста |

### 4.3 Адаптивность

| Требование | Значение |
|---|---|
| **NFR-F.4.3.1** | Mobile: 320px - 767px |
| **NFR-F.4.3.2** | Tablet: 768px - 1023px |
| **NFR-F.4.3.3** | Desktop: 1024px+ |

### 4.4 Безопасность

| Требование | Значение |
|---|---|
| **NFR-F.4.4.1** | JWT в httpOnly cookies (не localStorage) |
| **NFR-F.4.4.2** | CSRF protection через SameSite cookies |
| **NFR-F.4.4.3** | XSS prevention: React auto-escaping + CSP headers |
| **NFR-F.4.4.4** | Нет sensetive данных в client-side state |

---

## 5. Роутинг

### 5.1 Карта маршрутов

| Route Group | URL | Страница | Авторизация |
|---|---|---|---|
| — | `/` | Landing page | Нет |
| `(auth)` | `/login` | Вход | Нет |
| `(auth)` | `/register` | Регистрация | Нет |
| `(auth)` | `/verify` | Верификация email | Нет |
| `(auth)` | `/auth/callback` | OAuth callback | Нет |
| `(dashboard)` | `/dashboard` | Dashboard | Да |
| `(dashboard)` | `/profiles` | Профили (planned) | Да |
| `(dashboard)` | `/profiles/[id]` | Профиль (planned) | Да |
| `(dashboard)` | `/profiles/[id]/chart` | Карта (planned) | Да |
| `(dashboard)` | `/reports` | Отчёты (planned) | Да |
| `(dashboard)` | `/settings` | Настройки | Да |
| `(dashboard)` | `/billing` | Биллинг | Да |
| `(dashboard)` | `/subscriptions` | Подписки | Да |
| — | `/admin` | Admin panel (planned) | Admin |

### 5.2 Layouts

**Root Layout** (`app/layout.tsx`):
- Inter font
- ThemeProvider (dark/light/system)
- QueryProvider (TanStack Query)

**Auth Layout** (`app/(auth)/layout.tsx`):
- Centered card layout
- No sidebar/header

**Dashboard Layout** (`app/(dashboard)/layout.tsx`):
- Sidebar (навигация)
- Header (user menu, theme toggle)
- Main content area

---

## 6. State Management

### 6.1 Клиентское состояние (Zustand)

**auth-store:**
```typescript
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
  setUser: (user: User) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
}
```

**ui-store:**
```typescript
interface UIState {
  sidebarOpen: boolean;
  theme: "light" | "dark" | "system";
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: "light" | "dark" | "system") => void;
}
```

### 6.2 Серверное состояние (TanStack Query)

**useApiQuery<T>** — GET запросы с кэшированием:
```typescript
const { data, isLoading, error } = useApiQuery<ProfileListResponse>(
  ["profiles"],
  "/api/v1/profiles"
);
```

**useApiMutation<T, V>** — POST/PUT/PATCH/DELETE:
const mutation = useApiMutation<ProfileResponse, CreateProfileRequest>(
  "/api/v1/profiles",
  "POST"
);

---

## 7. API Integration

### 7.1 Proxy

Next.js rewrites proxy `/api/*` → backend:

```typescript
// next.config.ts
rewrites: [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }]
```

### 7.2 API Client

Typed fetch wrapper с auto Bearer token injection:

```typescript
const api = {
  get: <T>(endpoint: string, token?: string) => apiClient<T>(endpoint, { token }),
  post: <T>(endpoint: string, body: unknown, token?: string) => ...,
  patch: <T>(endpoint: string, body: unknown, token?: string) => ...,
  delete: <T>(endpoint: string, token?: string) => ...,
};
```

### 7.3 Endpoints mapping

| Frontend Hook | Backend Endpoint | Описание |
|---|---|---|
| `useApiQuery(["profiles"])` | `GET /api/v1/profiles` | Список профилей |
| `useMutation("/api/v1/profiles")` | `POST /api/v1/profiles` | Создать профиль |
| `useMutation("/api/v1/profiles/{id}/chart")` | `POST /api/v1/profiles/{id}/chart` | Вычислить карту |
| `useApiQuery(["geocode", q])` | `GET /api/v1/profiles/geocode?q=` | Геокодинг |
| `useMutation("/api/v1/auth/login")` | `POST /api/v1/auth/login` | Вход |
| `useMutation("/api/v1/auth/register")` | `POST /api/v1/auth/register` | Регистрация |

---

## 8. Дизайн-система

### 8.1 Цвета

| Токен | HEX | Назначение |
|---|---|---|
| `--background` | `#17142A` | Deep Space — основной фон |
| `--primary` | `#5B3FD6` | Royal Violet — CTA, активные элементы |
| `--accent` | `#D8B45A` | Soft Gold — премиальные акценты |
| `--muted` | `#D8DCE8` | Moon Silver — вторичный текст |
| `--interactive` | `#8DA8FF` | Mist Blue — ссылки, hover |
| `--foreground` | `#F6F1E8` | Warm Ivory — основной текст |

### 8.2 Вертикальные акценты

| Вертикаль | Цвет | HEX |
|---|---|---|
| Self | Violet + Gold | `#5B3FD6` / `#D8B45A` |
| Love | Rose-burgundy | `#B84A6B` |
| Child | Soft blue/mint | `#6BAFBD` |
| Career | Amber/steel | `#C28A2E` |

### 8.3 Типографика

| Элемент | Шрифт | Размер |
|---|---|---|
| H1 | Cormorant Garamond | 2.5rem |
| H2 | Cormorant Garamond | 2rem |
| H3 | Cormorant Garamond | 1.5rem |
| Body | Inter | 1rem |
| Small | Inter | 0.875rem |

### 8.4 UI-паттерны

- Border radius: 16-24px
- Cards: semi-transparent, glass-like, backdrop-filter: blur(16px)
- Background: radial-gradient(circle at top, rgba(91,63,214,0.35), transparent 40%)
- Primary button: linear-gradient(135deg, #5B3FD6, #D8B45A)
- Charts: radial, axis-based (не pie charts)
- Icons: line icons + celestial geometry

---

## 9. Тестирование

| Тип | Фреймворк | Покрытие |
|---|---|---|
| Unit | Vitest | Компоненты, хуки, stores |
| E2E | Playwright | Critical user flows |
| Visual | Storybook (planned) | Component states |

---

## 10. Критерии верификации

### 10.1 Quality Gates

| Проверка | Статус |
|---|---|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npx eslint .` | ✅ 0 errors |
| `npx prettier --check .` | ✅ 0 files |
| `npm run build` | ✅ success |
| CI (GitHub Actions) | ✅ all green |
