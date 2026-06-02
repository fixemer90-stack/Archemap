"""Unit tests for the reports module."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.modules.reports.models import Report, ReportVersion
from app.modules.reports.schemas import ReportResponse, ReportVersionResponse
from app.modules.reports.service import _build_chart_summary

# ── Fixtures ─────────────────────────────────────────────────────────


def make_chart_data() -> dict[str, Any]:
    """Create sample chart data."""
    return {
        "birth_datetime": "1990-08-24T11:00:00+00:00",
        "latitude": 55.7558,
        "longitude": 37.6173,
        "timezone": "Europe/Moscow",
        "house_system": "P",
        "planets": [
            {
                "name": "Sun",
                "longitude": 151.09,
                "latitude": 0.0,
                "speed": 0.96,
                "sign": "Virgo",
                "sign_degree": 1.09,
                "house": 9,
                "is_retrograde": False,
            }
        ],
        "houses": [{"number": 1, "longitude": 236.36, "sign": "Scorpio"}],
        "aspects": [
            {
                "planet_a": "Venus",
                "planet_b": "Neptune",
                "aspect_type": "quincunx",
                "angle": 150.86,
                "orb": 0.86,
                "is_applying": False,
            }
        ],
    }


def make_features() -> dict[str, Any]:
    """Create sample features dict."""
    return {
        "fire": 0.186,
        "earth": 0.571,
        "air": 0.171,
        "water": 0.071,
        "cardinal": 0.371,
        "fixed": 0.400,
        "mutable": 0.229,
        "has_birth_time": True,
        "birth_time_quality": 1.0,
    }


def make_report(
    user_id: UUID | None = None,
    profile_id: UUID | None = None,
    product: str = "self",
    status: str = "ready",
    version: int = 1,
) -> Report:
    """Create a sample Report."""
    return Report(
        id=uuid4(),
        user_id=user_id or uuid4(),
        profile_id=profile_id or uuid4(),
        product=product,
        version=version,
        status=status,
        mode="full",
        report_data={"product": product, "archetype": {"primary": "Стратег"}},
        archetype="Стратег",
        score=0.78,
        confidence=0.72,
        pdf_generated=False,
    )


# ── Chart summary tests ──────────────────────────────────────────────


class TestBuildChartSummary:
    """Test _build_chart_summary helper."""

    def test_basic_structure(self) -> None:
        chart_data = make_chart_data()
        features = make_features()
        summary = _build_chart_summary(chart_data, features)

        assert "planets" in summary
        assert "houses" in summary
        assert "aspects" in summary
        assert "elements" in summary
        assert "modalities" in summary

    def test_elements_from_features(self) -> None:
        chart_data = make_chart_data()
        features = make_features()
        summary = _build_chart_summary(chart_data, features)

        assert summary["elements"]["fire"] == 0.186
        assert summary["elements"]["earth"] == 0.571
        assert summary["elements"]["air"] == 0.171
        assert summary["elements"]["water"] == 0.071

    def test_modalities_from_features(self) -> None:
        chart_data = make_chart_data()
        features = make_features()
        summary = _build_chart_summary(chart_data, features)

        assert summary["modalities"]["cardinal"] == 0.371
        assert summary["modalities"]["fixed"] == 0.400
        assert summary["modalities"]["mutable"] == 0.229

    def test_planets_preserved(self) -> None:
        chart_data = make_chart_data()
        features = make_features()
        summary = _build_chart_summary(chart_data, features)

        assert len(summary["planets"]) == 1
        assert summary["planets"][0]["name"] == "Sun"
        assert summary["planets"][0]["sign"] == "Virgo"

    def test_empty_chart_data(self) -> None:
        chart_data: dict[str, Any] = {}
        features = make_features()
        summary = _build_chart_summary(chart_data, features)

        assert summary["planets"] == []
        assert summary["houses"] == []
        assert summary["aspects"] == []

    def test_missing_features_defaults_to_zero(self) -> None:
        chart_data = make_chart_data()
        features: dict[str, Any] = {}
        summary = _build_chart_summary(chart_data, features)

        assert summary["elements"]["fire"] == 0
        assert summary["modalities"]["cardinal"] == 0


# ── Report model tests ───────────────────────────────────────────────


class TestReportModel:
    """Test Report model defaults."""

    def test_default_status(self) -> None:
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
            status="pending",
        )
        assert report.status == "pending"

    def test_default_mode(self) -> None:
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
            mode="full",
        )
        assert report.mode == "full"

    def test_default_version(self) -> None:
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
            version=1,
        )
        assert report.version == 1

    def test_default_pdf_generated(self) -> None:
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
            pdf_generated=False,
        )
        assert report.pdf_generated is False

    def test_report_with_data(self) -> None:
        data: dict[str, Any] = {"product": "self", "archetype": {"primary": "Стратег"}}
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
            report_data=data,
            archetype="Стратег",
            score=0.78,
            confidence=0.72,
        )
        assert report.report_data == data
        assert report.archetype == "Стратег"
        assert report.score == 0.78
        assert report.confidence == 0.72

    def test_report_optional_fields(self) -> None:
        report = Report(
            user_id=uuid4(),
            profile_id=uuid4(),
            product="self",
        )
        assert report.archetype is None
        assert report.score is None
        assert report.confidence is None
        assert report.pdf_url is None
        assert report.error_message is None


# ── ReportVersion model tests ────────────────────────────────────────


class TestReportVersionModel:
    """Test ReportVersion model."""

    def test_creation(self) -> None:
        rv = ReportVersion(
            report_id=uuid4(),
            version=1,
            report_data={"test": True},
        )
        assert rv.version == 1
        assert rv.report_data == {"test": True}
        assert rv.pdf_url is None
        assert rv.diff_summary is None


# ── Report schema tests ───────────────────────────────────────────────


class TestReportSchemas:
    """Test API response schemas for ORM UUID fields."""

    def test_report_response_accepts_uuid_fields(self) -> None:
        report = make_report()
        report.created_at = report.updated_at = datetime.now(UTC)

        response = ReportResponse.model_validate(report)

        assert response.id == report.id
        assert response.profile_id == report.profile_id

    def test_report_version_response_accepts_uuid_fields(self) -> None:
        version = ReportVersion(
            id=uuid4(),
            report_id=uuid4(),
            version=1,
            report_data={"test": True},
            created_at=datetime.now(UTC),
        )

        response = ReportVersionResponse.model_validate(version)

        assert response.id == version.id
        assert response.report_id == version.report_id
