# S02: API уточнения и контракт геокодирования

## Статус

⬜ Не начато

## Контекст

Текущий универсальный `PATCH /profiles/{profile_id}` не выражает семантику «уточнить данные и пересчитать всё зависимое». Нужна отдельная операция с cooldown, идемпотентностью и предсказуемым ответом для Settings.

## Что сделать

### Endpoint доступности

```http
GET /api/v1/profiles/{profile_id}/birth-data-refinement-status
```

Возвращает серверное состояние:

```json
{
  "profile_id": "uuid",
  "can_refine": false,
  "last_refined_at": "2026-09-13T10:00:00Z",
  "next_available_at": "2026-09-14T10:00:00Z",
  "retry_after_seconds": 43120
}
```

### Endpoint изменения

```http
POST /api/v1/profiles/{profile_id}/birth-data-refinements
Idempotency-Key: <uuid>
Content-Type: application/json
```

```json
{
  "birth_time": "08:35",
  "birth_time_accuracy": "exact",
  "birth_place": "Москва, Россия",
  "latitude": 55.7558,
  "longitude": 37.6176,
  "timezone": "Europe/Moscow"
}
```

Клиент отправляет полный итоговый снимок времени и места. Допустимые согласования:

- `exact|approximate` требуют `birth_time`;
- `unknown` допускает `birth_time=null`, а расчёт использует существующую детерминированную fallback-политику без ложной точности;
- place, latitude, longitude и timezone изменяются как единый блок;
- date of birth не входит в DTO;
- хотя бы одно доменное значение должно реально отличаться.

Успешный ответ — `202 Accepted`:

```json
{
  "revision_id": "uuid",
  "generation_id": "uuid",
  "profile_id": "uuid",
  "changed_fields": ["birth_time", "birth_time_accuracy"],
  "status": "queued",
  "next_available_at": "2026-09-14T10:00:00Z"
}
```

Cooldown — `429 Too Many Requests`:

```json
{
  "detail": "Данные рождения можно уточнять не чаще одного раза за 24 часа",
  "code": "birth_data_refinement_cooldown",
  "next_available_at": "2026-09-14T10:00:00Z",
  "retry_after_seconds": 43120
}
```

Также обязателен HTTP-header `Retry-After`.

## Геокодирование

1. Расширить результат `/api/v1/profiles/geocode`, чтобы backend возвращал согласованный IANA timezone для координат.
2. UI принимает place/lat/lon/timezone только после выбора конкретной подсказки.
3. Backend повторно валидирует диапазоны, IANA timezone и согласованность полей.
4. Нулевые координаты, частичная пара координат и свободно введённое неподтверждённое место отклоняются.
5. Нельзя использовать жёсткий default `Europe/Moscow` для произвольного города.

## Коды ошибок

| HTTP | `code`                           | Смысл                                     |
| ---- | -------------------------------- | ----------------------------------------- |
| 400  | `birth_data_unchanged`           | Материальных изменений нет                |
| 400  | `birth_time_accuracy_mismatch`   | Время и точность не согласованы           |
| 422  | `birth_place_not_geocoded`       | Место/координаты/timezone невалидны       |
| 403  | `profile_not_owned`              | Профиль не принадлежит пользователю       |
| 409  | `idempotency_key_conflict`       | Ключ повторён с другим payload            |
| 429  | `birth_data_refinement_cooldown` | Не истекло скользящее окно 24 часа        |
| 503  | `refinement_enqueue_unavailable` | Операция не может быть надёжно поставлена |

## Затрагиваемые файлы

| Область                                           | Действие                         |
| ------------------------------------------------- | -------------------------------- |
| `backend/app/modules/profiles/router.py`          | Новые endpoints                  |
| `backend/app/modules/profiles/schemas.py`         | DTO и response/error contracts   |
| `backend/app/modules/profiles/service.py`         | Ownership, cooldown, transaction |
| `backend/app/infrastructure/geocoding.py`         | Timezone contract                |
| `contracts/openapi.yaml`                          | Публичная спецификация           |
| `backend/tests/unit`, `backend/tests/integration` | API и валидация                  |

## Критерии приёмки

- [ ] Операция требует авторизацию и ownership профиля.
- [ ] GET статуса не расходует cooldown.
- [ ] POST требует `Idempotency-Key` и корректно обрабатывает replay/conflict.
- [ ] Backend, а не frontend, является источником истины для cooldown.
- [ ] Ответ `429` содержит header и машинно-читаемые поля времени.
- [ ] Date of birth невозможно изменить новым endpoint.
- [ ] Time/accuracy и place/coordinates/timezone валидируются как согласованные группы.
- [ ] Геокодер возвращает реальный IANA timezone; московский default удалён из этого сценария.
- [ ] OpenAPI и тесты содержат все success/error response shapes.
