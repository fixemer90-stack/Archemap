"""Content resolver — renders claims into human-readable text using evidence templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.modules.rules.types import Claim, InterpretationResult

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "rules"


def load_evidence_templates(product: str, version: str = "v1") -> dict[str, Any]:
    """Load evidence templates for a product vertical."""
    filepath = TEMPLATES_DIR / product / f"evidence_templates_{version}.yaml"
    if not filepath.exists():
        return {}

    with open(filepath, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data.get("templates", {})


def render_claim_message(claim: Claim, templates: dict[str, Any], features: dict[str, float]) -> str:
    """Render a claim's message using evidence templates."""
    # Find matching template
    template = _find_template(claim.archetype, templates)
    if not template:
        return claim.message

    # Build interpolation context
    ctx: dict[str, Any] = dict(features)
    ctx["archetype"] = claim.archetype
    ctx["score"] = claim.score
    ctx["confidence"] = claim.confidence.value

    summary = template.get("summary", claim.message)
    evidence_text = template.get("evidence_text", "")

    try:
        evidence_text = evidence_text.format(**ctx)
    except (KeyError, ValueError):
        pass

    return f"{summary} {evidence_text}".strip()


def render_full_report(result: InterpretationResult, features: dict[str, Any], product: str = "self", version: str = "v1") -> dict[str, Any]:
    """Render a full interpretation result into a structured report dict."""
    templates = load_evidence_templates(product, version)

    rendered_claims = []
    for claim in result.claims:
        rendered_claims.append({
            "claim_id": claim.claim_id,
            "section": claim.section,
            "archetype": claim.archetype,
            "score": claim.score,
            "confidence": {
                "value": claim.confidence.value,
                "label": claim.confidence.label,
                "reason_codes": claim.confidence.reason_codes,
            },
            "message": render_claim_message(claim, templates, features),
            "basis": [
                {"rule_id": b.rule_id, "feature": b.feature, "value": b.value, "contribution": b.contribution}
                for b in claim.basis
            ],
            "counter_evidence": [
                {"rule_id": c.rule_id, "feature": c.feature, "value": c.value, "contribution": c.contribution}
                for c in claim.counter_evidence
            ],
            "provenance": claim.provenance,
        })

    return {
        "product": result.product,
        "primary_archetype": result.primary_archetype,
        "primary_score": result.primary_score,
        "primary_confidence": {
            "value": result.primary_confidence.value,
            "label": result.primary_confidence.label,
            "reason_codes": result.primary_confidence.reason_codes,
        },
        "claims": rendered_claims,
        "all_archetype_scores": result.all_archetype_scores,
        "quality_warning": result.quality_warning,
        "provenance": result.provenance,
    }


def _find_template(archetype_name: str, templates: dict[str, Any]) -> dict[str, Any] | None:
    """Find template matching archetype name."""
    for _key, tmpl in templates.items():
        if tmpl.get("title") == archetype_name:
            return tmpl
    return None
