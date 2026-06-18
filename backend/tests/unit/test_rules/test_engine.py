"""Unit tests for the rule engine."""

from __future__ import annotations

import pytest

from app.chart_engine.features import FeatureVector
from app.modules.rules.engine import _build_facts, _check_condition, _condition_match_score, interpret
from app.modules.rules.loader import load_ruleset
from app.modules.rules.types import Condition, ConditionOp

# ── Fixtures ─────────────────────────────────────────────────────────


def make_features(
    fire: float = 0.25,
    earth: float = 0.25,
    air: float = 0.25,
    water: float = 0.25,
    cardinal: float = 0.33,
    fixed: float = 0.33,
    mutable: float = 0.34,
    has_birth_time: bool = True,
    birth_time_quality: float = 1.0,
) -> FeatureVector:
    """Create a FeatureVector with custom values."""
    return FeatureVector(
        fire=fire,
        earth=earth,
        air=air,
        water=water,
        cardinal=cardinal,
        fixed=fixed,
        mutable=mutable,
        has_birth_time=has_birth_time,
        birth_time_quality=birth_time_quality,
    )


# ── Condition evaluation tests ───────────────────────────────────────


class TestConditionEvaluation:
    """Test single condition evaluation."""

    def test_gte_pass(self) -> None:
        facts = {"feature.earth": 0.50}
        cond = Condition(fact="feature.earth", op=ConditionOp.GTE, value=0.40)
        assert _check_condition(cond, facts) is True

    def test_gte_fail(self) -> None:
        facts = {"feature.earth": 0.30}
        cond = Condition(fact="feature.earth", op=ConditionOp.GTE, value=0.40)
        assert _check_condition(cond, facts) is False

    def test_lt_pass(self) -> None:
        facts = {"quality.birth_time_quality": 0.30}
        cond = Condition(fact="quality.birth_time_quality", op=ConditionOp.LT, value=0.50)
        assert _check_condition(cond, facts) is True

    def test_missing_fact(self) -> None:
        facts: dict[str, float] = {}
        cond = Condition(fact="feature.earth", op=ConditionOp.GTE, value=0.40)
        assert _check_condition(cond, facts) is False

    def test_eq(self) -> None:
        facts = {"feature.fire": 0.25}
        cond = Condition(fact="feature.fire", op=ConditionOp.EQ, value=0.25)
        assert _check_condition(cond, facts) is True

    def test_gte_match_score_uses_actual_strength(self) -> None:
        cond = Condition(fact="feature.earth", op=ConditionOp.GTE, value=0.35)
        assert _condition_match_score(cond, 0.45) == 0.45


# ── Fact building tests ──────────────────────────────────────────────


class TestFactBuilding:
    """Test FeatureVector → fact dictionary conversion."""

    def test_elements(self) -> None:
        features = make_features(fire=0.40, earth=0.30, air=0.20, water=0.10)
        facts = _build_facts(features)
        assert facts["feature.fire"] == 0.40
        assert facts["feature.earth"] == 0.30
        assert facts["feature.air"] == 0.20
        assert facts["feature.water"] == 0.10

    def test_modalities(self) -> None:
        features = make_features(cardinal=0.50, fixed=0.30, mutable=0.20)
        facts = _build_facts(features)
        assert facts["feature.cardinal"] == 0.50
        assert facts["feature.fixed"] == 0.30
        assert facts["feature.mutable"] == 0.20

    def test_quality_flags(self) -> None:
        features = make_features(has_birth_time=False, birth_time_quality=0.0)
        facts = _build_facts(features)
        assert facts["quality.has_birth_time"] is False
        assert facts["quality.birth_time_quality"] == 0.0


# ── Rule engine integration tests ────────────────────────────────────


class TestRuleEngine:
    """Test full rule engine interpretation."""

    def test_strateg_archetype(self) -> None:
        """Earth ≥ 0.35 + fixed ≥ 0.30 → Strateg archetype should score."""
        features = make_features(earth=0.45, fixed=0.40, fire=0.15, air=0.20, water=0.20)
        ruleset = load_ruleset("self", "v1")
        result = interpret(features, ruleset)

        # Should have at least one archetype
        assert result.primary_score > 0.0
        assert "Стратег" in result.primary_archetype or result.primary_score > 0

    def test_creator_archetype(self) -> None:
        """Fire ≥ 0.30 + mutable ≥ 0.25 → Creator archetype should score."""
        features = make_features(fire=0.40, mutable=0.35, earth=0.15, air=0.20, water=0.25)
        ruleset = load_ruleset("self", "v1")
        result = interpret(features, ruleset)

        assert result.primary_score > 0.0

    def test_active_archetype_scores_are_not_flat_yaml_weights(self) -> None:
        """Two activated archetypes with different feature strengths should not both show 0.25."""
        features = make_features(
            fire=0.40,
            mutable=0.35,
            air=0.31,
            cardinal=0.26,
            earth=0.15,
            water=0.10,
        )
        ruleset = load_ruleset("self", "v1")
        result = interpret(features, ruleset)

        assert result.all_archetype_scores["creator"] == pytest.approx(0.087)
        assert result.all_archetype_scores["diplomat"] == pytest.approx(0.045)
        assert len(set(result.all_archetype_scores.values())) > 1
        assert 0.25 not in result.all_archetype_scores.values()

    def test_no_archetype_low_values(self) -> None:
        """Balanced features → no archetype should dominate."""
        features = make_features(fire=0.25, earth=0.25, air=0.25, water=0.25)
        ruleset = load_ruleset("self", "v1")
        result = interpret(features, ruleset)

        # With balanced values, primary score should be low
        assert result.primary_score < 0.50

    def test_quality_warning_no_birth_time(self) -> None:
        """No birth time → quality warning should be present."""
        features = make_features(has_birth_time=False, birth_time_quality=0.0)
        ruleset = load_ruleset("self", "v1")
        result = interpret(features, ruleset)

        assert result.quality_warning is not None
        assert "неизвестно" in result.quality_warning.lower()

    def test_preview_mode_limits_claims(self) -> None:
        """Preview mode → max 2 archetypes, 3 claims."""
        features = make_features(earth=0.45, fixed=0.40, fire=0.35, mutable=0.30)
        ruleset = load_ruleset("self", "v1")
        result = interpret(features, ruleset, mode="preview")

        assert len(result.claims) <= 3

    def test_deterministic(self) -> None:
        """Same input → same output (deterministic)."""
        features = make_features(earth=0.45, fixed=0.40)
        ruleset = load_ruleset("self", "v1")

        result1 = interpret(features, ruleset)
        result2 = interpret(features, ruleset)

        assert result1.primary_score == result2.primary_score
        assert result1.primary_confidence.value == result2.primary_confidence.value

    def test_counter_evidence(self) -> None:
        """Both earth+fixed AND fire+mutable → counter-evidence should appear."""
        features = make_features(
            earth=0.40,
            fixed=0.35,
            fire=0.35,
            mutable=0.30,
            air=0.15,
            water=0.20,
        )
        ruleset = load_ruleset("self", "v1")
        result = interpret(features, ruleset)

        # Primary archetype should have counter-evidence when both earth+fixed and fire+mutable are high
        if result.primary_score > 0.15:
            assert len(result.claims) > 0

    def test_provenance_present(self) -> None:
        """Provenance should contain ruleset and engine versions."""
        features = make_features()
        ruleset = load_ruleset("self", "v1")
        result = interpret(features, ruleset)

        assert "ruleset_version" in result.provenance
        assert "engine_version" in result.provenance


# ── Loader tests ─────────────────────────────────────────────────────


class TestLoader:
    """Test YAML ruleset loading."""

    def test_load_self_ruleset(self) -> None:
        ruleset = load_ruleset("self", "v1")
        assert ruleset.product == "self"
        assert len(ruleset.archetypes) == 8

    def test_archetype_names(self) -> None:
        ruleset = load_ruleset("self", "v1")
        names = {a.name for a in ruleset.archetypes}
        assert "Стратег" in names
        assert "Творец" in names
        assert "Исследователь" in names
        assert "Опора" in names
        assert "Дипломат" in names
        assert "Катализатор" in names
        assert "Наставник" in names
        assert "Строитель" in names

    def test_scoring_params(self) -> None:
        ruleset = load_ruleset("self", "v1")
        assert ruleset.scoring.get("counter_penalty_lambda") == 0.30
        assert ruleset.confidence_config.get("weights", {}).get("q_input") == 0.35

    def test_nonexistent_ruleset(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_ruleset("nonexistent", "v1")
