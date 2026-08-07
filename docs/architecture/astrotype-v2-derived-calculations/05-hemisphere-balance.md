# 05 — Hemisphere Balance

## Purpose

Hemisphere balance estimates where chart weight is concentrated across two axes:

```text
upper vs lower
self-directed/eastern vs other-responsive/western
```

This is primarily a synthesis signal, not a default visible infographic.

---

## Mapping

### Upper / lower

| Hemisphere | Houses              | Product meaning                                            |
| ---------- | ------------------- | ---------------------------------------------------------- |
| Lower      | 1, 2, 3, 4, 5, 6    | private foundation, inner base, personal development       |
| Upper      | 7, 8, 9, 10, 11, 12 | public/social field, visibility, exchange with wider world |

### Eastern / western

| Hemisphere | Houses              | Product meaning                                                     |
| ---------- | ------------------- | ------------------------------------------------------------------- |
| Eastern    | 10, 11, 12, 1, 2, 3 | self-directed orientation, initiative from self                     |
| Western    | 4, 5, 6, 7, 8, 9    | other-responsive orientation, development through people/situations |

Note: naming can be confusing across traditions and chart renderers. Persist the house sets with the method version so the result is unambiguous.

---

## Included points

Use the same included points and weights as house emphasis v1.

---

## Algorithm

```text
for each included point:
  house = point.house
  upper_lower = HOUSE_TO_UPPER_LOWER[house]
  east_west = HOUSE_TO_EAST_WEST[house]

  score_upper_lower[upper_lower] += weight
  score_east_west[east_west] += weight

normalize each axis independently to 100%
```

---

## Output contract

```json
{
  "method": "hemisphere_balance_v1_weighted_points",
  "upper_lower": {
    "scores": {"lower": 3.6, "upper": 9.9},
    "percentages": {"lower": 27, "upper": 73}
  },
  "east_west": {
    "scores": {"eastern": 6.4, "western": 7.1},
    "percentages": {"eastern": 47, "western": 53}
  }
}
```

---

## UI rules

Do not show by default in compact infographic unless we design a clear educational label. It is easy to overinterpret.

Use mainly in `NatalSynthesisV2`.
