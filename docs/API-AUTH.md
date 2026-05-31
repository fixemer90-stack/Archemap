# Auth API Documentation

## Регистрация

### POST /api/v1/auth/register

Обычная регистрация с email, паролем и данными рождения. Автоматически вычисляет натальную карту.

**Требуется:** нет (публичный endpoint)

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "birth_date": "1991-08-29",
  "birth_time": "14:30",
  "birth_time_accuracy": "exact",
  "birth_place": "Москва, Москва, Россия",
  "latitude": 55.752,
  "longitude": 37.6178,
  "timezone": "Europe/Moscow"
}
```

**Поля:**

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `email` | string | ✅ | Email пользователя |
| `password` | string | ✅ | Пароль (мин. 8 символов) |
| `birth_date` | string | ✅ | Дата рождения (YYYY-MM-DD) |
| `birth_time` | string | ❌ | Время рождения (HH:MM). Если null → 12:00 |
| `birth_time_accuracy` | string | ❌ | `exact`, `approximate`, `unknown` (по умолчанию) |
| `birth_place` | string | ✅ | Место рождения (из geocoding) |
| `latitude` | float | ✅ | Широта (-90..90) |
| `longitude` | float | ✅ | Долгота (-180..180) |
| `timezone` | string | ✅ | IANA таймзона (напр. `Europe/Moscow`) |

**Response 201:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "birth_date": "1991-08-29",
  "profile_id": "uuid",
  "access_token": "jwt...",
  "refresh_token": "jwt...",
  "token_type": "bearer",
  "chart": {
    "planets": [...],
    "houses": [...],
    "aspects": [...]
  },
  "socionics": {
    "top3": [
      {"type": "EIE", "name": "Наставник", "score": 0.835, "confidence": 0.637, "functions": "Fe+Ni", "model_a": 0.688}
    ]
  }
}
```

**Errors:**
- `409` — Email уже зарегистрирован
- `422` — Валидация (пароль < 8, пустые поля)

---

### POST /api/v1/auth/complete-profile

Завершение профиля для OAuth пользователей. Без email/пароля — авторизация через JWT.

**Требуется:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "birth_date": "1991-08-29",
  "birth_time": "14:30",
  "birth_time_accuracy": "exact",
  "birth_place": "Москва, Москва, Россия",
  "latitude": 55.752,
  "longitude": 37.6178,
  "timezone": "Europe/Moscow"
}
```

**Поля:**

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `birth_date` | string | ✅ | Дата рождения (YYYY-MM-DD) |
| `birth_time` | string | ❌ | Время рождения (HH:MM). Если null → 12:00 |
| `birth_time_accuracy` | string | ❌ | `exact`, `approximate`, `unknown` (по умолчанию) |
| `birth_place` | string | ✅ | Место рождения (из geocoding) |
| `latitude` | float | ✅ | Широта (-90..90) |
| `longitude` | float | ✅ | Долгота (-180..180) |
| `timezone` | string | ✅ | IANA таймзона (напр. `Europe/Moscow`) |

**Response 201:**
```json
{
  "profile_id": "uuid",
  "chart": {
    "planets": [...],
    "houses": [...],
    "aspects": [...]
  },
  "socionics": {
    "top3": [...]
  }
}
```

**Errors:**
- `401` — Не авторизован (нет/невалидный JWT)
- `400` — Профиль уже существует
- `422` — Валидация (пустые поля)

---

## Сравнение

| | `/register` | `/complete-profile` |
|---|---|---|
| **Email** | ✅ обязателен | ❌ не нужен |
| **Password** | ✅ обязателен | ❌ не нужен |
| **Auth** | Нет (публичный) | JWT Bearer token |
| **Возвращает** | tokens + chart | только chart |
| **Use case** | Новый пользователь | OAuth (Яндекс) |

---

## OAuth Flow (Яндекс)

```
1. GET /auth/oauth/yandex/start
   → Redirect на Яндекс

2. Яндекс → callback → GET /auth/oauth/yandex/callback
   → Backend получает email + birth_date
   → Создаёт пользователя (без пароля)
   → Redirect на фронтенд:
     /register?step=2&birth_date=1991-08-29&email=user@ya.ru

3. Фронтенд показывает форму (шаг 2):
   - Email предзаполнен
   - Дата рождения предзаполнена
   - Пользователь вводит: время, место

4. Submit → POST /auth/complete-profile (с JWT)
   → Создаёт PersonProfile
   → Вычисляет карту
   → Возвращает chart + socionics

5. Redirect на /report/{profile_id}
```

---

## Geocoding

### GET /api/v1/profiles/geocode?q=<query>

Поиск мест по названию. Возвращает координаты.

**Требуется:** нет (публичный)

**Query Params:**
- `q` — поисковый запрос (мин. 2 символа)

**Response 200:**
```json
{
  "items": [
    {
      "display_name": "Москва, Москва, Россия",
      "latitude": 55.752,
      "longitude": 37.6178,
      "city": "Москва",
      "country": "Россия"
    }
  ]
}
```

**Fallback:** Nominatim → Open-Meteo (если Nominatim недоступен)
