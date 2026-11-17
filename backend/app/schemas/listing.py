"""What a listing looks like to the public.

These classes are an allow-list. A field that is not written here cannot
leak into a response, however the database model changes later. Notice
what is deliberately absent: the moderation status and its reason, the
owner's name and contact details, any document or storage key, and any
exact address.

They mirror the TypeScript types in frontend/types/listing.ts.
"""

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.models.enums import Furnishing, ListingCreatorType, ListingType

PublicVerificationState = Literal["NOT_VERIFIED", "PENDING", "VERIFIED"]


class LocalityPublic(BaseModel):
    id: uuid.UUID
    name: str
    city: str


class SocietyPublic(BaseModel):
    id: uuid.UUID
    name: str
    locality: LocalityPublic


class ListingPosterPublic(BaseModel):
    id: uuid.UUID
    display_name: str
    # Named for the specific check, never a generic "verified".
    identity_verification: PublicVerificationState


class BrokeragePublic(BaseModel):
    """Always present on a property, including when there is none."""

    applicable: bool
    amount: int | None = None
    note: str | None = None


class ListingPublic(BaseModel):
    id: uuid.UUID
    type: ListingType
    title: str
    description: str
    posted_by: ListingPosterPublic
    available_from: date
    # Rent for a property; budget per person for a search request.
    rent_per_person: int

    # --- Only for EXISTING_ACCOMMODATION ---
    creator_type: ListingCreatorType | None = None
    listing_authority: PublicVerificationState | None = None
    society: SocietyPublic | None = None
    deposit: int | None = None
    brokerage: BrokeragePublic | None = None
    bedroom_count: int | None = None
    available_bedrooms: int | None = None
    furnishing: Furnishing | None = None

    # --- Only for LOOKING_TO_RENT_TOGETHER ---
    preferred_societies: list[SocietyPublic] = []
    current_group_size: int | None = None
    required_roommates: int | None = None
