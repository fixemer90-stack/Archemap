"""DeepSeek adapter behind the generic LLM provider boundary."""

from __future__ import annotations

import json
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

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers=headers,
                    json=request_payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("LLM provider request timed out", code="llm_timeout") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMProviderUnavailableError(
                f"LLM provider request failed with status {exc.response.status_code}",
                code="llm_provider_unavailable",
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderUnavailableError(
                "LLM provider request failed",
                code="llm_provider_unavailable",
            ) from exc

        return self._parse_response(response.json(), schema)

    def _parse_response(self, response_payload: dict[str, Any], schema: type[StructuredSchemaT]) -> StructuredSchemaT:
        try:
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMInvalidResponseError(
                "LLM provider response did not contain structured content",
                code="llm_invalid_response",
            ) from exc

        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMInvalidResponseError(
                "LLM provider returned non-JSON content",
                code="llm_invalid_response",
            ) from exc

        if schema.__name__ == "SelfNarrative" and isinstance(parsed_content, dict):
            parsed_content = _normalize_self_narrative_shape(parsed_content)

        try:
            return schema.model_validate(parsed_content)
        except ValidationError as exc:
            raise LLMInvalidResponseError(
                "LLM provider returned JSON that does not match schema",
                code="llm_invalid_response",
            ) from exc


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
        "В Career-отчёте можно перевести этот личный паттерн "  # noqa: RUF001
        "в рабочие роли, стиль задач и профессиональные сценарии."
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
