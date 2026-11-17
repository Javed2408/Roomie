"""discovery and matching

Two small changes for Phase 5:

* A unique partial index on notifications, so each person can receive at
  most one "new match" notification for a given match. This is enforced by
  the database, not only by application code.
* matches.compatibility_score may be empty. It records the score when the
  match was made, and there is nothing honest to store if the score could
  not be calculated.

No rows are changed or removed.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-17 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_notifications_new_match",
        "notifications",
        ["user_id", "reference_id"],
        unique=True,
        postgresql_where=sa.text("type = 'NEW_MATCH'"),
    )
    op.alter_column(
        "matches", "compatibility_score", existing_type=sa.SmallInteger(), nullable=True
    )


def downgrade() -> None:
    # Refuses (rather than inventing a score) if a match has no score.
    op.alter_column(
        "matches", "compatibility_score", existing_type=sa.SmallInteger(), nullable=False
    )
    op.drop_index("uq_notifications_new_match", table_name="notifications")
