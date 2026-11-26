"""Owner-facing aggregate view. No provider, reconciliation or write path."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Context, Decimal, localcontext
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import TextClause

from app.modules.analytics.landing_documents import LandingDocuments

BusinessTimezone = Literal["Europe/Moscow", "UTC"]


class Coverage(BaseModel):
    status: Literal["unavailable", "stale", "observed"] = "unavailable"
    latest_recorded_at: datetime | None = None
    since: datetime | None = None
    window_complete: bool = False


class Registrations(BaseModel):
    email: int | None = None
    oauth: int | None = None
    unknown: int | None = None


class Activation(BaseModel):
    cohort_from: date
    cohort_to: date
    mature_count: int | None = None
    immature_count: int | None = None
    activated_count: int | None = None
    rate: Decimal | None = None
    status: Literal["available", "insufficient_history", "no_data", "unavailable"] = "unavailable"


class Payments(BaseModel):
    live: int | None = None
    test: int | None = None
    unknown: int | None = None


class CheckoutOutcomes(BaseModel):
    pending: int | None = None
    failed: int | None = None
    confirmed: int | None = None
    unknown: int | None = None


class Money(BaseModel):
    currency: str
    amount: Decimal


class PaidPlus(BaseModel):
    active: int | None = None
    proven_active: int | None = None
    status: Literal["observed", "partial", "unavailable"] = "unavailable"
    mrr_status: Literal["not_certified"] = "not_certified"


class Reports(BaseModel):
    requested: int | None = None
    ready: int | None = None
    partial: int | None = None
    failed: int | None = None


class BusinessOverview(BaseModel):
    as_of: datetime
    window_from: datetime
    window_to: datetime
    timezone: BusinessTimezone
    coverage: Coverage = Coverage()
    registrations: Registrations = Registrations()
    landing_documents: LandingDocuments | None = None
    verified: int | None = None
    activation_d7: Activation
    checkouts: int | None = None
    checkout_outcomes: CheckoutOutcomes = CheckoutOutcomes()
    payments: Payments = Payments()
    live_cash_received: list[Money] | None = None
    live_refunds: None = None  # no authoritative refund ledger
    paid_plus: PaidPlus = PaidPlus()
    reports: Reports = Reports()


def _query(sql: str, *datetimes: str) -> TextClause:
    return text(sql).bindparams(*(bindparam(name, type_=DateTime(timezone=True)) for name in datetimes))


_EVENT_COUNTS = _query(
    """
    SELECT event_type, coalesce(details->>'registration_method', '') AS method, count(*) AS n
      FROM business_events
     WHERE occurred_at >= :window_from AND occurred_at < :window_to AND created_at <= :as_of
       AND semantic_key = 'v1:' || event_type || ':' || entity_id::text || ':-'
       AND event_type IN ('registration_completed', 'account_verified', 'checkout_created',
                          'report_requested', 'report_ready', 'report_partial', 'report_failed')
     GROUP BY event_type, method
    """,
    "window_from",
    "window_to",
    "as_of",
)

# Neither timestamp on a readiness fact is proof of first visibility. Use retained
# evidence rather than the live report; only a strictly later lower bound rules out a candidate.
# Canonical signup keys are unique and classified only includes mature signups. Count the
# two populations separately so a generic plan cannot nested-loop them back together.
_D7 = _query(
    """
    WITH signups AS (
        SELECT entity_id, occurred_at AS signup_at, occurred_at + interval '168 hours' AS deadline
          FROM business_events
         WHERE event_type = 'registration_completed'
           AND semantic_key = 'v1:registration_completed:' || entity_id::text || ':-'
           AND occurred_at >= :cohort_from AND occurred_at < :cohort_to AND occurred_at <= :as_of
           AND created_at <= :as_of
    ), readiness AS (
        SELECT s.entity_id,
               CASE WHEN p.observed_at IS NULL OR p.observed_at > :as_of THEN 'unknown'
                    WHEN p.observed_at < s.signup_at THEN 'before_signup'
                    WHEN p.publish_not_before >= s.deadline THEN 'late'
                    WHEN p.publish_not_before >= s.signup_at AND p.observed_at < s.deadline THEN 'in_window'
                    ELSE 'unknown' END AS qualification
          FROM signups s
          JOIN business_events e ON e.subject_id = s.entity_id
          LEFT JOIN business_self_readiness_evidence p
            ON p.event_id = e.id AND p.report_id = e.entity_id AND p.owner_id = s.entity_id
         WHERE e.event_type = 'basic_report_ready' AND e.product = 'self'
           AND e.semantic_key = 'v1:basic_report_ready:' || e.entity_id::text || ':-'
           AND (p.publish_not_before IS NULL OR p.publish_not_before <= :as_of)
           AND s.deadline <= :as_of
    ), classified AS (
        SELECT entity_id,
               bool_or(qualification = 'unknown') AS unknown,
               bool_or(qualification = 'before_signup') AS before_signup,
               bool_or(qualification = 'in_window') AS in_window
          FROM readiness GROUP BY entity_id
    )
    SELECT cohort.mature, cohort.immature, outcomes.unproven, outcomes.activated
      FROM (
          SELECT count(*) FILTER (WHERE deadline <= :as_of) AS mature,
                 count(*) FILTER (WHERE deadline > :as_of) AS immature
            FROM signups
      ) cohort
      CROSS JOIN (
          SELECT count(*) FILTER (WHERE unknown) AS unproven,
                 count(*) FILTER (WHERE NOT unknown AND NOT before_signup AND in_window) AS activated
            FROM classified
      ) outcomes
    """,
    "cohort_from",
    "cohort_to",
    "as_of",
)

# Scope proofs to source id, owner, mode and exact paid timestamp. Rows without
# such a proof remain unknown, even if the ledger happens to carry a mode.
_CANONICAL = """
    e.event_type = 'payment_confirmed' AND e.product = 'plus'
    AND e.semantic_key = 'v1:payment_confirmed:' || p.id::text || ':-'
    AND e.entity_id = p.id AND e.subject_id = p.user_id AND e.source_id = p.merchant_binding_id
    AND e.mode = p.payment_mode AND e.occurred_at = p.paid_at AND e.created_at <= :as_of
    AND e.mode IN ('live', 'test')
    AND p.provider = 'yookassa' AND NULLIF(btrim(p.provider_payment_id), '') IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM payments other
                     WHERE other.id <> p.id AND other.provider = p.provider
                       AND other.provider_payment_id = p.provider_payment_id
                       AND (other.merchant_binding_id = p.merchant_binding_id
                            OR other.merchant_account_id = p.merchant_account_id))
"""

# Pair window rows by identity before classifying proof. A mismatched fact for a ledger row
# is one unknown, not an extra orphan; a fact without an in-window ledger row is also unknown.
_PAYMENT_COUNTS = _query(
    f"""
    WITH window_payments AS (
        SELECT * FROM payments WHERE paid_at >= :window_from AND paid_at < :window_to
    ), window_confirmations AS (
        SELECT * FROM business_events
         WHERE event_type = 'payment_confirmed' AND product = 'plus'
           AND semantic_key = 'v1:payment_confirmed:' || entity_id::text || ':-'
           AND occurred_at >= :window_from AND occurred_at < :window_to
           AND created_at <= :as_of
    ), receipts AS (
        SELECT CASE WHEN {_CANONICAL} THEN p.payment_mode ELSE 'unknown' END AS mode,
               p.currency, CASE WHEN p.amount > 0 AND p.amount < 10000000000000
                                THEN p.amount::text::numeric END AS amount
          FROM window_payments p FULL JOIN window_confirmations e ON e.entity_id = p.id
    )
    SELECT mode, currency, count(*) AS n,
           sum(round(amount, 2)) AS amount,
           count(*) FILTER (WHERE amount IS NULL OR currency NOT IN ('RUB', 'USD', 'EUR')
                                 OR amount <> round(amount, 2)) AS invalid
      FROM receipts GROUP BY mode, currency
    """,  # noqa: S608 -- module constant only; dates are bound.
    "window_from",
    "window_to",
    "as_of",
)

_CHECKOUT_OUTCOMES = _query(
    f"""
    WITH outcomes AS (
        SELECT CASE WHEN EXISTS (SELECT 1 FROM business_events e WHERE {_CANONICAL}) THEN 'confirmed'
                    WHEN p.paid_at IS NOT NULL THEN 'unknown'
                    WHEN p.status IN ('failed', 'cancelled') THEN 'failed'
                    WHEN p.status IN ('pending', 'processing') AND p.provider_payment_id IS NOT NULL THEN 'pending'
                    ELSE 'unknown' END AS status
          FROM business_events checkout LEFT JOIN payments p ON p.id = checkout.entity_id
               AND p.user_id = checkout.subject_id
         WHERE checkout.event_type = 'checkout_created' AND checkout.product = 'plus'
           AND checkout.semantic_key = 'v1:checkout_created:' || checkout.entity_id::text || ':-'
           AND checkout.occurred_at >= :window_from AND checkout.occurred_at < :window_to
           AND checkout.created_at <= :as_of
    )
    SELECT status, count(*) AS n FROM outcomes GROUP BY status
    """,  # noqa: S608 -- module constant only; dates are bound.
    "window_from",
    "window_to",
    "as_of",
)

_ACTIVE_PLUS = _query(
    f"""
    WITH effective AS (
        SELECT DISTINCT s.user_id, (e.mode = 'live') AS live, e.mode
          FROM subscriptions s JOIN subscription_plans plan ON plan.id = s.plan_id
          LEFT JOIN payments p ON p.id = s.latest_payment_id AND p.subscription_id = s.id
           AND p.user_id = s.user_id AND p.paid_at = s.current_period_start
           AND p.refunded_at IS NULL AND p.status = 'succeeded'
          LEFT JOIN business_events e ON {_CANONICAL}
           AND EXISTS (SELECT 1 FROM business_events period
                        WHERE period.event_type = 'subscription_period_started'
                          AND period.semantic_key = 'v1:subscription_period_started:' || p.id::text || ':-'
                          AND period.entity_id = p.id AND period.subject_id = p.user_id
                          AND period.product = 'plus' AND period.mode = e.mode
                          AND period.occurred_at = s.current_period_start AND period.created_at <= :as_of)
           AND EXISTS (SELECT 1 FROM entitlements proof_grant WHERE proof_grant.source_payment_id = p.id
                        AND proof_grant.user_id = s.user_id AND proof_grant.product = 'self'
                        AND proof_grant.status = 'active'
                        AND proof_grant.metadata_json->>'subscription_id' = s.id::text
                        AND proof_grant.starts_at <= :as_of
                        AND (proof_grant.expires_at IS NULL OR proof_grant.expires_at > :as_of))
         WHERE s.status IN ('active', 'cancel_scheduled') AND s.current_period_start <= :as_of
           AND s.current_period_end > :as_of AND plan.plan_code = 'astrotype_plus_monthly'
           AND EXISTS (SELECT 1 FROM entitlements g WHERE g.user_id = s.user_id
                        AND g.status = 'active' AND g.product = 'self'
                        AND g.metadata_json->>'subscription_id' = CAST(s.id AS text)
                        AND (g.starts_at IS NULL OR g.starts_at <= :as_of)
                        AND (g.expires_at IS NULL OR g.expires_at > :as_of))
    )
    SELECT count(DISTINCT user_id) FILTER (WHERE live) AS active,
           count(DISTINCT user_id) FILTER (WHERE mode NOT IN ('live', 'test') OR mode IS NULL) AS unproven
      FROM effective
    """,  # noqa: S608 -- module constant only; dates are bound.
    "as_of",
)

_WATERMARK = _query(
    "SELECT max(created_at) FROM business_events WHERE created_at >= :since AND created_at <= :as_of",
    "since",
    "as_of",
)


async def build_overview(
    db: AsyncSession,
    *,
    as_of: datetime,
    from_date: date | None,
    to_date: date | None,
    timezone: BusinessTimezone,
    enabled: bool,
    coverage_since: datetime | None,
) -> BusinessOverview:
    """Caller supplies a fresh read-only repeatable-read session."""
    if as_of.utcoffset() is None:
        raise ValueError("An aware observation instant is required")
    as_of = as_of.astimezone(UTC)
    zone = ZoneInfo(timezone)
    today = as_of.astimezone(zone).date()
    if (from_date is None) != (to_date is None):
        raise ValueError("Provide both from_date and to_date")
    explicit = from_date is not None
    start = from_date or today - timedelta(days=29)
    end = to_date or today + timedelta(days=1)
    if not (1 <= (end - start).days <= 90 and start <= today and end <= today + timedelta(days=1)):
        raise ValueError("Select a nonempty range of at most 90 days, no later than today")

    def midnight(day: date) -> datetime:
        return datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC)

    window_from, window_to = midnight(start), min(midnight(end), as_of)
    if window_from >= window_to:
        raise ValueError("The selected range has not started")
    cohort_end = end if explicit else today - timedelta(days=7)
    cohort_start = start if explicit else cohort_end - timedelta(days=30)
    result = BusinessOverview(
        as_of=as_of,
        window_from=window_from,
        window_to=window_to,
        timezone=timezone,
        activation_d7=Activation(cohort_from=cohort_start, cohort_to=cohort_end),
    )
    if not enabled or coverage_since is None or coverage_since.utcoffset() is None or coverage_since >= as_of:
        return result
    since = coverage_since.astimezone(UTC)
    latest = await db.scalar(_WATERMARK, {"since": since, "as_of": as_of})
    result.coverage = Coverage(
        status="observed" if latest and latest >= as_of - timedelta(minutes=10) else "stale",
        latest_recorded_at=latest,
        since=since,
        window_complete=since <= window_from,
    )
    if since <= midnight(cohort_start):
        activation = (
            await db.execute(
                _D7,
                {
                    "cohort_from": midnight(cohort_start),
                    "cohort_to": midnight(cohort_end),
                    "as_of": as_of,
                },
            )
        ).one()
        rate = None
        if activation.unproven:
            result.activation_d7.status = "unavailable"
        elif activation.immature:
            result.activation_d7.status = "insufficient_history"
        elif not activation.mature:
            result.activation_d7.status = "no_data"
        else:
            result.activation_d7.status = "available"
            with localcontext(Context(prec=50)):
                rate = Decimal(activation.activated) / Decimal(activation.mature)
        result.activation_d7.mature_count = activation.mature
        result.activation_d7.immature_count = activation.immature
        result.activation_d7.activated_count = None if activation.unproven else activation.activated
        result.activation_d7.rate = rate

    active = (await db.execute(_ACTIVE_PLUS, {"as_of": as_of})).one()
    result.paid_plus = PaidPlus(
        active=None if active.unproven else active.active,
        proven_active=active.active,
        status="partial" if active.unproven else "observed",
    )
    if since >= window_to:
        return result
    params = {"window_from": max(since, window_from), "window_to": window_to, "as_of": as_of}
    counts = (await db.execute(_EVENT_COUNTS, params)).all()
    methods = {row.method: row.n for row in counts if row.event_type == "registration_completed"}
    result.registrations = Registrations(
        email=methods.get("email", 0),
        oauth=methods.get("oauth", 0),
        unknown=sum(n for method, n in methods.items() if method not in {"email", "oauth"}),
    )
    by_type: dict[str, int] = {}
    for row in counts:
        by_type[row.event_type] = by_type.get(row.event_type, 0) + row.n
    result.verified = by_type.get("account_verified", 0)
    result.checkouts = by_type.get("checkout_created", 0)
    outcomes = {row.status: row.n for row in (await db.execute(_CHECKOUT_OUTCOMES, params)).all()}
    result.checkout_outcomes = CheckoutOutcomes(
        **{name: outcomes.get(name, 0) for name in CheckoutOutcomes.model_fields}
    )
    result.reports = Reports(**{name: by_type.get(f"report_{name}", 0) for name in Reports.model_fields})
    payment_totals: dict[str, int] = {"live": 0, "test": 0, "unknown": 0}
    cash: list[Money] = []
    cash_complete = True
    for row in (await db.execute(_PAYMENT_COUNTS, params)).all():
        mode = row.mode if row.mode in ("live", "test") else "unknown"
        payment_totals[mode] += row.n
        if mode == "live":
            if row.amount is None or row.invalid:
                cash_complete = False
            else:
                cash.append(Money(currency=row.currency, amount=row.amount))
    result.payments = Payments(**payment_totals)
    if cash_complete and result.coverage.window_complete and not payment_totals["unknown"]:
        result.live_cash_received = sorted(cash, key=lambda item: item.currency)
    return result
