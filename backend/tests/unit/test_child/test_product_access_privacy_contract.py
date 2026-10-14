from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import Settings
from app.modules.catalog.service import CatalogService


@pytest.mark.asyncio
async def test_child_access_requires_backend_plus_or_direct_child_grant() -> None:
    from app.modules.child.access import ChildAccessPolicy

    user_id = uuid4()
    entitlements = AsyncMock()
    entitlements.has_active_plus_access.return_value = False
    entitlements.has_active_direct_product_access.return_value = False

    denied = await ChildAccessPolicy(entitlements).check(user_id)

    assert denied.allowed is False
    assert denied.reason == "missing_child_access"
    entitlements.has_active_plus_access.assert_awaited_once_with(user_id=user_id)
    entitlements.has_active_direct_product_access.assert_awaited_once_with(
        user_id=user_id,
        product="child",
    )

    entitlements.reset_mock()
    entitlements.has_active_plus_access.return_value = True
    plus = await ChildAccessPolicy(entitlements).check(user_id)
    assert plus.allowed is True
    assert plus.source == "plus"
    entitlements.has_active_direct_product_access.assert_not_awaited()

    entitlements.reset_mock()
    entitlements.has_active_plus_access.return_value = False
    entitlements.has_active_direct_product_access.return_value = True
    grandfathered = await ChildAccessPolicy(entitlements).check(user_id)
    assert grandfathered.allowed is True
    assert grandfathered.source == "grandfathered_child"


def test_child_product_contract_is_canonical_plus_only_and_disabled_by_default() -> None:
    from app.modules.child.contracts import (
        CHILD_ACCESS_CLASS,
        CHILD_ENTITLEMENT_PRODUCT,
        CHILD_REPORT_TYPE,
        LEGACY_PAYLOAD_FALLBACK_ALLOWED,
    )

    report = CatalogService().get_report(CHILD_REPORT_TYPE)

    assert CHILD_REPORT_TYPE == report.report_type == "child"
    assert CHILD_ACCESS_CLASS == report.access_class.value == "plus_only"
    assert CHILD_ENTITLEMENT_PRODUCT == report.entitlement_product == "child"
    assert report.enabled is False
    assert LEGACY_PAYLOAD_FALLBACK_ALLOWED is False
    assert Settings.model_fields["CHILD_REPORT_ENABLED"].default is False


def test_child_access_matrix_covers_every_planned_protected_operation() -> None:
    from app.modules.child.contracts import CHILD_ACCESS_MATRIX

    assert set(CHILD_ACCESS_MATRIX) == {
        "child_create",
        "child_read",
        "child_update",
        "child_delete",
        "questionnaire",
        "report_create",
        "generation_status",
        "report_read",
        "report_regenerate",
        "report_versions",
        "age_update",
        "age_snapshots",
        "pdf",
    }
    assert all(rule.requires_ownership for rule in CHILD_ACCESS_MATRIX.values())
    assert all(rule.requires_target_access for rule in CHILD_ACCESS_MATRIX.values())
    assert CHILD_ACCESS_MATRIX["child_create"].requires_existing_resource is False
    assert CHILD_ACCESS_MATRIX["report_create"].requires_existing_resource is True


def test_locked_child_contract_exposes_only_safe_metadata() -> None:
    from app.modules.child.contracts import (
        CHILD_FOREIGN_RESOURCE_CONTRACT,
        CHILD_LOCKED_RESPONSE_FIELDS,
        CHILD_PROTECTED_FIELDS,
    )

    assert {
        "access_state",
        "report_type",
        "required_level",
        "reason",
        "upgrade_url",
    } == CHILD_LOCKED_RESPONSE_FIELDS
    assert CHILD_LOCKED_RESPONSE_FIELDS.isdisjoint(CHILD_PROTECTED_FIELDS)
    assert {
        "display_name",
        "birth_date",
        "birth_time",
        "birth_place",
        "answers",
        "scores",
        "guidance_facts",
        "narrative",
        "artifact_url",
    } <= CHILD_PROTECTED_FIELDS
    assert CHILD_FOREIGN_RESOURCE_CONTRACT.status_code == 404
    assert CHILD_FOREIGN_RESOURCE_CONTRACT.detail == "Child resource not found"
    assert CHILD_FOREIGN_RESOURCE_CONTRACT.conceals_existence is True
    assert CHILD_FOREIGN_RESOURCE_CONTRACT.loads_protected_payload is False


def test_child_deletion_and_safety_contracts_fail_closed() -> None:
    from app.modules.child.contracts import CHILD_DELETION_CONTRACT, CHILD_SAFETY_CONTRACT

    assert CHILD_DELETION_CONTRACT.allowed_cascade_roots == {"child_profile"}
    assert CHILD_DELETION_CONTRACT.forbidden_cascade_targets == {
        "user",
        "parent_profile",
        "billing",
        "entitlement",
        "other_child_profile",
    }
    assert CHILD_DELETION_CONTRACT.requires_export_support is True
    assert CHILD_DELETION_CONTRACT.requires_provider_payload_purge is True
    assert CHILD_DELETION_CONTRACT.archive_state == "archived"
    assert CHILD_DELETION_CONTRACT.hard_delete_strategy == "purge_child_domain"
    assert CHILD_DELETION_CONTRACT.retention_policy == "retain_until_owner_hard_delete"
    assert CHILD_DELETION_CONTRACT.deletion_order == (
        "provider_payloads",
        "pdf_artifacts",
        "child_report_age_guidance",
        "child_reports",
        "child_segment_generations",
        "guidance_facts",
        "context_resolutions",
        "questionnaire_answers",
        "questionnaire_sessions",
        "interaction_scores",
        "synastry_evidence",
        "child_need_scores",
        "parent_style_scores",
        "age_snapshots",
        "child_chart_versions",
        "child_profile",
    )
    assert CHILD_DELETION_CONTRACT.audit_event_fields == {
        "event_type",
        "owner_user_id",
        "child_profile_id",
        "occurred_at",
        "result",
    }
    assert CHILD_DELETION_CONTRACT.audit_event_forbidden_fields >= {
        "display_name",
        "birth_date",
        "birth_time",
        "birth_place",
        "answers",
        "narrative",
    }

    assert {
        "diagnosis",
        "attachment_label",
        "fatal_prediction",
        "adult_outcome_prediction",
        "ability_ranking",
        "fixed_personality_label",
        "child_blame",
        "caregiver_blame",
        "medical_advice",
        "legal_advice",
        "unsafe_discipline",
        "age_inappropriate_advice",
        "unsupported_recommendation",
        "direct_planet_to_child_trait",
    } <= CHILD_SAFETY_CONTRACT.forbidden_claim_categories
    assert CHILD_SAFETY_CONTRACT.requires_adult_action_framing is True
    assert CHILD_SAFETY_CONTRACT.requires_conditional_language_for_low_confidence is True


def test_child_export_contract_is_owner_authorized_complete_and_privacy_safe() -> None:
    from app.modules.child.contracts import CHILD_EXPORT_CONTRACT

    assert CHILD_EXPORT_CONTRACT.requires_owner_authorization is True
    assert CHILD_EXPORT_CONTRACT.includes_archived_records is True
    assert CHILD_EXPORT_CONTRACT.includes_protected_personal_data is True
    assert CHILD_EXPORT_CONTRACT.requires_encrypted_delivery is True
    assert CHILD_EXPORT_CONTRACT.excludes_provider_credentials is True
    assert CHILD_EXPORT_CONTRACT.included_records == {
        "child_profiles",
        "child_chart_versions",
        "child_age_snapshots",
        "child_parent_style_scores",
        "child_need_scores",
        "child_synastry_evidence",
        "child_interaction_scores",
        "child_questionnaire_sessions",
        "child_answers",
        "child_context_resolutions",
        "child_guidance_facts",
        "child_segment_generations",
        "child_reports",
        "child_report_age_guidance",
    }
    assert CHILD_EXPORT_CONTRACT.included_artifacts == {"pdf_artifacts"}


def test_child_rollout_contract_disables_writes_without_deleting_artifacts() -> None:
    from app.modules.child.contracts import CHILD_ROLLOUT_CONTRACT

    assert CHILD_ROLLOUT_CONTRACT.feature_flag == "CHILD_REPORT_ENABLED"
    assert CHILD_ROLLOUT_CONTRACT.new_writes_allowed_when_disabled is False
    assert CHILD_ROLLOUT_CONTRACT.existing_reads_allowed_when_disabled is True
    assert CHILD_ROLLOUT_CONTRACT.existing_artifacts_preserved is True
    assert CHILD_ROLLOUT_CONTRACT.destructive_rollback_allowed is False
