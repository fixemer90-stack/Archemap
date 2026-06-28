# E11 API: LLM narrative report flow

Этот документ описывает API-сценарий E11 с практической точки зрения:

- каким endpoint'ом запускается Self-report flow;
- как frontend узнаёт текущий status;
- когда `narrative` бывает `null`;
- как работает regenerate;
- какие статусы должен уметь обрабатывать клиент.

Документ основан на текущей backend-реализации в:

- `backend/app/modules/reports/router.py`
- `backend/app/modules/reports/schemas.py`
- `docs/features/E11-llm-report-narrative/S08-report-api-narrative-endpoints.md`

## 1. Назначение API в E11

E11 не вводит отдельный "LLM endpoint для анализа человека".

API-поведение такое:

1. клиент запускает обычную генерацию отчёта;
2. backend считает deterministic report;
3. backend ставит narrative generation в фон;
4. клиент читает статус отчёта;
5. когда narrative готов, тот же report endpoint начинает отдавать `narrative`;
6. если narrative не удался, клиент видит unavailable state и может вызвать regenerate.

## 2. Поддерживаемый продуктовый flow

Для E11-MVP narrative flow полноценно поддержан для:

- `product=self`

Для `self` backend после генерации пытается автоматически поставить фоновую задачу narrative generation.

Для других продуктов:

- общий report API может существовать;
- но narrative regenerate в E11 поддерживается только для `self`.

## 3. Аутентификация

Все endpoints reports работают для текущего авторизованного пользователя.

Практически это означает:

- backend использует `get_current_user`;
- пользователь не может читать чужой report;
- пользователь не может регенерировать narrative чужого report.

Если report не принадлежит пользователю, доступ должен быть отклонён сервисным слоем `ReportService.get_report(...)`.

## 4. Базовые сущности ответа

## 4.1 `ReportResponse`

Главный объект, который возвращают E11 endpoints:

```json
{
  "id": "report_uuid",
  "profile_id": "profile_uuid",
  "product": "self",
  "version": 1,
  "status": "generating_narrative",
  "mode": "full",
  "archetype": "...",
  "score": 0.82,
  "confidence": 0.76,
  "pdf_url": null,
  "pdf_generated": false,
  "report_data": {},
  "narrative": null,
  "error_message": null,
  "created_at": "2026-06-07T10:00:00Z",
  "updated_at": "2026-06-07T10:00:03Z"
}
```

### Поля, важные именно для E11

- `status` — жизненный цикл отчёта и narrative-слоя
- `report_data` — deterministic база, доступная даже без готового narrative
- `narrative` — persisted narrative payload или `null`
- `error_message` — причина сбоя enqueue/generation или unavailable-state

## 4.2 `NarrativeResponse`

Когда narrative уже существует, поле `narrative` имеет форму:

```json
{
  "id": "narrative_uuid",
  "report_id": "report_uuid",
  "product": "self",
  "prompt_version": "self_story_v1",
  "model_provider": "openai",
  "model_name": "gpt-4.1-mini",
  "status": "ready",
  "title": "Ваш внутренний портрет",
  "hero": {},
  "sections": [],
  "career_cta": {},
  "content": {},
  "error_message": null,
  "generation_started_at": "2026-06-07T10:00:04Z",
  "generation_finished_at": "2026-06-07T10:00:18Z",
  "generation_attempts": 1,
  "created_at": "2026-06-07T10:00:04Z",
  "updated_at": "2026-06-07T10:00:18Z"
}
```

### Поля, важные для клиента

- `prompt_version` — какая версия prompt породила narrative
- `model_provider` / `model_name` — чем именно он был сгенерирован
- `status` — статус уже narrative-row, не только всего report
- `sections` — основной narrative контент для рендера
- `career_cta` — CTA для отдельного Career-report
- `content` — полный сохранённый narrative JSON
- `generation_attempts` — сколько было попыток
- `error_message` — ошибка narrative generation, если есть

## 5. Статусы, которые клиент обязан понимать

На frontend и в интеграциях нельзя ориентироваться только на наличие `narrative`.

Нужно обрабатывать `status`.

Под E11 практически важны такие статусы:

- `generating_narrative`
- `ready`
- `narrative_failed`
- `deterministic_ready`

### `generating_narrative`

Значение:

- deterministic report уже создан или создаётся к моменту возврата;
- narrative generation поставлена в фон;
- клиент должен polling-ить detail endpoint.

Ожидаемое поведение клиента:

- показать progress state;
- не висеть бесконечно;
- после timeout дать `Обновить` и `Повторить генерацию`, но не открывать технический fallback summary как основной результат.

### `ready`

Значение:

- narrative готов и сохранён;
- клиент может рендерить narrative-first report.

Ожидаемое поведение клиента:

- использовать `narrative.sections`, `hero`, `career_cta`;
- deterministic блоки уводить в technical details.

### `narrative_failed`

Значение:

- narrative-слой не удался;
- deterministic report остаётся доступным на backend, но Self UI не должен маскировать это как готовый narrative-ответ.

Ожидаемое поведение клиента:

- показать unavailable state;
- показать warning;
- дать `Повторить генерацию`.

### `deterministic_ready`

Значение:

- базовый deterministic report доступен;
- narrative ещё не оказался в финальном usable `ready`.

Ожидаемое поведение клиента:

- для Self оставаться в progress/ожидании полного текста;
- не рендерить `DeterministicReportFallback` как нормальный ответ;
- можно предложить regenerate narrative.

## 6. Endpoint: generate report

## 6.1 Запрос

```http
POST /api/v1/reports/generate
Content-Type: application/json
```

Body:

```json
{
  "profile_id": "<profile_uuid>",
  "product": "self",
  "mode": "full"
}
```

### Поля

- `profile_id: string` — UUID профиля
- `product: string` — вертикаль, по умолчанию `self`
- `mode: string` — режим отчёта, по умолчанию `full`

## 6.2 Что делает backend

Для `product=self` endpoint делает следующее:

1. вызывает `ReportService.generate_report(...)`;
2. считает deterministic report;
3. ставит PDF generation в фон;
4. пытается поставить `generate_report_narrative.delay(report_id=...)`;
5. если enqueue narrative успешен:
   - `report.status = "generating_narrative"`
   - `report.error_message = null`
6. если enqueue narrative не удался:
   - `report.status = "deterministic_ready"`
   - `report.error_message = "Narrative task enqueue failed: ..."`
7. возвращает `ReportResponse`.

## 6.3 Happy path response

```json
{
  "id": "report_uuid",
  "profile_id": "profile_uuid",
  "product": "self",
  "status": "generating_narrative",
  "mode": "full",
  "report_data": { "...": "..." },
  "narrative": null,
  "error_message": null
}
```

Важно:

- generate endpoint не ждёт, пока LLM закончит;
- успешный ответ здесь обычно означает "generation started", а не "narrative already ready".

## 6.4 Degraded-but-not-user-ready response

Если не удалось даже поставить narrative-задачу в очередь:

```json
{
  "id": "report_uuid",
  "profile_id": "profile_uuid",
  "product": "self",
  "status": "deterministic_ready",
  "mode": "full",
  "report_data": { "...": "..." },
  "narrative": null,
  "error_message": "Narrative task enqueue failed: ..."
}
```

Это не означает провал всего deterministic расчёта. Это означает:

- deterministic результат уже сохранён;
- narrative-слой пока не запущен или не стартовал;
- для Self frontend не должен показывать это как готовый safe fallback report.

## 7. Endpoint: list reports

## 7.1 Запрос

```http
GET /api/v1/reports?product=self&limit=100
```

### Query params

- `product` — необязательный фильтр
- `limit` — 1..100
- `offset` — pagination offset

## 7.2 Зачем он нужен в E11

Frontend использует list endpoint, чтобы:

- получить список report'ов пользователя;
- выбрать latest report для конкретного `profile_id`;
- дальше перейти к polling/detail flow уже по `report_id`.

## 7.3 Ответ

```json
{
  "items": [
    {
      "id": "report_uuid",
      "profile_id": "profile_uuid",
      "product": "self",
      "status": "ready",
      "report_data": {},
      "narrative": {}
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

Важно:

- каждый item сериализуется тем же `ReportResponse`;
- backend подмешивает latest narrative state для каждого report.

## 8. Endpoint: get report by id

## 8.1 Запрос

```http
GET /api/v1/reports/{report_id}
```

Это главный polling endpoint в E11.

## 8.2 Что делает backend

1. проверяет ownership через `ReportService.get_report(...)`;
2. загружает latest narrative для `report_id`;
3. возвращает объединённый `ReportResponse`.

## 8.3 Ответ, пока narrative ещё в работе

```json
{
  "id": "report_uuid",
  "product": "self",
  "status": "generating_narrative",
  "report_data": { "...": "..." },
  "narrative": null,
  "error_message": null
}
```

Это нормальный и ожидаемый ответ.

Клиент в этом состоянии должен:

- продолжать polling;
- отсчитывать timeout;
- быть готовым остаться в progress/unavailable flow, но не открывать fallback summary как основной результат.

## 8.4 Ответ, когда narrative готов

```json
{
  "id": "report_uuid",
  "product": "self",
  "status": "ready",
  "report_data": { "...": "..." },
  "narrative": {
    "prompt_version": "self_story_v1",
    "model_provider": "openai",
    "model_name": "gpt-4.1-mini",
    "status": "ready",
    "title": "Ваш внутренний портрет",
    "hero": {},
    "sections": [],
    "career_cta": {},
    "content": {}
  },
  "error_message": null
}
```

Клиент в этом состоянии должен перейти на narrative-first rendering.

## 8.5 Ответ, когда narrative failed

```json
{
  "id": "report_uuid",
  "product": "self",
  "status": "narrative_failed",
  "report_data": { "...": "..." },
  "narrative": {
    "status": "narrative_failed",
    "error_message": "..."
  },
  "error_message": "..."
}
```

Практически клиенту важно следующее:

- отчёт не пропал;
- `report_data` доступен на backend как deterministic база;
- основной Self UI не должен подменять отсутствие полного narrative техническим fallback summary;
- можно вызвать regenerate.

## 9. Endpoint: regenerate narrative

## 9.1 Запрос

```http
POST /api/v1/reports/{report_id}/narrative/regenerate
```

Body не требуется:

```json
{}
```

## 9.2 Что делает backend

1. находит report и проверяет ownership;
2. проверяет, что `report.product == "self"`;
3. если report уже в `generating_narrative`, лишний enqueue не делает;
4. если генерация сейчас не идёт:
   - вызывает `generate_report_narrative.delay(report_id=..., force=True)`;
   - ставит `report.status = "generating_narrative"`;
   - очищает `report.error_message`;
5. возвращает `ReportResponse`.

### Почему `force=True` важно

`force=True` означает:

- новый narrative attempt не должен просто взять готовый cache hit;
- endpoint действительно инициирует новую попытку генерации narrative-слоя.

## 9.3 Успешный ответ

```json
{
  "id": "report_uuid",
  "product": "self",
  "status": "generating_narrative",
  "report_data": { "...": "..." },
  "narrative": {
    "status": "narrative_failed",
    "error_message": "old error"
  },
  "error_message": null
}
```

Важно понимать нюанс текущего контракта:

- report уже переведён в новый `generating_narrative`;
- но в ответе может ещё приехать предыдущий latest narrative state, считанный до enqueue;
- поэтому клиенту после regenerate надо ориентироваться прежде всего на верхнеуровневый `report.status`, а затем polling-ить detail endpoint.

## 9.4 Ошибки

### Регенерация не поддерживается для не-self report

```http
400 Bad Request
```

```json
{
  "detail": "Narrative regeneration is supported only for self reports"
}
```

### Не удалось поставить regenerate-задачу в очередь

```http
503 Service Unavailable
```

```json
{
  "detail": "Narrative regenerate task enqueue failed"
}
```

## 10. Типовой polling flow для frontend

Рекомендуемый сценарий клиента:

1. вызвать `POST /api/v1/reports/generate`;
2. если `status=generating_narrative`:
   - сохранить `report_id`;
   - открыть progress UI;
3. каждые 5 секунд вызывать `GET /api/v1/reports/{report_id}`;
4. если пришёл `ready`:
   - рендерить narrative;
5. если через 90 секунд всё ещё `generating_narrative`:
   - показать timeout UI;
   - предложить `Обновить`;
   - предложить `Повторить генерацию`;
6. если пришёл `narrative_failed` или `ready` без narrative:
   - показать unavailable state;
   - дать кнопку `Повторить генерацию`;
7. если пришёл `deterministic_ready`:
   - не рендерить technical fallback summary как основной результат;
   - продолжать progress UI или предложить regenerate, в зависимости от экрана;
8. при retry вызвать `POST /api/v1/reports/{report_id}/narrative/regenerate`;
9. снова перейти в polling.

## 11. Что клиенту нельзя предполагать

Нельзя строить интеграцию на неверных предположениях:

- нельзя считать, что `POST /generate` вернёт сразу готовый narrative;
- нельзя считать, что `narrative != null` обязательно означает новый актуальный attempt;
- нельзя считать, что отсутствие narrative означает отсутствие отчёта;
- нельзя смешивать deterministic failure и narrative failure;
- нельзя запускать regenerate как пересчёт всей карты.

## 12. Семантика API в одной фразе

E11 API работает так:

> report endpoint всегда остаётся источником состояния отчёта, а narrative — это асинхронно догружаемый слой поверх уже сохранённого deterministic результата.

## 13. TL;DR

Главные endpoints E11:

- `POST /api/v1/reports/generate` — запустить report flow
- `GET /api/v1/reports?product=self&limit=...` — найти latest report пользователя
- `GET /api/v1/reports/{report_id}` — главный status/polling endpoint
- `POST /api/v1/reports/{report_id}/narrative/regenerate` — повторить только narrative generation

Главная идея контракта:

- deterministic report живёт отдельно и раньше narrative;
- narrative может быть `null` или failed, но deterministic расчёт при этом всё равно сохранён;
- frontend должен мыслить через status machine, а не через "есть текст / нет текста";
- для Self отсутствие narrative не даёт права показывать safe fallback summary как готовый ответ.
