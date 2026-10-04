"""Versioned, deterministic Career path graph traversal."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.career.models import CareerPathStep, CareerRoleMatch
from app.modules.career.profile_resolver import CareerProfileResolution
from app.modules.career.role_matching import RoleMatchResult

CAREER_PATH_GRAPH_VERSION = "career-path-graph-2"


@dataclass(frozen=True)
class CareerPathNode:
    node_key: str
    transition_key: str | None
    prerequisites: tuple[str, ...] = ()


@dataclass(frozen=True)
class CareerPathResult:
    role_family_key: str
    steps: tuple[CareerPathNode, ...]
    limitations: tuple[str, ...]
    archetypal: bool
    graph_version: str = CAREER_PATH_GRAPH_VERSION


_GRAPH: dict[str, tuple[str, ...]] = {
    "architecture": ("domain_specialist", "solution_architect", "principal_architect"),
    "product": ("product_contributor", "product_owner", "product_lead"),
    "strategy": ("strategy_analyst", "strategy_partner", "strategy_lead"),
    "analytics": ("analyst", "senior_analyst", "analytics_lead"),
    "consulting": ("domain_advisor", "consultant", "practice_lead"),
    "operations": ("operations_specialist", "operations_manager", "operations_director"),
    "research": ("research_contributor", "senior_researcher", "research_lead"),
    "management": ("team_lead", "people_manager", "department_head"),
    "entrepreneurship": ("venture_experiment", "venture_builder", "founder_operator"),
    "visual_arts": ("guided_visual_practice", "independent_visual_creator", "artistic_direction"),
    "word_and_media": ("content_contributor", "independent_author_editor", "editorial_direction"),
    "performing_arts": ("ensemble_or_studio_practice", "professional_performer", "creative_production_lead"),
    "craft_and_manual_work": ("apprentice_craft_practice", "independent_craftsperson", "workshop_master"),
    "practical_technology": ("technical_apprentice", "field_technician", "technical_service_lead"),
    "care_and_service": ("service_practitioner", "senior_care_specialist", "service_practice_lead"),
    "land_and_nature": ("field_practitioner", "independent_land_specialist", "land_program_lead"),
    "sales_and_field_work": ("field_representative", "territory_specialist", "field_team_lead"),
}


def build_career_paths(
    *,
    matches: tuple[RoleMatchResult, ...] | list[RoleMatchResult],
    resolution: CareerProfileResolution,
) -> tuple[CareerPathResult, ...]:
    """Build two or three paths strictly from versioned graph nodes."""
    context = set(resolution.context_constraints)
    has_experience = any(item.startswith("experience:") for item in context)
    has_goal = any(item.startswith("goal:") or item == "change_goal:provided" for item in context)
    limitations: list[str] = []
    if not has_experience:
        limitations.append("context:current_experience_missing")
    if not has_goal:
        limitations.append("context:goal_missing")

    selected = list(matches[:3])
    preferences = set(resolution.preferences)
    if "manager" not in preferences:
        selected = [item for item in selected if item.role_family_key != "management"] or selected
    if "entrepreneur" not in preferences:
        selected = [item for item in selected if item.role_family_key != "entrepreneurship"] or selected
    selected = selected[:3]
    if len(selected) < 2:
        selected = list(matches[:2])

    results: list[CareerPathResult] = []
    for match in selected:
        nodes = _GRAPH.get(match.role_family_key)
        if nodes is None:
            continue
        steps = tuple(
            CareerPathNode(
                node_key=node,
                transition_key=None if index == 0 else f"{nodes[index - 1]}_to_{node}",
                prerequisites=(
                    () if index == 0 else (f"evidence:{match.role_family_key}", "context:validate_experience")
                ),
            )
            for index, node in enumerate(nodes)
        )
        results.append(
            CareerPathResult(
                role_family_key=match.role_family_key,
                steps=steps,
                limitations=tuple(sorted(limitations)),
                archetypal=bool(limitations),
            )
        )
    return tuple(results)


def build_career_path_rows(
    *,
    career_profile_id: UUID,
    chart_id: UUID,
    role_rows: list[CareerRoleMatch],
    paths: tuple[CareerPathResult, ...] | list[CareerPathResult],
) -> list[CareerPathStep]:
    role_ids = {row.role_family_key: row.id for row in role_rows}
    rows: list[CareerPathStep] = []
    for path in paths:
        role_id = role_ids.get(path.role_family_key)
        if role_id is None:
            continue
        for order, step in enumerate(path.steps):
            rows.append(
                CareerPathStep(
                    career_profile_id=career_profile_id,
                    role_match_id=role_id,
                    chart_id=chart_id,
                    step_order=order,
                    node_key=step.node_key,
                    transition_key=step.transition_key,
                    reference_version=path.graph_version,
                    payload={
                        "prerequisites": list(step.prerequisites),
                        "limitations": list(path.limitations),
                        "archetypal": path.archetypal,
                    },
                )
            )
    return rows
