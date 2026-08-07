# 08 — Aspect Profile

## Purpose

Aspect profile summarizes the structure of major aspects in the chart:

```text
resource vs tension vs fusion
aspect counts
average orb
most exact aspects
```

This is deterministic and should be derived from `natal_aspects` rows.

---

## Included aspects

MVP includes major aspects:

```text
conjunction
sextile
square
trine
opposition
quincunx
```

Minor aspects can be added in later method versions.

---

## Aspect grouping

| Group | Aspect types |
|---|---|
| fusion | conjunction |
| resource | sextile, trine |
| tension | square, opposition, quincunx |

Note: conjunction can be supportive, difficult, or mixed depending on planets. For profile counting, it is kept separate as `fusion`.

---

## Algorithm

```text
for each natal_aspect:
  if aspect_type not in MVP_TYPES:
    skip

  group = ASPECT_GROUP[aspect_type]
  group_count[group] += 1
  orb_values.append(aspect.orb)

average_orb = mean(orb_values)
most_exact_aspects = sort(aspects by orb asc).take(N)
```

Optional weighted profile:

```text
exactness_weight = max(0, 1 - orb / allowed_orb)
weighted_group_score[group] += exactness_weight
```

MVP can store both counts and exactness-weighted scores.

---

## Output contract

```json
{
  "method": "aspect_profile_v1_major_aspects",
  "counts": {
    "fusion": 0,
    "resource": 5,
    "tension": 5
  },
  "average_orb": 3.38,
  "most_exact_aspects": [
    "Venus quincunx Neptune",
    "Moon square Saturn",
    "Venus square Pluto"
  ]
}
```

---

## UI rules

Can be visible as a compact split:

```text
5 resource links / 5 tension links
```

Do not imply that tension is “bad” or resource is “easy life”. Use neutral language.
