# 09 — Most Aspected Planets

> Status: Неактуально на текущий момент / deferred.
>
> Этот документ сохранён как черновик возможного будущего technical/debug слоя аспектной сети, но `Most aspected planets` не входит в текущий MVP sample и не должен рендериться как пользовательский блок. В текущем макете блок “Самые включённые планеты” удалён, потому что выглядит слабым и слишком близким к архетипному рейтингу.

## Purpose

Most aspected planets identifies which planets are most involved in the aspect network.

This is deferred. If revived later, it may feed internal diagnostics or synthesis, but it must not become a big “dominant archetype” UI block.

---

## Included aspects

Use the same aspect inclusion rules as `aspect_profile_v1_major_aspects`.

---

## Scoring

MVP score combines:

```text
aspect participation
orb exactness
aspect type weight
```

Suggested v1 aspect type weights:

| Aspect | Weight |
|---|---:|
| conjunction | 1.2 |
| opposition | 1.1 |
| square | 1.0 |
| trine | 0.8 |
| sextile | 0.7 |
| quincunx | 0.8 |

Exactness weight:

```text
exactness = max(0, 1 - orb / max_orb_for_aspect_type)
```

Planet score contribution per aspect:

```text
contribution = aspect_type_weight * (0.5 + exactness)
```

Add the same contribution to both planets in the aspect.

---

## Algorithm

```text
planet_scores = {}

for aspect in included_aspects:
  type_weight = ASPECT_TYPE_WEIGHT[aspect.type]
  exactness = max(0, 1 - aspect.orb / allowed_orb(aspect.type))
  contribution = type_weight * (0.5 + exactness)

  planet_scores[aspect.planet_a] += contribution
  planet_scores[aspect.planet_b] += contribution

ranked = sort_desc(planet_scores)
```

---

## Output contract

```json
{
  "method": "most_aspected_planets_v1_major_aspects_exactness",
  "ranked_planets": [
    {
      "planet": "Venus",
      "score": 3.42,
      "aspect_count": 2,
      "evidence_ids": ["aspect_venus_neptune", "aspect_venus_pluto"]
    }
  ]
}
```

---

## Boundaries

Do not present this as:

```text
Your archetype is Venus
```

Better:

```text
Venus is highly connected in the aspect network.
```

This is a technical/synthesis signal.
