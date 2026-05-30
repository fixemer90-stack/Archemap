"""API v1 router — aggregates all module routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.authorization.router import router as authorization_router
from app.modules.billing.router import router as billing_router
from app.modules.catalog.router import router as catalog_router
from app.modules.charts.router import router as charts_router
from app.modules.notifications.router import router as notifications_router
from app.modules.payments.router import router as payments_router
from app.modules.profiles.router import router as profiles_router
from app.modules.reconciliation.router import router as reconciliation_router
from app.modules.subscriptions.router import router as subscriptions_router
from app.modules.users.router import router as users_router
from app.modules.webhooks.router import router as webhooks_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(authorization_router)
api_router.include_router(catalog_router)
api_router.include_router(subscriptions_router)
api_router.include_router(billing_router)
api_router.include_router(payments_router)
api_router.include_router(webhooks_router)
api_router.include_router(reconciliation_router)
api_router.include_router(notifications_router)
api_router.include_router(admin_router)
api_router.include_router(profiles_router)
api_router.include_router(charts_router)
