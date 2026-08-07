"""Contract tests for Astrotype v2 reference lookup service."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.astrotype_v2 import models

ROOT = Path(__file__).resolve().parents[3]

FORBIDDEN_LOOKUP_FRAGMENTS = (
    "socionics",
    "function_strength",
    "model_a",
    "report_narrative",
    "chart_snapshots",
    "ChartSnapshot",
)


class _RepositoryStub:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []
        self.interpretation = models.AspectPairInterpretation(
            aspect_code="sextile",
            planet_a="Mercury",
            planet_b="Saturn",
            locale="ru",
            summary="Disciplined thought with practical structure.",
            keywords=["discipline", "thinking"],
            source_version="v2.0",
            enabled=True,
        )

    async def get_aspect_pair_interpretation(
        self,
        *,
        aspect_code: str,
        planet_a: str,
        planet_b: str,
        locale: str = "ru",
        source_version: str = "v2.0",
    ) -> models.AspectPairInterpretation | None:
        self.calls.append(
            {
                "aspect_code": aspect_code,
                "planet_a": planet_a,
                "planet_b": planet_b,
                "locale": locale,
                "source_version": source_version,
            }
        )
        if (aspect_code, planet_a, planet_b, locale, source_version) == (
            "sextile",
            "Mercury",
            "Saturn",
            "ru",
            "v2.0",
        ):
            return self.interpretation
        return None


@pytest.mark.asyncio
async def test_reference_lookup_resolves_reversed_calculated_aspect_to_enabled_interpretation() -> None:
    from app.modules.astrotype_v2.reference_lookup import resolve_aspect_interpretation

    repository = _RepositoryStub()

    interpretation = await resolve_aspect_interpretation(
        repository,
        aspect_code="sextile",
        body_a="Saturn",
        body_b="Mercury",
        locale="ru",
        source_version="v2.0",
    )

    assert interpretation is repository.interpretation
    assert repository.calls == [
        {
            "aspect_code": "sextile",
            "planet_a": "Mercury",
            "planet_b": "Saturn",
            "locale": "ru",
            "source_version": "v2.0",
        }
    ]


@pytest.mark.asyncio
async def test_reference_lookup_returns_none_when_reference_row_is_missing() -> None:
    from app.modules.astrotype_v2.reference_lookup import resolve_aspect_interpretation

    repository = _RepositoryStub()

    assert (
        await resolve_aspect_interpretation(
            repository,
            aspect_code="square",
            body_a="Moon",
            body_b="Mars",
            locale="ru",
            source_version="v2.0",
        )
        is None
    )


def test_reference_lookup_source_does_not_import_legacy_v1_or_typology_modules() -> None:
    lookup_path = ROOT / "app" / "modules" / "astrotype_v2" / "reference_lookup.py"
    lookup_text = lookup_path.read_text()

    assert "canonicalize_body_pair" in lookup_text
    for fragment in FORBIDDEN_LOOKUP_FRAGMENTS:
        assert fragment not in lookup_text
