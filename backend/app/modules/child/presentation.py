# ruff: noqa: RUF001
"""Versioned, read-only Child presentation shared by the browser and PDF."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any, cast
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.child import models
from app.modules.child.age_resolver import AgeStage
from app.modules.child.assembly import assemble_child_report_payload, assess_child_report_quality
from app.modules.child.context_resolver import _AGE_ACTIONS
from app.modules.child.guidance_facts import ChildGuidanceFacts, ChildGuidanceFactsRepository
from app.modules.child.narrative import _ACTION_TEXT, ChildNarrativeValidationError, build_child_section_inputs
from app.modules.child.prompts.v1 import SECTION_METADATA
from app.modules.child.quality import validate_guidance_facts
from app.modules.child.repository import ChildLineageMismatchError
from app.modules.child.safety import ChildSafetyViolation

PRESENTATION_CONTRACT_VERSION = "child_report_presentation_v1"
INTRODUCTION = (
    "Этот отчёт — ориентир для взрослого, а не оценка ребёнка. "
    "Проверяйте рекомендации в спокойном повседневном общении и учитывайте обстоятельства. "
    "Он не заменяет медицинскую, психологическую или педагогическую помощь."
)


def compose_child_report_presentation(
    *,
    report: models.ChildReport,
    facts: ChildGuidanceFacts,
    age_snapshot: models.ChildAgeSnapshot,
    segment_rows: Sequence[models.ChildSegmentGeneration],
    generation_status: str,
    current_local_date: date,
    artifact_generation_id: UUID | None = None,
    age_guidance: models.ChildReportAgeGuidance | None = None,
) -> dict[str, Any]:
    """Project validated persisted artifacts; never invent replacement narrative."""
    manifest = report.presentation_manifest
    if (
        manifest.get("contract_version") != PRESENTATION_CONTRACT_VERSION
        or manifest.get("section_order") != list(SECTION_METADATA)
        or manifest.get("age_snapshot_id") != str(facts.age_snapshot_id)
        or report.child_profile_id != facts.child_id
        or report.generation_id != facts.generation_id
        or report.version != facts.core_report_version
        or age_snapshot.child_profile_id != facts.child_id
    ):
        raise ChildLineageMismatchError("Child presentation lineage is unavailable")
    if age_snapshot.id != facts.age_snapshot_id and (
        age_guidance is None
        or age_guidance.report_id != report.id
        or age_guidance.child_profile_id != facts.child_id
        or age_guidance.age_snapshot_id != age_snapshot.id
        or age_guidance.status != "age_update_ready"
    ):
        raise ChildLineageMismatchError("Age guidance does not belong to the report")
    try:
        validate_guidance_facts(facts)
        terminal = [row for row in segment_rows if row.status in {"ready", "failed", "not_applicable"}]
        assembled = assemble_child_report_payload(
            guidance_facts=facts, segment_rows=terminal, artifact_generation_id=artifact_generation_id
        )
        inputs = build_child_section_inputs(facts)
    except (ChildNarrativeValidationError, ChildSafetyViolation, KeyError, TypeError, ValueError) as exc:
        raise ChildLineageMismatchError("Child presentation artifacts failed validation") from exc
    narrative = {item["section_key"]: item for item in assembled["sections"]}
    states = {row.section_key: row.status for row in terminal}
    inputs_by_key = {item.section_key: item for item in inputs}
    age_changed = age_snapshot.id != facts.age_snapshot_id
    sections = []
    for key in manifest["section_order"]:
        source = narrative.get(key)
        actions = list(dict.fromkeys(item.approved_text for item in inputs_by_key[key].owned_facts))
        state = states.get(key, "pending")
        body = source["body"] if source else None
        if body:
            actions = []
        if key == "current_age" and age_changed:
            code = _AGE_ACTIONS.get(cast(AgeStage, age_snapshot.age_stage))
            if code is None:
                raise ChildLineageMismatchError("Unsupported pinned age stage")
            actions = [f"Взрослый может {_ACTION_TEXT[code]}."]
            body = None
            state = "deterministic_ready"
        sections.append(
            {
                "key": key,
                "title": SECTION_METADATA[key][0],
                "status": state,
                "body": body,
                "actions": actions,
                "confidence_note": "Проверьте в повседневном общении; это не оценка ребёнка.",
            }
        )
    return {
        "contract_version": PRESENTATION_CONTRACT_VERSION,
        "title": "Как поддерживать контакт с ребёнком",
        "introduction": INTRODUCTION,
        "status": generation_status,
        "quality": assess_child_report_quality(
            sections=assembled["sections"],
            omitted_sections=assembled["omitted_sections"],
            failed_sections=assembled["failed_sections"],
            missing_sections=assembled["missing_sections"],
        ),
        "metadata": {
            "report_id": str(report.id),
            "child_id": str(facts.child_id),
            "generation_id": str(artifact_generation_id or facts.generation_id),
            "core_report_version": report.version,
            "age_snapshot_id": str(age_snapshot.id),
            "as_of_date": age_snapshot.as_of_date.isoformat(),
            "age_guidance_version": age_guidance.version if age_guidance is not None else None,
        },
        "sections": sections,
        "age": {
            "age_snapshot_id": str(age_snapshot.id),
            "as_of_date": age_snapshot.as_of_date.isoformat(),
            "age_years": age_snapshot.age_years,
            "age_months": age_snapshot.age_months,
            "age_days": age_snapshot.age_days,
            "age_stage": age_snapshot.age_stage,
            "stale": age_snapshot.as_of_date != current_local_date,
            "guidance_version": age_guidance.version if age_guidance is not None else None,
        },
        "technical_basis": {
            "note": "Сохранённые расчёты и наблюдения помогают проверить основания рекомендаций.",
            "confidence_markers": [dict(item) for item in facts.confidence_markers],
            **(
                {
                    "source_indicators": [
                        {
                            key: item[key]
                            for key in ("source_kind", "dimension", "score", "confidence", "scoring_version")
                        }
                        for item in facts.source_profiles
                    ]
                }
                if facts.source_profiles
                else {}
            ),
        },
    }


async def build_child_report_presentation(
    session: AsyncSession, *, owner_user_id: UUID, report_id: UUID, age_snapshot_id: UUID | None = None
) -> dict[str, Any]:
    """Build after the route's paid gate; independently require minimal owned metadata."""
    child_id = await session.scalar(
        select(models.ChildReport.child_profile_id)
        .join(models.ChildProfile, models.ChildProfile.id == models.ChildReport.child_profile_id)
        .where(
            models.ChildReport.id == report_id,
            models.ChildProfile.owner_user_id == owner_user_id,
            models.ChildProfile.status == "active",
        )
    )
    if child_id is None:
        raise ChildLineageMismatchError("Child resource not found")
    report = await session.get(models.ChildReport, report_id, populate_existing=True)
    if report is None:
        raise ChildLineageMismatchError("Child resource not found")
    exists = await session.scalar(
        select(models.ChildGuidanceFacts.id).where(
            models.ChildGuidanceFacts.generation_id == report.generation_id,
            models.ChildGuidanceFacts.child_profile_id == child_id,
            models.ChildGuidanceFacts.core_report_version == report.version,
        )
    )
    if exists is None:
        raise ChildLineageMismatchError("Published guidance is unavailable")
    facts = await ChildGuidanceFactsRepository(session).load_domain_facts(
        owner_user_id=owner_user_id,
        child_profile_id=child_id,
        generation_id=report.generation_id,
        core_report_version=report.version,
    )
    guidance_query = select(models.ChildReportAgeGuidance).where(
        models.ChildReportAgeGuidance.report_id == report_id,
        models.ChildReportAgeGuidance.child_profile_id == child_id,
        models.ChildReportAgeGuidance.status == "age_update_ready",
    )
    if age_snapshot_id is not None:
        guidance_query = guidance_query.where(models.ChildReportAgeGuidance.age_snapshot_id == age_snapshot_id)
    guidance = await session.scalar(guidance_query.order_by(models.ChildReportAgeGuidance.version.desc()).limit(1))
    selected_age_id = age_snapshot_id or (guidance.age_snapshot_id if guidance is not None else facts.age_snapshot_id)
    snapshot = await session.scalar(
        select(models.ChildAgeSnapshot).where(
            models.ChildAgeSnapshot.id == selected_age_id, models.ChildAgeSnapshot.child_profile_id == child_id
        )
    )
    if snapshot is None:
        raise ChildLineageMismatchError("Pinned age snapshot is unavailable")
    ready_assembly = await session.scalar(
        select(models.ChildReportAssembly)
        .where(
            models.ChildReportAssembly.report_id == report_id,
            models.ChildReportAssembly.status == "ready",
        )
        .order_by(models.ChildReportAssembly.created_at.desc(), models.ChildReportAssembly.id.desc())
        .limit(1)
    )
    generation_query = select(models.ChildGeneration).where(
        models.ChildGeneration.child_profile_id == child_id,
        (
            (models.ChildGeneration.generation_id == report.generation_id)
            | (models.ChildGeneration.source_report_id == report_id)
        ),
        models.ChildGeneration.operation.in_(("full_report", "narrative_retry")),
    )
    if ready_assembly is not None:
        generation_query = generation_query.where(models.ChildGeneration.generation_id == ready_assembly.generation_id)
    generation = await session.scalar(
        generation_query.order_by(models.ChildGeneration.created_at.desc(), models.ChildGeneration.id.desc()).limit(1)
    )
    if generation is None:
        raise ChildLineageMismatchError("Published generation is unavailable")
    ids = {report.generation_id, generation.generation_id}
    rows = (
        await session.scalars(
            select(models.ChildSegmentGeneration)
            .where(
                models.ChildSegmentGeneration.generation_id.in_(ids),
                models.ChildSegmentGeneration.child_profile_id == child_id,
            )
            .execution_options(populate_existing=True)
        )
    ).all()
    by_key = {row.section_key: row for row in rows if row.generation_id == report.generation_id}
    by_key.update({row.section_key: row for row in rows if row.generation_id == generation.generation_id})
    child_timezone = await session.scalar(
        select(models.ChildProfile.timezone).where(models.ChildProfile.id == child_id)
    )
    current_date = datetime.now(UTC).astimezone(ZoneInfo(child_timezone or "UTC")).date()
    return compose_child_report_presentation(
        report=report,
        facts=facts,
        age_snapshot=snapshot,
        segment_rows=tuple(by_key.values()),
        generation_status=generation.status,
        current_local_date=current_date,
        artifact_generation_id=generation.generation_id if generation.generation_id != report.generation_id else None,
        age_guidance=guidance,
    )
