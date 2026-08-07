"""add astrotype v2 foundation

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-08-04 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d0e1f2a3b4"
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
        "astrotype_v2_aspect_definitions",
        *_base_columns(),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("angle_degrees", sa.Float(), nullable=False),
        sa.Column("default_orb_degrees", sa.Float(), nullable=False),
        sa.Column("major", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("code", name="uq_astrotype_v2_aspect_definitions_code"),
    )
    op.create_index(
        "ix_astrotype_v2_aspect_definitions_code",
        "astrotype_v2_aspect_definitions",
        ["code"],
    )

    op.create_table(
        "astrotype_v2_aspect_pair_interpretations",
        *_base_columns(),
        sa.Column("aspect_code", sa.String(40), nullable=False),
        sa.Column("planet_a", sa.String(40), nullable=False),
        sa.Column("planet_b", sa.String(40), nullable=False),
        sa.Column("locale", sa.String(10), nullable=False, server_default="ru"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("keywords", _jsonb, nullable=False, server_default="[]"),
        sa.Column("source_version", sa.String(40), nullable=False, server_default="v2.0"),
        sa.UniqueConstraint(
            "aspect_code",
            "planet_a",
            "planet_b",
            "locale",
            name="uq_astrotype_v2_aspect_pair_interpretation",
        ),
    )
    op.create_index(
        "ix_astrotype_v2_aspect_pair_interpretations_aspect_code",
        "astrotype_v2_aspect_pair_interpretations",
        ["aspect_code"],
    )

    op.create_table(
        "astrotype_v2_natal_charts",
        *_base_columns(),
        sa.Column("user_id", _uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", _uuid, sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("engine_version", sa.String(40), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("birth_datetime_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("house_system", sa.String(10), nullable=False, server_default="P"),
        sa.Column("calculation_payload", _jsonb, nullable=False, server_default="{}"),
        sa.UniqueConstraint(
            "profile_id",
            "engine_version",
            "input_hash",
            name="uq_astrotype_v2_natal_charts_profile_engine_input",
        ),
    )
    op.create_index("ix_astrotype_v2_natal_charts_user_id", "astrotype_v2_natal_charts", ["user_id"])
    op.create_index("ix_astrotype_v2_natal_charts_profile_id", "astrotype_v2_natal_charts", ["profile_id"])
    op.create_index("ix_astrotype_v2_natal_charts_input_hash", "astrotype_v2_natal_charts", ["input_hash"])

    op.create_table(
        "astrotype_v2_natal_planet_positions",
        *_base_columns(),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.String(40), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("sign", sa.String(20), nullable=False),
        sa.Column("sign_degree", sa.Float(), nullable=False),
        sa.Column("house_number", sa.Integer(), nullable=True),
        sa.Column("retrograde", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("chart_id", "body", name="uq_astrotype_v2_natal_planet_positions_chart_body"),
    )
    op.create_index(
        "ix_astrotype_v2_natal_planet_positions_chart_id",
        "astrotype_v2_natal_planet_positions",
        ["chart_id"],
    )

    op.create_table(
        "astrotype_v2_natal_houses",
        *_base_columns(),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("house_number", sa.Integer(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("sign", sa.String(20), nullable=False),
        sa.UniqueConstraint("chart_id", "house_number", name="uq_astrotype_v2_natal_houses_chart_house"),
    )
    op.create_index("ix_astrotype_v2_natal_houses_chart_id", "astrotype_v2_natal_houses", ["chart_id"])

    op.create_table(
        "astrotype_v2_natal_aspects",
        *_base_columns(),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body_a", sa.String(40), nullable=False),
        sa.Column("body_b", sa.String(40), nullable=False),
        sa.Column("aspect_code", sa.String(40), nullable=False),
        sa.Column("angle_degrees", sa.Float(), nullable=False),
        sa.Column("orb_degrees", sa.Float(), nullable=False),
        sa.Column("applying", sa.Boolean(), nullable=True),
        sa.Column("strength", sa.Float(), nullable=True),
        sa.UniqueConstraint(
            "chart_id",
            "body_a",
            "body_b",
            "aspect_code",
            name="uq_astrotype_v2_natal_aspects_chart_pair_code",
        ),
    )
    op.create_index("ix_astrotype_v2_natal_aspects_chart_id", "astrotype_v2_natal_aspects", ["chart_id"])
    op.create_index("ix_astrotype_v2_natal_aspects_aspect_code", "astrotype_v2_natal_aspects", ["aspect_code"])

    op.create_table(
        "astrotype_v2_natal_chart_balances",
        *_base_columns(),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.UniqueConstraint("chart_id", "category", "key", name="uq_astrotype_v2_natal_chart_balances_chart_key"),
    )
    op.create_index(
        "ix_astrotype_v2_natal_chart_balances_chart_id",
        "astrotype_v2_natal_chart_balances",
        ["chart_id"],
    )

    op.create_table(
        "astrotype_v2_natal_chart_patterns",
        *_base_columns(),
        sa.Column(
            "chart_id",
            _uuid,
            sa.ForeignKey("astrotype_v2_natal_charts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pattern_code", sa.String(80), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("evidence", _jsonb, nullable=False, server_default="{}"),
    )
    op.create_index(
        "ix_astrotype_v2_natal_chart_patterns_chart_id",
        "astrotype_v2_natal_chart_patterns",
        ["chart_id"],
    )
    op.create_index(
        "ix_astrotype_v2_natal_chart_patterns_pattern_code",
        "astrotype_v2_natal_chart_patterns",
        ["pattern_code"],
    )


def downgrade() -> None:
    op.drop_table("astrotype_v2_natal_chart_patterns")
    op.drop_table("astrotype_v2_natal_chart_balances")
    op.drop_table("astrotype_v2_natal_aspects")
    op.drop_table("astrotype_v2_natal_houses")
    op.drop_table("astrotype_v2_natal_planet_positions")
    op.drop_table("astrotype_v2_natal_charts")
    op.drop_table("astrotype_v2_aspect_pair_interpretations")
    op.drop_table("astrotype_v2_aspect_definitions")
