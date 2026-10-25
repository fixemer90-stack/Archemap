"""Strict public HTTP contracts; all lineage and age are server-owned."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ChildLockedDetail(APIModel):
    access_state: Literal["locked"]
    report_type: Literal["child"]
    required_level: Literal["plus"]
    reason: Literal["plus_required"]
    upgrade_url: Literal["/billing"]


class ChildValidationIssue(APIModel):
    loc: list[str | int]
    type: str
    msg: str


class CompleteChildQuestionnaireRequest(APIModel):
    """Completion never accepts caller hashes, dates, versions or answers."""


class ChildErrorResponse(APIModel):
    detail: str | ChildLockedDetail | list[ChildValidationIssue]


class BirthPlace(APIModel):
    label: str = Field(min_length=1, max_length=300)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    timezone: str = Field(min_length=1, max_length=80)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("A valid IANA timezone is required") from exc
        return value


class CaregiverContext(APIModel):
    primary_caregiver: bool | None = None
    daily_contact: Literal["low", "medium", "high"] | None = None
    boundary_role: Literal["mostly_me", "shared", "mostly_other"] | None = None
    soothing_role: Literal["mostly_me", "shared", "mostly_other"] | None = None


class CreateChildRequest(APIModel):
    display_name: str = Field(min_length=1, max_length=120)
    relationship_type: str = Field(min_length=1, max_length=40)
    child_gender: Literal["male", "female", "other", "unspecified"] | None = None
    birth_date: date
    birth_time: time | None = None
    birth_time_confidence: Literal["exact", "approximate", "unknown"]
    birth_place: BirthPlace
    caregiver_context: CaregiverContext = Field(default_factory=CaregiverContext)

    @model_validator(mode="after")
    def valid_time(self) -> Self:
        if self.birth_time is not None and self.birth_time.tzinfo is not None:
            raise ValueError("Birth time must not carry an offset")
        if (self.birth_time_confidence == "unknown") != (self.birth_time is None):
            raise ValueError("Birth time must agree with its confidence")
        return self


class PatchChildRequest(APIModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    relationship_type: str | None = Field(default=None, min_length=1, max_length=40)
    child_gender: Literal["male", "female", "other", "unspecified"] | None = None
    birth_date: date | None = None
    birth_time: time | None = None
    birth_time_confidence: Literal["exact", "approximate", "unknown"] | None = None
    birth_place: BirthPlace | None = None
    caregiver_context: CaregiverContext | None = None

    @model_validator(mode="after")
    def non_null_required_fields(self) -> Self:
        for key in self.model_fields_set - {"birth_time", "child_gender"}:
            if getattr(self, key) is None:
                raise ValueError("Required fields cannot be null")
        return self


class AgeResponse(APIModel):
    as_of_date: date
    age_years: int
    age_months: int
    age_days: int
    age_stage: str
    age_rules_version: str


class AgeSnapshotResponse(AgeResponse):
    age_snapshot_id: UUID


class ChartResponse(APIModel):
    chart_version_id: UUID
    version: int
    engine_version: str
    birth_time_confidence: str
    allowed_fact_families: list[str]
    excluded_fact_families: list[str]
    uncertainty_reason: str | None


class ChildResponse(CreateChildRequest):
    id: UUID
    status: str
    version: int
    age: AgeResponse
    current_chart: ChartResponse | None
    created_at: datetime
    updated_at: datetime


class ChildExportResponse(APIModel):
    export_version: Literal["child-export-1"]
    records: dict[str, list[dict[str, Any]]]


class ChildrenResponse(APIModel):
    children: list[ChildResponse]


class QuestionOptionResponse(APIModel):
    code: str
    label: str


class QuestionResponse(APIModel):
    key: str
    prompt: str
    required: bool
    options: list[QuestionOptionResponse]


class AnswerRequest(APIModel):
    question_key: str = Field(min_length=1, max_length=120)
    option: str = Field(min_length=1, max_length=120)


class SaveAnswersRequest(APIModel):
    answers: list[AnswerRequest] = Field(max_length=20)


class ChildQuestionnaireResponse(APIModel):
    session_id: UUID
    child_id: UUID
    age_snapshot_id: UUID
    age_stage: str
    status: str
    questionnaire_version: str
    answer_version: str
    context_version: str
    consent_version: str
    required_question_ids: list[str]
    missing_required: list[str]
    questions: list[QuestionResponse]
    answers: list[AnswerRequest]
    completed_at: datetime | None


class CreateChildReportRequest(APIModel):
    child_profile_id: UUID
    questionnaire_session_id: UUID


class ChildGenerationAcceptedResponse(APIModel):
    generation_id: UUID
    status: str
    report_id: UUID | None


class GenerationResponse(ChildGenerationAcceptedResponse):
    child_id: UUID
    operation: str
    error_code: str | None
    next_retry_at: datetime | None
    poll_after_ms: int = 2000


class ChildReportResponse(APIModel):
    report_id: UUID
    child_id: UUID
    display_name: str
    generation_id: UUID
    status: str
    presentation: dict[str, Any]


class SectionsResponse(APIModel):
    report_id: UUID
    sections: list[dict[str, Any]]


class ChildReportVersionResponse(APIModel):
    report_id: UUID
    generation_id: UUID
    core_report_version: int
    status: str
    created_at: datetime


class VersionsResponse(APIModel):
    versions: list[ChildReportVersionResponse]


class AgeSnapshotsResponse(APIModel):
    age_snapshots: list[AgeSnapshotResponse]


class RegenerateRequest(APIModel):
    scope: Literal["failed_sections", "narrative_all", "full_pair"]


class AgeUpdateRequest(APIModel):
    expected_core_report_version: int = Field(ge=1, strict=True)
