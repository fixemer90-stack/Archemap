# SRS-E20: Безопасное отключение legacy Career v1

## 1. Введение

### 1.1 Назначение

Спецификация определяет переход от параллельного legacy Career v1 к единственному target E19 Career Report без потери grandfathered access и исторических пользовательских артефактов.

### 1.2 Термины

- **Target Career** — E19 API `/api/v1/career/*`, target storage, reader и PDF.
- **Legacy Career row** — generic `reports` row с `product="career"`.
- **Grandfathered entitlement** — active access grant с `product="career"`, разрешающий target E19.
- **Compatibility path** — временное read-only чтение legacy JSON/PDF.
- **Retirement response** — отказ от нового legacy write с направлением в target flow.

### 1.3 Ссылки

- [`../features/E20-legacy-career-retirement/FEATURE.md`](../features/E20-legacy-career-retirement/FEATURE.md)
- [`../features/E20-legacy-career-retirement/WORKFLOW.md`](../features/E20-legacy-career-retirement/WORKFLOW.md)
- [`../features/E19-career-report/FEATURE.md`](../features/E19-career-report/FEATURE.md)
- [`SRS-E19-career-report.md`](./SRS-E19-career-report.md)

## 2. Общая модель

### 2.1 Целевая архитектура

Target Career является единственным write/generation контуром. Legacy rows остаются immutable read-only artifacts до отдельного removal decision. Entitlement compatibility сохраняется независимо от rows.

### 2.2 Ограничения

- Generic reports остаётся активным для Self Report.
- Target Career не принимает legacy payload/ID.
- E20 не удаляет production data.
- Любой read/write endpoint сохраняет ownership isolation.

## 3. Функциональные требования

### FR-E20.1 — Блокировка legacy generation

Система должна отклонять `POST /api/v1/reports/generate` с `product="career"` до DB mutation и rule-engine invocation.

Критерии:

- HTTP `410 Gone`;
- machine code `legacy_career_generation_retired`;
- target entrypoint `/products/career`;
- отсутствие insert/update/version archive.

### FR-E20.2 — Defense in depth

Прямой вызов generic report service с `product="career"` также должен быть запрещён, чтобы router guard нельзя было обойти внутренним consumer.

### FR-E20.3 — Immutable legacy read

GET legacy Career row должен возвращать persisted payload владельцу без refresh, regeneration, chart recompute или version change.

### FR-E20.4 — Legacy PDF

GET/HEAD generic PDF должен сохранять readable export существующего legacy payload без изменения row.

### FR-E20.5 — Target boundary

Target endpoint `/api/v1/career/reports/{id}` не должен принимать или возвращать legacy report row. Legacy payload fallback запрещён.

### FR-E20.6 — Grandfathered target access

Active `product="career"` entitlement должен давать доступ к target E19 наравне с active Plus. Expired/revoked grant не должен давать доступ.

### FR-E20.7 — Independence from rows

Target access по grandfathered entitlement не должен зависеть от наличия legacy row. Legacy row без active target entitlement не должен создавать target access.

### FR-E20.8 — UI entrypoints

Новые Career entrypoints должны вести в `/products/career`. Legacy route может только читать существующий row; отсутствие row не запускает generation.

### FR-E20.9 — Archive UX

Legacy reader должен обозначать исторический/read-only характер результата и предлагать открыть target Career flow без представления payload как нового E19 отчёта.

### FR-E20.10 — Telemetry

Система должна считать blocked writes, legacy reads, legacy PDF reads, missing-row deep links и grandfathered target access раздельно, без PII и high-cardinality IDs.

### FR-E20.11 — Removal gate

Удаление compatibility endpoints, ruleset или rows запрещено до production census, observation window, утверждённой retention strategy, backup/restore rehearsal и отдельного explicit approval.

### FR-E20.12 — Self Report non-regression

Все generic Self Report endpoints, narrative lifecycle, reader, versions и PDF должны сохранить текущее поведение.

## 4. API

### 4.1 Retired generic write

```http
POST /api/v1/reports/generate
Content-Type: application/json

{
  "profile_id": "<uuid>",
  "product": "career",
  "mode": "full"
}
```

```json
{
  "detail": {
    "code": "legacy_career_generation_retired",
    "message": "Career reports are created through the Career product flow.",
    "target_path": "/products/career"
  }
}
```

Expected status: `410 Gone`.

### 4.2 Compatibility reads

| Method | Endpoint                         | Contract                              |
| ------ | -------------------------------- | ------------------------------------- |
| GET    | `/api/v1/reports?product=career` | Список owned historical rows          |
| GET    | `/api/v1/reports/{id}`           | Immutable owned payload               |
| HEAD   | `/api/v1/reports/{id}/pdf`       | Availability/headers without mutation |
| GET    | `/api/v1/reports/{id}/pdf`       | Immutable PDF representation          |

### 4.3 Target API

`/api/v1/career/*` остаётся без legacy payload fallback. Access source может быть `plus` или `legacy_career`, но DTO/storage/lifecycle одинаковы.

## 5. Данные

### 5.1 Existing rows

E20 не изменяет schema и не удаляет rows автоматически. Для legacy Career rows вводится поведенческий invariant immutable/read-only.

### 5.2 Entitlements

`product="career"` сохраняется как grandfathered access identifier. Он не является foreign key или lookup key для legacy report payload.

### 5.3 Census

Допустимы только aggregate read-only результаты: counts, status distribution, age buckets и usage totals. Payload, birth data, names, email и tokens в evidence не сохраняются.

## 6. Нефункциональные требования

### NFR-E20.1 — Безопасность

Ownership checks обязательны для JSON/PDF. Error responses не раскрывают существование чужого row.

### NFR-E20.2 — Надёжность

Blocked write не должен иметь частичных side effects даже при retry/concurrency.

### NFR-E20.3 — Наблюдаемость

Метрики имеют bounded cardinality и позволяют отличить legacy compatibility от target E19.

### NFR-E20.4 — Обратимость

Rollout должен иметь config/code rollback без восстановления удалённых данных, поскольку E20 не выполняет deletion.

### NFR-E20.5 — Совместимость

Persisted legacy fixtures, созданные поддерживаемыми historical schema variants, должны читаться и экспортироваться без 500.

## 7. Проверка

Минимальный набор:

1. Router RED/GREEN test на `410` до mutation.
2. Service-level bypass test.
3. DB before/after immutable read/PDF test.
4. Negative target-boundary test с seeded legacy ID.
5. Grandfathered/Plus/expired entitlement matrix.
6. Generic Self Report regression suite.
7. Browser tests existing/missing legacy route и PDF download.
8. Stage target Career full flow и grandfathered smoke.
9. Telemetry/dashboard readback.
10. Production census, canary, rollback и observation evidence.

## 8. Rollout

1. Inventory and census.
2. Deploy telemetry if historical usage is not yet measurable.
3. Block legacy writes while preserving reads.
4. Update UI routing/archive messaging.
5. Stage matrix and rollback rehearsal.
6. Production canary and observation window.
7. Decide retain/export/migrate/delete in a separate approved change.

## 9. Риски и решения

| Риск                                               | Решение                                                                         |
| -------------------------------------------------- | ------------------------------------------------------------------------------- |
| Один literal `career` трактуется как один контракт | Separate constants, tests and docs for entitlement vs row vs target report type |
| Hidden writes continue                             | Router + service guards and blocked-write metrics                               |
| Historical payload corrupts target                 | No fallback and seeded-ID negative tests                                        |
| Users lose purchased access                        | Grandfathered target access matrix                                              |
| Self Report regression                             | Product-scoped changes and broad generic report tests                           |
| Premature deletion                                 | No destructive migration in E20 and explicit final removal gate                 |
