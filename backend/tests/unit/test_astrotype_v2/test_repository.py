"""Contract tests for Astrotype v2 repository layer."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.astrotype_v2 import models

FORBIDDEN_REPOSITORY_FRAGMENTS = (
    "app.modules.reports",
    "app.modules.report_narratives",
    "app.modules.socionics",
    "chart_snapshots",
    "report_narratives",
    "function_strength",
    "model_a",
)

ROOT = Path(__file__).resolve().parents[3]


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value

    def scalars(self) -> _ScalarResult:
        return self

    def all(self) -> list[object]:
        return [self._value]


@pytest.mark.asyncio
async def test_repository_get_chart_queries_v2_chart_by_id() -> None:
    from app.modules.astrotype_v2.repository import AstrotypeV2Repository

    chart_id = uuid.uuid4()
    expected = object()
    session = MagicMock()
    session.execute = AsyncMock(return_value=_ScalarResult(expected))

    result = await AstrotypeV2Repository(session).get_chart(chart_id)

    assert result is expected
    session.execute.assert_awaited_once()
    statement = session.execute.await_args.args[0]
    assert str(statement).count("astrotype_v2_natal_charts") >= 1
    assert "reports" not in str(statement)
    assert "report_narratives" not in str(statement)


@pytest.mark.asyncio
async def test_repository_get_chart_by_profile_engine_input_uses_v2_unique_key() -> None:
    from app.modules.astrotype_v2.repository import AstrotypeV2Repository

    profile_id = uuid.uuid4()
    expected = object()
    session = MagicMock()
    session.execute = AsyncMock(return_value=_ScalarResult(expected))

    result = await AstrotypeV2Repository(session).get_chart_by_profile_engine_input(
        profile_id=profile_id,
        engine_version="v2.0",
        input_hash="abc123",
    )

    assert result is expected
    statement_text = str(session.execute.await_args.args[0])
    assert "astrotype_v2_natal_charts" in statement_text
    assert "profile_id" in statement_text
    assert "engine_version" in statement_text
    assert "input_hash" in statement_text


@pytest.mark.asyncio
async def test_repository_save_helpers_add_only_v2_model_instances() -> None:
    from app.modules.astrotype_v2.repository import AstrotypeV2Repository

    session = MagicMock()
    repository = AstrotypeV2Repository(session)
    objects = [
        models.NatalFact(),
        models.NatalFactEvidence(),
        models.NatalSynthesis(),
        models.ReportOutline(),
        models.ReportSegmentGeneration(),
        models.NatalInfographicData(),
        models.NatalReport(),
    ]

    for obj in objects:
        returned = await repository.add(obj)
        assert returned is obj

    assert session.add.call_count == len(objects)
    for call in session.add.call_args_list:
        added = call.args[0]
        assert added.__table__.name.startswith("astrotype_v2_")


@pytest.mark.asyncio
async def test_repository_get_latest_report_for_chart_orders_v2_reports() -> None:
    from app.modules.astrotype_v2.repository import AstrotypeV2Repository

    chart_id = uuid.uuid4()
    expected = object()
    session = MagicMock()
    session.execute = AsyncMock(return_value=_ScalarResult(expected))

    result = await AstrotypeV2Repository(session).get_latest_report_for_chart(chart_id)

    assert result is expected
    statement_text = str(session.execute.await_args.args[0])
    assert "astrotype_v2_natal_reports" in statement_text
    assert "version" in statement_text
    assert "reports" not in statement_text.replace("astrotype_v2_natal_reports", "")


@pytest.mark.asyncio
async def test_repository_list_segments_queries_v2_segments_by_outline() -> None:
    from app.modules.astrotype_v2.repository import AstrotypeV2Repository

    outline_id = uuid.uuid4()
    expected = object()
    session = MagicMock()
    session.execute = AsyncMock(return_value=_ScalarResult(expected))

    result = await AstrotypeV2Repository(session).list_segments_for_outline(outline_id)

    assert result == [expected]
    statement_text = str(session.execute.await_args.args[0])
    assert "astrotype_v2_report_segment_generations" in statement_text
    assert "outline_id" in statement_text
    assert "report_narratives" not in statement_text


def test_repository_source_does_not_import_legacy_runtime_modules() -> None:
    repository_path = ROOT / "app" / "modules" / "astrotype_v2" / "repository.py"
    repository_text = repository_path.read_text()

    for fragment in FORBIDDEN_REPOSITORY_FRAGMENTS:
        assert fragment not in repository_text
