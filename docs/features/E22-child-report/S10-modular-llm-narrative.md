# S10: Modular LLM narrative

## Статус

🟡 Переоткрыто для [BUG-50](../../reviews/2026-10-28/BUG-50-child-content-quality.md): исторические schema/evidence/safety проверки не обнаружили повторяющийся и тематически обеднённый текст.

Дополнительные критерии BUG-50:

- [x] Обезличенный middle-score сценарий больше не сводится к одинаковым общим фразам и дублирующимся разделам.
- [x] Содержательное раскрытие фактов сохраняет enforceable child-safety и не добавляет неподдержанные рекомендации.
- [x] Версии prompt/input/validator/assembly согласованы; legacy read/retry не переинтерпретирует старые артефакты.
- [ ] Полный pipeline и восстановленный пользовательский результат проверены, а не только технический `ready`.

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

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
