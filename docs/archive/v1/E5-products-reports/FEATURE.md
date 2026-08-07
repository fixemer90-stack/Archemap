# Feature E5: Products & Reports

## Цель

Четыре продуктовых отчёта (Self, Love, Child, Career) с PDF-экспортом, версионированием и API. Источник истины для отчёта — JSON в PostgreSQL; PDF рендерится on demand.

## Зависимости

`E3`, `E4`

## Критерии приёмки

- [ ] Self-отчёт: солнце, луна, асцендент, доминанты, архетип
- [ ] Love: синастрия, совместимость 0–100, триггеры
- [ ] Child: темперамент, сильные стороны, советы по воспитанию
- [ ] Career: топ-5 профессий, сильные/слабые стороны
- [ ] Версионирование отчётов: история, immutable по умолчанию
- [x] PDF-генерация on demand из сохранённого JSON (WeasyPrint)
- [ ] REST API: POST generate, GET list/detail

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Self-отчёт: архетипический портрет, evidence-trail, PDF, Celery-задача](S01-self-report.md) | ✅ Готово |
| S02 | [Love: синастрия двух карт, communication sync, friction polarity, pair report](S02-love-compatibility.md) | ⬜ Не начато |
| S03 | [Child: детский профиль, рекомендации родителю, мягкий tone, без диагнозов](S03-child-profile.md) | ⬜ Не начато |
| S04 | [Career: сильные стороны, роли, рабочая среда, anti-patterns, growth map](S04-career-profile.md) | ✅ Готово |
| S05 | [Версионирование: при изменении профиля — новый artifact, старый сохраняется](S05-report-versioning.md) | ✅ Готово |
| S06 | [Хранилище: JSON в PostgreSQL как source of truth, PDF on demand без S3/MinIO](S06-report-storage.md) | ✅ Готово |
| S07 | [REST API отчётов: POST generate, GET list/detail, pagination, permissions](S07-report-api.md) | ✅ Готово |
