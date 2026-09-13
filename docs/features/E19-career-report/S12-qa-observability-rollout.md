# S12: QA, observability, migration и rollout

## Статус

⬜ Не начато

## Контекст

Career объединяет deterministic scoring, пользовательские ответы, LLM, access policy и long-running runtime. Закрытие по unit tests одного слоя недостаточно.

## Что сделать

### Quality suites

- Golden natal fixtures с ожидаемыми dimension ranges/evidence.
- Разные answers при одной карте: manager vs expert leader vs entrepreneur preference.
- Missing/unknown birth time без invented houses/ASC.
- Contradiction retention и low-confidence wording.
- Role/path catalog integrity.
- Prompt/input snapshots и LLM schema validation.
- Anti-generic, duplication, overclaim, diagnosis и direct profession validators.
- API ownership/access/idempotency/concurrency.
- Web/PDF parity.

### Наблюдаемость

- generation duration по deterministic/narrative stage;
- failure/retry/stuck counts по безопасному error code;
- dimension/role catalog version adoption;
- questionnaire completion/drop-off без хранения ответов в labels;
- provider cost/token metrics без персонального payload;
- alert на stuck generation и массовый validator failure.

### Rollout

1. Migration + feature flag off.
2. Backfill не выполняется автоматически для legacy Career.
3. Staging с mock provider, затем real provider.
4. Проверить active Plus, grandfathered legacy и locked account.
5. Проверить deterministic-first reader, PDF, section retry и provider failure.
6. Canary cohort; сравнить outcomes/latency/cost.
7. Включить target UI; legacy route оставить только на ограниченное migration window.
8. Отключить legacy generation после доказанного переноса доступа/истории.

## Data safety

- Backup/restore rehearsal перед production migration.
- Row counts/checksums для profiles, legacy reports, payments, entitlements.
- Additive tables/columns only.
- Никакого drop/truncate/mutable backfill существующих Career payloads.
- Rollback выключает новые writes, но сохраняет все новые artifacts.

## Критерии приёмки

- [ ] Все deterministic, resolver, role/path, LLM, API и UI suites зелёные.
- [ ] Staging real-provider report проходит human quality review по design-документу.
- [ ] Locked/expired аккаунт не получает protected Career data.
- [ ] Grandfathered legacy владелец не теряет доступ.
- [ ] Старые Career reports/PDF остаются читаемыми.
- [ ] Метрики/alerts доказывают отсутствие stuck pipeline.
- [ ] Cost/latency budgets зафиксированы и измерены.
- [ ] Rollback feature flag проверен без потери данных.
- [ ] Production smoke и точный CI SHA записаны в Story перед `✅`.
