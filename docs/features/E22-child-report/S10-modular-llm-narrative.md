# S10: Modular LLM narrative

## Статус

🟡 Переоткрыто для [BUG-50](../../reviews/2026-10-28/BUG-50-child-content-quality.md): исторические schema/evidence/safety проверки не обнаружили повторяющийся и тематически обеднённый текст.

Дополнительные критерии BUG-50:

- [x] Обезличенный middle-score сценарий больше не сводится к одинаковым общим фразам и дублирующимся разделам.
- [x] Содержательное раскрытие фактов сохраняет enforceable child-safety и не добавляет неподдержанные рекомендации.
- [x] Версии prompt/input/validator/assembly согласованы; legacy read/retry не переинтерпретирует старые артефакты.
- [x] Полный pipeline и восстановленный пользовательский результат проверены, а не только технический `ready`: production core v3 на `3e3ee67`, 11 real-provider sections, persisted/API/native desktop/mobile/PDF readback. Проверка выявила остаточный дефект, а не безусловное принятие текста.
- [x] Повторяющиеся стандартные caveat/uncertainty sentences устранены versioned section-aware rendering без потери child-safety и локальной неопределённости; в десяти успешных production bodies core version 4 полных sentence-level повторов нет. Полная генерация при этом не принята из-за failed praise.
- [ ] Новый citation contract проходит независимое review и real-provider acceptance без failed sections. Offline V4 использует проверенные per-claim IDs, но не переинтерпретирует pinned V3 retry; новые платные вызовы не разрешены.

## Контекст

Narrative должен быть подробным и человечным, но строго ограниченным Guidance Facts, section contract и child-safety policy.

## Что сделать

1. Создать prompt family по секциям report contract.
2. Передавать каждой секции только owned/reference facts.
3. Валидировать structured output, evidence refs и prohibited claims.
4. Реализовать section retry и assembly без повторного deterministic calculation.
5. Версионировать prompt/model/provider и сохранять generation metadata без PII в telemetry.

## Затрагиваемые файлы

| Область                                                    | Действие          |
| ---------------------------------------------------------- | ----------------- |
| `backend/app/modules/child/prompts/*`                      | Изменить/добавить |
| `backend/app/modules/child/narrative.py`                   | Изменить/добавить |
| `backend/app/modules/child/assembly.py`                    | Изменить/добавить |
| `backend/tests/unit/test_child/test_narrative_pipeline.py` | Изменить/добавить |

## Критерии приёмки

- [x] LLM не получает raw chart и не вычисляет scores.
- [x] LLM не добавляет новые child facts/recommendations.
- [x] Каждая section проходит schema/evidence/safety gates.
- [x] Failed section можно повторить независимо.
- [x] Mock и real-provider fixtures покрыты.
- [x] Assembly сохраняет section order и age snapshot reference.

## Verification

- `uv run pytest tests/unit/test_child/test_narrative_pipeline.py -q` — 30 passed.
- `uv run pytest tests/unit/test_child -q` — 299 passed.
- `uv run ruff check .` — passed.
- `uv run ruff format --check .` — 436 files already formatted.
- `uv run mypy app` — 248 source files clean.
- `git diff --check` — passed.
- Real-provider fixture проходит через настоящий `OpenRouterProvider` с HTTP mock и проверяет structured response,
  отсутствие child/generation/age/fact UUID в provider payload и сохранение только opaque model reference.
- Отдельные integration/frontend тесты не добавлялись: Story не меняет API, worker lifecycle или frontend surface;
  PostgreSQL persistence и async orchestration входят в S11.

## Реализованный safety contract

- Provider получает только section-local `owned-N` / `reference-N`, approved text и section metadata без PII/lineage UUID.
- Свободный LLM-текст не публикуется: body обязан полностью состоять из claims, которые дословно совпадают с
  deterministic approved rendering authoritative Guidance Facts.
- На сервере opaque refs переводятся обратно в authoritative fact IDs перед child-safety validation и persistence.
- Пустые по owned facts секции фиксируются как `not_applicable` без provider call; остальные секции повторяются
  независимо и не запускают deterministic calculation повторно.
- Assembly проверяет lineage, section status, prompt/input/output hashes, provider allowlist, opaque model reference,
  error metadata, section order и age snapshot reference.
- Независимый specification review: **PASS**. Финальный code-quality/security review: **APPROVED**.

## Citation contract V4 — проверенный offline-кандидат

Backend commit `0d600fe375b17c27ee37d20d358426b281e3048d` добавляет narrative input/prompt/assembly V4 и provider/canonical output V2, не меняя Guidance Facts V3. Provider не передаёт redundant `cited_fact_ids`: extra field запрещён. Сервер выводит ordered citations только после проверки уникальных per-claim IDs, полной approved rendering, conditional/body/section/title, coverage/ownership/lineage/safety. Stored derived list снова проверяется, а не чинится на чтении. Новый prompt требует целый `approved_text`, допускающий несколько предложений, и запрещает sentence splitting; legacy misleading example не добавляется.

Новая full generation сохраняет prompt V4 в immutable report до provider work; resume использует этот pin. Narrative-only retry старого V3 остаётся V3, не получает новый контракт задним числом. V4 retry хранит дополнительный prompt pin; API/PDF выбирают по report version, не текущему alias. Frozen V1/V2/V3 fixtures и негативные duplicate/fragment/unsupported/missing/conditional/body/safety проверки сохранены.

Родительский агент свежим запуском проверил **1280 unit tests**, whole-backend Ruff/format/mypy (**493 source files**) — PASS. Отдельно на owned disposable PostgreSQL с прочитанными `fsync/synchronous_commit/full_page_writes=on/on/on` повторены persisted V3/V4 praise retry, historical coexistence, canonical API и PDF — **5 passed**; после teardown ноль public tables, cluster остановлен. Implementer-прогон broader lifecycle/retry/API/PDF batch — **54 passed**; финальный повтор использовал только disposable `fsync=off` и не доказывает crash durability. Все provider fixtures in-process, `LLM_ENABLED=false`.

Независимые spec и security reviews точного `0d600fe` запущены, verdict пока не записан. Candidate не опубликован/не выложен и не проверен реальным провайдером. Причина конкретного исходного отклонённого output остаётся неизвестной; removal redundant list не означает принятия split/duplicate claims. S10 и BUG-50 остаются открытыми для review/release/real-provider acceptance.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
