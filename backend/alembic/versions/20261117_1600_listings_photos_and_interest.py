"""listings, photos and interest

Phase 6. Adds to existing tables rather than creating parallel ones:

* accommodation_listings: `facilities` (a fixed list of values),
  `brokerage_payable_to` (who receives a brokerage fee) and
  `authority_declared_at` (when the creator declared their right to list
  the property). The database refuses a fee without a named recipient, a
  recipient without a fee, and an owner or tenant naming themselves as the
  recipient.
* listing_authority_verifications: for tenants, the reviewer's record of
  why the tenant may take someone in (`tenant_permission_basis`) and the
  rental agreement's end date (`rental_agreement_valid_until`).
* listing_images: the re-encoded photo's type, size and dimensions, and a
  unique storage key.
* listing_interests: `updated_at`, `responded_at`, and the brokerage amount
  the student was shown when they expressed interest.
* listing_changes (new): an append-only history of every edit a creator
  makes to a listing, including brokerage changes.

listing_images had no way to be filled before this phase, so its new
NOT NULL columns need no default. No existing rows are changed or removed.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-17 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FACILITIES = (
    "WIFI",
    "AIR_CONDITIONING",
    "WASHING_MACHINE",
    "REFRIGERATOR",
    "KITCHEN",
    "WATER_PURIFIER",
    "GEYSER",
    "POWER_BACKUP",
    "LIFT",
    "PARKING",
    "SECURITY",
    "HOUSEKEEPING",
)
FACILITIES_SQL = "ARRAY[" + ", ".join(f"'{item}'" for item in FACILITIES) + "]::varchar[]"


def upgrade() -> None:
    # --- accommodation_listings ---
    op.add_column(
        "accommodation_listings",
        sa.Column("brokerage_payable_to", sa.String(length=30), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_accommodation_listings_brokerage_payable_to"),
        "accommodation_listings",
        "brokerage_payable_to IN ('LISTING_CREATOR', 'THIRD_PARTY_AGENT')",
    )
    op.create_check_constraint(
        op.f("ck_accommodation_listings_brokerage_payee_matches_flag"),
        "accommodation_listings",
        "(brokerage_applicable IS TRUE AND brokerage_payable_to IS NOT NULL) "
        "OR (brokerage_applicable IS NOT TRUE AND brokerage_payable_to IS NULL)",
    )
    op.create_check_constraint(
        op.f("ck_accommodation_listings_only_agents_collect_brokerage"),
        "accommodation_listings",
        "brokerage_payable_to IS DISTINCT FROM 'LISTING_CREATOR' "
        "OR creator_type = 'AUTHORIZED_AGENT'",
    )
    op.add_column(
        "accommodation_listings",
        sa.Column(
            "facilities",
            sa.ARRAY(sa.String(length=30)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_accommodation_listings_facilities_known"),
        "accommodation_listings",
        f"facilities <@ {FACILITIES_SQL}",
    )
    op.add_column(
        "accommodation_listings",
        sa.Column("authority_declared_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Existing property listings (none exist before this phase, which had no
    # way to create one) would need a declaration before this check passes.
    op.create_check_constraint(
        op.f("ck_accommodation_listings_property_authority_declared"),
        "accommodation_listings",
        "NOT (listing_type = 'EXISTING_ACCOMMODATION') OR authority_declared_at IS NOT NULL",
    )

    # --- listing_authority_verifications (tenants) ---
    op.add_column(
        "listing_authority_verifications",
        sa.Column("tenant_permission_basis", sa.String(length=30), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_listing_authority_verifications_tenant_permission_basis"),
        "listing_authority_verifications",
        "tenant_permission_basis IN ('AGREEMENT_PERMITS_SHARING', 'LANDLORD_PERMISSION')",
    )
    op.add_column(
        "listing_authority_verifications",
        sa.Column("rental_agreement_valid_until", sa.Date(), nullable=True),
    )

    # --- listing_images ---
    op.add_column("listing_images", sa.Column("content_type", sa.String(50), nullable=False))
    op.add_column("listing_images", sa.Column("width", sa.SmallInteger(), nullable=False))
    op.add_column("listing_images", sa.Column("height", sa.SmallInteger(), nullable=False))
    op.add_column("listing_images", sa.Column("size_bytes", sa.Integer(), nullable=False))
    op.create_check_constraint(
        op.f("ck_listing_images_dimensions_positive"),
        "listing_images",
        "width > 0 AND height > 0",
    )
    op.create_check_constraint(
        op.f("ck_listing_images_size_positive"), "listing_images", "size_bytes > 0"
    )
    op.create_unique_constraint(
        op.f("uq_listing_images_object_key"), "listing_images", ["object_key"]
    )

    # --- listing_interests ---
    op.add_column(
        "listing_interests",
        sa.Column("acknowledged_brokerage_amount", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_listing_interests_acknowledged_brokerage_positive"),
        "listing_interests",
        "acknowledged_brokerage_amount IS NULL OR acknowledged_brokerage_amount > 0",
    )
    op.add_column(
        "listing_interests",
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "listing_interests",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_listing_interests_user_id", "listing_interests", ["user_id"])

    # --- listing_changes ---
    op.create_table(
        "listing_changes",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sequence", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["accommodation_listings.id"],
            name=op.f("fk_listing_changes_listing_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_listing_changes_actor_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listing_changes")),
    )
    op.create_index("ix_listing_changes_listing_id", "listing_changes", ["listing_id"])


def downgrade() -> None:
    op.drop_index("ix_listing_changes_listing_id", table_name="listing_changes")
    op.drop_table("listing_changes")

    op.drop_index("ix_listing_interests_user_id", table_name="listing_interests")
    op.drop_column("listing_interests", "updated_at")
    op.drop_column("listing_interests", "responded_at")
    op.drop_constraint(
        op.f("ck_listing_interests_acknowledged_brokerage_positive"),
        "listing_interests",
        type_="check",
    )
    op.drop_column("listing_interests", "acknowledged_brokerage_amount")

    op.drop_constraint(op.f("uq_listing_images_object_key"), "listing_images", type_="unique")
    op.drop_constraint(op.f("ck_listing_images_size_positive"), "listing_images", type_="check")
    op.drop_constraint(
        op.f("ck_listing_images_dimensions_positive"), "listing_images", type_="check"
    )
    for column in ("size_bytes", "height", "width", "content_type"):
        op.drop_column("listing_images", column)

    op.drop_column("listing_authority_verifications", "rental_agreement_valid_until")
    op.drop_constraint(
        op.f("ck_listing_authority_verifications_tenant_permission_basis"),
        "listing_authority_verifications",
        type_="check",
    )
    op.drop_column("listing_authority_verifications", "tenant_permission_basis")

    for name in (
        "property_authority_declared",
        "facilities_known",
        "only_agents_collect_brokerage",
        "brokerage_payee_matches_flag",
        "brokerage_payable_to",
    ):
        op.drop_constraint(
            op.f(f"ck_accommodation_listings_{name}"), "accommodation_listings", type_="check"
        )
    op.drop_column("accommodation_listings", "authority_declared_at")
    op.drop_column("accommodation_listings", "facilities")
    op.drop_column("accommodation_listings", "brokerage_payable_to")
