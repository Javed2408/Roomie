"""Student profiles, roommate preferences and preferred societies."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin, enum_type
from app.models.enums import (
    CleanlinessLevel,
    FoodPreference,
    GuestFrequency,
    HabitFrequency,
    RoomType,
    SleepSchedule,
    SocialPreference,
)

if TYPE_CHECKING:
    from app.models.society import Society
    from app.models.user import User


class StudentProfile(TimestampMixin, Base):
    """What other students see. Only users who are students have one."""

    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint(
            "academic_year IS NULL OR academic_year BETWEEN 1 AND 8",
            name="academic_year_range",
        ),
        Index("ix_student_profiles_college_name", "college_name"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Private: never included in any public response.
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    college_name: Mapped[str] = mapped_column(String(180), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120))
    course: Mapped[str | None] = mapped_column(String(120))
    academic_year: Mapped[int | None] = mapped_column(SmallInteger)
    bio: Mapped[str | None] = mapped_column(Text)
    profile_photo_key: Mapped[str | None] = mapped_column(Text)
    gender: Mapped[str | None] = mapped_column(String(40))
    # Gender stays private unless the student chooses to show it.
    gender_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    profile_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    user: Mapped[User] = relationship(back_populates="student_profile")


class RoommatePreferences(Base):
    """A student's own budget, timing and habits.

    Every column is optional. A missing value means "unknown" and must not
    be counted as a match by the compatibility score.
    """

    __tablename__ = "roommate_preferences"
    __table_args__ = (
        CheckConstraint("min_budget IS NULL OR min_budget >= 0", name="min_budget_non_negative"),
        CheckConstraint("max_budget IS NULL OR max_budget >= 0", name="max_budget_non_negative"),
        CheckConstraint(
            "min_budget IS NULL OR max_budget IS NULL OR min_budget <= max_budget",
            name="budget_range_ordered",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Whole rupees per month.
    min_budget: Mapped[int | None] = mapped_column(Integer)
    max_budget: Mapped[int | None] = mapped_column(Integer)
    move_in_date: Mapped[date | None] = mapped_column(Date)
    room_type: Mapped[RoomType | None] = mapped_column(enum_type(RoomType, "room_type", 20))
    food_preference: Mapped[FoodPreference | None] = mapped_column(
        enum_type(FoodPreference, "food_preference", 20)
    )
    smoking_preference: Mapped[HabitFrequency | None] = mapped_column(
        enum_type(HabitFrequency, "smoking_preference", 20)
    )
    drinking_preference: Mapped[HabitFrequency | None] = mapped_column(
        enum_type(HabitFrequency, "drinking_preference", 20)
    )
    sleep_schedule: Mapped[SleepSchedule | None] = mapped_column(
        enum_type(SleepSchedule, "sleep_schedule", 20)
    )
    cleanliness_level: Mapped[CleanlinessLevel | None] = mapped_column(
        enum_type(CleanlinessLevel, "cleanliness_level", 20)
    )
    social_preference: Mapped[SocialPreference | None] = mapped_column(
        enum_type(SocialPreference, "social_preference", 20)
    )
    guest_frequency: Mapped[GuestFrequency | None] = mapped_column(
        enum_type(GuestFrequency, "guest_frequency", 20)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="roommate_preferences")


class UserSocietyPreference(CreatedAtMixin, Base):
    """One society a user would like to live in, with its rank."""

    __tablename__ = "user_society_preferences"
    __table_args__ = (
        CheckConstraint("priority > 0", name="priority_positive"),
        # Two societies cannot share the same rank for one user.
        UniqueConstraint("user_id", "priority"),
        Index("ix_user_society_preferences_society_id_user_id", "society_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    society_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("societies.id"), primary_key=True)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    society: Mapped[Society] = relationship()
