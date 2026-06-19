# ruff: noqa: RUF001
"""Unit tests for narrative validation and repair policy."""

from __future__ import annotations

from typing import Any, cast

from tests.unit.test_report_narratives.test_schemas import (
    make_narrative_input_payload,
    make_self_narrative_payload,
)

from app.modules.report_narratives.exceptions import NarrativeValidationError
from app.modules.report_narratives.schemas import SelfNarrative
from app.modules.report_narratives.validators import (
    choose_narrative_recovery_action,
    validate_self_narrative,
)


def make_validated_inputs() -> tuple[SelfNarrative, dict[str, Any]]:
    narrative_payload = make_self_narrative_payload()
    narrative_input = make_narrative_input_payload()

    sections = narrative_payload["sections"]
    assert isinstance(sections, list)
    existing_sections = {
        section_id: section
        for section in sections
        if isinstance(section, dict) and isinstance(section_id := section.get("id"), str)
    }

    allowed_sections = cast(
        list[object],
        cast(dict[str, Any], narrative_input["product_boundaries"])["allowed_sections"],
    )
    assert isinstance(allowed_sections, list)
    narrative_payload["sections"] = [
        existing_sections.get(
            section_id,
            {
                "id": section_id,
                "title": f"Раздел {section_id}",
                "body": f"Краткое содержание для раздела {section_id}.",
                "bullets": [],
                "evidence_notes": [],
            },
        )
        for section_id in allowed_sections
        if isinstance(section_id, str)
    ]

    narrative = SelfNarrative.model_validate(narrative_payload)
    return narrative, narrative_input


class TestValidateSelfNarrative:
    def test_accepts_valid_narrative(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()

        errors = validate_self_narrative(narrative, narrative_input_payload)

        assert errors == []

    def test_rejects_unknown_evidence_ref(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()
        narrative.sections[0].evidence_notes[0].fact_ids = ["unknown_fact"]

        errors = validate_self_narrative(narrative, narrative_input_payload)

        assert any(error.code == "unknown_evidence_ref" for error in errors)

    def test_rejects_unknown_limitation_evidence_ref(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()
        narrative.sections[0].evidence_notes[0].limitation = "Контекст может смягчать вывод."
        narrative.sections[0].evidence_notes[0].limitation_fact_ids = ["unknown_limitation_fact"]

        errors = validate_self_narrative(narrative, narrative_input_payload)

        assert any(error.code == "unknown_evidence_ref" for error in errors)
        assert any("limitation_fact_ids" in error.location for error in errors)

    def test_rejects_key_section_without_evidence_notes(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()
        narrative.sections[0].evidence_notes = []

        errors = validate_self_narrative(narrative, narrative_input_payload)

        assert any(error.code == "missing_section_evidence" for error in errors)

    def test_rejects_dominant_without_evidence_refs(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()
        narrative.dominants[0].evidence_ids = []

        errors = validate_self_narrative(narrative, narrative_input_payload)

        assert any(error.code == "dominant_missing_evidence" for error in errors)

    def test_rejects_inner_mechanism_outside_three_to_five_steps(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()
        narrative.inner_mechanism.steps = narrative.inner_mechanism.steps[:2]

        errors = validate_self_narrative(narrative, narrative_input_payload)

        assert any(error.code == "invalid_inner_mechanism" for error in errors)

    def test_rejects_house_scenario_without_manifestation_shadow_or_evidence(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()
        narrative.house_scenarios[0].manifestation = ""
        narrative.house_scenarios[0].shadow = ""
        narrative.house_scenarios[0].evidence_ids = []

        errors = validate_self_narrative(narrative, narrative_input_payload)

        assert any(error.code == "invalid_house_scenario" for error in errors)

    def test_rejects_house_scenario_unknown_evidence_ref(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()
        narrative.house_scenarios[0].evidence_ids = ["unknown_house_fact"]

        errors = validate_self_narrative(narrative, narrative_input_payload)

        assert any(error.code == "unknown_evidence_ref" for error in errors)

    def test_rejects_missing_career_cta(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()
        invalid_narrative = narrative.model_copy(update={"career_cta": None})

        errors = validate_self_narrative(invalid_narrative, narrative_input_payload)

        assert any(error.code == "missing_career_cta" for error in errors)

    def test_rejects_career_deep_dive_inside_self_sections(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()
        narrative.sections[0].body = "Вам подойдут профессии в менеджменте и денежная стратегия роста."

        errors = validate_self_narrative(narrative, narrative_input_payload)

        assert any(error.code == "career_boundary_violation" for error in errors)

    def test_rejects_forbidden_fatalistic_medical_and_graphic_language(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()
        narrative.sections[-1].body = "У вас неизбежно будет диагноз, а близость сводится к половому акту."

        errors = validate_self_narrative(narrative, narrative_input_payload)

        assert any(error.code == "forbidden_language" for error in errors)

    def test_rejects_unknown_astrology_or_socionics_terms(self) -> None:
        narrative, narrative_input_payload = make_validated_inputs()
        narrative.hero.body = "Ваш Марс в 10 доме и тип ЛСИ создают жёсткую карьерную линию."

        errors = validate_self_narrative(narrative, narrative_input_payload)

        assert any(error.code == "unsupported_domain_term" for error in errors)


class TestNarrativeRecoveryPolicy:
    def test_uses_single_repair_attempt_for_recoverable_errors(self) -> None:
        action = choose_narrative_recovery_action(
            errors=[
                NarrativeValidationError(
                    code="unknown_evidence_ref",
                    message="Unknown fact id.",
                    location="sections[0].evidence_notes[0]",
                    recoverable=True,
                )
            ],
            repair_attempts_used=0,
            llm_available=True,
        )

        assert action == "repair"

    def test_falls_back_after_repair_budget_is_spent(self) -> None:
        action = choose_narrative_recovery_action(
            errors=[
                NarrativeValidationError(
                    code="unknown_evidence_ref",
                    message="Unknown fact id.",
                    location="sections[0].evidence_notes[0]",
                    recoverable=True,
                )
            ],
            repair_attempts_used=1,
            llm_available=True,
        )

        assert action == "fallback"

    def test_marks_nonrecoverable_output_as_failed(self) -> None:
        action = choose_narrative_recovery_action(
            errors=[
                NarrativeValidationError(
                    code="forbidden_language",
                    message="Forbidden language detected.",
                    location="sections[7].body",
                    recoverable=False,
                )
            ],
            repair_attempts_used=0,
            llm_available=True,
        )

        assert action == "narrative_failed"

    def test_falls_back_when_llm_is_unavailable(self) -> None:
        action = choose_narrative_recovery_action(
            errors=[],
            repair_attempts_used=0,
            llm_available=False,
        )

        assert action == "fallback"
