# S01 — Human Storytelling Contract and Tone Guide

Статус: ✅ Готово
Эпик: `E15-self-report-human-storytelling`

## Контекст

Текущий Self report evidence-backed, но звучит слишком сухо. Перед изменением prompt/code нужен явный storytelling contract: какой язык считается человеческим, какой — “душным”, и как сохранять точность без канцелярита.

S01 фиксирует этот контракт в коде и документации. Реализация находится в:

- `backend/app/modules/report_narratives/human_storytelling.py`
- `backend/tests/unit/test_report_narratives/test_human_storytelling_contract.py`

## Что сделано

1. Создан versioned human tone contract:
   - `HUMAN_STORYTELLING_CONTRACT_VERSION = "self_human_storytelling_v1"`.
2. Зафиксирована целевая narrative chain:
   - `recognition`;
   - `personal_formula`;
   - `lived_scene`;
   - `inner_tension`;
   - `protective_strategy`;
   - `mature_expression`;
   - `soft_question`.
3. Добавлен `HUMAN_TONE_GUIDE`:
   - hero должен быть recognition-first;
   - raw placements, socionics labels, scores и calculation-first evidence не должны открывать первый экран;
   - evidence remains source of truth, но раскрывается progressively/secondary.
4. Добавлены banned tone patterns:
   - `bureaucratic_abstraction` — канцелярит и служебная абстракция;
   - `generic_astrology_prose` — generic horoscope prose;
   - `unsupported_therapy_language` — терапевтический/диагностический язык без основания;
   - `technical_first_hero` — hero, начинающийся с расчётных маркеров.
5. Добавлены 5 before/after examples:
   - `hero`;
   - `main_formula`;
   - `emotions_and_communication`;
   - `relationships`;
   - `development`.
6. Добавлен первый helper:
   - `validate_human_storytelling_text(...)`.

Этот helper пока не является финальным S04 quality gate для всего отчёта. Он задаёт контракт и тестируемый словарь, на который будут опираться S02 prompts, S03 assembler и S04 validators.

## Tone contract

### Целевая формула

```text
узнавание → личная формула → жизненная сцена → внутреннее напряжение → защитная стратегия → зрелая форма → мягкий вопрос
```

### Неправильный старт

```text
Солнце и Луна в Козероге в 7 доме формируют устойчивый паттерн самоопределения.
```

Проблема: текст сначала звучит как объяснение карты, а не как узнавание человека.

### Правильный старт

```text
Вам важно не просто быть собой в вакууме — вы точнее собираетесь рядом с другим человеком. В диалоге быстрее становится понятно, где ваша позиция, за что вы отвечаете и какие отношения выдерживают реальность, а не только эмоцию момента.
```

Разница: факт карты не исчезает, но не ломает первую человеческую точку входа.

## Before/after examples

### Hero

До:

```text
Солнце и Луна в Козероге в 7 доме формируют устойчивый паттерн самоопределения.
```

После:

```text
Вам важно не просто быть собой в вакууме — вы точнее собираетесь рядом с другим человеком. В диалоге быстрее становится понятно, где ваша позиция, за что вы отвечаете и какие отношения выдерживают реальность, а не только эмоцию момента.
```

### Main formula

До:

```text
Доминанты карты формируют механизм ответственности и структурирования опыта.
```

После:

```text
Ваша главная формула — не торопиться с красивым впечатлением, а собрать опору, которой можно доверять. Когда внутри появляется ясный каркас, вы становитесь спокойнее, точнее и заметно сильнее.
```

### Emotions and communication

До:

```text
Эмоциональная обработка проходит через аналитический фильтр и коммуникативную динамику.
```

После:

```text
Сильное чувство у вас редко остаётся просто волной. Почти сразу появляется попытка назвать его, объяснить, найти правильную форму — и именно здесь можно как прояснить контакт, так и слишком быстро закрыться в контроле.
```

### Relationships

До:

```text
Партнёрская сфера активирует сценарии глубины, границ и взаимной регуляции.
```

После:

```text
В близости вам мало формальной симпатии. Нужен контакт, где можно почувствовать глубину, но не потерять собственные границы; поэтому вы можете одновременно тянуться к человеку и проверять, выдержит ли он реальность.
```

### Development

До:

```text
Вектор развития связан с интеграцией зрелой формы и снижением защитных реакций.
```

После:

```text
Рост начинается там, где вы не заставляете себя сразу быть сильнее, а замечаете момент защиты. Если выдержать паузу и выбрать следующий спокойный шаг, внутренняя строгость превращается не в зажим, а в устойчивость.
```

## Связь с S02

S02 должна использовать этот контракт как источник tone requirements для staged prompt family v2. Prompt tests должны проверять, что новые prompt files требуют:

- recognition-first opening;
- lived manifestation;
- inner tension/protection;
- mature expression;
- soft question where appropriate;
- evidence as secondary/progressive disclosure;
- no канцелярит / generic horoscope prose / unsupported therapy language.

## Затрагиваемые файлы

| Файл                                                                                  | Изменение                         |
| ------------------------------------------------------------------------------------- | --------------------------------- |
| `backend/app/modules/report_narratives/human_storytelling.py`                         | New versioned human tone contract |
| `backend/app/modules/report_narratives/__init__.py`                                   | Export contract helpers           |
| `backend/tests/unit/test_report_narratives/test_human_storytelling_contract.py`       | Contract tests                    |
| `docs/features/E15-self-report-human-storytelling/S01-human-storytelling-contract.md` | Story status/details              |
| `docs/features/E15-self-report-human-storytelling/S02-staged-prompts-v2.md`           | Reference to S01 contract         |
| `docs/features/E15-self-report-human-storytelling/FEATURE.md`                         | Story status                      |
| `docs/SRS/SRS-E15-self-report-human-storytelling.md`                                  | Contract reference                |

## Acceptance criteria

- [x] Tone guide names concrete banned patterns: канцелярит, generic astrology prose, unsupported therapy language.
- [x] Tone guide gives at least 5 before/after examples.
- [x] Contract says evidence remains source of truth but should be progressively disclosed.
- [x] Contract defines hero as recognition-first, not calculation-first.
- [x] Contract is referenced by S02 prompt work.

## Verification

```bash
docker compose run --rm backend sh -lc 'cd /app && python -m pytest tests/unit/test_report_narratives/test_human_storytelling_contract.py -q'
# 5 passed
```
