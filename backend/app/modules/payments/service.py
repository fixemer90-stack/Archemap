"""Payments service — orchestrates payment creation, webhooks, and status updates."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.payments.models import Payment, PaymentWebhook
from app.modules.payments.providers.yookassa import YooKassaProvider

logger = structlog.get_logger()


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
    ) -> Payment:
        """Create a payment and initiate checkout.

        1. Create Payment record in DB
        2. Call provider API to create payment
        3. Update Payment with provider_payment_id and confirmation_url
        """
        # Create payment record
        payment = Payment(
            user_id=user_id,
            subscription_id=subscription_id,
            provider=provider,
            amount=amount,
            currency=currency,
            description=description,
            metadata_json=metadata,
            status="pending",
        )
        self.db.add(payment)
        await self.db.flush()

        # Call provider
        if provider == "yookassa":
            result = await self._create_yookassa_payment(
                payment=payment,
                return_url=return_url,
            )
        else:
            raise ValidationError(f"Unsupported payment provider: {provider}")

        # Update payment with provider info
        payment.provider_payment_id = result.get("id")
        payment.status = self._map_provider_status(result.get("status", "pending"))

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

    async def get_payment(self, payment_id: UUID, user_id: UUID) -> Payment:
        """Get payment by ID."""
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id, Payment.user_id == user_id)
        )
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

        # Parse event
        if provider == "yookassa":
            yookassa = YooKassaProvider()
            event = yookassa.parse_webhook_event(payload)
        else:
            raise ValidationError(f"Unsupported provider: {provider}")

        # Find payment
        payment_result = await self.db.execute(
            select(Payment).where(
                Payment.provider == provider,
                Payment.provider_payment_id == event["payment_id"],
            )
        )
        payment = payment_result.scalar_one_or_none()

        if payment is None:
            logger.warning("webhook_payment_not_found", provider=provider, payment_id=event["payment_id"])
            webhook.processed = True
            webhook.error_message = "Payment not found"
            await self.db.flush()
            return {"processed": False, "message": "Payment not found"}

        # Update payment status
        old_status = payment.status
        new_status = self._map_provider_status(event["status"])
        payment.status = new_status

        if new_status == "succeeded":
            payment.paid_at = datetime.now(UTC)
            payment.payment_method_type = event.get("payment_method", {}).get("type")
        elif new_status == "failed":
            payment.failed_at = datetime.now(UTC)
            payment.error_code = event.get("status")
        elif new_status == "cancelled":
            payment.cancelled_at = datetime.now(UTC)

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

    async def _create_yookassa_payment(
        self,
        payment: Payment,
        return_url: str,
    ) -> dict[str, Any]:
        """Create payment via YooKassa API."""
        yookassa = YooKassaProvider()

        metadata = payment.metadata_json or {}
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
