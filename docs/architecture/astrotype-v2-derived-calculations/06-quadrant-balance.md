# 06 — Quadrant Balance

## Purpose

Quadrant balance shows which quarter of the house wheel carries the most weighted chart emphasis.

It is useful for synthesis because it summarizes where life energy tends to concentrate.

---

## Mapping

| Quadrant | Houses | Product meaning |
|---|---|---|
| Q1 | 1, 2, 3 | self-definition, body/resources, immediate environment |
| Q2 | 4, 5, 6 | private foundation, creativity, practice and skills |
| Q3 | 7, 8, 9 | relationships, deep exchange, worldview expansion |
| Q4 | 10, 11, 12 | vocation, communities, collective/hidden background |

---

## Included points

Use the same included points and weights as house emphasis v1.

---

## Algorithm

```text
for each included point:
  house = point.house
  quadrant = HOUSE_TO_QUADRANT[house]
  score[quadrant] += weight

total = sum(score.values())
percent[quadrant] = score[quadrant] / total * 100
```

---

## Output contract

```json
{
  "method": "quadrant_balance_v1_weighted_points",
  "scores": {
    "q1_identity_foundation": 3.6,
    "q2_private_foundation": 0.0,
    "q3_relationship_worldview": 4.4,
    "q4_public_collective": 5.5
  },
  "percentages": {
    "q1_identity_foundation": 27,
    "q2_private_foundation": 0,
    "q3_relationship_worldview": 33,
    "q4_public_collective": 40
  }
}
```

---

## Report use

Quadrant balance can feed:

- `core_pattern`
- `relationships_and_intimacy`
- `agency_and_desire`
- `growth_vector`

Avoid presenting quadrant labels to users without explanation.
