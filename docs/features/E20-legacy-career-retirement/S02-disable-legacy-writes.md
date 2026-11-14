# S02: Отключить legacy Career write/generation paths

## Статус

🟢 Local implementation/SPEC/code-security PASS. P1 `E20-CQ-01` исправлен; exact allowlist проверен на HTTP и direct-service boundaries, runtime/static enums согласованы. Publication/CI и post-fix full persisted QA учитываются отдельно в S07; live retirement acceptance не заявляется.

## Контекст

Пока generic `/reports/generate` принимает `career`, в системе существуют два параллельных генератора с разными access, payload и lifecycle контрактами.

## Что сделать

1. Добавить product-scoped guard до создания/поиска/архивации `Report` row.
2. Для `product="career"` возвращать `410 Gone` с кодом `legacy_career_generation_retired` и target URL `/products/career`.
3. Гарантировать отсутствие DB mutation, version increment и ruleset invocation.
4. Запретить любые generic regeneration paths для legacy Career.
5. Оставить Self Report generation/narrative без изменений.

## Файлы

| Файл                                     | Действие                                |
| ---------------------------------------- | --------------------------------------- |
| `backend/app/modules/reports/router.py`  | Retirement response до service write    |
| `backend/app/modules/reports/schemas.py` | Stable error contract при необходимости |
| `backend/app/modules/reports/service.py` | Defense-in-depth product guard          |
| `backend/tests/unit/test_reports/*`      | RED/GREEN mutation и regression tests   |
| API/OpenAPI docs                         | Зафиксировать retirement behavior       |

## Критерии приёмки

- [x] Career request получает стабильный `410` contract.
- [x] До и после запроса одинаковы row count, payload, status и version существующего legacy report.
- [x] Career rules не вызываются ни для literal `career`, ни через malformed/path-shaped product aliases; tokens отклоняются без нормализации.
- [x] Нельзя обойти guard прямым вызовом service, включая malformed product identifiers.
- [x] Self Report generation, narrative и PDF regression suites зелёные.
- [x] OpenAPI отражает retirement response и exact product allowlist, сохраняя literal `career` parseable для 410.

## Security finding E20-CQ-01

Reviewer воспроизвёл `/rules/interpret` с `career/.`, `career/`, `self/../career`: HTTP 200 с Career claims при real rules pipeline и mocked snapshot persistence. Literal `career` давал 410. Root cause — arbitrary string product превращается в filesystem component, а retirement сравнивает только literal. Текущий fix scope: exact canonical allowlist на HTTP/service input boundaries до snapshot/SQL/rules; без strip/lower/path normalization, без удаления retained low-level Career rules или изменения historical reads. Старые зелёные тесты не покрывали этот обход.

## Evidence

До P1 fix: parent **1477 unit / 230 integration**, прежний SPEC `deleg_644a7521` (224 scoped units + real PDF) — исторический baseline, не доказательство закрытия bypass. После fix: author **1580 unit**, parent **119 focused** + full Ruff/format/mypy PASS. Fresh SPEC `deleg_b016d85a`: **316 unit** и independent ASGI/no-work/immutable-status probes PASS. CODE/security `deleg_fdb0b999`: strict JSON PASS, independently **119 tests**; fingerprints проверены parent. Parent full post-fix persisted rerun: **230 passed**, 3 warnings, test/cleanup exits 0; task-container absence проверено. Publication и CI подтверждены для `0d109e9` (run `43641818436`, 8/8 jobs success). Live gates остаются открытыми; details в review log.
