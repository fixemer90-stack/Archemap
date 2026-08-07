# 01 — Element Balance

## Purpose

Element balance estimates how strongly the chart weight is distributed across:

```text
Огонь, Земля, Воздух, Вода
```

It is a deterministic chart-derived UI/synthesis signal, not an LLM interpretation.

Canonical full method:

`docs/architecture/astrotype-v2-balance-calculation.md`

---

## Included points and weights

Use `weighted_chart_points_v1_personality_heuristic`.

The same included points and weights must be used for both element and modality balance.

```text
Солнце      2.0
Луна        2.0
Асцендент   1.8
Меркурий    1.2
Венера      1.2
Марс        1.2
MC          1.0
Юпитер      0.8
Сатурн      0.8
Уран        0.5
Нептун      0.5
Плутон      0.5
```

These weights are Astrotype v2 product heuristics for personality reports, not universal astrology canon.

---

## Sign mapping

| Element | Signs |
|---|---|
| Огонь | Овен, Лев, Стрелец |
| Земля | Телец, Дева, Козерог |
| Воздух | Близнецы, Весы, Водолей |
| Вода | Рак, Скорпион, Рыбы |

---

## Algorithm

```text
for each included chart point:
  sign = point.sign
  element = SIGN_TO_ELEMENT[sign]
  score[element] += POINT_WEIGHT[point.name]

total = sum(all included point weights)
percent[element] = score[element] / total * 100
ui_percent = largest_remainder_rounding(percent)
```

---

## Output contract

```json
{
  "method": "weighted_chart_points_v1_personality_heuristic",
  "scores": {
    "fire": 2.0,
    "earth": 7.2,
    "air": 2.0,
    "water": 2.3
  },
  "percentages": {
    "fire": 15,
    "earth": 53,
    "air": 15,
    "water": 17
  },
  "included_points": ["Sun", "Moon", "Ascendant", "Mercury", "Venus", "Mars", "MC", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
}
```

---

## UI rules

- Show as relative distribution inside the chart, not absolute elemental “power”.
- Always show method/help text in debug or expanded info.
- Do not imply that low element means absence of that human quality.
- Dominant element can feed report synthesis, but should not become a simplistic label.
