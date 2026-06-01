# Story E4.S06: CMS для редакторов

**Feature:** [Rules & Content](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Admin UI для редактирования YAML-правил и шаблонов. Preview генерации отчёта на лету.

## Что сделать

- Admin dashboard для просмотра/редактирования правил
- Валидация YAML перед сохранением
- Preview: выбрать profile → запустить interpret → показать результат
- Publish workflow: draft → review → published
- Версионирование: создание новой версии из текущей

## Затрагиваемые файлы

_Требует проектирования._

## Критерии приёмки

- [ ] UI для просмотра правил (read-only)
- [ ] UI для редактирования правил (YAML editor)
- [ ] Валидация YAML (schema + dry-run)
- [ ] Preview генерации на реальных данных
- [ ] Publish workflow
- [ ] Версионирование
- [ ] Тесты
- [ ] ruff, mypy, eslint — 0 ошибок

## Примечания

В backlog. Требует:
- Admin role в auth
- YAML editor component (Monaco/CodeMirror)
- Schema validation (JSON Schema для YAML)
- Dry-run endpoint для preview
