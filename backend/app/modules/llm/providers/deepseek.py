# ruff: noqa: RUF001
# mypy: ignore-errors
"""DeepSeek adapter behind the generic LLM provider boundary."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.modules.llm.exceptions import (
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMTimeoutError,
)
from app.modules.report_narratives.schemas import NarrativeInput

StructuredSchemaT = TypeVar("StructuredSchemaT", bound=BaseModel)


class DeepSeekProvider:
    """Minimal DeepSeek provider using the chat completions HTTP API."""

    supports_staged_pipeline = True

    def __init__(self, *, api_key: str, model: str, timeout_seconds: int, max_retries: int) -> None:
        self._api_key = api_key
        self.model_name = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def generate_structured(
        self,
        *,
        prompt: str,
        narrative_input: NarrativeInput,
        schema: type[StructuredSchemaT],
    ) -> StructuredSchemaT:
        request_payload = {
            "model": self.model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": narrative_input.model_dump_json(indent=2)},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        response: httpx.Response | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        "https://api.deepseek.com/chat/completions",
                        headers=headers,
                        json=request_payload,
                    )
                    response.raise_for_status()
                break
            except httpx.TimeoutException as exc:
                if attempt >= self.max_retries:
                    raise LLMTimeoutError("LLM provider request timed out", code="llm_timeout") from exc
                await asyncio.sleep(min(2**attempt, 5))
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if attempt >= self.max_retries or status_code < 500:
                    raise LLMProviderUnavailableError(
                        f"LLM provider request failed with status {status_code}",
                        code="llm_provider_unavailable",
                    ) from exc
                await asyncio.sleep(min(2**attempt, 5))
            except httpx.HTTPError as exc:
                if attempt >= self.max_retries:
                    raise LLMProviderUnavailableError(
                        "LLM provider request failed",
                        code="llm_provider_unavailable",
                    ) from exc
                await asyncio.sleep(min(2**attempt, 5))

        if response is None:
            raise LLMProviderUnavailableError(
                "LLM provider request failed",
                code="llm_provider_unavailable",
            )

        return self._parse_response(response.json(), schema, narrative_input)

    def _parse_response(
        self,
        response_payload: dict[str, Any],
        schema: type[StructuredSchemaT],
        narrative_input: Any | None = None,
    ) -> StructuredSchemaT:
        try:
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMInvalidResponseError(
                "LLM provider response did not contain structured content",
                code="llm_invalid_response",
            ) from exc

        try:
            parsed_content = _load_structured_json_content(content)
        except json.JSONDecodeError as exc:
            raise LLMInvalidResponseError(
                "LLM provider returned non-JSON content",
                code="llm_invalid_response",
            ) from exc

        if isinstance(parsed_content, list) and schema.__name__ == "ReportSegmentOutputV2":
            parsed_content = _normalize_report_segment_output_v2_shape(
                {"sections": parsed_content},
                narrative_input,
            )
        elif isinstance(parsed_content, dict):
            parsed_content = _normalize_structured_shape(parsed_content, schema.__name__, narrative_input)

        try:
            return schema.model_validate(parsed_content)
        except ValidationError as exc:
            diagnostics = _schema_validation_diagnostics(parsed_content, schema.__name__, exc)
            raise LLMInvalidResponseError(
                f"LLM provider returned JSON that does not match schema: {diagnostics}",
                code="llm_invalid_response",
            ) from exc


def _schema_validation_diagnostics(payload: Any, schema_name: str, exc: ValidationError) -> str:
    if isinstance(payload, dict):
        shape: dict[str, Any] = {
            "schema": schema_name,
            "type": "dict",
            "keys": sorted(str(key) for key in payload),
        }
        for key in ("section", "segment", "output", "sections"):
            value = payload.get(key)
            if isinstance(value, dict):
                shape[f"{key}_keys"] = sorted(str(nested_key) for nested_key in value)
            elif isinstance(value, list):
                shape[f"{key}_type"] = "list"
                shape[f"{key}_len"] = len(value)
                first = next((item for item in value if isinstance(item, dict)), None)
                if first is not None:
                    shape[f"{key}_first_keys"] = sorted(str(nested_key) for nested_key in first)
    elif isinstance(payload, list):
        shape = {"schema": schema_name, "type": "list", "len": len(payload)}
        first = next((item for item in payload if isinstance(item, dict)), None)
        if first is not None:
            shape["first_keys"] = sorted(str(key) for key in first)
    else:
        shape = {"schema": schema_name, "type": type(payload).__name__}
    shape["errors"] = [
        {"loc": list(error.get("loc", ())), "type": error.get("type")}
        for error in exc.errors(include_url=False, include_context=False, include_input=False)
    ]
    return json.dumps(shape, ensure_ascii=False, sort_keys=True)


def _load_structured_json_content(content: str) -> Any:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        stripped = content.strip()
        fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
        if fence_match is not None:
            return json.loads(fence_match.group(1))
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return json.loads(stripped[start : end + 1])
        raise


_SECTION_TITLES: dict[str, str] = {
    "main_formula": "Главная формула",
    "world_perception": "Как вы воспринимаете мир",
    "emotions_and_communication": "Эмоции и общение",
    "strengths": "Сильные стороны",
    "vulnerabilities": "Уязвимости",
    "relationships": "Отношения и близость",
    "sexuality": "Сексуальность",
    "development": "Направление развития",
}


def _normalize_structured_shape(
    payload: dict[str, Any],
    schema_name: str,
    narrative_input: NarrativeInput | None,
) -> dict[str, Any]:
    if schema_name == "SelfNarrative":
        return _normalize_self_narrative_shape(payload)
    if schema_name == "NarrativePlan":
        return _normalize_narrative_plan_shape(payload, narrative_input)
    if schema_name == "IdentitySectionOutput":
        return _normalize_identity_section_shape(payload, narrative_input)
    if schema_name == "EmotionalSectionOutput":
        return _normalize_emotional_section_shape(payload, narrative_input)
    if schema_name == "RelationshipSectionOutput":
        return _normalize_relationship_section_shape(payload, narrative_input)
    if schema_name == "DevelopmentSectionOutput":
        return _normalize_development_section_shape(payload, narrative_input)
    if schema_name == "HouseScenariosSectionOutput":
        return _normalize_house_scenarios_section_shape(payload, narrative_input)
    if schema_name == "ReportSegmentOutputV2":
        return _normalize_report_segment_output_v2_shape(payload, narrative_input)
    if schema_name == "AssemblyCheck" and "assembly_check" in payload and isinstance(payload["assembly_check"], dict):
        return payload["assembly_check"]
    return payload


def _normalize_report_segment_output_v2_shape(
    payload: dict[str, Any], section_input: Any | None = None
) -> dict[str, Any]:
    source = _first_mapping(
        payload,
        (
            "sections",
            "report_segment_output_v2",
            "report_segment_output",
            "segment_output",
            "segment",
            "section",
            "output",
        ),
    )
    normalized = dict(source)
    normalized.setdefault("contract_version", "report_segment_output_v2")
    if section_input is not None:
        normalized.setdefault("section_id", getattr(section_input, "section_id", None))
        normalized.setdefault("title", getattr(section_input, "section_title", None))
    if "body" not in normalized:
        body = _coerce_body_text(normalized)
        if body:
            normalized["body"] = body
    covered_theme_ids = _unique_strings(
        normalized.get("theme_ids")
        or normalized.get("covered_themes")
        or normalized.get("covered_theme_ids")
        or []
    )
    if not covered_theme_ids and section_input is not None:
        covered_theme_ids = [str(theme.id) for theme in getattr(section_input, "owned_themes", [])]
    if not covered_theme_ids and section_input is not None:
        covered_theme_ids = [str(theme.id) for theme in getattr(section_input, "reference_themes", [])]
    normalized["covered_theme_ids"] = covered_theme_ids

    evidence_ids = _unique_strings(
        normalized.get("evidence")
        or normalized.get("evidence_ids")
        or normalized.get("source_evidence_ids")
        or []
    )
    if not evidence_ids and section_input is not None:
        evidence_ids = [str(item) for item in getattr(section_input, "evidence_ids", [])]
    normalized["evidence_ids"] = evidence_ids
    normalized.setdefault("continuation_complete", True)
    normalized.setdefault("continuation_cursor", None)
    normalized["notes"] = _coerce_notes(normalized.get("notes"))
    return normalized


def _first_mapping(payload: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            first_mapping = next((item for item in value if isinstance(item, dict)), None)
            if first_mapping is not None:
                return first_mapping
    return payload


def _coerce_body_text(payload: dict[str, Any]) -> str:
    for key in ("body", "body_prose", "content", "text", "prose", "section_body", "narrative"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    paragraphs = payload.get("paragraphs")
    if isinstance(paragraphs, list):
        parts = [item.strip() for item in paragraphs if isinstance(item, str) and item.strip()]
        if parts:
            return "\n\n".join(parts)
    return ""


def _coerce_notes(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_narrative_plan_shape(
    payload: dict[str, Any],
    narrative_input: NarrativeInput | None,
) -> dict[str, Any]:
    if {"prompt_version", "sections", "global_guardrails", "assembly_notes"} <= set(payload):
        return payload

    source = payload.get("narrative_plan") if isinstance(payload.get("narrative_plan"), dict) else payload
    sections_source = source.get("sections") if isinstance(source.get("sections"), dict) else {}

    def build_section(section_id: str, legacy_ids: list[str], fallback_title: str) -> dict[str, Any]:
        legacy_sections = [
            sections_source.get(legacy_id)
            for legacy_id in legacy_ids
            if isinstance(sections_source.get(legacy_id), dict)
        ]
        evidence_ids = _unique_strings(
            evidence_id for section in legacy_sections for evidence_id in section.get("evidence_ids", [])
        )
        focus_parts = [
            _coerce_text(section.get("description") or section.get("focus") or section.get("summary"))
            for section in legacy_sections
        ]
        focus = " ".join(part for part in focus_parts if part).strip()
        title = next(
            (_coerce_text(section.get("title")) for section in legacy_sections if _coerce_text(section.get("title"))),
            fallback_title,
        )
        return {
            "section_id": section_id,
            "title": title,
            "required_evidence_ids": evidence_ids or ["legacy_plan_fallback"],
            "focus": focus or fallback_title,
        }

    return {
        "prompt_version": "self_plan_v1",
        "sections": [
            build_section(
                "identity", ["main_formula", "world_perception", "strengths"], "Идентичность и внутренняя опора"
            ),
            build_section(
                "emotional",
                ["emotions_and_communication", "vulnerabilities"],
                "Эмоциональная динамика и уязвимости",
            ),
            build_section("relationships", ["relationships", "sexuality"], "Отношения, близость и сексуальность"),
            build_section("development", ["development"], "Развитие и интеграция напряжения"),
            build_section("house_scenarios", ["house_scenarios"], "Жизненные сценарии по домам"),
        ],
        "global_guardrails": [
            "Использовать только evidence-backed выводы.",
            "Не уходить в Career и не использовать диагностический язык.",
            "Сохранять narrative-first тон без generic horoscope prose.",
        ],
        "assembly_notes": _coerce_text(source.get("assembly_notes"))
        or "Собрать единый Self narrative из пяти staged секций без противоречий и дублирования.",
    }


def _normalize_identity_section_shape(
    payload: dict[str, Any],
    narrative_input: NarrativeInput | None,
) -> dict[str, Any]:
    if {"section_id", "title", "paragraphs", "evidence_ids", "covered_pattern_ids"} <= set(payload):
        return payload
    raw_source = payload.get("identity_section")
    source: dict[str, Any] = raw_source if isinstance(raw_source, dict) else payload
    if (
        "identity" not in source
        and "identity_synthesis" not in source
        and "identity_summary" not in source
        and "summary" not in source
    ):
        return payload
    evidence_ids = _unique_strings(source.get("evidence_ids", [])) or _fallback_evidence_ids(narrative_input)
    component_paragraphs = [
        _coerce_text(component.get("contribution"))
        for component in source.get("components", [])
        if isinstance(component, dict)
    ]
    paragraphs = [
        part
        for part in [
            _coerce_text(source.get("identity")),
            _coerce_text(source.get("identity_synthesis") or source.get("identity_summary") or source.get("summary")),
            _coerce_text(source.get("worldview")),
            _coerce_text(source.get("position")),
            *component_paragraphs[:2],
        ]
        if part
    ]
    return {
        "section_id": "identity",
        "title": _coerce_text(source.get("title")) or "Идентичность и опора личности",
        "paragraphs": paragraphs or ["Идентичность требует дополнительной сборки."],
        "evidence_ids": evidence_ids,
        "covered_pattern_ids": _unique_strings(source.get("covered_pattern_ids", [])) or evidence_ids,
    }


def _normalize_emotional_section_shape(
    payload: dict[str, Any],
    narrative_input: NarrativeInput | None,
) -> dict[str, Any]:
    if {"section_id", "title", "paragraphs", "evidence_ids", "covered_pattern_ids"} <= set(payload):
        return payload
    if not any(
        key in payload
        for key in [
            "emotional_processing_summary",
            "emotional_processing",
            "emotional_expression",
            "emotional_regulation",
            "chart_dynamics",
            "contradictions",
            "maturity_levels",
        ]
    ):
        return payload
    chart_dynamics = payload.get("chart_dynamics") if isinstance(payload.get("chart_dynamics"), list) else []
    contradictions = payload.get("contradictions") if isinstance(payload.get("contradictions"), list) else []
    maturity_levels = payload.get("maturity_levels") if isinstance(payload.get("maturity_levels"), dict) else {}
    paragraphs = [
        _coerce_text(payload.get("emotional_processing_summary") or payload.get("emotional_processing")),
        _coerce_text(payload.get("emotional_expression")),
        _coerce_text(payload.get("emotional_regulation")),
        _coerce_text((contradictions[0] if contradictions else {}).get("manifestation")),
        _coerce_text(
            (maturity_levels.get("high") if isinstance(maturity_levels.get("high"), dict) else {}).get("body")
        ),
    ]
    combined_items = list(chart_dynamics) + list(contradictions)
    evidence_ids = _unique_strings(
        evidence_id for item in combined_items if isinstance(item, dict) for evidence_id in item.get("evidence_ids", [])
    )
    covered_pattern_ids = _unique_strings(item.get("id") for item in combined_items if isinstance(item, dict))
    return {
        "section_id": "emotional",
        "title": "Эмоциональная динамика",
        "paragraphs": [part for part in paragraphs if part]
        or ["Эмоциональная динамика требует дополнительной сборки."],
        "evidence_ids": evidence_ids or covered_pattern_ids or _fallback_evidence_ids(narrative_input),
        "covered_pattern_ids": covered_pattern_ids or evidence_ids or _fallback_evidence_ids(narrative_input),
    }


def _normalize_relationship_section_shape(
    payload: dict[str, Any],
    narrative_input: NarrativeInput | None,
) -> dict[str, Any]:
    if {"section_id", "title", "paragraphs", "evidence_ids", "covered_pattern_ids"} <= set(payload):
        return payload
    wrapped = (
        payload.get("relationships_sexuality") if isinstance(payload.get("relationships_sexuality"), dict) else None
    )
    if wrapped is not None:
        content_items = wrapped.get("content") if isinstance(wrapped.get("content"), list) else []
        if content_items:
            paragraphs = [
                " ".join(
                    part
                    for part in [
                        _coerce_text(item.get("psychological_mechanism") or item.get("mechanism")),
                        _coerce_text(
                            item.get("life_manifestation") or item.get("manifestation") or item.get("tension")
                        ),
                        _coerce_text(item.get("risk") or item.get("compensation") or item.get("mature_expression")),
                    ]
                    if part
                )
                for item in content_items
                if isinstance(item, dict)
            ]
            evidence_ids = _unique_strings(
                evidence_id
                for item in content_items
                if isinstance(item, dict)
                for evidence_id in item.get("evidence_ids", [])
            ) or _fallback_evidence_ids(narrative_input)
            covered_pattern_ids = (
                _unique_strings(item.get("source") for item in content_items if isinstance(item, dict)) or evidence_ids
            )
            return {
                "section_id": "relationships",
                "title": _coerce_text(wrapped.get("title")) or "Отношения и близость",
                "paragraphs": [part for part in paragraphs if part] or ["Отношения требуют дополнительной сборки."],
                "evidence_ids": evidence_ids,
                "covered_pattern_ids": covered_pattern_ids,
            }
        wrapped_body = _coerce_text(wrapped.get("body"))
        wrapped_evidence_ids = _unique_strings(wrapped.get("evidence_ids", [])) or _fallback_evidence_ids(
            narrative_input
        )
        return {
            "section_id": "relationships",
            "title": _coerce_text(wrapped.get("title")) or "Отношения и близость",
            "paragraphs": [wrapped_body] if wrapped_body else ["Отношения требуют дополнительной сборки."],
            "evidence_ids": wrapped_evidence_ids,
            "covered_pattern_ids": wrapped_evidence_ids,
        }
    relationships = payload.get("relationships") if isinstance(payload.get("relationships"), dict) else {}
    sexuality = payload.get("sexuality") if isinstance(payload.get("sexuality"), dict) else {}
    if not relationships and not sexuality:
        return payload
    relationship_body = " ".join(
        part
        for part in [
            _coerce_text(relationships.get("mechanism")),
            _coerce_text(relationships.get("tension")),
            _coerce_text(relationships.get("compensation")),
        ]
        if part
    )
    sexuality_body = " ".join(
        part
        for part in [
            _coerce_text(sexuality.get("mechanism")),
            _coerce_text(sexuality.get("risk")),
            _coerce_text(sexuality.get("mature_expression")),
        ]
        if part
    )
    evidence_ids = _unique_strings(payload.get("evidence_ids", []))
    covered_pattern_ids = _unique_strings(payload.get("covered_pattern_ids", []))
    fallback_ids = evidence_ids or covered_pattern_ids or _fallback_evidence_ids(narrative_input)
    return {
        "section_id": "relationships",
        "title": _coerce_text(relationships.get("title")) or "Отношения и близость",
        "paragraphs": [part for part in [relationship_body, sexuality_body] if part]
        or ["Отношения требуют дополнительной сборки."],
        "evidence_ids": fallback_ids,
        "covered_pattern_ids": covered_pattern_ids or fallback_ids,
    }


def _normalize_development_section_shape(
    payload: dict[str, Any],
    narrative_input: NarrativeInput | None,
) -> dict[str, Any]:
    if {"section_id", "title", "paragraphs", "evidence_ids", "covered_pattern_ids"} <= set(payload):
        return payload
    if payload.get("section") != "development" and not any(
        key in payload for key in ["chart_dynamics", "contradictions", "maturity_levels", "calibration_hypotheses"]
    ):
        return payload
    chart_dynamics = payload.get("chart_dynamics") if isinstance(payload.get("chart_dynamics"), list) else []
    contradictions = payload.get("contradictions") if isinstance(payload.get("contradictions"), list) else []
    maturity_levels = payload.get("maturity_levels") if isinstance(payload.get("maturity_levels"), dict) else {}
    calibration_hypotheses = (
        payload.get("calibration_hypotheses") if isinstance(payload.get("calibration_hypotheses"), list) else []
    )
    paragraphs = [
        _coerce_text((chart_dynamics[0] if chart_dynamics else {}).get("compensation")),
        _coerce_text((contradictions[0] if contradictions else {}).get("mature_expression")),
        _coerce_text(
            (maturity_levels.get("high") if isinstance(maturity_levels.get("high"), dict) else {}).get("body")
        ),
        _coerce_text((calibration_hypotheses[0] if calibration_hypotheses else {}).get("hypothesis")),
    ]
    combined_items = chart_dynamics + contradictions + calibration_hypotheses
    evidence_ids = _unique_strings(
        evidence_id for item in combined_items if isinstance(item, dict) for evidence_id in item.get("evidence_ids", [])
    )
    covered_pattern_ids = _unique_strings(item.get("id") for item in combined_items if isinstance(item, dict))
    fallback_ids = evidence_ids or covered_pattern_ids or _fallback_evidence_ids(narrative_input)
    return {
        "section_id": "development",
        "title": "Развитие и зрелая интеграция",
        "paragraphs": [part for part in paragraphs if part] or ["Развитие требует дополнительной сборки."],
        "evidence_ids": fallback_ids,
        "covered_pattern_ids": covered_pattern_ids or fallback_ids,
    }


def _normalize_house_scenarios_section_shape(
    payload: dict[str, Any],
    narrative_input: NarrativeInput | None,
) -> dict[str, Any]:
    if {"section_id", "title", "paragraphs", "evidence_ids", "covered_pattern_ids"} <= set(payload):
        return payload
    scenarios = payload.get("house_scenarios") if isinstance(payload.get("house_scenarios"), list) else []
    if not scenarios:
        return payload
    paragraphs = [
        " ".join(
            part
            for part in [
                _coerce_text(scenario.get("placement")),
                _coerce_text(scenario.get("manifestation")),
                _coerce_text(scenario.get("mature_expression")),
            ]
            if part
        )
        for scenario in scenarios[:3]
        if isinstance(scenario, dict)
    ]
    evidence_ids = _unique_strings(
        evidence_id
        for scenario in scenarios
        if isinstance(scenario, dict)
        for evidence_id in scenario.get("evidence_ids", [])
    )
    covered_pattern_ids = _unique_strings(scenario.get("id") for scenario in scenarios if isinstance(scenario, dict))
    fallback_ids = evidence_ids or covered_pattern_ids or _fallback_evidence_ids(narrative_input)
    return {
        "section_id": "house_scenarios",
        "title": "Жизненные сценарии по домам",
        "paragraphs": paragraphs or ["Жизненные сценарии требуют дополнительной сборки."],
        "evidence_ids": fallback_ids,
        "covered_pattern_ids": covered_pattern_ids or fallback_ids,
    }


def _unique_strings(values: Any) -> list[str]:
    unique: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if not normalized or normalized in unique:
            continue
        unique.append(normalized)
    return unique


def _fallback_evidence_ids(narrative_input: NarrativeInput | None, *, limit: int = 6) -> list[str]:
    if narrative_input is None:
        return ["fallback_evidence"]
    evidence_map = getattr(getattr(narrative_input, "deep_natal_synthesis", None), "evidence_map", None)
    if isinstance(evidence_map, dict):
        return [evidence_id for evidence_id in list(evidence_map.keys())[:limit] if isinstance(evidence_id, str)]
    return []


def _normalize_self_narrative_shape(payload: dict[str, Any]) -> dict[str, Any]:
    hero = payload.get("hero")
    normalized_hero = hero
    if isinstance(hero, str):
        normalized_hero = {
            "id": "hero",
            "title": payload.get("title") or "Ваш разбор",
            "body": hero,
            "bullets": [],
            "evidence_notes": [],
        }
    elif isinstance(hero, dict) and {"id", "title", "body"} - set(hero):
        hero_body_parts = [
            part
            for part in [
                _coerce_text(hero.get("body")),
                _coerce_text(hero.get("greeting")),
                _coerce_text(hero.get("summary")),
                _coerce_text(hero.get("resonance")),
            ]
            if isinstance(part, str) and part.strip()
        ]
        normalized_hero = {
            "id": "hero",
            "title": hero.get("title") or payload.get("title") or "Ваш разбор",
            "body": "\n\n".join(hero_body_parts) or payload.get("final_summary") or "",
            "bullets": hero.get("bullets", []),
            "evidence_notes": [
                {
                    "claim": note.get("claim") or note.get("text") or "",
                    "fact_ids": note.get("fact_ids", []),
                }
                for note in hero.get("evidence_notes", [])
                if isinstance(note, dict)
            ],
        }

    normalized_sections: list[dict[str, Any]] = []
    raw_sections = payload.get("sections", [])
    if isinstance(raw_sections, dict):
        raw_sections = [
            {"id": section_id, **section} if isinstance(section, dict) else {"id": section_id, "body": section}
            for section_id, section in raw_sections.items()
        ]
    for section in raw_sections:
        if not isinstance(section, dict):
            normalized_sections.append(section)
            continue
        section_id = section.get("id")
        normalized_section = {
            "id": section_id,
            "title": section.get("title") or _SECTION_TITLES.get(str(section_id), str(section_id or "Раздел")),
            "body": _coerce_text(section.get("body") or section.get("content")),
            "bullets": section.get("bullets", []),
            "evidence_notes": [
                {
                    "claim": note.get("claim") or note.get("text") or "",
                    "fact_ids": note.get("fact_ids", []),
                }
                for note in section.get("evidence_notes", [])
                if isinstance(note, dict)
            ],
        }
        normalized_sections.append(normalized_section)

    career_cta = payload.get("career_cta")
    normalized_career_cta = career_cta
    fallback_career_body = (
        "В Career-отчёте можно перевести этот личный паттерн в рабочие роли, стиль задач и профессиональные сценарии."
    )

    if not isinstance(career_cta, dict):
        normalized_career_cta = {
            "title": "Развернуть это в Career",
            "body": fallback_career_body,
            "bullets": [],
            "button_label": "Перейти в Career",
        }
    else:
        body = _coerce_text(career_cta.get("body") or career_cta.get("text"))
        normalized_career_cta = {
            "title": career_cta.get("title") or "Развернуть это в Career",
            "body": body or fallback_career_body,
            "bullets": career_cta.get("bullets", []),
            "button_label": career_cta.get("button_label") or "Перейти в Career",
        }

    normalized_payload = dict(payload)
    normalized_payload["hero"] = normalized_hero
    normalized_payload["sections"] = normalized_sections
    normalized_payload["career_cta"] = normalized_career_cta
    normalized_payload["final_summary"] = _coerce_text(
        payload.get("final_summary") or payload.get("summary"),
    )
    return normalized_payload


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n\n".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return _coerce_text(
            value.get("body")
            or value.get("text")
            or value.get("content")
            or value.get("summary")
            or value.get("description"),
        )
    return "" if value is None else str(value)
