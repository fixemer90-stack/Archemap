"""Report narrative module."""

from app.modules.report_narratives.hash import compute_input_hash
from app.modules.report_narratives.input_builder import build_narrative_input
from app.modules.report_narratives.models import ReportNarrative
from app.modules.report_narratives.prompts import (
    SELF_STORY_PROMPT_VERSION,
    build_self_story_prompt,
    load_prompt_template,
)
from app.modules.report_narratives.schemas import NarrativeInput, SelfNarrative
from app.modules.report_narratives.service import find_cached_narrative

__all__ = [
    "SELF_STORY_PROMPT_VERSION",
    "NarrativeInput",
    "ReportNarrative",
    "SelfNarrative",
    "build_narrative_input",
    "build_self_story_prompt",
    "compute_input_hash",
    "find_cached_narrative",
    "load_prompt_template",
]
