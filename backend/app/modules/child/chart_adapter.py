"""Birth-time-aware child chart adapter over the deterministic natal engine."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.chart_engine.chart import build_chart
from app.chart_engine.types import ChartData
from app.modules.child.birth_time_policy import (
    APPROXIMATE_SAMPLE_OFFSETS_MINUTES,
    APPROXIMATE_WINDOW_MINUTES,
    BIRTH_TIME_POLICY_VERSION,
    resolve_birth_time_policy,
)

ChartBuilder = Callable[[datetime, float, float, str, str], ChartData]


@dataclass(frozen=True, slots=True)
class ChildChartInput:
    birth_date: date
    birth_time: time | None
    birth_time_confidence: str
    latitude: float
    longitude: float
    timezone: str
    house_system: str = "P"


@dataclass(frozen=True, slots=True)
class ChildChartBuild:
    engine_version: str
    input_hash: str
    birth_time_confidence: str
    allowed_fact_families: tuple[str, ...]
    excluded_fact_families: tuple[str, ...]
    uncertainty_reason: str | None
    calculation_payload: dict[str, Any]


def build_child_chart(
    chart_input: ChildChartInput,
    *,
    engine_version: str,
    chart_builder: ChartBuilder = build_chart,
) -> ChildChartBuild:
    """Calculate and filter a child chart according to birth-time confidence."""
    resolve_birth_time_policy(chart_input.birth_time_confidence)
    if chart_input.birth_time_confidence == "approximate":
        return _build_approximate_chart(
            chart_input=chart_input,
            engine_version=engine_version,
            chart_builder=chart_builder,
        )
    if chart_input.birth_time_confidence == "exact":
        return _build_exact_chart(
            chart_input=chart_input,
            engine_version=engine_version,
            chart_builder=chart_builder,
        )

    return _build_unknown_chart(
        chart_input=chart_input,
        engine_version=engine_version,
        chart_builder=chart_builder,
    )


def _build_unknown_chart(
    *,
    chart_input: ChildChartInput,
    engine_version: str,
    chart_builder: ChartBuilder,
) -> ChildChartBuild:
    if chart_input.birth_time is not None:
        raise ValueError("Unknown birth time must not contain a user-supplied time")
    policy = resolve_birth_time_policy("unknown")
    local_tz = ZoneInfo(chart_input.timezone)
    local_samples = [
        datetime.combine(chart_input.birth_date, time(0, 0), tzinfo=local_tz),
        datetime.combine(chart_input.birth_date, time(12, 0), tzinfo=local_tz),
        datetime.combine(chart_input.birth_date, time(23, 59, 59), tzinfo=local_tz),
    ]
    sample_datetimes = [value.astimezone(UTC) for value in local_samples]
    samples = [
        chart_builder(
            sample_datetime,
            chart_input.latitude,
            chart_input.longitude,
            chart_input.timezone,
            chart_input.house_system,
        )
        for sample_datetime in sample_datetimes
    ]
    reference_chart = samples[1]
    sample_by_body = [{point.name: point for point in sample.planets} for sample in samples]
    facts: dict[str, dict[str, Any]] = {}
    stable_bodies: set[str] = set()
    for point in reference_chart.planets:
        if point.name in {"Ascendant", "MC"}:
            continue
        values = [points[point.name].sign for points in sample_by_body if point.name in points]
        evidence = _stability_evidence(values, len(samples))
        if point.name == "Moon":
            evidence = {
                **evidence,
                "stable": False,
                "reason": "unknown_time_moon",
            }
        fact_key = f"planet_sign:{point.name}"
        facts[fact_key] = evidence
        if evidence["stable"]:
            stable_bodies.add(point.name)

    aspect_sets = [
        {
            (min(aspect.planet_a, aspect.planet_b), max(aspect.planet_a, aspect.planet_b), aspect.aspect_type)
            for aspect in sample.aspects
        }
        for sample in samples
    ]
    stable_aspect_keys = set.intersection(*aspect_sets) if aspect_sets else set()
    stable_aspect_keys = {key for key in stable_aspect_keys if key[0] in stable_bodies and key[1] in stable_bodies}
    reference_aspects = {
        (min(aspect.planet_a, aspect.planet_b), max(aspect.planet_a, aspect.planet_b), aspect.aspect_type): aspect
        for aspect in reference_chart.aspects
    }
    for aspect_key in sorted(set.union(*aspect_sets) if aspect_sets else set()):
        evidence = _stability_evidence(
            [aspect_key in sample_set for sample_set in aspect_sets],
            len(samples),
        )
        if aspect_key[0] not in stable_bodies or aspect_key[1] not in stable_bodies:
            evidence = {**evidence, "stable": False, "reason": "aspect_involves_unstable_body"}
        facts[f"aspect:{':'.join(aspect_key)}"] = evidence

    exclusions = [
        *policy.excluded_fact_families,
        *(fact_key for fact_key, evidence in facts.items() if not evidence["stable"]),
    ]
    payload: dict[str, Any] = {
        "contract_version": BIRTH_TIME_POLICY_VERSION,
        "technical_reference": {
            "birth_datetime_utc": sample_datetimes[1].isoformat(),
            "synthetic_noon": True,
            "user_supplied_time": False,
        },
        "planet_positions": [
            {
                "body": point.name,
                "longitude": None,
                "latitude": None,
                "speed": None,
                "sign": point.sign,
                "sign_degree": None,
                "house_number": None,
                "retrograde": None,
            }
            for point in reference_chart.planets
            if point.name in stable_bodies
        ],
        "houses": [],
        "aspects": [
            {
                "body_a": aspect.planet_a,
                "body_b": aspect.planet_b,
                "aspect_code": aspect.aspect_type,
                "angle_degrees": None,
                "orb_degrees": None,
                "applying": None,
            }
            for key, aspect in reference_aspects.items()
            if key in stable_aspect_keys
        ],
        "stability_evidence": {
            "policy_version": BIRTH_TIME_POLICY_VERSION,
            "window": "local_birth_date",
            "sample_datetimes_utc": [value.isoformat() for value in sample_datetimes],
            "facts": facts,
        },
        "exclusions": sorted(set(exclusions)),
    }
    return ChildChartBuild(
        engine_version=engine_version,
        input_hash=_input_hash(chart_input, engine_version=engine_version),
        birth_time_confidence="unknown",
        allowed_fact_families=policy.allowed_fact_families,
        excluded_fact_families=tuple(sorted(set(exclusions))),
        uncertainty_reason=policy.uncertainty_reason,
        calculation_payload=payload,
    )


def _build_exact_chart(
    *,
    chart_input: ChildChartInput,
    engine_version: str,
    chart_builder: ChartBuilder,
) -> ChildChartBuild:
    if chart_input.birth_time is None:
        raise ValueError("Exact birth time requires a user-supplied time")
    policy = resolve_birth_time_policy("exact")
    birth_datetime_utc = datetime.combine(
        chart_input.birth_date,
        chart_input.birth_time,
        tzinfo=ZoneInfo(chart_input.timezone),
    ).astimezone(UTC)
    chart = chart_builder(
        birth_datetime_utc,
        chart_input.latitude,
        chart_input.longitude,
        chart_input.timezone,
        chart_input.house_system,
    )
    payload: dict[str, Any] = {
        "contract_version": BIRTH_TIME_POLICY_VERSION,
        "technical_reference": {
            "birth_datetime_utc": birth_datetime_utc.isoformat(),
            "synthetic_noon": False,
            "user_supplied_time": True,
        },
        "planet_positions": [
            {
                "body": point.name,
                "longitude": point.longitude,
                "latitude": point.latitude,
                "speed": point.speed,
                "sign": point.sign,
                "sign_degree": point.sign_degree,
                "house_number": point.house,
                "retrograde": point.is_retrograde,
            }
            for point in chart.planets
        ],
        "houses": [
            {
                "house_number": house.number,
                "longitude": house.longitude,
                "sign": house.sign,
            }
            for house in chart.houses
        ],
        "aspects": [
            {
                "body_a": aspect.planet_a,
                "body_b": aspect.planet_b,
                "aspect_code": aspect.aspect_type,
                "angle_degrees": aspect.angle,
                "orb_degrees": aspect.orb,
                "applying": aspect.is_applying,
            }
            for aspect in chart.aspects
        ],
        "stability_evidence": {
            "policy_version": BIRTH_TIME_POLICY_VERSION,
            "exact_input": True,
            "confidence": 1.0,
        },
        "exclusions": [],
    }
    return ChildChartBuild(
        engine_version=engine_version,
        input_hash=_input_hash(chart_input, engine_version=engine_version),
        birth_time_confidence="exact",
        allowed_fact_families=policy.allowed_fact_families,
        excluded_fact_families=policy.excluded_fact_families,
        uncertainty_reason=policy.uncertainty_reason,
        calculation_payload=payload,
    )


def _build_approximate_chart(
    *,
    chart_input: ChildChartInput,
    engine_version: str,
    chart_builder: ChartBuilder,
) -> ChildChartBuild:
    if chart_input.birth_time is None:
        raise ValueError("Approximate birth time requires a user-supplied time")
    policy = resolve_birth_time_policy("approximate")
    local_tz = ZoneInfo(chart_input.timezone)
    center_local = datetime.combine(chart_input.birth_date, chart_input.birth_time, tzinfo=local_tz)
    sample_datetimes = [
        (center_local + timedelta(minutes=offset)).astimezone(UTC) for offset in APPROXIMATE_SAMPLE_OFFSETS_MINUTES
    ]
    samples = [
        chart_builder(
            sample_datetime,
            chart_input.latitude,
            chart_input.longitude,
            chart_input.timezone,
            chart_input.house_system,
        )
        for sample_datetime in sample_datetimes
    ]
    center_chart = samples[APPROXIMATE_SAMPLE_OFFSETS_MINUTES.index(0)]

    facts: dict[str, dict[str, Any]] = {}
    center_by_body = {point.name: point for point in center_chart.planets}
    sample_by_body = [{point.name: point for point in sample.planets} for sample in samples]
    stable_bodies: set[str] = set()
    for body in center_by_body:
        family = "angle_sign" if body in {"Ascendant", "MC"} else "planet_sign"
        values = [points[body].sign for points in sample_by_body if body in points]
        evidence = _stability_evidence(values, len(samples))
        facts[f"{family}:{body}"] = evidence
        if family == "planet_sign" and evidence["stable"]:
            stable_bodies.add(body)

    aspect_sets = [
        {
            (min(aspect.planet_a, aspect.planet_b), max(aspect.planet_a, aspect.planet_b), aspect.aspect_type)
            for aspect in sample.aspects
        }
        for sample in samples
    ]
    center_aspects = {
        (min(aspect.planet_a, aspect.planet_b), max(aspect.planet_a, aspect.planet_b), aspect.aspect_type): aspect
        for aspect in center_chart.aspects
    }
    stable_aspect_keys = set.intersection(*aspect_sets) if aspect_sets else set()
    stable_aspect_keys = {key for key in stable_aspect_keys if key[0] in stable_bodies and key[1] in stable_bodies}
    for aspect_key in sorted(set.union(*aspect_sets) if aspect_sets else set()):
        present = [aspect_key in sample_set for sample_set in aspect_sets]
        evidence = _stability_evidence(present, len(samples))
        if aspect_key[0] not in stable_bodies or aspect_key[1] not in stable_bodies:
            evidence = {**evidence, "stable": False, "reason": "aspect_involves_unstable_body"}
        facts[f"aspect:{':'.join(aspect_key)}"] = evidence

    exclusions = [
        *policy.excluded_fact_families,
        *(fact_key for fact_key, evidence in facts.items() if not evidence["stable"]),
    ]
    payload: dict[str, Any] = {
        "contract_version": BIRTH_TIME_POLICY_VERSION,
        "technical_reference": {
            "birth_datetime_utc": sample_datetimes[APPROXIMATE_SAMPLE_OFFSETS_MINUTES.index(0)].isoformat(),
            "synthetic_noon": False,
            "user_supplied_time": True,
        },
        "planet_positions": [
            {
                "body": point.name,
                "longitude": None,
                "latitude": None,
                "speed": None,
                "sign": point.sign,
                "sign_degree": None,
                "house_number": None,
                "retrograde": None,
            }
            for point in center_chart.planets
            if point.name in stable_bodies
        ],
        "houses": [],
        "aspects": [
            {
                "body_a": aspect.planet_a,
                "body_b": aspect.planet_b,
                "aspect_code": aspect.aspect_type,
                "angle_degrees": None,
                "orb_degrees": None,
                "applying": None,
            }
            for key, aspect in center_aspects.items()
            if key in stable_aspect_keys
        ],
        "stability_evidence": {
            "policy_version": BIRTH_TIME_POLICY_VERSION,
            "window_minutes": APPROXIMATE_WINDOW_MINUTES,
            "sample_offsets_minutes": list(APPROXIMATE_SAMPLE_OFFSETS_MINUTES),
            "sample_datetimes_utc": [value.isoformat() for value in sample_datetimes],
            "facts": facts,
        },
        "exclusions": sorted(set(exclusions)),
    }
    return ChildChartBuild(
        engine_version=engine_version,
        input_hash=_input_hash(chart_input, engine_version=engine_version),
        birth_time_confidence="approximate",
        allowed_fact_families=policy.allowed_fact_families,
        excluded_fact_families=tuple(sorted(set(exclusions))),
        uncertainty_reason=policy.uncertainty_reason,
        calculation_payload=payload,
    )


def _stability_evidence(values: list[Any], sample_count: int) -> dict[str, Any]:
    stable = len(values) == sample_count and len(set(values)) == 1
    max_agreement = max((values.count(value) for value in set(values)), default=0)
    return {
        "stable": stable,
        "confidence": round(max_agreement / sample_count, 3),
        "observed_values": values,
        "sample_count": sample_count,
    }


def _input_hash(chart_input: ChildChartInput, *, engine_version: str) -> str:
    return _stable_hash(
        {
            "birth_date": chart_input.birth_date.isoformat(),
            "birth_time": chart_input.birth_time.isoformat() if chart_input.birth_time else None,
            "birth_time_confidence": chart_input.birth_time_confidence,
            "latitude": chart_input.latitude,
            "longitude": chart_input.longitude,
            "timezone": chart_input.timezone,
            "house_system": chart_input.house_system,
            "engine_version": engine_version,
            "policy_version": BIRTH_TIME_POLICY_VERSION,
        }
    )


def _stable_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()
