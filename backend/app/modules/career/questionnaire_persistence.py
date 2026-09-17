"""Ordered persistence for questionnaire parent/child rows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.modules.career.models import CareerAnswer, CareerQuestionnaireSession, CareerResolution


class QuestionnaireRepository(Protocol):
    async def add(self, instance: object) -> object: ...

    async def add_many(self, instances: Sequence[object]) -> Sequence[object]: ...

    async def flush(self) -> None: ...


async def persist_questionnaire_completion(
    repository: QuestionnaireRepository,
    *,
    questionnaire: CareerQuestionnaireSession,
    answers: Sequence[CareerAnswer],
    resolution: CareerResolution,
) -> None:
    """Flush the session parent before its FK-dependent answer rows."""
    await repository.add(questionnaire)
    await repository.flush()
    await repository.add_many(answers)
    await repository.add(resolution)
    await repository.flush()
