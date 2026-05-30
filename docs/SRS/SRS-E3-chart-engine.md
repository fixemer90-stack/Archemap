# SRS: E3 — Profile & Chart Engine

**Версия:** 1.0
**Дата:** 2026-05-30
**Статус:** Implemented
**Автор:** Archemap Team

---

## 1. Введение

### 1.1 Назначение

Документ описывает программные требования к модулю **Profile & Chart Engine** — вычислительному ядру платформы Archemap. Модуль отвечает за хранение натальных данных пользователя, вычисление астрологической карты и извлечение нормализованных признаков для последующей интерпретации rule engine.

### 1.2 Область применения

Модуль является фундаментом для четырёх продуктовых вертикалей:

| Вертикаль | Использование E3 |
|---|---|
| **Archemap Self** | Натальная карта + feature vector → интерпретация архетипа |
| **Archemap Love** | Две карты → синастрия, совместимость |
| **Archemap Child** | Карта ребёнка → профиль темперамента |
| **Archemap Career** | Карта → карьерные сильные стороны |

### 1.3 Определения и сокращения

| Термин | Определение |
|---|---|
| **PersonProfile** | Профиль с данными рождения (дата, время, место, координаты, TZ) |
| **ChartSnapshot** | Вычисленный снимок натальной карты (планеты, дома, аспекты) в JSON |
| **FeatureVector** | Нормализованный вектор признаков карты (значения 0.0-1.0) |
| **IANA TZ** | Часовой пояс по базе IANA (напр. `Europe/Moscow`) |
| **Moshier** | Встроенная эфемеридная модель Swiss Ephemeris (без внешних файлов) |
| **Placidus** | Система домов по умолчанию |

### 1.4 Ссылки

| Документ | Путь |
|---|---|
| Product Spec | `docs/SPEC.md` |
| Roadmap | `docs/ROADMAP.md` |
| Business Logic Spec | `docs/Спецификация бизнес-логики и доменных правил Archemap.md` |
| C4 Architecture | `docs/C4 архитектура SaaS-платформы Archemap.md` |
| Feature Stories | `docs/features/E3-chart-engine/` |

---

## 2. Общее описание

### 2.1 Перспектива продукта

E3 — это **middle layer** между вводом данных пользователя (E2: Identity) и интерпретацией (E4: Rules & Content). Не зависит от UI, не содержит бизнес-логики интерпретации, не взаимодействует с платёжными системами.

```
E2 (Identity)  →  E3 (Chart Engine)  →  E4 (Rules)  →  E5 (Reports)
  пользователь      натальная карта       интерпретация    отчёт
```

### 2.2 Функции продукта

| Функция | Описание | Story |
|---|---|---|
| **F3.1** | CRUD профилей рождения | S01 |
| **F3.2** | Геокодинг места рождения | S02 |
| **F3.3** | Определение часового пояса | S03 |
| **F3.4** | Вычисление позиций планет | S04 |
| **F3.5** | Вычисление домов (Placidus) | S04 |
| **F3.6** | Детекция аспектов | S04 |
| **F3.7** | Сохранение и кэширование карты | S05 |
| **F3.8** | Извлечение нормализованных признаков | S06 |

### 2.3 Ограничения

| Ограничение | Описание |
|---|---|
| **C1** | Эфемериды: Moshier (встроенный), точность ±0.01° для классических планет |
| **C2** | Chiron: недоступен без внешних эфемеридных файлов (`seas_18.se1`) |
| **C3** | Система домов: только Placidus (P) и Equal (E) |
| **C4** | Часовые пояса: offline-резолв через timezonefinder, без API |
| **C5** | Геокодинг: Nominatim (OSM), лимит 1 req/sec |

### 2.4 Предположения

- Пользователь аутентифицирован (E2)
- Координаты места рождения валидны (lat: -90..90, lon: -180..180)
- Часовой пояс — валидная IANA-строка
- Дата рождения в диапазоне 1900-2100

---

## 3. Функциональные требования

### 3.1 PersonProfile (FR-3.1)

**FR-3.1.1** Система ДОЛЖНА позволять создавать профиль с полями:
- `name` (строка, 1-120 символов)
- `birth_date` (дата, 1900-2100)
- `birth_time` (время, nullable)
- `birth_time_accuracy` (`exact` | `approximate` | `unknown`)
- `birth_place` (строка, 1-300 символов)
- `latitude` (float, -90..90)
- `longitude` (float, -180..180)
- `timezone` (IANA-строка, 1-60 символов)

**FR-3.1.2** Система ДОЛЖНА обеспечивать CRUD-операции для профилей.

**FR-3.1.3** Система ДОЛЖНА ограничивать доступ: пользователь видит только свои профили.

**FR-3.1.4** Система ДОЛЖНА валидировать год рождения (1900-2100).

**FR-3.1.5** Система ДОЛЖНА поддерживать partial update (PATCH) — изменение только переданных полей.

### 3.2 Геокодинг (FR-3.2)

**FR-3.2.1** Система ДОЛЖНА предоставлять поиск места по строке.

**FR-3.2.2** Результат ДОЛЖЕН содержать: `display_name`, `latitude`, `longitude`, `city`, `country`.

**FR-3.2.3** Результаты ДОЛЖНЫ кэшироваться в Redis на 24 часа.

**FR-3.2.4** При ошибке внешнего API система ДОЛЖНА возвращать пустой список (не crash).

### 3.3 Часовые пояса (FR-3.3)

**FR-3.3.1** Система ДОЛЖНА определять IANA timezone по координатам.

**FR-3.3.2** Резолв ДОЛЖЕН быть offline (без внешнего API).

**FR-3.3.3** Результаты ДОЛЖНЫ кэшироваться в Redis на 30 дней.

**FR-3.3.4** При ошибке Redis система ДОЛЖНА вычислять timezone без кэша.

### 3.4 Chart Engine (FR-3.4)

**FR-3.4.1** Система ДОЛЖНА вычислять позиции 11 планет/точек:
Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, North Node.

**FR-3.4.2** Для каждой планеты система ДОЛЖНА возвращать:
- ecliptic longitude (0-360°)
- ecliptic latitude
- speed (градусы/день, отрицательная = ретроградность)
- zodiac sign + degree within sign
- house number (1-12)

**FR-3.4.3** Система ДОЛЖНА вычислять 12 домов по системе Placidus.

**FR-3.4.4** Система ДОЛЖНА детектировать аспекты:
- conjunction (0°), sextile (60°), square (90°), trine (120°), quincunx (150°), opposition (180°)

**FR-3.4.5** Для каждого аспекта система ДОЛЖНА возвращать:
- planet_a, planet_b
- aspect_type, angle, orb
- is_applying (true/false)

**FR-3.4.6** Система ДОЛЖНА использовать Moshier эфемериды (встроенные).

**FR-3.4.7** Вычисление ДОЛЖНО быть детерминированным: одинаковый вход → одинаковый выход.

### 3.5 ChartSnapshot (FR-3.5)

**FR-3.5.1** Система ДОЛЖНА сохранять вычисленную карту как JSON в PostgreSQL.

**FR-3.5.2** Система ДОЛЖНА возвращать кэшированный снимок при повторном запросе (если engine_version не изменилась).

**FR-3.5.3** Система ДОЛЖНА поддерживать принудительный пересчёт (force_recompute=true).

**FR-3.5.4** Каждый снимок ДОЛЖЕН содержать `engine_version` для воспроизводимости.

### 3.6 Feature Extraction (FR-3.6)

**FR-3.6.1** Система ДОЛЖНА извлекать нормализованный FeatureVector со значениями 0.0-1.0.

**FR-3.6.2** FeatureVector ДОЛЖЕН содержать:
- Element distribution: fire, earth, air, water (сумма = 1.0)
- Modality distribution: cardinal, fixed, mutable (сумма = 1.0)
- House emphasis: нормализованные веса по домам
- Aspect counts: нормализованы от max possible
- Quality flags: has_birth_time, birth_time_quality

**FR-3.6.3** Извлечение ДОЛЖНО быть детерминированным.

---

## 4. Нефункциональные требования

### 4.1 Производительность

| Требование | Значение |
|---|---|
| **NFR-4.1.1** | Вычисление карты < 2 секунды |
| **NFR-4.1.2** | Геокодинг (с кэшем) < 100 мс |
| **NFR-4.1.3** | Геокодинг (без кэша) < 5 секунд |

### 4.2 Надёжность

| Требование | Значение |
|---|---|
| **NFR-4.2.1** | При ошибке Redis — fallback на вычисление без кэша |
| **NFR-4.2.2** | При ошибке внешнего API (геокодинг) — пустой результат, не crash |
| **NFR-4.2.3** | При отсутствии эфемеридных файлов — fallback на встроенные |

### 4.3 Безопасность

| Требование | Значение |
|---|---|
| **NFR-4.3.1** | Все endpoints требуют аутентификации (JWT Bearer) |
| **NFR-4.3.2** | Ownership check: пользователь работает только со своими данными |
| **NFR-4.3.3** | Нет хранения паролей в E3 (делегируется в E2) |

### 4.4 Тестируемость

| Требование | Значение |
|---|---|
| **NFR-4.4.1** | Unit-тесты: 39 тестов, все проходят |
| **NFR-4.4.2** | ruff check: 0 ошибок |
| **NFR-4.4.3** | mypy strict: 0 ошибок |
| **NFR-4.4.4** | CI: все 7 jobs green |

---

## 5. Модель данных

### 5.1 PersonProfile

```
person_profiles
├── id              UUID PK
├── user_id         UUID FK → users.id (CASCADE)
├── name            VARCHAR(120)
├── birth_date      DATE
├── birth_time      TIME (nullable)
├── birth_time_accuracy VARCHAR(20) — "exact"|"approximate"|"unknown"
├── birth_place     VARCHAR(300)
├── latitude        FLOAT
├── longitude       FLOAT
├── timezone        VARCHAR(60) — IANA
├── created_at      TIMESTAMP WITH TZ
└── updated_at      TIMESTAMP WITH TZ
```

### 5.2 ChartSnapshot

```
chart_snapshots
├── id              UUID PK
├── profile_id      UUID FK → person_profiles.id (CASCADE)
├── user_id         UUID FK → users.id (CASCADE)
├── engine_version  VARCHAR(20)
├── chart_data      JSON — полный снимок карты
├── created_at      TIMESTAMP WITH TZ
└── updated_at      TIMESTAMP WITH TZ
```

### 5.3 chart_data (JSON structure)

```json
{
  "birth_datetime": "1990-08-24T11:00:00+00:00",
  "latitude": 55.7558,
  "longitude": 37.6173,
  "timezone": "Europe/Moscow",
  "house_system": "P",
  "planets": [
    {
      "name": "Sun",
      "longitude": 151.09,
      "latitude": 0.0,
      "speed": 0.96,
      "sign": "Virgo",
      "sign_degree": 1.09,
      "house": 9,
      "is_retrograde": false
    }
  ],
  "houses": [
    {"number": 1, "longitude": 236.36, "sign": "Scorpio"}
  ],
  "aspects": [
    {
      "planet_a": "Venus",
      "planet_b": "Neptune",
      "aspect_type": "quincunx",
      "angle": 150.86,
      "orb": 0.86,
      "is_applying": false
    }
  ]
}
```

### 5.4 FeatureVector

```json
{
  "fire": 0.186,
  "earth": 0.571,
  "air": 0.171,
  "water": 0.071,
  "cardinal": 0.371,
  "fixed": 0.400,
  "mutable": 0.229,
  "sun_moon_balance": 0.42,
  "house_emphasis": {"7": 1.0, "8": 0.48, "9": 0.43, "2": 0.39, "12": 0.24},
  "conjunction_count": 0.0,
  "trine_count": 0.012,
  "square_count": 0.012,
  "opposition_count": 0.0,
  "has_birth_time": true,
  "birth_time_quality": 1.0
}
```

---

## 6. API Specification

### 6.1 Endpoints

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/v1/profiles` | Создать профиль |
| `GET` | `/api/v1/profiles` | Список профилей |
| `GET` | `/api/v1/profiles/{id}` | Получить профиль |
| `PATCH` | `/api/v1/profiles/{id}` | Обновить профиль |
| `DELETE` | `/api/v1/profiles/{id}` | Удалить профиль |
| `GET` | `/api/v1/profiles/geocode?q=` | Поиск места |
| `POST` | `/api/v1/profiles/{id}/chart` | Вычислить/получить карту |
| `GET` | `/api/v1/profiles/{id}/chart` | Список снимков карты |
| `GET` | `/api/v1/profiles/{id}/chart/{snapshot_id}` | Получить снимок |

### 6.2 Пример запроса

```http
POST /api/v1/profiles
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "name": "Тест",
  "birth_date": "1990-08-24",
  "birth_time": "14:00:00",
  "birth_time_accuracy": "exact",
  "birth_place": "Москва, Россия",
  "latitude": 55.7558,
  "longitude": 37.6173,
  "timezone": "Europe/Moscow"
}
```

---

## 7. Критерии верификации

### 7.1 Тесты

| Тип | Количество | Покрытие |
|---|---|---|
| Unit (profile service) | 14 | CRUD, валидация, ownership |
| Unit (geocoding) | 8 | cache hit/miss, parsing, HTTP errors |
| Unit (timezone) | 10 | resolve, cache, fallback |
| Unit (chart engine) | 16 | planets, houses, aspects, determinism |
| Unit (chart service) | 5 | cache, compute, serialization |
| Unit (features) | 8 | elements, modalities, ranges, determinism |
| **Итого** | **61** | |

### 7.2 Quality Gates

| Проверка | Статус |
|---|---|
| `ruff check .` | ✅ 0 errors |
| `ruff format --check .` | ✅ 0 files |
| `mypy .` | ✅ 0 errors |
| `pytest` | ✅ 61/61 passed |
| CI (GitHub Actions) | ✅ 7/7 jobs green |

---

## 8. Зависимости

### 8.1 Внешние зависимости

| Пакет | Версия | Назначение |
|---|---|---|
| `pyswisseph` | 2.10.3.2 | Swiss Ephemeris — астрономические вычисления |
| `timezonefinder` | 8.x | Offline-резолв координат → IANA timezone |
| `flatlib` | 0.2.x | Астрологические утилиты (reserv) |
| `httpx` | 0.28+ | Async HTTP для геокодинга (Nominatim) |

### 8.2 Внутренние зависимости

| Модуль | Зависимость |
|---|---|
| `app.core.models` | BaseModel (UUID PK + timestamps) |
| `app.core.exceptions` | NotFoundError, ValidationError |
| `app.infrastructure.redis` | Redis client для кэша |
| `app.dependencies` | get_current_user, get_db |

### 8.3 Downstream consumers

| Модуль | Что использует из E3 |
|---|---|
| **E4: Rules** | FeatureVector → rule engine scoring |
| **E5: Reports** | ChartSnapshot → render report |
| **E6: Billing** | PersonProfile → entitlement check |
