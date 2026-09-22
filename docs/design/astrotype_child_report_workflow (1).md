# Astrotype — Child Report & Workflow

## 1. Цель фичи

**Child Report** — персональный вспомогательный отчёт для родителя, который помогает лучше понимать ребёнка и выстраивать с ним взаимодействие.

Это **не отчёт о ребёнке как об отдельной личности** и не попытка заранее определить его характер, судьбу или способности.

Главный принцип:

> **Child Report отвечает не на вопрос «Какой мой ребёнок?», а на вопрос «Как мне лучше быть родителем именно для этого ребёнка?»**

Пользователь уже имеет собственную натальную карту в Astrotype.

Он добавляет данные ребёнка, после чего система анализирует:

- натальную карту родителя;
- натальную карту ребёнка;
- взаимодействие двух карт;
- потенциальные зоны лёгкого контакта;
- потенциальные зоны напряжения;
- возраст ребёнка;
- ответы родителя на контрольные вопросы;
- реальный семейный контекст.

Результат — практический parenting guide.

---

# 2. Продуктовый принцип

Child Report нельзя строить по модели:

```text
Moon in Aries
→
ребёнок вспыльчивый
→
родителю нужно делать X
```

Такой подход:

- слишком прямолинейный;
- навешивает ярлыки;
- плохо учитывает возраст;
- не учитывает конкретного родителя;
- создаёт риск самосбывающихся ожиданий.

Вместо этого используем многоуровневую модель:

```text
Parent Natal Chart
        +
Child Natal Chart
        +
Parent–Child Synastry
        +
Child Age
        +
Parent Answers
        ↓
Interaction Dimensions
        ↓
Parenting Guidance
        ↓
LLM Narrative
        ↓
Child Report for Parent
```

---

# 3. Что именно получает пользователь

Пользователь получает не «характеристику ребёнка», а ответы на практические вопросы:

- Как ребёнку проще получать поддержку от меня?
- Как мне лучше его успокаивать?
- Как давать ему границы?
- Где я могу бессознательно давить сильнее, чем нужно?
- Где я, наоборот, могу быть слишком мягким?
- Как ребёнок может реагировать на мой привычный стиль общения?
- Как ему лучше объяснять новое?
- Как поддерживать самостоятельность?
- Как реагировать на сильные эмоции?
- Какие сценарии конфликтов между нами наиболее вероятны?
- Что важно не принимать на свой счёт?
- Какие мои родительские качества особенно полезны именно этому ребёнку?
- Что мне стоит сознательно компенсировать?

---

# 4. Ключевая идея

Система должна анализировать не только ребёнка.

Главный объект анализа:

```text
PARENT ↔ CHILD
```

То есть результат должен описывать **отношение и взаимодействие**, а не две независимые личности.

Пример:

Плохой вывод:

> Ваш ребёнок очень независимый.

Лучший вариант:

> Ребёнку может быть особенно важно постепенно получать пространство для самостоятельного выбора. Если ваш естественный родительский стиль предполагает высокий уровень контроля, здесь может возникать больше напряжения, чем в других областях.

---

# 5. Входные данные

## 5.1 Уже известные данные

У владельца аккаунта уже есть:

```text
Parent Natal Chart
```

Система использует:

- планеты;
- дома;
- аспекты;
- Ascendant;
- MC;
- стихии;
- модальности;
- доминирующие зоны карты;
- существующие Astrotype dimensions.

---

## 5.2 Данные ребёнка

Родитель указывает:

```text
Date of Birth
Time of Birth
Place of Birth
```

Если точное время неизвестно:

```text
Birth Time Confidence:
- exact
- approximate
- unknown
```

Это принципиально важно.

Если время неизвестно, система не должна использовать:

- дома;
- Ascendant;
- MC;
- чувствительные к времени позиции Луны, если в этот день возможна смена знака;
- house synastry.

---

## 5.3 Контекст ребёнка

Дополнительно:

```text
Child Name
Child Birth Date
Child Gender — optional
Relationship to account owner
```

Например:

```text
mother
father
guardian
step-parent
other caregiver
```

---

# 6. Нужно ли учитывать пол родителя

## Короткий ответ

**Пол родителя не должен участвовать в основном астрологическом scoring.**

Для целей Child Report намного важнее:

- кто владелец аккаунта;
- его роль в жизни ребёнка;
- насколько он включён в ежедневный уход;
- кто чаще устанавливает границы;
- кто чаще успокаивает ребёнка;
- кто проводит больше времени с ребёнком.

---

## 6.1 Почему пол не должен быть основным фактором

Нельзя закладывать правила вроде:

```text
Mother → Moon
Father → Sun
```

или:

```text
женщина → emotional parenting
мужчина → authority
```

Это создаёт слишком жёсткую модель и ухудшает персонализацию.

Натальная карта конкретного родителя уже содержит гораздо больше информации о его стиле взаимодействия, чем его пол.

---

## 6.2 Что лучше использовать вместо пола

Поле:

```text
parent_role
```

Например:

```json
{
  "relationship": "mother",
  "primary_caregiver": true,
  "daily_contact": "high",
  "boundary_role": "shared",
  "soothing_role": "mostly_me"
}
```

Это намного полезнее для анализа.

---

## 6.3 Когда пол всё-таки может быть полезен

Пол / биологическая роль может использоваться только в контекстных сценариях, если пользователь сам предоставляет такие данные.

Например:

- беременность;
- послеродовой период;
- грудное вскармливание;
- физиологические вопросы;
- специфическая семейная роль.

Но это отдельный слой контекста, а не часть core astrology engine.

---

# 7. Возраст — обязательный системный слой

Возраст ребёнка **не спрашивается у пользователя отдельно**.

Он всегда рассчитывается автоматически:

```text
Child Date of Birth
+
Report Generation Date
↓
Exact Child Age
```

Система должна хранить и использовать:

```text
age_years
age_months
age_days
age_stage
```

Для младенцев и детей раннего возраста особенно важно использовать не только годы, но и месяцы.

Пример:

```json
{
  "date_of_birth": "2026-05-12",
  "age_years": 0,
  "age_months": 4,
  "age_days": 1,
  "age_stage": "0-1"
}
```

Возраст пересчитывается каждый раз при открытии или регенерации возрастного блока отчёта.

Таким образом, один и тот же Child Report может постепенно менять рекомендации без повторного ввода данных пользователем.

Одна из главных ошибок потенциального Child Report — анализировать новорождённого и 14-летнего подростка одинаково.

Возраст ребёнка должен влиять на:

- формулировки;
- рекомендации;
- список актуальных тем;
- набор контрольных вопросов;
- набор adaptive questions;
- допустимую степень самостоятельности;
- практические примеры;
- приоритет Interaction Dimensions;
- текущий блок `Guidance for Current Age`.

---

## 7.1 Age Stages

Для MVP можно использовать:

```text
0–1 year
1–3 years
3–6 years
6–9 years
9–12 years
12–15 years
15–18 years
```

---

## 7.2 Пример

Для ребёнка 6 месяцев:

```text
не использовать:
- выбор профессии
- лидерские амбиции
- стиль обучения в школе
```

Фокус:

- контакт;
- успокоение;
- сенсорная нагрузка;
- ритм;
- реакция на родительское состояние;
- мягкость / интенсивность стимуляции;
- сепарация в пределах возраста.

Для ребёнка 8 лет:

- обучение;
- правила;
- ошибки;
- похвала;
- мотивация;
- конфликты;
- социализация;
- самостоятельность.

Для подростка:

- автономия;
- личные границы;
- доверие;
- контроль;
- ответственность;
- выбор;
- конфликты;
- признание взрослости.

---

# 8. Архитектура фичи

```text
┌────────────────────┐
│ Parent Natal Chart │
└──────────┬─────────┘
           │
           │
           ├─────────────────┐
           │                 │
           ▼                 ▼
┌────────────────────┐   ┌────────────────────┐
│ Parent Style       │   │ Child Natal Chart  │
│ Dimensions         │   └──────────┬─────────┘
└──────────┬─────────┘              │
           │                         ▼
           │              ┌────────────────────┐
           │              │ Child Needs        │
           │              │ Dimensions         │
           │              └──────────┬─────────┘
           │                         │
           └────────────┬────────────┘
                        ▼
             ┌────────────────────┐
             │ Parent–Child       │
             │ Synastry Engine    │
             └──────────┬─────────┘
                        │
                        ▼
             ┌────────────────────┐
             │ Interaction        │
             │ Dimensions         │
             └──────────┬─────────┘
                        │
               ┌────────┴─────────┐
               │                  │
               ▼                  ▼
      ┌────────────────┐  ┌──────────────────┐
      │ Age Layer      │  │ Control Questions│
      └────────┬───────┘  └─────────┬────────┘
               │                    │
               └─────────┬──────────┘
                         ▼
                ┌───────────────────┐
                │ Context Resolver  │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │ Guidance Facts    │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │ LLM Narrative     │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │ Child Report      │
                │ for Parent        │
                └───────────────────┘
```

---

# 9. Parent Style Dimensions

Из карты владельца аккаунта сначала формируется его базовый родительский стиль.

Примерный набор:

1. Emotional Responsiveness
2. Structure & Boundaries
3. Control Tendency
4. Flexibility
5. Patience
6. Directiveness
7. Communication Style
8. Protection
9. Autonomy Support
10. Expectations
11. Conflict Intensity
12. Consistency
13. Playfulness
14. Teaching Style
15. Sensitivity to Disorder

---

# 10. Child Needs Dimensions

Важно:

Эти показатели не должны называться personality traits.

Лучше описывать их как **условия, в которых ребёнку может быть проще взаимодействовать с родителем**.

Примерный набор:

1. Need for Emotional Reassurance
2. Need for Predictability
3. Need for Autonomy
4. Need for Verbal Explanation
5. Need for Physical / Sensory Calm
6. Need for Exploration
7. Need for Recognition
8. Need for Personal Space
9. Need for Gentle Transition
10. Need for Variety
11. Need for Firm Boundaries
12. Need for Social Contact
13. Need for One-on-One Attention
14. Need for Intellectual Stimulation
15. Need for Slow Processing Time

---

# 11. Interaction Dimensions

Это главный слой Child Report.

Именно он определяет, где стиль родителя совпадает или расходится с потребностями ребёнка.

Пример:

```text
Parent:
Structure = 89

Child:
Need for Flexibility = 74

↓
Potential tension:
Structure vs Flexibility
```

Или:

```text
Parent:
Emotional Responsiveness = 82

Child:
Need for Reassurance = 88

↓
Strong natural compatibility
```

---

# 12. Основные Interaction Dimensions

## 12.1 Emotional Attunement

Насколько естественно родителю считывать и поддерживать эмоциональное состояние ребёнка.

## 12.2 Boundaries Fit

Насколько родительский способ задавать правила соответствует тому, как ребёнку легче принимать ограничения.

## 12.3 Autonomy Balance

Баланс:

```text
Protection ↔ Independence
```

## 12.4 Communication Fit

Как родитель объясняет и как ребёнку проще воспринимать информацию.

## 12.5 Tempo Fit

Например:

```text
Parent:
fast reaction / fast decisions

Child:
slow processing / gradual adaptation
```

Это может стать постоянным источником непонимания.

## 12.6 Conflict Pattern

Как возникает и усиливается напряжение между конкретным родителем и ребёнком.

## 12.7 Soothing Compatibility

Какие способы эмоциональной регуляции могут быть наиболее естественны в этой паре.

## 12.8 Learning Interaction

Как родителю легче обучать ребёнка и где его естественный стиль может мешать.

## 12.9 Recognition Fit

Как ребёнку легче получать похвалу и подтверждение значимости.

## 12.10 Control Sensitivity

Насколько родительский контроль может ощущаться ребёнком как поддержка или давление.

## 12.11 Energy / Stimulation Fit

Соотношение:

```text
high stimulation
vs
low stimulation
```

## 12.12 Trust & Separation

Как постепенно строить доверие и самостоятельность.

Особенно важно для детей старшего возраста.

---

# 13. Synastry Engine

Синастрия используется не для оценки:

```text
compatibility = 82%
```

Такой показатель для отношений родитель–ребёнок продуктово вреден.

У родителя нет задачи узнать:

> Насколько мы совместимы?

Задача:

> Где нам будет легко понимать друг друга, а где потребуется больше осознанности?

---

## 13.1 Что анализируем

В первую очередь:

- Sun ↔ Sun
- Sun ↔ Moon
- Moon ↔ Moon
- Moon ↔ Mercury
- Mercury ↔ Mercury
- Mercury ↔ Mars
- Venus ↔ Moon
- Mars ↔ Mars
- Saturn ↔ personal planets
- Jupiter ↔ personal planets
- angles ↔ personal planets
- house overlays, если время рождения надёжно.

---

## 13.2 Особая роль Saturn

Saturn в Parent–Child Synastry должен интерпретироваться особенно аккуратно.

Он может указывать на:

- структуру;
- ответственность;
- ожидания;
- дисциплину;
- давление;
- ощущение оценки.

Нельзя писать:

> Вы будете подавлять ребёнка.

Правильнее:

> В этой паре тема правил и ожиданий может ощущаться особенно значимой. Родителю важно отличать полезную структуру от чрезмерного давления.

---

# 14. Weight Engine

Каждая Interaction Dimension строится из нескольких факторов.

Пример:

```yaml
autonomy_balance:
  parent:
    uranus_strength: 0.10
    saturn_strength: 0.10
    mars_style: 0.10
    control_dimension: 0.20

  child:
    uranus_strength: 0.10
    mars_style: 0.10
    autonomy_need: 0.20

  synastry:
    saturn_personal_aspects: 0.05
    uranus_personal_aspects: 0.05
```

Итог:

```text
interaction_score =
Σ(factor_score × factor_weight)
```

---

# 15. Не использовать бинарные выводы

Нельзя:

```text
strict_parent = true
sensitive_child = true
```

Нужно:

```json
{
  "dimension": "boundary_fit",
  "score": 64,
  "confidence": 0.78,
  "pattern": "moderate_tension",
  "evidence": [
    "parent_structure_high",
    "child_autonomy_need_high",
    "parent_saturn_square_child_mars"
  ]
}
```

---

# 16. Confidence Score

Как и в Career Report, каждый вывод должен содержать confidence.

Пример:

```json
{
  "dimension": "communication_fit",
  "score": 81,
  "confidence": 0.92
}
```

Высокая confidence:

> Вам, скорее всего, будет достаточно естественно объяснять ребёнку сложные вещи понятным для него способом.

Низкая confidence:

> В некоторых ситуациях может быть полезно давать ребёнку больше времени на обработку объяснений.

---

# 17. Control Questions

Астрологическая модель не знает реальную семейную ситуацию.

Поэтому после расчёта первичного профиля система задаёт вопросы.

---

## 17.1 Общие вопросы

### Возрастной контекст

Возраст уже рассчитывается по дате рождения.

Дополнительно:

> Есть ли у ребёнка братья или сёстры?

> Кто проводит с ребёнком больше всего времени?

> Кто обычно устанавливает правила?

### Emotional Regulation

> Когда ребёнок сильно расстроен, что чаще помогает?

Пример ответов:

```text
Физический контакт
Разговор
Побыть рядом молча
Переключение внимания
Оставить пространство
Зависит от ситуации
```

### Boundaries

> Что обычно происходит, когда вы говорите ребёнку «нет»?

### Independence

> Насколько ребёнок сейчас стремится делать всё самостоятельно?

### Communication

> Что лучше работает: короткая инструкция или подробное объяснение?

### Conflict

> Как обычно выглядит ваш конфликт?

```text
ребёнок протестует
ребёнок закрывается
я начинаю давить сильнее
мы оба быстро успокаиваемся
конфликты редкие
другое
```

---

# 18. Adaptive Questions

После scoring система задаёт вопросы только там, где это действительно нужно.

Пример:

```text
Parent Structure = 91
Child Autonomy Need = 86
```

Adaptive Question:

> Когда ребёнок хочет сделать что-то по-своему, вам обычно легко позволить ему попробовать, даже если вы уверены, что ваш способ лучше?

Другой пример:

```text
Parent Emotional Expression = low
Child Reassurance Need = high
```

Вопрос:

> Вам легко вслух проговаривать ребёнку поддержку и тёплые чувства или вы чаще показываете заботу действиями?

---

# 19. Context Resolver

Context Resolver объединяет:

```text
Parent Natal Profile
+
Child Natal Profile
+
Synastry
+
Age
+
Parent Answers
+
Family Context
```

И выделяет:

### Natural Strengths

Где контакт уже естественно работает хорошо.

### Potential Friction

Где разные стили могут создавать напряжение.

### Compensation Areas

Где родителю стоит сознательно делать то, что не является его естественным стилем.

### Age-Relevant Guidance

Что актуально именно сейчас.

---

# 20. Важный принцип: не исправлять ребёнка

Child Report не должен говорить:

> Ребёнку нужно стать более дисциплинированным.

Фокус всегда на действиях взрослого.

Лучше:

> Если ребёнку сложно быстро переключаться на внешние требования, заранее предупреждать о смене активности может быть эффективнее, чем усиливать давление в момент перехода.

---

# 21. Guidance Facts

До вызова LLM формируется структурированный объект.

Пример:

```json
{
  "child_age_stage": "3-6",

  "strong_matches": [
    {
      "dimension": "emotional_attunement",
      "score": 88,
      "confidence": 0.91
    }
  ],

  "friction_points": [
    {
      "dimension": "autonomy_balance",
      "score": 31,
      "confidence": 0.83,
      "pattern": "parent_control_vs_child_independence"
    }
  ],

  "parent_strengths": ["consistency", "protection", "teaching"],

  "parent_compensation_areas": [
    "allow_more_choice",
    "reduce_immediate_correction"
  ],

  "recommended_actions": [
    "offer_two_acceptable_choices",
    "warn_before_transitions",
    "explain_rules_before_conflict"
  ],

  "avoid_patterns": [
    "escalating_control_during_resistance",
    "interpreting_independence_as_disobedience"
  ]
}
```

---

# 22. Роль LLM

LLM должна:

- превращать Guidance Facts в понятный текст;
- объяснять механику взаимодействия;
- адаптировать рекомендации под возраст;
- приводить бытовые примеры;
- показывать сильные стороны родителя;
- мягко описывать потенциальные сложности;
- давать конкретные действия.

LLM не должна:

- самостоятельно рассчитывать синастрию;
- диагностировать ребёнка;
- присваивать ребёнку психологические расстройства;
- прогнозировать его судьбу;
- утверждать, каким взрослым он станет;
- использовать фатальные формулировки;
- советовать медицинские вмешательства на основе астрологии.

---

# 23. Структура итогового Child Report

## 1. Как пользоваться этим отчётом

Короткое введение:

> Этот отчёт описывает не личность ребёнка как фиксированный набор качеств, а особенности взаимодействия между вами и возможные способы сделать воспитание комфортнее для обоих.

## 2. Ваш естественный стиль как родителя

Кратко:

- что у родителя получается естественно;
- что он склонен делать автоматически;
- как он реагирует на стресс;
- как задаёт границы;
- как проявляет заботу.

## 3. Что особенно важно этому ребёнку во взаимодействии с вами

Не:

```text
Ребёнок такой-то
```

А:

```text
В контакте с вами особенно полезны:
- ...
- ...
- ...
```

## 4. Где вам легко понимать друг друга

Top natural matches.

## 5. Где могут возникать сложности

Top friction points.

Важно описывать:

```text
механизм
→
как он выглядит в жизни
→
что делать родителю
```

## 6. Как успокаивать и поддерживать

Age-aware рекомендации.

Пример:

```text
0–3:
co-regulation

3–6:
co-regulation + naming emotions

6–12:
discussion + structure

12+:
space + availability + respect
```

## 7. Границы и правила

Ответы на вопросы:

- насколько жёстко задавать правило;
- когда объяснять;
- насколько давать выбор;
- как реагировать на протест;
- как не превращать правило в борьбу за власть.

## 8. Самостоятельность

Как помогать ребёнку:

- пробовать;
- ошибаться;
- выбирать;
- брать ответственность.

## 9. Как объяснять и учить

В зависимости от Interaction Dimensions:

- коротко;
- подробно;
- через пример;
- через действие;
- через игру;
- через самостоятельное исследование.

## 10. Похвала и поддержка

Что может лучше работать:

```text
Recognition of effort
Recognition of result
Warm emotional feedback
Concrete feedback
Private praise
Public praise
```

## 11. Конфликты

Отдельный сценарий:

```text
Trigger
↓
Parent reaction
↓
Child reaction
↓
Escalation
↓
Better alternative
```

## 12. Что важно не принимать на свой счёт

Очень важный раздел.

Например:

> Потребность ребёнка делать что-то самостоятельно не обязательно означает отказ от вашей помощи или сопротивление вам как родителю.

## 13. Ваши сильные стороны именно для этого ребёнка

Этот раздел должен укреплять родителя, но без пустой похвалы.

## 14. Что вам может быть полезно делать осознанно

3–5 конкретных compensation actions.

## 15. Сейчас, в этом возрасте

Динамический раздел, который строится на автоматически рассчитанном текущем возрасте ребёнка.

```text
Child DOB
+
Current Date
↓
Exact Age
↓
Age Stage
↓
Current Age Guidance
```

Для конкретного age stage:

> На текущем этапе особенно важны...

Например, для ребёнка 4 месяцев система может акцентировать:

- co-regulation;
- ритм и предсказуемость;
- реакцию на перегрузку;
- способы успокоения;
- контакт с основным caregiver.

Для ребёнка 4 лет:

- автономию;
- протест;
- границы;
- игру;
- переходы между активностями;
- называние эмоций.

Этот раздел может обновляться автоматически без пересоздания всей натальной карты и без повторного ввода возраста.

---

# 24. Workflow пользователя

## Step 1 — Entry Point

На странице существующего Natal Report:

```text
Create Child Report
```

## Step 2 — Relationship

Пользователь указывает:

```text
Who is this child to you?

- Son
- Daughter
- Child
- Stepchild
- Other
```

Для backend лучше хранить отдельно:

```text
relationship_type
child_gender_optional
```

## Step 3 — Birth Data

```text
Date of Birth
Time of Birth
Place of Birth
```

Также:

```text
How accurate is the birth time?

Exact
Approximate
Unknown
```

## Step 4 — Calculate Child Natal Chart

Используется тот же natal calculation engine, что и для обычного пользователя.

Но карта ребёнка не обязана становиться самостоятельным Astrotype account/profile.

## Step 5 — Parent Profile

Система получает существующую карту владельца аккаунта.

```text
account_owner_id
↓
parent_natal_chart
```

## Step 6 — Initial Scoring

Параллельно считаются:

```text
Parent Style Dimensions
Child Needs Dimensions
Parent–Child Synastry
Interaction Dimensions
```

## Step 7 — Age Resolver

Возраст не вводится пользователем вручную.

Он рассчитывается системой автоматически на текущую дату:

```text
Child DOB
+
Current Date
↓
Exact Age
↓
Age Stage
↓
Age-Relevant Rules
```

Результат:

```json
{
  "age_years": 4,
  "age_months": 3,
  "age_stage": "3-6"
}
```

Age Resolver определяет:

- какие темы включать в отчёт;
- какие темы скрывать как преждевременные;
- какие контрольные вопросы задавать;
- какие рекомендации считать актуальными;
- какие бытовые примеры использовать;
- какие Interaction Dimensions имеют больший приоритет.

Возраст должен пересчитываться при каждом новом Age Update.

## Step 8 — Control Questions

Сначала задаются общие вопросы.

После этого — 3–7 adaptive questions по наиболее важным или неоднозначным Interaction Dimensions.

## Step 9 — Context Resolver

Объединяет:

```text
Astrology
+
Interaction scoring
+
Age
+
Answers
```

## Step 10 — Generate Guidance Facts

Создаётся детерминированный объект рекомендаций.

## Step 11 — LLM Generation

LLM создаёт итоговый narrative.

## Step 12 — Render Report

Пользователь получает Child Report.

---

# 25. Повторное использование

В отличие от Natal Report, Child Report должен быть частично динамическим.

Например:

```text
Core Relationship Report
```

строится один раз.

Но раздел:

```text
Сейчас, в этом возрасте
```

может обновляться.

Это создаёт естественную возвращаемость в продукт.

---

# 26. Возможная продуктовая модель

## Core Child Report

Разовая покупка:

- базовое взаимодействие;
- сильные стороны;
- конфликты;
- границы;
- поддержка;
- обучение.

## Age Updates

По мере взросления:

```text
1 year
3 years
6 years
9 years
12 years
15 years
```

можно предлагать обновлённую интерпретацию.

## Subscription

Позже:

```text
Current Age Guidance
+
Transit Layer
+
Parenting Calendar
```

Но transit layer — отдельная фича и не должен входить в MVP.

---

# 27. Multiple Children

Один родитель может создать несколько Child Reports.

Структура:

```text
Parent
├── Child A
│   └── Child Report
│
├── Child B
│   └── Child Report
│
└── Child C
    └── Child Report
```

Важно:

отчёты могут сильно отличаться, потому что анализируется не только карта родителя, но конкретная пара.

---

# 28. Второй родитель

Не требуется для MVP.

Но в будущем:

```text
Parent A
Parent B
Child
```

можно создать:

### Co-Parenting Report

Он отвечает:

- где родители используют разные стили;
- как ребёнок может реагировать на каждого;
- где правила расходятся;
- как согласовать границы;
- какие роли естественно распределяются.

---

# 29. Safety / Product Guardrails

Child Report должен иметь более строгие guardrails, чем обычный Natal Report.

Запрещённые выводы:

```text
Ваш ребёнок будет агрессивным.
Ваш ребёнок склонен к депрессии.
У ребёнка проблемы с привязанностью.
Ребёнок будет плохо учиться.
Ребёнок не создан для командной работы.
Ваш ребёнок будет манипулятором.
```

Правильная модель формулировок:

Не:

> Ребёнок упрямый.

А:

> В ситуациях, где ребёнок уже выбрал собственный способ действия, прямое давление может усиливать сопротивление.

Не:

> Он эмоционально холодный.

А:

> Ребёнок может не всегда сразу показывать переживания внешне, поэтому отсутствие яркой реакции не обязательно означает отсутствие эмоций.

---

# 30. MVP

Для первой версии достаточно:

## Input

```text
Existing Parent Natal Chart
Child Birth Data
Relationship
8–12 Parent Questions
```

Возраст не является отдельным input.

```text
Child Birth Date
↓
Age Resolver
↓
Current Age
```

## Core Dimensions

### Parent Style

```text
Emotional Responsiveness
Structure
Control
Flexibility
Communication
Protection
Autonomy Support
Consistency
```

### Child Needs

```text
Reassurance
Predictability
Autonomy
Explanation
Exploration
Recognition
Personal Space
Transition Time
```

### Interaction

```text
Emotional Attunement
Boundary Fit
Autonomy Balance
Communication Fit
Tempo Fit
Conflict Pattern
Soothing Compatibility
Learning Interaction
```

## Output

1. Parenting Summary
2. Your Natural Parenting Style
3. What This Child Needs From You
4. Natural Strengths
5. Potential Friction
6. Emotional Support
7. Boundaries
8. Autonomy
9. Communication & Learning
10. Conflicts
11. What Not to Take Personally
12. Your Strengths for This Child
13. Conscious Adjustments
14. Guidance for Current Age

---

# 31. V2

Добавить:

- adaptive questions;
- full confidence scoring;
- more precise synastry weights;
- birth-time uncertainty model;
- sibling context;
- school-age modules;
- teenage modules.

---

# 32. V3

Добавить:

```text
Second Parent
Sibling Charts
Family Dynamics
Transit Layer
Age Milestones
```

Возможные продукты:

- Co-Parenting Report
- Sibling Report
- Family Dynamics
- Teen Report
- Current Parenting Forecast

---

# 33. Итоговая модель

```text
Parent Natal Chart
        +
Child Natal Chart
        ↓
Parent Style Dimensions
        +
Child Needs Dimensions
        +
Synastry Engine
        ↓
Interaction Dimensions
        +
Age Layer
        +
Control Questions
        ↓
Context Resolver
        ↓
Guidance Facts
        ↓
LLM Narrative
        ↓
Child Report for Parent
```

---

# 34. Главный продуктовый принцип

Astrotype не должен говорить родителю:

> Вот какой ваш ребёнок.

Astrotype должен говорить:

> Вот как особенности вашего взаимодействия могут проявляться в повседневной жизни, что у вас уже получается естественно и что вы можете делать осознанно, чтобы ребёнку было легче расти рядом с вами.

Именно это отличает Child Report от обычного детского натального гороскопа.
