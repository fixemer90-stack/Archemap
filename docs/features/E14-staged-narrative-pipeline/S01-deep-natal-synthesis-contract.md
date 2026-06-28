# S01 — DeepNatalSynthesis Contract

> Статус: ⬜ Не начато

## Контекст

Single-shot LLM получает слишком плоский `NarrativeInput`: facts, aspects, dominants and sections, но не получает полноценную модель “как карта работает”. Перед staged LLM pipeline нужен deterministic contract, который собирает натальную карту в смысловую структуру.

## Что сделать

1. Создать backend schemas для `DeepNatalSynthesis`.
2. Создать builder из `Report.report_data`.
3. Включить evidence map для всех planet/sign/house/aspect facts.
4. Связать synthesis с `input_hash` и `chart_snapshot/source_chart`.
5. Добавить unit tests на стабильность структуры и отсутствие unsupported evidence refs.

## Затрагиваемые файлы

| Файл                                                               | Действие                                              |
| ------------------------------------------------------------------ | ----------------------------------------------------- |
| `backend/app/modules/report_narratives/schemas.py`                 | Добавить synthesis schemas                            |
| `backend/app/modules/report_narratives/input_builder.py`           | Вызвать synthesis builder или использовать его output |
| `backend/app/modules/report_narratives/deep_synthesis.py`          | Новый модуль builder-а                                |
| `backend/tests/unit/test_report_narratives/test_deep_synthesis.py` | Новые тесты                                           |

## Acceptance criteria

- [ ] `DeepNatalSynthesis` создаётся без LLM.
- [ ] Все interpretive items имеют `evidence_ids`.
- [ ] Unknown evidence ids невозможны на уровне builder tests.
- [ ] Synthesis включает planets, houses, signs, aspects, chart dynamics and calibration hypotheses.
- [ ] Stable hash меняется при изменении исходной карты или synthesis contract version.
