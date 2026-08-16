"""Unit tests for chart snapshot service."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.chart_engine.chart import build_chart
from app.core.exceptions import NotFoundError
from app.modules.charts.service import ChartService, _chart_to_dict


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_db: AsyncMock) -> ChartService:
    return ChartService(mock_db)


class TestChartToDict:
    def test_serialization(self) -> None:
        dt = datetime(1990, 5, 15, 12, 30, tzinfo=UTC)
        chart = build_chart(dt, 55.75, 37.62, "Europe/Moscow")
        d = _chart_to_dict(chart)

        assert "planets" in d
        assert "houses" in d
        assert "aspects" in d
        assert len(d["planets"]) == 14
        assert len(d["houses"]) == 12
        assert d["timezone"] == "Europe/Moscow"

    def test_planet_fields(self) -> None:
        dt = datetime(2000, 1, 1, tzinfo=UTC)
        chart = build_chart(dt, 0, 0, "UTC")
        d = _chart_to_dict(chart)

        sun = next(p for p in d["planets"] if p["name"] == "Sun")
        assert "longitude" in sun
        assert "sign" in sun
        assert "house" in sun
        assert "is_retrograde" in sun


class TestGetById:
    async def test_not_found(self, service: ChartService, mock_db: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError, match="Chart snapshot not found"):
            await service.get_by_id("snap-id", "user-id")  # type: ignore[arg-type]


class TestGetOrCompute:
    async def test_returns_cached(self, service: ChartService, mock_db: AsyncMock) -> None:
        mock_snapshot = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_snapshot
        mock_db.execute.return_value = mock_result

        result = await service.get_or_compute("profile-id", "user-id")  # type: ignore[arg-type]
        assert result == mock_snapshot

    async def test_computes_when_no_cache(self, service: ChartService, mock_db: AsyncMock) -> None:
        # First call: no cached snapshot
        mock_no_result = MagicMock()
        mock_no_result.scalars.return_value.first.return_value = None

        # Second call: profile lookup
        mock_profile = MagicMock()
        mock_profile.birth_date = date(1990, 5, 15)
        mock_profile.birth_time = time(12, 30)
        mock_profile.latitude = 55.75
        mock_profile.longitude = 37.62
        mock_profile.timezone = "Europe/Moscow"
        mock_profile_result = MagicMock()
        mock_profile_result.scalar_one_or_none.return_value = mock_profile

        mock_db.execute.side_effect = [mock_no_result, mock_profile_result]
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        await service.get_or_compute("profile-id", "user-id")  # type: ignore[arg-type]
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    async def test_uses_profile_timezone_when_building_chart(
        self,
        service: ChartService,
        mock_db: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_no_result = MagicMock()
        mock_no_result.scalars.return_value.first.return_value = None

        mock_profile = MagicMock()
        mock_profile.birth_date = date(1990, 5, 15)
        mock_profile.birth_time = time(15, 22)
        mock_profile.latitude = 55.7558
        mock_profile.longitude = 37.6173
        mock_profile.timezone = "Europe/Moscow"
        mock_profile_result = MagicMock()
        mock_profile_result.scalar_one_or_none.return_value = mock_profile

        mock_db.execute.side_effect = [mock_no_result, mock_profile_result]
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        captured: dict[str, object] = {}

        def fake_build_chart(
            *, birth_datetime: datetime, latitude: float, longitude: float, timezone_name: str
        ) -> SimpleNamespace:
            captured["birth_datetime"] = birth_datetime
            captured["latitude"] = latitude
            captured["longitude"] = longitude
            captured["timezone_name"] = timezone_name
            return SimpleNamespace(
                planets=[],
                houses=[],
                aspects=[],
                birth_datetime=birth_datetime,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone_name,
                house_system="P",
            )

        monkeypatch.setattr("app.modules.charts.service.build_chart", fake_build_chart)
        monkeypatch.setattr("app.modules.charts.service.extract_features", lambda _: SimpleNamespace())
        monkeypatch.setattr(
            "app.modules.charts.service.evaluate_socionics",
            lambda *_: [
                SimpleNamespace(type_code="EIE", type_name="ЭИЭ", score=1.0, confidence=1.0, functions={}, breakdown={})
            ],
        )
        monkeypatch.setattr(
            "app.modules.charts.service._chart_to_dict",
            lambda chart: {"birth_datetime": chart.birth_datetime.isoformat(), "timezone": chart.timezone},
        )

        await service.get_or_compute("profile-id", "user-id")  # type: ignore[arg-type]

        assert captured["timezone_name"] == "Europe/Moscow"
        assert captured["latitude"] == 55.7558
        assert captured["longitude"] == 37.6173
        assert captured["birth_datetime"] == datetime(1990, 5, 15, 11, 22, tzinfo=UTC)
