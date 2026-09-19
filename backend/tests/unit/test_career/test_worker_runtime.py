from __future__ import annotations

import uuid

from app.modules.career.models import CareerReport


def _source_report() -> CareerReport:
    return CareerReport(
        career_profile_id=uuid.uuid4(),
        chart_id=uuid.uuid4(),
        generation_id=uuid.uuid4(),
        idempotency_key="source",
        version=3,
        status="ready",
        scoring_version="career-mvp-1",
        reference_version="career-ref-1",
        questionnaire_version="career-q-1",
        prompt_version="career-prompt-1",
        deterministic_payload={"contract_version": "career_interpretation_facts_v1", "marker": "immutable"},
        narrative_payload={"sections": [{"section_key": "old"}]},
        assembled_payload={"status": "ready"},
    )


def test_regeneration_report_preserves_deterministic_artifacts() -> None:
    from workers.tasks.career import build_regeneration_report_row

    source = _source_report()
    generation_id = uuid.uuid4()

    regenerated = build_regeneration_report_row(
        source=source,
        generation_id=generation_id,
        idempotency_key="retry-1",
    )

    assert regenerated.generation_id == generation_id
    assert regenerated.version == source.version + 1
    assert regenerated.status == "deterministic_ready"
    assert regenerated.deterministic_payload == source.deterministic_payload
    assert regenerated.deterministic_payload is not source.deterministic_payload
    assert regenerated.narrative_payload["sections"] == []
