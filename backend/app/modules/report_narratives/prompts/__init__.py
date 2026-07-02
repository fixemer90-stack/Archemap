"""Prompt contract loader for report narratives."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from app.modules.report_narratives.schemas import DeepNatalSynthesis

StageName = Literal["plan", "identity", "emotional", "relationships", "development", "house_scenarios", "assembly"]

SELF_STORY_PROMPT_VERSION = "self_story_v5"
STAGED_SELF_PROMPT_VERSIONS: dict[StageName, str] = {
    "plan": "self_plan_v2",
    "identity": "self_section_identity_v2",
    "emotional": "self_section_emotional_v2",
    "relationships": "self_section_relationships_v2",
    "development": "self_section_development_v2",
    "house_scenarios": "self_section_house_scenarios_v2",
    "assembly": "self_assemble_v2",
}
_PROMPTS_DIR = Path(__file__).parent


_STAGE_SLICE_KEYS: dict[StageName, list[str]] = {
    "plan": [
        "contract_version",
        "source_chart_snapshot_id",
        "evidence_map",
        "ranked_aspects",
        "aspect_patterns",
        "house_axis_patterns",
        "planet_roles",
        "chart_dynamics",
        "contradictions",
        "maturity_levels",
        "calibration_hypotheses",
    ],
    "identity": ["planet_roles", "house_axis_patterns", "chart_dynamics"],
    "emotional": ["chart_dynamics", "contradictions", "maturity_levels", "calibration_hypotheses"],
    "relationships": ["aspect_patterns", "chart_dynamics", "contradictions"],
    "development": ["chart_dynamics", "contradictions", "maturity_levels", "calibration_hypotheses"],
    "house_scenarios": ["house_axis_patterns", "planet_roles"],
    "assembly": [],
}


def load_prompt_template(version: str) -> str:
    """Load a versioned narrative prompt template from disk."""
    prompt_path = _PROMPTS_DIR / f"{version}.md"
    return prompt_path.read_text(encoding="utf-8")


def _slice_synthesis(stage: StageName, synthesis: DeepNatalSynthesis) -> dict[str, Any]:
    payload = synthesis.model_dump(mode="json")
    keys = _STAGE_SLICE_KEYS[stage]
    return {key: payload[key] for key in keys}


def build_stage_prompt(
    stage: StageName,
    *,
    synthesis: DeepNatalSynthesis,
    stage_outputs: dict[str, Any] | None = None,
) -> str:
    template = load_prompt_template(STAGED_SELF_PROMPT_VERSIONS[stage]).strip()
    if stage == "assembly":
        payload = {"stage_outputs": stage_outputs or {}}
        label = "stage_outputs"
    elif stage == "plan":
        payload = {"DeepNatalSynthesis": synthesis.model_dump(mode="json")}
        label = "DeepNatalSynthesis"
    else:
        payload = _slice_synthesis(stage, synthesis)
        label = "stage_input"
    import json

    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"{template}\n\n{label}:\n{serialized}\n"


def build_self_story_prompt(narrative_input: Any) -> str:
    """Build the legacy concrete prompt sent to the LLM for Self reports."""
    template = load_prompt_template(SELF_STORY_PROMPT_VERSION).strip()
    serialized_input = narrative_input.model_dump_json(indent=2)
    return f"{template}\n\nNarrativeInput:\n{serialized_input}\n"
