# 07 — Chart Ruler / Ascendant Ruler

## Purpose

Chart ruler calculation identifies where the Ascendant’s ruling energy goes in the chart.

This is one of the most useful deterministic links between the external personality style and a concrete life sphere.

---

## Rulership policy

Astrotype v2 MVP uses:

```text
traditional ruler as primary
modern ruler as secondary for Scorpio, Aquarius, Pisces
```

| Sign | Primary ruler | Secondary ruler |
|---|---|---|
| Aries | Mars | — |
| Taurus | Venus | — |
| Gemini | Mercury | — |
| Cancer | Moon | — |
| Leo | Sun | — |
| Virgo | Mercury | — |
| Libra | Venus | — |
| Scorpio | Mars | Pluto |
| Sagittarius | Jupiter | — |
| Capricorn | Saturn | — |
| Aquarius | Saturn | Uranus |
| Pisces | Jupiter | Neptune |

This policy must be versioned because modern-only astrology would produce different results.

---

## Algorithm

```text
asc_sign = house_1_cusp.sign
primary_ruler = TRADITIONAL_RULER[asc_sign]
secondary_ruler = MODERN_SECONDARY_RULER.get(asc_sign)

primary_position = planet_position[primary_ruler]
secondary_position = planet_position[secondary_ruler] if exists
```

---

## Output contract

```json
{
  "method": "chart_ruler_v1_traditional_primary_modern_secondary",
  "ascendant": {
    "sign": "Scorpio",
    "degree": 19.98
  },
  "primary_ruler": {
    "planet": "Mars",
    "sign": "Taurus",
    "house": 7,
    "is_retrograde": false
  },
  "secondary_ruler": {
    "planet": "Pluto",
    "sign": "Scorpio",
    "house": 12,
    "is_retrograde": false
  }
}
```

---

## Report use

- `core_pattern`: how the personality style finds expression.
- `agency_and_desire`: how the chart ruler acts.
- `relationships_and_intimacy`: if ruler lands in 7th/8th or strongly aspects Venus/Mars/Moon.
- `growth_vector`: if ruler is stressed, retrograde, cadent, or in hard aspects.

---

## UI rules

Can be shown compactly in calculation basis:

```text
ASC: Scorpio
Chart ruler: Mars in Taurus, 7th house
```

Do not call this an “archetype”.
