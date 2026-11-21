"""Privacy boundary for internal business events."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.modules.analytics.schemas import BusinessEventInput, EventDetails, EventType, Mode


@pytest.mark.asyncio
async def test_emitter_rejects_injected_field_before_repository() -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.analytics.service import emit_business_event

    event = BusinessEventInput.model_validate(payload()).model_copy(update={"private_note": "sentinel"})
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        await emit_business_event(AsyncSession(), event)


@pytest.mark.parametrize("clock", [False, "", datetime(2026, 1, 1)])
async def test_emit_rejects_invalid_recorded_clock(clock: datetime) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.analytics.service import emit_business_event

    async with AsyncSession() as session:
        with pytest.raises(ValueError, match="aware clock required"):
            await emit_business_event(session, BusinessEventInput.model_validate(payload()), recorded_at=clock)


def test_registration_cannot_add_a_second_identity_component() -> None:
    with pytest.raises(ValidationError, match="only the account UUID"):
        BusinessEventInput.model_validate(payload(source_id=UUID(int=2)))


def test_payment_confirmation_requires_local_merchant_binding() -> None:
    values = payload(event_type=EventType.PAYMENT_CONFIRMED, mode=Mode.LIVE)
    with pytest.raises(ValidationError, match="local merchant binding UUID"):
        BusinessEventInput.model_validate(values)
    payment = BusinessEventInput.model_validate({**values, "source_id": UUID(int=2)})
    corrected = BusinessEventInput.model_validate({**values, "source_id": UUID(int=3), "mode": Mode.TEST})
    assert payment.source_id == UUID(int=2)
    assert payment.semantic_key == corrected.semantic_key


@pytest.mark.parametrize("event_type", [event for event in EventType if event is not EventType.PAYMENT_CONFIRMED])
def test_nonpayment_events_reject_noncanonical_source(event_type: EventType) -> None:
    with pytest.raises(ValidationError, match="identity uses only"):
        BusinessEventInput.model_validate(payload(event_type=event_type, source_id=UUID(int=2)))


def test_minimal_event_has_derived_identity_and_unknown_mode() -> None:
    entity = UUID("00000000-0000-0000-0000-000000000001")
    event = BusinessEventInput(
        event_type=EventType.REGISTRATION_COMPLETED, entity_id=entity, occurred_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    assert event.mode is Mode.UNKNOWN
    assert event.product is None
    assert event.semantic_key == f"v1:registration_completed:{entity}:-"
    assert event.details.model_dump(exclude_none=True) == {}


def payload(**changes: object) -> dict[str, object]:
    return {
        "event_type": EventType.REGISTRATION_COMPLETED,
        "entity_id": UUID(int=1),
        "occurred_at": datetime(2026, 1, 1, tzinfo=UTC),
        **changes,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"event_type": "unregistered"},
        {"schema_version": True},
        {"schema_version": 1.0},
        {"entity_id": "person@example.org"},
        {"source_id": "external-provider-id"},
        {"subject_id": "person@example.org"},
        {"semantic_key": "free text"},
        {"event_id": UUID(int=2)},
        {"name": "private"},
        {"birth": {"date": "private"}},
        {"mode": "live"},
        {"product": "other"},
        {"occurred_at": datetime(2026, 1, 1)},
        {"details": {"email": "private"}},
        {"details": {"raw_exception": "secret"}},
        {"details": {"nested": {"answers": ["secret"]}}},
        {"details": {"input_tokens": 12}},
    ],
)
def test_rejects_non_registry_or_private_input(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        BusinessEventInput.model_validate(payload(**changes))


def test_nested_model_instances_are_revalidated() -> None:
    forged = EventDetails.model_construct(input_tokens=True)
    with pytest.raises(ValidationError):
        BusinessEventInput.model_validate(payload(event_type=EventType.PROVIDER_USAGE_OBSERVED, details=forged))


@pytest.mark.parametrize("value", [True, -1, 1_000_000_001, float("nan"), float("inf"), "12"])
def test_usage_counts_are_strict_finite_bounded(value: object) -> None:
    with pytest.raises(ValidationError):
        BusinessEventInput.model_validate(
            payload(event_type=EventType.PROVIDER_USAGE_OBSERVED, details={"input_tokens": value})
        )


def test_usage_has_observed_numbers_but_unknown_cost_is_not_zero() -> None:
    event = BusinessEventInput.model_validate(
        payload(
            event_type=EventType.PROVIDER_USAGE_OBSERVED,
            details={"input_tokens": 10, "output_tokens": 0, "duration_ms": 3},
            occurred_at=datetime(2026, 1, 1, 3, tzinfo=timezone(timedelta(hours=3))),
        )
    )
    assert event.occurred_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert event.occurred_at.tzinfo is UTC
    assert event.details.input_tokens == 10
    assert event.details.cost_microunits is None
    assert event.model_dump(mode="json")["schema_version"] == 1


def test_cost_requires_explicit_currency_and_provenance() -> None:
    for details in (
        {"cost_microunits": 10},
        {"cost_currency": "USD"},
        {"cost_microunits": 0, "cost_currency": "USD", "cost_basis": "guessed"},
    ):
        with pytest.raises(ValidationError):
            BusinessEventInput.model_validate(payload(event_type=EventType.PROVIDER_USAGE_OBSERVED, details=details))
    event = BusinessEventInput.model_validate_json(
        '{"event_type":"provider_usage_observed","entity_id":"00000000-0000-0000-0000-000000000001",'
        '"occurred_at":"2026-01-01T00:00:00Z","details":{"cost_microunits":10,'
        '"cost_currency":"USD","cost_basis":"observed"}}'
    )
    assert event.details.cost_microunits == 10
    assert event.details.cost_currency is not None


def test_registry_is_closed_and_full() -> None:
    assert {item.value for item in EventType} == {
        "registration_completed",
        "account_verified",
        "basic_report_ready",
        "checkout_created",
        "payment_confirmed",
        "refund_confirmed",
        "subscription_period_started",
        "renewal_confirmed",
        "renewal_canceled",
        "report_requested",
        "report_ready",
        "report_partial",
        "report_failed",
        "report_opened",
        "provider_usage_observed",
    }
