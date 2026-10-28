"""Post-LLM child-safety validation for bounded Child Report sections."""

# ruff: noqa: N818, RUF001

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from app.modules.child.contracts import CHILD_SAFETY_CONTRACT
from app.modules.child.guidance_facts import LOW_CONFIDENCE_THRESHOLD, ChildGuidanceFacts
from app.modules.child.quality import (
    SectionContract,
    fact_families,
    fact_matches_section,
    section_contracts,
    validate_guidance_facts,
)


@dataclass(frozen=True, slots=True)
class NarrativeSectionCandidate:
    section_key: str
    content: str
    fact_refs: tuple[str, ...]


class ChildSafetyViolation(ValueError):
    def __init__(self, categories: tuple[str, ...]) -> None:
        self.categories = categories
        super().__init__("Child narrative failed safety validation")


_PATTERN_CATEGORIES: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    (
        "diagnosis",
        re.compile(
            r"\b(диагноз|расстройств\w*|синдром\w*|аутизм\w*|сдвг|депресси\w*|шизофрени\w*|"
            r"страдает\s+аутизм\w*)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "diagnosis",
        re.compile(r"\b(diagnos\w*|disorder|autis\w*|adhd|depress(?:ion|ive|ed))\b", re.IGNORECASE),
    ),
    ("attachment_label", re.compile(r"проблем\w*\s+с\s+привязанност", re.IGNORECASE)),
    ("attachment_label", re.compile(r"\battachment\s+(disorder|problem|issue)\b", re.IGNORECASE)),
    (
        "fatal_prediction",
        re.compile(
            r"\b((будет|станет)\s+.{0,25}(агрессив\w*|жесток\w*|опасн\w*|манипулятор\w*|"
            r"депресси\w*)|склонен\s+к\s+депресси|будет\s+страдать\s+от\s+депресси)",
            re.IGNORECASE,
        ),
    ),
    (
        "fatal_prediction",
        re.compile(
            r"\bchild\s+(will\s+(become|be)|is\s+destined\s+to\s+be)\s+"
            r"(violent|aggressive|dangerous|depressed|a\s+failure)\b|"
            r"\bchild\s+will\s+suffer\s+from\s+depression\b",
            re.IGNORECASE,
        ),
    ),
    (
        "adult_outcome_prediction",
        re.compile(r"\bвырастет\b.{0,30}\b(неудачник\w*|одинок\w*|несчастн\w*)", re.IGNORECASE),
    ),
    (
        "fatal_prediction",
        re.compile(
            r"\b(обреч[её]н\w*\s+на\s+(провал|неудач)|нет\s+шанс\w*\s+на\s+успех)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "adult_outcome_prediction",
        re.compile(r"\bchild\s+will\s+grow\s+up\s+(to\s+be\s+)?(a\s+failure|lonely|unhappy)\b", re.IGNORECASE),
    ),
    (
        "fatal_prediction",
        re.compile(
            r"\bchild\b.{0,20}\b(doomed\s+to\s+fail|has\s+no\s+chance\s+of\s+success|will\s+never\s+succeed)\b",
            re.IGNORECASE,
        ),
    ),
    ("fatal_prediction", re.compile(r"\bреб[её]нок\b.{0,20}\bникогда\s+не\s+добь[её]тся\s+успеха\b", re.IGNORECASE)),
    (
        "ability_ranking",
        re.compile(
            r"\b(плохо\s+учиться|глуп\w*|низк\w*\s+интеллект|не\s+создан\w*\s+для\s+командн\w*)\b",
            re.IGNORECASE,
        ),
    ),
    ("ability_ranking", re.compile(r"\b(child\s+is\s+stupid|low\s+intelligence|bad\s+at\s+school)\b", re.IGNORECASE)),
    (
        "fixed_personality_label",
        re.compile(
            r"\bреб[её]нок\s*(будет\s+|является\s+)?[—-]?\s*"
            r"(манипулятор\w*|упрям\w*|ленив\w*|нарцисс\w*|психопат\w*|эгоист\w*)",
            re.IGNORECASE,
        ),
    ),
    (
        "fixed_personality_label",
        re.compile(
            r"\b(your\s+)?child\s+is\s+"
            r"(lazy|manipulative|a\s+manipulator|stubborn|a\s+psychopath|a\s+narcissist)\b",
            re.IGNORECASE,
        ),
    ),
    ("child_blame", re.compile(r"реб[её]нок\s+(специально|намеренно).{0,50}(выводит|злит|провоцирует)", re.IGNORECASE)),
    (
        "child_blame",
        re.compile(r"\b(your\s+)?child\s+(deliberately|intentionally).{0,30}(provokes|angers|upsets)\b", re.IGNORECASE),
    ),
    (
        "caregiver_blame",
        re.compile(r"(вы\s+плох(?:ой|ая)\s+(?:родитель|мать|отец)|виноват\w*\s+родител\w*)", re.IGNORECASE),
    ),
    ("caregiver_blame", re.compile(r"\byou\s+are\s+a\s+bad\s+(parent|mother|father)\b", re.IGNORECASE)),
    (
        "medical_advice",
        re.compile(
            r"\b(антидепрессант\w*|нейролептик\w*|дайте\s+реб[её]нк\w*\s+лекарств|"
            r"дайте\s+реб[её]нк\w*\s+таблетк\w*|начните\s+принимать\s+лекарств)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "medical_advice",
        re.compile(
            r"\b(give|start)\s+(the\s+|your\s+)?child\s+"
            r"(antidepressants|medication|medicine|pills?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "medical_advice",
        re.compile(
            r"\badminister\s+(antidepressants|medication|medicine|pills?)\s+to\s+(the\s+|your\s+)?child\b",
            re.IGNORECASE,
        ),
    ),
    ("medical_advice", re.compile(r"\bувелич\w*\s+реб[её]нк\w*\s+доз\w*\s+лекарств\w*", re.IGNORECASE)),
    ("legal_advice", re.compile(r"\b(лишени\w*\s+родительских\s+прав|подайте\s+в\s+суд)\b", re.IGNORECASE)),
    ("legal_advice", re.compile(r"\b(file\s+a\s+lawsuit|terminate\s+parental\s+rights)\b", re.IGNORECASE)),
    (
        "unsafe_discipline",
        re.compile(
            r"\b(шл[её]пн\w*|удар\w*\s+реб[её]н|физическ\w*\s+наказан|действовать\s+ж[её]стче|"
            r"лиш\w*\s+реб[её]нк\w*\s+ед\w*|накаж\w*\s+реб[её]нк\w*\s+ремн\w*)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "unsafe_discipline",
        re.compile(
            r"\b(hit|slap|spank|strike)\s+(the|your)\s+child\b|"
            r"\bbeat\s+(the|your)\s+child\s+with\s+a\s+belt\b|"
            r"\bwithhold\s+food\s+from\s+(the|your)\s+child\b|"
            r"\bstarve\s+(the|your)\s+child\b|"
            r"\block\s+(the|your)\s+child\s+in\s+a\s+room\b",
            re.IGNORECASE,
        ),
    ),
    (
        "unsafe_discipline",
        re.compile(
            r"\bзапер\w*\s+реб[её]нк\w*\s+в\s+комнат\w*|"
            r"бить\s+реб[её]нк\w*\s+ремн\w*|"
            r"лиш\w*\s+реб[её]нк\w*\s+сн\w*|"
            r"морить\s+реб[её]нк\w*\s+голод\w*",
            re.IGNORECASE,
        ),
    ),
    (
        "direct_planet_to_child_trait",
        re.compile(
            r"\b(солнце|луна|меркурий|венера|марс|юпитер|сатурн|уран|нептун|плутон)\b"
            r".{0,25}\b(делает|означает,?\s+что|указывает,?\s+что)\b.{0,30}\bреб[её]н",
            re.IGNORECASE,
        ),
    ),
    (
        "direct_planet_to_child_trait",
        re.compile(
            r"\b(sun|moon|mercury|venus|mars|jupiter|saturn|uranus|neptune|pluto)\b"
            r".{0,25}\b(makes|means)\b.{0,30}\b(your\s+)?child\b",
            re.IGNORECASE,
        ),
    ),
    (
        "direct_planet_to_child_trait",
        re.compile(
            r"\b(your\s+)?child\b.{0,35}\b(aggressive|lazy|manipulative|stubborn)\b.{0,20}\b"
            r"(because|due\s+to)\b.{0,20}\b(sun|moon|mercury|venus|mars|jupiter|saturn|uranus|neptune|pluto)\b",
            re.IGNORECASE,
        ),
    ),
)
_ADULT_ACTION_MARKERS: Final = (
    "вы можете",
    "родитель может",
    "взрослый может",
    "попробуйте",
    "предложите",
    "предупредите",
    "объясните",
    "сохраняйте",
    "you can",
    "you may",
    "a caregiver can",
    "try ",
    "offer ",
)
_CONDITIONAL_MARKERS: Final = (
    "если ",
    "может ",
    "возможно",
    "похоже",
    "стоит проверить",
    "посмотреть, помогает ли",
    "не обязательно",
    "if ",
    "may ",
    "might ",
    "possibly",
    "see whether",
)
_UNDER_TWELVE_STAGES: Final = frozenset({"0-1", "1-3", "3-6", "6-9", "9-12"})
_AGE_UNSAFE_PATTERNS: Final = (
    re.compile(
        r"остав\w*.{0,35}(реб[её]н|пятилетн\w*|шестилетн\w*).{0,35}(одн\w*\s+дома|без\s+присмотр)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bleave\b.{0,35}(five-year-old|six-year-old|young\s+child|child).{0,35}"
        r"\b(home\s+alone|without\s+supervision)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(let|allow|tell|instruct)\b.{0,20}(five-year-old|six-year-old|young\s+child|child).{0,35}"
        r"\b(drive\s+(a\s+)?car|use\s+a\s+weapon|drink\s+alcohol|operate\s+a\s+chainsaw)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(let|allow)\b.{0,20}(your\s+)?child.{0,20}\boperate\s+a\s+chainsaw\b", re.IGNORECASE),
)
_FACT_FAMILIES: Final = (
    "strong_matches",
    "friction_points",
    "parent_strengths",
    "compensation_areas",
    "recommended_actions",
    "avoid_patterns",
)
_INTERNAL_CATEGORIES: Final = frozenset(
    {
        "missing_adult_action_framing",
        "missing_conditional_language",
        "unknown_section",
        "section_fact_ownership",
        "invalid_fact_reference",
    }
)
_SUPPORTED_SAFETY_MARKERS: Final = frozenset({"adult_action_framing", "evidence_only", "no_fixed_child_labels"})


def _fact_index(payload: Mapping[str, Any]) -> dict[str, tuple[str, Mapping[str, Any]]]:
    index: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for family in fact_families(str(payload.get("contract_version"))):
        rows = payload.get(family)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, Mapping) and isinstance(row.get("id"), str):
                index[str(row["id"])] = (family, row)
    return index


def _matches_section_topic(fact: Mapping[str, Any], *, contract: SectionContract) -> bool:
    if not contract.owned_topics and not contract.owned_dimensions:
        return True
    return fact.get("topic") in contract.owned_topics or fact.get("dimension") in contract.owned_dimensions


def validate_child_narrative(
    candidate: NarrativeSectionCandidate,
    *,
    guidance_facts: ChildGuidanceFacts,
) -> None:
    validate_guidance_facts(guidance_facts)
    payload = guidance_facts.to_payload()
    fact_index = _fact_index(payload)
    age_stage = next(
        str(metadata["age_stage"])
        for metadata in payload["evidence_registry"].values()
        if metadata.get("source_type") == "age_snapshot"
    )
    normalized = " ".join(candidate.content.lower().replace("ё", "е").split())
    categories: list[str] = []
    for category, pattern in _PATTERN_CATEGORIES:
        if pattern.search(normalized):
            categories.append(category)

    if age_stage in _UNDER_TWELVE_STAGES and any(pattern.search(normalized) for pattern in _AGE_UNSAFE_PATTERNS):
        categories.append("age_inappropriate_advice")

    contract = section_contracts(guidance_facts.contract_version).get(candidate.section_key)
    referenced: list[tuple[str, Mapping[str, Any]]] = []
    if contract is None:
        categories.append("unknown_section")
    elif (
        contract.required_safety_markers != _SUPPORTED_SAFETY_MARKERS
        or contract.low_confidence_behavior != "conditional"
    ):
        raise RuntimeError(f"Unsupported section safety contract: {candidate.section_key}")

    for reference in candidate.fact_refs:
        if not isinstance(reference, str):
            categories.append("invalid_fact_reference")
            continue
        resolved = fact_index.get(reference)
        if resolved is None:
            categories.append("unsupported_recommendation")
            continue
        referenced.append(resolved)
        if contract is not None and (
            resolved[0] in contract.forbidden_fact_families
            or resolved[0] not in (contract.owned_fact_families | contract.reference_fact_families)
            or (
                resolved[0] in contract.owned_fact_families
                and not fact_matches_section(
                    resolved[1],
                    section_key=candidate.section_key,
                    version=guidance_facts.contract_version,
                    contract=contract,
                    family=resolved[0],
                )
            )
        ):
            categories.append("section_fact_ownership")
    if contract is not None and not any(
        family in contract.owned_fact_families
        and fact_matches_section(
            fact,
            section_key=candidate.section_key,
            version=guidance_facts.contract_version,
            contract=contract,
            family=family,
        )
        for family, fact in referenced
    ):
        categories.append("section_fact_ownership")

    evidence_refs = {str(evidence_ref) for _, fact in referenced for evidence_ref in fact.get("evidence_refs", ())}
    if contract is not None and len(evidence_refs) < contract.minimum_evidence:
        categories.append("unsupported_recommendation")

    if not any(marker in normalized for marker in _ADULT_ACTION_MARKERS):
        categories.append("missing_adult_action_framing")
    referenced_confidences = [
        float(fact["confidence"]) for _, fact in referenced if isinstance(fact.get("confidence"), int | float)
    ]
    if (
        referenced_confidences
        and min(referenced_confidences) < LOW_CONFIDENCE_THRESHOLD
        and not any(marker in normalized for marker in _CONDITIONAL_MARKERS)
    ):
        categories.append("missing_conditional_language")

    allowed_categories = CHILD_SAFETY_CONTRACT.forbidden_claim_categories | _INTERNAL_CATEGORIES
    unsupported_categories = set(categories) - allowed_categories
    if unsupported_categories:
        raise RuntimeError(f"Safety validator emitted unknown categories: {sorted(unsupported_categories)}")
    if categories:
        raise ChildSafetyViolation(tuple(dict.fromkeys(categories)))
