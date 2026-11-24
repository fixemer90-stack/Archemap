"""Offline S04 benchmark: python -m scripts.benchmark_e23_overview (from backend)."""

import argparse
import asyncio
import json
import os
import shlex
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import ORMExecuteState
from sqlalchemy.sql.elements import TextClause

if TYPE_CHECKING:
    from app.modules.analytics.overview import BusinessOverview

BACKEND = Path(__file__).resolve().parents[1]
AS_OF = datetime(2026, 10, 1, 21, tzinfo=UTC)  # October 2, 00:00 Moscow
ZONE = ZoneInfo("Europe/Moscow")
HISTORY_DAYS = 180
WINDOW_LAG = 7  # both explicit calendar windows contain only mature cohorts
BUDGET_MS = 5000
DB_USER = "e23_bench"
DB_NAME = "e23_benchmark"
TABLES = (
    "users",
    "business_events",
    "business_self_readiness_evidence",
    "payments",
    "subscriptions",
    "entitlements",
)

# psql variables are supplied by the runner and cast before use. Fixture-only temp tables
# are discarded at commit. All inserts use the schema and constraints from Alembic head.
SEED_SQL = """
BEGIN;
SET LOCAL TIME ZONE 'UTC';
CREATE TEMP TABLE people ON COMMIT DROP AS
SELECT d, n, n % 10 AS d7_case, n % 20 AS pay_case,
       md5('user-' || d || '-' || n)::uuid AS owner,
       md5('self-' || d || '-' || n)::uuid AS report,
       CAST(:'as_of' AS timestamptz) - d * interval '1 day'
           + interval '12 hours' + (n % 120) * interval '1 minute' AS signup
  FROM generate_series(1, :'history_days'::int) d CROSS JOIN generate_series(0, :'users_per_day'::int - 1) n;

INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified, created_at, updated_at)
SELECT owner, 'synthetic-' || d || '-' || n || '@example.invalid', '!', true, false, d7_case < 8, signup, signup
  FROM people;

CREATE TEMP TABLE self_ready ON COMMIT DROP AS
SELECT *, md5('basic_report_ready:' || report)::uuid AS event_id,
       signup + CASE d7_case WHEN 6 THEN interval '168 hours' WHEN 7 THEN interval '-1 hour'
                    ELSE interval '2 hours' END AS lower_bound
  FROM people WHERE d7_case < 8 OR (d = 45 AND d7_case = 9);

INSERT INTO business_events
    (id, schema_version, event_type, semantic_key, entity_id, subject_id, occurred_at, created_at, updated_at,
     mode, product, details)
SELECT md5(e.kind || ':' || e.entity)::uuid, 1, e.kind, 'v1:' || e.kind || ':' || e.entity || ':-',
       e.entity, p.owner, e.at, e.at, e.at, 'unknown', e.product, e.details
  FROM people p CROSS JOIN LATERAL (
    SELECT 'registration_completed' AS kind, p.owner AS entity, p.signup AS at, NULL::text AS product,
           jsonb_build_object('registration_method', CASE WHEN p.n % 4 = 0 THEN 'oauth' ELSE 'email' END) AS details
    UNION ALL SELECT 'account_verified', p.owner, p.signup + interval '15 minutes', NULL, '{}' WHERE p.d7_case < 8
    UNION ALL SELECT 'report_requested', p.report, p.signup + interval '20 minutes', 'self', '{}' WHERE p.d7_case < 8
    UNION ALL SELECT CASE p.d7_case WHEN 6 THEN 'report_failed' WHEN 7 THEN 'report_partial' ELSE 'report_ready' END,
                     p.report, p.signup + interval '3 hours', 'self', '{}' WHERE p.d7_case < 8
  ) e;

INSERT INTO business_events
    (id, schema_version, event_type, semantic_key, entity_id, subject_id, occurred_at, created_at, updated_at,
     mode, product, details)
SELECT event_id, 1, 'basic_report_ready', 'v1:basic_report_ready:' || report || ':-', report, owner,
       lower_bound, lower_bound, lower_bound, 'unknown', 'self', '{}'
  FROM self_ready;

-- Observe in a second transaction so the seed follows the migrated write-once protocol.
INSERT INTO business_self_readiness_evidence (event_id, report_id, owner_id, generation_id, publish_not_before)
SELECT event_id, report, owner, md5('generation:' || report)::uuid, lower_bound FROM self_ready;
CREATE TEMP TABLE observations AS
SELECT event_id, lower_bound + interval '3 seconds' AS upper_bound FROM self_ready WHERE d7_case <> 9;

INSERT INTO subscription_plans (id, plan_code, display_name, amount, billing_interval)
VALUES (md5('benchmark-plan')::uuid, 'astrotype_plus_monthly', 'Synthetic Plus', 19.99, 'month');
INSERT INTO yookassa_merchant_bindings (id, payment_mode, merchant_account_id)
SELECT md5('benchmark-' || mode)::uuid, mode, 'synthetic-shop-' || mode FROM (VALUES ('live'), ('test')) modes(mode);

CREATE TEMP TABLE attempts ON COMMIT DROP AS
SELECT *, md5('payment:' || owner)::uuid AS payment, md5('subscription:' || owner)::uuid AS subscription,
       signup + interval '1 hour' AS checkout_at,
       CASE WHEN pay_case IN (0, 1, 2, 7, 8) THEN signup + interval '2 hours' END AS paid,
       CASE WHEN pay_case = 1 THEN 'test' WHEN pay_case IN (0, 7, 8) THEN 'live' END AS mode,
       CASE WHEN pay_case IN (0, 1, 2, 7, 8) THEN 'succeeded' WHEN pay_case = 4 THEN 'failed' ELSE 'pending' END
           AS status,
       CASE WHEN pay_case IN (7, 8) THEN 'duplicate-' || d || '-' || (n / 20)
            WHEN pay_case NOT IN (5, 6) THEN 'synthetic-' || owner END AS receipt,
       CASE WHEN n % 40 = 0 THEN 'USD' ELSE 'RUB' END AS currency
  FROM people WHERE pay_case IN (0, 1, 3, 4, 5) OR (d >= 15 AND pay_case IN (2, 6, 7, 8));

INSERT INTO subscriptions
    (id, user_id, plan_id, status, current_period_start, current_period_end, created_at, updated_at)
SELECT subscription, owner, md5('benchmark-plan')::uuid,
       CASE WHEN paid + interval '30 days' <= CAST(:'as_of' AS timestamptz) THEN 'expired'
            WHEN n % 40 = 0 THEN 'cancel_scheduled' ELSE 'active' END,
       paid, paid + interval '30 days', checkout_at, paid
  FROM attempts WHERE paid IS NOT NULL;

INSERT INTO payments (id, user_id, subscription_id, provider, provider_payment_id, amount, currency, status, paid_at,
                      merchant_binding_id, payment_mode, merchant_account_id, created_at, updated_at)
SELECT payment, owner, CASE WHEN paid IS NOT NULL THEN subscription END, 'yookassa', receipt, 19.99, currency,
       status, paid, md5('benchmark-' || mode)::uuid, mode, 'synthetic-shop-' || mode, checkout_at,
       coalesce(paid, checkout_at)
  FROM attempts WHERE pay_case <> 6;

UPDATE subscriptions s SET latest_payment_id = a.payment FROM attempts a WHERE s.id = a.subscription;

INSERT INTO entitlements (id, user_id, product, source_payment_id, starts_at, expires_at, metadata_json,
                          created_at, updated_at)
SELECT md5('grant:' || owner)::uuid, owner, 'self', payment, paid, paid + interval '30 days',
       json_build_object('subscription_id', subscription), paid, paid
  FROM attempts WHERE paid IS NOT NULL;

INSERT INTO business_events
    (id, schema_version, event_type, semantic_key, entity_id, source_id, subject_id, occurred_at, created_at,
     updated_at, mode, product, details)
SELECT md5(e.kind || ':' || a.payment)::uuid, 1, e.kind, 'v1:' || e.kind || ':' || a.payment || ':-',
       a.payment, e.binding, a.owner, e.at, e.at, e.at, e.mode, 'plus', '{}'
  FROM attempts a CROSS JOIN LATERAL (
    SELECT 'checkout_created' AS kind, NULL::uuid AS binding, a.checkout_at AS at, 'unknown' AS mode
     WHERE a.pay_case <> 6
    UNION ALL SELECT 'payment_confirmed', md5('benchmark-' || coalesce(a.mode, 'live'))::uuid,
                     coalesce(a.paid, a.checkout_at), coalesce(a.mode, 'live')
     WHERE a.mode IS NOT NULL OR a.pay_case = 6
    UNION ALL SELECT 'subscription_period_started', NULL, a.paid, a.mode WHERE a.mode IS NOT NULL
  ) e;
COMMIT;

BEGIN;
UPDATE business_self_readiness_evidence p SET observed_at = o.upper_bound
  FROM observations o WHERE p.event_id = o.event_id AND o.upper_bound <= CAST(:'as_of' AS timestamptz);
DROP TABLE observations;
INSERT INTO business_events
    (id, schema_version, event_type, semantic_key, entity_id, occurred_at, created_at, updated_at,
     mode, product, details)
SELECT md5('watermark')::uuid, 1, 'report_opened', 'v1:report_opened:' || md5('watermark-report')::uuid || ':-',
       md5('watermark-report')::uuid, anchor, anchor, anchor, 'unknown', 'self', '{}'
  FROM (SELECT CAST(:'as_of' AS timestamptz) - interval '1 minute' AS anchor) t;
COMMIT;
VACUUM (ANALYZE);
"""


def verify_result(result: "BusinessOverview", days: int, daily: int) -> None:
    # Independent expectations calculated from fixture proportions, not the overview SQL.
    users = days * daily
    attempts = users // 20
    older_attempts = (days - 7) * daily // 20
    assert result.coverage.status == "observed" and result.coverage.window_complete
    assert result.coverage.latest_recorded_at == AS_OF - timedelta(minutes=1)
    assert result.registrations.model_dump() == {"email": users * 3 // 4, "oauth": users // 4, "unknown": 0}
    assert result.verified == users * 8 // 10
    assert result.reports.model_dump() == dict(
        requested=users * 8 // 10, ready=users * 6 // 10, partial=users // 10, failed=users // 10
    )
    assert result.activation_d7.mature_count == users and result.activation_d7.immature_count == 0
    if days == 7:
        assert result.activation_d7.status == "available" and result.activation_d7.rate == Decimal("0.6")
        assert result.activation_d7.activated_count == users * 6 // 10
        assert result.live_cash_received is not None
        assert [entry.model_dump() for entry in result.live_cash_received] == [
            {"currency": currency, "amount": Decimal("19.99") * (attempts // 2)} for currency in ("RUB", "USD")
        ]
    else:
        assert result.activation_d7.status == "unavailable" and result.activation_d7.rate is None
        assert result.activation_d7.activated_count is None and result.live_cash_received is None
    assert result.payments.model_dump() == dict(live=attempts, test=attempts, unknown=4 * older_attempts)
    assert result.checkouts == 5 * attempts + 3 * older_attempts
    assert result.checkout_outcomes.model_dump() == dict(
        confirmed=2 * attempts, failed=attempts, pending=attempts, unknown=attempts + 3 * older_attempts
    )
    assert result.paid_plus.status == "partial" and result.paid_plus.active is None
    assert result.paid_plus.proven_active == 30 * daily // 20
    assert result.live_refunds is None and result.paid_plus.mrr_status == "not_certified"


async def measure(daily: int, repeats: int) -> dict[str, Any]:
    from app.infrastructure.database import engine
    from app.modules.admin.router import business_read_session
    from app.modules.analytics import overview

    read_session = asynccontextmanager(business_read_session)
    statements = {
        "watermark": overview._WATERMARK,
        "d7": overview._D7,
        "active_plus": overview._ACTIVE_PLUS,
        "event_counts": overview._EVENT_COUNTS,
        "checkout_outcomes": overview._CHECKOUT_OUTCOMES,
        "payment_counts": overview._PAYMENT_COUNTS,
    }
    since = AS_OF - timedelta(days=HISTORY_DAYS)
    day_end = AS_OF.astimezone(ZONE).date() - timedelta(days=WINDOW_LAG)
    output: dict[str, Any] = {
        "as_of": AS_OF.isoformat(),
        "history_days": HISTORY_DAYS,
        "users_per_day": daily,
        "repeats": repeats,
        "within_budget": True,
        "windows": {},
    }
    try:
        async with read_session() as db:
            output["postgresql"] = await db.scalar(text("SHOW server_version"))
            output["revision"] = await db.scalar(text("SELECT version_num FROM alembic_version"))
            output["rows"] = {
                table: await db.scalar(text(f"SELECT count(*) FROM {table}"))  # noqa: S608 -- fixed table allowlist
                for table in TABLES
            }
            assert output["rows"]["users"] == daily * HISTORY_DAYS
            assert await db.scalar(text("SELECT inet_server_addr() IS NULL AND current_database() = 'e23_benchmark'"))
            settings = {
                key: await db.scalar(text(f"SHOW {key}"))
                for key in (
                    "transaction_read_only",
                    "transaction_isolation",
                    "statement_timeout",
                    "extra_float_digits",
                )
            }
            assert settings == {
                "transaction_read_only": "on",
                "transaction_isolation": "repeatable read",
                "statement_timeout": "5s",
                "extra_float_digits": "1",
            }
            output["settings"] = settings
            try:
                async with db.begin_nested():
                    await db.execute(text("UPDATE users SET is_active = is_active WHERE false"))
            except DBAPIError as exc:
                assert getattr(exc.orig, "sqlstate", None) == "25006"
                output["write_rejected_sqlstate"] = "25006"
            else:
                raise AssertionError("read-only session accepted a write")

        for days in (7, 90):
            async with read_session() as db:
                day_start = day_end - timedelta(days=days)
                window_from = datetime.combine(day_start, time.min, ZONE).astimezone(UTC)
                window_to = datetime.combine(day_end, time.min, ZONE).astimezone(UTC)
                expected_binds = dict(
                    as_of=AS_OF,
                    since=since,
                    window_from=window_from,
                    window_to=window_to,
                    cohort_from=window_from,
                    cohort_to=window_to,
                )
                calls: list[tuple[TextClause, dict[str, Any]]] = []

                def capture(state: ORMExecuteState, captured: list[tuple[TextClause, dict[str, Any]]] = calls) -> None:
                    assert isinstance(state.statement, TextClause) and isinstance(state.parameters, dict)
                    captured.append((state.statement, state.parameters.copy()))

                walls = []
                report: dict[str, Any] = {
                    "queries": {},
                    "overview": None,
                    "overview_timeout": None,
                    "window_from": window_from.isoformat(),
                    "window_to": window_to.isoformat(),
                }
                # Use a savepoint for each real build;
                # SQLSTATE 57014 aborts only the savepoint, not the read snapshot.
                for _ in range(repeats):
                    calls.clear()
                    start = perf_counter()
                    try:
                        async with db.begin_nested():
                            event.listen(db.sync_session, "do_orm_execute", capture)
                            try:
                                result = await overview.build_overview(
                                    db,
                                    as_of=AS_OF,
                                    from_date=day_start,
                                    to_date=day_end,
                                    timezone="Europe/Moscow",
                                    enabled=True,
                                    coverage_since=since,
                                )
                                walls.append((perf_counter() - start) * 1000)
                            finally:
                                event.remove(db.sync_session, "do_orm_execute", capture)
                    except DBAPIError as exc:
                        if getattr(exc.orig, "sqlstate", None) != "57014" or not calls:
                            raise
                        timed_out = next(name for name, stmt in statements.items() if stmt is calls[-1][0])
                        report["overview_timeout"] = dict(
                            query=timed_out, sqlstate="57014", wall_ms=round((perf_counter() - start) * 1000, 3)
                        )
                        output["within_budget"] = False
                        break
                    verify_result(result, days, daily)
                    assert len(calls) == len(statements)
                    report["overview"] = result.model_dump(mode="json")
                report["overview_wall_ms"] = (
                    {"median": round(median(walls), 3), "max": round(max(walls), 3), "samples": len(walls)}
                    if walls
                    else None
                )
                if walls and max(walls) >= BUDGET_MS:
                    output["within_budget"] = False
                captured_params: dict[str, dict[str, Any]] = {}
                for (name, expected), (emitted, actual) in zip(statements.items(), calls, strict=False):
                    assert emitted is expected and actual == {key: expected_binds[key] for key in expected._bindparams}
                    captured_params[name] = actual
                for name, statement in statements.items():
                    # If build_overview aborted, explain the remaining production statements with the same
                    # typed binds and derived explicit window, checked against every bind captured above.
                    params = captured_params.get(name, {key: expected_binds[key] for key in statement._bindparams})
                    explain = text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON, TIMING OFF) " + statement.text)
                    explain = explain.bindparams(*statement._bindparams.values())
                    samples = []
                    scan_paths: set[str] = set()
                    explain_timeout = None
                    for _ in range(repeats):
                        try:
                            async with db.begin_nested():
                                plan = await db.scalar(explain, params)
                        except DBAPIError as exc:
                            if getattr(exc.orig, "sqlstate", None) != "57014":
                                raise
                            output["within_budget"] = False
                            estimate = text("EXPLAIN (FORMAT JSON) " + statement.text)
                            estimate = estimate.bindparams(*statement._bindparams.values())
                            estimate_plan = await db.scalar(estimate, params)
                            explain_timeout = {
                                "sqlstate": "57014",
                                "estimated_plan": (
                                    json.loads(estimate_plan) if isinstance(estimate_plan, str) else estimate_plan
                                ),
                            }
                            break
                        if isinstance(plan, str):
                            plan = json.loads(plan)
                        item = plan[0]
                        root = item["Plan"]
                        pending = [root]
                        while pending:
                            node = pending.pop()
                            pending.extend(node.get("Plans", []))
                            if "Relation Name" in node or "Index Name" in node:
                                scan_paths.add(
                                    " / ".join(
                                        node[key] for key in ("Node Type", "Relation Name", "Index Name") if key in node
                                    )
                                )
                        samples.append(
                            {
                                "execution_ms": item["Execution Time"],
                                "planning_ms": item["Planning Time"],
                                "shared_hit_blocks": root["Shared Hit Blocks"],
                                "shared_read_blocks": root["Shared Read Blocks"],
                                "temp_written_blocks": root["Temp Written Blocks"],
                            }
                        )
                    durations = [sample["execution_ms"] for sample in samples]
                    if durations and max(durations) >= BUDGET_MS:
                        output["within_budget"] = False
                    report["queries"][name] = {
                        "median_execution_ms": median(durations) if durations else None,
                        "max_execution_ms": max(durations) if durations else None,
                        "binds": "captured" if name in captured_params else "derived_after_overview_timeout",
                        "timeout": explain_timeout,
                        "scan_paths": sorted(scan_paths),
                        "samples": samples,
                    }
                output["windows"][f"{days}d"] = report
    finally:
        await engine.dispose()
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--users-per-day", type=int, default=1000, help="positive multiple of 40 (default: 1000)")
    parser.add_argument("--repeats", type=int, default=5, help="samples per window and statement (default: 5)")
    args = parser.parse_args()
    if args.users_per_day <= 0 or args.users_per_day % 40 or args.repeats < 1:
        parser.error("--users-per-day must be a positive multiple of 40 and --repeats at least 1")
    if not __debug__:
        parser.error("run without Python optimization so verification assertions are enabled")

    env = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
    for key in tuple(os.environ):
        if key.startswith("PG"):
            del os.environ[key]
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    pg = Path(subprocess.check_output(["pg_config", "--bindir"], env=env, text=True).strip())  # noqa: S607
    with TemporaryDirectory(prefix="e23-s04.") as directory:
        root = Path(directory)
        if len(os.fsencode(root / ".s.PGSQL.5432")) >= 108:
            parser.error("TMPDIR is too long for a PostgreSQL Unix socket; choose a shorter private path")
        data = root / "pg"
        from sqlalchemy.engine import URL

        url = URL.create("postgresql+asyncpg", username=DB_USER, database=DB_NAME, query={"host": str(root)})
        env.update(
            DATABASE_URL=url.render_as_string(hide_password=False),
            APP_ENV="development",
            LLM_ENABLED="false",
            LLM_PROVIDER="mock",
            BUSINESS_MONITORING_ENABLED="false",
            BUSINESS_ALERTS_ENABLED="false",
            YANDEX_METRICA_EXPORT_ENABLED="false",
            REDIS_URL=f"unix://{root}/unused-redis.sock?db=0",
        )
        # Application imports only happen in measure(), after the local target is pinned.
        # Drop the optional setting so Pydantic can parse it as None even if inherited.
        env.pop("BUSINESS_MONITORING_COVERAGE_SINCE", None)
        for key in (
            "DATABASE_URL",
            "APP_ENV",
            "LLM_ENABLED",
            "LLM_PROVIDER",
            "BUSINESS_MONITORING_ENABLED",
            "BUSINESS_ALERTS_ENABLED",
            "YANDEX_METRICA_EXPORT_ENABLED",
            "REDIS_URL",
        ):
            os.environ[key] = env[key]
        os.environ.pop("BUSINESS_MONITORING_COVERAGE_SINCE", None)

        def run(program: str, *argv: str, input_sql: str | None = None) -> None:
            executable = str(pg / program) if program != sys.executable else program
            subprocess.run(  # noqa: S603 -- fixed programs and generated local arguments; no shell
                [executable, *argv],
                env=env,
                cwd=BACKEND,
                input=input_sql,
                text=True,
                stdout=sys.stderr,
                check=True,
            )

        run("initdb", "-D", str(data), "-U", DB_USER, "-A", "trust", "--encoding=UTF8", "--locale=C.UTF-8", "--no-sync")
        try:
            run(
                "pg_ctl",
                "-D",
                str(data),
                "-l",
                str(root / "pg.log"),
                "-o",
                f"-F -c listen_addresses='' -k {shlex.quote(str(root))}",
                "-w",
                "start",
            )
            run("createdb", "-h", str(root), "-U", DB_USER, DB_NAME)
            run(sys.executable, "-m", "alembic", "upgrade", "head")
            run(
                "psql",
                "-X",
                "-h",
                str(root),
                "-U",
                DB_USER,
                "-d",
                DB_NAME,
                "-v",
                "ON_ERROR_STOP=1",
                "-v",
                f"as_of={AS_OF.isoformat()}",
                "-v",
                f"history_days={HISTORY_DAYS}",
                "-v",
                f"users_per_day={args.users_per_day}",
                input_sql=SEED_SQL,
            )
            result = asyncio.run(measure(args.users_per_day, args.repeats))
        finally:
            if (data / "postmaster.pid").exists():
                run("pg_ctl", "-D", str(data), "-m", "immediate", "-w", "stop")
    print(json.dumps(result, sort_keys=True, indent=2))
    if not result["within_budget"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
