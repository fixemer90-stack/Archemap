#!/usr/bin/env python3
"""Local Astrotype V2 full-flow smoke.

Flow: backend health -> frontend route -> register -> DB verification-token lookup
-> verify -> login -> V2 generation -> report read -> canonical reader payload checks.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    retry_rate_limit: bool = True,
) -> tuple[int, dict[str, Any]]:
    ensure_http_url(url)
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"detail": body}
        if retry_rate_limit and exc.code == 429:
            retry_after = _retry_after_seconds(parsed)
            if retry_after is not None:
                time.sleep(retry_after)
                return request_json(
                    url,
                    method=method,
                    payload=payload,
                    token=token,
                    retry_rate_limit=False,
                )
        raise RuntimeError(f"{method} {url} -> HTTP {exc.code}: {parsed}") from exc


def _retry_after_seconds(payload: dict[str, Any]) -> int | None:
    value = payload.get("retry_after")
    if isinstance(value, int | float) and value > 0:
        return min(int(value) + 1, 60)
    return None


def request_text(url: str) -> tuple[int, str]:
    ensure_http_url(url)
    req = urllib.request.Request(url, headers={"Accept": "text/html"})  # noqa: S310
    with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310
        return response.status, response.read().decode("utf-8", errors="replace")


def ensure_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"unsupported URL scheme for smoke request: {parsed.scheme}")


async def latest_verification_token(email: str) -> str:
    from sqlalchemy import select

    from app.infrastructure.database import async_session_factory, engine
    from app.modules.auth.models import EmailVerification
    from app.modules.users.models import User

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(EmailVerification.token)
                .join(User, User.id == EmailVerification.user_id)
                .where(User.email == email, EmailVerification.used_at.is_(None))
                .order_by(EmailVerification.created_at.desc())
                .limit(1)
            )
            token = result.scalar_one_or_none()
            if not token:
                raise RuntimeError(f"verification token not found for {email}")
            return str(token)
    finally:
        await engine.dispose()


async def latest_v2_report_id_for_profile(profile_id: str) -> str | None:
    from uuid import UUID

    from sqlalchemy import select

    from app.infrastructure.database import async_session_factory, engine
    from app.modules.astrotype_v2.models import NatalChart, NatalReport

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(NatalReport.id)
                .join(NatalChart, NatalChart.id == NatalReport.chart_id)
                .where(NatalChart.profile_id == UUID(profile_id))
                .order_by(NatalReport.created_at.desc())
                .limit(1)
            )
            report_id = result.scalar_one_or_none()
            return str(report_id) if report_id is not None else None
    finally:
        await engine.dispose()


def assert_no_forbidden(payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False).lower()
    forbidden = ["socionics", "model a", "function_strengths", "mbti"]
    hits = [marker for marker in forbidden if marker in text]
    if hits:
        raise AssertionError(f"forbidden markers leaked: {hits}")


def assert_canonical_report(payload: dict[str, Any]) -> None:
    report = payload["report"]
    assembled = report["assembled_payload"]
    narrative = report["narrative_payload"]
    layer = payload["infographic"]["calculation_layer"]
    assert assembled["reader_view"]["layout_order"] == [
        "hero",
        "narrative",
        "calculation_layer",
    ]
    assert (
        assembled["reader_view"]["hero"]["eyebrow"] == "Astrotype v2 · натальный отчёт"
    )
    assert narrative["section_order"] == [
        "core_pattern",
        "perception_and_mind",
        "emotional_regulation",
        "agency_and_desire",
        "relationships_and_intimacy",
        "growth_vector",
    ]
    assert len(narrative["sections"]) == 6
    for section in narrative["sections"]:
        assert section["reader_display"]["eyebrow"]
        assert section["reader_display"]["aside_bullets"]
    assert layer["reader_blocks"] == [
        "key_indicators",
        "planet_positions",
        "balance_bars",
        "house_emphasis",
        "aspect_network",
        "key_aspects",
        "calculation_matrix",
    ]
    assert set(layer["key_indicators"]) >= {"ascendant", "mc", "ascendant_ruler"}
    assert layer["planet_positions"]
    assert set(layer["balance_bars"])
    assert layer["house_emphasis"]["bars"]
    assert layer["aspect_network"]["nodes"]
    assert layer["aspect_network"]["edges"]
    assert layer["key_aspects"]
    assert set(layer["calculation_matrix"]) >= {
        "house_mode",
        "hemispheres",
        "quadrants",
        "aspect_profile",
    }
    assert_no_forbidden(payload)


def redact_llm_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Return smoke-safe LLM config evidence without leaking secrets."""

    api_key_present = bool(raw.get("llm_api_key"))
    return {
        "llm_enabled": raw.get("llm_enabled"),
        "llm_provider": raw.get("llm_provider"),
        "llm_model": raw.get("llm_model"),
        "llm_api_key_present": api_key_present,
        "llm_api_key": "[REDACTED]" if api_key_present else "",
        "llm_timeout_seconds": raw.get("llm_timeout_seconds"),
        "llm_max_retries": raw.get("llm_max_retries"),
    }


def llm_config_summary() -> dict[str, Any]:
    from app.config import settings

    return redact_llm_config(
        {
            "llm_enabled": settings.LLM_ENABLED,
            "llm_provider": settings.LLM_PROVIDER,
            "llm_model": settings.LLM_MODEL,
            "llm_api_key": settings.LLM_API_KEY,
            "llm_timeout_seconds": settings.LLM_TIMEOUT_SECONDS,
            "llm_max_retries": settings.LLM_MAX_RETRIES,
        }
    )


def assert_report_progress_ready(progress: dict[str, Any]) -> None:
    status = progress.get("status")
    ready_segments = progress.get("ready_segments")
    total_segments = progress.get("total_segments")
    if status not in {"ready", "complete"}:
        raise AssertionError(f"report progress is not ready/complete: {progress}")
    if ready_segments != total_segments or total_segments != 6:
        raise AssertionError(
            "segment readiness mismatch: "
            + json.dumps(
                {
                    "report_status": status,
                    "ready_segments": ready_segments,
                    "total_segments": total_segments,
                },
                ensure_ascii=False,
            )
        )


def assert_expected_segment_provider(
    payload: dict[str, Any], *, expect_provider: str | None, expect_model: str | None
) -> None:
    if expect_provider is None and expect_model is None:
        return
    segments = (
        payload.get("segments") or payload.get("progress", {}).get("segments") or []
    )
    if not segments:
        raise AssertionError(
            "provider/model assertion requested, but report payload has no segments"
        )
    mismatches: list[dict[str, Any]] = []
    for segment in segments:
        provider = segment.get("provider")
        model = segment.get("model")
        if expect_provider is not None and provider != expect_provider:
            mismatches.append(
                {
                    "section_key": segment.get("section_key"),
                    "provider": provider,
                    "model": model,
                }
            )
            continue
        if expect_model is not None and model != expect_model:
            mismatches.append(
                {
                    "section_key": segment.get("section_key"),
                    "provider": provider,
                    "model": model,
                }
            )
    if mismatches:
        raise AssertionError(
            "segment provider/model mismatch: "
            + json.dumps(
                {
                    "expect_provider": expect_provider,
                    "expect_model": expect_model,
                    "mismatches": mismatches,
                },
                ensure_ascii=False,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--expect-provider", default=None)
    parser.add_argument("--expect-model", default=None)
    args = parser.parse_args()

    config_summary = llm_config_summary()

    health_status, health = request_json(f"{args.backend_url}/api/v1/health")
    assert health_status == 200 and health["status"] == "ok", health

    front_status, front_html = request_text(f"{args.base_url}/")
    assert front_status == 200 and "__next" in front_html

    stamp = int(time.time())
    email = f"v2-smoke-{stamp}@example.com"
    password = "SmokePass123!"
    register_status, register = request_json(
        f"{args.backend_url}/api/v1/auth/register",
        method="POST",
        payload={
            "email": email,
            "password": password,
            "name": "V2 Smoke User",
            "birth_date": "1990-08-24",
            "birth_time": "10:22:00",
            "birth_time_accuracy": "exact",
            "birth_place": "Moscow",
            "latitude": 55.7558,
            "longitude": 37.6173,
            "timezone": "Europe/Moscow",
        },
    )
    assert register_status == 201
    profile_id = register["profile_id"]

    verification_token = asyncio.run(latest_verification_token(email))
    verify_status, _ = request_json(
        f"{args.backend_url}/api/v1/auth/verify",
        method="POST",
        payload={"token": verification_token},
    )
    assert verify_status == 200

    login_status, login = request_json(
        f"{args.backend_url}/api/v1/auth/login",
        method="POST",
        payload={"email": email, "password": password},
    )
    assert login_status == 200
    access_token = login["access_token"]

    generation_status, generation = request_json(
        f"{args.backend_url}/api/v1/astrotype-v2/reports",
        method="POST",
        payload={"profile_id": profile_id, "force": True},
        token=access_token,
    )
    assert generation_status == 202, generation

    deadline = time.time() + args.timeout
    report_payload: dict[str, Any] | None = None
    last_generation = generation
    while time.time() < deadline:
        report_id = asyncio.run(latest_v2_report_id_for_profile(profile_id))
        if report_id:
            _, report_payload = request_json(
                f"{args.backend_url}/api/v1/astrotype-v2/reports/{report_id}",
                token=access_token,
            )
            if report_payload["progress"]["status"] in {"ready", "complete"}:
                break
        _, last_generation = request_json(
            f"{args.backend_url}{generation['links']['progress']}",
            token=access_token,
        )
        time.sleep(5)
    if report_payload is None:
        raise RuntimeError(
            f"report not ready before timeout; last_generation={last_generation}"
        )

    assert_canonical_report(report_payload)
    assert_report_progress_ready(report_payload["progress"])
    assert_expected_segment_provider(
        report_payload,
        expect_provider=args.expect_provider,
        expect_model=args.expect_model,
    )
    page_status, page_html = request_text(f"{args.base_url}/report/v2/{profile_id}")
    assert page_status == 200 and "__next" in page_html

    summary = {
        "status": "ok",
        "checked_at": datetime.now(UTC).isoformat(),
        "profile_id": profile_id,
        "report_id": report_payload["report"]["id"],
        "report_status": report_payload["progress"]["status"],
        "ready_segments": report_payload["progress"]["ready_segments"],
        "total_segments": report_payload["progress"]["total_segments"],
        "llm_config": config_summary,
        "segment_providers": [
            {
                "section_key": segment.get("section_key"),
                "status": segment.get("status"),
                "provider": segment.get("provider"),
                "model": segment.get("model"),
                "prompt_version": segment.get("prompt_version"),
            }
            for segment in report_payload.get("segments", [])
        ],
        "reader_blocks": report_payload["infographic"]["calculation_layer"][
            "reader_blocks"
        ],
        "frontend_route_http": page_status,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
