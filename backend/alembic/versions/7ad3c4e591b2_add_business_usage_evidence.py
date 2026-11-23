"""Add isolated provider usage facts and a retained Child usage projection.

Revision ID: 7ad3c4e591b2
Revises: e23s07b001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "7ad3c4e591b2"
down_revision: str = "e23s07b001"
branch_labels: str | None = None
depends_on: str | None = None

_TRANSPORT = "business_transport_usage"
_CHILD = "business_child_usage_projection"
_GUARD = "business_usage_reject_mutation"


def upgrade() -> None:
    op.create_table(
        _TRANSPORT,
        sa.Column("attempt_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("model_ref", sa.String(77), nullable=False),
        sa.Column("outcome", sa.String(9), nullable=False),
        sa.Column("usage_source", sa.String(18)),
        sa.Column("input_tokens", sa.BigInteger),
        sa.Column("output_tokens", sa.BigInteger),
        sa.Column("total_tokens", sa.BigInteger),
        sa.Column("cache_hit_tokens", sa.BigInteger),
        sa.Column("rate_version", sa.String(128)),
        sa.Column("rate_pinned_at", sa.DateTime(timezone=True)),
        sa.Column("currency", sa.String(3)),
        sa.Column("input_rate", sa.String(48)),
        sa.Column("output_rate", sa.String(48)),
        sa.Column("cache_rate", sa.String(48)),
        sa.Column("cache_pricing", sa.String(7)),
        sa.CheckConstraint("provider IN ('deepseek', 'openrouter')", name="ck_business_transport_provider"),
        sa.CheckConstraint("model_ref ~ '^model-sha256:[0-9a-f]{64}$'", name="ck_business_transport_model"),
        sa.CheckConstraint("outcome IN ('succeeded', 'failed', 'unknown')", name="ck_business_transport_outcome"),
        sa.CheckConstraint(
            "(usage_source IS NULL AND num_nonnulls(input_tokens,output_tokens,total_tokens,cache_hit_tokens)=0) OR "
            "(usage_source IS NOT NULL AND usage_source IN ('provider','token_estimate','character_estimate') AND "
            "num_nonnulls(input_tokens,output_tokens,total_tokens)=3 AND input_tokens>=0 AND output_tokens>=0 AND "
            "total_tokens::numeric=input_tokens::numeric+output_tokens::numeric AND "
            "(cache_hit_tokens IS NULL OR cache_hit_tokens BETWEEN 0 AND input_tokens))",
            name="ck_business_transport_tokens",
        ),
        sa.CheckConstraint(
            "num_nonnulls(rate_version,rate_pinned_at,currency,input_rate,output_rate,cache_rate,cache_pricing)=0 OR "
            "(num_nonnulls(rate_version,rate_pinned_at,currency,input_rate,output_rate,cache_pricing)=6 AND "
            "currency ~ '^[A-Z]{3}$' AND (cache_pricing='split' OR (cache_pricing='uniform' AND cache_rate IS NULL)))",
            name="ck_business_transport_rate",
        ),
    )
    op.create_index("ix_business_transport_occurred", _TRANSPORT, ["occurred_at", "attempt_id"])
    op.create_table(
        _CHILD,
        sa.Column("segment_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("segment_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("section_outcome", sa.String(6), nullable=False),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("model_ref", sa.String(77), nullable=False),
        sa.Column("http_attempts", sa.BigInteger),
        sa.Column("responses_with_usage", sa.BigInteger),
        sa.Column("responses_without_usage", sa.BigInteger),
        sa.Column("prompt_tokens", sa.BigInteger),
        sa.Column("completion_tokens", sa.BigInteger),
        sa.Column("total_tokens", sa.BigInteger),
        sa.Column("prompt_cache_hit_tokens", sa.BigInteger),
        sa.Column("prompt_cache_miss_tokens", sa.BigInteger),
        sa.CheckConstraint("provider IN ('deepseek','openrouter')", name="ck_business_child_usage_provider"),
        sa.CheckConstraint("model_ref ~ '^model-sha256:[0-9a-f]{64}$'", name="ck_business_child_usage_model"),
        sa.CheckConstraint("section_outcome IN ('ready','failed')", name="ck_business_child_usage_outcome"),
        sa.CheckConstraint(
            "num_nonnulls(http_attempts,responses_with_usage,responses_without_usage)=0 OR "
            "(num_nonnulls(http_attempts,responses_with_usage,responses_without_usage)=3 "
            "AND responses_with_usage>=0 AND responses_without_usage>=0 AND http_attempts::numeric >= "
            "responses_with_usage::numeric + responses_without_usage::numeric)",
            name="ck_business_child_usage_counters",
        ),
        sa.CheckConstraint(
            # With two or more observed responses, otherwise-valid totals may overflow BIGINT.
            "(coalesce(responses_with_usage,0)<>1 AND num_nonnulls(prompt_tokens,completion_tokens,total_tokens)=0) OR "
            "(responses_with_usage IS NOT NULL AND responses_with_usage>0 AND "
            "num_nonnulls(prompt_tokens,completion_tokens,total_tokens)=3 AND prompt_tokens>=0 "
            "AND completion_tokens>=0 AND total_tokens::numeric=prompt_tokens::numeric+completion_tokens::numeric)",
            name="ck_business_child_usage_tokens",
        ),
        sa.CheckConstraint(
            "num_nonnulls(prompt_cache_hit_tokens,prompt_cache_miss_tokens)=0 OR "
            "(num_nonnulls(prompt_cache_hit_tokens,prompt_cache_miss_tokens,prompt_tokens)=3 "
            "AND prompt_cache_hit_tokens>=0 AND prompt_cache_miss_tokens>=0 AND "
            "prompt_cache_hit_tokens::numeric+prompt_cache_miss_tokens::numeric=prompt_tokens::numeric)",
            name="ck_business_child_usage_cache",
        ),
    )
    op.create_index("ix_business_child_usage_created", _CHILD, ["segment_created_at", "segment_id"])
    op.execute(f"""
        CREATE FUNCTION {_GUARD}() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'usage evidence is append-only' USING ERRCODE = 'check_violation';
        END $$
        """)
    for table in (_TRANSPORT, _CHILD):
        op.execute(f"""
            CREATE TRIGGER reject_usage_mutation BEFORE UPDATE OR DELETE OR TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION {_GUARD}()
            """)


def downgrade() -> None:
    op.execute(f"LOCK TABLE {_TRANSPORT}, {_CHILD} IN ACCESS EXCLUSIVE MODE")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT FROM business_transport_usage) OR EXISTS (SELECT FROM business_child_usage_projection)
            THEN
                RAISE EXCEPTION 'refusing downgrade: provider usage evidence exists';
            END IF;
        END $$
        """)
    op.drop_table(_CHILD)
    op.drop_table(_TRANSPORT)
    op.execute(f"DROP FUNCTION {_GUARD}()")
