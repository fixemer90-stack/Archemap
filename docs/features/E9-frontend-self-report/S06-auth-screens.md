# Story E9.S06: Auth Screens

**Feature:** [Frontend Self Report](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Экраны авторизации: логин, регистрация с полными данными рождения, OAuth через Яндекс. Это точка входа в продукт — первый экран, который видит пользователь.

Регистрация собирает всё для немедленного обсчёта натальной карты: email, password, дата рождения, время (3 категории), место (с геокодингом), координаты, timezone.

## Что сделать

### 1. Login Page (`app/(auth)/login/page.tsx`)

- Email + password поля
- Кнопка "Войти"
- Ссылка "Забыли пароль?" → `/forgot-password`
- Ссылка "Нет аккаунта? Зарегистрироваться" → `/register`
- Кнопка "Войти через Яндекс" (OAuth)
- Loading state при submit
- Error state: неверный email/password, email не подтверждён

### 2. Register Page (`app/(auth)/register/page.tsx`)

**Шаг 1: Credentials**
- Email (валидация: формат, уникальность)
- Password (мин 8 символов, индикатор силы)
- Подтверждение password

**Шаг 2: Birth Data**
- Дата рождения (date picker, не в будущем, не раньше 1900)
- Время рождения (time picker + 3 radio):
  - `exact` — "Точно знаю" → показать time picker
  - `approximate` — "Примерно" → показать time picker
  - `unknown` — "Не знаю" → ставить 12:00 автоматически
- Место рождения (autocomplete через `/api/v1/profiles/geocode`):
  - Debounce 300ms
  - Dropdown с результатами: город, регион, страна
  - При выборе → latitude, longitude, timezone
  - Если timezone не определился → показать select

**Шаг 3: Подтверждение**
- Сводка введённых данных
- Кнопка "Зарегистрироваться"
- Ссылка на политику конфиденциальности

### 3. OAuth Callback (`app/(auth)/callback/page.tsx`)

- Обработка редиректа от Яндекса
- Парсинг query params: `access_token`, `refresh_token`, `birth_date`, `needs_profile`
- Если `needs_profile=true` → redirect на `/register?step=2&birth_date=...`
- Если профиль есть → redirect на `/report`

### 4. Shared Components

- `AuthLayout` — layout с лого, центрированной формой, фоном
- `BirthTimeSelector` — radio group для выбора категории времени
- `PlaceAutocomplete` — input с dropdown для геокодинга
- `PasswordStrength` — индикатор силы пароля
- `OAuthButtons` — кнопки OAuth провайдеров

### 5. State Management

- Zustand store для формы регистрации (`stores/register-form-store.ts`)
- TanStack Query для API calls (login, register, geocode)
- URL state для multi-step формы (`?step=2`)

### 6. Validation

- Client-side: react-hook-form + zod schema
- Server-side: FastAPI валидация (уже есть)
- Real-time валидация email (debounced uniqueness check)
- Password: мин 8 символов, индикатор силы

## Затрагиваемые файлы

```
frontend/src/
├── app/
│   └── (auth)/
│       ├── layout.tsx              # AuthLayout
│       ├── login/
│       │   └── page.tsx            # Login page
│       ├── register/
│       │   └── page.tsx            # Register page (multi-step)
│       ├── callback/
│       │   └── page.tsx            # OAuth callback handler
│       └── forgot-password/
│           └── page.tsx            # Password reset request
├── components/
│   ├── auth/
│   │   ├── birth-time-selector.tsx # Radio: exact/approximate/unknown
│   │   ├── place-autocomplete.tsx  # Geocoding autocomplete
│   │   ├── password-strength.tsx   # Password strength indicator
│   │   └── oauth-buttons.tsx       # Yandex OAuth button
│   └── ui/                         # shadcn components (existing)
├── stores/
│   └── register-form-store.ts      # Zustand store for registration
├── lib/
│   ├── api/
│   │   ├── auth.ts                 # Login, register, OAuth API calls
│   │   └── geocode.ts              # Geocoding API calls
│   └── validators/
│       └── register.ts             # Zod schemas for registration
└── types/
    └── auth.ts                     # TypeScript interfaces
```

## Критерии приёмки

- [ ] Login page: email/password, error states, OAuth button
- [ ] Register page: 3-step form с birth data
- [ ] Birth time: 3 категории (exact/approximate/unknown)
- [ ] Place autocomplete: geocoding с debounce
- [ ] OAuth callback: обработка birth_date и needs_profile
- [ ] Responsive: работает на 320px, 768px, 1024px, 1440px
- [ ] Accessibility: keyboard navigation, ARIA labels, focus management
- [ ] Loading/error/empty states для всех форм
- [ ] Zod валидация на клиенте
- [ ] ruff, mypy, eslint — 0 ошибок

## Дизайн-система

- Цвета: semantic tokens из Tailwind (`text-primary`, `bg-surface`)
- Типографика: h1 → заголовок, body → текст, small → подсказки
- Spacing: стандартная шкала Tailwind (0.25rem increments)
- Без AI-эстетики: без purple gradients, без rounded-2xl, без stock card grids

## Примечания

- Geocoding через Nominatim (OpenStreetMap) — бесплатно, без API key
- Timezone определяется автоматически по координатам (timezonefinder)
- Если время неизвестно → 12:00, accuracy=unknown
- Multi-step форма: шаги через URL query param `?step=N`
- OAuth birthday предзаполнение: из query param `?birth_date=YYYY-MM-DD`
