"""Payments service — orchestrates payment creation, webhooks, and status updates."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundError, PaymentError, ValidationError
from app.modules.analytics.schemas import BusinessEventInput, EventType, Mode, Product
from app.modules.analytics.service import emit_business_event
from app.modules.authorization.models import Entitlement
from app.modules.authorization.service import AccountTierService, EntitlementsService
from app.modules.catalog.service import CatalogService
from app.modules.payments.models import Payment, PaymentWebhook, YooKassaMerchantBinding
from app.modules.payments.providers.yookassa import YooKassaProvider
from app.modules.payments.schemas import (
    BillingAccessResponse,
    BillingEntitlementSummary,
    BillingPaymentSummary,
    BillingSubscriptionSummary,
)
from app.modules.subscriptions.models import Subscription
from app.modules.subscriptions.observability import subscription_telemetry

logger = structlog.get_logger()
_PROVIDER_AMOUNT = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?")


class PaymentsService:
    """Payment orchestration across providers."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_payment(
        self,
        user_id: UUID,
        amount: float,
        provider: str = "yookassa",
        currency: str = "RUB",
        description: str = "",
        metadata: dict[str, Any] | None = None,
        return_url: str = "",
        subscription_id: UUID | None = None,
        save_payment_method: bool = False,
        provider_payment_method_id: str | None = None,
    ) -> Payment:
        """Create a payment and initiate checkout.

        1. Create Payment record in DB
        2. Call provider API to create payment
        3. Update Payment with provider_payment_id and confirmation_url
        """
        if provider != "yookassa":
            raise ValidationError(f"Unsupported payment provider: {provider}")
        yookassa = YooKassaProvider()
        commercial_facts = metadata or {}
        initial_plus = (
            subscription_id is not None
            and commercial_facts.get("plan_code") == "astrotype_plus_monthly"
            and commercial_facts.get("product_id") == "astrotype_plus_monthly"
            and commercial_facts.get("subscription_id") == str(subscription_id)
            and commercial_facts.get("billing_reason") in (None, "initial")
        )
        bind_merchant = settings.YOOKASSA_PROVENANCE_ENABLED and initial_plus
        binding_id = settings.YOOKASSA_MERCHANT_BINDING_ID if bind_merchant else None
        mode = settings.YOOKASSA_PAYMENT_MODE if bind_merchant else None
        if bind_merchant and (
            binding_id is None
            or mode is None
            or not yookassa.shop_id.strip()
            or yookassa.shop_id != yookassa.shop_id.strip()
            or len(yookassa.shop_id) > 255
            or not yookassa.secret_key.strip()
        ):
            raise PaymentError("Payment merchant provenance is not configured", code="payment_provenance_unconfigured")
        if binding_id is not None and mode is not None:
            await self._pin_merchant_binding(binding_id, mode, yookassa.shop_id)

        payment = Payment(
            user_id=user_id,
            subscription_id=subscription_id,
            provider=provider,
            merchant_binding_id=binding_id,
            payment_mode=mode,
            merchant_account_id=yookassa.shop_id if bind_merchant else None,
            amount=amount,
            currency=currency,
            description=description,
            metadata_json=metadata,
            status="pending",
        )
        self.db.add(payment)
        await self.db.flush()

        # Call provider
        result = await self._create_yookassa_payment(
            yookassa=yookassa,
            payment=payment,
            return_url=return_url,
            save_payment_method=save_payment_method,
            payment_method_id=provider_payment_method_id,
        )

        # Update payment with provider info
        payment.provider_payment_id = result.get("id")
        payment.status = self._map_provider_status(result.get("status", "pending"))
        # A create response isn't an authenticated canonical read, even when it says paid.
        if bind_merchant and payment.status == "succeeded":
            payment.status = "pending"

        # Extract confirmation URL
        confirmation = result.get("confirmation", {})
        if confirmation.get("type") == "redirect":
            payment.metadata_json = {
                **(payment.metadata_json or {}),
                "confirmation_url": confirmation.get("confirmation_url", ""),
            }

        # Extract payment method if available
        payment_method = result.get("payment_method", {})
        if payment_method:
            payment.payment_method_id = payment_method.get("id")
            payment.payment_method_type = payment_method.get("type")

        await self.db.flush()

        logger.info(
            "payment_created",
            payment_id=str(payment.id),
            provider=provider,
            amount=amount,
            provider_payment_id=payment.provider_payment_id,
        )

        return payment

    async def create_payment_for_product(
        self,
        user_id: UUID,
        product_id: str,
        provider: str = "yookassa",
        return_url: str = "",
    ) -> Payment:
        """Create checkout for a server-priced product.

        The client supplies only ``product_id``. Price, currency, description,
        and commercial metadata are owned by backend catalog.
        """
        product = CatalogService().get_product(product_id)
        return await self.create_payment(
            user_id=user_id,
            amount=product.amount,
            provider=provider,
            currency=product.currency,
            description=product.description,
            metadata={"product_id": product.product_id, "product": product.product},
            return_url=return_url,
        )

    async def get_payment(self, payment_id: UUID, user_id: UUID) -> Payment:
        """Get payment by ID."""
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id, Payment.user_id == user_id))
        payment = result.scalar_one_or_none()
        if payment is None:
            raise NotFoundError("Payment not found")
        return payment

    async def list_payments(
        self,
        user_id: UUID,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[Payment], int]:
        """List payments for a user."""
        query = select(Payment).where(Payment.user_id == user_id)
        count_query = select(func.count()).select_from(Payment).where(Payment.user_id == user_id)

        query = query.order_by(Payment.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        payments = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return payments, total

    async def get_billing_access_state(self, user_id: UUID) -> BillingAccessResponse:
        """Return backend-owned billing/access state for the user."""
        latest_payment_result = await self.db.execute(
            select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc()).limit(1)
        )
        latest_payment = latest_payment_result.scalars().all()
        payment = latest_payment[0] if latest_payment else None
        if payment is not None:
            await self.reconcile_pending_provider_payment(payment)

        entitlements_result = await self.db.execute(
            select(Entitlement).where(Entitlement.user_id == user_id).order_by(Entitlement.created_at.desc())
        )
        entitlements = list(entitlements_result.scalars().all())

        subscription_result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        subscriptions = subscription_result.scalars().all()
        subscription = subscriptions[0] if subscriptions else None

        now = datetime.now(UTC)
        active_entitlements = [
            entitlement
            for entitlement in entitlements
            if entitlement.status == "active"
            and (entitlement.starts_at is None or entitlement.starts_at <= now)
            and (entitlement.expires_at is None or entitlement.expires_at > now)
        ]

        subscription_plan_code = (
            str((subscription.metadata_json or {}).get("plan_code")) if subscription is not None else None
        )
        subscription_is_canonical_plus = subscription_plan_code == "astrotype_plus_monthly"
        subscription_active = (
            subscription is not None
            and subscription_is_canonical_plus
            and subscription.status in {"active", "cancel_scheduled"}
            and subscription.current_period_start is not None
            and subscription.current_period_end is not None
            and subscription.current_period_start <= now < subscription.current_period_end
        )
        accessible_products = {
            entitlement.product
            for entitlement in active_entitlements
            if not (getattr(entitlement, "metadata_json", None) or {}).get("subscription_id")
        }
        if subscription_active:
            accessible_products.update(CatalogService().get_subscription_plan("astrotype_plus_monthly").products)

        if subscription is not None and subscription_active:
            access_state = "cancel_scheduled" if subscription.cancel_at_period_end else "plus_active"
            account_tier = "plus"
        elif subscription and subscription_is_canonical_plus and subscription.status == "past_due":
            access_state = "past_due"
            account_tier = "free"
        elif subscription and subscription_is_canonical_plus and subscription.status == "suspended":
            access_state = "plus_suspended"
            account_tier = "free"
        elif subscription and subscription_is_canonical_plus and subscription.status in {"expired", "cancelled"}:
            access_state = "plus_expired"
            account_tier = "free"
        elif active_entitlements:
            access_state = "product_access"
            account_tier = "free"
        elif payment and payment.status in {"pending", "processing"}:
            access_state = "checkout_pending"
            account_tier = "free"
        elif payment and payment.status in {"failed", "cancelled", "refunded"}:
            access_state = "payment_failed"
            account_tier = "free"
        elif entitlements:
            access_state = "plus_inactive"
            account_tier = "free"
        else:
            access_state = "free"
            account_tier = "free"

        return BillingAccessResponse(
            account_tier=account_tier,
            access_state=access_state,
            child_enabled=settings.CHILD_REPORT_ENABLED,
            accessible_products=sorted(accessible_products),
            subscription=(
                BillingSubscriptionSummary(
                    id=str(subscription.id),
                    plan_code=subscription_plan_code or "unknown",
                    status=subscription.status,
                    current_period_start=subscription.current_period_start,
                    current_period_end=subscription.current_period_end,
                    cancel_at_period_end=subscription.cancel_at_period_end,
                    next_billing_at=(
                        subscription.current_period_end
                        if subscription_active and not subscription.cancel_at_period_end
                        else None
                    ),
                    grace_until=subscription.grace_until,
                )
                if subscription
                else None
            ),
            entitlements=[
                BillingEntitlementSummary(
                    product=entitlement.product,
                    status=entitlement.status,
                    starts_at=entitlement.starts_at,
                    expires_at=entitlement.expires_at,
                )
                for entitlement in entitlements
            ],
            latest_payment=(
                BillingPaymentSummary(
                    id=str(payment.id),
                    product_id=(payment.metadata_json or {}).get("product_id"),
                    product=(payment.metadata_json or {}).get("product"),
                    status=payment.status,
                    created_at=payment.created_at,
                    paid_at=payment.paid_at,
                )
                if payment
                else None
            ),
        )

    async def _pin_merchant_binding(self, binding_id: UUID, mode: str, account_id: str) -> None:
        binding = YooKassaMerchantBinding
        await self.db.execute(
            insert(binding)
            .values(id=binding_id, payment_mode=mode, merchant_account_id=account_id)
            .on_conflict_do_nothing(index_elements=[binding.id])
        )
        result = await self.db.execute(
            select(binding.payment_mode, binding.merchant_account_id).where(binding.id == binding_id)
        )
        row = result.one()
        if (row.payment_mode, row.merchant_account_id) != (mode, account_id):
            raise PaymentError(
                "Payment merchant binding conflicts with registered provenance", code="payment_binding_conflict"
            )

    async def reconcile_pending_provider_payment(self, payment: Payment) -> None:
        """Reconcile a pending provider payment before access state is shown.

        This is an idempotent fallback for cases where YooKassa captured the
        payment but webhook delivery did not reach the app yet. Provider truth
        still comes from YooKassa; the browser return URL is not trusted.
        """
        if payment.provider != "yookassa" or payment.status not in {"pending", "processing"}:
            return
        if not payment.provider_payment_id:
            return

        yookassa = YooKassaProvider()
        canonical_payload = await yookassa.get_payment(payment.provider_payment_id)
        event = yookassa.parse_webhook_event({"object": canonical_payload})
        if event.get("status") in ("pending", "waiting_for_capture"):
            return  # This fallback only applies final provider states.
        # Provider I/O happens before the lock. Reload even for legacy rows:
        # the identity map may still contain pending state after a webhook committed.
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment.id).with_for_update().execution_options(populate_existing=True)
        )
        locked = result.scalar_one_or_none()
        if locked is None or locked.status not in {"pending", "processing"}:
            return
        payment = locked
        if not self._event_matches_payment(payment, event, authenticated_shop_id=yookassa.shop_id):
            logger.warning(
                "pending_payment_reconciliation_mismatch",
                provider=payment.provider,
                payment_id=payment.provider_payment_id,
                local_payment_id=str(payment.id),
            )
            subscription_telemetry.record_failure("pending_payment_reconciliation_mismatch")
            return

        new_status = self._map_provider_status(event["status"])
        if new_status == "succeeded":
            await self._apply_canonical_success(payment, event)
            await self.db.flush()
        elif payment.paid_at is not None:
            return  # An older provider snapshot cannot reopen an already confirmed payment.
        elif new_status == "failed":
            payment.status = "failed"
            payment.failed_at = datetime.now(UTC)
            payment.error_code = event.get("status")
            await self._record_renewal_failure(payment, str(event.get("status") or "failed"))
            await self.db.flush()
        elif new_status == "cancelled":
            payment.status = "cancelled"
            payment.cancelled_at = datetime.now(UTC)
            await self._record_renewal_failure(payment, str(event.get("status") or "cancelled"))
            await self.db.flush()

    async def reconcile_latest_pending_provider_payment(self, user_id: UUID) -> None:
        """Reconcile the user's latest pending provider payment if one exists."""
        latest_payment_result = await self.db.execute(
            select(Payment)
            .where(Payment.user_id == user_id, Payment.status.in_(["pending", "processing"]))
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
        latest_payment = latest_payment_result.scalars().all()
        payment = latest_payment[0] if latest_payment else None
        if payment is not None:
            await self.reconcile_pending_provider_payment(payment)

    async def handle_webhook(
        self,
        provider: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle payment webhook from provider.

        1. Parse webhook event
        2. Find payment by provider_payment_id
        3. Update payment status
        4. Trigger downstream actions (subscription activation, etc.)
        """
        # Store raw webhook
        webhook = PaymentWebhook(
            provider=provider,
            event_type=payload.get("event", "unknown"),
            payment_id=payload.get("object", {}).get("id"),
            payload=payload,
        )
        self.db.add(webhook)
        await self.db.flush()

        # Parse event. YooKassa does not sign notification bodies with an
        # X-Signature HMAC. Per official docs, authenticity must be checked by
        # reconciling the current object status via API and/or sender IP.
        if provider == "yookassa":
            yookassa = YooKassaProvider()
            event = yookassa.parse_webhook_event(payload)
            requested_payment_id = event["payment_id"]
            try:
                canonical_payload = await yookassa.get_payment(requested_payment_id)
            except httpx.HTTPError as exc:
                logger.warning(
                    "webhook_provider_reconciliation_failed",
                    provider=provider,
                    payment_id=event["payment_id"],
                    error=str(exc),
                )
                subscription_telemetry.record_failure("webhook_provider_reconciliation_failed")
                webhook.processed = False
                webhook.processed_at = None
                webhook.error_message = "Provider reconciliation failed"
                await self.db.flush()
                raise
            canonical_event = yookassa.parse_webhook_event({"object": canonical_payload})
            canonical_event["event_type"] = event["event_type"]
            event = canonical_event
        else:
            raise ValidationError(f"Unsupported provider: {provider}")

        # Find payment
        payment_result = await self.db.execute(
            select(Payment)
            .where(
                Payment.provider == provider,
                Payment.provider_payment_id == requested_payment_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        payment = payment_result.scalar_one_or_none()

        if payment is None:
            logger.warning("webhook_payment_not_found", provider=provider, payment_id=event["payment_id"])
            webhook.processed = True
            webhook.error_message = "Payment not found"
            await self.db.flush()
            return {"processed": False, "message": "Payment not found"}

        if event["payment_id"] != requested_payment_id or not self._event_matches_payment(
            payment, event, authenticated_shop_id=yookassa.shop_id
        ):
            logger.warning(
                "webhook_payment_mismatch",
                provider=provider,
                payment_id=event["payment_id"],
                local_payment_id=str(payment.id),
            )
            subscription_telemetry.record_failure("webhook_payment_mismatch")
            webhook.processed = True
            webhook.processed_at = datetime.now(UTC)
            webhook.error_message = "Payment payload mismatch"
            await self.db.flush()
            return {
                "processed": False,
                "payment_id": str(payment.id),
                "status": payment.status,
                "message": "Payment payload mismatch",
            }

        # Update payment status
        old_status = payment.status
        new_status = self._map_provider_status(event["status"])
        if new_status == "succeeded":
            await self._apply_canonical_success(payment, event)
            new_status = payment.status
        elif payment.paid_at is not None:
            # Protect confirmed legacy payments as well as merchant-bound attempts.
            new_status = old_status
        else:
            payment.status = new_status
            if new_status == "failed":
                payment.failed_at = datetime.now(UTC)
                payment.error_code = event.get("status")
                await self._record_renewal_failure(payment, str(event.get("status") or "failed"))
            elif new_status == "cancelled":
                payment.cancelled_at = datetime.now(UTC)
                await self._record_renewal_failure(payment, str(event.get("status") or "cancelled"))

        # Mark webhook as processed
        webhook.processed = True
        webhook.processed_at = datetime.now(UTC)

        await self.db.flush()

        logger.info(
            "payment_status_updated",
            payment_id=str(payment.id),
            old_status=old_status,
            new_status=new_status,
        )

        return {
            "processed": True,
            "payment_id": str(payment.id),
            "status": new_status,
            "message": f"Payment status updated: {old_status} → {new_status}",
        }

    async def _apply_canonical_success(self, payment: Payment, event: dict[str, Any]) -> None:
        """Apply validated success under the lock, without repeating a recorded grant."""
        if payment.paid_at is not None:
            if payment.status in {"pending", "processing", "failed", "cancelled"} and payment.refunded_at is None:
                payment.status = "succeeded"
            return
        payment.status = "succeeded"
        payment.paid_at = datetime.now(UTC)
        payment.payment_method_id = event.get("payment_method", {}).get("id")
        payment.payment_method_type = event.get("payment_method", {}).get("type")

        subscription_id = getattr(payment, "subscription_id", None)
        metadata = payment.metadata_json or {}
        if subscription_id is not None:
            from app.modules.subscriptions.service import SubscriptionsService

            subscription_service = SubscriptionsService(self.db)
            event_id = payment.provider_payment_id or str(payment.id)
            if metadata.get("billing_reason") == "renewal":
                await subscription_service.apply_renewal_success(
                    subscription_id=subscription_id,
                    payment=payment,
                    provider_event_id=event_id,
                )
            else:
                subscription = await subscription_service.activate_initial_payment(
                    subscription_id=subscription_id,
                    payment=payment,
                    provider_event_id=event_id,
                )
                await self._emit_initial_plus_confirmation(payment, subscription)
            return
        if product := metadata.get("product"):
            product_id = metadata.get("product_id")
            await EntitlementsService(self.db).grant_paid_product(
                user_id=payment.user_id,
                product=product,
                source_payment_id=payment.id,
                metadata={"product_id": product_id} if product_id else None,
            )
        await AccountTierService(self.db).upgrade_to_plus(payment.user_id)

    async def _emit_initial_plus_confirmation(self, payment: Payment, subscription: Subscription) -> None:
        if not settings.BUSINESS_MONITORING_ENABLED or getattr(payment, "merchant_binding_id", None) is None:
            return
        # The authenticated provider match and locked first-success check have already won.
        # Match the local period as well, before any financial event can leave this transaction.
        if (
            payment.paid_at is None
            or payment.payment_mode not in ("test", "live")
            or subscription.user_id != payment.user_id
            or subscription.latest_payment_id != payment.id
            or subscription.current_period_start != payment.paid_at
        ):
            await self.db.rollback()
            raise ValidationError("Confirmed payment does not match its initial subscription period")
        for event_type in (EventType.PAYMENT_CONFIRMED, EventType.SUBSCRIPTION_PERIOD_STARTED):
            await emit_business_event(
                self.db,
                BusinessEventInput(
                    event_type=event_type,
                    entity_id=payment.id,
                    source_id=payment.merchant_binding_id if event_type is EventType.PAYMENT_CONFIRMED else None,
                    subject_id=payment.user_id,
                    mode=Mode(payment.payment_mode),
                    product=Product.PLUS,
                    occurred_at=payment.paid_at,
                ),
            )

    async def _record_renewal_failure(self, payment: Payment, reason: str) -> None:
        if (payment.metadata_json or {}).get("billing_reason") != "renewal" or payment.subscription_id is None:
            return
        from app.modules.subscriptions.service import SubscriptionsService

        await SubscriptionsService(self.db).apply_renewal_failure(
            subscription_id=payment.subscription_id,
            provider_event_id=payment.provider_payment_id or str(payment.id),
            reason=reason,
        )

    async def _create_yookassa_payment(
        self,
        yookassa: YooKassaProvider,
        payment: Payment,
        return_url: str,
        save_payment_method: bool = False,
        payment_method_id: str | None = None,
    ) -> dict[str, Any]:
        """Create payment via YooKassa API."""
        metadata = dict(payment.metadata_json or {})
        metadata["payment_id"] = str(payment.id)
        metadata["user_id"] = str(payment.user_id)

        result = await yookassa.create_payment(
            amount=payment.amount,
            currency=payment.currency,
            description=payment.description,
            metadata=metadata,
            capture=True,
            return_url=return_url,
            idempotency_key=str(payment.id),
            save_payment_method=save_payment_method,
            payment_method_id=payment_method_id,
        )

        return result

    def _map_provider_status(self, provider_status: str) -> str:
        """Map provider-specific status to our internal status."""
        status_map = {
            # YooKassa statuses
            "pending": "pending",
            "waiting_for_capture": "processing",
            "succeeded": "succeeded",
            "canceled": "cancelled",
        }
        return status_map.get(provider_status, "pending")

    def _event_matches_payment(self, payment: Payment, event: dict[str, Any], *, authenticated_shop_id: str) -> bool:
        """Match the authenticated canonical provider object, not the notification body."""
        provider_status = event.get("status")
        if not isinstance(provider_status, str):
            return False
        if event.get("payment_id") != payment.provider_payment_id:
            return False
        if event.get("currency") != payment.currency:
            return False
        wire_amount = event.get("amount")
        if not isinstance(wire_amount, str) or not _PROVIDER_AMOUNT.fullmatch(wire_amount):
            return False
        expected_amount = Decimal(str(payment.amount))
        if not expected_amount.is_finite() or expected_amount <= 0 or Decimal(wire_amount) != expected_amount:
            return False

        metadata = event.get("metadata")
        if not isinstance(metadata, dict):
            return False
        payment_metadata = payment.metadata_json or {}
        if metadata.get("payment_id") != str(payment.id):
            return False
        if metadata.get("user_id") != str(payment.user_id):
            return False
        if metadata.get("product_id") != payment_metadata.get("product_id"):
            return False
        if payment_metadata.get("product") and metadata.get("product") != payment_metadata.get("product"):
            return False

        # Null binding is historical/unproven. It retains the compatibility
        # access path but cannot supply financial-mode evidence.
        if getattr(payment, "merchant_binding_id", None) is not None and (
            not authenticated_shop_id
            or authenticated_shop_id != payment.merchant_account_id
            or event.get("recipient_account_id") != payment.merchant_account_id
            or payment.payment_mode not in ("test", "live")
            or event.get("test") is not (payment.payment_mode == "test")
            or payment.subscription_id is None
            or metadata.get("subscription_id") != str(payment.subscription_id)
            or metadata.get("subscription_id") != payment_metadata.get("subscription_id")
            or metadata.get("plan_code") != "astrotype_plus_monthly"
            or metadata.get("plan_code") != payment_metadata.get("plan_code")
            or metadata.get("product_id") != "astrotype_plus_monthly"
            or metadata.get("product") != payment_metadata.get("product")
            or metadata.get("billing_reason") != payment_metadata.get("billing_reason")
            or metadata.get("billing_reason") not in (None, "initial")
        ):
            return False
        return provider_status != "succeeded" or event.get("paid") is True
