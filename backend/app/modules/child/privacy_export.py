"""Owner-scoped export data, never a public URL or a replacement for route auth."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Table, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.child import models

# Explicit inventory: additions require an intentional export/privacy review.
CHILD_EXPORT_TABLES = cast(
    tuple[Table, ...],
    (
        models.ChildProfile.__table__,
        models.ChildChartVersion.__table__,
        models.ChildAgeSnapshot.__table__,
        models.ChildParentStyleScore.__table__,
        models.ChildNeedScore.__table__,
        models.ChildSynastryEvidence.__table__,
        models.ChildInteractionScore.__table__,
        models.ChildQuestionnaireSession.__table__,
        models.ChildAnswer.__table__,
        models.ChildContextResolution.__table__,
        models.ChildGuidanceFacts.__table__,
        models.ChildSegmentGeneration.__table__,
        models.ChildReport.__table__,
        models.ChildReportAgeGuidance.__table__,
        models.ChildGeneration.__table__,
        models.ChildGenerationEvent.__table__,
        models.ChildReportAssembly.__table__,
    ),
)
_SECRET_KEYS = frozenset(
    {
        "apikey",
        "providerapikey",
        "providercredentials",
        "credentials",
        "secret",
        "clientsecret",
        "password",
        "authorization",
        "accesstoken",
        "refreshtoken",
        "claimtoken",
        "cookie",
        "setcookie",
    }
)


class ChildExportNotFoundError(LookupError):
    """Indistinguishable missing/foreign aggregate."""


def _secret_key(value: object) -> bool:
    normalized = "".join(char for char in str(value).lower() if char.isalnum())
    return normalized in _SECRET_KEYS | {"token", "lifecycletoken"} or normalized.endswith(
        ("apikey", "accesstoken", "refreshtoken", "password", "secret", "credentials")
    )


def _without_credentials(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _without_credentials(item) for key, item in value.items() if not _secret_key(key)}
    if isinstance(value, list):
        return [_without_credentials(item) for item in value]
    return value


async def export_child_domain(session: AsyncSession, *, owner_user_id: UUID, child_profile_id: UUID) -> dict[str, Any]:
    """Read complete archived/active aggregate; no commit, purge or provider requests.

    Caller MUST authenticate, check Child access, and require authenticated HTTPS
    in production. Return as private/no-store attachment, never public object URL.
    Holds root shared lock until caller ends transaction to exclude concurrent purge.
    PDF is generated from exported persisted report data by the authenticated PDF
    endpoint; no stored PDF table/object exists in this domain.
    """
    root = models.ChildProfile.__table__
    generation = models.ChildGeneration.__table__
    with session.no_autoflush:
        owned = await session.scalar(
            select(root.c.id)
            .where(root.c.id == child_profile_id, root.c.owner_user_id == owner_user_id)
            .with_for_update(read=True)
        )
        if owned is None:
            raise ChildExportNotFoundError("Child resource not found")
        # All payload subqueries execute in ONE PostgreSQL statement/MVCC snapshot.
        # A shared root lock alone does not serialize questionnaire answer writers.
        columns = []
        for table in CHILD_EXPORT_TABLES:
            if table is root:
                query = select(table).where(root.c.id == child_profile_id, root.c.owner_user_id == owner_user_id)
            elif table is models.ChildGenerationEvent.__table__:
                query = (
                    select(table)
                    .join(generation, table.c.generation_id == generation.c.generation_id)
                    .where(
                        generation.c.child_profile_id == child_profile_id, generation.c.owner_user_id == owner_user_id
                    )
                )
            else:
                query = (
                    select(table)
                    .join(root, table.c.child_profile_id == root.c.id)
                    .where(root.c.id == child_profile_id, root.c.owner_user_id == owner_user_id)
                )
            source = query.order_by(table.c.id).subquery()
            columns.append(
                select(func.jsonb_agg(func.to_jsonb(source.table_valued()))).scalar_subquery().label(table.name)
            )
        snapshot = (await session.execute(select(*columns))).mappings().one()
        records = {name: _without_credentials(rows or []) for name, rows in snapshot.items()}
    # PostgreSQL row JSON has portable dates/UUIDs; no credentials are sourced from settings.
    return json.loads(json.dumps({"export_version": "child-export-1", "records": records}, default=str))  # type: ignore[no-any-return]
