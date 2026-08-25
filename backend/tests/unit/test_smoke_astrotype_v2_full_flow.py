"""Unit coverage for the local Astrotype v2 full-flow smoke helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
SMOKE_PATH = ROOT / "scripts" / "smoke" / "astrotype-v2-full-flow.py"


def _load_smoke_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("astrotype_v2_full_flow_smoke", SMOKE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _payload(*, provider: str = "deepseek", model: str = "deepseek-v4-flash") -> dict[str, Any]:
    return {
        "progress": {
            "status": "ready",
            "ready_segments": 6,
            "total_segments": 6,
            "segments": [],
        },
        "segments": [
            {"section_key": f"section_{index}", "provider": provider, "model": model, "status": "ready"}
            for index in range(6)
        ],
    }


def test_expected_segment_provider_accepts_all_real_provider_segments() -> None:
    smoke = _load_smoke_module()

    smoke.assert_expected_segment_provider(
        _payload(),
        expect_provider="deepseek",
        expect_model="deepseek-v4-flash",
    )


def test_expected_segment_provider_fails_loudly_for_bad_provider_or_model() -> None:
    smoke = _load_smoke_module()

    with pytest.raises(AssertionError, match="segment provider/model mismatch") as exc_info:
        smoke.assert_expected_segment_provider(
            _payload(provider="mock", model="mock-self-v1"),
            expect_provider="deepseek",
            expect_model="deepseek-v4-flash",
        )

    message = str(exc_info.value)
    assert "expect_provider" in message
    assert "deepseek" in message
    assert "mock" in message


def test_report_progress_gate_requires_ready_complete_segments() -> None:
    smoke = _load_smoke_module()

    smoke.assert_report_progress_ready(_payload()["progress"])

    with pytest.raises(AssertionError, match="report progress is not ready"):
        smoke.assert_report_progress_ready({"status": "failed", "ready_segments": 2, "total_segments": 6})

    with pytest.raises(AssertionError, match="segment readiness mismatch"):
        smoke.assert_report_progress_ready({"status": "ready", "ready_segments": 5, "total_segments": 6})


def test_redacted_llm_config_summary_never_contains_secret_value() -> None:
    smoke = _load_smoke_module()
    raw = {
        "llm_enabled": True,
        "llm_provider": "deepseek",
        "llm_model": "deepseek-v4-flash",
        "llm_api_key": "sk-test-secret-value",
        "llm_timeout_seconds": 180,
        "llm_max_retries": 2,
    }

    summary = smoke.redact_llm_config(raw)

    assert summary["llm_api_key_present"] is True
    assert summary["llm_api_key"] == "[REDACTED]"
    assert "sk-test-secret-value" not in str(summary)


def test_redacted_llm_config_summary_marks_missing_secret_without_printing_empty_key() -> None:
    smoke = _load_smoke_module()
    raw = {
        "llm_enabled": False,
        "llm_provider": "mock",
        "llm_model": "mock-self-v1",
        "llm_api_key": "",
        "llm_timeout_seconds": 30,
        "llm_max_retries": 2,
    }

    summary = smoke.redact_llm_config(raw)

    assert summary["llm_api_key_present"] is False
    assert summary["llm_api_key"] == ""
