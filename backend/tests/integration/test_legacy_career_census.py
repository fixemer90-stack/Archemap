"""Exercise E20 census SQL and the PostgreSQL read-only boundary, not a customer census."""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal, localcontext
from typing import Any, cast
from uuid import UUID

import pytest
from scripts import legacy_career_census as census
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.modules.authorization.models import Entitlement
from app.modules.authorization.service import EntitlementsService

pytestmark = pytest.mark.asyncio


def _owner(number: int) -> UUID:
    return UUID(int=number)


async def test_aggregate_census_separates_rows_grants_and_unknown_usage_without_private_fields(
    db_session: AsyncSession,
) -> None:
    assert isinstance(db_session.bind, AsyncEngine)
    async with db_session.bind.connect() as connection:
        # Temporary tables shadow app tables only inside this connection. No
        # application fixture/schema/data is rewritten by the census probe.
        await connection.exec_driver_sql(
            "CREATE TEMP TABLE reports (user_id uuid, product text, status text, version integer, report_data json)"
        )
        await connection.exec_driver_sql(
            "CREATE TEMP TABLE entitlements (user_id uuid, product text, status text, "
            "starts_at timestamptz, expires_at timestamptz, metadata_json json)"
        )
        now = (await connection.exec_driver_sql("SELECT CURRENT_TIMESTAMP")).scalar_one()
        secret = "synthetic-private-name-email-birth-payload"
        reports = [
            (1, "career", "ready", 1),
            (1, "career", secret, 3),
            (2, "career", "failed", 2),
            (3, "self", "ready", 1),
        ]
        for owner, product, status, version in reports:
            await connection.execute(
                text("INSERT INTO reports VALUES (:owner, :product, :status, :version, CAST(:payload AS json))"),
                {
                    "owner": _owner(owner),
                    "product": product,
                    "status": status,
                    "version": version,
                    "payload": json.dumps({"name": secret}),
                },
            )
        grants: list[tuple[int, str, Any, Any, Any]] = [
            (1, "active", now - timedelta(days=1), None, None),
            (3, "active", now - timedelta(days=1), None, {}),
            (3, "active", now - timedelta(days=1), None, None),
            (2, "active", now - timedelta(days=2), now - timedelta(days=1), None),
            (4, "revoked", now - timedelta(days=1), None, None),
            (5, "active", now + timedelta(days=1), None, None),
            (6, "active", now - timedelta(days=1), None, {"subscription_id": str(_owner(40))}),
            (7, "active", now - timedelta(days=1), None, {"subscription_id": 0}),
            (8, "active", now - timedelta(days=1), None, [secret]),
            (9, "active", now - timedelta(days=1), None, None),
            (10, "active", now - timedelta(days=1), None, {}),
            (11, "active", now - timedelta(days=1), now, None),
        ]
        for owner, status, starts_at, expires_at, metadata in grants:
            await connection.execute(
                text(
                    "INSERT INTO entitlements VALUES "
                    "(:owner, 'career', :status, :starts, :expires, CAST(:metadata AS json))"
                ),
                {
                    "owner": _owner(owner),
                    "status": status,
                    "starts": starts_at,
                    "expires": expires_at,
                    "metadata": json.dumps(metadata),
                },
            )
        await connection.execute(
            text("INSERT INTO entitlements VALUES (:owner, 'self', 'active', :starts, NULL, NULL)"),
            {"owner": _owner(20), "starts": now},
        )
        before = (
            (await connection.exec_driver_sql("SELECT json_agg(r) FROM reports r")).scalar_one(),
            (await connection.exec_driver_sql("SELECT json_agg(e) FROM entitlements e")).scalar_one(),
        )
        await connection.commit()
        result = await census.collect_census(connection)
        assert result["contract_version"] == "e20_legacy_career_census_v1"
        assert result["reports"] == {
            "rows": 3,
            "owners": 2,
            "status_counts": {"ready": 1, "failed": 1, "other": 1},
            "version_counts": {"1": 1, "2": 1, "3": 1},
        }
        assert result["career_entitlements"] == {
            "rows": 12,
            "owners": 11,
            "active_direct_grants": 6,
            "active_direct_owners": 5,
            "status_counts": {"active": 11, "revoked": 1},
        }
        assert result["owner_overlap"] == {"both": 1, "report_only": 1, "active_direct_grant_only": 4}
        assert result["compatibility_usage"] == {"available": False, "reason": "requires_observation_telemetry"}
        serialized = json.dumps(result)
        assert secret not in serialized
        assert str(_owner(1)) not in serialized
        after = (
            (await connection.exec_driver_sql("SELECT json_agg(r) FROM reports r")).scalar_one(),
            (await connection.exec_driver_sql("SELECT json_agg(e) FROM entitlements e")).scalar_one(),
        )
        assert before == after
        await connection.rollback()


@pytest.mark.parametrize("metadata", [[], False, 0, "", {}, None])
async def test_census_matches_canonical_access_for_falsy_root_metadata(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, metadata: Any
) -> None:
    assert isinstance(db_session.bind, AsyncEngine)
    async with db_session.bind.connect() as connection:
        await connection.exec_driver_sql(
            "CREATE TEMP TABLE reports (user_id uuid, product text, status text, version integer)"
        )
        await connection.exec_driver_sql(
            "CREATE TEMP TABLE entitlements (user_id uuid, product text, status text, "
            "starts_at timestamptz, expires_at timestamptz, metadata_json json)"
        )
        now = (await connection.exec_driver_sql("SELECT CURRENT_TIMESTAMP")).scalar_one()
        await connection.execute(
            text(
                "INSERT INTO entitlements VALUES (:owner, 'career', 'active', :starts, NULL, CAST(:metadata AS json))"
            ),
            {"owner": _owner(1), "starts": now, "metadata": json.dumps(metadata)},
        )
        await connection.commit()
        grant = Entitlement(
            product="career", status="active", starts_at=now, expires_at=None, metadata_json=cast(Any, metadata)
        )

        async def active_grants(user_id: UUID, product: str) -> list[Entitlement]:
            assert user_id == _owner(1) and product == "career"
            return [grant]

        policy = EntitlementsService(db_session, now=lambda: now)
        monkeypatch.setattr(policy, "_active_entitlements", active_grants)
        assert await policy.has_active_direct_product_access(_owner(1), "career") is True
        result = await census.collect_census(connection)
        assert result["career_entitlements"]["active_direct_grants"] == 1
        assert result["career_entitlements"]["active_direct_owners"] == 1
        assert result["owner_overlap"] == {"both": 0, "report_only": 0, "active_direct_grant_only": 1}


def _raw_numeric_metadata_cases() -> list[tuple[str, str, bool]]:
    # Compute the exact binary64 half-minimum boundary independently of SQL.
    with localcontext() as context:
        context.prec = 1600
        half_minimum = Decimal(2) ** -1075
        near_boundary = Decimal("1e-1100")
        numbers = [
            ("1e-400", True),
            ("-1e-400", True),
            (str(half_minimum), True),
            (str(-half_minimum), True),
            (str(half_minimum - near_boundary), True),
            (str(-half_minimum + near_boundary), True),
            (str(half_minimum + near_boundary), False),
            (str(-half_minimum - near_boundary), False),
            ("5e-324", False),
            ("-5e-324", False),
            ("1e-310", False),
            ("1e400", False),
        ]
    return [
        (location, literal, allowed)
        for location in ("root", "subscription_id")
        for literal, allowed in numbers
        if location != "root" or allowed
    ]


@pytest.mark.parametrize(
    "location,literal,allowed",
    _raw_numeric_metadata_cases(),
    ids=[f"{location}-{index}" for index, (location, _, _) in enumerate(_raw_numeric_metadata_cases())],
)
async def test_raw_json_numeric_truthiness_matches_database_decoded_canonical_access(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, location: str, literal: str, allowed: bool
) -> None:
    assert isinstance(db_session.bind, AsyncEngine)
    async with db_session.bind.connect() as connection:
        await connection.exec_driver_sql(
            "CREATE TEMP TABLE reports (user_id uuid, product text, status text, version integer)"
        )
        await connection.exec_driver_sql(
            "CREATE TEMP TABLE entitlements (user_id uuid, product text, status text, "
            "starts_at timestamptz, expires_at timestamptz, metadata_json json)"
        )
        now = (await connection.exec_driver_sql("SELECT CURRENT_TIMESTAMP")).scalar_one()
        raw_metadata = literal if location == "root" else '{"subscription_id":' + literal + "}"
        await connection.execute(
            text(
                "INSERT INTO entitlements VALUES (:owner, 'career', 'active', :starts, NULL, CAST(:metadata AS json))"
            ),
            {"owner": _owner(1), "starts": now, "metadata": raw_metadata},
        )
        # Fetch through the real configured SQLAlchemy/asyncpg JSON decoder;
        # never json.dumps an already-rounded Python value before insertion.
        decoded = (await connection.exec_driver_sql("SELECT metadata_json FROM entitlements")).scalar_one()
        grant = Entitlement(product="career", status="active", starts_at=now, expires_at=None, metadata_json=decoded)

        async def active_grants(user_id: UUID, product: str) -> list[Entitlement]:
            assert user_id == _owner(1) and product == "career"
            return [grant]

        policy = EntitlementsService(db_session, now=lambda: now)
        monkeypatch.setattr(policy, "_active_entitlements", active_grants)
        assert await policy.has_active_direct_product_access(_owner(1), "career") is allowed
        await connection.commit()
        result = await census.collect_census(connection)
        assert result["career_entitlements"]["active_direct_grants"] == int(allowed)
        assert result["career_entitlements"]["active_direct_owners"] == int(allowed)
        assert result["owner_overlap"]["active_direct_grant_only"] == int(allowed)


async def test_readonly_census_transaction_rejects_a_mutating_query_and_preserves_the_database(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert isinstance(db_session.bind, AsyncEngine)
    async with db_session.bind.connect() as connection:
        # No IF EXISTS: never adopt/drop a pre-existing table on a mistaken target.
        await connection.exec_driver_sql("CREATE TABLE e20_census_test_guard (value integer)")
        await connection.commit()
        try:
            monkeypatch.setattr(census, "CENSUS_SQL", "INSERT INTO e20_census_test_guard VALUES (1) RETURNING value")
            with pytest.raises(DBAPIError) as error:
                await census.collect_census(connection)
            assert getattr(error.value.orig, "sqlstate", None) == "25006"
            assert (await connection.exec_driver_sql("SELECT count(*) FROM e20_census_test_guard")).scalar_one() == 0
            await connection.rollback()
        finally:
            await connection.exec_driver_sql("DROP TABLE e20_census_test_guard")
            await connection.commit()
