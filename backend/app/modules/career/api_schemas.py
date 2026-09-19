"""Typed request/response contracts for the Career API."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.career.questionnaire import CareerQuestionnaireDraft


class CareerErrorResponse(BaseModel):
    detail: str | dict[str, Any]


class CareerLockedResponse(BaseModel):
    contract_version: Literal["career_locked_v1"] = "career_locked_v1"
    access_state: Literal["locked"] = "locked"
    required_product: Literal["plus"] = "plus"
    reason: str


class QuestionnaireAnswersRequest(BaseModel):
    answers: CareerQuestionnaireDraft


class QuestionnaireCurrentResponse(BaseModel):
    contract_version: Literal["career_questionnaire_v1"] = "career_questionnaire_v1"
    session_id: UUID
    career_profile_id: UUID
    profile_id: UUID
    chart_id: UUID
    status: str
    questionnaire_version: str
    questions: list[dict[str, Any]]
    answers: dict[str, Any]
    missing_required: list[str]


class QuestionnaireResponse(BaseModel):
    contract_version: Literal["career_questionnaire_v1"] = "career_questionnaire_v1"
    session_id: UUID
    status: str
    answers: dict[str, Any]
    missing_required: list[str]


class CreateCareerReportRequest(BaseModel):
    profile_id: UUID


class RegenerateCareerReportRequest(BaseModel):
    section_keys: list[str] = Field(default_factory=list)


class CareerGenerationAcceptedResponse(BaseModel):
    contract_version: Literal["career_generation_job_v1"] = "career_generation_job_v1"
    status: str
    generation_id: UUID
    report_id: UUID | None = None
    links: dict[str, str]


class CareerSectionStateResponse(BaseModel):
    section_key: str
    status: str
    error: str | None = None


class CareerGenerationStatusResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    contract_version: Literal["career_generation_status_v1"]
    generation_id: UUID
    report_id: UUID | None
    status: str
    deterministic_status: str
    narrative_status: str
    progress: dict[str, int]
    sections: list[CareerSectionStateResponse]
    diagnostics: dict[str, Any]


class CareerReportResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    contract_version: Literal["career_report_read_v1"]
    report_id: UUID
    generation_id: UUID
    status: str
    version: int
    versions: dict[str, str]
    deterministic_payload: dict[str, Any]
    sections: list[dict[str, Any]]
    section_states: list[CareerSectionStateResponse]
    assembled_payload: dict[str, Any]


class CareerSectionsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    contract_version: Literal["career_sections_v1"]
    sections: list[dict[str, Any]]
