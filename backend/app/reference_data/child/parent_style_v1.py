"""Versioned Parent Style factor catalog and scale semantics."""

from __future__ import annotations

from app.modules.child.scoring.types import (
    ParentStyleDimension,
    ScaleSemantics,
    ScoringPolicy,
    ScoringRule,
)

PARENT_STYLE_SCORING_VERSION = "parent-style-mvp-2"
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
    R(D.EMOTIONAL_RESPONSIVENESS, ("placement:moon:cancer:",), "body:moon", 0.18),
    R(D.EMOTIONAL_RESPONSIVENESS, ("placement:moon:pisces:",), "body:moon", 0.16),
    R(D.EMOTIONAL_RESPONSIVENESS, ("placement:moon:scorpio:",), "body:moon", 0.12),
    R(D.EMOTIONAL_RESPONSIVENESS, ("placement:moon:capricorn:",), "body:moon", -0.14),
    R(D.EMOTIONAL_RESPONSIVENESS, ("placement:moon:aquarius:",), "body:moon", -0.10),
    R(D.EMOTIONAL_RESPONSIVENESS, ("placement:venus:libra:",), "body:venus", 0.12),
    R(D.EMOTIONAL_RESPONSIVENESS, ("placement:venus:taurus:",), "body:venus", 0.10),
    R(D.EMOTIONAL_RESPONSIVENESS, ("placement:venus:aries:",), "body:venus", -0.10),
    R(D.EMOTIONAL_RESPONSIVENESS, ("balance:element:water",), "balance:water", 0.18),
    R(D.EMOTIONAL_RESPONSIVENESS, ("aspect:moon:venus:trine",), "pair:moon-venus", 0.14),
    R(D.EMOTIONAL_RESPONSIVENESS, ("aspect:moon:venus:sextile",), "pair:moon-venus", 0.10),
    R(D.EMOTIONAL_RESPONSIVENESS, ("aspect:moon:venus:square",), "pair:moon-venus", -0.12),
    R(D.EMOTIONAL_RESPONSIVENESS, ("aspect:moon:saturn:opposition",), "pair:moon-saturn", -0.12),
    R(D.STRUCTURE, ("placement:saturn:capricorn:",), "body:saturn", 0.20),
    R(D.STRUCTURE, ("placement:saturn:aquarius:",), "body:saturn", 0.14),
    R(D.STRUCTURE, ("placement:saturn:cancer:",), "body:saturn", -0.14),
    R(D.STRUCTURE, ("placement:saturn:aries:",), "body:saturn", -0.12),
    R(D.STRUCTURE, ("balance:element:earth",), "balance:earth", 0.18),
    R(D.STRUCTURE, ("balance:modality:fixed",), "balance:fixed", 0.14),
    R(D.STRUCTURE, ("balance:modality:mutable",), "balance:mutable", -0.10),
    R(D.STRUCTURE, ("house_10",), "house:10", 0.10, time_sensitive=True),
    R(D.CONTROL_TENDENCY, ("placement:saturn:capricorn:",), "body:saturn", 0.18),
    R(D.CONTROL_TENDENCY, ("placement:saturn:cancer:",), "body:saturn", -0.12),
    R(D.CONTROL_TENDENCY, ("placement:mars:aries:",), "body:mars", 0.14),
    R(D.CONTROL_TENDENCY, ("placement:mars:capricorn:",), "body:mars", 0.12),
    R(D.CONTROL_TENDENCY, ("placement:mars:libra:",), "body:mars", -0.10),
    R(D.CONTROL_TENDENCY, ("balance:modality:fixed",), "balance:fixed", 0.15),
    R(D.CONTROL_TENDENCY, ("placement:uranus:aquarius:",), "body:uranus", -0.16),
    R(D.CONTROL_TENDENCY, ("balance:modality:mutable",), "balance:mutable", -0.12),
    R(D.FLEXIBILITY, ("placement:uranus:aquarius:",), "body:uranus", 0.18),
    R(D.FLEXIBILITY, ("placement:uranus:gemini:",), "body:uranus", 0.16),
    R(D.FLEXIBILITY, ("placement:uranus:taurus:",), "body:uranus", -0.14),
    R(D.FLEXIBILITY, ("placement:mercury:gemini:",), "body:mercury", 0.10),
    R(D.FLEXIBILITY, ("placement:mercury:aquarius:",), "body:mercury", 0.10),
    R(D.FLEXIBILITY, ("placement:mercury:taurus:",), "body:mercury", -0.10),
    R(D.FLEXIBILITY, ("balance:modality:mutable",), "balance:mutable", 0.20),
    R(D.FLEXIBILITY, ("balance:element:air",), "balance:air", 0.12),
    R(D.FLEXIBILITY, ("placement:saturn:capricorn:",), "body:saturn", -0.12),
    R(D.FLEXIBILITY, ("balance:modality:fixed",), "balance:fixed", -0.14),
    R(D.COMMUNICATION_STYLE, ("placement:mercury:gemini:",), "body:mercury", 0.20),
    R(D.COMMUNICATION_STYLE, ("placement:mercury:virgo:",), "body:mercury", 0.16),
    R(D.COMMUNICATION_STYLE, ("placement:mercury:pisces:",), "body:mercury", -0.14),
    R(D.COMMUNICATION_STYLE, ("placement:venus:libra:",), "body:venus", 0.10),
    R(D.COMMUNICATION_STYLE, ("balance:element:air",), "balance:air", 0.20),
    R(D.COMMUNICATION_STYLE, ("aspect:mercury:saturn:trine",), "pair:mercury-saturn", 0.08),
    R(D.COMMUNICATION_STYLE, ("aspect:mercury:saturn:square",), "pair:mercury-saturn", -0.10),
    R(D.COMMUNICATION_STYLE, ("house_3",), "house:3", 0.10, time_sensitive=True),
    R(D.PROTECTION, ("placement:moon:cancer:",), "body:moon", 0.18),
    R(D.PROTECTION, ("placement:moon:aquarius:",), "body:moon", -0.10),
    R(D.PROTECTION, ("placement:mars:cancer:",), "body:mars", 0.12),
    R(D.PROTECTION, ("placement:mars:aries:",), "body:mars", 0.08),
    R(D.PROTECTION, ("balance:element:water",), "balance:water", 0.16),
    R(D.PROTECTION, ("placement:saturn:capricorn:",), "body:saturn", 0.10),
    R(D.PROTECTION, ("placement:uranus:aquarius:",), "body:uranus", -0.10),
    R(D.PROTECTION, ("house_4",), "house:4", 0.10, time_sensitive=True),
    R(D.AUTONOMY_SUPPORT, ("placement:uranus:aquarius:",), "body:uranus", 0.20),
    R(D.AUTONOMY_SUPPORT, ("placement:uranus:taurus:",), "body:uranus", -0.12),
    R(D.AUTONOMY_SUPPORT, ("placement:sun:leo:",), "body:sun", 0.12),
    R(D.AUTONOMY_SUPPORT, ("placement:sun:aquarius:",), "body:sun", 0.14),
    R(D.AUTONOMY_SUPPORT, ("placement:sun:cancer:",), "body:sun", -0.10),
    R(D.AUTONOMY_SUPPORT, ("balance:element:air",), "balance:air", 0.14),
    R(D.AUTONOMY_SUPPORT, ("balance:modality:mutable",), "balance:mutable", 0.12),
    R(D.AUTONOMY_SUPPORT, ("placement:saturn:capricorn:",), "body:saturn", -0.14),
    R(D.AUTONOMY_SUPPORT, ("balance:modality:fixed",), "balance:fixed", -0.10),
    R(D.CONSISTENCY, ("placement:saturn:capricorn:",), "body:saturn", 0.20),
    R(D.CONSISTENCY, ("placement:saturn:cancer:",), "body:saturn", -0.12),
    R(D.CONSISTENCY, ("balance:element:earth",), "balance:earth", 0.18),
    R(D.CONSISTENCY, ("balance:modality:fixed",), "balance:fixed", 0.18),
    R(D.CONSISTENCY, ("balance:modality:mutable",), "balance:mutable", -0.14),
    R(D.CONSISTENCY, ("placement:uranus:aquarius:",), "body:uranus", -0.12),
)
