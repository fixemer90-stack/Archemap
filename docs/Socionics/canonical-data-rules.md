# Canonical Data Rules: Socionics → Archemap

**Версия:** 1.0
**Дата:** 2026-05-30
**Статус:** Draft
**Источник:** Загубисало П.С. «Каркас типологии Юнга-Аугустинавичюте» (2013)

---

## 1. Назначение

Документ определяет канонические правила маппинга соционических типов на астрологические данные. Используется как спецификация для создания YAML-правил в E4 (Rule Engine).

**Принцип:** соционика описывает 16 типов личности через 8 психических функций. Archemap вычисляет 8 функций через астрологические данные (стихии, модальности, планеты, дома). Правила маппят одно на другое.

---

## 2. Соционические функции

### 2.1 Классификация

| Код | Название | Тип | Вертность | Нальность |
|---|---|---|---|---|
| **Se** | Экстравертная «волевая» сенсорика | Иррациональная | Экстравертная | Сенсорика |
| **Si** | Интровертная сенсорика «ощущений» | Иррациональная | Интровертная | Сенсорика |
| **Ne** | Экстравертная интуиция «возможностей» | Иррациональная | Экстравертная | Интуиция |
| **Ni** | Интровертная интуиция «времени» | Иррациональная | Интровертная | Интуиция |
| **Fe** | Экстравертная этика «эмоций» | Рациональная | Экстравертная | Этика |
| **Fi** | Интровертная этика «отношений» | Рациональная | Интровертная | Этика |
| **Te** | Экстравертная «деловая» логика | Рациональная | Экстравертная | Логика |
| **Ti** | Интровертная «структурная» логика | Рациональная | Интровертная | Логика |

### 2.2 Оси

| Ось | Полюс A | Полюс B |
|---|---|---|
| Рациональность | p (irrational, perceiving) | j (rational, judging) |
| Сенсорика-Интуиция | S (sensing) | N (intuition) |
| Логика-Этика | T (thinking) | F (feeling) |
| Экстраверсия-Интроверсия | e (extraverted) | i (introverted) |

---

## 3. Маппинг: Астрология → Соционические функции

### 3.1 Стихии → Функциональные оси

| Стихия | Соционическая ось | Логика маппинга |
|---|---|---|
| **Огонь** (fire) | Se + Fe | Волевое действие + эмоциональное воздействие |
| **Земля** (earth) | Si + Te | Ощущения + деловая логика |
| **Воздух** (air) | Ne + Ti | Возможности + структурная логика |
| **Вода** (water) | Ni + Fi | Внутреннее видение + отношения |

### 3.2 Модальности → Рациональность/Иррациональность

| Модальность | Соционическое соответствие |
|---|---|
| **Кардинальные** (cardinal) | Рациональные (j) — инициирование, решение |
| **Фиксированные** (fixed) | Рациональные (j) — стабильность, удержание |
| **Мутабельные** (mutable) | Иррациональные (p) — адаптация, восприятие |

### 3.3 Планеты → Функции

| Планета | Доминирующая функция | Логика |
|---|---|---|
| **Солнце** | Программная функция (1-я) | Ядро личности, осознанная ценность |
| **Луна** | Творческая функция (2-я) | Инструмент реализации, эмоциональная основа |
| **Меркурий** | Ti / Te | Логика, коммуникация, анализ |
| **Венера** | Fi / Fe | Этика, ценности, отношения |
| **Марс** | Se | Воля, действие, энергия |
| **Юпитер** | Ne / Fe | Расширение, возможности, энтузиазм |
| **Сатурн** | Ti / Si | Структура, ограничения, дисциплина |
| **Уран** | Ne | Инновации, прорыв, нестандартность |
| **Нептун** | Ni / Fi | Интуиция, видение, иллюзии |
| **Плутон** | Se / Fi | Трансформация, глубина, власть |

### 3.4 Дома → Сферы проявления функций

| Дом | Соционическая сфера |
|---|---|
| **1** (Асц) | Se — самопрезентация, воля, имидж |
| **2** | Si — ресурсы, комфорт, обладание |
| **3** | Te / Ti — коммуникация, обучение |
| **4** | Si / Fi — семья, корни, безопасность |
| **5** | Ne / Fe — творчество, самовыражение |
| **6** | Te — работа, здоровье, рутина |
| **7** | Fi / Fe — партнёрство, отношения |
| **8** | Se / Pluto — трансформация, кризис |
| **9** | Ne / Ni — философия, путешествия, смыслы |
| **10** (MC) | Te / Fe — карьера, статус, призвание |
| **11** | Ne — друзья, сообщества, идеи |
| **12** | Ni / Fi — подсознание, уединение, жертва |

---

## 4. 16 типов (архетипы)

### 4.1 Таблица типов

| Тип | Программная (1) | Творческая (2) | Сокращение | Quadra |
|---|---|---|---|---|
| **ILE** (Искатель) | Ne | Ti | ENTp | α |
| **SEI** (Посредник) | Si | Fe | ISFp | α |
| **ESE** (Энтузиаст) | Fe | Si | ESFj | α |
| **LII** (Аналитик) | Ti | Ne | INTj | α |
| **EIE** (Наставник) | Fe | Ni | ENFj | β |
| **LSI** (Инспектор) | Ti | Se | ISTj | β |
| **SLE** (Маршал) | Se | Ti | ESTp | β |
| **IEI** (Лирик) | Ni | Fe | INFp | β |
| **SEE** (Политик) | Se | Fi | ESFp | γ |
| **ILI** (Критик) | Ni | Te | INTp | γ |
| **LIE** (Предприниматель) | Te | Ni | ENTj | γ |
| **ESI** (Хранитель) | Fi | Se | ISFj | γ |
| **LSE** (Администратор) | Te | Si | ESTj | δ |
| **EII** (Гуманист) | Fi | Ne | INFj | δ |
| **IEE** (Психолог) | Ne | Fi | ENFp | δ |
| **SLI** (Мастер) | Si | Te | ISTp | δ |

### 4.2 Квадры

| Квадра | Типы | Доминирующие функции | Стихия |
|---|---|---|---|
| **α (Альфа)** | ILE, SEI, ESE, LII | Ne, Si, Fe, Ti | Воздух + Земля |
| **β (Бета)** | EIE, LSI, SLE, IEI | Fe, Ti, Se, Ni | Огонь + Вода |
| **γ (Гамма)** | SEE, ILI, LIE, ESI | Se, Ni, Te, Fi | Огонь + Вода |
| **δ (Дельта)** | LSE, EII, IEE, SLI | Te, Fi, Ne, Si | Земля + Воздух |

---

## 5. Правила для E4 Rule Engine

### 5.1 Формат правила

```yaml
rule_id: socionics.<type_code>.v1
product: self
version: 1.0.0
status: draft
depends_on:
  - feature.fire
  - feature.earth
  - feature.air
  - feature.water
  - feature.cardinal
  - feature.fixed
  - feature.mutable
  - feature.planet_sun_sign
  - feature.planet_moon_sign
  - feature.house_emphasis
conditions:
  all:
    - fact: feature.<primary_element>
      op: gte
      value: <threshold>
    - fact: feature.<secondary_element>
      op: gte
      value: <threshold>
effects:
  archetype.<type_code>: <weight>
  claim.self.<function>: <weight>
```

### 5.2 Правила: примеры

#### ILE (Искатель) — Ne + Ti

```yaml
rule_id: socionics.ile.v1
product: self
version: 1.0.0
status: draft
depends_on:
  - feature.air
  - feature.earth
  - feature.mutable
conditions:
  all:
    - fact: feature.air
      op: gte
      value: 0.30
    - fact: feature.mutable
      op: gte
      value: 0.35
    - fact: feature.fire
      op: lt
      value: 0.30
effects:
  archetype.ile: 0.20
  claim.self.intuition_possibilities: 0.15
  claim.self.logic_structure: 0.10
evidence:
  template_key: ev.socionics.ile
  show_basis_features:
    - feature.air
    - feature.mutable
```

#### SLE (Маршал) — Se + Ti

```yaml
rule_id: socionics.sle.v1
product: self
version: 1.0.0
status: draft
depends_on:
  - feature.fire
  - feature.earth
  - feature.fixed
conditions:
  all:
    - fact: feature.fire
      op: gte
      value: 0.30
    - fact: feature.fixed
      op: gte
      value: 0.30
    - fact: feature.earth
      op: gte
      value: 0.25
effects:
  archetype.sle: 0.20
  claim.self.will_sensory: 0.15
  claim.self.logic_structure: 0.10
evidence:
  template_key: ev.socionics.sle
  show_basis_features:
    - feature.fire
    - feature.fixed
```

#### EII (Гуманист) — Fi + Ne

```yaml
rule_id: socionics.eii.v1
product: self
version: 1.0.0
status: draft
depends_on:
  - feature.water
  - feature.air
  - feature.mutable
conditions:
  all:
    - fact: feature.water
      op: gte
      value: 0.30
    - fact: feature.air
      op: gte
      value: 0.25
    - fact: feature.mutable
      op: gte
      value: 0.30
effects:
  archetype.eii: 0.20
  claim.self.ethics_relations: 0.15
  claim.self.intuition_possibilities: 0.10
evidence:
  template_key: ev.socionics.eii
  show_basis_features:
    - feature.water
    - feature.air
```

### 5.3 Все 16 типов: thresholds

| Тип | Прог. функция | Стихия 1 ≥ | Стихия 2 ≥ | Модальность ≥ | Архетип |
|---|---|---|---|---|---|
| ILE | Ne | air 0.30 | — | mutable 0.35 | Искатель |
| SEI | Si | earth 0.30 | — | mutable 0.35 | Посредник |
| ESE | Fe | fire 0.25 | earth 0.25 | cardinal 0.30 | Энтузиаст |
| LII | Ti | air 0.35 | earth 0.25 | — | Аналитик |
| EIE | Fe | fire 0.30 | water 0.25 | cardinal 0.30 | Наставник |
| LSI | Ti | earth 0.30 | fire 0.25 | fixed 0.30 | Инспектор |
| SLE | Se | fire 0.30 | earth 0.25 | fixed 0.30 | Маршал |
| IEI | Ni | water 0.30 | fire 0.25 | mutable 0.30 | Лирик |
| SEE | Se | fire 0.30 | water 0.25 | fixed 0.30 | Политик |
| ILI | Ni | water 0.35 | earth 0.20 | — | Критик |
| LIE | Te | earth 0.30 | fire 0.25 | cardinal 0.30 | Предприниматель |
| ESI | Fi | water 0.30 | earth 0.25 | fixed 0.30 | Хранитель |
| LSE | Te | earth 0.35 | fire 0.20 | fixed 0.30 | Администратор |
| EII | Fi | water 0.30 | air 0.25 | mutable 0.30 | Гуманист |
| IEE | Ne | air 0.30 | water 0.25 | mutable 0.35 | Психолог |
| SLI | Si | earth 0.35 | air 0.20 | mutable 0.30 | Мастер |

---

## 6. Примечания

1. **Точность:** thresholds — приблизительные, требуют калибровки на golden tests
2. **Вторичные функции:** творческая функция учитывается через вторичную стихию
3. **Модальность:** cardinal/fixed → rational (j), mutable → irrational (p)
4. **Время рождения:** при unknown — функции, зависящие от домов/ASC, снижают confidence
5. **Archemap ≠ соционика:** Archemap использует астрологические данные, а не соционические тесты. Маппинг — гипотеза, не факт
