"""society directory

Turns localities and societies into an admin-curated directory:

* Both gain a verification status (UNVERIFIED / VERIFIED), who verified it
  and when, a private source note, and a normalised `name_key` used to
  reject duplicates such as "Abode Valley" vs "abode-valley".
* Localities gain a description and created/updated timestamps.
* Societies gain a community type (apartment complex, villa community).
* A new `directory_events` table records every administrative change.

Existing rows are kept. They become UNVERIFIED, so nothing already in the
directory is shown to students until an administrator verifies it. No user
data is removed.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-17 00:46:09.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must give exactly the same result as app.models.society.normalise_name.
NAME_KEY_SQL = "btrim(regexp_replace(lower(name), '[^a-z0-9]+', ' ', 'g'))"

VERIFIED_IS_ATTRIBUTED = (
    "verification_status = 'UNVERIFIED' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)"
)


def _add_directory_columns(table: str) -> None:
    """The columns localities and societies share, filled in for existing rows."""
    # Added as optional first, filled in, then made required.
    op.add_column(table, sa.Column("name_key", sa.String(length=180), nullable=True))
    op.execute(f"UPDATE {table} SET name_key = {NAME_KEY_SQL}")
    op.alter_column(table, "name_key", nullable=False)

    op.add_column(
        table,
        sa.Column(
            "verification_status",
            sa.String(length=20),
            server_default="UNVERIFIED",
            nullable=False,
        ),
    )
    op.add_column(table, sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(table, sa.Column("verified_by", sa.Uuid(), nullable=True))
    op.add_column(table, sa.Column("source_note", sa.Text(), nullable=True))

    op.create_check_constraint(
        op.f(f"ck_{table}_verification_status"),
        table,
        "verification_status IN ('UNVERIFIED', 'VERIFIED')",
    )
    op.create_check_constraint(
        op.f(f"ck_{table}_verification_attributed"), table, VERIFIED_IS_ATTRIBUTED
    )
    op.create_check_constraint(op.f(f"ck_{table}_name_key_not_empty"), table, "name_key <> ''")
    op.create_foreign_key(op.f(f"fk_{table}_verified_by"), table, "users", ["verified_by"], ["id"])


def _drop_directory_columns(table: str) -> None:
    op.drop_constraint(op.f(f"fk_{table}_verified_by"), table, type_="foreignkey")
    op.drop_constraint(op.f(f"ck_{table}_name_key_not_empty"), table, type_="check")
    op.drop_constraint(op.f(f"ck_{table}_verification_attributed"), table, type_="check")
    op.drop_constraint(op.f(f"ck_{table}_verification_status"), table, type_="check")
    for column in ("source_note", "verified_by", "verified_at", "verification_status", "name_key"):
        op.drop_column(table, column)


def upgrade() -> None:
    # --- localities ---------------------------------------------------
    op.add_column("localities", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "localities",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "localities",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    _add_directory_columns("localities")
    op.drop_constraint(op.f("uq_localities_name_city_state"), "localities", type_="unique")
    op.create_unique_constraint(
        op.f("uq_localities_name_key_city_state"), "localities", ["name_key", "city", "state"]
    )

    # --- societies ----------------------------------------------------
    op.add_column(
        "societies", sa.Column("community_type", sa.String(length=30), nullable=True)
    )
    op.create_check_constraint(
        op.f("ck_societies_community_type"),
        "societies",
        "community_type IN ('APARTMENT_COMPLEX', 'VILLA_COMMUNITY')",
    )
    _add_directory_columns("societies")
    op.drop_constraint(op.f("uq_societies_locality_id_name"), "societies", type_="unique")
    op.create_unique_constraint(op.f("uq_societies_name_key"), "societies", ["name_key"])

    # --- change history -----------------------------------------------
    op.create_table(
        "directory_events",
        sa.Column("sequence", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("locality_id", sa.Uuid(), nullable=True),
        sa.Column("society_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column(
            "action",
            sa.Enum(
                "CREATED",
                "UPDATED",
                "VERIFIED",
                "UNVERIFIED",
                "ACTIVATED",
                "DEACTIVATED",
                name="action",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "num_nonnulls(locality_id, society_id) = 1",
            name=op.f("ck_directory_events_exactly_one_subject"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_directory_events_actor_id")
        ),
        sa.ForeignKeyConstraint(
            ["locality_id"],
            ["localities.id"],
            name=op.f("fk_directory_events_locality_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["society_id"],
            ["societies.id"],
            name=op.f("fk_directory_events_society_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_directory_events")),
    )
    op.create_index(
        "ix_directory_events_locality_id", "directory_events", ["locality_id"], unique=False
    )
    op.create_index(
        "ix_directory_events_society_id", "directory_events", ["society_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_directory_events_society_id", table_name="directory_events")
    op.drop_index("ix_directory_events_locality_id", table_name="directory_events")
    op.drop_table("directory_events")

    op.drop_constraint(op.f("uq_societies_name_key"), "societies", type_="unique")
    op.create_unique_constraint(
        op.f("uq_societies_locality_id_name"), "societies", ["locality_id", "name"]
    )
    _drop_directory_columns("societies")
    op.drop_constraint(op.f("ck_societies_community_type"), "societies", type_="check")
    op.drop_column("societies", "community_type")

    op.drop_constraint(op.f("uq_localities_name_key_city_state"), "localities", type_="unique")
    op.create_unique_constraint(
        op.f("uq_localities_name_city_state"), "localities", ["name", "city", "state"]
    )
    _drop_directory_columns("localities")
    op.drop_column("localities", "updated_at")
    op.drop_column("localities", "created_at")
    op.drop_column("localities", "description")
