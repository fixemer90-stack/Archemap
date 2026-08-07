"""Contract tests for Astrotype v2 canonical body ordering."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.astrotype_v2 import models

ROOT = Path(__file__).resolve().parents[3]


class _ScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def scalar_one_or_none(self) -> object | None:
        return self._values[0] if self._values else None


def test_canonical_body_order_exposes_expected_astrological_sequence() -> None:
    from app.modules.astrotype_v2.reference_data import CANONICAL_BODY_ORDER

    assert CANONICAL_BODY_ORDER[:10] == (
        "Sun",
        "Moon",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
    )
    assert "North Node" in CANONICAL_BODY_ORDER
    assert "Chiron" in CANONICAL_BODY_ORDER
    assert len(CANONICAL_BODY_ORDER) == len(set(CANONICAL_BODY_ORDER))


def test_canonicalize_body_pair_normalizes_symmetric_pairs_and_preserves_unknown_tie_break() -> None:
    from app.modules.astrotype_v2.reference_data import canonicalize_body_pair

    assert canonicalize_body_pair("Saturn", "Mercury") == ("Mercury", "Saturn")
    assert canonicalize_body_pair("Uranus", "Mars") == ("Mars", "Uranus")
    assert canonicalize_body_pair("Lilith", "Ceres") == ("Ceres", "Lilith")


def test_seed_pair_examples_are_stored_only_in_canonical_body_order() -> None:
    from app.modules.astrotype_v2.reference_data import CANONICAL_ASPECT_PAIR_INTERPRETATIONS, canonicalize_body_pair

    for seed in CANONICAL_ASPECT_PAIR_INTERPRETATIONS:
        assert (seed.planet_a, seed.planet_b) == canonicalize_body_pair(seed.planet_a, seed.planet_b)


@pytest.mark.asyncio
async def test_repository_normalizes_reversed_pair_lookup_before_querying() -> None:
    from app.modules.astrotype_v2.repository import AstrotypeV2Repository

    interpretation = models.AspectPairInterpretation(
        aspect_code="sextile",
        planet_a="Mercury",
        planet_b="Saturn",
        locale="ru",
        summary="Disciplined thought with practical structure.",
        keywords=["discipline", "thinking"],
        source_version="v2.0",
        enabled=True,
    )
    session = MagicMock()
    session.execute = AsyncMock(return_value=_ScalarResult([interpretation]))
    repository = AstrotypeV2Repository(session)

    assert (
        await repository.get_aspect_pair_interpretation(
            aspect_code="sextile",
            planet_a="Saturn",
            planet_b="Mercury",
            locale="ru",
            source_version="v2.0",
        )
        is interpretation
    )

    statement_text = str(session.execute.await_args.args[0])
    assert "planet_a" in statement_text
    assert "planet_b" in statement_text
    compiled_params = session.execute.await_args.args[0].compile().params
    assert "Mercury" in compiled_params.values()
    assert "Saturn" in compiled_params.values()


def test_chart_adapter_reuses_reference_canonicalizer_instead_of_local_order_table() -> None:
    adapter_path = ROOT / "app" / "modules" / "astrotype_v2" / "chart_adapter.py"
    adapter_text = adapter_path.read_text()

    assert "canonicalize_body_pair" in adapter_text
    assert "_PLANET_ORDER" not in adapter_text
