"""Report narrative module."""

from app.modules.report_narratives.exceptions import (
    NarrativeRecoveryAction,
    NarrativeValidationAggregateError,
    NarrativeValidationError,
)
from app.modules.report_narratives.fallback import build_deterministic_self_fallback
from app.modules.report_narratives.hash import compute_input_hash
from app.modules.report_narratives.human_storytelling import (
    HUMAN_STORYTELLING_CONTRACT_VERSION,
    HUMAN_TONE_GUIDE,
    validate_human_storytelling_text,
)
from app.modules.report_narratives.input_builder import build_narrative_input
from app.modules.report_narratives.models import ReportNarrative
from app.modules.report_narratives.prompts import (
    SELF_STORY_PROMPT_VERSION,
    build_self_story_prompt,
    load_prompt_template,
)
from app.modules.report_narratives.schemas import NarrativeInput, SelfNarrative
from app.modules.report_narratives.validators import (
    choose_narrative_recovery_action,
    validate_self_narrative,
)

__all__ = [
    "HUMAN_STORYTELLING_CONTRACT_VERSION",
    "HUMAN_TONE_GUIDE",
    "SELF_STORY_PROMPT_VERSION",
    "NarrativeInput",
    "NarrativeRecoveryAction",
    "NarrativeValidationAggregateError",
    "NarrativeValidationError",
    "ReportNarrative",
    "SelfNarrative",
    "build_deterministic_self_fallback",
    "build_narrative_input",
    "build_self_story_prompt",
    "choose_narrative_recovery_action",
    "compute_input_hash",
    "load_prompt_template",
    "validate_human_storytelling_text",
    "validate_self_narrative",
]
