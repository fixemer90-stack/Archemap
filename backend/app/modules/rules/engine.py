"""Rule engine — deterministic evaluation of rules against a FeatureVector.

Scoring formula:
    contrib_r = w_r * match_r * q_input * q_rule
    score_k = clamp((bias_k + sum(support) - lambda * sum(counter)) / max_possible, 0, 1)

Confidence formula:
    confidence = 0.35*q_input + 0.30*q_coverage + 0.20*q_margin + 0.15*q_consistency
"""

from __future__ import annotations

import operator
from typing import Any

from app.chart_engine.features import FeatureVector
from app.modules.rules.types import (
    ArchetypeRule,
    BasisItem,
    Claim,
    Condition,
    ConditionGroup,
    ConditionOp,
    ConfidenceResult,
    InterpretationResult,
    RuleEvaluation,
    RuleSet,
)

# Operator dispatch
_OPERATORS = {
    ConditionOp.GTE: operator.ge,
    ConditionOp.LTE: operator.le,
    ConditionOp.GT: operator.gt,
    ConditionOp.LT: operator.lt,
    ConditionOp.EQ: operator.eq,
    ConditionOp.NEQ: operator.ne,
}

RULE_ENGINE_VERSION = "0.1.1"


def interpret(
    features: FeatureVector,
    ruleset: RuleSet,
    mode: str = "full",
) -> InterpretationResult:
    """Run rule engine on a FeatureVector.

    Args:
        features: Extracted feature vector
        ruleset: Loaded ruleset
        mode: "full" or "preview" (2-3 claims max)

    Returns:
        InterpretationResult with scored archetypes and evidence trail
    """
    facts = _build_facts(features)

    # Evaluate all rules
    evaluations = [_evaluate_rule(arch, facts, ruleset) for arch in ruleset.archetypes]

    # Aggregate scores
    archetype_scores = _aggregate_scores(evaluations, ruleset)

    # Find primary archetype
    if not archetype_scores:
        return InterpretationResult(
            product=ruleset.product,
            primary_archetype="Неопределённый",
            primary_score=0.0,
            primary_confidence=_zero_confidence(),
            quality_warning=_quality_warning(features),
            provenance={
                "ruleset_version": f"{ruleset.product}-{ruleset.version}",
                "engine_version": RULE_ENGINE_VERSION,
            },
        )

    primary_id = max(archetype_scores, key=archetype_scores.get)  # type: ignore[arg-type]
    primary_score = archetype_scores[primary_id]

    # Build claims for activated archetypes
    conf_config = ruleset.confidence_config
    claims: list[Claim] = []

    for eval_result in evaluations:
        if not eval_result.activated:
            continue

        arch = next(a for a in ruleset.archetypes if a.archetype_id == eval_result.archetype_id)
        score = archetype_scores.get(eval_result.archetype_id, 0.0)

        confidence = _compute_confidence(
            eval_result=eval_result,
            all_evaluations=evaluations,
            facts=facts,
            conf_config=conf_config,
        )

        basis = _build_basis(eval_result, facts)
        counter = _build_counter_evidence(eval_result, evaluations, facts)

        claim = Claim(
            claim_id=f"archetype.{eval_result.archetype_id}",
            section="strengths",
            archetype=arch.name,
            score=round(score, 3),
            confidence=confidence,
            message=arch.description,
            basis=basis,
            counter_evidence=counter,
            provenance={"ruleset_version": f"{ruleset.product}-{ruleset.version}"},
        )
        claims.append(claim)

    # Sort by score
    claims.sort(key=lambda c: c.score, reverse=True)

    # Apply mode limits
    if mode == "preview":
        claims = claims[:3]

    # Primary archetype confidence
    primary_eval = next(
        (e for e in evaluations if e.archetype_id == primary_id),
        None,
    )
    primary_confidence = (
        _compute_confidence(primary_eval, evaluations, facts, conf_config) if primary_eval else _zero_confidence()
    )

    primary_arch = next(
        (a for a in ruleset.archetypes if a.archetype_id == primary_id),
        None,
    )

    return InterpretationResult(
        product=ruleset.product,
        primary_archetype=primary_arch.name if primary_arch else primary_id,
        primary_score=round(primary_score, 3),
        primary_confidence=primary_confidence,
        claims=claims,
        all_archetype_scores={k: round(v, 3) for k, v in sorted(archetype_scores.items(), key=lambda x: -x[1])},
        quality_warning=_quality_warning(features),
        provenance={
            "ruleset_version": f"{ruleset.product}-{ruleset.version}",
            "engine_version": RULE_ENGINE_VERSION,
        },
    )


def _build_facts(features: FeatureVector) -> dict[str, Any]:
    """Build fact dictionary from FeatureVector."""
    facts: dict[str, Any] = {
        "feature.fire": features.fire,
        "feature.earth": features.earth,
        "feature.air": features.air,
        "feature.water": features.water,
        "feature.cardinal": features.cardinal,
        "feature.fixed": features.fixed,
        "feature.mutable": features.mutable,
        "feature.sun_moon_balance": features.sun_moon_balance,
        "quality.has_birth_time": features.has_birth_time,
        "quality.birth_time_quality": features.birth_time_quality,
    }
    for house_num, emphasis in features.house_emphasis.items():
        facts[f"feature.house_emphasis.{house_num}"] = emphasis
    return facts


def _evaluate_rule(archetype: ArchetypeRule, facts: dict[str, Any], ruleset: RuleSet) -> RuleEvaluation:
    """Evaluate a single archetype rule."""
    match_score, matched, unmatched = _evaluate_conditions(archetype.conditions, facts)

    activated = match_score > 0.0
    contributions: dict[str, float] = {}

    if activated:
        q_input = facts.get("quality.birth_time_quality", 1.0)
        q_rule = ruleset.scoring.get("default_q_rule", 1.0)
        w_r = ruleset.scoring.get("default_weight", 1.0)

        for effect_key, weight in archetype.effects.items():
            contrib = w_r * match_score * q_input * q_rule * weight
            contributions[effect_key] = round(contrib, 4)

    conf_delta = 0.0
    for adj in archetype.confidence_adjustments:
        if _check_condition(adj.when, facts):
            conf_delta += adj.delta

    return RuleEvaluation(
        rule_id=f"{ruleset.product}.{archetype.archetype_id}.{ruleset.version}",
        archetype_id=archetype.archetype_id,
        activated=activated,
        match_score=round(match_score, 4),
        contributions=contributions,
        confidence_delta=conf_delta,
        matched_facts=matched,
        unmatched_facts=unmatched,
    )


def _evaluate_conditions(
    group: ConditionGroup,
    facts: dict[str, Any],
) -> tuple[float, list[tuple[str, Any, Any]], list[tuple[str, Any, Any]]]:
    """Evaluate condition group, return (score, matched_facts, unmatched_facts)."""
    matched: list[tuple[str, Any, Any]] = []
    unmatched: list[tuple[str, Any, Any]] = []

    if not group.conditions:
        return 1.0, matched, unmatched

    results = []
    for cond in group.conditions:
        if isinstance(cond, ConditionGroup):
            sub_score, sub_m, sub_u = _evaluate_conditions(cond, facts)
            results.append(sub_score)
            matched.extend(sub_m)
            unmatched.extend(sub_u)
        else:
            actual = facts.get(cond.fact)
            if actual is None:
                results.append(0.0)
                unmatched.append((cond.fact, cond.value, None))
            elif _check_condition(cond, facts):
                results.append(_condition_match_score(cond, actual))
                matched.append((cond.fact, cond.value, actual))
            else:
                results.append(0.0)
                unmatched.append((cond.fact, cond.value, actual))

    if group.conjunction == "all":
        score = min(results) if results else 0.0
    elif group.conjunction == "any":
        score = max(results) if results else 0.0
    elif group.conjunction == "not":
        score = 1.0 - max(results) if results else 1.0
    else:
        score = min(results) if results else 0.0

    return score, matched, unmatched


def _check_condition(condition: Condition, facts: dict[str, Any]) -> bool:
    """Check a single condition against facts."""
    actual = facts.get(condition.fact)
    if actual is None:
        return False

    op_func = _OPERATORS.get(condition.op)
    if op_func:
        return bool(op_func(actual, condition.value))

    if condition.op == ConditionOp.BETWEEN:
        return bool(condition.value <= actual <= (condition.value_upper or condition.value))
    return False


def _condition_match_score(condition: Condition, actual: Any) -> float:
    """Return a graded 0..1 match strength for an already matched condition.

    Threshold checks still decide whether a rule activates. Once activated, the
    contribution should reflect the strength of the underlying normalized fact;
    otherwise every matched archetype keeps the YAML effect weight unchanged
    (for example 0.25), which makes the typage/rating look like flat 25% rows.
    """
    if condition.op in {ConditionOp.EQ, ConditionOp.NEQ, ConditionOp.IN, ConditionOp.NOT_IN}:
        return 1.0

    try:
        actual_float = float(actual)
    except (TypeError, ValueError):
        return 1.0

    actual_float = max(0.0, min(1.0, actual_float))

    if condition.op in {ConditionOp.GTE, ConditionOp.GT}:
        return actual_float
    if condition.op in {ConditionOp.LTE, ConditionOp.LT}:
        return 1.0 - actual_float
    if condition.op == ConditionOp.BETWEEN:
        try:
            lower = float(condition.value)
            upper = float(condition.value_upper if condition.value_upper is not None else condition.value)
        except (TypeError, ValueError):
            return actual_float
        if upper <= lower:
            return actual_float
        midpoint = (lower + upper) / 2
        half_width = (upper - lower) / 2
        distance = abs(actual_float - midpoint)
        return max(0.0, min(1.0, 1.0 - distance / half_width))

    return 1.0


def _aggregate_scores(evaluations: list[RuleEvaluation], ruleset: RuleSet) -> dict[str, float]:
    """Aggregate rule evaluations into archetype scores."""
    bias = ruleset.scoring.get("default_bias", 0.0)
    lam = ruleset.scoring.get("counter_penalty_lambda", 0.30)
    max_possible = ruleset.scoring.get("max_possible_score", 1.0)

    support: dict[str, float] = {}
    counter: dict[str, float] = {}

    for ev in evaluations:
        if not ev.activated:
            continue
        for key, contrib in ev.contributions.items():
            if key.startswith("archetype."):
                aid = key[len("archetype.") :]
                support[aid] = support.get(aid, 0.0) + contrib

    # Counter-evidence: if a counter-rule is activated, subtract its contribution
    for ev in evaluations:
        if not ev.activated:
            continue
        arch = next((a for a in ruleset.archetypes if a.archetype_id == ev.archetype_id), None)
        if not arch:
            continue
        for counter_id in arch.counter_rules:
            counter_eval = next((e for e in evaluations if e.archetype_id == counter_id and e.activated), None)
            if counter_eval:
                for key, contrib in counter_eval.contributions.items():
                    if key.startswith("archetype."):
                        counter[ev.archetype_id] = counter.get(ev.archetype_id, 0.0) + contrib

    scores: dict[str, float] = {}
    for aid in set(list(support.keys()) + list(counter.keys())):
        s = support.get(aid, 0.0)
        c = counter.get(aid, 0.0)
        raw = (bias + s - lam * c) / max_possible
        scores[aid] = max(0.0, min(1.0, raw))

    return scores


def _compute_confidence(
    eval_result: RuleEvaluation | None,
    all_evaluations: list[RuleEvaluation],
    facts: dict[str, Any],
    conf_config: dict[str, Any],
) -> ConfidenceResult:
    """Compute confidence using 4-factor model."""
    weights = conf_config.get(
        "weights",
        {
            "q_input": 0.35,
            "q_coverage": 0.30,
            "q_margin": 0.20,
            "q_consistency": 0.15,
        },
    )
    thresholds = conf_config.get(
        "thresholds",
        {
            "good_input": 0.70,
            "low_coverage": 0.30,
            "high_contradiction": 0.40,
            "low_margin": 0.10,
        },
    )
    labels = conf_config.get(
        "labels",
        {
            "high": [0.80, 1.0],
            "medium_high": [0.60, 0.80],
            "medium": [0.40, 0.60],
            "medium_low": [0.20, 0.40],
            "low": [0.0, 0.20],
        },
    )

    q_input = facts.get("quality.birth_time_quality", 1.0)

    activated_count = sum(1 for e in all_evaluations if e.activated)
    total_count = len(all_evaluations) or 1
    q_coverage = activated_count / total_count

    if eval_result:
        this_score = eval_result.match_score
        other_scores = [e.match_score for e in all_evaluations if e.archetype_id != eval_result.archetype_id]
        best_other = max(other_scores) if other_scores else 0.0
        q_margin = max(0.0, this_score - best_other)

        contradicted = sum(1 for e in all_evaluations if e.activated and e.archetype_id != eval_result.archetype_id)
        q_consistency = max(0.0, 1.0 - contradicted / max(total_count, 1))
    else:
        q_margin = 0.0
        q_consistency = 1.0

    raw = (
        weights.get("q_input", 0.35) * q_input
        + weights.get("q_coverage", 0.30) * q_coverage
        + weights.get("q_margin", 0.20) * q_margin
        + weights.get("q_consistency", 0.15) * q_consistency
    )

    if eval_result:
        raw += eval_result.confidence_delta
    raw = max(0.0, min(1.0, raw))

    # Determine label
    label = "medium"
    for lbl, (lo, hi) in labels.items():
        if lo <= raw < hi or (lbl == "high" and raw >= hi):
            label = lbl
            break

    # Reason codes
    codes: list[str] = []
    if q_input >= thresholds.get("good_input", 0.70):
        codes.append("GOOD_INPUT")
    elif q_input < 0.5:
        codes.append("MISSING_BIRTH_TIME")

    if q_coverage < thresholds.get("low_coverage", 0.30):
        codes.append("LOW_RULE_COVERAGE")
    else:
        codes.append("HIGH_COVERAGE")

    if q_margin >= thresholds.get("low_margin", 0.10):
        codes.append("GOOD_MARGIN")
    else:
        codes.append("LOW_MARGIN")

    return ConfidenceResult(
        value=round(raw, 3),
        label=label,
        reason_codes=codes,
        factors={
            "q_input": round(q_input, 3),
            "q_coverage": round(q_coverage, 3),
            "q_margin": round(q_margin, 3),
            "q_consistency": round(q_consistency, 3),
        },
    )


def _build_basis(eval_result: RuleEvaluation, facts: dict[str, Any]) -> list[BasisItem]:
    """Build evidence basis from matched facts."""
    return [
        BasisItem(
            rule_id=eval_result.rule_id,
            feature=fact_name,
            value=float(actual) if actual is not None else 0.0,
            contribution=eval_result.contributions.get(f"archetype.{eval_result.archetype_id}", 0.0),
        )
        for fact_name, _expected, actual in eval_result.matched_facts
    ]


def _build_counter_evidence(
    eval_result: RuleEvaluation,
    all_evaluations: list[RuleEvaluation],
    facts: dict[str, Any],
) -> list[BasisItem]:
    """Build counter-evidence from activated counter-rules."""
    result: list[BasisItem] = []
    # Find which rules counter this one
    # (we need access to the ruleset for this, so we approximate)
    for other in all_evaluations:
        if other.archetype_id != eval_result.archetype_id and other.activated:
            for fact_name, _expected, actual in other.matched_facts:
                result.append(
                    BasisItem(
                        rule_id=other.rule_id,
                        feature=fact_name,
                        value=float(actual) if actual is not None else 0.0,
                        contribution=-other.contributions.get(f"archetype.{other.archetype_id}", 0.0),
                    )
                )
    return result


def _quality_warning(features: FeatureVector) -> str | None:
    """Generate quality warning based on input data."""
    if not features.has_birth_time:
        return "Время рождения неизвестно. Точность прогноза снижена."
    if features.birth_time_quality < 0.5:
        return "Время рождения приблизительное. Некоторые детали могут быть неточны."
    return None


def _zero_confidence() -> ConfidenceResult:
    """Return zero confidence."""
    return ConfidenceResult(
        value=0.0,
        label="low",
        reason_codes=["LOW_RULE_COVERAGE"],
        factors={
            "q_input": 0.0,
            "q_coverage": 0.0,
            "q_margin": 0.0,
            "q_consistency": 0.0,
        },
    )
