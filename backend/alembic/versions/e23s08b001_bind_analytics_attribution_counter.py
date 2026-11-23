"""Pin S05 attribution to the approved counter without blessing historical rows."""

import sqlalchemy as sa
from alembic import op

revision: str = "e23s08b001"
down_revision: str = "e23s07t001"
branch_labels = None
depends_on = None

_TABLE = "analytics_attributions"
_CHECK = "ck_analytics_attribution_counter"


def upgrade() -> None:
    # No default or backfill: no counter can be proven for older observations.
    op.add_column(_TABLE, sa.Column("counter_id", sa.BigInteger(), nullable=True))
    op.create_check_constraint(_CHECK, _TABLE, "counter_id IS NULL OR (counter_id > 0 AND revoked_at IS NULL)")


def downgrade() -> None:
    # Do not allow a downgrade to the pre-provenance sender with used exports or
    # silently strip the destination of a retained observation. Lock in the same
    # order as an export's preflight (existing fence, then attribution).
    op.execute("LOCK TABLE analytics_yandex_conversion_exports, analytics_attributions IN ACCESS EXCLUSIVE MODE")
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM analytics_yandex_conversion_exports) THEN
            RAISE EXCEPTION 'refusing S08 downgrade: keep existing offline conversion fences';
        END IF;
        IF EXISTS (SELECT 1 FROM analytics_attributions WHERE counter_id IS NOT NULL) THEN
            RAISE EXCEPTION 'refusing S08 downgrade: keep retained attribution counter provenance';
        END IF;
    END $$""")
    op.drop_constraint(_CHECK, _TABLE, type_="check")
    op.drop_column(_TABLE, "counter_id")
