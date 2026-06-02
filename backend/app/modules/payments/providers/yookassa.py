"""YooKassa payment provider adapter."""

from __future__ import annotations

import hashlib
import hmac
from base64 import b64encode
from typing import Any
from uuid import uuid4

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

YOOKASSA_API_URL = "https://api.yookassa.ru/v3"


class YooKassaProvider:
    """YooKassa payment provider implementation.

    Docs: https://yookassa.ru/developers/api
    """

    def __init__(self) -> None:
        self.shop_id = settings.YOOKASSA_SHOP_ID
        self.secret_key = settings.YOOKASSA_SECRET_KEY
        self.webhook_secret = settings.YOOKASSA_WEBHOOK_SECRET

    def _get_auth_header(self) -> str:
        """Get Basic auth header for YooKassa API."""
        credentials = f"{self.shop_id}:{self.secret_key}"
        return b64encode(credentials.encode()).decode()

    async def create_payment(
        self,
        amount: float,
        currency: str = "RUB",
        description: str = "",
        metadata: dict[str, Any] | None = None,
        capture: bool = True,
        return_url: str = "",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a payment in YooKassa.

        Args:
            amount: Payment amount in major currency units (e.g., 100.00 for 100 rubles)
            currency: Currency code (default RUB)
            description: Payment description
            metadata: Custom metadata (max 16 keys, values up to 512 chars)
            capture: Auto-capture payment (default True)
            return_url: URL to redirect after payment
            idempotency_key: Idempotency key for safe retries

        Returns:
            YooKassa payment object
        """
        if not idempotency_key:
            idempotency_key = str(uuid4())

        body: dict[str, Any] = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": currency,
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or f"{settings.FRONTEND_URL}/dashboard",
            },
            "capture": capture,
            "description": description,
        }

        if metadata:
            body["metadata"] = metadata

        headers = {
            "Authorization": f"Basic {self._get_auth_header()}",
            "Content-Type": "application/json",
            "Idempotence-Key": idempotency_key,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{YOOKASSA_API_URL}/payments",
                json=body,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()

        logger.info(
            "yookassa_payment_created",
            payment_id=result.get("id"),
            status=result.get("status"),
            amount=amount,
        )

        return result

    async def get_payment(self, payment_id: str) -> dict[str, Any]:
        """Get payment status from YooKassa.

        Args:
            payment_id: YooKassa payment ID

        Returns:
            YooKassa payment object
        """
        headers = {
            "Authorization": f"Basic {self._get_auth_header()}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{YOOKASSA_API_URL}/payments/{payment_id}",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()

        return result

    async def capture_payment(
        self,
        payment_id: str,
        amount: float | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Capture a previously created payment.

        Args:
            payment_id: YooKassa payment ID
            amount: Amount to capture (if partial)
            idempotency_key: Idempotency key

        Returns:
            YooKassa payment object
        """
        if not idempotency_key:
            idempotency_key = str(uuid4())

        body: dict[str, Any] = {}
        if amount is not None:
            body["amount"] = {
                "value": f"{amount:.2f}",
                "currency": "RUB",
            }

        headers = {
            "Authorization": f"Basic {self._get_auth_header()}",
            "Content-Type": "application/json",
            "Idempotence-Key": idempotency_key,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{YOOKASSA_API_URL}/payments/{payment_id}/capture",
                json=body,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()

        logger.info("yookassa_payment_captured", payment_id=payment_id)
        return result

    async def cancel_payment(
        self,
        payment_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Cancel a payment.

        Args:
            payment_id: YooKassa payment ID
            idempotency_key: Idempotency key

        Returns:
            YooKassa payment object
        """
        if not idempotency_key:
            idempotency_key = str(uuid4())

        headers = {
            "Authorization": f"Basic {self._get_auth_header()}",
            "Content-Type": "application/json",
            "Idempotence-Key": idempotency_key,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{YOOKASSA_API_URL}/payments/{payment_id}/cancel",
                json={},
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()

        logger.info("yookassa_payment_cancelled", payment_id=payment_id)
        return result

    def verify_webhook(self, body: bytes, signature: str) -> bool:
        """Verify webhook signature from YooKassa.

        Args:
            body: Raw request body
            signature: Signature from X-Signature header

        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("yookassa_webhook_secret_not_set")
            return False

        expected = hmac.new(
            self.webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_webhook_event(self, body: dict[str, Any]) -> dict[str, Any]:
        """Parse webhook event from YooKassa.

        Args:
            body: Webhook request body

        Returns:
            Parsed event with event_type, payment_id, status, amount
        """
        event_type = body.get("event", "")
        payment = body.get("object", {})

        return {
            "event_type": event_type,
            "payment_id": payment.get("id", ""),
            "status": payment.get("status", ""),
            "amount": float(payment.get("amount", {}).get("value", "0")),
            "currency": payment.get("amount", {}).get("currency", "RUB"),
            "metadata": payment.get("metadata", {}),
            "payment_method": payment.get("payment_method", {}),
            "created_at": payment.get("created_at", ""),
            "captured_at": payment.get("captured_at"),
            "paid": payment.get("paid", False),
        }
