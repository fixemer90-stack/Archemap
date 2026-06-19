"""Prompt contract loader for report narratives."""

from __future__ import annotations

from pathlib import Path

from app.modules.report_narratives.schemas import NarrativeInput

SELF_STORY_PROMPT_VERSION = "self_story_v3"
_PROMPTS_DIR = Path(__file__).with_name("prompts")


def load_prompt_template(version: str) -> str:
    """Load a versioned narrative prompt template from disk."""
    prompt_path = _PROMPTS_DIR / f"{version}.md"
    return prompt_path.read_text(encoding="utf-8")


def build_self_story_prompt(narrative_input: NarrativeInput) -> str:
    """Build the concrete prompt sent to the LLM for Self reports."""
    template = load_prompt_template(SELF_STORY_PROMPT_VERSION).strip()
    serialized_input = narrative_input.model_dump_json(indent=2)
    return f"{template}\n\nNarrativeInput:\n{serialized_input}\n"
