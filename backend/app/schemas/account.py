"""Request and response shapes for sign-in, the account and the profile.

Response classes are allow-lists: only the fields written here can ever be
returned. None of them includes a password hash, a session token, a date
of birth or a storage reference.
"""

import uuid
from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import (
    CleanlinessLevel,
    DocumentType,
    FoodPreference,
    GuestFrequency,
    HabitFrequency,
    RoomType,
    SleepSchedule,
    SocialPreference,
    UserRole,
)
from app.schemas.listing import SocietyPublic

BIO_MAX_LENGTH = 500
MAX_SOCIETIES = 5
MIN_BUDGET = 1000
MAX_BUDGET = 100000

Gender = Literal["WOMAN", "MAN", "NON_BINARY"]

# What the account's owner sees for one of their own verifications.
OwnVerificationStatus = Literal[
    "NOT_SUBMITTED", "PENDING", "APPROVED", "REJECTED", "NEEDS_RESUBMISSION"
]


def _blank_to_none(value: object) -> object:
    """Treat an empty or all-spaces string as "not provided"."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


# --- Sign-in -----------------------------------------------------------


class RegisterRequest(BaseModel):
    email: str = Field(max_length=320)
    # Length and strength are checked by the auth service, which returns a
    # friendlier message than a generic validation error.
    password: str = Field(max_length=1024)
    accepted_terms: bool


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


class EmailRequest(BaseModel):
    email: str = Field(max_length=320)


class TokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)
    new_password: str = Field(max_length=1024)


class MessageResponse(BaseModel):
    message: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    email_verified: bool


class SessionOut(BaseModel):
    user: UserOut
    # Must be sent back in the X-CSRF-Token header on every change.
    csrf_token: str


# --- Profile -----------------------------------------------------------


class ProfileIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    college_name: str = Field(min_length=1, max_length=180)
    course: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    academic_year: int | None = Field(default=None, ge=1, le=8)
    bio: str | None = Field(default=None, max_length=BIO_MAX_LENGTH)
    gender: Gender | None = None
    gender_visible: bool = False

    _strip = field_validator(
        "full_name", "college_name", "course", "department", "bio", "gender", mode="before"
    )(_blank_to_none)


class ProfileOut(BaseModel):
    full_name: str
    college_name: str
    course: str | None
    department: str | None
    academic_year: int | None
    bio: str | None
    gender: str | None
    gender_visible: bool
    profile_completed: bool


class PreferencesIn(BaseModel):
    min_budget: int | None = Field(default=None, ge=MIN_BUDGET, le=MAX_BUDGET)
    max_budget: int | None = Field(default=None, ge=MIN_BUDGET, le=MAX_BUDGET)
    move_in_date: date | None = None
    room_type: RoomType | None = None
    food_preference: FoodPreference | None = None
    smoking_preference: HabitFrequency | None = None
    drinking_preference: HabitFrequency | None = None
    sleep_schedule: SleepSchedule | None = None
    cleanliness_level: CleanlinessLevel | None = None
    social_preference: SocialPreference | None = None
    guest_frequency: GuestFrequency | None = None

    _strip = field_validator("*", mode="before")(_blank_to_none)

    @model_validator(mode="after")
    def budget_is_ordered(self) -> Self:
        if (
            self.min_budget is not None
            and self.max_budget is not None
            and self.min_budget > self.max_budget
        ):
            raise ValueError("The maximum budget must be at least the minimum.")
        return self


class PreferencesOut(PreferencesIn):
    pass


class SocietyPreferencesIn(BaseModel):
    # Most preferred first. The position in the list becomes the priority.
    society_ids: list[uuid.UUID] = Field(max_length=MAX_SOCIETIES)

    @field_validator("society_ids")
    @classmethod
    def no_duplicates(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Each society can only be chosen once.")
        return value


class SocietyPreferenceOut(BaseModel):
    society: SocietyPublic
    priority: int
    # False when the society has since been unverified or switched off. It
    # stays in the person's list (nothing is deleted behind their back) but
    # no longer counts, and the app asks them to choose again.
    available: bool


# --- Verification, as seen by the account's owner ------------------------


class DocumentOut(BaseModel):
    """Facts about an uploaded file. Never its storage location."""

    id: uuid.UUID
    document_type: DocumentType
    original_filename: str | None
    content_type: str
    size_bytes: int
    created_at: datetime


class OwnVerificationOut(BaseModel):
    status: OwnVerificationStatus
    submitted_at: datetime | None = None
    documents: list[DocumentOut] = []


class OwnVerificationsOut(BaseModel):
    # Two separate checks. Neither implies the other.
    identity: OwnVerificationOut
    student: OwnVerificationOut


class AccountOut(BaseModel):
    """Everything the signed-in person needs about their own account."""

    user: UserOut
    profile: ProfileOut | None
    preferences: PreferencesOut | None
    societies: list[SocietyPreferenceOut]
    verifications: OwnVerificationsOut
