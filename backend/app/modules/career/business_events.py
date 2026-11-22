"""Business facts shared by Career dispatch and worker transitions."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.analytics.schemas import BusinessEventInput, EventType, Product
from app.modules.analytics.service import emit_business_event
from app.modules.career import models


async def emit_career_terminal(
    db: AsyncSession,
    generation: models.CareerGeneration,
    *,
    report: models.CareerReport | None = None,
) -> None:
    if not settings.BUSINESS_MONITORING_ENABLED:
        return
    status = generation.status
    if status in {"failed", "narrative_failed"}:
        event_type = EventType.REPORT_FAILED
        artifact: models.CareerGeneration | models.CareerReport = generation
        entity_id = generation.generation_id
    elif report is not None and status in {"ready", "partial_failure"}:
        event_type = EventType.REPORT_READY if status == "ready" else EventType.REPORT_PARTIAL
        artifact = report
        entity_id = report.id
    else:
        return

    await db.flush()
    await db.refresh(artifact, attribute_names=["updated_at"])
    await emit_business_event(
        db,
        BusinessEventInput(
            event_type=event_type,
            entity_id=entity_id,
            subject_id=generation.user_id,
            product=Product.CAREER,
            occurred_at=artifact.updated_at,
        ),
    )
