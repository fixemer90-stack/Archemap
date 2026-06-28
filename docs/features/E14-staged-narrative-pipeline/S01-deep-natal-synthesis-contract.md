# S01 — DeepNatalSynthesis Contract

> Статус: ✅ Готово
> Коммит: `92584af`

## Контекст

Single-shot LLM получает слишком плоский `NarrativeInput`: facts, aspects, dominants and sections, но не получает полноценную модель “как карта работает”. Перед staged LLM pipeline нужен deterministic contract, который собирает натальную карту в смысловую структуру.

## Что сделано

1. Добавлены backend schemas для `DeepNatalSynthesis` и связанных interpretive contracts.
2. Добавлен deterministic builder из `Report.report_data`.
3. Включён `evidence_map` для planet/sign/house/aspect facts.
4. Синтез привязан к `contract_version` и `source_chart_snapshot_id`.
5. Добавлены unit tests на стабильность структуры и unsupported evidence refs.

## Затрагиваемые файлы

| Файл                                                               | Действие                                      |
| ------------------------------------------------------------------ | --------------------------------------------- |
| `backend/app/modules/report_narratives/schemas.py`                 | Добавлены synthesis schemas                   |
| `backend/app/modules/report_narratives/input_builder.py`           | `DeepNatalSynthesis` включён в `NarrativeInput` |
| `backend/app/modules/report_narratives/deep_synthesis.py`          | Builder и deterministic synthesis logic       |
| `backend/tests/unit/test_report_narratives/test_deep_synthesis.py` | Тесты synthesis contract                      |
| `backend/tests/unit/test_report_narratives/test_input_builder.py`  | Регрессия на включение synthesis во вход      |

## Acceptance criteria

- [x] `DeepNatalSynthesis` создаётся без LLM.
- [x] Все interpretive items имеют `evidence_ids`.
- [x] Unknown evidence ids невозможны на уровне builder tests.
- [x] Synthesis включает planets, houses, signs, aspects, chart dynamics and calibration hypotheses.
- [x] Stable hash / version-sensitive deterministic contract меняется при изменении карты или версии synthesis contract.

## Verification

- `pytest tests/unit/test_report_narratives/test_deep_synthesis.py tests/unit/test_report_narratives/test_input_builder.py -q`
- `pytest tests/unit/test_report_narratives -q`
- `ruff check app/modules/report_narratives/deep_synthesis.py app/modules/report_narratives/schemas.py tests/unit/test_report_narratives/test_deep_synthesis.py`
- `mypy app/modules/report_narratives/deep_synthesis.py tests/unit/test_report_narratives/test_deep_synthesis.py`
