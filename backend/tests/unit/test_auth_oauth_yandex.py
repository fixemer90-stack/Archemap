"""Tests for Yandex OAuth URL construction."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from app.modules.auth.oauth.yandex import YandexOAuthProvider


def test_yandex_authorize_url_uses_production_scope_and_redirect(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.config import settings

    monkeypatch.setattr(settings, "YANDEX_CLIENT_ID", "client-id")
    monkeypatch.setattr(
        settings,
        "YANDEX_REDIRECT_URI",
        "https://astrotype.ru/api/v1/auth/oauth/yandex/callback",
    )

    url = YandexOAuthProvider().get_authorize_url("state-token")
    params = parse_qs(urlparse(url).query)

    assert params["client_id"] == ["client-id"]
    assert params["redirect_uri"] == ["https://astrotype.ru/api/v1/auth/oauth/yandex/callback"]
    assert params["state"] == ["state-token"]
    assert params["scope"] == ["login:info login:birthday login:email"]
