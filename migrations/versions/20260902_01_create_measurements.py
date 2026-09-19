"""Create measurements table."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "measurements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("location", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=23), nullable=False),
        sa.Column("value", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source", "location", "kind", "observed_at", name="uq_measurement_identity"
        ),
    )
    op.create_index(
        "ix_measurements_kind_location_time",
        "measurements",
        ["kind", "location", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_measurements_kind_location_time", table_name="measurements")
    op.drop_table("measurements")
