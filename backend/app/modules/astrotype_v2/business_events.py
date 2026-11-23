"""Business facts shared by Self dispatch and worker transitions."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.analytics.schemas import BusinessEventInput, EventType, Product
from app.modules.analytics.service import emit_business_event
from app.modules.astrotype_v2.models import NatalReportGeneration


async def emit_self_generation_failure(db: AsyncSession, generation: NatalReportGeneration) -> None:
    if not settings.BUSINESS_MONITORING_ENABLED:
        return
    await db.flush()
    await db.refresh(generation, attribute_names=["updated_at"])
    await emit_business_event(
        db,
        BusinessEventInput(
            event_type=EventType.REPORT_FAILED,
            entity_id=generation.generation_id,
            subject_id=generation.user_id,
            product=Product.SELF,
            occurred_at=generation.updated_at,
        ),
    )
