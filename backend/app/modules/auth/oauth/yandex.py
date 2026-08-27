"""Yandex ID OAuth provider."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

YANDEX_AUTHORIZE_URL = "https://oauth.yandex.ru/authorize"
YANDEX_TOKEN_URL = "https://oauth.yandex.ru/token"
YANDEX_USERINFO_URL = "https://login.yandex.ru/info"


class YandexOAuthProvider:
    """Handles Yandex OAuth 2.0 flow."""

    def get_authorize_url(self, state: str) -> str:
        """Build the Yandex authorization URL."""
        params = {
            "response_type": "code",
            "client_id": settings.YANDEX_CLIENT_ID,
            "redirect_uri": settings.YANDEX_REDIRECT_URI,
            "state": state,
            "scope": "login:info login:birthday login:email",
        }
        return f"{YANDEX_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                YANDEX_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.YANDEX_CLIENT_ID,
                    "client_secret": settings.YANDEX_CLIENT_SECRET,
                },
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user profile from Yandex."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                YANDEX_USERINFO_URL,
                headers={"Authorization": f"OAuth {access_token}"},
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
