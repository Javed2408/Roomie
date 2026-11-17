"""The society directory: localities (areas) and the societies inside them.

Both are curated by administrators. A record is shown to students only when
it is BOTH verified (an administrator has confirmed it is accurate) and
active (not switched off). A society also needs its locality to be shown.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ColumnElement,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    and_,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UuidPrimaryKeyMixin, enum_type
from app.models.enums import CommunityType, DirectoryAction, DirectoryStatus

if TYPE_CHECKING:
    from app.models.user import User


def normalise_name(name: str) -> str:
    """The form of a name used to spot duplicates.

    Lower case, with every run of punctuation or spaces turned into one
    space: "Abode-Valley ", "abode valley" and "ABODE  VALLEY" all become
    "abode valley". It cannot catch genuinely different spellings
    ("Guduvanchery" and "Guduvancheri"); an administrator must review those.

    The database migration that filled this column for existing rows uses
    the same rule in SQL. Keep the two identical.
    """
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


class DirectoryRecordMixin(TimestampMixin):
    """Columns shared by localities and societies."""

    # Filled in automatically from `name` (see `normalise_name`).
    name_key: Mapped[str] = mapped_column(String(180), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    verification_status: Mapped[DirectoryStatus] = mapped_column(
        enum_type(DirectoryStatus, "verification_status", 20),
        nullable=False,
        default=DirectoryStatus.UNVERIFIED,
        server_default=DirectoryStatus.UNVERIFIED.value,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The administrator who confirmed the record.
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    # Where the information came from (web pages, a site visit, ...).
    # For administrators only; never shown publicly.
    source_note: Mapped[str | None] = mapped_column(Text)

    @hybrid_property
    def is_listed(self) -> bool:
        """Verified and active: allowed to be shown, as far as this record goes."""
        return self.verification_status == DirectoryStatus.VERIFIED and self.is_active

    @is_listed.inplace.expression
    @classmethod
    def _is_listed_expression(cls) -> ColumnElement[bool]:
        return and_(cls.verification_status == DirectoryStatus.VERIFIED, cls.is_active.is_(True))


# A verified record must say who verified it and when.
def _verification_is_attributed() -> CheckConstraint:
    return CheckConstraint(
        "verification_status = 'UNVERIFIED' "
        "OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)",
        name="verification_attributed",
    )


def _name_key_not_empty() -> CheckConstraint:
    return CheckConstraint("name_key <> ''", name="name_key_not_empty")


class Locality(UuidPrimaryKeyMixin, DirectoryRecordMixin, Base):
    """An area, such as Potheri or Guduvanchery."""

    __tablename__ = "localities"
    __table_args__ = (
        # One record per area: "SRM Nagar" and "srm-nagar" cannot both exist.
        UniqueConstraint("name_key", "city", "state"),
        _verification_is_attributed(),
        _name_key_not_empty(),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(120), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)

    societies: Mapped[list[Society]] = relationship(back_populates="locality")

    @validates("name")
    def _set_name_key(self, _key: str, value: str) -> str:
        self.name_key = normalise_name(value)
        return value


class Society(UuidPrimaryKeyMixin, DirectoryRecordMixin, Base):
    """One named residential development inside a locality."""

    __tablename__ = "societies"
    __table_args__ = (
        # Unique across the whole directory, not just within one area: the
        # same complex filed under two neighbouring areas is a duplicate.
        UniqueConstraint("name_key"),
        _verification_is_attributed(),
        _name_key_not_empty(),
        Index("ix_societies_locality_id_is_active", "locality_id", "is_active"),
    )

    locality_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("localities.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    # Unknown until confirmed. Required before the record can be verified.
    community_type: Mapped[CommunityType | None] = mapped_column(
        enum_type(CommunityType, "community_type", 30)
    )
    # Private. Public views show the locality and description only.
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    # Public: a short, factual description such as its general location.
    description: Mapped[str | None] = mapped_column(Text)

    locality: Mapped[Locality] = relationship(back_populates="societies")

    @validates("name")
    def _set_name_key(self, _key: str, value: str) -> str:
        self.name_key = normalise_name(value)
        return value


class DirectoryEvent(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    """One administrative change to the directory: who, what and why.

    Written for every create, edit, verification and (de)activation. Rows
    are never edited or deleted.
    """

    __tablename__ = "directory_events"
    __table_args__ = (
        CheckConstraint("num_nonnulls(locality_id, society_id) = 1", name="exactly_one_subject"),
        Index("ix_directory_events_locality_id", "locality_id"),
        Index("ix_directory_events_society_id", "society_id"),
    )

    # Strictly increasing, so the history always reads in the order things
    # happened. (Timestamps are not enough: several changes made in one
    # transaction all get the same time.)
    sequence: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    locality_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("localities.id", ondelete="CASCADE")
    )
    society_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("societies.id", ondelete="CASCADE")
    )
    # The administrator. Empty only for changes made by a server-side
    # import script, which then names itself in `note`.
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[DirectoryAction] = mapped_column(
        enum_type(DirectoryAction, "action", 20), nullable=False
    )
    # For edits: {"field": {"from": old, "to": new}}.
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    note: Mapped[str | None] = mapped_column(Text)

    actor: Mapped[User | None] = relationship()
