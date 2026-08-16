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
    url: str, *, method: str = "GET", payload: dict[str, Any] | None = None, token: str | None = None
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
        raise RuntimeError(f"{method} {url} -> HTTP {exc.code}: {parsed}") from exc


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

    from app.infrastructure.database import async_session_factory
    from app.modules.auth.models import EmailVerification
    from app.modules.users.models import User

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
    assert assembled["reader_view"]["layout_order"] == ["hero", "narrative", "calculation_layer"]
    assert assembled["reader_view"]["hero"]["eyebrow"] == "Astrotype v2 · натальный отчёт"
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
    assert set(layer["calculation_matrix"]) >= {"house_mode", "hemispheres", "quadrants", "aspect_profile"}
    assert_no_forbidden(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

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
        generation_status, last_generation = request_json(
            f"{args.backend_url}/api/v1/astrotype-v2/reports",
            method="POST",
            payload={"profile_id": profile_id, "force": False},
            token=access_token,
        )
        report_id = last_generation.get("report_id")
        if report_id:
            _, report_payload = request_json(
                f"{args.backend_url}/api/v1/astrotype-v2/reports/{report_id}", token=access_token
            )
            if report_payload["progress"]["status"] == "ready":
                break
        time.sleep(2)
    if report_payload is None:
        raise RuntimeError(f"report not ready before timeout; last_generation={last_generation}")

    assert_canonical_report(report_payload)
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
        "reader_blocks": report_payload["infographic"]["calculation_layer"]["reader_blocks"],
        "frontend_route_http": page_status,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
