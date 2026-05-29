# Feature E4: Rules & Content

## Цель

Rule-based движок интерпретации: YAML-правила, версионированные шаблоны, локализация. Детерминированный scoring с explainability.

## Зависимости

`E3`

## Критерии приёмки

- [ ] RuleSetVersion: иммутабельные версии правил, привязка к вертикали
- [ ] TemplateVersion: Jinja2-шаблоны, версионирование
- [ ] Rule engine: JSON Logic условия → скор → категория
- [ ] Content Resolver: набор правил → текст отчёта
- [ ] Локализация RU/EN с fallback
- [ ] CMS для редакторов (опционально)

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [RuleSetVersion: модель версионирования правил, published_at, несколько версий сосуществуют](S01-ruleset-version.md) | ⬜ Не начато |
| S02 | [TemplateVersion: Jinja2-шаблоны, версионирование, привязка к вертикали](S02-template-version.md) | ⬜ Не начато |
| S03 | [Rule engine: JSON Logic условия, weighted scoring, confidence model, evidence trail](S03-rule-engine.md) | ⬜ Не начато |
| S04 | [Content Resolver: маппинг правил → шаблоны, fallback при пустых правилах](S04-content-resolver.md) | ⬜ Не начато |
| S05 | [Локализация: RU/EN для правил и шаблоны, fallback на RU](S05-localization.md) | ⬜ Не начато |
| S06 | [CMS для редакторов: UI для правил и шаблонов, preview генерации](S06-cms-editor.md) | ⬜ Не начато |
