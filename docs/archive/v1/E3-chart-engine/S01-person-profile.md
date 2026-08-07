# Story E3.S01: PersonProfile: модель (дата, время, место, TZ), CRUD API, валидация даты (1900–2100)

**Feature:** [Profile & Chart Engine](Archemap/docs/features/v1/E3-chart-engine/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Астрологическое вычислительное ядро: по натальным данным строится каноническая карта, извлекаются нормализованные признаки. Детерминировано, воспроизводимо, без AI.

PersonProfile — базовая сущность, хранящая данные рождения. Без неё невозможен расчёт карты (E3.S04) и снимок ChartSnapshot (E3.S05).

## Что сделать

1. SQLAlchemy-модель `PersonProfile` с полями: `user_id` (FK → users), `name`, `birth_date`, `birth_time` (nullable), `birth_time_accuracy` (exact/approximate/unknown), `birth_place`, `latitude`, `longitude`, `timezone` (IANA)
2. Pydantic-схемы: `CreateProfileRequest`, `UpdateProfileRequest`, `ProfileResponse`, `ProfileListResponse`
3. `ProfileService`: CRUD с валидацией года рождения (1900–2100), ownership check (только свои профили)
4. FastAPI router: `POST /profiles`, `GET /profiles`, `GET /profiles/{id}`, `PATCH /profiles/{id}`, `DELETE /profiles/{id}`
5. Alembic-миграция для таблицы `person_profiles`
6. Unit-тесты для service (14 тестов)
7. Регистрация роутера в `api/v1/__init__.py`

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/modules/profiles/__init__.py` | Создан |
| `app/modules/profiles/models.py` | Создан — PersonProfile модель |
| `app/modules/profiles/schemas.py` | Создан — Pydantic request/response |
| `app/modules/profiles/service.py` | Создан — CRUD бизнес-логика |
| `app/modules/profiles/router.py` | Создан — FastAPI эндпоинты |
| `app/api/v1/__init__.py` | Изменён — регистрация profiles_router |
| `alembic/versions/a1b2c3d4e5f6_*.py` | Создан — миграция |
| `tests/unit/test_profile_service.py` | Создан — 14 unit-тестов |

## Критерии приёмки

- [x] PersonProfile CRUD (дата, время, место рождения)
- [x] Валидация даты рождения: год 1900–2100
- [x] `birth_time_accuracy`: exact / approximate / unknown
- [x] `birth_time` nullable (для unknown — null)
- [x] Ownership check: пользователь видит только свои профили
- [x] PATCH: partial update (только переданные поля)
- [x] DELETE: CASCADE от users
- [x] Alembic-миграция с downgrade
- [x] Тесты написаны и проходят (14/14)
- [x] ruff, mypy — 0 ошибок

## Примечания

- `birth_time_accuracy` — строка, не enum, для гибкости (можно расширить без миграции)
- Координаты хранятся как `Float`, а не `Decimal` — для совместимости с Swiss Ephemeris
- `timezone` — IANA-строка (например `Europe/Moscow`), валидация будет в S03 (Timezone Resolution)
- Геокодинг (заполнение lat/lon/tz по строке места) — отдельная Story S02
