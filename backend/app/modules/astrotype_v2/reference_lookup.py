"""Reference lookup helpers for Astrotype v2 deterministic interpretation data."""

from __future__ import annotations

from typing import Protocol

from app.modules.astrotype_v2 import models
from app.modules.astrotype_v2.reference_data import canonicalize_body_pair


class SupportsReferenceLookupRepository(Protocol):
    """Read-side repository protocol for v2 reference lookup helpers."""

    async def get_aspect_pair_interpretation(
        self,
        *,
        aspect_code: str,
        planet_a: str,
        planet_b: str,
        locale: str = "ru",
        source_version: str = "v2.0",
    ) -> models.AspectPairInterpretation | None:
        """Return one enabled v2 pair interpretation for a canonical pair key."""
        ...


async def resolve_aspect_interpretation(
    repository: SupportsReferenceLookupRepository,
    *,
    aspect_code: str,
    body_a: str,
    body_b: str,
    locale: str = "ru",
    source_version: str = "v2.0",
) -> models.AspectPairInterpretation | None:
    """Resolve a calculated aspect to an enabled versioned v2 reference interpretation."""
    planet_a, planet_b = canonicalize_body_pair(body_a, body_b)
    return await repository.get_aspect_pair_interpretation(
        aspect_code=aspect_code,
        planet_a=planet_a,
        planet_b=planet_b,
        locale=locale,
        source_version=source_version,
    )
