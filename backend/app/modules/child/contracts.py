"""Stable product, access, privacy, and safety contracts for Child Report."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from app.modules.catalog.service import CatalogService

_CHILD_REPORT = CatalogService().get_report("child")
CHILD_REPORT_TYPE = _CHILD_REPORT.report_type
CHILD_ACCESS_CLASS = _CHILD_REPORT.access_class.value
CHILD_ENTITLEMENT_PRODUCT = _CHILD_REPORT.entitlement_product or CHILD_REPORT_TYPE
LEGACY_PAYLOAD_FALLBACK_ALLOWED = False


@dataclass(frozen=True)
class ChildAccessRule:
    """Required gates for one protected Child Report operation."""

    requires_ownership: bool = True
    requires_target_access: bool = True
    requires_existing_resource: bool = True


CHILD_ACCESS_MATRIX: dict[str, ChildAccessRule] = {
    "child_create": ChildAccessRule(requires_existing_resource=False),
    "child_read": ChildAccessRule(),
    "child_update": ChildAccessRule(),
    "child_delete": ChildAccessRule(),
    "questionnaire": ChildAccessRule(),
    "report_create": ChildAccessRule(),
    "generation_status": ChildAccessRule(),
    "report_read": ChildAccessRule(),
    "report_regenerate": ChildAccessRule(),
    "report_versions": ChildAccessRule(),
    "age_update": ChildAccessRule(),
    "age_snapshots": ChildAccessRule(),
    "pdf": ChildAccessRule(),
}

_ChildHandler = TypeVar("_ChildHandler", bound=Callable[..., Any])


def child_access_operation(operation: str) -> Callable[[_ChildHandler], _ChildHandler]:
    """Attach the canonical Child access operation contract to a route handler."""

    if operation not in CHILD_ACCESS_MATRIX:
        raise ValueError(f"Unknown Child access operation: {operation}")

    def decorate(handler: _ChildHandler) -> _ChildHandler:
        handler.__dict__["child_access_operation"] = operation
        return handler

    return decorate


CHILD_LOCKED_RESPONSE_FIELDS = frozenset(
    {
        "access_state",
        "report_type",
        "required_level",
        "reason",
        "upgrade_url",
    }
)

CHILD_PROTECTED_FIELDS = frozenset(
    {
        "display_name",
        "birth_date",
        "birth_time",
        "birth_place",
        "caregiver_context",
        "answers",
        "scores",
        "evidence",
        "guidance_facts",
        "narrative",
        "age_snapshot",
        "artifact_url",
    }
)


@dataclass(frozen=True)
class ChildForeignResourceContract:
    """Response boundary that does not reveal whether a foreign resource exists."""

    status_code: int
    detail: str
    conceals_existence: bool
    loads_protected_payload: bool


CHILD_FOREIGN_RESOURCE_CONTRACT = ChildForeignResourceContract(
    status_code=404,
    detail="Child resource not found",
    conceals_existence=True,
    loads_protected_payload=False,
)


@dataclass(frozen=True)
class ChildDeletionContract:
    """Fail-closed deletion boundary for a minor's data."""

    allowed_cascade_roots: frozenset[str]
    forbidden_cascade_targets: frozenset[str]
    requires_export_support: bool
    requires_provider_payload_purge: bool
    archive_state: str
    hard_delete_strategy: str
    retention_policy: str
    deletion_order: tuple[str, ...]
    audit_event_fields: frozenset[str]
    audit_event_forbidden_fields: frozenset[str]


CHILD_DELETION_CONTRACT = ChildDeletionContract(
    allowed_cascade_roots=frozenset({"child_profile"}),
    forbidden_cascade_targets=frozenset(
        {
            "user",
            "parent_profile",
            "billing",
            "entitlement",
            "other_child_profile",
        }
    ),
    requires_export_support=True,
    requires_provider_payload_purge=True,
    archive_state="archived",
    hard_delete_strategy="purge_child_domain",
    retention_policy="retain_until_owner_hard_delete",
    deletion_order=(
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
    ),
    audit_event_fields=frozenset(
        {
            "event_type",
            "owner_user_id",
            "child_profile_id",
            "occurred_at",
            "result",
        }
    ),
    audit_event_forbidden_fields=frozenset(
        {
            "display_name",
            "birth_date",
            "birth_time",
            "birth_place",
            "caregiver_context",
            "answers",
            "scores",
            "guidance_facts",
            "narrative",
        }
    ),
)


@dataclass(frozen=True)
class ChildSafetyContract:
    """Non-negotiable content restrictions for reports about minors."""

    forbidden_claim_categories: frozenset[str]
    requires_adult_action_framing: bool
    requires_conditional_language_for_low_confidence: bool


CHILD_SAFETY_CONTRACT = ChildSafetyContract(
    forbidden_claim_categories=frozenset(
        {
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
        }
    ),
    requires_adult_action_framing=True,
    requires_conditional_language_for_low_confidence=True,
)


@dataclass(frozen=True)
class ChildExportContract:
    """Owner-authorized export boundary for a complete child-domain archive."""

    requires_owner_authorization: bool
    includes_archived_records: bool
    includes_protected_personal_data: bool
    requires_encrypted_delivery: bool
    excludes_provider_credentials: bool
    included_records: frozenset[str]
    included_artifacts: frozenset[str]


CHILD_EXPORT_CONTRACT = ChildExportContract(
    requires_owner_authorization=True,
    includes_archived_records=True,
    includes_protected_personal_data=True,
    requires_encrypted_delivery=True,
    excludes_provider_credentials=True,
    included_records=frozenset(
        {
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
    ),
    included_artifacts=frozenset({"pdf_artifacts"}),
)


@dataclass(frozen=True)
class ChildRolloutContract:
    """Non-destructive feature-flag rollback semantics."""

    feature_flag: str
    new_writes_allowed_when_disabled: bool
    existing_reads_allowed_when_disabled: bool
    existing_artifacts_preserved: bool
    destructive_rollback_allowed: bool


CHILD_ROLLOUT_CONTRACT = ChildRolloutContract(
    feature_flag="CHILD_REPORT_ENABLED",
    new_writes_allowed_when_disabled=False,
    existing_reads_allowed_when_disabled=True,
    existing_artifacts_preserved=True,
    destructive_rollback_allowed=False,
)
