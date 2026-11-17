"""What one student may see about another, and the compatibility result.

These classes are allow-lists: only the fields written here can ever be
returned. Notice what is deliberately absent: email address, date of
birth, a hidden gender, photo storage keys, account status, and any
society that is not currently public. Nothing here reveals whether
someone liked you, unless you have matched.

They mirror the TypeScript types in frontend/types/discovery.ts.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import (
    CleanlinessLevel,
    FoodPreference,
    GuestFrequency,
    HabitFrequency,
    RoomType,
    SleepSchedule,
    SocialPreference,
    SwipeAction,
)
from app.schemas.listing import PublicVerificationState, SocietyPublic
from app.services.compatibility import AreaOverlap, Factor

# --- A student, as other students see them ------------------------------------


class PublicPreferencesOut(BaseModel):
    """The student's own budget, timing and habits. Any may be missing."""

    min_budget: int | None
    max_budget: int | None
    move_in_date: date | None
    room_type: RoomType | None
    food_preference: FoodPreference | None
    smoking_preference: HabitFrequency | None
    drinking_preference: HabitFrequency | None
    sleep_schedule: SleepSchedule | None
    cleanliness_level: CleanlinessLevel | None
    social_preference: SocialPreference | None
    guest_frequency: GuestFrequency | None


class PublicSocietyChoiceOut(BaseModel):
    society: SocietyPublic
    # 1 is their first choice, counted among societies that are public.
    priority: int


class StudentPublicOut(BaseModel):
    id: uuid.UUID
    full_name: str
    college_name: str
    course: str | None
    department: str | None
    academic_year: int | None
    bio: str | None
    # Only when the student chose to show it.
    gender: str | None
    preferences: PublicPreferencesOut
    societies: list[PublicSocietyChoiceOut]
    # Two separate checks, never one combined "verified".
    identity_verification: PublicVerificationState
    student_verification: PublicVerificationState


# --- Compatibility -------------------------------------------------------------


class CompatibilityFactorOut(BaseModel):
    key: Factor
    label: str
    # 0 to 100, or None when it could not be judged.
    score: int | None
    available: bool
    # The configured weight, and the share it really had after factors that
    # could not be judged were left out (both in percent).
    weight: int
    effective_weight: float
    explanation: str


class CompatibilityOut(BaseModel):
    # 0 to 100, or None if nothing at all could be compared.
    score: int | None
    summary: str
    factors: list[CompatibilityFactorOut]
    # Keys of the factors that could not be judged.
    unavailable: list[Factor]
    area_overlap: AreaOverlap
    shared_societies: list[str]


# --- Discovery -------------------------------------------------------------------


class DiscoveryCandidateOut(BaseModel):
    student: StudentPublicOut
    compatibility: CompatibilityOut


class DiscoveryPageOut(BaseModel):
    items: list[DiscoveryCandidateOut]
    # Pass back as `cursor` to get the next page. None on the last page.
    next_cursor: str | None
    # How many people are left to decide on, including this page.
    remaining: int


class StudentViewOut(BaseModel):
    """A full profile, opened from a card or from a match."""

    student: StudentPublicOut
    compatibility: CompatibilityOut
    # Your own decision about them. Theirs about you is never shown.
    your_decision: SwipeAction | None
    # Set only when you have matched.
    match_id: uuid.UUID | None


class DecisionOut(BaseModel):
    decision: SwipeAction
    matched: bool
    match_id: uuid.UUID | None


# --- Matches -------------------------------------------------------------------------


class MatchStudentOut(BaseModel):
    id: uuid.UUID
    full_name: str
    college_name: str
    course: str | None
    department: str | None
    academic_year: int | None


class MatchOut(BaseModel):
    id: uuid.UUID
    matched_at: datetime
    # The score when you matched (None if it could not be calculated).
    compatibility_score: int | None
    # The private conversation this match enables. Messaging itself is
    # built in roadmap Phase 7.
    conversation_id: uuid.UUID | None
    student: MatchStudentOut


class MatchDetailOut(BaseModel):
    id: uuid.UUID
    matched_at: datetime
    compatibility_score: int | None
    conversation_id: uuid.UUID | None
    student: StudentPublicOut
    # Worked out again now, from their current answers.
    compatibility: CompatibilityOut


# --- Notifications -----------------------------------------------------------------------


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str
    reference_type: str | None
    reference_id: uuid.UUID | None
    is_read: bool
    created_at: datetime


class NotificationsOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int
