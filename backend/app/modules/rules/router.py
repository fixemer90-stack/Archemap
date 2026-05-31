"""Rules router — API endpoints for chart interpretation."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.modules.rules.schemas import (
    InterpretRequest,
    InterpretResponse,
    RuleSetInfo,
)
from app.modules.rules.service import RulesService

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("/interpret", response_model=InterpretResponse)
async def interpret_chart(
    body: InterpretRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user),
) -> InterpretResponse:
    """Interpret a chart snapshot through the rule engine.

    Takes a profile_id and returns archetype scores, claims,
    evidence trail, and confidence assessment.
    """
    service = RulesService(db)
    result = await service.interpret_chart(
        profile_id=UUID(body.profile_id),
        user_id=current_user,
        product=body.product,
        ruleset_version=body.ruleset_version,
        locale=body.locale,
        mode=body.mode,
    )
    return InterpretResponse(**result)


@router.get("/rulesets", response_model=list[RuleSetInfo])
async def list_rulesets(
    current_user: UUID = Depends(get_current_user),
) -> list[RuleSetInfo]:
    """List all available rulesets."""
    from app.modules.rules.loader import list_available_rulesets

    rulesets = list_available_rulesets()
    return [RuleSetInfo(**rs) for rs in rulesets]
