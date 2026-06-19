# ruff: noqa: RUF001
"""Unit tests for PDF rendering from saved narrative JSON."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.modules.report_narratives.models import ReportNarrative
from app.modules.reports.models import Report
from app.modules.reports.pdf import generate_report_pdf, render_report_html
from app.modules.reports.tasks import _generate_pdf_async
from tests.unit.test_report_narratives.test_schemas import make_self_narrative_payload


def make_report_data() -> dict[str, object]:
    return {
        "product": "self",
        "archetype": {
            "primary": "Наставник",
            "score": 0.82,
            "confidence": {
                "value": 0.76,
                "label": "high",
                "reason_codes": ["strong_signal"],
            },
        },
        "claims": [
            {
                "claim_id": "claim_main",
                "section": "strengths",
                "archetype": "Наставник",
                "score": 0.82,
                "confidence": {
                    "value": 0.76,
                    "label": "high",
                    "reason_codes": ["strong_signal"],
                },
                "message": "Вы умеете собирать людей вокруг смысла.",
                "basis": [],
                "counter_evidence": [],
            }
        ],
        "chart": {
            "planets": [
                {
                    "name": "Sun",
                    "sign": "Virgo",
                    "sign_degree": 1.09,
                    "house": 9,
                }
            ],
            "aspects": [
                {
                    "planet_a": "Moon",
                    "planet_b": "Mercury",
                    "aspect_type": "trine",
                    "orb": 0.5,
                }
            ],
            "elements": {
                "fire": 0.25,
                "earth": 0.35,
                "air": 0.20,
                "water": 0.20,
            },
        },
        "quality_warning": "Время рождения указано приблизительно.",
        "provenance": {
            "ruleset_version": "v1",
            "engine_version": "0.1.0",
        },
    }


def test_render_report_html_prefers_saved_narrative_before_technical_appendix() -> None:
    narrative = make_self_narrative_payload()

    html = render_report_html(
        make_report_data(),
        profile_name="Алексей",
        narrative_content=narrative,
        narrative_status="ready",
        narrative_error=None,
    )

    assert "Главное о вас" in html
    assert "Открыть Career" in html
    assert "Финальное резюме" in html
    assert "Жизненные сценарии домов" in html
    assert "Тень / риск" in html
    assert "Ограничение" in html
    assert "Это не отменяет перегрузку речи" in html
    assert "moon_trine_mercury" in html
    assert "Техническое приложение" in html
    assert html.index("Главное о вас") < html.index("Техническое приложение")
    assert html.index("Главное о вас") < html.index("Планеты")


def test_render_report_html_shows_deterministic_fallback_warning_when_narrative_failed() -> None:
    html = render_report_html(
        make_report_data(),
        profile_name="Алексей",
        narrative_content=None,
        narrative_status="narrative_failed",
        narrative_error="provider timeout",
    )

    assert "Текстовая narrative-версия недоступна" in html
    assert "provider timeout" in html
    assert "Вы умеете собирать людей вокруг смысла." in html
    assert html.index("Текстовая narrative-версия недоступна") < html.index("Техническое приложение")


def test_render_report_html_handles_missing_narrative_without_llm_text() -> None:
    html = render_report_html(
        make_report_data(),
        profile_name="Алексей",
        narrative_content=None,
        narrative_status=None,
        narrative_error=None,
    )

    assert "Техническое приложение" in html
    assert "Вы умеете собирать людей вокруг смысла." in html
    assert "Текстовая narrative-версия недоступна" not in html
    assert "Главное о вас" not in html


def test_generate_report_pdf_smoke_returns_pdf_bytes() -> None:
    pdf = generate_report_pdf(
        make_report_data(),
        profile_name="Алексей",
        narrative_content=make_self_narrative_payload(),
        narrative_status="ready",
        narrative_error=None,
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_generate_pdf_task_uses_latest_ready_narrative_without_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = Report(
        id=uuid4(),
        user_id=uuid4(),
        profile_id=uuid4(),
        product="self",
        version=1,
        status="ready",
        mode="full",
        report_data=make_report_data(),
        archetype="Наставник",
        score=0.82,
        confidence=0.76,
        pdf_generated=False,
    )
    narrative = ReportNarrative(
        id=uuid4(),
        report_id=report.id,
        product="self",
        prompt_version="self_story_v1",
        model_provider="mock",
        model_name="mock-self-v1",
        status="ready",
        content=make_self_narrative_payload(),
        input_hash="abc123",
        generation_attempts=1,
    )

    captured: dict[str, object] = {}

    def fake_generate_report_pdf(
        report_data: dict[str, object],
        profile_name: str = "",
        *,
        narrative_content: dict[str, object] | None,
        narrative_status: str | None,
        narrative_error: str | None,
    ) -> bytes:
        captured["report_data"] = report_data
        captured["profile_name"] = profile_name
        captured["narrative_content"] = narrative_content
        captured["narrative_status"] = narrative_status
        captured["narrative_error"] = narrative_error
        return b"%PDF-test"

    class FakeScalarCollection:
        def __init__(self, value: object) -> None:
            self._value = value

        def first(self) -> object:
            return self._value

    class FakeScalarResult:
        def __init__(self, value: object) -> None:
            self._value = value

        def scalar_one_or_none(self) -> object:
            return self._value

        def scalars(self) -> FakeScalarCollection:
            return FakeScalarCollection(self._value)

    class FakeSession:
        def __init__(self) -> None:
            self.calls = 0
            self.committed = False

        async def __aenter__(self) -> FakeSession:
            return self

        async def __aexit__(
            self,
            exc_type: object | None,
            exc: object | None,
            tb: object | None,
        ) -> None:
            return None

        async def execute(self, statement):  # type: ignore[no-untyped-def]
            del statement
            self.calls += 1
            if self.calls == 1:
                return FakeScalarResult(report)
            if self.calls == 2:
                return FakeScalarResult(narrative)
            raise AssertionError("Unexpected extra database query")

        async def commit(self) -> None:
            self.committed = True

    fake_session = FakeSession()

    monkeypatch.setattr(
        "app.modules.reports.tasks.async_session_factory",
        lambda: fake_session,
    )
    monkeypatch.setattr(
        "app.modules.reports.tasks.generate_report_pdf",
        fake_generate_report_pdf,
    )
    result = asyncio.run(_generate_pdf_async(report.id, report.user_id, "Алексей"))

    assert fake_session.committed is False
    assert captured["profile_name"] == "Алексей"
    assert captured["narrative_content"] == make_self_narrative_payload()
    assert captured["narrative_status"] == "ready"
    assert captured["narrative_error"] is None
    assert result == {"report_id": str(report.id), "size": len(b"%PDF-test"), "stored": False}
