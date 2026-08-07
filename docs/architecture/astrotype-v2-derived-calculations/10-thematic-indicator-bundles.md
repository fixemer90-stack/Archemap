# 10 — Thematic Indicator Bundles

> Status: Неактуально на текущий момент / deferred.
>
> Этот документ сохранён как черновик возможного будущего synthesis/debug слоя, но `Thematic indicator bundles` не входят в текущий MVP sample и не должны рендериться как пользовательский блок. Текущий макет `astrotype-v2-infographic-db-report-sample.html` намеренно не содержит блок “Связь расчёта с разделами отчёта”.

## Purpose

Thematic indicator bundles collect deterministic evidence for the major report sections.

They are not current MVP scope. If revived later, they may become an internal curated input for `NatalSynthesisV2`, `ReportOutlineV2` and section-specific LLM rendering, but they must not be shown as a report UI block without a new design decision.

---

## Deferred bundle draft

```text
cognition_indicators
emotion_indicators
agency_indicators
relationship_indicators
growth_indicators
```

Optional later:

```text
vocation_indicators
creative_expression_indicators
body_and_rhythm_indicators
```

---

## Bundle inputs

### Cognition indicators

Use:

```text
Mercury sign/house/aspects
3rd house cusp/ruler/planets
9th house cusp/ruler/planets
Air balance
Mutable balance
```

### Emotion indicators

Use:

```text
Moon sign/house/aspects
4th house
8th house
12th house
Water balance
Moon-Saturn/Moon-Neptune/Moon-Pluto aspects
```

### Agency indicators

Use:

```text
Mars sign/house/aspects
1st house
10th house
Fire balance
Cardinal balance
Mars-Saturn/Mars-Uranus/Mars-Pluto aspects
```

### Relationship indicators

Use:

```text
Descendant sign
7th house planets
7th house ruler position
Venus sign/house/aspects
Mars sign/house/aspects
Moon relationship-relevant aspects
```

### Growth indicators

Use:

```text
tight hard aspects
Saturn condition
chart ruler condition
12th house emphasis
low-emphasis elements/modalities
repeated tensions from aspect profile
```

---

## Scoring model

Each bundle contains evidence, not a single opaque score.

Suggested fields:

```json
{
  "bundle_id": "relationship_indicators",
  "method": "thematic_indicator_bundle_v1",
  "primary_evidence_ids": [],
  "secondary_evidence_ids": [],
  "themes": [],
  "warnings": [],
  "section_targets": ["relationships_and_intimacy"]
}
```

If a numeric score is needed for sorting, use it only internally:

```text
bundle_strength = sum(evidence_weight * relevance_weight)
```

Do not show `bundle_strength` to the user by default.

---

## Evidence weighting

MVP evidence priority:

| Evidence kind | Priority |
|---|---:|
| direct section planet: Moon/Mercury/Mars/Venus | high |
| house ruler relevant to section | high |
| exact aspect involving section planet | high |
| balance support: element/modality | medium |
| broad hemisphere/quadrant support | low-medium |
| outer planet background without personal/angle contact | low |

---

## Relationship with ReportOutlineV2

Indicator bundles should not directly write prose. They feed the outline planner:

```text
indicator bundle → candidate themes → owned section → SectionRenderInputV2
```

This prevents the same fact from being expanded in every report section.

---

## Output contract

```json
{
  "method": "thematic_indicator_bundle_v1",
  "bundles": {
    "cognition_indicators": {
      "primary_evidence_ids": ["mercury_in_virgo", "mercury_trine_saturn"],
      "themes": ["structured_thinking", "precision_filter"],
      "section_targets": ["perception_and_mind"]
    },
    "relationship_indicators": {
      "primary_evidence_ids": ["descendant_taurus", "mars_in_7th", "venus_square_pluto"],
      "themes": ["trust_and_control", "slow_stability_in_contact"],
      "section_targets": ["relationships_and_intimacy"]
    }
  }
}
```
