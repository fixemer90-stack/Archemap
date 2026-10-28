"""Reviewed deterministic content renderings, prompt family v2."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.child.narrative import ChildSectionRenderInput


def build_child_section_prompt_v2(section_input: ChildSectionRenderInput) -> str:
    from app.modules.child.prompts.v1 import _build_legacy_section_prompt

    return (
        "Content contract: child-section-prompt-v2.\n"
        "The approved renderings preserve source perspective, topic, dimension and uncertainty.\n"
        "They are reviewed deterministic paragraphs, not terse action labels. Preserve all their semantics.\n"
        "Calculated parent-style and possible child-needs indicators are hypotheses for the caregiver to check, "
        "never fixed child traits or established observations.\n" + _build_legacy_section_prompt(section_input)
    )
