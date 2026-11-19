"""Accommodation listings and the tables that hang off them."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    ColumnElement,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    and_,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UuidPrimaryKeyMixin, enum_type
from app.models.enums import (
    BrokeragePayableTo,
    Facility,
    Furnishing,
    ListingCreatorType,
    ListingInterestStatus,
    ListingLifecycleStatus,
    ListingType,
    ModerationStatus,
)

if TYPE_CHECKING:
    from app.models.society import Society
    from app.models.user import User
    from app.models.verification import ListingAuthorityVerification

_IS_PROPERTY = "listing_type = 'EXISTING_ACCOMMODATION'"
_IS_SEARCH = "listing_type = 'LOOKING_TO_RENT_TOGETHER'"
FACILITIES_SQL = "ARRAY[" + ", ".join(f"'{item.value}'" for item in Facility) + "]::varchar[]"


class AccommodationListing(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """Either a real room with space to fill, or a request to rent together.

    The two kinds share a table but have different rules, enforced by the
    constraints below so that invalid combinations cannot be saved at all.
    """

    __tablename__ = "accommodation_listings"
    __table_args__ = (
        # A property states who is offering it. A search request has no
        # creator type, because nobody is offering a property.
        CheckConstraint(
            f"({_IS_PROPERTY} AND creator_type IS NOT NULL) "
            f"OR ({_IS_SEARCH} AND creator_type IS NULL)",
            name="creator_type_matches_listing_type",
        ),
        CheckConstraint(
            f"NOT ({_IS_PROPERTY}) OR society_id IS NOT NULL",
            name="property_has_society",
        ),
        # Brokerage must be disclosed for every property, either way...
        CheckConstraint(
            f"({_IS_PROPERTY} AND brokerage_applicable IS NOT NULL) "
            f"OR ({_IS_SEARCH} AND brokerage_applicable IS NULL)",
            name="brokerage_disclosed_for_property",
        ),
        # ...and if it applies, the amount must be stated. "IS NOT NULL" is
        # essential: a missing amount compared with 0 is "unknown" in SQL,
        # and a CHECK lets "unknown" through.
        CheckConstraint(
            "(brokerage_applicable IS TRUE AND brokerage_amount IS NOT NULL "
            "AND brokerage_amount > 0) "
            "OR (brokerage_applicable IS NOT TRUE AND brokerage_amount IS NULL)",
            name="brokerage_amount_matches_flag",
        ),
        # Who receives the fee is stated whenever brokerage applies...
        CheckConstraint(
            "(brokerage_applicable IS TRUE AND brokerage_payable_to IS NOT NULL) "
            "OR (brokerage_applicable IS NOT TRUE AND brokerage_payable_to IS NULL)",
            name="brokerage_payee_matches_flag",
        ),
        # ...and only an authorised agent may collect it themselves. An owner
        # or tenant charging "brokerage" would be an unauthorised broker.
        CheckConstraint(
            "brokerage_payable_to IS DISTINCT FROM 'LISTING_CREATOR' "
            "OR creator_type = 'AUTHORIZED_AGENT'",
            name="only_agents_collect_brokerage",
        ),
        CheckConstraint(f"facilities <@ {FACILITIES_SQL}", name="facilities_known"),
        # The creator's declaration that they may list the property is kept,
        # with when it was made.
        CheckConstraint(
            f"NOT ({_IS_PROPERTY}) OR authority_declared_at IS NOT NULL",
            name="property_authority_declared",
        ),
        CheckConstraint("rent_per_person > 0", name="rent_per_person_positive"),
        CheckConstraint("total_rent IS NULL OR total_rent > 0", name="total_rent_positive"),
        CheckConstraint("deposit IS NULL OR deposit >= 0", name="deposit_non_negative"),
        CheckConstraint(
            "bedroom_count IS NULL OR bedroom_count > 0", name="bedroom_count_positive"
        ),
        CheckConstraint(
            "available_bedrooms IS NULL OR available_bedrooms > 0",
            name="available_bedrooms_positive",
        ),
        CheckConstraint(
            "available_bedrooms IS NULL OR bedroom_count IS NULL "
            "OR available_bedrooms <= bedroom_count",
            name="available_bedrooms_within_total",
        ),
        CheckConstraint("current_group_size >= 0", name="current_group_size_non_negative"),
        CheckConstraint("required_roommates > 0", name="required_roommates_positive"),
        # Serves public browsing, which always filters on both statuses.
        Index(
            "ix_accommodation_listings_public_browse",
            "lifecycle_status",
            "moderation_status",
            "listing_type",
            "available_from",
        ),
        # Serves the admin review queue, oldest first.
        Index("ix_accommodation_listings_moderation_queue", "moderation_status", "created_at"),
        Index("ix_accommodation_listings_society_id", "society_id"),
        Index("ix_accommodation_listings_owner_id", "owner_id"),
    )

    # The account that created the listing, whatever their creator type.
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    listing_type: Mapped[ListingType] = mapped_column(
        enum_type(ListingType, "listing_type", 30), nullable=False
    )
    creator_type: Mapped[ListingCreatorType | None] = mapped_column(
        enum_type(ListingCreatorType, "creator_type", 20)
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    # Must never contain a flat number or exact address.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    society_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("societies.id"))

    # Money is in whole rupees. For a search request, `rent_per_person`
    # holds the budget per person.
    total_rent: Mapped[int | None] = mapped_column(Integer)
    rent_per_person: Mapped[int] = mapped_column(Integer, nullable=False)
    deposit: Mapped[int | None] = mapped_column(Integer)
    brokerage_applicable: Mapped[bool | None] = mapped_column(Boolean)
    brokerage_amount: Mapped[int | None] = mapped_column(Integer)
    # How the fee is worked out, e.g. "one month's rent, shared".
    brokerage_note: Mapped[str | None] = mapped_column(String(255))
    brokerage_payable_to: Mapped[BrokeragePayableTo | None] = mapped_column(
        enum_type(BrokeragePayableTo, "brokerage_payable_to", 30)
    )

    bedroom_count: Mapped[int | None] = mapped_column(SmallInteger)
    available_bedrooms: Mapped[int | None] = mapped_column(SmallInteger)
    furnishing: Mapped[Furnishing | None] = mapped_column(enum_type(Furnishing, "furnishing", 20))
    # When the creator declared they have the right to list this property.
    # A declaration only: the evidence is checked separately by a person.
    authority_declared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Values from `Facility`; the CHECK above refuses anything else.
    facilities: Mapped[list[str]] = mapped_column(
        ARRAY(String(30)), nullable=False, default=list, server_default=text("'{}'")
    )
    available_from: Mapped[date] = mapped_column(Date, nullable=False)
    current_group_size: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    required_roommates: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # --- Two independent statuses. Never merge these into one. ---
    # Set by the creator: is this still available?
    lifecycle_status: Mapped[ListingLifecycleStatus] = mapped_column(
        enum_type(ListingLifecycleStatus, "lifecycle_status", 20),
        nullable=False,
        default=ListingLifecycleStatus.DRAFT,
        server_default=ListingLifecycleStatus.DRAFT.value,
    )
    # Set by administrators: is this allowed to be shown?
    moderation_status: Mapped[ModerationStatus] = mapped_column(
        enum_type(ModerationStatus, "moderation_status", 20),
        nullable=False,
        default=ModerationStatus.PENDING,
        server_default=ModerationStatus.PENDING.value,
    )

    owner: Mapped[User] = relationship()
    society: Mapped[Society | None] = relationship()
    authority_verification: Mapped[ListingAuthorityVerification | None] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )
    society_preferences: Mapped[list[ListingSocietyPreference]] = relationship(
        cascade="all, delete-orphan", order_by="ListingSocietyPreference.priority"
    )
    images: Mapped[list[ListingImage]] = relationship(
        cascade="all, delete-orphan", order_by="ListingImage.sort_order"
    )

    @hybrid_property
    def is_publicly_visible(self) -> bool:
        """THE visibility rule: active AND approved, and nothing else.

        Every public query must filter on this. Written as a "hybrid", it
        works both on a loaded listing (`listing.is_publicly_visible`) and
        inside a database query
        (`select(...).where(AccommodationListing.is_publicly_visible)`),
        so the rule exists in exactly one place.
        """
        return (
            self.lifecycle_status == ListingLifecycleStatus.ACTIVE
            and self.moderation_status == ModerationStatus.APPROVED
        )

    @is_publicly_visible.inplace.expression
    @classmethod
    def _is_publicly_visible_expression(cls) -> ColumnElement[bool]:
        return and_(
            cls.lifecycle_status == ListingLifecycleStatus.ACTIVE,
            cls.moderation_status == ModerationStatus.APPROVED,
        )


class ListingSocietyPreference(Base):
    """A society that a "looking to rent together" post is hoping for."""

    __tablename__ = "listing_society_preferences"
    __table_args__ = (CheckConstraint("priority > 0", name="priority_positive"),)

    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accommodation_listings.id", ondelete="CASCADE"), primary_key=True
    )
    society_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("societies.id"), primary_key=True)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    society: Mapped[Society] = relationship()


class ListingImage(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """A reference to one listing photo held in private photo storage.

    The file is the re-encoded copy made on upload (metadata removed), not
    the original. `object_key` is private and never sent to anyone.
    """

    __tablename__ = "listing_images"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="sort_order_non_negative"),
        CheckConstraint("width > 0 AND height > 0", name="dimensions_positive"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
        UniqueConstraint("object_key"),
        Index("ix_listing_images_listing_id", "listing_id"),
    )

    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accommodation_listings.id", ondelete="CASCADE"), nullable=False
    )
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    width: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    height: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)


class ListingInterest(UuidPrimaryKeyMixin, TimestampMixin, Base):
    """One user saying they are interested in one listing."""

    __tablename__ = "listing_interests"
    __table_args__ = (
        UniqueConstraint("listing_id", "user_id"),
        Index("ix_listing_interests_listing_id_status", "listing_id", "status"),
        Index("ix_listing_interests_user_id", "user_id"),
        CheckConstraint(
            "acknowledged_brokerage_amount IS NULL OR acknowledged_brokerage_amount > 0",
            name="acknowledged_brokerage_positive",
        ),
    )

    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accommodation_listings.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[ListingInterestStatus] = mapped_column(
        enum_type(ListingInterestStatus, "status", 20),
        nullable=False,
        default=ListingInterestStatus.PENDING,
        server_default=ListingInterestStatus.PENDING.value,
    )
    # The brokerage the student was shown, and accepted, when expressing
    # interest. Empty when the listing has no brokerage.
    acknowledged_brokerage_amount: Mapped[int | None] = mapped_column(Integer)
    # When the listing's creator accepted or declined.
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    listing: Mapped[AccommodationListing] = relationship()
    user: Mapped[User] = relationship()


class ListingChange(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """One edit a creator made to their listing: which fields, from what, to
    what. Append-only, so administrators can always see, for example, when a
    brokerage fee was added or changed."""

    __tablename__ = "listing_changes"
    __table_args__ = (Index("ix_listing_changes_listing_id", "listing_id"),)

    # Strictly increasing, so the history reads in the order things happened.
    sequence: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accommodation_listings.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    # {"field": {"from": old, "to": new}}
    changes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
