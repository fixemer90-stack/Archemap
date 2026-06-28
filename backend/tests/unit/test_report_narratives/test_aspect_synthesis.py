"""RED tests for E14 S02 aspect ranking and pattern clustering."""

from __future__ import annotations

from app.modules.report_narratives.aspect_synthesis import (
    cluster_aspect_patterns,
    rank_chart_aspects,
)


def test_rank_chart_aspects_prioritizes_tight_personal_aspects_over_wide_outer_aspects() -> None:
    chart = {
        "planets": [
            {"name": "Moon", "sign": "Leo", "house": 8},
            {"name": "Mercury", "sign": "Aries", "house": 5},
            {"name": "Venus", "sign": "Libra", "house": 7},
            {"name": "Mars", "sign": "Cancer", "house": 4},
            {"name": "Saturn", "sign": "Capricorn", "house": 10},
            {"name": "Uranus", "sign": "Capricorn", "house": 10},
            {"name": "Neptune", "sign": "Capricorn", "house": 10},
            {"name": "Pluto", "sign": "Scorpio", "house": 2},
        ],
        "aspects": [
            {
                "planet_a": "Moon",
                "planet_b": "Mercury",
                "aspect_type": "trine",
                "orb": 0.4,
                "is_applying": True,
            },
            {
                "planet_a": "Venus",
                "planet_b": "Mars",
                "aspect_type": "square",
                "orb": 1.1,
                "is_applying": True,
            },
            {
                "planet_a": "Uranus",
                "planet_b": "Neptune",
                "aspect_type": "sextile",
                "orb": 5.8,
                "is_applying": False,
            },
        ],
    }

    ranked = rank_chart_aspects(chart)

    assert [item.id for item in ranked[:2]] == [
        "moon_trine_mercury",
        "venus_square_mars",
    ]
    assert ranked[0].weight > ranked[1].weight > ranked[2].weight
    assert ranked[0].section_targets == ["emotions_and_communication", "world_perception"]
    assert ranked[-1].id == "uranus_sextile_neptune"


def test_cluster_aspect_patterns_groups_psychological_mechanisms_and_downweights_outer_noise() -> None:
    chart = {
        "planets": [
            {"name": "Moon", "sign": "Leo", "house": 8},
            {"name": "Mercury", "sign": "Aries", "house": 5},
            {"name": "Venus", "sign": "Libra", "house": 7},
            {"name": "Mars", "sign": "Cancer", "house": 4},
            {"name": "Saturn", "sign": "Capricorn", "house": 10},
            {"name": "Uranus", "sign": "Capricorn", "house": 10},
            {"name": "Neptune", "sign": "Capricorn", "house": 10},
        ],
        "aspects": [
            {
                "planet_a": "Moon",
                "planet_b": "Mercury",
                "aspect_type": "trine",
                "orb": 0.4,
                "is_applying": True,
            },
            {
                "planet_a": "Moon",
                "planet_b": "Saturn",
                "aspect_type": "opposition",
                "orb": 0.9,
                "is_applying": True,
            },
            {
                "planet_a": "Venus",
                "planet_b": "Mars",
                "aspect_type": "square",
                "orb": 1.1,
                "is_applying": True,
            },
            {
                "planet_a": "Uranus",
                "planet_b": "Neptune",
                "aspect_type": "sextile",
                "orb": 5.8,
                "is_applying": False,
            },
        ],
    }

    ranked = rank_chart_aspects(chart)
    patterns = cluster_aspect_patterns(chart, ranked)

    pattern_ids = {pattern.id for pattern in patterns}
    assert "moon_mercury_pattern" in pattern_ids
    assert "venus_mars_pattern" in pattern_ids
    assert "saturn_boundary_pattern" in pattern_ids
    assert all(pattern.evidence_ids for pattern in patterns)
    assert all(pattern.section_targets for pattern in patterns)

    moon_mercury = next(pattern for pattern in patterns if pattern.id == "moon_mercury_pattern")
    assert moon_mercury.pattern_type == "support"
    assert moon_mercury.aspect_ids == ["moon_trine_mercury"]
    assert moon_mercury.section_targets == ["emotions_and_communication", "world_perception"]

    venus_mars = next(pattern for pattern in patterns if pattern.id == "venus_mars_pattern")
    assert venus_mars.pattern_type == "tension"
    assert venus_mars.section_targets == ["relationships", "sexuality"]

    saturn = next(pattern for pattern in patterns if pattern.id == "saturn_boundary_pattern")
    assert saturn.pattern_type == "tension"
    assert "moon_opposition_saturn" in saturn.aspect_ids

    assert all("uranus_sextile_neptune" not in pattern.aspect_ids for pattern in patterns)
