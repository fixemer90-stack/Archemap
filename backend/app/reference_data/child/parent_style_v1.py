"""Versioned Parent Style factor catalog and scale semantics."""

from __future__ import annotations

from app.modules.child.scoring.types import (
    ParentStyleDimension,
    ScaleSemantics,
    ScoringPolicy,
    ScoringRule,
)

PARENT_STYLE_SCORING_VERSION = "parent-style-mvp-1"
PARENT_STYLE_REFERENCE_VERSION = "parent-style-reference-1"
PARENT_STYLE_POLICY = ScoringPolicy(
    correlation_family_cap=0.30,
    minimum_independent_families=2,
    expected_independent_families=4,
)

PARENT_STYLE_SCALES: dict[ParentStyleDimension, ScaleSemantics] = {
    ParentStyleDimension.EMOTIONAL_RESPONSIVENESS: ScaleSemantics(
        zero="more reserved and less immediately affect-responsive",
        hundred="more immediately emotionally responsive and reassuring",
    ),
    ParentStyleDimension.STRUCTURE: ScaleSemantics(
        zero="more open-ended and lightly structured",
        hundred="more structured with explicit routines and boundaries",
    ),
    ParentStyleDimension.CONTROL_TENDENCY: ScaleSemantics(
        zero="more permissive and low-directive",
        hundred="more directive and inclined to retain control",
    ),
    ParentStyleDimension.FLEXIBILITY: ScaleSemantics(
        zero="more plan-bound and change-resistant",
        hundred="more adaptive to changing pace and circumstances",
    ),
    ParentStyleDimension.COMMUNICATION_STYLE: ScaleSemantics(
        zero="more concise, implicit, or action-led communication",
        hundred="more verbal, explanatory, and dialog-oriented communication",
    ),
    ParentStyleDimension.PROTECTION: ScaleSemantics(
        zero="more observational and willing to allow distance",
        hundred="more actively protective and intervention-ready",
    ),
    ParentStyleDimension.AUTONOMY_SUPPORT: ScaleSemantics(
        zero="more guidance-led and closely supervised",
        hundred="more choice-oriented and independence-supporting",
    ),
    ParentStyleDimension.CONSISTENCY: ScaleSemantics(
        zero="more variable and context-responsive",
        hundred="more steady, repeatable, and routine-oriented",
    ),
}

R = ScoringRule
D = ParentStyleDimension

PARENT_STYLE_RULES: tuple[ScoringRule, ...] = (
    R(D.EMOTIONAL_RESPONSIVENESS, ("placement:moon:",), "body:moon", 0.18),
    R(D.EMOTIONAL_RESPONSIVENESS, ("placement:venus:",), "body:venus", 0.12),
    R(D.EMOTIONAL_RESPONSIVENESS, ("balance:element:water",), "balance:water", 0.18),
    R(D.EMOTIONAL_RESPONSIVENESS, ("aspect:moon:venus",), "pair:moon-venus", 0.14),
    R(D.EMOTIONAL_RESPONSIVENESS, ("placement:saturn:",), "body:saturn", -0.08),
    R(D.STRUCTURE, ("placement:saturn:",), "body:saturn", 0.20),
    R(D.STRUCTURE, ("balance:element:earth",), "balance:earth", 0.18),
    R(D.STRUCTURE, ("balance:modality:fixed",), "balance:fixed", 0.14),
    R(D.STRUCTURE, ("balance:modality:mutable",), "balance:mutable", -0.10),
    R(D.STRUCTURE, ("house_10",), "house:10", 0.10, time_sensitive=True),
    R(D.CONTROL_TENDENCY, ("placement:saturn:",), "body:saturn", 0.18),
    R(D.CONTROL_TENDENCY, ("placement:mars:",), "body:mars", 0.14),
    R(D.CONTROL_TENDENCY, ("balance:modality:fixed",), "balance:fixed", 0.15),
    R(D.CONTROL_TENDENCY, ("placement:uranus:",), "body:uranus", -0.16),
    R(D.CONTROL_TENDENCY, ("balance:modality:mutable",), "balance:mutable", -0.12),
    R(D.FLEXIBILITY, ("placement:uranus:",), "body:uranus", 0.18),
    R(D.FLEXIBILITY, ("placement:mercury:",), "body:mercury", 0.10),
    R(D.FLEXIBILITY, ("balance:modality:mutable",), "balance:mutable", 0.20),
    R(D.FLEXIBILITY, ("balance:element:air",), "balance:air", 0.12),
    R(D.FLEXIBILITY, ("placement:saturn:",), "body:saturn", -0.12),
    R(D.FLEXIBILITY, ("balance:modality:fixed",), "balance:fixed", -0.14),
    R(D.COMMUNICATION_STYLE, ("placement:mercury:",), "body:mercury", 0.20),
    R(D.COMMUNICATION_STYLE, ("placement:venus:",), "body:venus", 0.10),
    R(D.COMMUNICATION_STYLE, ("balance:element:air",), "balance:air", 0.20),
    R(D.COMMUNICATION_STYLE, ("aspect:mercury:saturn",), "pair:mercury-saturn", -0.10),
    R(D.COMMUNICATION_STYLE, ("house_3",), "house:3", 0.10, time_sensitive=True),
    R(D.PROTECTION, ("placement:moon:",), "body:moon", 0.18),
    R(D.PROTECTION, ("placement:mars:",), "body:mars", 0.12),
    R(D.PROTECTION, ("balance:element:water",), "balance:water", 0.16),
    R(D.PROTECTION, ("placement:saturn:",), "body:saturn", 0.10),
    R(D.PROTECTION, ("placement:uranus:",), "body:uranus", -0.10),
    R(D.PROTECTION, ("house_4",), "house:4", 0.10, time_sensitive=True),
    R(D.AUTONOMY_SUPPORT, ("placement:uranus:",), "body:uranus", 0.20),
    R(D.AUTONOMY_SUPPORT, ("placement:sun:",), "body:sun", 0.12),
    R(D.AUTONOMY_SUPPORT, ("balance:element:air",), "balance:air", 0.14),
    R(D.AUTONOMY_SUPPORT, ("balance:modality:mutable",), "balance:mutable", 0.12),
    R(D.AUTONOMY_SUPPORT, ("placement:saturn:",), "body:saturn", -0.14),
    R(D.AUTONOMY_SUPPORT, ("balance:modality:fixed",), "balance:fixed", -0.10),
    R(D.CONSISTENCY, ("placement:saturn:",), "body:saturn", 0.20),
    R(D.CONSISTENCY, ("balance:element:earth",), "balance:earth", 0.18),
    R(D.CONSISTENCY, ("balance:modality:fixed",), "balance:fixed", 0.18),
    R(D.CONSISTENCY, ("balance:modality:mutable",), "balance:mutable", -0.14),
    R(D.CONSISTENCY, ("placement:uranus:",), "body:uranus", -0.12),
)
