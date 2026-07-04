# LLM narrative architecture for Astrotype reports

Дата: 2026-06-04
Статус: Technical design / до реализации
Область: backend report generation, LLM narrative layer, frontend report UX, PDF
Связанные документы:

- `docs/design/self-report-storytelling.md`
- `docs/design/report-ux-redesign.md`
- `docs/features/E11-llm-report-narrative/FEATURE.md`
- `docs/SRS/SRS-E11-llm-report-narrative.md`
- `docs/features/E14-staged-narrative-pipeline/FEATURE.md`
- `docs/SRS/SRS-E14-staged-narrative-pipeline.md`
- `docs/architecture/report-generation-data-flow.md`

## 1. Главная идея

Сложный мягкий сторителлинг нельзя качественно сделать полностью детерминированным. Для живого Self-отчёта нужны связность, тон, переходы, индивидуальные формулировки, аккуратное описание близости и сексуальности. Это зона LLM.

Но LLM не должна рассчитывать отчёт.

Правильная архитектура — гибридная:

1. Детерминированный слой:
   - натальная карта;
   - планеты, дома, аспекты;
   - соционика;
   - архетипы;
   - evidence trail;
   - confidence;
   - ключевые claims;
   - ограничения качества расчёта.
2. LLM-слой:
   - превращает рассчитанные факты в мягкую историю;
   - связывает блоки между собой;
   - пишет текст в нужном тоне;
   - адаптирует формулировки под продукт: Self / Career / Love;
   - не придумывает новые астрологические или соционические факты.

Главное правило:

> LLM — не источник истины. LLM — редактор и рассказчик.

## 2. Общая схема pipeline

Текущий pipeline отчёта:

```text
POST /reports/generate
  → ChartService.get_or_compute()
  → extract_features()
  → load_ruleset(product)
  → interpret()
  → render_full_report()
  → persist Report
  → PDF task
```

Целевой pipeline:

```text
POST /reports/generate
  → deterministic calculation
  → save Report with structured report_data
  → enqueue LLM narrative generation
  → return report status: generating_narrative
```

Асинхронная Celery-задача:

```text
generate_report_narrative(report_id)
  → load report_data
  → build NarrativeInput
  → call LLM
  → validate response schema
  → save narrative JSON
  → mark report ready
```

Важно: пользователь не должен ждать LLM синхронно внутри HTTP-запроса. Генерация текста должна быть фоновой задачей с явным статусом.

### 2.1 Next evolution: staged pipeline

E11 реализует базовый narrative layer, но глубокий Self report не должен навсегда оставаться одним большим LLM-запросом. Для отчётов, которые не должны звучать как поверхностный гороскоп, целевой next-step описан в E14:

```text
Report.report_data
  → DeepNatalSynthesisBuilder
  → NarrativePlan stage
  → parallel section stages
  → deterministic assembly / optional consistency pass
  → validated SelfNarrative
```

Ключевое отличие: аспекты, дома, планеты и напряжения карты сначала собираются в deterministic `DeepNatalSynthesis`, а LLM получает уже ранжированные aspect patterns, chart dynamics, contradictions, maturity levels and calibration hypotheses. LLM не выбирает важные аспекты из плоского списка и не изобретает психологическую модель с нуля.

Подробный контракт: `docs/features/E14-staged-narrative-pipeline/FEATURE.md`.

## 3. Где живёт LLM-код

Рекомендуемый backend-модуль:

```text
backend/app/modules/llm/
  __init__.py
  provider.py
  schemas.py
  prompts.py
  service.py
  exceptions.py
```

И отдельный слой для narrative reports:

```text
backend/app/modules/report_narratives/
  __init__.py
  models.py
  schemas.py
  service.py
  prompts.py
  provider.py
  router.py
```

Если хочется начать проще, можно сначала добавить:

```text
backend/app/modules/reports/narrative_service.py
```

Но долгосрочно лучше отдельный `report_narratives` модуль, потому что LLM-текст нужно хранить, версионировать и регенерировать независимо от детерминированного отчёта.

## 4. Хранение данных

Отчёт должен иметь две части:

```json
{
  "deterministic": {
    "chart": {},
    "socionics": {},
    "archetype": {},
    "evidence": {},
    "scores": {}
  },
  "narrative": {
    "version": "self_story_v1",
    "model": "gpt-4.1-mini",
    "language": "ru",
    "sections": []
  }
}
```

Лучше хранить narrative отдельно в БД:

```text
reports
  id
  user_id
  profile_id
  product
  status
  report_data
  created_at
  updated_at

report_narratives
  id
  report_id
  product
  prompt_version
  model_provider
  model_name
  status
  content
  input_hash
  error_message
  created_at
  updated_at
```

Преимущества отдельной таблицы:

- можно регенерировать только LLM-текст;
- можно хранить несколько версий нарратива;
- можно сравнивать `prompt_version`;
- можно откатить плохую генерацию;
- можно не трогать детерминированный расчёт.

## 5. NarrativeInput вместо сырого report_data

LLM не должна получать весь сырой отчёт как есть. Нужно собрать специальный DTO — очищенный вход для генерации текста.

Пример схемы:

```python
class NarrativeInput(BaseModel):
    product: Literal["self", "career", "love"]
    language: Literal["ru"]
    profile: NarrativeProfile
    calculation_quality: CalculationQuality
    key_facts: list[AstroFact]
    key_aspects: list[AspectFact]
    socionics: SocionicsSummary
    archetype: ArchetypeSummary
    strengths: list[EvidenceBackedClaim]
    risks: list[EvidenceBackedClaim]
    relationship_patterns: list[EvidenceBackedClaim]
    sexuality_patterns: list[EvidenceBackedClaim]
    development_recommendations: list[EvidenceBackedClaim]
    product_boundaries: ProductBoundaries
```

Пример входа:

```json
{
  "product": "self",
  "language": "ru",
  "profile": {
    "name": "Алексей",
    "birth_date": "1991-08-29",
    "birth_time_quality": "exact",
    "birth_place": "Москва"
  },
  "key_facts": [
    {
      "id": "mercury_venus_jupiter_leo_8",
      "label": "Меркурий, Венера и Юпитер во Льве в 8 доме",
      "meaning": "выразительное мышление, эмоциональное влияние, интерес к скрытым мотивам"
    }
  ],
  "key_aspects": [
    {
      "id": "moon_trine_mercury",
      "label": "Луна тригон Меркурий",
      "orb": "0°50′",
      "meaning": "связь эмоций и речи"
    }
  ],
  "socionics": {
    "type": "EIE",
    "type_ru": "ЭИЭ",
    "confidence_label": "средняя",
    "explanation": "этико-интуитивная выразительность"
  },
  "product_boundaries": {
    "career_policy": "В Self-отчёте карьеру затрагивать кратко, не давать список профессий, деньги, стратегию роста и управленческий разбор. В конце добавить CTA на Career."
  }
}
```

LLM получает не сырую карту, а уже рассчитанные и подготовленные факты.

## 6. Structured output: JSON, не Markdown

LLM должна возвращать JSON строго по схеме, а не свободный Markdown.

Пример целевого ответа:

```json
{
  "title": "Ваш внутренний портрет",
  "hero": {
    "headline": "...",
    "summary": "...",
    "bullets": []
  },
  "sections": [
    {
      "id": "main_formula",
      "title": "Главная формула личности",
      "body": "...",
      "evidence_notes": [
        {
          "claim": "...",
          "facts": ["moon_trine_mercury", "venus_leo_8"]
        }
      ]
    }
  ],
  "career_cta": {
    "title": "Отдельный отчёт Career",
    "body": "...",
    "bullets": []
  },
  "technical_disclaimer": "..."
}
```

Почему JSON лучше Markdown:

- проще валидировать;
- проще рендерить в дизайне;
- проще скрывать/раскрывать сноски;
- проще менять порядок секций;
- проще строить PDF;
- проще писать regression checks.

## 7. Prompt contract

Для каждого продукта нужна своя версия prompt-а:

```text
backend/app/modules/report_narratives/prompts/
  self_story_v1.md
  career_story_v1.md
  love_story_v1.md
```

### System role

```text
Ты пишешь персональный психологически мягкий отчёт на русском языке.
Ты не рассчитываешь астрологию.
Ты используешь только переданные факты.
Ты не добавляешь новые положения планет, аспекты, дома, типы или диагнозы.
Ты не говоришь медицинским, фаталистичным или мистическим языком.
```

### Product boundary для Self

```text
Это Self-отчёт.
Главная тема: личность, восприятие, эмоции, мышление, отношения, близость, сексуальность, развитие.
Работу и карьеру затрагивай кратко, только как проявление личности.
Не давай список профессий, денежную стратегию, карьерный план, управленческий профиль.
В конце добавь CTA на отдельный Career-отчёт.
```

### Tone

```text
Тон: мягкий, взрослый, точный, без эзотерического тумана.
Не использовать: "энергии Вселенной", "предначертано", "судьба заставляет".
Не писать диагнозы.
Не обвинять пользователя.
Уязвимости описывать как напряжение сильных сторон.
```

### Evidence discipline

```text
Каждый важный вывод должен ссылаться на один или несколько переданных fact_id.
Если факта нет во входных данных, не делай вывод.
```

## 8. Валидация LLM-ответа

Ответ LLM нельзя сразу сохранять как готовый отчёт. После генерации нужны проверки:

1. JSON валиден.
2. Все обязательные секции есть.
3. Порядок секций правильный.
4. Нет запрещённых слов и формулировок.
5. Нет карьерного deep dive в Self.
6. Все `evidence_refs` существуют во входных данных.
7. Нет новых планет, аспектов, домов или типов, которых не было во входе.
8. Текст на русском.
9. Нет медицинских диагнозов.
10. Нет гарантий, фатализма и предсказательной категоричности.

Если проверка не прошла:

- сделать повторный LLM-call с repair prompt;
- или fallback на детерминированный шаблон;
- или выставить `narrative_failed`, но UI не должен висеть бесконечно.

Пример validator-а:

```python
def validate_self_narrative(
    narrative: SelfNarrative,
    narrative_input: NarrativeInput,
) -> list[str]:
    errors = []

    if not narrative.career_cta:
        errors.append("Self report must include career CTA")

    if contains_forbidden_career_deep_dive(narrative):
        errors.append("Self report contains career deep dive")

    if has_unknown_evidence_refs(narrative, narrative_input):
        errors.append("Unknown evidence refs")

    return errors
```

## 9. Статусы генерации

Чтобы не было бесконечной генерации, нужны явные статусы:

```text
pending
calculating
deterministic_ready
generating_narrative
ready
failed
narrative_failed
```

Дополнительные поля:

```text
generation_started_at
generation_finished_at
generation_error
generation_attempts
```

Frontend не должен бесконечно показывать spinner.

Правила UI:

- если статус `generating_narrative` длится дольше 90 секунд, показать сообщение: «Текстовый отчёт ещё собирается»;
- дать кнопку «Обновить»;
- дать fallback «Показать технический отчёт»;
- дать кнопку «Повторить генерацию»;
- если задача упала, показать `narrative_failed`, а не вечную генерацию.

Пример ответа при частичном сбое:

```json
{
  "status": "narrative_failed",
  "message": "Не удалось создать текстовую версию отчёта. Базовый расчёт доступен."
}
```

Отчёт не должен пропадать из-за LLM.

## 10. API

### Генерация отчёта

```http
POST /api/v1/reports/generate
```

Ответ:

```json
{
  "id": "report_uuid",
  "product": "self",
  "status": "generating_narrative"
}
```

### Получение отчёта

```http
GET /api/v1/reports/{report_id}
```

Пока narrative генерируется:

```json
{
  "id": "...",
  "product": "self",
  "status": "generating_narrative",
  "deterministic": {},
  "narrative": null
}
```

Когда готово:

```json
{
  "id": "...",
  "product": "self",
  "status": "ready",
  "deterministic": {},
  "narrative": {
    "version": "self_story_v1",
    "sections": []
  }
}
```

### Регенерация только LLM-текста

```http
POST /api/v1/reports/{report_id}/narrative/regenerate
```

Опциональное тело:

```json
{
  "style": "soft",
  "length": "full"
}
```

На MVP лучше не давать пользователю много вариантов. Один качественный стиль важнее набора настроек.

## 11. Абстракция LLM provider

Бизнес-логика не должна напрямую зависеть от OpenAI или другого провайдера.

Интерфейс:

```python
class LLMProvider(Protocol):
    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
        temperature: float,
        max_tokens: int,
    ) -> BaseModel:
        ...
```

Реализации:

```text
OpenAIProvider
AnthropicProvider
OpenRouterProvider
MockLLMProvider
```

Настройки:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
LLM_API_KEY=...
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
LLM_ENABLED=true
```

Для dev/test:

```env
LLM_PROVIDER=mock
```

Mock должен возвращать фиксированный JSON, чтобы тесты не ходили в сеть.

## 12. LLM только на backend

LLM-вызовы должны быть только на backend.

Причины:

- нельзя светить API key в браузере;
- нужен контроль prompt-а;
- нужна валидация;
- нужен retry;
- нужен cache;
- нужен audit;
- нужны лимиты;
- нужна защита от prompt injection.

Frontend только показывает статус и результат.

## 13. Кэширование

LLM дорогая и недетерминированная, поэтому нужен `input_hash`.

```python
input_hash = sha256(
    json.dumps(narrative_input.model_dump(), sort_keys=True).encode()
).hexdigest()
```

Если уже есть narrative с тем же набором:

```text
report_id + product + prompt_version + input_hash + model_name
```

то не генерировать заново.

Это защищает от повторных кликов, перезагрузок и дублей фоновых задач.

## 14. Версионирование prompt-ов

В narrative нужно хранить:

```json
{
  "prompt_version": "self_story_v1",
  "model": "gpt-4.1-mini",
  "input_hash": "...",
  "generated_at": "..."
}
```

Когда меняется структура, тон или product boundary, создаётся новая версия:

```text
self_story_v2
```

Старые отчёты остаются на v1, новые генерируются на v2. При необходимости можно добавить ручную регенерацию.

## 15. Контроль качества

### 15.1 Schema validation

Pydantic проверяет структуру LLM-ответа.

### 15.2 Rule validation

Код проверяет продуктовые ограничения:

- Self содержит Career CTA;
- Self не содержит глубокий карьерный разбор;
- sexuality section не графичная и не медицинская;
- evidence references существуют;
- обязательные секции есть;
- технические термины не доминируют в первом экране.

### 15.3 LLM-as-judge позже

Можно добавить второй LLM-вызов для проверки:

- мягкости тона;
- связности;
- отсутствия фатализма;
- соответствия продукту.

На MVP лучше не добавлять второй LLM-вызов. Сначала достаточно deterministic validators.

## 16. Антигаллюцинации

Правила:

1. В input передавать только разрешённые факты.
2. Каждый section должен ссылаться на `fact_id`.
3. После ответа проверять, что все `fact_id` существуют.
4. Запрещать новые астрологические термины, которых не было во входе.
5. Запрещать точные утверждения без evidence.
6. Не давать LLM raw birth data как единственную основу.
7. Не просить «проанализируй карту».
8. Просить: «напиши текст по этим уже рассчитанным выводам».

Плохой prompt:

```text
Вот дата рождения. Сделай психологический отчёт.
```

Хороший prompt:

```text
Вот список утверждений, уже рассчитанных системой.
Напиши связный Self-отчёт.
Не добавляй новых астрологических фактов.
Каждый вывод связывай с переданными evidence id.
```

## 17. Safety-контур для сексуальности

Раздел сексуальности допустим, но должен быть аккуратным.

Правила:

- только для взрослых пользователей;
- не писать графично;
- не давать медицинских или психиатрических диагнозов;
- не делать выводов о травмах как фактах;
- не использовать манипулятивный язык;
- не писать «вам нужно» / «вы обязаны»;
- формулировать как психологический стиль желания и близости.

Prompt-фрагмент:

```text
Раздел "Сексуальность" должен быть взрослым, мягким, неграфичным.
Не описывать сексуальные практики.
Не давать медицинских диагнозов.
Не делать утверждений о травме, насилии или расстройствах.
Писать про стиль желания, доверие, близость, контроль, уязвимость, эмоциональную интенсивность.
```

## 18. Frontend rendering

Frontend должен рендерить narrative-first отчёт, а не только raw deterministic блоки.

Пример структуры:

```tsx
<ReportNarrativePage report={report} />
```

Внутри:

```tsx
<HeroSection data={narrative.hero} />
<SummarySection data={narrative.summary} />
<NarrativeSection id="main_formula" />
<NarrativeSection id="world_perception" />
<NarrativeSection id="strengths" />
<NarrativeSection id="vulnerabilities" />
<NarrativeSection id="relationships" />
<NarrativeSection id="sexuality" />
<NarrativeSection id="development" />
<CareerCTA data={narrative.career_cta} />
<TypologySection collapsed />
<TechnicalDetails collapsed />
```

Если `narrative == null`:

```tsx
if (report.status === "generating_narrative") {
  return <ReportGenerationProgress />;
}
```

Если `narrative_failed`:

```tsx
return (
  <>
    <Warning>Текстовый отчёт не удалось создать.</Warning>
    <DeterministicReportFallback />
    <Button>Повторить генерацию</Button>
  </>
);
```

## 19. PDF

PDF должен строиться из того же `narrative JSON`, а не отдельным LLM-вызовом.

```text
LLM → narrative JSON → frontend report
                   → PDF template
```

Не делать отдельную генерацию текста для PDF.

## 20. Очередь и retry

LLM нельзя вызывать прямо в HTTP endpoint. Нужно использовать Celery.

```python
@celery_app.task(bind=True, max_retries=2)
def generate_report_narrative_task(self, report_id: str):
    ...
```

Timeout:

```env
LLM_TIMEOUT_SECONDS=60
```

Retry для:

- network timeout;
- 429;
- 5xx provider error.

Не retry для:

- invalid input;
- validation failed после repair;
- user/report not found.

## 21. MVP-план внедрения

### Этап 1. Документация и контракт

Development docs для реализации разбиты на атомарные stories в `docs/features/E11-llm-report-narrative/`; SRS-контракт находится в `docs/SRS/SRS-E11-llm-report-narrative.md`.

- Зафиксировать `SelfNarrative` schema.
- Зафиксировать `NarrativeInput`.
- Зафиксировать prompt `self_story_v1`.
- Зафиксировать product boundaries: Self vs Career.

### Этап 2. Backend LLM infrastructure

- `LLMProvider`.
- `OpenAIProvider` или `OpenRouterProvider`.
- `MockLLMProvider`.
- settings.
- unit tests без реального LLM.

### Этап 3. Narrative generation service

- собрать `NarrativeInput` из текущего `report_data`;
- вызвать LLM;
- провалидировать JSON;
- сохранить `report_narrative`.

### Этап 4. Report statuses

- `generating_narrative`;
- `ready`;
- `narrative_failed`;
- retry endpoint.

Это особенно важно, чтобы не было бесконечной генерации.

### Этап 5. Frontend

- narrative-first рендер отчёта;
- fallback на deterministic report;
- polling статуса;
- timeout UI;
- retry button.

### Этап 6. PDF

- PDF из narrative JSON.

## 22. Пример схемы narrative

```python
class EvidenceNote(BaseModel):
    claim: str
    fact_ids: list[str]


class NarrativeSection(BaseModel):
    id: str
    title: str
    body: str
    bullets: list[str] = []
    evidence_notes: list[EvidenceNote] = []


class CareerCTA(BaseModel):
    title: str
    body: str
    bullets: list[str]
    button_label: str


class SelfNarrative(BaseModel):
    title: str
    hero: NarrativeSection
    sections: list[NarrativeSection]
    career_cta: CareerCTA
    final_summary: str
```

## 23. Пример сервиса

```python
class ReportNarrativeService:
    def __init__(
        self,
        db: AsyncSession,
        llm_provider: LLMProvider,
    ) -> None:
        self.db = db
        self.llm_provider = llm_provider

    async def generate_for_report(self, report_id: UUID) -> ReportNarrative:
        report = await self._get_report(report_id)

        narrative_input = build_narrative_input(report)
        input_hash = compute_input_hash(narrative_input)

        cached = await self._find_cached(
            report_id=report.id,
            prompt_version="self_story_v1",
            input_hash=input_hash,
        )
        if cached:
            return cached

        prompt = build_self_story_prompt(narrative_input)

        result = await self.llm_provider.generate_structured(
            system_prompt=SELF_SYSTEM_PROMPT,
            user_prompt=prompt,
            schema=SelfNarrative,
            temperature=0.4,
            max_tokens=6000,
        )

        validate_self_narrative(result, narrative_input)

        return await self._save_narrative(
            report=report,
            content=result,
            input_hash=input_hash,
            prompt_version="self_story_v1",
        )
```

## 24. Выбор модели

Для MVP:

- модель уровня `gpt-4.1-mini` или аналог через OpenRouter;
- temperature `0.3–0.5`;
- structured output / JSON schema;
- timeout 60 секунд;
- max tokens 5000–8000.

Для премиального отчёта позже:

- более сильная модель;
- более длинный output;
- возможно второй pass на редактуру.

На старте важнее стабильность:

- валидный JSON;
- нет галлюцинаций;
- product boundaries соблюдены;
- генерация не зависает;
- стоимость контролируема.

## 25. Что остаётся детерминированным

Детерминированно:

- расчёт карты;
- соционика;
- архетип;
- список facts;
- список claims;
- evidence trail;
- порядок секций;
- product boundaries;
- валидация;
- fallback.

Недетерминированно:

- формулировки;
- связки между абзацами;
- тон;
- глубина примеров;
- мягкость подачи.

Для повторяемости:

- использовать низкую temperature (`0.3`);
- кэшировать результат по `input_hash`;
- хранить `prompt_version` и `model_name`.

## 26. Главный вывод

LLM нельзя встраивать как магический генератор отчёта.

Нужно встраивать как контролируемый narrative renderer:

```text
Birth data
  → deterministic astrology/socionics/rules
  → structured claims with evidence
  → LLM writes narrative JSON
  → validators check it
  → frontend renders controlled sections
```

Так продукт получает лучшее из двух миров:

- расчёт остаётся проверяемым;
- отчёт становится живым;
- продуктовые границы сохраняются;
- Career не съедается Self-отчётом;
- пользователь не видит хаос из графиков и процентов;
- технические детали остаются доступны, но не ломают чтение.

Коротко:

> Надо не заменить движок на LLM, а добавить LLM поверх движка как слой сторителлинга.
