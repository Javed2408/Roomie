"""Listings: what the public may see, what a creator sends and sees.

These classes are allow-lists. A field that is not written here cannot
leak into a response, however the database model changes later. Notice
what is deliberately absent from the PUBLIC shapes: the moderation status
and its reason, the owner's name and contact details, any document, storage
key or file path, and any exact address.

They mirror the TypeScript types in frontend/types/listing.ts.
"""

import re
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

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

PublicVerificationState = Literal["NOT_VERIFIED", "PENDING", "VERIFIED"]

TITLE_MAX_LENGTH = 80
DESCRIPTION_MAX_LENGTH = 1000
MIN_RENT = 1000
MAX_RENT = 100000
MAX_ROOMS = 10
MAX_SEARCH_SOCIETIES = 5
# How far ahead a listing may say it is available.
MAX_DAYS_AHEAD = 366

# Contact details in a listing would let a broker take the conversation
# off Roomie before anyone's authority has been checked.
_PHONE = re.compile(r"(?:\+?91[\s-]?)?(?<!\d)[6-9]\d{4}[\s-]?\d{5}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


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
    # Shown on requests to rent together, which come from students.
    student_verification: PublicVerificationState | None = None


class BrokeragePublic(BaseModel):
    """Always present on a property, including when there is none."""

    applicable: bool
    amount: int | None = None
    note: str | None = None
    # Who receives the fee: the person who posted (an authorised agent),
    # or another agent.
    payable_to: BrokeragePayableTo | None = None


class ListingPhotoOut(BaseModel):
    id: uuid.UUID
    # An API address that checks who is asking. Never a storage path.
    url: str
    width: int
    height: int


class ListingPublic(BaseModel):
    id: uuid.UUID
    type: ListingType
    title: str
    description: str
    posted_by: ListingPosterPublic
    available_from: date
    # Rent for a property; budget per person for a search request.
    rent_per_person: int
    photos: list[ListingPhotoOut] = []

    # --- Only for EXISTING_ACCOMMODATION ---
    creator_type: ListingCreatorType | None = None
    listing_authority: PublicVerificationState | None = None
    society: SocietyPublic | None = None
    total_rent: int | None = None
    deposit: int | None = None
    brokerage: BrokeragePublic | None = None
    bedroom_count: int | None = None
    available_bedrooms: int | None = None
    furnishing: Furnishing | None = None
    facilities: list[Facility] = []

    # --- Only for LOOKING_TO_RENT_TOGETHER ---
    preferred_societies: list[SocietyPublic] = []

    # For a property: people living there now. For a search: the group so far.
    current_group_size: int | None = None
    # How many more people are wanted.
    required_roommates: int | None = None


class ListingViewOut(BaseModel):
    """One public listing, as one signed-in member sees it."""

    listing: ListingPublic
    is_yours: bool
    # Your own interest in it, if any. Nobody else's is ever shown here.
    your_interest: ListingInterestStatus | None


class ListingPageOut(BaseModel):
    items: list[ListingPublic]
    total: int
    limit: int
    offset: int


# --- What a creator sends ----------------------------------------------------


def _clean_text(value: str) -> str:
    return " ".join(value.split()) if "\n" not in value else value.strip()


def _no_contact_details(value: str) -> str:
    if _PHONE.search(value) or _EMAIL.search(value):
        raise ValueError(
            "Remove phone numbers and email addresses. People contact you through Roomie."
        )
    return value


Title = Annotated[str, Field(min_length=1, max_length=TITLE_MAX_LENGTH)]
Description = Annotated[str, Field(min_length=1, max_length=DESCRIPTION_MAX_LENGTH)]
Rent = Annotated[int, Field(ge=MIN_RENT, le=MAX_RENT)]
Rooms = Annotated[int, Field(ge=1, le=MAX_ROOMS)]


class _ListingInBase(BaseModel):
    title: Title
    description: Description

    @field_validator("title", "description")
    @classmethod
    def tidy_and_check(cls, value: str) -> str:
        value = _clean_text(value)
        if not value:
            raise ValueError("This cannot be empty.")
        return _no_contact_details(value)

    @staticmethod
    def _check_date(value: date, what: str) -> date:
        today = datetime.now(UTC).date()
        if value < today - timedelta(days=1):
            raise ValueError(f"The {what} cannot be in the past.")
        if value > today + timedelta(days=MAX_DAYS_AHEAD):
            raise ValueError(f"The {what} must be within a year.")
        return value


class PropertyListingIn(_ListingInBase):
    """A real room with space to fill (type A)."""

    listing_type: Literal[ListingType.EXISTING_ACCOMMODATION]
    creator_type: ListingCreatorType
    society_id: uuid.UUID
    rent_per_person: Rent
    total_rent: Annotated[int, Field(ge=MIN_RENT, le=10 * MAX_RENT)] | None = None
    deposit: Annotated[int, Field(ge=0, le=10 * MAX_RENT)] | None = None
    # Brokerage must always be answered, including "no".
    brokerage_applicable: bool
    brokerage_amount: Annotated[int, Field(ge=1, le=10 * MAX_RENT)] | None = None
    brokerage_payable_to: BrokeragePayableTo | None = None
    brokerage_note: Annotated[str, Field(max_length=255)] | None = None
    bedroom_count: Rooms
    available_bedrooms: Rooms
    furnishing: Furnishing
    facilities: Annotated[list[Facility], Field(max_length=len(Facility))] = []
    available_from: date
    # People living there now, and how many more are wanted.
    current_occupants: Annotated[int, Field(ge=0, le=MAX_ROOMS)]
    roommates_wanted: Rooms
    # The creator states they have the right to list this property. It is
    # a declaration only; evidence is checked separately by a person.
    confirmed_authority: Literal[True]

    @field_validator("available_from")
    @classmethod
    def available_soon(cls, value: date) -> date:
        return cls._check_date(value, "availability date")

    @field_validator("brokerage_note")
    @classmethod
    def tidy_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        return _no_contact_details(value) if value else None

    @field_validator("facilities")
    @classmethod
    def no_repeats(cls, value: list[Facility]) -> list[Facility]:
        if len(set(value)) != len(value):
            raise ValueError("Each facility can only be chosen once.")
        return value

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.available_bedrooms > self.bedroom_count:
            raise ValueError("Rooms available cannot be more than the bedrooms.")
        if self.brokerage_applicable:
            if self.brokerage_amount is None:
                raise ValueError("State the brokerage amount in rupees.")
            if self.brokerage_payable_to is None:
                raise ValueError("Say who receives the brokerage.")
            if (
                self.brokerage_payable_to == BrokeragePayableTo.LISTING_CREATOR
                and self.creator_type != ListingCreatorType.AUTHORIZED_AGENT
            ):
                raise ValueError(
                    "Only an authorised agent can collect brokerage. Owners and "
                    "tenants cannot charge a brokerage fee themselves."
                )
        elif (
            self.brokerage_amount is not None
            or self.brokerage_payable_to is not None
            or self.brokerage_note
        ):
            raise ValueError("Leave the brokerage details empty when there is no brokerage.")
        return self


class SearchListingIn(_ListingInBase):
    """Students who want to find a place together (type B). Not a property."""

    listing_type: Literal[ListingType.LOOKING_TO_RENT_TOGETHER]
    society_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=MAX_SEARCH_SOCIETIES)]
    budget_per_person: Rent
    desired_bedrooms: Rooms
    current_group_size: Rooms
    roommates_wanted: Rooms
    move_in_date: date

    @field_validator("move_in_date")
    @classmethod
    def move_in_soon(cls, value: date) -> date:
        return cls._check_date(value, "move-in date")

    @field_validator("society_ids")
    @classmethod
    def no_duplicate_societies(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Each society can only be chosen once.")
        return value


ListingIn = Annotated[PropertyListingIn | SearchListingIn, Field(discriminator="listing_type")]


class LifecycleIn(BaseModel):
    # DRAFT -> ACTIVE happens only through "submit", which checks evidence.
    status: Literal[
        ListingLifecycleStatus.ACTIVE,
        ListingLifecycleStatus.FILLED,
        ListingLifecycleStatus.CLOSED,
    ]


# --- What a creator sees about their own listing -----------------------------------


class OwnAuthorityOut(BaseModel):
    """The listing authority check, as the creator sees it."""

    status: Literal["NOT_SUBMITTED", "PENDING", "APPROVED", "REJECTED", "NEEDS_RESUBMISSION"]
    # Why it was not approved, when it was not. Written for the creator.
    reason: str | None = None
    # Agents only: whether Roomie has confirmed the authorisation with the owner.
    owner_confirmation: Literal["NOT_REQUIRED", "PENDING", "CONFIRMED", "DENIED"]
    # Document types uploaded so far (never file locations).
    documents: list[str]


class OwnListingEventOut(BaseModel):
    at: datetime
    kind: Literal["moderation", "authority", "edit"]
    summary: str
    # A reason, shown for rejections and suspensions.
    note: str | None = None


class OwnListingOut(BaseModel):
    listing: ListingPublic
    lifecycle_status: ListingLifecycleStatus
    moderation_status: ModerationStatus
    # Why it was rejected or suspended. Only ever shown to its creator.
    moderation_reason: str | None
    is_public: bool
    authority: OwnAuthorityOut | None
    # What is still missing before it can be submitted for review.
    submission_requirements: list[str]
    can_submit: bool
    can_edit: bool
    pending_interests: int
    created_at: datetime
    updated_at: datetime
    history: list[OwnListingEventOut]


class OwnListingSummaryOut(BaseModel):
    id: uuid.UUID
    type: ListingType
    title: str
    lifecycle_status: ListingLifecycleStatus
    moderation_status: ModerationStatus
    moderation_reason: str | None
    is_public: bool
    authority_status: str | None
    pending_interests: int
    cover_photo: ListingPhotoOut | None
    updated_at: datetime


# --- Interest ------------------------------------------------------------------------


class InterestIn(BaseModel):
    # Required when the listing charges brokerage: proof the student saw it.
    acknowledge_brokerage: bool = False


class InterestOut(BaseModel):
    listing_id: uuid.UUID
    status: ListingInterestStatus
    created_at: datetime


class MyInterestOut(BaseModel):
    listing_id: uuid.UUID
    title: str
    type: ListingType
    status: ListingInterestStatus
    # False once the listing is closed, filled, hidden or no longer approved.
    listing_available: bool
    acknowledged_brokerage_amount: int | None
    created_at: datetime
    responded_at: datetime | None


class InterestRespondIn(BaseModel):
    status: Literal[ListingInterestStatus.ACCEPTED, ListingInterestStatus.DECLINED]
