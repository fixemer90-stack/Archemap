# E22 Child Report — API Contract

## Общие правила

- Prefix: `/api/v1/child`.
- Все routes требуют authenticated owner и backend access policy.
- Foreign-owner или неизвестный resource возвращает неразличимый `404`.
- `POST create`, questionnaire complete, regenerate и age update требуют `Idempotency-Key`.
- Polling выполняется по `generation_id`, не по `child_id`.
- Child record не является аккаунтом и не получает auth token.
- Locked responses не содержат protected child data.

## Child records

| Method | Endpoint                                   | Назначение                                     |
| ------ | ------------------------------------------ | ---------------------------------------------- |
| GET    | `/api/v1/child/children`                   | Список child records владельца                 |
| POST   | `/api/v1/child/children`                   | Создать child record                           |
| GET    | `/api/v1/child/children/{child_id}`        | Прочитать record                               |
| PATCH  | `/api/v1/child/children/{child_id}`        | Изменить context или birth data                |
| DELETE | `/api/v1/child/children/{child_id}`        | Архивировать/удалить по privacy contract       |
| GET    | `/api/v1/child/children/{child_id}/export` | Приватный JSON export владельцу, включая архив |

Пример создания:

```json
{
  "display_name": "Миша",
  "relationship_type": "son",
  "child_gender": "male",
  "birth_date": "2021-05-12",
  "birth_time": null,
  "birth_time_confidence": "unknown",
  "birth_place": {
    "label": "Москва",
    "latitude": 55.7558,
    "longitude": 37.6173,
    "timezone": "Europe/Moscow"
  },
  "caregiver_context": {
    "primary_caregiver": true,
    "daily_contact": "high",
    "boundary_role": "shared",
    "soothing_role": "mostly_me"
  }
}
```

`child_gender` optional и не участвует в scoring.

### Private export

`GET children/{child_id}/export` возвращает attachment JSON `child-export-1` с полным owned Child graph в одном PostgreSQL snapshot, включая lifecycle/events/assemblies и archived child. Нужны canonical authenticated owner и paid Child access; отключение admission flag не блокирует это чтение. Foreign/deletion-pending — private 404. Ответ `Cache-Control: private, no-store`; production требует HTTPS. Credentials/worker claim/lifecycle tokens удаляются рекурсивно. Обычные ошибки Child API также no-store; 422 не отражает значения или произвольные имена неизвестных полей.

## Questionnaire

| Method | Endpoint                                                   | Назначение                            |
| ------ | ---------------------------------------------------------- | ------------------------------------- |
| GET    | `/api/v1/child/children/{child_id}/questionnaires/current` | Получить versioned age-filtered draft |
| PUT    | `/api/v1/child/questionnaires/{session_id}/answers`        | Сохранить draft answers               |
| POST   | `/api/v1/child/questionnaires/{session_id}/complete`       | Зафиксировать immutable answer set    |

Questionnaire response содержит `questionnaire_version`, `age_stage`, `required_question_ids` и draft state. Клиент не вычисляет age filtering самостоятельно.

## Report lifecycle

| Method | Endpoint                                          | Назначение                                        |
| ------ | ------------------------------------------------- | ------------------------------------------------- |
| POST   | `/api/v1/child/reports`                           | Создать generation для child/questionnaire        |
| GET    | `/api/v1/child/generations/{generation_id}`       | Получить progress и artifact IDs                  |
| GET    | `/api/v1/child/reports/{report_id}`               | Получить progressive report                       |
| GET    | `/api/v1/child/reports/{report_id}/sections`      | Получить section statuses                         |
| GET    | `/api/v1/child/reports/{report_id}/versions`      | История immutable core versions                   |
| POST   | `/api/v1/child/reports/{report_id}/regenerate`    | Retry narrative или полная versioned regeneration |
| POST   | `/api/v1/child/reports/{report_id}/age-updates`   | Создать новый age snapshot/guidance               |
| GET    | `/api/v1/child/reports/{report_id}/age-snapshots` | История age snapshots                             |
| GET    | `/api/v1/child/reports/{report_id}/pdf`           | Скачать PDF для pinned snapshot                   |

Create использует server-owned lineage; HTTP surface реализован в S12/S14, aggregate review остаётся отдельным gate:

```json
{
  "child_profile_id": "uuid",
  "questionnaire_session_id": "uuid"
}
```

Parent/child chart IDs, owner, age snapshot и operation payload клиентом не задаются. Сервер проверяет active child, completed/current questionnaire и выбирает текущую chart lineage до создания generation. Paid access gate выполняется до загрузки protected lineage.

Ответ `202 Accepted`:

```json
{
  "generation_id": "uuid",
  "report_id": null,
  "status": "queued"
}
```

`report_id` появляется после deterministic publication; повтор того же accepted request возвращает прежний generation ID и его текущие status/report ID. Polling endpoint и `poll_after_ms` ещё не реализованы в S11.

## State machine

```text
child_profile_ready
→ questionnaire_draft
→ questionnaire_completed
→ queued
→ calculating_pair
→ deterministic_ready
→ generating_sections
→ ready | narrative_failed | failed
```

Transient post-report failure: `generating_sections → narrative_retry_waiting → generating_sections`. `next_retry_at` и exponential backoff durable; всё время ожидания сохраняется `report_id` и доступен опубликованный deterministic report. После исчерпания попыток — `narrative_failed`, не plain `queued`. Сбой до публикации может повторить `queued → calculating_pair`. Outcome-unknown provider intent не вызывает повторный external call. Отключённый LLM даёт terminal `child_narrative_disabled` без fake-ready narrative и без retry loop.

Age state:

```text
age_snapshot_current
→ age_snapshot_stale
→ age_update_queued
→ age_update_ready | age_update_failed
```

### Клиентское поведение

| Status                        | Что рендерить                                                  |
| ----------------------------- | -------------------------------------------------------------- |
| `queued` / `calculating_pair` | progress без вымышленных результатов                           |
| `deterministic_ready`         | полноценный deterministic summary и section skeleton           |
| `generating_sections`         | готовые sections progressive, остальные loading                |
| `ready`                       | полный report                                                  |
| `narrative_failed`            | deterministic report + retry action                            |
| `narrative_retry_waiting`     | deterministic report + готовые sections; повтор после deadline |
| `age_snapshot_stale`          | core report + датированный прошлый age block + update action   |
| `failed`                      | безопасная ошибка без частичного неподтверждённого prose       |
| `locked`                      | access CTA без protected child fields                          |

## Regenerate semantics

`scope`:

- `failed_sections` — повторить failed narrative sections и отсутствующие sections после раннего exhaustion; scope сохраняется с source segment pins и canonical hashes missing inputs. Outcome-unknown sections не вызываются повторно, в том числе через другой retry той же report lineage;
- `narrative_all` — новая narrative version из тех же Guidance Facts;
- `full_pair` — новая core version при изменившихся inputs/rules.

Нельзя использовать `narrative_all` для скрытого пересчёта chart/dimensions.

## Age update semantics

```json
{
  "expected_core_report_version": 1
}
```

Клиент не передаёт `as_of_date`, дату или timestamp для расчёта возраста. Backend берёт текущий timezone-aware UTC instant из серверных часов, переводит его в persisted timezone ребёнка и сохраняет полученную local `as_of_date`. Явная clock injection допустима только во внутреннем repository/test interface как `now: datetime | None` и отклоняет naive datetime.

Backend создаёт immutable snapshot:

```json
{
  "age_snapshot_id": "uuid",
  "as_of_date": "2026-10-14",
  "age_years": 5,
  "age_months": 5,
  "age_days": 2,
  "age_stage": "3-6",
  "age_rules_version": "child-age-mvp-1",
  "status": "age_update_ready"
}
```

## PDF contract

PDF request принимает или выбирает конкретный `age_snapshot_id`. Response metadata/headers должны позволять установить `core_report_version`, `age_snapshot_id`, `as_of_date` и presentation schema version. Web и PDF не собирают content независимо.

## Access matrix

Route-level tests обязаны покрыть:

- owner + active Plus;
- owner without access;
- expired/inactive entitlement;
- grandfathered policy, если она принята S01;
- foreign owner;
- archived/deleted child;
- child/report mismatch;
- two children of the same owner;
- direct PDF/versions/status access;
- locked payload leakage.
