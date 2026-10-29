# ruff: noqa: RUF001
"""Versioned quality signals, never a prose rewrite or publication length gate."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

# Known shared semantic explanations can occur inside otherwise distinct claims.
# Match their substantive core, not topic words or necessary local qualifiers.
_SHARED_EXPLANATIONS: Final = (
    "это не оценка способностей и не фиксированная черта ребенка",
    "сопоставляйте гипотезу с повседневным контактом",
    "расчет находится между полюсами шкалы и не дает оснований выбрать один способ как устойчиво подходящий",
    "оснований для направленного вывода недостаточно",
    "расчет и наблюдение не дают однозначного основания для направленного вывода",
    "это расчетная гипотеза, а не подтвержденное наблюдение",
    "выделение ресурса в расчете не доказывает успеха в семье",
    "это гипотеза для проверки, не наблюдаемый факт",
    "опору имеет смысл считать рабочей только после сопоставления с реальным контактом",
)


def _normalize(text: str) -> str:
    return " ".join(text.casefold().replace("ё", "е").split())


def repeated_content_scopes(sections: Sequence[Mapping[str, Any]]) -> set[str]:
    """Find repeated full sentences and known boilerplate cores, even within a section.

    Body and claims are alternate encodings of the same prose: scan body once,
    not both, so a valid claim never counts as its own duplicate. Local evidence
    qualifiers and legitimate overlapping topic vocabulary are not boilerplate.
    """
    occurrences: dict[str, list[str]] = {}
    for section in sections:
        key = str(section["section_key"])
        body = _normalize(str(section["body"]))
        for sentence in re.split(r"[.!?]+(?:\s|$)", body):
            if sentence.strip():
                occurrences.setdefault(f"sentence:{sentence.strip()}", []).append(key)
        for explanation in _SHARED_EXPLANATIONS:
            occurrences.setdefault(f"explanation:{explanation}", []).extend([key] * body.count(explanation))
    return {key for keys in occurrences.values() if len(keys) > 1 for key in keys}
