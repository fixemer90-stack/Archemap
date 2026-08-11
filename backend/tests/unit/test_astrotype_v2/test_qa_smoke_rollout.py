"""QA/smoke contract tests for Astrotype v2 rollout readiness."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ROLLOUT_RUNBOOK = ROOT / ".." / "docs" / "implementation" / "astrotype-v2-qa-smoke-rollout.md"
FEATURE_PATH = ROOT / ".." / "docs" / "features" / "E16-v2-e14-qa-smoke-rollout" / "FEATURE.md"


def test_v2_smoke_bundle_reaches_complete_report_readiness_not_infra_health_only() -> None:
    from app.modules.astrotype_v2.qa_smoke import build_smoke_report_bundle_v2, validate_v2_smoke_bundle

    bundle = build_smoke_report_bundle_v2()
    result = validate_v2_smoke_bundle(bundle)

    assert result["report_status"] == "ready"
    assert result["assembled_contract"] == "natal_report_v2"
    assert result["ready_segments"] == result["total_segments"]
    assert result["checks"]["actual_report_readiness"] is True
    assert result["checks"]["not_infra_health_only"] is True


def test_v2_smoke_facts_match_report_evidence_and_infographics_are_deterministic() -> None:
    from app.modules.astrotype_v2.qa_smoke import build_smoke_report_bundle_v2, validate_v2_smoke_bundle

    result = validate_v2_smoke_bundle(build_smoke_report_bundle_v2())

    assert result["checks"]["facts_match_report_evidence_ids"] is True
    assert result["checks"]["infographics_from_deterministic_data"] is True
    assert result["evidence_fact_keys"] == sorted(result["evidence_fact_keys"])
    assert result["infographic_contract"] == "natal_infographic_data_v2"


def test_v2_smoke_has_no_excluded_typology_leakage_in_payloads_prompts_or_ui_contracts() -> None:
    from app.modules.astrotype_v2.qa_smoke import build_smoke_report_bundle_v2, validate_v2_smoke_bundle

    result = validate_v2_smoke_bundle(build_smoke_report_bundle_v2())

    assert result["checks"]["no_excluded_typology_leakage"] is True
    assert result["forbidden_hits"] == []


def test_v2_multi_client_smoke_uses_same_report_id_for_web_android_and_desktop() -> None:
    from app.modules.astrotype_v2.qa_smoke import build_smoke_report_bundle_v2, validate_v2_smoke_bundle

    result = validate_v2_smoke_bundle(build_smoke_report_bundle_v2())

    assert result["checks"]["multi_client_same_report_id"] is True
    assert set(result["client_report_ids"]) == {result["report_id"]}
    assert result["client_endpoints"]["web"].endswith(result["report_id"])
    assert result["client_endpoints"]["android_pwa"].endswith(result["report_id"])
    assert result["client_endpoints"]["desktop_optional"].endswith(result["report_id"])


def test_v2_segment_retry_recovery_and_rollout_observability_are_documented() -> None:
    from app.modules.astrotype_v2.qa_smoke import (
        build_rollout_observability_checklist,
        simulate_failed_segment_recovery_v2,
    )

    recovery = simulate_failed_segment_recovery_v2()
    checklist = build_rollout_observability_checklist()

    assert recovery["before"]["status"] == "failed"
    assert recovery["after"]["status"] == "ready"
    assert recovery["after"]["ready_segments"] == recovery["after"]["total_segments"]
    for required in [
        "llm_cost_by_segment",
        "llm_latency_by_segment",
        "llm_failures_by_segment",
        "generation_recovery_rate",
        "report_ready_latency",
        "rollback_to_previous_main_sha",
    ]:
        assert required in checklist


def test_e14_runbook_and_feature_docs_record_verified_rollout_gate() -> None:
    runbook = ROLLOUT_RUNBOOK.read_text()
    feature = FEATURE_PATH.read_text()

    assert "## Status\n\n✅ Verified" in runbook
    assert "## Status\n\n✅ Завершено" in feature
    for required in [
        "actual report readiness, not infra health only",
        "same report id across web, Android/PWA and optional desktop",
        "facts shown to user match report evidence ids",
        "infographics render from deterministic data",
        "no excluded typology appears in v2 payloads/prompts/UI",
        "segment-level retry recovery",
        "LLM cost, latency and failures by segment",
    ]:
        assert required in runbook
