# Story E10.S07: Glossary / term help для терминов отчёта

**Feature:** [Report UX Redesign — понятный self-report](Archemap/docs/features/v1/E10-report-ux-redesign/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Термины вроде ASC, дом, аспект, Model A и evidence trail не должны появляться без объяснения. Эта story добавляет общий механизм подсказок, независимый от перестройки layout.

## Что сделать

1. Создать `TermHelp` trigger для inline терминов.
2. Создать `GlossaryModal`/drawer.
3. Desktop: popover/modal; mobile: drawer/bottom sheet.
4. Добавить glossary entries для минимального набора терминов.
5. Для каждого entry хранить: определение, почему важно в отчёте, пример.
6. Подключить term-help к основным report sections.

## Минимальный glossary

- Натальная карта
- Солнце
- Луна
- Асцендент
- Дом
- Аспект
- Орб
- Стихия
- Модальность
- Архетип
- Соционический тип
- Model A
- Confidence
- Evidence trail

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/components/glossary/term-help.tsx` | Создать |
| `frontend/src/components/glossary/glossary-modal.tsx` | Создать |
| `frontend/src/lib/glossary/report-glossary.ts` | Создать словарь терминов |
| `frontend/src/components/report/*` | Подключить term-help где используются термины |

## Критерии приёмки

- [x] Все минимальные термины имеют glossary entry.
- [x] У каждого entry есть определение, значение для отчёта и пример.
- [x] Desktop interaction работает через popover/modal.
- [x] Mobile interaction работает через drawer/bottom sheet или адаптивный modal.
- [x] Термины в report sections имеют `TermHelp` trigger.
- [x] `npx eslint .`, `npx prettier --check .` и `npx tsc --noEmit --pretty false` проходят без ошибок.
