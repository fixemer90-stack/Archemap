"""Versioned Child Needs factor catalog and interaction-condition scale semantics."""

from __future__ import annotations

from app.modules.child.scoring.types import (
    ChildNeedDimension,
    ScaleSemantics,
    ScoringPolicy,
    ScoringRule,
)

CHILD_NEEDS_SCORING_VERSION = "child-needs-mvp-1"
CHILD_NEEDS_REFERENCE_VERSION = "child-needs-reference-1"
CHILD_NEEDS_POLICY = ScoringPolicy(
    correlation_family_cap=0.30,
    minimum_independent_families=2,
    expected_independent_families=4,
)

D = ChildNeedDimension
R = ScoringRule

CHILD_NEEDS_SCALES: dict[ChildNeedDimension, ScaleSemantics] = {
    D.REASSURANCE: ScaleSemantics(
        zero="interaction can rely more on quiet availability than repeated reassurance",
        hundred="interaction may be easier with frequent explicit emotional reassurance",
    ),
    D.PREDICTABILITY: ScaleSemantics(
        zero="interaction may tolerate more spontaneity and changing routines",
        hundred="interaction may be easier with stable routines and advance expectations",
    ),
    D.AUTONOMY: ScaleSemantics(
        zero="interaction may be easier with closer adult guidance and shared decisions",
        hundred="interaction may be easier with meaningful choice and self-directed attempts",
    ),
    D.VERBAL_EXPLANATION: ScaleSemantics(
        zero="interaction may work better through concise cues, examples, or action",
        hundred="interaction may be easier with detailed verbal explanation and dialogue",
    ),
    D.PHYSICAL_SENSORY_CALM: ScaleSemantics(
        zero="interaction may tolerate stronger stimulation and faster activation",
        hundred="interaction may be easier with lower sensory intensity and physical calm",
    ),
    D.EXPLORATION: ScaleSemantics(
        zero="interaction may be easier with familiar paths and guided practice",
        hundred="interaction may be easier with room to investigate and experiment",
    ),
    D.RECOGNITION: ScaleSemantics(
        zero="interaction may need less explicit acknowledgment and visible feedback",
        hundred="interaction may be easier with clear recognition of effort and contribution",
    ),
    D.PERSONAL_SPACE: ScaleSemantics(
        zero="interaction may be easier with more continuous shared engagement",
        hundred="interaction may be easier when privacy and decompression space are protected",
    ),
    D.TRANSITION_TIME: ScaleSemantics(
        zero="interaction may handle quick changes and immediate redirection more easily",
        hundred="interaction may be easier with warning and gradual transitions",
    ),
    D.VARIETY: ScaleSemantics(
        zero="interaction may be easier with repetition and a narrower stable rhythm",
        hundred="interaction may be easier with varied activities and changing approaches",
    ),
}

CHILD_NEEDS_RULES: tuple[ScoringRule[ChildNeedDimension], ...] = (
    R(D.REASSURANCE, ("placement:moon:cancer:",), "body:moon", 0.20),
    R(D.REASSURANCE, ("placement:moon:pisces:",), "body:moon", 0.16),
    R(D.REASSURANCE, ("placement:moon:capricorn:",), "body:moon", -0.14),
    R(D.REASSURANCE, ("placement:venus:libra:",), "body:venus", 0.12),
    R(D.REASSURANCE, ("balance:element:water",), "balance:water", 0.18),
    R(D.REASSURANCE, ("aspect:moon:venus:trine",), "pair:moon-venus", 0.14),
    R(D.REASSURANCE, ("house_4",), "house:4", 0.08, time_sensitive=True),
    R(D.PREDICTABILITY, ("placement:saturn:capricorn:",), "body:saturn", 0.20),
    R(D.PREDICTABILITY, ("placement:saturn:cancer:",), "body:saturn", -0.12),
    R(D.PREDICTABILITY, ("balance:element:earth",), "balance:earth", 0.18),
    R(D.PREDICTABILITY, ("balance:modality:fixed",), "balance:fixed", 0.16),
    R(D.PREDICTABILITY, ("balance:modality:mutable",), "balance:mutable", -0.14),
    R(D.PREDICTABILITY, ("house_6",), "house:6", 0.10, time_sensitive=True),
    R(D.AUTONOMY, ("placement:uranus:aquarius:",), "body:uranus", 0.20),
    R(D.AUTONOMY, ("placement:uranus:taurus:",), "body:uranus", -0.14),
    R(D.AUTONOMY, ("placement:mars:aries:",), "body:mars", 0.14),
    R(D.AUTONOMY, ("placement:sun:leo:",), "body:sun", 0.12),
    R(D.AUTONOMY, ("balance:element:air",), "balance:air", 0.14),
    R(D.AUTONOMY, ("house_1",), "house:1", 0.10, time_sensitive=True),
    R(D.VERBAL_EXPLANATION, ("placement:mercury:gemini:",), "body:mercury", 0.20),
    R(D.VERBAL_EXPLANATION, ("placement:mercury:virgo:",), "body:mercury", 0.16),
    R(D.VERBAL_EXPLANATION, ("placement:mercury:pisces:",), "body:mercury", -0.14),
    R(D.VERBAL_EXPLANATION, ("balance:element:air",), "balance:air", 0.18),
    R(D.VERBAL_EXPLANATION, ("aspect:mercury:saturn:trine",), "pair:mercury-saturn", 0.10),
    R(D.VERBAL_EXPLANATION, ("house_3",), "house:3", 0.10, time_sensitive=True),
    R(D.PHYSICAL_SENSORY_CALM, ("placement:moon:cancer:",), "body:moon", 0.14),
    R(D.PHYSICAL_SENSORY_CALM, ("placement:venus:taurus:",), "body:venus", 0.18),
    R(D.PHYSICAL_SENSORY_CALM, ("placement:mars:aries:",), "body:mars", -0.14),
    R(D.PHYSICAL_SENSORY_CALM, ("balance:element:earth",), "balance:earth", 0.16),
    R(D.PHYSICAL_SENSORY_CALM, ("balance:element:fire",), "balance:fire", -0.12),
    R(D.PHYSICAL_SENSORY_CALM, ("house_4",), "house:4", 0.08, time_sensitive=True),
    R(D.EXPLORATION, ("placement:jupiter:sagittarius:",), "body:jupiter", 0.20),
    R(D.EXPLORATION, ("placement:uranus:aquarius:",), "body:uranus", 0.14),
    R(D.EXPLORATION, ("placement:saturn:capricorn:",), "body:saturn", -0.10),
    R(D.EXPLORATION, ("balance:element:fire",), "balance:fire", 0.16),
    R(D.EXPLORATION, ("balance:modality:mutable",), "balance:mutable", 0.12),
    R(D.EXPLORATION, ("house_9",), "house:9", 0.10, time_sensitive=True),
    R(D.RECOGNITION, ("placement:sun:leo:",), "body:sun", 0.20),
    R(D.RECOGNITION, ("placement:sun:aquarius:",), "body:sun", -0.10),
    R(D.RECOGNITION, ("placement:venus:libra:",), "body:venus", 0.12),
    R(D.RECOGNITION, ("balance:element:fire",), "balance:fire", 0.14),
    R(D.RECOGNITION, ("house_5",), "house:5", 0.12, time_sensitive=True),
    R(D.RECOGNITION, ("house_10",), "house:10", 0.08, time_sensitive=True),
    R(D.PERSONAL_SPACE, ("placement:moon:aquarius:",), "body:moon", 0.16),
    R(D.PERSONAL_SPACE, ("placement:uranus:aquarius:",), "body:uranus", 0.18),
    R(D.PERSONAL_SPACE, ("placement:moon:cancer:",), "body:moon", -0.10),
    R(D.PERSONAL_SPACE, ("balance:element:air",), "balance:air", 0.16),
    R(D.PERSONAL_SPACE, ("balance:element:water",), "balance:water", -0.08),
    R(D.PERSONAL_SPACE, ("house_12",), "house:12", 0.12, time_sensitive=True),
    R(D.TRANSITION_TIME, ("placement:mercury:taurus:",), "body:mercury", 0.16),
    R(D.TRANSITION_TIME, ("placement:saturn:capricorn:",), "body:saturn", 0.14),
    R(D.TRANSITION_TIME, ("placement:uranus:aquarius:",), "body:uranus", -0.12),
    R(D.TRANSITION_TIME, ("balance:modality:fixed",), "balance:fixed", 0.20),
    R(D.TRANSITION_TIME, ("balance:modality:mutable",), "balance:mutable", -0.16),
    R(D.TRANSITION_TIME, ("house_6",), "house:6", 0.08, time_sensitive=True),
    R(D.VARIETY, ("placement:mercury:gemini:",), "body:mercury", 0.16),
    R(D.VARIETY, ("placement:jupiter:sagittarius:",), "body:jupiter", 0.14),
    R(D.VARIETY, ("placement:uranus:aquarius:",), "body:uranus", 0.16),
    R(D.VARIETY, ("placement:saturn:capricorn:",), "body:saturn", -0.12),
    R(D.VARIETY, ("balance:modality:mutable",), "balance:mutable", 0.20),
    R(D.VARIETY, ("balance:modality:fixed",), "balance:fixed", -0.14),
    R(D.VARIETY, ("house_3",), "house:3", 0.08, time_sensitive=True),
)
