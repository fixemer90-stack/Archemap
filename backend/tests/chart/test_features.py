"""Unit tests for feature extraction."""

from __future__ import annotations

from datetime import UTC, datetime

from app.chart_engine.chart import build_chart
from app.chart_engine.features import FeatureVector, extract_features


class TestFeatureExtraction:
    def test_extract_returns_feature_vector(self) -> None:
        dt = datetime(1990, 5, 15, 12, 30, tzinfo=UTC)
        chart = build_chart(dt, 55.75, 37.62, "Europe/Moscow")
        features = extract_features(chart)

        assert isinstance(features, FeatureVector)

    def test_elements_sum_to_one(self) -> None:
        dt = datetime(1990, 5, 15, 12, 30, tzinfo=UTC)
        chart = build_chart(dt, 55.75, 37.62, "Europe/Moscow")
        features = extract_features(chart)

        total = features.fire + features.earth + features.air + features.water
        assert abs(total - 1.0) < 0.01

    def test_modalities_sum_to_one(self) -> None:
        dt = datetime(2000, 1, 1, tzinfo=UTC)
        chart = build_chart(dt, 0, 0, "UTC")
        features = extract_features(chart)

        total = features.cardinal + features.fixed + features.mutable
        assert abs(total - 1.0) < 0.01

    def test_values_in_range(self) -> None:
        dt = datetime(1985, 7, 20, 8, 15, tzinfo=UTC)
        chart = build_chart(dt, 48.85, 2.35, "Europe/Paris")
        features = extract_features(chart)

        for val in [
            features.fire,
            features.earth,
            features.air,
            features.water,
            features.cardinal,
            features.fixed,
            features.mutable,
            features.sun_moon_balance,
        ]:
            assert 0.0 <= val <= 1.0, f"Value {val} out of range"

    def test_house_emphasis_not_empty(self) -> None:
        dt = datetime(1990, 5, 15, 12, 30, tzinfo=UTC)
        chart = build_chart(dt, 55.75, 37.62, "Europe/Moscow")
        features = extract_features(chart)

        assert len(features.house_emphasis) > 0
        for val in features.house_emphasis.values():
            assert 0.0 <= val <= 1.0

    def test_aspect_counts_non_negative(self) -> None:
        dt = datetime(2000, 6, 21, tzinfo=UTC)
        chart = build_chart(dt, 48.85, 2.35, "Europe/Paris")
        features = extract_features(chart)

        for count in [
            features.conjunction_count,
            features.trine_count,
            features.square_count,
            features.opposition_count,
        ]:
            assert count >= 0.0

    def test_to_dict(self) -> None:
        dt = datetime(1990, 5, 15, 12, 30, tzinfo=UTC)
        chart = build_chart(dt, 55.75, 37.62, "Europe/Moscow")
        features = extract_features(chart)
        d = features.to_dict()

        assert isinstance(d, dict)
        assert "fire" in d
        assert "house_emphasis" in d
        assert "has_birth_time" in d

    def test_deterministic(self) -> None:
        dt = datetime(2000, 1, 1, tzinfo=UTC)
        chart = build_chart(dt, 0, 0, "UTC")
        f1 = extract_features(chart)
        f2 = extract_features(chart)

        assert f1 == f2
