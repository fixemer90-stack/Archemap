"""Read-only, aggregate-only census for the retained legacy Career boundary.

The operator must explicitly supply E20_CENSUS_DATABASE_URL; application config
is deliberately not imported. This tool does not prove environment identity,
recover lost data, measure compatibility usage, or authorize removal.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from typing import Any, cast

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

CENSUS_SQL = """
WITH float_zero AS MATERIALIZED (
    -- Match Python's JSON binary64 decoding, including ties rounded to zero.
    -- This positive integer power times an exact decimal is precisely 2^-1075.
    SELECT power(5::numeric, 1075) * 1e-1075::numeric AS half_minimum
), legacy AS MATERIALIZED (
    SELECT user_id, version,
           CASE WHEN status IN ('pending', 'generating', 'ready', 'failed',
                                'deterministic_ready', 'generating_narrative', 'narrative_failed')
                THEN status ELSE 'other' END AS status_bucket
    FROM reports WHERE product = 'career'
), grants AS MATERIALIZED (
    SELECT user_id, starts_at, expires_at,
           CASE WHEN json_typeof(metadata_json::json) = 'object'
                THEN (metadata_json::json -> 'subscription_id')::jsonb
                ELSE metadata_json::jsonb END AS direct_marker,
           CASE WHEN status IN ('active', 'expired', 'revoked', 'suspended')
                THEN status ELSE 'other' END AS status_bucket
    FROM entitlements WHERE product = 'career'
), active_direct AS MATERIALIZED (
    SELECT user_id FROM grants
    WHERE status_bucket = 'active'
      AND (starts_at IS NULL OR starts_at <= CURRENT_TIMESTAMP)
      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
      AND (
          direct_marker IS NULL
          OR direct_marker IN ('null'::jsonb, 'false'::jsonb, '0'::jsonb,
                               '\"\"'::jsonb, '[]'::jsonb, '{}'::jsonb)
          OR CASE WHEN jsonb_typeof(direct_marker) = 'number'
                  THEN abs((direct_marker #>> '{}')::numeric) <= (SELECT half_minimum FROM float_zero)
                  ELSE false END
      )
), report_owners AS MATERIALIZED (
    SELECT DISTINCT user_id FROM legacy
), grant_owners AS MATERIALIZED (
    SELECT DISTINCT user_id FROM active_direct
)
SELECT json_build_object(
    'contract_version', 'e20_legacy_career_census_v1',
    'source_kind', 'connected_database_snapshot',
    'as_of', to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"'),
    'reports', json_build_object(
        'rows', (SELECT count(*) FROM legacy),
        'owners', (SELECT count(*) FROM report_owners),
        'status_counts', (SELECT COALESCE(json_object_agg(status_bucket, n), '{}'::json)
                          FROM (SELECT status_bucket, count(*) AS n FROM legacy GROUP BY status_bucket) s),
        'version_counts', (SELECT COALESCE(json_object_agg(version_bucket, n), '{}'::json)
                           FROM (SELECT CASE WHEN version > 0 THEN version::text ELSE 'invalid' END AS version_bucket,
                                        count(*) AS n FROM legacy GROUP BY 1) v)
    ),
    'career_entitlements', json_build_object(
        'rows', (SELECT count(*) FROM grants),
        'owners', (SELECT count(DISTINCT user_id) FROM grants),
        'active_direct_grants', (SELECT count(*) FROM active_direct),
        'active_direct_owners', (SELECT count(*) FROM grant_owners),
        'status_counts', (SELECT COALESCE(json_object_agg(status_bucket, n), '{}'::json)
                          FROM (SELECT status_bucket, count(*) AS n FROM grants GROUP BY status_bucket) g)
    ),
    'owner_overlap', json_build_object(
        'both', (SELECT count(*) FROM report_owners r JOIN grant_owners g USING (user_id)),
        'report_only', (SELECT count(*) FROM report_owners r
                        WHERE NOT EXISTS (SELECT 1 FROM grant_owners g WHERE g.user_id = r.user_id)),
        'active_direct_grant_only', (SELECT count(*) FROM grant_owners g
                                     WHERE NOT EXISTS (SELECT 1 FROM report_owners r WHERE r.user_id = g.user_id))
    ),
    'compatibility_usage', json_build_object(
        'available', false, 'reason', 'requires_observation_telemetry'
    )
)
"""


def database_url_from_env(variable: str) -> str:
    """Read only the explicitly selected credential, without .env fallbacks."""
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", variable):
        raise ValueError("census_database_env_invalid")
    value = os.environ.get(variable)
    if not value:
        raise ValueError("census_database_url_missing")
    try:
        url = make_url(value)
        if url.drivername != "postgresql+asyncpg" or not url.database:
            raise ValueError("unsupported_driver")
    except Exception:
        raise ValueError("census_database_url_invalid") from None
    return value


async def collect_census(connection: AsyncConnection) -> dict[str, Any]:
    """Return aggregate counts from one confirmed repeatable read-only snapshot."""
    if connection.in_transaction():
        raise ValueError("fresh_connection_required")
    async with connection.begin():
        await connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        await connection.exec_driver_sql("SET LOCAL statement_timeout = '15s'")
        readonly = (await connection.exec_driver_sql("SHOW transaction_read_only")).scalar_one()
        isolation = (await connection.exec_driver_sql("SHOW transaction_isolation")).scalar_one()
        if readonly != "on" or isolation != "repeatable read":
            raise ValueError("census_readonly_unconfirmed")
        result = (await connection.exec_driver_sql(CENSUS_SQL)).scalar_one()
        if not isinstance(result, dict):
            raise ValueError("census_output_invalid")
        return cast(dict[str, Any], result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only aggregate legacy Career census; no application DB default.")
    parser.add_argument(
        "--database-url-env", default="E20_CENSUS_DATABASE_URL", help="Name of an explicit URL environment variable"
    )
    parser.add_argument(
        "--confirm-read-only",
        action="store_true",
        required=True,
        help="Acknowledge the selected read-only census scope",
    )
    return parser


async def _run(variable: str) -> dict[str, Any]:
    url = database_url_from_env(variable)
    engine = create_async_engine(url, echo=False, hide_parameters=True)
    try:
        async with engine.connect() as connection:
            return await collect_census(connection)
    finally:
        await engine.dispose()


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = asyncio.run(_run(args.database_url_env))
    except Exception:
        print("e20_census_failed: verify the selected database and read-only permissions privately", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
