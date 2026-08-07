"""add astrotype v2 report artifacts

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-05 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2a3b4c5d6e7"
down_revision: str | None = "e1f2a3b4c5d6"
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
        "astrotype_v2_natal_syntheses",
        *_base_columns(),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(40), nullable=False, server_default="ready"),
        sa.Column("facts_version", sa.String(40), nullable=False),
        sa.Column("payload", _jsonb, nullable=False, server_default="{}"),
        sa.Column("source_version", sa.String(40), nullable=False, server_default="v2.0"),
        sa.UniqueConstraint("chart_id", "source_version", name="uq_astrotype_v2_natal_syntheses_chart_version"),
    )
    op.create_index("ix_astrotype_v2_natal_syntheses_chart_id", "astrotype_v2_natal_syntheses", ["chart_id"])
    op.create_index("ix_astrotype_v2_natal_syntheses_status", "astrotype_v2_natal_syntheses", ["status"])

    op.create_table(
        "astrotype_v2_report_outlines",
        *_base_columns(),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(40), nullable=False, server_default="ready"),
        sa.Column("outline", _jsonb, nullable=False, server_default="{}"),
        sa.Column("section_keys", _jsonb, nullable=False, server_default="[]"),
        sa.Column("source_version", sa.String(40), nullable=False, server_default="v2.0"),
        sa.UniqueConstraint("chart_id", "source_version", name="uq_astrotype_v2_report_outlines_chart_version"),
    )
    op.create_index("ix_astrotype_v2_report_outlines_chart_id", "astrotype_v2_report_outlines", ["chart_id"])
    op.create_index("ix_astrotype_v2_report_outlines_status", "astrotype_v2_report_outlines", ["status"])

    op.create_table(
        "astrotype_v2_report_segment_generations",
        *_base_columns(),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "outline_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_report_outlines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_key", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(80), nullable=True),
        sa.Column("model", sa.String(120), nullable=True),
        sa.Column("prompt_version", sa.String(80), nullable=True),
        sa.Column("payload", _jsonb, nullable=False, server_default="{}"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.UniqueConstraint("outline_id", "section_key", name="uq_astrotype_v2_report_segments_outline_section"),
    )
    op.create_index(
        "ix_astrotype_v2_report_segment_generations_chart_id",
        "astrotype_v2_report_segment_generations",
        ["chart_id"],
    )
    op.create_index(
        "ix_astrotype_v2_report_segment_generations_outline_id",
        "astrotype_v2_report_segment_generations",
        ["outline_id"],
    )
    op.create_index(
        "ix_astrotype_v2_report_segment_generations_section_key",
        "astrotype_v2_report_segment_generations",
        ["section_key"],
    )
    op.create_index(
        "ix_astrotype_v2_report_segment_generations_status",
        "astrotype_v2_report_segment_generations",
        ["status"],
    )

    op.create_table(
        "astrotype_v2_natal_infographic_data",
        *_base_columns(),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(40), nullable=False, server_default="ready"),
        sa.Column("calculation_layer", _jsonb, nullable=False, server_default="{}"),
        sa.Column("source_version", sa.String(40), nullable=False, server_default="v2.0"),
        sa.UniqueConstraint("chart_id", "source_version", name="uq_astrotype_v2_natal_infographic_data_chart_version"),
    )
    op.create_index(
        "ix_astrotype_v2_natal_infographic_data_chart_id",
        "astrotype_v2_natal_infographic_data",
        ["chart_id"],
    )
    op.create_index(
        "ix_astrotype_v2_natal_infographic_data_status",
        "astrotype_v2_natal_infographic_data",
        ["status"],
    )

    op.create_table(
        "astrotype_v2_natal_reports",
        *_base_columns(),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "synthesis_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_syntheses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "outline_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_report_outlines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "infographic_data_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_infographic_data.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(40), nullable=False, server_default="deterministic_ready"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deterministic_payload", _jsonb, nullable=False, server_default="{}"),
        sa.Column("narrative_payload", _jsonb, nullable=False, server_default="{}"),
        sa.Column("assembled_payload", _jsonb, nullable=False, server_default="{}"),
        sa.UniqueConstraint("chart_id", "version", name="uq_astrotype_v2_natal_reports_chart_version"),
    )
    op.create_index("ix_astrotype_v2_natal_reports_chart_id", "astrotype_v2_natal_reports", ["chart_id"])
    op.create_index("ix_astrotype_v2_natal_reports_synthesis_id", "astrotype_v2_natal_reports", ["synthesis_id"])
    op.create_index("ix_astrotype_v2_natal_reports_outline_id", "astrotype_v2_natal_reports", ["outline_id"])
    op.create_index("ix_astrotype_v2_natal_reports_status", "astrotype_v2_natal_reports", ["status"])


def downgrade() -> None:
    op.drop_table("astrotype_v2_natal_reports")
    op.drop_table("astrotype_v2_natal_infographic_data")
    op.drop_table("astrotype_v2_report_segment_generations")
    op.drop_table("astrotype_v2_report_outlines")
    op.drop_table("astrotype_v2_natal_syntheses")
