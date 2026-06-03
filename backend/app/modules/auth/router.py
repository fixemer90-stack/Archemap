"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.rate_limit import RateLimiter
from app.dependencies import get_current_user, get_db
from app.infrastructure.redis import get_redis_client
from app.modules.auth.oauth.service import OAuthService
from app.modules.auth.password_reset import PasswordResetService
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    CompleteProfileRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RateLimitErrorResponse,
    RegisterRequest,
    ResendVerificationRequest,
    TokenResponse,
    VerifyRequest,
)
from app.modules.auth.service import AuthService
from app.modules.auth.verification import VerificationService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Register a new user with birth data. Returns tokens and computed chart."""
    service = AuthService(db)
    result = await service.register(
        email=body.email,
        password=body.password,
        name=body.name,
        birth_date=body.birth_date,
        birth_time=body.birth_time,
        birth_time_accuracy=body.birth_time_accuracy,
        birth_place=body.birth_place,
        latitude=body.latitude,
        longitude=body.longitude,
        timezone=body.timezone,
    )
    return result


@router.post("/complete-profile", response_model=dict, status_code=status.HTTP_201_CREATED)
async def complete_oauth_profile(
    body: CompleteProfileRequest,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Complete OAuth user profile with birth data. Creates PersonProfile and computes chart."""
    service = AuthService(db)
    result = await service.complete_oauth_profile(
        user_id=current_user_id,
        name=body.name,
        birth_date=body.birth_date,
        birth_time=body.birth_time,
        birth_time_accuracy=body.birth_time_accuracy,
        birth_place=body.birth_place,
        latitude=body.latitude,
        longitude=body.longitude,
        timezone=body.timezone,
    )
    return result


@router.post("/verify", response_model=MessageResponse)
async def verify_email(
    body: VerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Verify email address using token from email."""
    service = VerificationService(db)
    await service.verify_email(token=body.token)
    return MessageResponse(message="Email verified successfully. You can now sign in.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    body: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Resend verification email."""
    from sqlalchemy import select

    from app.modules.users.models import User

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if user and not user.is_verified:
        service = VerificationService(db)
        await service.resend_verification(body.email)

    return MessageResponse(message="If an account with that email exists, a verification link has been sent.")


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={429: {"model": RateLimitErrorResponse}},
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Authenticate with email and password. Requires verified email."""
    redis = get_redis_client()
    limiter = RateLimiter(redis)
    rate_key = limiter._make_key("login", body.email)

    if not await limiter.check_rate_limit(
        rate_key,
        settings.RATE_LIMIT_LOGIN_MAX_ATTEMPTS,
        settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
    ):
        retry_after = await limiter.get_retry_after(rate_key)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Too many login attempts. Please try again later.", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    service = AuthService(db)
    try:
        tokens = await service.login(email=body.email, password=body.password)
    except Exception:
        await limiter.increment_rate_limit(rate_key, settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS)
        raise

    await limiter.reset_rate_limit(rate_key)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: TokenResponse,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get new tokens using refresh token."""
    service = AuthService(db)
    tokens = await service.refresh_tokens(body.refresh_token)
    return TokenResponse(**tokens)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    authorization: str = Header(...),
    refresh_token: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Log out by blacklisting current tokens."""
    access_token = authorization.replace("Bearer ", "")
    service = AuthService(db)
    await service.logout(access_token=access_token, refresh_token=refresh_token)
    return MessageResponse(message="Logged out successfully.")


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Request password reset. Always returns success (anti-enumeration)."""
    service = PasswordResetService(db)
    await service.request_reset(email=body.email)
    return MessageResponse(message="If an account with that email exists, a reset link has been sent.")


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Reset password using token from email."""
    service = PasswordResetService(db)
    await service.confirm_reset(token=body.token, new_password=body.new_password)
    return MessageResponse(message="Password reset successfully. You can now sign in with your new password.")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Change password for authenticated user."""
    service = AuthService(db)
    await service.change_password(
        user_id=current_user_id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return MessageResponse(message="Password changed successfully.")


# ── OAuth endpoints ─────────────────────────────────────────────────


@router.get("/oauth/yandex/start")
async def yandex_oauth_start(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Redirect user to Yandex authorization page."""
    service = OAuthService(db)
    url = await service.get_yandex_authorize_url()
    return RedirectResponse(url=url)


@router.get("/oauth/yandex/callback")
async def yandex_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Handle Yandex OAuth callback. Sets HttpOnly cookies and redirects to frontend."""
    service = OAuthService(db)
    tokens = await service.handle_yandex_callback(code=code, state=state)

    # Build redirect URL without tokens in query string (CRIT-01)
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback"

    # Add non-sensitive params
    params = []
    if tokens.get("birth_date"):
        params.append(f"birth_date={tokens['birth_date']}")
    if tokens.get("email"):
        params.append(f"email={tokens['email']}")
    if tokens.get("has_profile") is False:
        params.append("needs_profile=true")
    if params:
        redirect_url += "?" + "&".join(params)

    # Set HttpOnly cookies for tokens
    response = RedirectResponse(url=redirect_url)
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    return response


# ── Account linking endpoints ────────────────────────────────────────


@router.get("/linked-providers")
async def get_linked_providers(
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get list of linked OAuth providers for the current user."""
    service = AuthService(db)
    result = await service.get_linked_providers(current_user_id)
    return result


@router.delete("/unlink/{provider}", response_model=MessageResponse)
async def unlink_provider(
    provider: str,
    current_user_id: Annotated[UUID, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Unlink an OAuth provider from the current user.

    Validates that user has another way to log in (password or other providers).
    """
    service = AuthService(db)
    await service.unlink_provider(current_user_id, provider)
    return MessageResponse(message=f"Successfully unlinked {provider}.")
