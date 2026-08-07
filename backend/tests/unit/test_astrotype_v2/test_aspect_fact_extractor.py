"""Contract tests for Astrotype v2 aspect fact extraction."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.modules.astrotype_v2 import models

ROOT = Path(__file__).resolve().parents[3]

FORBIDDEN_EXTRACTOR_FRAGMENTS = (
    "socionics",
    "function_strength",
    "model_a",
    "report_narrative",
    "chart_snapshots",
    "ChartSnapshot",
)


class _ReferenceRepositoryStub:
    def __init__(self, interpretation: models.AspectPairInterpretation | None) -> None:
        self.interpretation = interpretation
        self.calls: list[dict[str, str]] = []

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
        return self.interpretation


def _aspect(*, chart_id: uuid.UUID, body_a: str = "Saturn", body_b: str = "Mercury") -> models.NatalAspect:
    return models.NatalAspect(
        chart_id=chart_id,
        body_a=body_a,
        body_b=body_b,
        aspect_code="sextile",
        angle_degrees=60.0,
        orb_degrees=1.25,
        applying=True,
        strength=0.9,
    )


@pytest.mark.asyncio
async def test_build_aspect_fact_rows_resolves_reference_and_links_v2_aspect_evidence() -> None:
    from app.modules.astrotype_v2.fact_extractor import build_aspect_fact_rows

    chart_id = uuid.uuid4()
    aspect = _aspect(chart_id=chart_id)
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
    repository = _ReferenceRepositoryStub(interpretation)

    facts, evidence = await build_aspect_fact_rows(
        repository,
        chart_id=chart_id,
        aspects=[aspect],
        locale="ru",
        source_version="v2.0",
    )

    assert repository.calls == [
        {
            "aspect_code": "sextile",
            "planet_a": "Mercury",
            "planet_b": "Saturn",
            "locale": "ru",
            "source_version": "v2.0",
        }
    ]
    assert len(facts) == 1
    assert len(evidence) == 1

    fact = facts[0]
    assert isinstance(fact, models.NatalFact)
    assert fact.chart_id == chart_id
    assert fact.fact_type == "aspect"
    assert fact.fact_key == "aspect:mercury:saturn:sextile"
    assert fact.title == "Mercury sextile Saturn"
    assert fact.summary == "Disciplined thought with practical structure."
    assert fact.weight == 0.9
    assert fact.confidence == 1.0
    assert fact.section_hint == "aspects"
    assert fact.source_version == "v2.0"
    assert fact.payload == {
        "body_a": "Mercury",
        "body_b": "Saturn",
        "aspect_code": "sextile",
        "angle_degrees": 60.0,
        "orb_degrees": 1.25,
        "applying": True,
        "strength": 0.9,
        "reference": {
            "id": str(interpretation.id),
            "summary": "Disciplined thought with practical structure.",
            "keywords": ["discipline", "thinking"],
            "source_version": "v2.0",
        },
    }

    link = evidence[0]
    assert isinstance(link, models.NatalFactEvidence)
    assert link.fact_id == fact.id
    assert link.chart_id == chart_id
    assert link.source_table == "astrotype_v2_natal_aspects"
    assert link.source_id == aspect.id
    assert link.source_key == "aspect:Mercury:Saturn:sextile"
    assert link.payload == {"fact_key": "aspect:mercury:saturn:sextile", "reference_id": str(interpretation.id)}


@pytest.mark.asyncio
async def test_build_aspect_fact_rows_returns_deterministic_fact_when_reference_is_missing() -> None:
    from app.modules.astrotype_v2.fact_extractor import build_aspect_fact_rows

    chart_id = uuid.uuid4()
    aspect = models.NatalAspect(
        chart_id=chart_id,
        body_a="Moon",
        body_b="Mars",
        aspect_code="square",
        angle_degrees=90.0,
        orb_degrees=2.0,
        applying=False,
        strength=None,
    )
    repository = _ReferenceRepositoryStub(None)

    facts, evidence = await build_aspect_fact_rows(
        repository,
        chart_id=chart_id,
        aspects=[aspect],
        locale="ru",
        source_version="v2.0",
    )

    assert facts[0].fact_key == "aspect:moon:mars:square"
    assert facts[0].title == "Moon square Mars"
    assert facts[0].summary == "Moon square Mars with orb 2.0°."
    assert facts[0].weight == 0.0
    assert facts[0].confidence == 0.7
    assert facts[0].payload["reference"] is None
    assert evidence[0].payload == {"fact_key": "aspect:moon:mars:square", "reference_id": None}


def test_fact_extractor_source_uses_reference_lookup_without_legacy_fallback() -> None:
    extractor_path = ROOT / "app" / "modules" / "astrotype_v2" / "fact_extractor.py"
    extractor_text = extractor_path.read_text()

    assert "resolve_aspect_interpretation" in extractor_text
    for fragment in FORBIDDEN_EXTRACTOR_FRAGMENTS:
        assert fragment not in extractor_text
