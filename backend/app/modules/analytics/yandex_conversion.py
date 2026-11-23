"""Explicit, default-off S08 operations; no API, scheduler, or producer hooks."""

import asyncio
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

import httpx
from pydantic import SecretStr
from sqlalchemy import Text, cast, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased

from app.config import settings
from app.infrastructure.database import async_session_factory
from app.modules.analytics.attribution import read_active_attribution
from app.modules.analytics.models import BusinessEvent
from app.modules.analytics.service import utc_time
from app.modules.analytics.yandex_conversion_models import YandexConversionExport
from app.modules.analytics.yandex_transport import (
    CLIENT_ID,
    MetricaDestination,
    MetricaTransport,
    UploadPhase,
    UploadReceipt,
)
from app.modules.payments.models import Payment, YooKassaMerchantBinding
from app.modules.subscriptions.models import Subscription, SubscriptionEvent


@dataclass(frozen=True, slots=True)
class CurrentConsent:
    owner_id: UUID
    policy_version: str
    counter_id: int
    consented_at: datetime
    captured_at: datetime
    expires_at: datetime
    is_current: bool
    client_id: str | None = field(repr=False)


async def read_s05_consent(
    session: AsyncSession,
    *,
    owner_id: UUID,
    approved_policy_version: str,
    approved_counter_id: int,
    occurred_at: datetime,
    now: datetime,
    for_dispatch: bool = False,
) -> CurrentConsent | None:
    snapshot = await read_active_attribution(
        session,
        owner_id=owner_id,
        approved_policy_version=approved_policy_version,
        approved_counter_id=approved_counter_id,
        occurred_at=occurred_at,
        now=now,
        for_dispatch=for_dispatch,
    )
    if snapshot is None:
        return None
    # The consent-backed capture is usable only once it has been bound to this account.
    return CurrentConsent(
        owner_id=snapshot.owner_id,
        policy_version=snapshot.policy_version,
        counter_id=snapshot.counter_id,
        consented_at=snapshot.bound_at,
        captured_at=snapshot.captured_at,
        expires_at=snapshot.expires_at,
        is_current=True,
        client_id=snapshot.client_id,
    )


@dataclass(frozen=True, slots=True)
class ExportConfig:
    destination: MetricaDestination
    policy_version: str
    not_before: datetime

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", self.policy_version):
            raise ValueError("invalid export policy version")
        utc_time(self.not_before)


def load_export_config() -> ExportConfig | None:
    """Management token is separate from Yandex login credentials; no dotenv fallback for secrets."""
    if not settings.YANDEX_METRICA_EXPORT_ENABLED:
        return None
    counter = os.getenv("YANDEX_METRICA_EXPORT_COUNTER_ID", "")
    if not re.fullmatch(r"[1-9][0-9]{0,18}", counter):
        return None
    try:
        return ExportConfig(
            MetricaDestination(
                int(counter),
                os.getenv("YANDEX_METRICA_EXPORT_TARGET", ""),
                SecretStr(os.getenv("YANDEX_METRICA_EXPORT_OAUTH_TOKEN", "")),
            ),
            os.getenv("YANDEX_METRICA_EXPORT_POLICY_VERSION", ""),
            datetime.fromisoformat(os.getenv("YANDEX_METRICA_EXPORT_NOT_BEFORE", "")),
        )
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class ExportResult:
    status: Literal["disabled", "not_found", "skipped", "outcome_unknown", "upload_received"]
    reason: str | None = None
    upload_id: int | None = None
    upload_phase: UploadPhase | None = None


# Yandex's attribution window is about the last site session, not payment age.
# These conservative local cutoffs cannot prove that provider matching will succeed.
MAX_AGE = timedelta(days=21)
DISPATCH_DEADLINE_SECONDS = 10.0
_SKIP = Literal["outside_window", "unproven_purchase", "no_current_consent"]


def _now() -> datetime:
    return datetime.now(UTC)


def _in_window(occurred_at: datetime, now: datetime, config: ExportConfig) -> bool:
    return config.not_before <= occurred_at < now and now - occurred_at < MAX_AGE


def _contact_id(
    consent: CurrentConsent | None, owner: UUID, occurred_at: datetime, now: datetime, config: ExportConfig
) -> str | None:
    if (
        consent is None
        or consent.is_current is not True
        or consent.owner_id != owner
        or consent.policy_version != config.policy_version
        or consent.counter_id != config.destination.counter_id
        or not isinstance(consent.client_id, str)
        or not CLIENT_ID.fullmatch(consent.client_id)
    ):
        return None
    try:
        granted, captured, expires = map(utc_time, (consent.consented_at, consent.captured_at, consent.expires_at))
    except ValueError:
        return None
    if granted <= occurred_at and captured <= occurred_at <= now < expires and now - captured < MAX_AGE:
        return consent.client_id
    return None


async def _proven_purchase(session: AsyncSession, event_id: UUID) -> tuple[UUID, datetime] | None:
    """Bind the S03 immutable fact pair to one proven, unrefunded initial ledger attempt."""
    period = aliased(BusinessEvent)
    payment = Payment
    binding = YooKassaMerchantBinding
    fact = BusinessEvent
    fields = payment.metadata_json
    result = await session.execute(
        select(payment.user_id, fact.occurred_at)
        .select_from(fact)
        .join(payment, payment.id == fact.entity_id)
        .join(binding, binding.id == payment.merchant_binding_id)
        .join(Subscription, Subscription.id == payment.subscription_id)
        .join(
            SubscriptionEvent,
            SubscriptionEvent.event_key == func.concat("initial_payment_succeeded:", payment.provider_payment_id),
        )
        .join(
            period, period.semantic_key == func.concat("v1:subscription_period_started:", cast(payment.id, Text), ":-")
        )
        .where(
            fact.id == event_id,
            fact.schema_version == 1,
            fact.event_type == "payment_confirmed",
            fact.semantic_key == func.concat("v1:payment_confirmed:", cast(payment.id, Text), ":-"),
            fact.product == "plus",
            fact.mode == "live",
            fact.subject_id == payment.user_id,
            fact.source_id == payment.merchant_binding_id,
            fact.occurred_at == payment.paid_at,
            fact.details == {},
            period.schema_version == 1,
            period.event_type == "subscription_period_started",
            period.entity_id == payment.id,
            period.product == "plus",
            period.mode == "live",
            period.subject_id == payment.user_id,
            period.source_id.is_(None),
            period.occurred_at == fact.occurred_at,
            period.details == {},
            payment.provider == "yookassa",
            func.length(func.btrim(payment.provider_payment_id)) > 0,
            payment.status == "succeeded",
            payment.refunded_at.is_(None),
            payment.payment_mode == "live",
            payment.amount > 0,
            cast(payment.amount, Text).not_in(("NaN", "Infinity", "-Infinity")),
            payment.currency == "RUB",
            binding.payment_mode == "live",
            binding.merchant_account_id == payment.merchant_account_id,
            Subscription.user_id == payment.user_id,
            Subscription.provider == "yookassa",
            SubscriptionEvent.subscription_id == Subscription.id,
            SubscriptionEvent.provider_event_id == payment.provider_payment_id,
            SubscriptionEvent.event_type == "initial_payment_succeeded",
            SubscriptionEvent.effective_at == fact.occurred_at,
            SubscriptionEvent.payload_json["payment_id"].as_string() == cast(payment.id, Text),
            fields["product_id"].as_string() == "astrotype_plus_monthly",
            fields["plan_code"].as_string() == "astrotype_plus_monthly",
            fields["subscription_id"].as_string() == cast(payment.subscription_id, Text),
            or_(fields["billing_reason"].as_string().is_(None), fields["billing_reason"].as_string() == "initial"),
        )
    )
    row = result.one_or_none()
    return row._tuple() if row is not None else None


def _result(row: YandexConversionExport) -> ExportResult:
    phase = UploadPhase(row.upload_phase) if row.upload_phase is not None else None
    if row.status == "skipped":
        return ExportResult("skipped", reason=row.reason)
    if row.status == "upload_received":
        return ExportResult("upload_received", upload_id=row.upload_id, upload_phase=phase)
    return ExportResult("outcome_unknown")


async def export_initial_purchase(
    event_id: UUID,
    *,
    sessions: async_sessionmaker[AsyncSession] = async_session_factory,
    clock: Callable[[], datetime] = _now,
    mock_transport: httpx.MockTransport | None = None,
) -> ExportResult:
    """Trusted operations entrypoint: one explicit committed event ID. No replay or backfill scan."""
    config = load_export_config()
    if config is None:
        return ExportResult("disabled")
    async with sessions.begin() as session:
        existing = await session.get(YandexConversionExport, event_id)
        if existing is not None:
            return _result(existing)
        if await session.scalar(select(BusinessEvent.id).where(BusinessEvent.id == event_id)) is None:
            return ExportResult("not_found")
        purchase = await _proven_purchase(session, event_id)
        now = utc_time(clock())
        reason: _SKIP | None = None
        if purchase is None:
            reason = "unproven_purchase"
        elif not _in_window(purchase[1], now, config):
            reason = "outside_window"
        else:
            owner, occurred_at = purchase
            consent = await read_s05_consent(
                session,
                owner_id=owner,
                approved_policy_version=config.policy_version,
                approved_counter_id=config.destination.counter_id,
                occurred_at=occurred_at,
                now=now,
            )
            if _contact_id(consent, owner, occurred_at, now, config) is None:
                reason = "no_current_consent"
        # Inherited async commit must not acknowledge this permanent fence
        # before the primary has flushed its WAL. Applies only to this transaction.
        await session.execute(text("SET LOCAL synchronous_commit = on"))
        claimed = await session.scalar(
            insert(YandexConversionExport)
            .values(
                event_id=event_id,
                status="skipped" if reason else "outcome_unknown",
                reason=reason,
                counter_id=config.destination.counter_id,
                target=config.destination.target,
                policy_version=config.policy_version,
            )
            .on_conflict_do_nothing(index_elements=[YandexConversionExport.event_id])
            .returning(YandexConversionExport.event_id)
        )
        if claimed is None:
            return _result((await session.scalars(select(YandexConversionExport).filter_by(event_id=event_id))).one())
    if reason is not None or purchase is None:
        return ExportResult("skipped", reason=reason)

    # Only the insertion winner may proceed. A crash here, during the POST, or
    # before receipt persistence leaves the durable outcome_unknown fence intact.
    try:
        async with asyncio.timeout(DISPATCH_DEADLINE_SECONDS):
            async with sessions() as session:
                receipt, denial = await _admit_and_upload(session, event_id, purchase, config, clock, mock_transport)
    except TimeoutError:
        # No later attempt may distinguish a timeout before admission from a
        # timeout after sending. Leave the committed fence untouched in both cases.
        return ExportResult("outcome_unknown")
    if denial is not None:
        return await _skip(sessions, event_id, denial)
    if receipt is None:
        return ExportResult("outcome_unknown")
    async with sessions.begin() as session:
        await session.execute(
            update(YandexConversionExport)
            .where(YandexConversionExport.event_id == event_id, YandexConversionExport.status == "outcome_unknown")
            .values(status="upload_received", upload_id=receipt.upload_id, upload_phase=receipt.phase)
        )
    return ExportResult("upload_received", upload_id=receipt.upload_id, upload_phase=receipt.phase)


async def _admit_and_upload(
    session: AsyncSession,
    event_id: UUID,
    purchase: tuple[UUID, datetime],
    config: ExportConfig,
    clock: Callable[[], datetime],
    mock_transport: httpx.MockTransport | None,
) -> tuple[UploadReceipt | None, _SKIP | None]:
    if await _proven_purchase(session, event_id) != purchase:
        return None, "unproven_purchase"
    owner, occurred_at = purchase
    now = utc_time(clock())
    if not _in_window(occurred_at, now, config):
        return None, "outside_window"
    consent = await read_s05_consent(
        session,
        owner_id=owner,
        approved_policy_version=config.policy_version,
        approved_counter_id=config.destination.counter_id,
        occurred_at=occurred_at,
        now=now,
        for_dispatch=True,
    )
    # The row lock is the dispatch/revoke ordering boundary. While we own it,
    # S05 cannot commit revocation; keep it through the bounded one-shot HTTP
    # attempt (separate from the already-committed, non-reclaimable export fence).
    now = utc_time(clock())
    if not _in_window(occurred_at, now, config):
        return None, "outside_window"
    if (client_id := _contact_id(consent, owner, occurred_at, now, config)) is None:
        return None, "no_current_consent"
    return await MetricaTransport(config.destination, mock_transport=mock_transport).upload(
        client_id, occurred_at
    ), None


async def _skip(sessions: async_sessionmaker[AsyncSession], event_id: UUID, reason: _SKIP) -> ExportResult:
    async with sessions.begin() as session:
        await session.execute(
            update(YandexConversionExport)
            .where(YandexConversionExport.event_id == event_id, YandexConversionExport.status == "outcome_unknown")
            .values(status="skipped", reason=reason)
        )
    return ExportResult("skipped", reason=reason)


_PHASES = tuple(UploadPhase)
_TERMINAL_PHASES = (UploadPhase.PROCESSED, UploadPhase.LINKAGE_FAILURE)


async def refresh_upload_status(
    event_id: UUID,
    *,
    sessions: async_sessionmaker[AsyncSession] = async_session_factory,
    mock_transport: httpx.MockTransport | None = None,
) -> ExportResult:
    """Read-only external reconciliation for a known receipt; never calls POST."""
    config = load_export_config()
    if config is None:
        return ExportResult("disabled")
    async with sessions() as session:
        row = await session.get(YandexConversionExport, event_id)
        if row is None:
            return ExportResult("not_found")
        current = _result(row)
        if (
            row.counter_id != config.destination.counter_id
            or current.upload_id is None
            or current.upload_phase in _TERMINAL_PHASES
        ):
            return current
    receipt = await MetricaTransport(config.destination, mock_transport=mock_transport).read_status(current.upload_id)
    if receipt is None or receipt.phase is None:
        return current
    async with sessions.begin() as session:
        row = await session.get(YandexConversionExport, event_id, with_for_update=True)
        if row is None:
            return ExportResult("not_found")
        latest = _result(row)
        if latest.upload_phase not in _TERMINAL_PHASES and (
            latest.upload_phase is None or _PHASES.index(receipt.phase) > _PHASES.index(latest.upload_phase)
        ):
            row.upload_phase = receipt.phase
        return _result(row)
