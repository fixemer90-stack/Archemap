# Documentation Standard

Каждая фича разбита на **Features** и **Stories**.

## Иерархия

```
docs/features/
├── <feature-id>-<slug>/
│   ├── FEATURE.md          # Описание фичи: ценность, критерии, зависимости
│   ├── S01-<slug>.md       # Story 1
│   ├── S02-<slug>.md       # Story 2
│   └── ...
```

## Feature (FEATURE.md)

Фича = конкретная ценность для пользователя или платформы. Содержит:

- **Цель**: что даёт эта фича
- **Критерии приёмки**: что считается «сделано»
- **Зависимости**: от каких фич зависит
- **Stories**: список с ссылками

## Story (S01-*.md)

Story = атомарный шаг реализации. Содержит:

- **Контекст**: зачем этот шаг нужен
- **Что сделать**: конкретные изменения
- **Файлы**: какие файлы затрагиваются
- **Критерии приёмки**: что проверяем
- **Статус**: `⬜ Не начато` / `🟡 В процессе` / `✅ Готово`

## Правила

1. Без документации — нет кода. Каждый PR должен ссылаться на Story.
2. Story не делается «частично» — либо все критерии выполнены, либо Story не закрыта.
3. Фича закрывается только когда все Stories выполнены.

---

## Astrotype v2 feature set

Cloud-core multi-client v2 feature documentation. This is the active implementation index; historical v1 docs are archived under `docs/archive/v1/` and are not active contracts.

Canonical v2 contract:

- natal-only, no socionics/Model A/MBTI in v2 payloads;
- existing auth/profile infrastructure is reused, not rewritten for v2;
- registration/profile completion can trigger deterministic natal calculation when enough birth data is present;
- `deterministic_ready` foundation is renderable before LLM narrative completion;
- old v1 REST/report/socionics methods and compatibility aliases are forbidden from the active v2 surface.

Active v2 features:

- `V2-E1` — [Architecture & contracts](./E16-v2-e1-architecture-contracts/FEATURE.md)
- `V2-E2` — [Database foundation](./E16-v2-e2-database-foundation/FEATURE.md)
- `V2-E3` — [Natal chart adapter](./E16-v2-e3-natal-chart-adapter/FEATURE.md)
- `V2-E4` — [Reference data](./E16-v2-e4-reference-data/FEATURE.md)
- `V2-E5` — [Fact extraction](./E16-v2-e5-fact-extraction/FEATURE.md)
- `V2-E6` — [Synthesis & outline](./E16-v2-e6-synthesis-outline/FEATURE.md)
- `V2-E7` — [Modular LLM generation](./E16-v2-e7-modular-llm-generation/FEATURE.md)
- `V2-E8` — [Final report assembly](./E16-v2-e8-final-report-assembly/FEATURE.md)
- `V2-E9` — [Infographics & calculation layer](./E16-v2-e9-infographics-factual-basis/FEATURE.md)
- `V2-E10` — [API & async runtime](./E16-v2-e10-api-async-runtime/FEATURE.md)
- `V2-E11` — [Web responsive reader](./E16-v2-e11-web-responsive-reader/FEATURE.md)
- `V2-E12` — [Android MVP path](./E16-v2-e12-android-mvp-path/FEATURE.md)
- `V2-E13` — [Desktop thin client decision](./E16-v2-e13-desktop-thin-client-decision/FEATURE.md)
- `V2-E14` — [QA, smoke, rollout](./E16-v2-e14-qa-smoke-rollout/FEATURE.md)
- `V2-E15` — [LLM runtime integration](./E16-v2-e15-llm-runtime-integration/FEATURE.md) ([workflow](./E16-v2-e15-llm-runtime-integration/WORKFLOW.md), [API](./E16-v2-e15-llm-runtime-integration/API.md))
- `V2-E16` — [Narrative depth quality](./E16-v2-e16-narrative-depth-quality/FEATURE.md)
- `V2-E17` — [Section evidence grounding remediation](./E16-v2-e17-section-evidence-grounding/FEATURE.md) ([workflow](./E16-v2-e17-section-evidence-grounding/WORKFLOW.md))
- `V2-E18` — [Product surface redesign: homepage, dashboard, billing](./E16-v2-e18-product-surface-redesign/FEATURE.md)

Umbrella SRS: `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`
Narrative depth contract: `docs/architecture/astrotype-v2-narrative-depth-contract.md`
Section evidence grounding remediation: `docs/architecture/astrotype-v2-section-evidence-grounding.md`
Deterministic-first delivery contract: `docs/architecture/astrotype-v2-deterministic-first-delivery.md`
Current payment confirmation flow: `docs/architecture/current-payment-confirmation-flow.md`
Billing/payment feature contract: `docs/features/E6-billing-subscriptions/FEATURE.md`
Account tier foundation: `docs/architecture/account-tier-role-foundation.md`
Product surface redesign samples: `docs/design/astrotype-v2-homepage-sample.html`, `docs/design/astrotype-v2-dashboard-sample.html`, `docs/design/astrotype-v2-billing-sample.html`
