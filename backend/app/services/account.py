"""Reading and updating the signed-in person's own profile.

Every function takes the `User` who is signed in and only ever touches
that user's rows. There is no "user id" parameter that a caller could set
to someone else's id, which is what rules out one person editing another's
profile.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BusinessRuleError
from app.models.profile import RoommatePreferences, StudentProfile, UserSocietyPreference
from app.models.society import Society
from app.models.user import User
from app.repositories.directory import public_society_ids
from app.schemas.account import (
    AccountOut,
    DocumentOut,
    OwnVerificationOut,
    OwnVerificationsOut,
    PreferencesIn,
    PreferencesOut,
    ProfileIn,
    ProfileOut,
    SocietyPreferenceOut,
    SocietyPreferencesIn,
    UserOut,
)
from app.services.listings import public_society
from app.services.verification import Verification


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        email_verified=user.email_verified_at is not None,
    )


def own_verification(verification: Verification | None) -> OwnVerificationOut:
    """A person's view of their own verification.

    They see the real status, including a rejection, and their own
    documents. They do not see the reviewer's internal note.
    """
    if verification is None:
        return OwnVerificationOut(status="NOT_SUBMITTED")
    return OwnVerificationOut(
        status=verification.status.value,
        submitted_at=verification.submitted_at,
        documents=[
            DocumentOut.model_validate(document, from_attributes=True)
            for document in sorted(verification.documents, key=lambda item: item.created_at)
            if document.deleted_at is None
        ],
    )


def _society_preferences(db: Session, user: User) -> list[UserSocietyPreference]:
    return list(
        db.scalars(
            select(UserSocietyPreference)
            .where(UserSocietyPreference.user_id == user.id)
            .options(selectinload(UserSocietyPreference.society).selectinload(Society.locality))
            .order_by(UserSocietyPreference.priority)
        )
    )


def get_account(db: Session, user: User) -> AccountOut:
    db.refresh(user)
    profile, preferences = user.student_profile, user.roommate_preferences
    return AccountOut(
        user=user_out(user),
        profile=ProfileOut.model_validate(profile, from_attributes=True) if profile else None,
        preferences=(
            PreferencesOut.model_validate(preferences, from_attributes=True)
            if preferences
            else None
        ),
        societies=[
            SocietyPreferenceOut(
                society=public_society(item.society),
                priority=item.priority,
                available=item.society.is_listed and item.society.locality.is_listed,
            )
            for item in _society_preferences(db, user)
        ],
        verifications=OwnVerificationsOut(
            identity=own_verification(user.identity_verification),
            student=own_verification(user.student_verification),
        ),
    )


def missing_for_completion(db: Session, user: User) -> list[str]:
    """What still has to be filled in before the profile can be published.

    These are the profile completion rules: the details discovery and the
    compatibility score cannot work without.
    """
    db.refresh(user)
    missing: list[str] = []
    if user.student_profile is None:
        missing.append("Add your name and college.")
    preferences = user.roommate_preferences
    if preferences is None or preferences.min_budget is None or preferences.max_budget is None:
        missing.append("Set your monthly budget.")
    if preferences is None or preferences.move_in_date is None:
        missing.append("Choose a move-in date.")
    # Only societies still in the directory count.
    if not any(
        item.society.is_listed and item.society.locality.is_listed
        for item in _society_preferences(db, user)
    ):
        missing.append("Choose at least one society.")
    return missing


def _keep_completion_honest(db: Session, user: User) -> None:
    """If an edit removed something required, the profile is no longer complete."""
    profile = user.student_profile
    if profile is not None and profile.profile_completed and missing_for_completion(db, user):
        profile.profile_completed = False
        db.flush()


def save_profile(db: Session, user: User, data: ProfileIn) -> None:
    """Create the profile, or replace its editable fields."""
    profile = user.student_profile
    if profile is None:
        profile = StudentProfile(user_id=user.id, **data.model_dump())
        db.add(profile)
    else:
        for field, value in data.model_dump().items():
            setattr(profile, field, value)
    db.flush()


def save_preferences(db: Session, user: User, data: PreferencesIn) -> None:
    preferences = user.roommate_preferences
    if preferences is None:
        db.add(RoommatePreferences(user_id=user.id, **data.model_dump()))
    else:
        for field, value in data.model_dump().items():
            setattr(preferences, field, value)
    db.flush()
    _keep_completion_honest(db, user)


def save_society_preferences(db: Session, user: User, data: SocietyPreferencesIn) -> None:
    """Replace the person's ranked list of societies.

    Only societies students can currently see may be chosen: verified,
    active, and in a verified, active locality.
    """
    if data.society_ids:
        available = public_society_ids(db, data.society_ids)
        if len(available) != len(data.society_ids):
            raise BusinessRuleError("One of the chosen societies is not available.")

    # Remove the old list first, so the new ranks cannot collide with it.
    db.execute(delete(UserSocietyPreference).where(UserSocietyPreference.user_id == user.id))
    db.flush()
    for position, society_id in enumerate(data.society_ids, start=1):
        db.add(UserSocietyPreference(user_id=user.id, society_id=society_id, priority=position))
    db.flush()
    _keep_completion_honest(db, user)


def publish_profile(db: Session, user: User) -> None:
    """Mark the profile complete, if the completion rules are met."""
    missing = missing_for_completion(db, user)
    if missing:
        raise BusinessRuleError("Your profile is not complete yet.", details=missing)
    profile = user.student_profile
    if profile is not None:
        profile.profile_completed = True
        db.flush()
