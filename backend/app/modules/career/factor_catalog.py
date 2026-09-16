"""Versioned deterministic factor weights for Career MVP dimensions."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.career.schemas import CareerDimensionKey

CAREER_SCORING_VERSION = "career-mvp-1"
CAREER_NORMALIZATION_VERSION = "career-linear-1"
CAREER_CONFIDENCE_VERSION = "career-independent-families-1"
CORRELATION_FAMILY_CAP = 0.35
MIN_INDEPENDENT_FAMILIES = 2
EXPECTED_INDEPENDENT_FAMILIES = 3


@dataclass(frozen=True)
class FactorRule:
    dimension: CareerDimensionKey
    contains: tuple[str, ...]
    weight: float

    def matches(self, factor_key: str) -> bool:
        return all(token in factor_key for token in self.contains)


FACTOR_RULES: tuple[FactorRule, ...] = (
    FactorRule(CareerDimensionKey.LEADERSHIP, ("placement:sun:",), 0.11),
    FactorRule(CareerDimensionKey.LEADERSHIP, ("placement:mars:",), 0.11),
    FactorRule(CareerDimensionKey.LEADERSHIP, ("placement:saturn:",), 0.10),
    FactorRule(CareerDimensionKey.LEADERSHIP, ("balance:modality:cardinal",), 0.1285714286),
    FactorRule(CareerDimensionKey.ANALYTICAL_THINKING, ("placement:mercury:",), 0.12),
    FactorRule(CareerDimensionKey.ANALYTICAL_THINKING, ("placement:saturn:",), 0.12),
    FactorRule(CareerDimensionKey.ANALYTICAL_THINKING, ("balance:element:earth",), 0.125),
    FactorRule(CareerDimensionKey.ANALYTICAL_THINKING, ("aspect:mercury:saturn",), 0.15),
    FactorRule(CareerDimensionKey.SYSTEMS_THINKING, ("placement:mercury:",), 0.13),
    FactorRule(CareerDimensionKey.SYSTEMS_THINKING, ("placement:saturn:",), 0.13),
    FactorRule(CareerDimensionKey.SYSTEMS_THINKING, ("placement:uranus:",), 0.12),
    FactorRule(CareerDimensionKey.SYSTEMS_THINKING, ("house_8",), 0.08),
    FactorRule(CareerDimensionKey.COMMUNICATION, ("placement:mercury:",), 0.12),
    FactorRule(CareerDimensionKey.COMMUNICATION, ("placement:venus:",), 0.12),
    FactorRule(CareerDimensionKey.COMMUNICATION, ("balance:element:air",), 0.20),
    FactorRule(CareerDimensionKey.CREATIVITY, ("placement:sun:",), 0.12),
    FactorRule(CareerDimensionKey.CREATIVITY, ("placement:venus:",), 0.12),
    FactorRule(CareerDimensionKey.CREATIVITY, ("placement:neptune:",), 0.12),
    FactorRule(CareerDimensionKey.CREATIVITY, ("pattern:creative",), 0.10),
    FactorRule(CareerDimensionKey.STRUCTURE, ("placement:saturn:",), 0.12),
    FactorRule(CareerDimensionKey.STRUCTURE, ("balance:element:earth",), 0.125),
    FactorRule(CareerDimensionKey.STRUCTURE, ("balance:modality:fixed",), 0.20),
    FactorRule(CareerDimensionKey.STRUCTURE, ("house_2",), 0.08),
    FactorRule(CareerDimensionKey.AUTONOMY, ("placement:uranus:",), 0.16),
    FactorRule(CareerDimensionKey.AUTONOMY, ("placement:mars:",), 0.14),
    FactorRule(CareerDimensionKey.AUTONOMY, ("placement:sun:",), 0.14),
    FactorRule(CareerDimensionKey.RISK_TOLERANCE, ("placement:mars:",), 0.04),
    FactorRule(CareerDimensionKey.RISK_TOLERANCE, ("placement:uranus:",), 0.04),
    FactorRule(CareerDimensionKey.RISK_TOLERANCE, ("placement:saturn:",), -0.04),
    FactorRule(CareerDimensionKey.PEOPLE_ORIENTATION, ("placement:moon:",), 0.10),
    FactorRule(CareerDimensionKey.PEOPLE_ORIENTATION, ("placement:venus:",), 0.10),
    FactorRule(CareerDimensionKey.PEOPLE_ORIENTATION, ("house_7",), 0.08),
    FactorRule(CareerDimensionKey.PEOPLE_ORIENTATION, ("balance:element:air",), 0.1333333333),
    FactorRule(CareerDimensionKey.INNOVATION, ("placement:uranus:",), 0.16),
    FactorRule(CareerDimensionKey.INNOVATION, ("balance:element:air",), 0.20),
    FactorRule(CareerDimensionKey.INNOVATION, ("pattern:innovation",), 0.12),
    FactorRule(CareerDimensionKey.LONG_TERM_FOCUS, ("placement:saturn:",), 0.12),
    FactorRule(CareerDimensionKey.LONG_TERM_FOCUS, ("balance:modality:fixed",), 0.20),
    FactorRule(CareerDimensionKey.LONG_TERM_FOCUS, ("balance:element:earth",), 0.125),
    FactorRule(CareerDimensionKey.LONG_TERM_FOCUS, ("house_9",), 0.08),
    FactorRule(CareerDimensionKey.EXECUTION, ("placement:mars:",), 0.11),
    FactorRule(CareerDimensionKey.EXECUTION, ("placement:saturn:",), 0.11),
    FactorRule(CareerDimensionKey.EXECUTION, ("balance:modality:cardinal",), 0.1428571429),
    FactorRule(CareerDimensionKey.EXECUTION, ("balance:modality:fixed",), 0.1666666667),
)
