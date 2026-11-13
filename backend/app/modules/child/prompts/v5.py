"""Thematic measures retain their uncertainty; provider citation V2 is unchanged."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.child.prompts.v4 import build_child_section_prompt_v4

if TYPE_CHECKING:
    from app.modules.child.narrative import ChildSectionRenderInput


def build_child_section_prompt_v5(section_input: ChildSectionRenderInput) -> str:
    # The provider envelope is the accepted V4 envelope; only the bounded input
    # and editorial semantics change. Historical V4 prompt bytes stay frozen.
    return build_child_section_prompt_v4(section_input).replace(
        "Content contract: child-section-prompt-v4.",
        "Content contract: child-section-prompt-v5.\n"
        "Moderate measures are not missing data or evidence of a pronounced skew. "
        "Do not infer a concrete conflict cycle or intentions from thematic measures.",
        1,
    )
