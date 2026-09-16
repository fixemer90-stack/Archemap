from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import Settings
from app.core.exceptions import ValidationError
from app.modules.catalog.service import PRODUCT_CATALOG, CatalogService


@pytest.mark.asyncio
async def test_career_access_requires_backend_plus_or_grandfathered_entitlement() -> None:
    from app.modules.career.access import CareerAccessPolicy

    user_id = uuid4()
    entitlements = AsyncMock()
    entitlements.has_active_product_access.side_effect = [False, False]

    denied = await CareerAccessPolicy(entitlements).check(user_id)

    assert denied.allowed is False
    assert denied.reason == "missing_career_access"
    assert entitlements.has_active_product_access.await_args_list[0].kwargs == {
        "user_id": user_id,
        "product": "self",
    }
    assert entitlements.has_active_product_access.await_args_list[1].kwargs == {
        "user_id": user_id,
        "product": "career",
    }

    entitlements.reset_mock()
    entitlements.has_active_product_access.side_effect = [True]
    plus = await CareerAccessPolicy(entitlements).check(user_id)
    assert plus.allowed is True
    assert plus.source == "plus"

    entitlements.reset_mock()
    entitlements.has_active_product_access.side_effect = [False, True]
    grandfathered = await CareerAccessPolicy(entitlements).check(user_id)
    assert grandfathered.allowed is True
    assert grandfathered.source == "legacy_career"


def test_career_product_contract_is_canonical_and_legacy_sku_is_not_purchasable() -> None:
    from app.modules.career.contracts import CAREER_ACCESS_CLASS, CAREER_REPORT_TYPE, LEGACY_CAREER_SKU

    assert CAREER_REPORT_TYPE == "career"
    assert CAREER_ACCESS_CLASS == "plus_only"
    assert LEGACY_CAREER_SKU == "career_full"
    assert PRODUCT_CATALOG[LEGACY_CAREER_SKU].purchasable is False

    with pytest.raises(ValidationError, match="retired"):
        CatalogService().get_product(LEGACY_CAREER_SKU)


def test_career_access_matrix_and_migration_boundary_are_explicit() -> None:
    from app.modules.career.contracts import CAREER_ACCESS_MATRIX, LEGACY_PAYLOAD_FALLBACK_ALLOWED

    assert set(CAREER_ACCESS_MATRIX) == {
        "create",
        "questionnaire",
        "generate",
        "read",
        "regenerate",
        "versions",
        "pdf",
    }
    assert all(rule.requires_ownership for rule in CAREER_ACCESS_MATRIX.values())
    assert all(rule.requires_target_access for rule in CAREER_ACCESS_MATRIX.values())
    assert LEGACY_PAYLOAD_FALLBACK_ALLOWED is False


def test_career_rollout_flag_is_off_by_default() -> None:
    assert Settings.model_fields["CAREER_REPORT_ENABLED"].default is False
