"""add astrotype v2 fact storage

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-05 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_jsonb = postgresql.JSONB(astext_type=sa.Text())
_uuid = postgresql.UUID(as_uuid=True)


def _base_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("id", _uuid, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "astrotype_v2_natal_facts",
        *_base_columns(),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fact_type", sa.String(60), nullable=False),
        sa.Column("fact_key", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column("polarity", sa.String(40), nullable=True),
        sa.Column("section_hint", sa.String(80), nullable=True),
        sa.Column("payload", _jsonb, nullable=False, server_default="{}"),
        sa.Column("source_version", sa.String(40), nullable=False, server_default="v2.0"),
        sa.UniqueConstraint(
            "chart_id",
            "fact_key",
            "source_version",
            name="uq_astrotype_v2_natal_facts_chart_key_version",
        ),
    )
    op.create_index("ix_astrotype_v2_natal_facts_chart_id", "astrotype_v2_natal_facts", ["chart_id"])
    op.create_index("ix_astrotype_v2_natal_facts_fact_type", "astrotype_v2_natal_facts", ["fact_type"])
    op.create_index("ix_astrotype_v2_natal_facts_fact_key", "astrotype_v2_natal_facts", ["fact_key"])
    op.create_index("ix_astrotype_v2_natal_facts_section_hint", "astrotype_v2_natal_facts", ["section_hint"])

    op.create_table(
        "astrotype_v2_natal_fact_evidence",
        *_base_columns(),
        sa.Column(
            "fact_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_facts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_table", sa.String(80), nullable=False),
        sa.Column("source_id", _uuid, nullable=True),
        sa.Column("source_key", sa.String(160), nullable=True),
        sa.Column("payload", _jsonb, nullable=False, server_default="{}"),
        sa.UniqueConstraint("fact_id", "source_table", "source_id", name="uq_astrotype_v2_natal_fact_evidence_source"),
    )
    op.create_index("ix_astrotype_v2_natal_fact_evidence_fact_id", "astrotype_v2_natal_fact_evidence", ["fact_id"])
    op.create_index("ix_astrotype_v2_natal_fact_evidence_chart_id", "astrotype_v2_natal_fact_evidence", ["chart_id"])


def downgrade() -> None:
    op.drop_table("astrotype_v2_natal_fact_evidence")
    op.drop_table("astrotype_v2_natal_facts")
