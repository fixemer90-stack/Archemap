"""Persistence boundary for immutable Career artifacts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import BaseModel
from app.modules.career import models

_CareerModel = TypeVar("_CareerModel", bound=BaseModel)


class CareerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, instance: _CareerModel) -> _CareerModel:
        self.session.add(instance)
        return instance

    async def add_many(self, instances: Sequence[_CareerModel]) -> Sequence[_CareerModel]:
        self.session.add_all(list(instances))
        return instances

    async def flush(self) -> None:
        await self.session.flush()

    async def get_profile_by_idempotency_key(
        self,
        user_id: UUID,
        idempotency_key: str,
    ) -> models.CareerProfile | None:
        result = await self.session.execute(
            select(models.CareerProfile).where(
                models.CareerProfile.user_id == user_id,
                models.CareerProfile.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def get_profile_for_user(
        self,
        career_profile_id: UUID,
        user_id: UUID,
    ) -> models.CareerProfile | None:
        result = await self.session.execute(
            select(models.CareerProfile).where(
                models.CareerProfile.id == career_profile_id,
                models.CareerProfile.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_questionnaire_session(
        self,
        *,
        career_profile_id: UUID,
        questionnaire_version: str,
    ) -> models.CareerQuestionnaireSession | None:
        result = await self.session.execute(
            select(models.CareerQuestionnaireSession).where(
                models.CareerQuestionnaireSession.career_profile_id == career_profile_id,
                models.CareerQuestionnaireSession.questionnaire_version == questionnaire_version,
            )
        )
        return result.scalar_one_or_none()

    async def list_questionnaire_answers(self, questionnaire_session_id: UUID) -> list[models.CareerAnswer]:
        result = await self.session.execute(
            select(models.CareerAnswer)
            .where(models.CareerAnswer.questionnaire_session_id == questionnaire_session_id)
            .order_by(models.CareerAnswer.question_key)
        )
        return list(result.scalars().all())

    async def get_report_by_generation_id(self, generation_id: UUID) -> models.CareerReport | None:
        result = await self.session.execute(
            select(models.CareerReport).where(models.CareerReport.generation_id == generation_id)
        )
        return result.scalar_one_or_none()

    async def get_report_for_user(self, report_id: UUID, user_id: UUID) -> models.CareerReport | None:
        result = await self.session.execute(
            select(models.CareerReport)
            .join(models.CareerProfile, models.CareerReport.career_profile_id == models.CareerProfile.id)
            .where(
                models.CareerReport.id == report_id,
                models.CareerProfile.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_report(self, career_profile_id: UUID) -> models.CareerReport | None:
        result = await self.session.execute(
            select(models.CareerReport)
            .where(models.CareerReport.career_profile_id == career_profile_id)
            .order_by(models.CareerReport.version.desc(), models.CareerReport.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_report_history_for_user(
        self,
        career_profile_id: UUID,
        user_id: UUID,
    ) -> list[models.CareerReport]:
        result = await self.session.execute(
            select(models.CareerReport)
            .join(models.CareerProfile, models.CareerReport.career_profile_id == models.CareerProfile.id)
            .where(
                models.CareerReport.career_profile_id == career_profile_id,
                models.CareerProfile.user_id == user_id,
            )
            .order_by(models.CareerReport.version.desc())
        )
        return list(result.scalars().all())
