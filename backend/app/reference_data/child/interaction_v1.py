"""Versioned deterministic references for parent-child interaction scoring."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.child.scoring.types import ChildNeedDimension, InteractionDimension, ParentStyleDimension

INTERACTION_SCORING_VERSION = "child-interaction-mvp-1"
INTERACTION_REFERENCE_VERSION = "child-interaction-reference-1"
SYNASTRY_REFERENCE_VERSION = "child-synastry-reference-1"
CORRELATION_FAMILY_CAP = 0.30
SATURN_DIMENSION_CAP = 0.08
MINIMUM_INDEPENDENT_FAMILIES = 2
EXPECTED_INDEPENDENT_FAMILIES = 3


@dataclass(frozen=True, slots=True)
class FitRule:
    dimension: InteractionDimension
    parent_dimension: ParentStyleDimension
    child_dimension: ChildNeedDimension
    signal_family: str
    weight: float
    invert_child: bool = False


@dataclass(frozen=True, slots=True)
class AspectDefinition:
    code: str
    angle: float
    orb: float
    direction: int


@dataclass(frozen=True, slots=True)
class SynastryRule:
    parent_body: str
    child_body: str
    dimensions: tuple[InteractionDimension, ...]
    signal_family: str
    weight: float
    factor_label: str
    saturn_bounded: bool = False


@dataclass(frozen=True, slots=True)
class HouseOverlayDefinition:
    house_number: int
    dimensions: tuple[InteractionDimension, ...]
    direction: int
    factor_label: str


D = InteractionDimension
P = ParentStyleDimension
C = ChildNeedDimension

FIT_RULES: tuple[FitRule, ...] = (
    FitRule(D.EMOTIONAL_ATTUNEMENT, P.EMOTIONAL_RESPONSIVENESS, C.REASSURANCE, "fit:emotional-reassurance", 0.24),
    FitRule(D.EMOTIONAL_ATTUNEMENT, P.COMMUNICATION_STYLE, C.RECOGNITION, "fit:emotional-recognition", 0.16),
    FitRule(D.BOUNDARY_FIT, P.STRUCTURE, C.PREDICTABILITY, "fit:structure-predictability", 0.24),
    FitRule(D.BOUNDARY_FIT, P.CONSISTENCY, C.TRANSITION_TIME, "fit:consistency-transition", 0.18),
    FitRule(D.AUTONOMY_BALANCE, P.AUTONOMY_SUPPORT, C.AUTONOMY, "fit:autonomy-support", 0.25),
    FitRule(D.AUTONOMY_BALANCE, P.CONTROL_TENDENCY, C.EXPLORATION, "fit:control-exploration", 0.18, True),
    FitRule(D.COMMUNICATION_FIT, P.COMMUNICATION_STYLE, C.VERBAL_EXPLANATION, "fit:communication-explanation", 0.25),
    FitRule(D.COMMUNICATION_FIT, P.FLEXIBILITY, C.VARIETY, "fit:flexibility-variety", 0.16),
    FitRule(D.TEMPO_FIT, P.FLEXIBILITY, C.TRANSITION_TIME, "fit:flexibility-transition", 0.22, True),
    FitRule(D.TEMPO_FIT, P.CONSISTENCY, C.PREDICTABILITY, "fit:consistency-predictability", 0.18),
    FitRule(D.CONFLICT_PATTERN, P.CONTROL_TENDENCY, C.AUTONOMY, "fit:control-autonomy", 0.24, True),
    FitRule(D.CONFLICT_PATTERN, P.FLEXIBILITY, C.PERSONAL_SPACE, "fit:flexibility-space", 0.16),
    FitRule(
        D.SOOTHING_COMPATIBILITY, P.EMOTIONAL_RESPONSIVENESS, C.PHYSICAL_SENSORY_CALM, "fit:responsiveness-calm", 0.22
    ),
    FitRule(D.SOOTHING_COMPATIBILITY, P.PROTECTION, C.REASSURANCE, "fit:protection-reassurance", 0.18),
    FitRule(D.LEARNING_INTERACTION, P.COMMUNICATION_STYLE, C.VERBAL_EXPLANATION, "fit:teaching-explanation", 0.22),
    FitRule(D.LEARNING_INTERACTION, P.AUTONOMY_SUPPORT, C.EXPLORATION, "fit:autonomy-exploration", 0.18),
)

ASPECT_CATALOG: tuple[AspectDefinition, ...] = (
    AspectDefinition("conjunction", 0.0, 8.0, 1),
    AspectDefinition("sextile", 60.0, 5.0, 1),
    AspectDefinition("square", 90.0, 6.0, -1),
    AspectDefinition("trine", 120.0, 6.0, 1),
    AspectDefinition("opposition", 180.0, 8.0, -1),
)

PERSONAL_BODIES = ("sun", "moon", "mercury", "venus", "mars")
ANGLE_BODIES = ("ascendant", "mc")

SYNASTRY_RULES: tuple[SynastryRule, ...] = (
    SynastryRule(
        "sun",
        "sun",
        (D.AUTONOMY_BALANCE, D.LEARNING_INTERACTION),
        "pair:sun-sun",
        0.10,
        "identity_expression_awareness",
    ),
    SynastryRule(
        "sun",
        "moon",
        (D.EMOTIONAL_ATTUNEMENT, D.SOOTHING_COMPATIBILITY),
        "pair:sun-moon",
        0.12,
        "emotional_expression_awareness",
    ),
    SynastryRule(
        "moon",
        "sun",
        (D.EMOTIONAL_ATTUNEMENT, D.SOOTHING_COMPATIBILITY),
        "pair:sun-moon",
        0.12,
        "emotional_expression_awareness",
    ),
    SynastryRule(
        "moon",
        "moon",
        (D.EMOTIONAL_ATTUNEMENT, D.SOOTHING_COMPATIBILITY),
        "pair:moon-moon",
        0.14,
        "emotional_rhythm_awareness",
    ),
    SynastryRule(
        "moon",
        "mercury",
        (D.COMMUNICATION_FIT, D.EMOTIONAL_ATTUNEMENT),
        "pair:moon-mercury",
        0.10,
        "emotion_language_awareness",
    ),
    SynastryRule(
        "mercury",
        "moon",
        (D.COMMUNICATION_FIT, D.EMOTIONAL_ATTUNEMENT),
        "pair:moon-mercury",
        0.10,
        "emotion_language_awareness",
    ),
    SynastryRule(
        "mercury",
        "mercury",
        (D.COMMUNICATION_FIT, D.LEARNING_INTERACTION),
        "pair:mercury-mercury",
        0.13,
        "communication_processing_awareness",
    ),
    SynastryRule(
        "mercury",
        "mars",
        (D.COMMUNICATION_FIT, D.CONFLICT_PATTERN),
        "pair:mercury-mars",
        0.11,
        "communication_activation_awareness",
    ),
    SynastryRule(
        "venus",
        "moon",
        (D.EMOTIONAL_ATTUNEMENT, D.SOOTHING_COMPATIBILITY),
        "pair:venus-moon",
        0.12,
        "care_reception_awareness",
    ),
    SynastryRule(
        "moon",
        "venus",
        (D.EMOTIONAL_ATTUNEMENT, D.SOOTHING_COMPATIBILITY),
        "pair:venus-moon",
        0.12,
        "care_reception_awareness",
    ),
    SynastryRule(
        "mars",
        "mercury",
        (D.COMMUNICATION_FIT, D.CONFLICT_PATTERN),
        "pair:mercury-mars",
        0.11,
        "communication_activation_awareness",
    ),
    SynastryRule(
        "mars", "mars", (D.TEMPO_FIT, D.CONFLICT_PATTERN), "pair:mars-mars", 0.12, "activation_tempo_awareness"
    ),
)

SATURN_DIMENSIONS = (D.BOUNDARY_FIT, D.AUTONOMY_BALANCE, D.CONFLICT_PATTERN)
JUPITER_DIMENSIONS = (D.AUTONOMY_BALANCE, D.LEARNING_INTERACTION)

HOUSE_OVERLAY_WEIGHT = 0.04
HOUSE_OVERLAY_DEFINITIONS: tuple[HouseOverlayDefinition, ...] = (
    HouseOverlayDefinition(1, (D.AUTONOMY_BALANCE,), 1, "self_expression_context"),
    HouseOverlayDefinition(3, (D.COMMUNICATION_FIT, D.LEARNING_INTERACTION), 1, "communication_context"),
    HouseOverlayDefinition(4, (D.EMOTIONAL_ATTUNEMENT, D.SOOTHING_COMPATIBILITY), 1, "emotional_home_context"),
    HouseOverlayDefinition(5, (D.LEARNING_INTERACTION, D.AUTONOMY_BALANCE), 1, "play_expression_context"),
    HouseOverlayDefinition(6, (D.TEMPO_FIT, D.LEARNING_INTERACTION), -1, "routine_adjustment_awareness"),
    HouseOverlayDefinition(7, (D.EMOTIONAL_ATTUNEMENT, D.BOUNDARY_FIT), 1, "relational_awareness"),
    HouseOverlayDefinition(8, (D.CONFLICT_PATTERN, D.SOOTHING_COMPATIBILITY), -1, "intensity_awareness"),
    HouseOverlayDefinition(9, (D.LEARNING_INTERACTION, D.AUTONOMY_BALANCE), 1, "exploration_learning_context"),
    HouseOverlayDefinition(10, (D.BOUNDARY_FIT, D.CONFLICT_PATTERN), -1, "expectations_structure_awareness"),
    HouseOverlayDefinition(11, (D.AUTONOMY_BALANCE, D.COMMUNICATION_FIT), 1, "social_exploration_context"),
    HouseOverlayDefinition(12, (D.SOOTHING_COMPATIBILITY, D.EMOTIONAL_ATTUNEMENT), -1, "private_regulation_awareness"),
)
