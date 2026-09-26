# E19: Astrotype Career Report

## Статус

🟡 В работе — требуется публикация Career на stage по S14; после неё остаются canary/production evidence S12

## Цель

Создать персональный профессиональный отчёт на основе уже рассчитанной натальной карты и ответов пользователя. Отчёт должен объяснять профессиональную механику человека — рабочий стиль, решения, мотивацию, лидерство, среду, классы ролей и траектории — а не назначать профессию по одному астрологическому фактору.

## Канонический источник

- Design/architecture: [`../../design/astrotype_career_report.md`](../../design/astrotype_career_report.md)
- Canonical UI sample: [`../../design/astrotype-career-report-sample.html`](../../design/astrotype-career-report-sample.html)
- SRS: [`../../SRS/SRS-E19-career-report.md`](../../SRS/SRS-E19-career-report.md)

При расхождении короткого Story с продуктовым смыслом источником истины является SRS вместе с design-документом. Формулы, DTO и миграции должны быть зафиксированы тестами до production rollout.

## Продуктовая формула

```text
Natal Chart
→ evidence-backed Astrological Factors
→ deterministic Career Dimensions
→ Control Questions
→ Profile Resolver
→ Career Archetypes + Work Environment
→ Role Families + Career Paths
→ curated Interpretation Facts
→ modular LLM narrative
→ Career Report
```

LLM не получает сырую натальную карту и не вычисляет scores, архетипы, роли или карьерные траектории. Она превращает заранее рассчитанный, ограниченный и evidence-backed объект в связный текст.

## Пользовательская ценность

Career Report отвечает не «кем вам стать», а:

- как пользователь решает задачи и принимает решения;
- какие условия усиливают или снижают эффективность;
- какой баланс автономии, структуры, риска и взаимодействия ему подходит;
- как разделяются лидерский потенциал и желание управлять людьми;
- какие классы ролей и карьерные переходы согласуются с профилем;
- где вывод подтверждён многими сигналами, а где требует осторожной формулировки.

## MVP scope

### Вход

- готовая Astrotype v2 `NatalChart` и связанные persisted facts/evidence;
- версия scoring/reference rules;
- 8–12 обязательных контрольных вопросов;
- ответы пользователя и контекст: текущая деятельность, опыт, цель изменения карьеры.

### 12 Career Dimensions

1. Leadership
2. Analytical Thinking
3. Systems Thinking
4. Communication
5. Creativity
6. Structure
7. Autonomy
8. Risk Tolerance
9. People Orientation
10. Innovation
11. Long-Term Focus
12. Execution

### Выход

1. Профессиональный профиль
2. Рабочий стиль
3. Сильные стороны
4. Принятие решений
5. Лидерство и влияние
6. Оптимальная рабочая среда
7. Условия риска/снижения эффективности
8. Top-3 профессиональных архетипа
9. Семейства ролей
10. Карьерные траектории

## После MVP

- Adaptive Questions.
- Entrepreneurship, Competition, Learning Orientation, Influence, Adaptability и расширенный Decision Making.
- Более точный role matching.
- CV, skills, образование, текущая должность и опыт как отдельный consent-based слой.
- Career Change, Leadership Profile, Entrepreneurship Profile, Team/Manager Compatibility.
- Career Timing только после отдельной фичи транзитов; не входит в натальный MVP.

## Вне области работ

- Прямая формула «планета/знак → профессия».
- Гарантии трудоустройства, дохода или профессионального успеха.
- Диагностика личности, психического здоровья или профпригодности.
- Использование соционики, MBTI или Model A в Career v1.
- Автоматический анализ CV/соцсетей без отдельного согласия.
- Самостоятельное вычисление астрологических или карьерных фактов LLM-моделью.
- Перезапись базовой натальной карты, Self-отчёта или исторических Career-версий.
- Синхронное ожидание полного narrative в одном HTTP-запросе.

## Текущий implementation gap

В репозитории уже есть legacy product `career`, цена `career_full`, synchronous `/reports/generate`, v1 rules/resolver и простой Career reader. Этот путь:

- использует legacy `ChartSnapshot`/ruleset `career/v1`, а не нормализованный v2 Career pipeline;
- не содержит 12 версионированных dimensions с независимыми evidence/confidence;
- не собирает обязательные контрольные ответы и contradictions;
- ожидает готовый ответ за 30 секунд;
- не предоставляет durable generation/status lifecycle;
- не соответствует целевому layered report contract.

Legacy baseline не закрывает ни одну Story E19. Его нельзя расширять как скрытый compatibility path: необходимо либо явно мигрировать, либо выключить после rollout.

## Доступ и монетизация

Career — специализированный отчёт. Целевой доступ должен использовать единую account-level policy E8: активный Plus для всех не-basic отчётов. Текущий one-time SKU `career_full` — зафиксированное расхождение, которое нужно решить в S01 до реализации checkout/entitlement. Нельзя одновременно обещать две конфликтующие модели доступа.

## Критерии приёмки Feature

- [x] Career использует существующую v2 натальную карту и не пересчитывает её без изменения birth data/engine version.
- [x] Все 12 MVP dimensions рассчитываются детерминированно по нескольким независимым сигналам.
- [x] Каждый score имеет evidence, confidence, scoring version и объяснимый breakdown.
- [x] Контрольные вопросы versioned; ответы пользователя отделены от астрологических сигналов.
- [x] Profile Resolver сохраняет подтверждения, противоречия и предпочтения, не «исправляя» ответы пользователя.
- [x] Top-3 archetypes, environment, anti-environment, role families и paths строятся детерминированно.
- [x] Роли сначала определяются как классы; профессии приводятся только как примеры с уровнем соответствия.
- [x] LLM получает только curated interpretation facts и section contract, не raw chart и не полный unrestricted payload.
- [x] Отчёт доступен с `deterministic_ready`; narrative загружается по секциям асинхронно.
- [x] Web reader и PDF используют один persisted report payload и одинаковый порядок секций.
- [x] Backend ownership и Plus-access policy покрывают create/read/status/regenerate/PDF.
- [x] Исторические версии, вопросы/ответы, scores, evidence и prompt/scoring versions сохраняются.
- [x] Anti-generic, contradiction, evidence, overclaim и profession-prescription validators проходят локальные suites.
- [ ] Staging smoke доказывает полный questionnaire → deterministic → narrative → reader/PDF flow.

## Stories

| ID  | Story                                                                                            | Статус       |
| --- | ------------------------------------------------------------------------------------------------ | ------------ |
| S01 | [Зафиксировать product/access/migration contract](./S01-product-access-migration-contract.md)    | ✅ Завершено |
| S02 | [Добавить Career storage и versioned schemas](./S02-storage-domain-schemas.md)                   | ✅ Завершено |
| S03 | [Построить factor и Career Dimension engine](./S03-factor-dimension-engine.md)                   | ✅ Завершено |
| S04 | [Реализовать контрольные вопросы и Profile Resolver](./S04-questions-profile-resolver.md)        | ✅ Завершено |
| S05 | [Рассчитать archetypes и рабочую среду](./S05-archetypes-work-environment.md)                    | ✅ Завершено |
| S06 | [Реализовать role matching и карьерные траектории](./S06-role-matching-career-paths.md)          | ✅ Завершено |
| S07 | [Собрать Interpretation Facts и quality gates](./S07-interpretation-facts-quality-gates.md)      | ✅ Завершено |
| S08 | [Добавить modular LLM narrative и assembly](./S08-llm-narrative-assembly.md)                     | ✅ Завершено |
| S09 | [Добавить async Career API и access enforcement](./S09-api-async-access.md)                      | ✅ Завершено |
| S10 | [Создать questionnaire/product UX](./S10-questionnaire-product-ux.md)                            | 🟡 Частично  |
| S11 | [Создать Career reader и PDF](./S11-report-reader-pdf.md)                                        | ✅ Завершено |
| S12 | [Закрыть QA, observability, migration и rollout](./S12-qa-observability-rollout.md)              | 🟡 Частично  |
| S13 | [Подготовить Career rollout / rollback runbook](./S13-rollout-runbook.md)                        | ✅ Завершено |
| S14 | [Опубликовать Career на stage и собрать live evidence](./S14-stage-publication-live-evidence.md) | ⬜ Не начато |

## Порядок реализации

```mermaid
flowchart LR
  S01[S01 contract] --> S02[S02 storage]
  S02 --> S03[S03 dimensions]
  S03 --> S04[S04 questions/resolver]
  S04 --> S05[S05 archetypes/environment]
  S05 --> S06[S06 roles/paths]
  S06 --> S07[S07 interpretation facts]
  S07 --> S08[S08 LLM/assembly]
  S02 --> S09[S09 API/access]
  S04 --> S10[S10 questionnaire UX]
  S08 --> S11[S11 reader/PDF]
  S09 --> S10
  S10 --> S14[S14 stage publication/live evidence]
  S11 --> S14
  S13[S13 rollout runbook] --> S14
  S14 --> S12[S12 final QA/canary/production]
```

## Зависимости

- V2-E2 database foundation.
- V2-E3 natal chart adapter.
- V2-E5 facts/evidence.
- V2-E6 synthesis/outline patterns.
- V2-E7/V2-E15 modular real-provider LLM runtime.
- V2-E10 async API/status lifecycle.
- E6 billing lifecycle and E8 report access policy.
- E10 birth-data refinement for safe regeneration when natal inputs change.

## Документационная готовность

Feature находится в реализации: S01–S09, S11 и документационный runbook S13 завершены. S10 имеет desktop/mobile Chromium+Axe evidence, но ждёт live-backend entitlement smoke. S14 требует публикации точного зелёного Career SHA на `staging.astrotype.ru`, real-provider flow, live entitlement matrix, metrics observation и rollback rehearsal. После S14 в S12 останутся canary и production report/PDF evidence.
