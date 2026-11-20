"""Career degraded completion must not masquerade as active paid work."""

from scripts import child_staging_probe as probe


def test_career_partial_failure_is_settled_but_active_and_unknown_are_not() -> None:
    row = {"status": "partial_failure", "diagnostics": {"stage": "complete", "report_status": "partial_failure"}}
    assert probe.settled("career_generations", row)
    assert not probe.settled("career_generations", {"status": "generating_sections", "diagnostics": {}})
    assert not probe.settled(
        "career_generations", {"status": "partial_failure", "diagnostics": {"error_code": "provider_outcome_unknown"}}
    )
