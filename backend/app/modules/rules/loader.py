"""YAML ruleset loader — parses rule YAML files into typed RuleSet."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.modules.rules.types import (
    ArchetypeRule,
    Condition,
    ConditionGroup,
    ConditionOp,
    ConfidenceAdjustment,
    EvidenceSpec,
    RuleSet,
)

RULES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "rules"


def load_ruleset(product: str, version: str = "v1") -> RuleSet:
    """Load a ruleset YAML file.

    Args:
        product: Vertical name (self, love, child, career)
        version: Version tag (v1, v2, etc.)

    Returns:
        Parsed RuleSet

    Raises:
        FileNotFoundError: If ruleset file not found
        ValueError: If YAML is invalid
    """
    filepath = RULES_DIR / product / f"archetypes_{version}.yaml"
    if not filepath.exists():
        raise FileNotFoundError(f"Ruleset not found: {filepath}")

    with open(filepath, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Empty ruleset: {filepath}")

    return _parse_ruleset(data, product)


def list_available_rulesets() -> list[dict[str, str]]:
    """List all available rulesets.

    Returns:
        List of dicts with product, version, path keys
    """
    result = []
    for product_dir in sorted(RULES_DIR.iterdir()):
        if not product_dir.is_dir():
            continue
        for rule_file in sorted(product_dir.glob("archetypes_*.yaml")):
            version = rule_file.stem.replace("archetypes_", "")
            result.append({
                "product": product_dir.name,
                "version": version,
                "path": str(rule_file),
            })
    return result


def _parse_ruleset(data: dict[str, Any], product: str) -> RuleSet:
    """Parse YAML dict into RuleSet."""
    archetypes = []
    for archetype_id, arch_data in data.get("archetypes", {}).items():
        archetypes.append(_parse_archetype(archetype_id, arch_data))

    return RuleSet(
        product=product,
        version=data.get("version", "1.0.0"),
        effective_from=data.get("effective_from", ""),
        locale=data.get("locale", "ru-RU"),
        archetypes=archetypes,
        scoring=data.get("scoring", {}),
        confidence_config=data.get("confidence", {}),
    )


def _parse_archetype(archetype_id: str, data: dict[str, Any]) -> ArchetypeRule:
    """Parse single archetype from YAML."""
    return ArchetypeRule(
        archetype_id=archetype_id,
        name=data.get("name", archetype_id),
        description=data.get("description", ""),
        conditions=_parse_condition_group(data.get("conditions", {})),
        effects=data.get("effects", {}),
        confidence_adjustments=[
            _parse_confidence_adjustment(adj)
            for adj in data.get("confidence_adjustments", [])
        ],
        counter_rules=data.get("counter_rules", []),
        evidence=_parse_evidence(data.get("evidence")),
    )


def _parse_condition_group(data: dict[str, Any]) -> ConditionGroup:
    """Parse condition group (all/any/not)."""
    if "all" in data:
        return ConditionGroup(
            conjunction="all",
            conditions=[_parse_condition(c) for c in data["all"]],
        )
    elif "any" in data:
        return ConditionGroup(
            conjunction="any",
            conditions=[_parse_condition(c) for c in data["any"]],
        )
    elif "not" in data:
        return ConditionGroup(
            conjunction="not",
            conditions=[_parse_condition(c) for c in data["not"]],
        )
    else:
        return ConditionGroup(conjunction="all", conditions=[])


def _parse_condition(data: dict[str, Any]) -> Condition:
    """Parse single condition."""
    return Condition(
        fact=data["fact"],
        op=ConditionOp(data.get("op", "gte")),
        value=data["value"],
        value_upper=data.get("value_upper"),
    )


def _parse_confidence_adjustment(data: dict[str, Any]) -> ConfidenceAdjustment:
    """Parse confidence adjustment."""
    when_data = data.get("when", {})
    return ConfidenceAdjustment(
        when=Condition(
            fact=when_data.get("fact", ""),
            op=ConditionOp(when_data.get("op", "gte")),
            value=when_data.get("value", 0),
        ),
        delta=data.get("delta", 0),
    )


def _parse_evidence(data: dict[str, Any] | None) -> EvidenceSpec | None:
    """Parse evidence specification."""
    if not data:
        return None
    return EvidenceSpec(
        template_key=data.get("template_key", ""),
        show_basis_features=data.get("show_basis_features", []),
    )
