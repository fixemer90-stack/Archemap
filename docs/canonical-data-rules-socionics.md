# Canonical Data Rules: Socionics

## 1. Purpose

This document defines the canonical data rules for the Socionics domain in Archemap.

The goal is to make socionics data:

- consistent;
- explainable;
- versioned;
- AI-friendly;
- free from school-specific hardcode;
- safe for probabilistic interpretation;
- extensible for compatibility, career guidance, and future matching/dating modules.

Archemap does not store “socionics in general”.

Archemap stores a controlled **Socionics Kernel**.

---

## 2. Methodological Position

Socionics in Archemap is treated as an interpretive typological model.

It is not treated as:

- medical diagnosis;
- clinical psychology;
- scientifically validated personality assessment;
- deterministic prediction system;
- absolute truth about a person.

Correct wording:

> Archemap uses socionics as a structured language for describing information processing, interaction patterns, strengths, vulnerabilities, and compatibility hypotheses.

Incorrect wording:

> Archemap determines your real type with certainty.

---

## 3. Canonical Layering

All socionics data MUST belong to one of the following layers.

| Layer | Status | Description |
|---|---|---|
| `jungian_core` | canonical | Basic Jungian axes and functions |
| `socionics_core` | canonical | 16 TIMs, 8 aspects, Model A positions, intertype relation matrix |
| `archemap_kernel` | canonical | Archemap-specific normalized definitions and interpretation rules |
| `supported_extension` | allowed | Reinin traits, quadras, clubs, temperaments, subtypes if explicitly marked |
| `experimental_extension` | isolated | Astro-socionics, visual typing, author-specific forks, signs of functions, non-standard subtype systems |
| `deprecated` | forbidden for new logic | Old, conflicting, or rejected concepts |

No data from `experimental_extension` may influence canonical type scoring unless explicitly enabled by a feature flag.

---

## 4. Canonical Source Rule

Every canonical entity MUST have:

```yaml
id: string
display_name: string
layer: string
status: canonical | supported | experimental | deprecated
version: string
source_basis: string[]
description: string
```

Example:

```yaml
id: aspect.fe
display_name: "ЧЭ / Fe / экстравертная этика"
layer: socionics_core
status: canonical
version: "1.0.0"
source_basis:
  - "Jungian function model"
  - "Model A tradition"
  - "Archemap Socionics Kernel"
description: "Aspect of emotional dynamics, emotional influence, motivation, and expressive state change."
```

---

## 5. No School-Specific Hardcode

Archemap MUST NOT silently hardcode one school of socionics as universal truth.

Forbidden:

```yaml
fe:
  definition: "energy of bodies"
```

Allowed:

```yaml
fe:
  canonical_definition: "Emotional dynamics, emotional influence, motivation, and expressive state change."
  school_variants:
    - school: "aspect/body-field tradition"
      definition: "Internal dynamics of a living object/body."
      status: "supported_interpretation"
    - school: "behavioral tradition"
      definition: "Emotional atmosphere, expressiveness, group mood."
      status: "secondary_manifestation"
```

Canonical data MUST separate:

- core definition;
- school variant;
- behavioral manifestation;
- typing signal;
- stereotype.

---

## 6. Aspect Definition Rule

Each information aspect MUST be described through the following structure:

```yaml
id: aspect.fe
symbol: "Fe"
ru_symbol: "ЧЭ"
name_ru: "Экстравертная этика"
name_en: "Extraverted Ethics"
short_name: "Этика эмоций"

gray_function: "ethics"
verted_pair: "aspect.fi"

canonical_definition: string
core_information: string[]
manifestations: string[]
not_evidence: string[]
common_mistakes: string[]
```

Each aspect MUST define:

1. gray function;
2. extraverted or introverted semantic core;
3. observable manifestations;
4. what is NOT evidence of the aspect;
5. common typing mistakes.

---

## 7. Gray Function Rule

Every aspect MUST be linked to a gray function.

Gray functions are the shared semantic bases behind extraverted and introverted variants.

Canonical gray functions:

| ID | Name | Shared basis |
|---|---|---|
| `gray.sensing` | Серая сенсорика | Concrete physical reality, bodily and material perception |
| `gray.intuition` | Серая интуиция | Associations, possibilities, images, abstract potential |
| `gray.ethics` | Серая этика | Emotions, feelings, relations, emotional significance |
| `gray.logic` | Серая логика | Facts, causal links, rules, usefulness, structures |

Example:

```yaml
gray.ethics:
  shared_basis:
    - emotions
    - feelings
    - relations
    - emotional motivation
    - moral or personal significance

aspect.fe:
  specialization:
    - emotional influence
    - inspiration
    - state change
    - motivation through emotion

aspect.fi:
  specialization:
    - stable relations
    - sympathy and antipathy
    - personal distance
    - moral attitude
```

---

## 8. Canonical Aspect Definitions

### 8.1 ЧЭ / Fe / Extraverted Ethics

```yaml
id: aspect.fe
canonical_definition: >
  Aspect of emotional dynamics, emotional influence, motivation,
  expressive state change, inspiration, affective involvement,
  and transmission of emotional states.

core_information:
  - emotional excitation and decline
  - enthusiasm
  - fear
  - joy
  - grief
  - expressive state
  - emotional contagion
  - motivational effect of emotion

not_evidence:
  - loudness
  - hysteria
  - theatricality
  - kindness
  - empathy in general
  - public performance

common_mistakes:
  - reducing Fe to artistry
  - treating emotional instability as strong Fe
  - confusing Fe with Fi
```

### 8.2 БЭ / Fi / Introverted Ethics

```yaml
id: aspect.fi
canonical_definition: >
  Aspect of stable personal relations, subjective distance,
  sympathy and antipathy, trust, loyalty, personal boundaries,
  and moral attitude.

core_information:
  - like/dislike
  - close/far
  - trust/distrust
  - own/alien
  - personal loyalty
  - stable attitude
  - moral relation

not_evidence:
  - politeness
  - softness
  - kindness
  - etiquette
  - emotional expressiveness

common_mistakes:
  - reducing Fi to morality
  - confusing Fi with social politeness
  - treating introversion as Fi
```

### 8.3 ЧЛ / Te / Extraverted Logic

```yaml
id: aspect.te
canonical_definition: >
  Aspect of practical action, work, efficiency, usefulness,
  application, facts as results of activity, and causal links
  between action and outcome.

core_information:
  - works/does not work
  - useful/useless
  - efficient/inefficient
  - cost
  - result
  - process
  - technology
  - algorithm of action

not_evidence:
  - intelligence
  - business interest
  - money orientation
  - career ambition

common_mistakes:
  - confusing Te with Ti
  - reducing Te to business
  - treating pragmatism as always Te-leading
```

### 8.4 БЛ / Ti / Introverted Logic

```yaml
id: aspect.ti
canonical_definition: >
  Aspect of structure, rules, systems, classifications,
  hierarchy, definitions, formal relations, and internal consistency.

core_information:
  - structure
  - rule
  - system
  - hierarchy
  - definition
  - category
  - law
  - consistency

not_evidence:
  - intelligence
  - education
  - mathematics
  - bureaucratic thinking
  - pedantry

common_mistakes:
  - treating Ti as intelligence
  - confusing structure with practical efficiency
  - reducing Ti to formalism
```

### 8.5 ЧС / Se / Extraverted Sensing

```yaml
id: aspect.se
canonical_definition: >
  Aspect of objective physical and status presence:
  force, pressure, territory, boundary, possession, material resource,
  visible strength, and ability to overcome resistance.

core_information:
  - force
  - pressure
  - territory
  - resource
  - possession
  - boundary
  - status
  - resistance
  - physical impact

not_evidence:
  - aggression
  - violence
  - leadership in general
  - sportiness
  - rude behavior

common_mistakes:
  - reducing Se to aggression
  - confusing Se with dominance behavior
  - ignoring calm and controlled Se
```

### 8.6 БС / Si / Introverted Sensing

```yaml
id: aspect.si
canonical_definition: >
  Aspect of subjective bodily state, comfort, physical harmony,
  sensory quality, relaxation, discomfort, health, taste,
  and inner bodily balance.

core_information:
  - comfort
  - discomfort
  - taste
  - temperature
  - pain
  - relaxation
  - bodily harmony
  - sensory pleasure
  - health state

not_evidence:
  - laziness
  - love of food
  - domesticity
  - passivity
  - hedonism in general

common_mistakes:
  - reducing Si to food and comfort
  - confusing Si with laziness
  - ignoring precision of sensory perception
```

### 8.7 ЧИ / Ne / Extraverted Intuition

```yaml
id: aspect.ne
canonical_definition: >
  Aspect of external possibilities, potential, alternatives,
  hidden properties, unusual associations, new meanings,
  and possible ways an object or situation may unfold.

core_information:
  - possibility
  - potential
  - alternative
  - hidden property
  - unusual use
  - new idea
  - talent
  - open scenario

not_evidence:
  - fantasy in general
  - chaos
  - humor
  - creativity in general
  - novelty for novelty's sake

common_mistakes:
  - reducing Ne to fantasy
  - confusing Ne with Ni forecasting
  - treating every creative person as Ne-strong
```

### 8.8 БИ / Ni / Introverted Intuition

```yaml
id: aspect.ni
canonical_definition: >
  Aspect of internal temporal modeling, development of events,
  probable future, timing, scenario, maturation, connection
  between past, present, and future, and inner image of process.

core_information:
  - time
  - timing
  - trend
  - scenario
  - maturation
  - probability
  - future image
  - past-to-future continuity
  - inner world model

not_evidence:
  - mysticism
  - anxiety
  - passivity
  - dreaminess
  - magical prediction

common_mistakes:
  - reducing Ni to mysticism
  - confusing Ni with anxiety
  - confusing Ni with Ne alternatives
```

---

## 9. Model A Canonical Rule

Model A is canonical in Archemap.

Every TIM MUST define all 8 function positions:

```yaml
model_a:
  1: aspect
  2: aspect
  3: aspect
  4: aspect
  5: aspect
  6: aspect
  7: aspect
  8: aspect
```

Each position MUST include canonical properties:

| Position | Name | Strength | Value | Awareness |
|---|---|---|---|---|
| 1 | program/base | strong | valued | mental |
| 2 | creative | strong | valued | mental |
| 3 | role | weak | displaced | mental |
| 4 | vulnerable/painful | weak | displaced | mental |
| 5 | suggestive | weak | valued | vital |
| 6 | mobilizing/activating | weak | valued | vital |
| 7 | limiting/observing | strong | displaced | vital |
| 8 | demonstrative/background | strong | displaced | vital |

Canonical position object:

```yaml
position:
  number: 1
  name: "program"
  strength: "strong"
  value_status: "valued"
  awareness: "mental"
  archemap_role: "core worldview and primary information lens"
```

---

## 10. TIM Canonical Rule

Each type MUST be represented as canonical data, not prose.

Example:

```yaml
id: tim.ile
code_ru: "ИЛЭ"
code_latin: "ILE"
legacy_code: "ENTp"
display_name: "Интуитивно-логический экстраверт"
archetype_name: "Дон Кихот"

quadra: "alpha"
club: "researcher"
temperament: "EP"

model_a:
  1: aspect.ne
  2: aspect.ti
  3: aspect.se
  4: aspect.fi
  5: aspect.si
  6: aspect.fe
  7: aspect.ni
  8: aspect.te

status: canonical
```

The following are canonical TIM identifiers:

| ID | RU | Legacy | Common Name |
|---|---|---|---|
| `tim.ile` | ИЛЭ | ENTp | Дон Кихот |
| `tim.sei` | СЭИ | ISFp | Дюма |
| `tim.ese` | ЭСЭ | ESFj | Гюго |
| `tim.lii` | ЛИИ | INTj | Робеспьер |
| `tim.eie` | ЭИЭ | ENFj | Гамлет |
| `tim.lsi` | ЛСИ | ISTj | Максим Горький |
| `tim.sle` | СЛЭ | ESTp | Жуков |
| `tim.iei` | ИЭИ | INFp | Есенин |
| `tim.see` | СЭЭ | ESFp | Наполеон |
| `tim.ili` | ИЛИ | INTp | Бальзак |
| `tim.lie` | ЛИЭ | ENTj | Джек Лондон |
| `tim.esi` | ЭСИ | ISFj | Драйзер |
| `tim.lse` | ЛСЭ | ESTj | Штирлиц |
| `tim.eii` | ЭИИ | INFj | Достоевский |
| `tim.iee` | ИЭЭ | ENFp | Гексли |
| `tim.sli` | СЛИ | ISTp | Габен |

---

## 11. Interpretation Rule

Archemap MUST NOT interpret an aspect without its Model A position.

Forbidden:

```yaml
claim: "Strong Fe means the person is emotional."
```

Allowed:

```yaml
claim: "Fe in position 1 may indicate that emotional dynamics and motivational states are a primary lens of perception and action."
```

Required interpretation dimensions:

```yaml
interpretation:
  aspect: aspect.fe
  position: 1
  strength: strong
  value_status: valued
  awareness: mental
  confidence: 0.72
  explanation: string
```

---

## 12. Anti-Stereotype Rule

Canonical data MUST separate:

- aspect;
- position;
- behavior;
- stereotype;
- typing signal.

Forbidden stereotypes:

| Aspect | Forbidden reduction |
|---|---|
| Fe | emotional, hysterical, theatrical |
| Fi | kind, moral, polite |
| Te | businesslike, rich, careerist |
| Ti | smart, nerdy, pedantic |
| Se | aggressive, violent, dominant |
| Si | lazy, foodie, domestic |
| Ne | chaotic, funny, fantasist |
| Ni | mystical, passive, anxious |

---

## 13. Probabilistic Typing Rule

Archemap MUST NOT produce a single final type without alternatives.

Forbidden:

```yaml
result:
  type: tim.ili
```

Required:

```yaml
result:
  primary_hypothesis:
    tim: tim.ili
    confidence: 0.61

  alternatives:
    - tim: tim.lii
      confidence: 0.18
    - tim: tim.iei
      confidence: 0.13
    - tim: tim.lie
      confidence: 0.08

  explanation:
    strongest_signals:
      - aspect.ni
      - aspect.te
    weak_or_conflicting_signals:
      - aspect.fi
      - aspect.se

  disclaimer: >
    This is a probabilistic typological hypothesis, not a diagnosis or verified psychological assessment.
```

---

## 14. Evidence Rule

Every typing signal MUST have an evidence type.

Allowed evidence types:

```yaml
evidence_type:
  - self_report
  - behavioral_pattern
  - preference_pattern
  - conflict_pattern
  - professional_pattern
  - relationship_pattern
  - astrological_mapping
  - manual_expert_input
  - questionnaire_answer
```

Astrological evidence MUST NOT be treated as direct proof of TIM.

Correct:

```yaml
evidence:
  type: astrological_mapping
  weight: 0.15
  affects:
    - aspect.ni
    - aspect.fi
  status: experimental_support
```

Incorrect:

```yaml
evidence:
  type: astrological_mapping
  result: tim.iei
  confidence: 1.0
```

---

## 15. Weighting Rule

Canonical socionics scoring MUST use weighted hypotheses.

Each score contribution MUST include:

```yaml
weight_contribution:
  target: aspect | position | tim | relation
  value: number
  source: string
  confidence: number
  explanation: string
```

Example:

```yaml
weight_contribution:
  target: aspect.ni
  value: 0.18
  source: "birth_chart.symbolic_mapping"
  confidence: 0.35
  explanation: "Several symbolic indicators suggest stronger orientation toward temporal modeling and inner scenario construction."
```

No hidden scoring logic is allowed for canonical interpretation.

---

## 16. Compatibility Rule

Compatibility MUST NOT be reduced to intertype relation alone.

Intertype relation is one layer.

Compatibility calculation MUST include:

```yaml
compatibility_layers:
  - socionics_intertype_relation
  - function_value_alignment
  - communication_style
  - conflict_zones
  - emotional_tempo
  - life_goals
  - attachment_or_boundary_style
  - context: romantic | friendship | family | work | team | dating
```

Forbidden:

```yaml
claim: "Duals are always compatible."
```

Allowed:

```yaml
claim: "Duality may indicate complementary information needs, but relationship quality also depends on maturity, values, communication, lifestyle, and context."
```

---

## 17. Career Guidance Rule

Career guidance MUST NOT map TIM directly to professions.

Forbidden:

```yaml
tim.ili:
  professions:
    - analyst
    - trader
    - philosopher
```

Allowed:

```yaml
career_profile:
  preferred_task_style:
    - strategic forecasting
    - risk modeling
    - analytical synthesis

  suitable_environments:
    - low-chaos intellectual work
    - autonomous research
    - long-horizon planning

  risk_zones:
    - high emotional performance demand
    - constant sensory pressure
    - chaotic short-cycle execution

  possible_roles:
    - analyst
    - strategist
    - architect
    - researcher

  disclaimer: "Roles are examples, not deterministic prescriptions."
```

---

## 18. Dating and Matching Rule

Dating/matching MUST use socionics only as one compatibility layer.

Matching score MUST NOT be based only on TIM.

Required matching inputs:

```yaml
matching_inputs:
  - age_range
  - location
  - relationship_goal
  - consent_to_matching
  - visibility_status
  - socionics_profile
  - compatibility_preferences
  - communication_style
  - safety_filters
```

Socionics profile may affect:

```yaml
matching_socionics_factors:
  - intertype_relation
  - valued_function_alignment
  - likely conflict zones
  - communication tempo
  - support needs
  - emotional compatibility
```

Forbidden:

```yaml
claim: "This person is your dual, therefore ideal partner."
```

Allowed:

```yaml
claim: "This profile may complement your information needs, but the match should be evaluated through communication, values, goals, and boundaries."
```

---

## 19. Experimental Extension Rule

The following concepts are NOT canonical by default:

- signs of functions;
- Reinin traits as primary diagnostics;
- visual typing;
- physiognomy;
- subtype systems;
- astro-socionics;
- tarot-socionics;
- Human Design mappings;
- author-specific function modifications;
- energy/body/field metaphysics as primary ontology.

They may be stored only as:

```yaml
status: experimental
feature_flag_required: true
canonical_score_impact: false
```

Example:

```yaml
id: extension.function_signs.shss
status: experimental
feature_flag_required: true
canonical_score_impact: false
```

---

## 20. Source Traceability Rule

Every interpretation template MUST declare its source class.

Allowed source classes:

```yaml
source_class:
  - canonical_kernel
  - archemap_interpretation
  - supported_school_variant
  - experimental_hypothesis
  - user_feedback
  - expert_override
```

Example:

```yaml
template:
  id: interpretation.fe.position_1.short
  source_class: archemap_interpretation
  canonical_dependencies:
    - aspect.fe
    - model_a.position.1
```

---

## 21. User-Facing Language Rule

User-facing text MUST use careful language.

Required words:

- likely;
- may;
- hypothesis;
- tendency;
- possible;
- signal;
- interpretation;
- probability.

Forbidden absolute words:

- always;
- never;
- proven;
- guaranteed;
- real type;
- exact type;
- destiny;
- diagnosis.

Correct:

> Your strongest current hypothesis is ILI. This suggests a possible focus on temporal modeling, risk perception, and long-horizon interpretation.

Incorrect:

> You are ILI. This is your real type.

---

## 22. Data Versioning Rule

Every canonical data file MUST include:

```yaml
schema_version: "1.0.0"
kernel_version: "1.0.0"
content_hash: string
updated_at: datetime
```

Breaking changes require major version update.

Examples of breaking changes:

- changing aspect definitions;
- changing Model A positions;
- changing TIM identifiers;
- changing compatibility matrix logic;
- changing scoring interpretation rules.

Non-breaking changes:

- typo fixes;
- additional examples;
- new optional metadata;
- additional user-facing templates.

---

## 23. No Hardcoded Prose Rule

Application logic MUST NOT depend on prose descriptions.

Forbidden:

```python
if "эмоциональный" in aspect.description:
    score_fe += 1
```

Allowed:

```yaml
aspect.fe:
  tags:
    - emotional_dynamics
    - motivation
    - expressive_state
    - emotional_influence
```

Application logic MUST depend on structured tags, IDs, and weights.

---

## 24. Canonical File Structure

Recommended canonical data structure:

```text
data/
  socionics/
    manifest.yaml
    schema/
      aspect.schema.json
      gray-function.schema.json
      tim.schema.json
      model-a-position.schema.json
      relation.schema.json
      interpretation-template.schema.json

    canonical/
      gray-functions.yaml
      aspects.yaml
      model-a-positions.yaml
      tims.yaml
      intertype-relations.yaml
      quadras.yaml

    archemap/
      interpretation-rules.yaml
      scoring-rules.yaml
      compatibility-rules.yaml
      career-rules.yaml

    extensions/
      reinin.yaml
      subtypes.yaml
      function-signs.yaml
      astro-socionics.yaml

    deprecated/
      legacy-mappings.yaml
```

---

## 25. Canonical Validation Rules

The validator MUST check:

- every TIM has exactly 8 Model A positions;
- every Model A position references an existing aspect;
- every aspect references an existing gray function;
- every interpretation template references canonical IDs;
- no experimental entity affects canonical score unless explicitly enabled;
- no duplicate IDs exist;
- every entity has version and status;
- every user-facing template avoids forbidden absolute language;
- every compatibility output includes disclaimer;
- every type result includes alternatives.

---

## 26. Canonical Output Contract

A socionics profile output MUST follow this structure:

```yaml
socionics_profile:
  primary_hypothesis:
    tim: tim.ili
    confidence: 0.61

  alternatives:
    - tim: tim.lii
      confidence: 0.18
    - tim: tim.iei
      confidence: 0.13
    - tim: tim.lie
      confidence: 0.08

  function_profile:
    strongest_aspects:
      - aspect.ni
      - aspect.te
    vulnerable_aspects:
      - aspect.se
      - aspect.fi

  model_a_interpretation:
    ego:
      - position: 1
        aspect: aspect.ni
      - position: 2
        aspect: aspect.te

  confidence_notes:
    - "Typing result is probabilistic."
    - "Astrological indicators are treated as symbolic support, not proof."
    - "User feedback may update the score."

  user_facing_summary: string
```

---

## 27. Canonical Disclaimer

Every socionics result MUST be able to display this disclaimer:

> Archemap uses socionics as an interpretive typological model. The result is a probabilistic hypothesis intended for self-reflection, compatibility analysis, and career orientation. It is not a medical, psychological, or scientific diagnosis.

---

## 28. Golden Rule

The canonical socionics kernel MUST optimize for:

1. internal consistency;
2. explainability;
3. probabilistic output;
4. separation of canon and extensions;
5. resistance to stereotypes;
6. transparent scoring;
7. safe user-facing language.

Archemap MUST NOT claim to know the user's type absolutely.

Archemap MAY suggest a structured, explainable, revisable hypothesis.
