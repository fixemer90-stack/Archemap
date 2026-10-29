"""Scoped deterministic content composition, prompt family v3."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.child.narrative import ChildSectionRenderInput


def build_child_section_prompt_v3(section_input: ChildSectionRenderInput) -> str:
    from app.modules.child.prompts.v1 import _build_legacy_section_prompt

    return (
        "Content contract: child-section-prompt-v3.\n"
        "Approved renderings own their perspective, scale, local uncertainty and adult action.\n"
        "Shared caveats belong to how_to_use, not to every fact. Preserve every owned rendering exactly.\n"
        "Do not add boilerplate, remove dimensions, strengthen uncertain claims or invent observations.\n"
        + _build_legacy_section_prompt(section_input)
    )
