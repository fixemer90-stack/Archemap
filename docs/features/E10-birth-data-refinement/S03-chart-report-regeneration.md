# S03: Пересчёт карты и безопасная версия отчёта

## Статус

⬜ Не начато

## Контекст

Изменение времени или места влияет на UTC-момент, дома, ASC/MC, аспекты и последующие факты/синтез. Простое обновление `PersonProfile` оставит пользователю старый отчёт, не соответствующий новым данным, либо опасно перезапишет уже оплаченный результат.

## Что сделать

1. После committed-ревизии создать новый `NatalChart` по новому `input_hash`, не изменяя старую карту.
2. Прогнать детерминированную цепочку: нормализованная карта → факты/evidence → синтез → outline → infographic/calculation layer.
3. Создать новую версию `NatalReport`, связанную с новой картой и generation ID.
4. Сохранить старый активный отчёт доступным до состояния нового `deterministic_ready`.
5. Атомарно переключить активную версию после готовности детерминированного слоя; narrative может догружаться прогрессивно.
6. Не переносить narrative/infographic payload старой карты в новую версию.
7. Не создавать новый payment и не менять subscription/entitlement.
8. Сделать задачу retry-safe: повтор worker-задачи для revision ID не создаёт дубликаты.
9. Отразить `queued`, `processing`, `deterministic_ready`, `ready`, `failed` в статусе ревизии.
10. При terminal failure сохранить старый активный отчёт и дать пользователю безопасное сообщение/повтор через поддержку; cooldown не должен приводить к потере доступа.

## Правило активации

```text
old_report remains active
UNTIL new_report.status >= deterministic_ready
THEN active report pointer switches atomically
```

Новая версия не должна становиться активной в `queued/processing/failed`.

## Сохранность данных

- Миграции только additive.
- Старые `NatalChart`, `NatalReport`, сегменты и PDF не удаляются.
- Снимок ревизии позволяет связать пользовательское изменение с новой картой/отчётом.
- Существующие оплаченные права доступа сохраняются.
- Повторная генерация создаёт lineage, а не silent overwrite.

## Затрагиваемые файлы

| Область                              | Действие                                   |
| ------------------------------------ | ------------------------------------------ |
| `backend/app/modules/astrotype_v2/*` | Rebuild orchestration и lineage            |
| `backend/workers/*`                  | Idempotent async task                      |
| `backend/app/modules/profiles/*`     | Revision status/result links               |
| `backend/alembic/versions/*`         | Active/latest linkage при необходимости    |
| `backend/tests/unit/*`               | Pipeline/version tests                     |
| `backend/tests/integration/*`        | Durable async state and preservation tests |

## Критерии приёмки

- [ ] Изменение времени создаёт новый `input_hash` и новую карту, когда расчёт реально меняется.
- [ ] Изменение места/timezone создаёт карту из корректного UTC-момента и координат.
- [ ] Старые карта, отчёт, сегменты и PDF остаются в базе.
- [ ] Старый отчёт читается до `deterministic_ready` новой версии.
- [ ] Новая версия активируется атомарно и соответствует новой карте.
- [ ] Narrative строится только на фактах новой карты.
- [ ] Worker retry не создаёт дубликаты карты, отчёта или ревизии.
- [ ] Failure не скрывает старый отчёт и не запускает платёж.
- [ ] Revision status доступен API/UI без утечки внутренних traceback/provider secrets.
