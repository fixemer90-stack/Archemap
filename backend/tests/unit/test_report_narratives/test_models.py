"""Unit tests for report narrative storage models."""

from __future__ import annotations

from uuid import uuid4

from app.modules.report_narratives.models import ReportNarrative


class TestReportNarrativeModel:
    """Validate ReportNarrative storage contract."""

    def test_creation_with_required_fields(self) -> None:
        narrative = ReportNarrative(
            report_id=uuid4(),
            product="self",
            prompt_version="self_story_v1",
            model_provider="mock",
            model_name="mock-self-narrative",
            status="ready",
            content={"title": "Ваш внутренний портрет", "sections": []},
            input_hash="abc123",
            generation_attempts=1,
        )

        assert narrative.product == "self"
        assert narrative.prompt_version == "self_story_v1"
        assert narrative.model_provider == "mock"
        assert narrative.model_name == "mock-self-narrative"
        assert narrative.content == {"title": "Ваш внутренний портрет", "sections": []}
        assert narrative.input_hash == "abc123"
        assert narrative.generation_attempts == 1

    def test_optional_error_fields_default_to_none(self) -> None:
        narrative = ReportNarrative(
            report_id=uuid4(),
            product="self",
            prompt_version="self_story_v1",
            model_provider="mock",
            model_name="mock-self-narrative",
            status="generating_narrative",
            input_hash="abc123",
        )

        assert narrative.content is None
        assert narrative.error_message is None
        assert narrative.generation_started_at is None
        assert narrative.generation_finished_at is None

    def test_generation_attempts_default_to_zero(self) -> None:
        narrative = ReportNarrative(
            report_id=uuid4(),
            product="self",
            prompt_version="self_story_v1",
            model_provider="mock",
            model_name="mock-self-narrative",
            status="pending",
            input_hash="abc123",
        )

        assert narrative.generation_attempts == 0
