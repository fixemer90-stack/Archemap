# ruff: noqa: RUF001
"""Child Report section prompt family v1."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from app.modules.child.narrative import ChildSectionRenderInput

SECTION_METADATA: Final[dict[str, tuple[str, str]]] = {
    "how_to_use": ("Как читать этот отчёт", "Объяснить практический и недиагностический способ использования отчёта."),
    "parent_style": ("Ваш стиль взаимодействия", "Показать сильные стороны взрослого в контакте с ребёнком."),
    "child_interaction_needs": ("Что помогает ребёнку в контакте", "Описать наблюдаемые потребности взаимодействия."),
    "natural_contact": ("Где контакт складывается естественно", "Раскрыть устойчивые совпадения во взаимодействии."),
    "friction_zones": ("Где может возникать напряжение", "Объяснить зоны трения без фиксированных ярлыков."),
    "soothing_support": ("Как поддерживать и успокаивать", "Дать ограниченные фактами способы поддержки."),
    "boundaries_rules": ("Границы и правила", "Показать возрастно уместную спокойную структуру."),
    "autonomy": ("Самостоятельность", "Объяснить поддержку автономии без давления."),
    "explanation_learning": ("Объяснения и обучение", "Описать подходящий способ объяснять и тренировать навыки."),
    "praise_recognition": ("Похвала и признание", "Предложить способы замечать усилия без оценочных ярлыков."),
    "conflict_cycle": ("Цикл конфликта", "Показать взрослому, как не усиливать повторяющееся напряжение."),
    "not_personal": ("Что важно не принимать на свой счёт", "Отделить реакцию ребёнка от оценки взрослого."),
    "parent_strengths": ("На что вы уже можете опереться", "Собрать доказанные сильные стороны взрослого."),
    "conscious_adjustments": ("Что можно настраивать осознанно", "Описать компенсации как действия взрослого."),
    "current_age": ("Что важно в текущем возрасте", "Связать рекомендации с зафиксированным возрастным этапом."),
}


def build_child_section_prompt(section_input: ChildSectionRenderInput) -> str:
    """Build one bounded prompt without raw chart, answers, or PII."""

    if section_input.contract_version == "child_section_render_input_v4":
        from app.modules.child.prompts.v4 import build_child_section_prompt_v4

        return build_child_section_prompt_v4(section_input)
    if section_input.contract_version == "child_section_render_input_v3":
        from app.modules.child.prompts.v3 import build_child_section_prompt_v3

        return build_child_section_prompt_v3(section_input)
    if section_input.contract_version == "child_section_render_input_v2":
        from app.modules.child.prompts.v2 import build_child_section_prompt_v2

        return build_child_section_prompt_v2(section_input)
    return _build_legacy_section_prompt(section_input)


def _build_legacy_section_prompt(section_input: ChildSectionRenderInput) -> str:
    payload = json.dumps(section_input.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    return f"""Write one Child Report section in Russian.
Use only the owned_facts and bounded reference_facts in the provided JSON.
The input is a minimal content projection: it contains no lineage UUIDs, raw chart, answers, birth data, or names.
Do not calculate scores, infer traits, diagnose, prescribe medicine, or write any new recommendation.
For each owned fact, copy its approved_text verbatim into exactly one claim and cite only that fact id.
Reference facts may be selected only by copying their approved_text verbatim; they cannot replace owned facts.
Set each claim's conditional value exactly as provided by its fact.
Set cited_fact_ids to the claim fact ids in the same order, without duplicates.
Set body to the exact single-space join of claim texts; no headings, bridges, additions, or uncited prose.
Return an explicit contract_version and JSON matching child_segment_output_v1, with nothing outside JSON.
If the previous attempt failed validation, correct only this section; do not recalculate deterministic inputs.

Section: {section_input.section_key} — {section_input.section_title}
Purpose: {section_input.section_purpose}

Output shape:
{{"contract_version":"child_segment_output_v1","section_key":"{section_input.section_key}",
"title":"{section_input.section_title}","body":"Russian prose",
"cited_fact_ids":["exact fact id"],
"claims":[{{"text":"sentence copied from body","fact_ids":["exact fact id"],"conditional":false}}]}}

Bounded section input:
{payload}"""
