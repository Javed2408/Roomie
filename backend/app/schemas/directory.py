"""Request and response shapes for the society directory.

Public shapes are allow-lists: they never include a society's address,
coordinates, source notes or who verified it. Admin shapes include those,
and are returned only by admin endpoints.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, ClassVar, Self

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.models.enums import CommunityType, DirectoryAction, DirectoryStatus
from app.schemas.listing import SocietyPublic

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
SocietyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=180)]
PostalCode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]
Description = Annotated[str, StringConstraints(max_length=2000)]
SourceNote = Annotated[str, StringConstraints(max_length=4000)]
Note = Annotated[str, StringConstraints(max_length=2000)]


# --- Public -------------------------------------------------------------


class LocalityPublicOut(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    description: str | None
    # How many societies students can choose in this locality.
    society_count: int


class SocietyDirectoryOut(SocietyPublic):
    """A society as shown in the directory and the society picker."""

    community_type: CommunityType | None
    description: str | None


# --- Admin requests -----------------------------------------------------


class _RejectNulls(BaseModel):
    """For edits: a field may be left out, but a required one cannot be cleared."""

    required_if_given: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _no_null_for_required(self) -> Self:
        for name in self.required_if_given:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be empty.")
        return self


class LocalityCreateIn(BaseModel):
    name: ShortText
    city: ShortText
    state: ShortText
    postal_code: PostalCode | None = None
    description: Description | None = None
    source_note: SourceNote | None = None
    note: Note | None = None


class LocalityUpdateIn(_RejectNulls):
    required_if_given = ("name", "city", "state")

    name: ShortText | None = None
    city: ShortText | None = None
    state: ShortText | None = None
    postal_code: PostalCode | None = None
    description: Description | None = None
    source_note: SourceNote | None = None
    # Why the change was made; kept in the history.
    note: Note | None = None


class SocietyCreateIn(BaseModel):
    locality_id: uuid.UUID
    name: SocietyName
    community_type: CommunityType | None = None
    address: Annotated[str, StringConstraints(max_length=500)] | None = None
    latitude: Annotated[Decimal, Field(ge=-90, le=90, decimal_places=6)] | None = None
    longitude: Annotated[Decimal, Field(ge=-180, le=180, decimal_places=6)] | None = None
    description: Description | None = None
    source_note: SourceNote | None = None
    note: Note | None = None


class SocietyUpdateIn(_RejectNulls):
    required_if_given = ("name", "locality_id")

    locality_id: uuid.UUID | None = None
    name: SocietyName | None = None
    community_type: CommunityType | None = None
    address: Annotated[str, StringConstraints(max_length=500)] | None = None
    latitude: Annotated[Decimal, Field(ge=-90, le=90, decimal_places=6)] | None = None
    longitude: Annotated[Decimal, Field(ge=-180, le=180, decimal_places=6)] | None = None
    description: Description | None = None
    source_note: SourceNote | None = None
    note: Note | None = None


class DirectoryActionIn(BaseModel):
    """Body for verify, unverify, activate and deactivate."""

    note: Note | None = None


# --- Admin responses ----------------------------------------------------


class DirectoryEventOut(BaseModel):
    action: DirectoryAction
    # None means a server-side import script made the change.
    actor_email: str | None
    changes: dict[str, Any] | None
    note: str | None
    created_at: datetime


class _AdminRecordOut(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool
    verification_status: DirectoryStatus
    verified_at: datetime | None
    verified_by_email: str | None
    source_note: str | None
    # True only when students can currently see this record.
    is_public: bool
    created_at: datetime
    updated_at: datetime


class LocalityAdminOut(_AdminRecordOut):
    city: str
    state: str
    postal_code: str | None
    description: str | None
    society_count: int


class SocietyAdminOut(_AdminRecordOut):
    locality_id: uuid.UUID
    locality_name: str
    community_type: CommunityType | None
    address: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    description: str | None
    # How many people currently have it among their preferred societies.
    chosen_by_count: int


class LocalityAdminDetail(LocalityAdminOut):
    history: list[DirectoryEventOut]


class SocietyAdminDetail(SocietyAdminOut):
    history: list[DirectoryEventOut]
