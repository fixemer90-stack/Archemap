"""Executable documentation contracts for V2-E13 desktop thin-client decision."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DECISION_PATH = ROOT / ".." / "docs" / "architecture" / "astrotype-v2-desktop-thin-client-decision.md"
FEATURE_PATH = ROOT / ".." / "docs" / "features" / "E16-v2-e13-desktop-thin-client-decision" / "FEATURE.md"


def test_desktop_decision_artifact_exists_and_defers_exe_from_core_launch() -> None:
    decision = DECISION_PATH.read_text()

    assert "Decision: do not require a Windows `.exe` for Astrotype v2 core launch." in decision
    assert "web-first responsive reader" in decision
    assert "Android/PWA/Capacitor path remains ahead of desktop packaging" in decision
    assert "Desktop is optional, not a prerequisite" in decision


def test_desktop_shell_is_thin_client_over_same_v2_api_and_report_ids() -> None:
    decision = DECISION_PATH.read_text()

    for required in [
        "same backend API",
        "same account identity",
        "same report ids",
        "GET /api/v1/astrotype-v2/reports/{report_id}",
        "GET /api/v1/astrotype-v2/reports/{report_id}/progress",
        "GET /api/v1/astrotype-v2/reports/{report_id}/infographic",
        "POST /api/v1/astrotype-v2/reports/{report_id}/regenerate",
    ]:
        assert required in decision


def test_desktop_cache_contract_forbids_local_source_of_truth_and_embedded_keys() -> None:
    decision = DECISION_PATH.read_text()

    for required in [
        "No local DB is source of truth",
        "PostgreSQL remains canonical",
        "SQLite is allowed only for cache/drafts",
        "cache is disposable",
        "No production LLM key is embedded in the desktop app",
        "full offline generation is out of scope",
    ]:
        assert required in decision


def test_tauri_electron_spike_selects_tauri_first_with_electron_fallback() -> None:
    decision = DECISION_PATH.read_text()

    assert "Tauri-first" in decision
    assert "Electron fallback" in decision
    assert "frontend reuse" in decision
    assert "auth/session storage" in decision
    assert "auto-update/signing" in decision


def test_feature_doc_acceptance_is_completed_from_decision_contract() -> None:
    feature = FEATURE_PATH.read_text()

    assert "## Status\n\n✅ Завершено" in feature
    for required in [
        "- [x] `.exe` is not required for v2 core launch.",
        "- [x] If built, `.exe` uses same backend/API/report ids.",
        "- [x] No local DB is source of truth.",
        "- [x] Desktop decision does not block Android roadmap.",
        "astrotype-v2-desktop-thin-client-decision.md",
    ]:
        assert required in feature
