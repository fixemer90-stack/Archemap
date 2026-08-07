# 02 — Modality Balance

## Purpose

Modality balance estimates how strongly the same chart weight is distributed across:

```text
Кардинальная, Фиксированная, Мутабельная
```

It uses the same points and weights as element balance.

---

## Required consistency rule

```text
Element balance and modality balance use identical point weights.
```

If `Sun = 2.0` in element balance, `Sun = 2.0` in modality balance.

No separate modality-specific weights are allowed in v1.

---

## Sign mapping

| Modality | Signs |
|---|---|
| Кардинальная | Овен, Рак, Весы, Козерог |
| Фиксированная | Телец, Лев, Скорпион, Водолей |
| Мутабельная | Близнецы, Дева, Стрелец, Рыбы |

---

## Algorithm

```text
for each included chart point:
  sign = point.sign
  modality = SIGN_TO_MODALITY[sign]
  score[modality] += POINT_WEIGHT[point.name]

total = sum(all included point weights)
percent[modality] = score[modality] / total * 100
ui_percent = largest_remainder_rounding(percent)
```

---

## Output contract

```json
{
  "method": "weighted_chart_points_v1_personality_heuristic",
  "scores": {
    "cardinal": 3.8,
    "fixed": 5.5,
    "mutable": 4.2
  },
  "percentages": {
    "cardinal": 28,
    "fixed": 41,
    "mutable": 31
  }
}
```

---

## Interpretation boundaries

- Cardinal emphasis: initiation, movement, external push.
- Fixed emphasis: consolidation, persistence, resistance, loyalty to form.
- Mutable emphasis: adaptation, transition, reconfiguration, learning.

These are synthesis hints, not full interpretation by themselves.
