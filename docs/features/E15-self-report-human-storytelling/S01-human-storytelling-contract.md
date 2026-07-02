# S01 — Human Storytelling Contract and Tone Guide

Статус: ⬜ Не начато
Эпик: `E15-self-report-human-storytelling`

## Контекст

Текущий Self report evidence-backed, но звучит слишком сухо. Перед изменением prompt/code нужен явный storytelling contract: какой язык считается человеческим, какой — “душным”, и как сохранять точность без канцелярита.

## Что сделать

1. Создать human tone guide для Self narrative.
2. Зафиксировать allowed/prohibited language patterns.
3. Добавить examples “до/после” для hero и каждой ключевой секции.
4. Определить минимальный storytelling unit:
   - recognition;
   - lived manifestation;
   - inner tension/protection;
   - mature expression;
   - soft question.
5. Обновить feature/SRS ссылки так, чтобы E15 не конфликтовал с E13/E14.

## Затрагиваемые файлы

| Файл                                                           | Изменение                                     |
| -------------------------------------------------------------- | --------------------------------------------- |
| `docs/features/E15-self-report-human-storytelling/FEATURE.md`  | Feature contract                              |
| `docs/features/E15-self-report-human-storytelling/WORKFLOW.md` | Product workflow and examples                 |
| `docs/SRS/SRS-E15-self-report-human-storytelling.md`           | Requirements                                  |
| `backend/app/modules/report_narratives/prompts/`               | Later prompt examples reference this contract |
| `backend/tests/unit/test_report_narratives/`                   | Later tests enforce tone markers              |

## Acceptance criteria

- [ ] Tone guide names concrete banned patterns: канцелярит, generic astrology prose, unsupported therapy language.
- [ ] Tone guide gives at least 5 before/after examples.
- [ ] Contract says evidence remains source of truth but should be progressively disclosed.
- [ ] Contract defines hero as recognition-first, not calculation-first.
- [ ] Contract is referenced by S02 prompt work.

## Verification

```bash
git diff --check -- docs/features/E15-self-report-human-storytelling docs/SRS/SRS-E15-self-report-human-storytelling.md
```
