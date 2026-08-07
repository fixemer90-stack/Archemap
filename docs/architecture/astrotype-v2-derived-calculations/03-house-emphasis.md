# 03 — House Emphasis

## Purpose

House emphasis shows which life spheres are most loaded by chart points.

It is user-visible in the compact chart section, but must be labelled clearly:

```text
The tallest bar is the strongest house accent in this chart; other bars are relative to it.
```

No `%` labels should be shown in house description cards by default.

---

## Included points

MVP includes:

```text
Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Ascendant, MC
```

Angles are special:

- Ascendant contributes to house 1.
- MC contributes to house 10.

---

## Suggested weights

House emphasis may use the same base point weights as balance v1 for consistency:

```text
Sun 2.0, Moon 2.0, Ascendant 1.8, Mercury/Venus/Mars 1.2, MC 1.0,
Jupiter/Saturn 0.8, Uranus/Neptune/Pluto 0.5
```

Optional later versions may include house cusp rulers or angular boosts, but MVP should not.

---

## Algorithm

```text
for each included point:
  house = point.house
  house_score[house] += POINT_WEIGHT[point.name]

max_score = max(house_score.values())
relative_score[house] = house_score[house] / max_score * 100
```

If all scores are zero, all relative scores are zero.

---

## Output contract

```json
{
  "method": "house_emphasis_v1_weighted_points_relative_to_max",
  "scores": {
    "1": 1.8,
    "2": 1.8,
    "7": 1.2,
    "9": 3.2,
    "10": 2.2
  },
  "relative_scores": {
    "1": 56,
    "2": 56,
    "7": 38,
    "9": 100,
    "10": 69
  },
  "top_houses": [9, 10, 1]
}
```

---

## UI rules

- Show columns labelled `1..12`.
- Do not display `100%` in explanatory cards; it invites confusion.
- Explain relative scale in plain language.
- Add house meaning labels for top houses.
- Empty houses should be described as “less planet-loaded”, not absent.
