# 04 — Angular / Succedent / Cadent Balance

## Purpose

House mode balance shows how chart weight distributes across three house categories:

```text
Angular, Succedent, Cadent
```

This helps distinguish how strongly energy pushes into visible action, consolidation, or adaptation.

---

## House mapping

| Category | Houses | Meaning |
|---|---|---|
| Angular | 1, 4, 7, 10 | initiation, visibility, immediate life axes |
| Succedent | 2, 5, 8, 11 | stabilization, accumulation, continuity |
| Cadent | 3, 6, 9, 12 | adaptation, learning, transition, processing |

---

## Included points

Use the same included points as house emphasis v1:

```text
Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Ascendant, MC
```

Use the same point weights as house emphasis v1 unless a later method version changes it.

---

## Algorithm

```text
for each included point:
  house = point.house
  category = HOUSE_TO_MODE[house]
  score[category] += POINT_WEIGHT[point.name]

total = sum(score.values())
percent[category] = score[category] / total * 100
```

---

## Output contract

```json
{
  "method": "house_mode_balance_v1_weighted_points",
  "scores": {
    "angular": 4.0,
    "succedent": 4.1,
    "cadent": 5.4
  },
  "percentages": {
    "angular": 30,
    "succedent": 30,
    "cadent": 40
  }
}
```

---

## Report use

- Angular emphasis can feed sections about directness, visibility, identity axes and relational immediacy.
- Succedent emphasis can feed sections about persistence, values, resource consolidation.
- Cadent emphasis can feed sections about learning, observation, preparation and inner processing.

This is usually more useful for synthesis than for a large user-facing chart.
