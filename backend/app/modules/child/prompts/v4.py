"""Provider claims only; canonical citations are derived after application validation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.child.narrative import ChildSectionRenderInput


def build_child_section_prompt_v4(section_input: ChildSectionRenderInput) -> str:
    payload = json.dumps(section_input.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    return f"""Content contract: child-section-prompt-v4.
Write one Child Report section in Russian using only the owned_facts and bounded reference_facts.
The content projection contains no lineage UUIDs, raw chart, answers, birth data, or names.
Do not calculate scores, infer traits, diagnose, prescribe medicine, or write any new recommendation.
For each owned fact, copy its whole approved_text verbatim into exactly one claim with only that fact id.
An approved_text may contain multiple sentences. Do not split it into sentence claims or fragments.
Do not repeat any fact id, even with the whole approved_text repeated.
Reference facts may be selected only with their whole approved_text; they cannot replace owned facts.
Set each claim's conditional value exactly as provided by its fact.
Do not supply cited_fact_ids: the application derives citations only after validating all claims.
Set body to the exact single-space join of claim texts; no headings, bridges, additions, or uncited prose.
Approved renderings own their perspective, scale, local uncertainty and adult action.
Shared caveats belong to how_to_use, not every fact. Do not strengthen claims or invent observations.
If an attempt failed, correct only this section; do not recalculate deterministic inputs.
Return JSON matching child_segment_output_v2, with nothing outside JSON.
Section: {section_input.section_key} — {section_input.section_title}
Purpose: {section_input.section_purpose}
Output shape:
{{"contract_version":"child_segment_output_v2","section_key":"{section_input.section_key}",
"title":"{section_input.section_title}","body":"whole approved_text copied verbatim",
"claims":[{{"text":"whole approved_text copied verbatim (may contain multiple sentences)",
"fact_ids":["exact fact id"],"conditional":false}}]}}
Bounded section input:
{payload}"""
