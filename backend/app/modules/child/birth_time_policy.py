"""Versioned fail-closed policies for child birth-time confidence."""

from __future__ import annotations

from dataclasses import dataclass

BIRTH_TIME_POLICY_VERSION = "child-birth-time-policy-v3"
APPROXIMATE_WINDOW_MINUTES = 60
APPROXIMATE_SAMPLE_OFFSETS_MINUTES = (-60, -30, 0, 30, 60)


@dataclass(frozen=True, slots=True)
class BirthTimePolicy:
    confidence: str
    allowed_fact_families: tuple[str, ...]
    excluded_fact_families: tuple[str, ...]
    uncertainty_reason: str | None


_UNKNOWN_EXCLUSIONS = (
    "houses",
    "angles",
    "house_assignments",
    "house_overlays",
    "time_sensitive_moon",
)


def resolve_birth_time_policy(confidence: str) -> BirthTimePolicy:
    """Return the versioned fact-family boundary for one confidence level."""
    if confidence == "exact":
        return BirthTimePolicy(
            confidence=confidence,
            allowed_fact_families=(
                "planet_positions",
                "planet_signs",
                "moon_sign",
                "aspects",
                "houses",
                "angles",
                "house_assignments",
                "house_overlays",
            ),
            excluded_fact_families=(),
            uncertainty_reason=None,
        )
    if confidence == "approximate":
        return BirthTimePolicy(
            confidence=confidence,
            allowed_fact_families=("stable_planet_signs", "stable_aspects", "stable_moon_sign"),
            excluded_fact_families=(
                "houses",
                "angles",
                "house_assignments",
                "house_overlays",
                "unstable_facts",
            ),
            uncertainty_reason="Birth time is approximate; only facts stable across the versioned window are retained.",
        )
    if confidence == "unknown":
        return BirthTimePolicy(
            confidence=confidence,
            allowed_fact_families=("stable_planet_signs", "stable_aspects"),
            excluded_fact_families=_UNKNOWN_EXCLUSIONS,
            uncertainty_reason=(
                "Birth time is unknown; a synthetic noon chart is technical only and time-sensitive facts are excluded."
            ),
        )
    raise ValueError(f"Unsupported birth-time confidence: {confidence}")


def canonical_excluded_fact_families(
    policy: BirthTimePolicy, unstable_fact_keys: tuple[str, ...] | list[str]
) -> tuple[str, ...]:
    """Keep policy exclusions first, followed by unique unstable fact keys."""

    canonical = policy.excluded_fact_families
    canonical_set = set(canonical)
    return (*canonical, *(key for key in sorted(set(unstable_fact_keys)) if key not in canonical_set))
