"""Helpers that build valid database records for tests.

Each helper fills in sensible defaults, so a test only states the details
it actually cares about. Every helper saves its record (`db.flush()`), so
it has an id and has passed the database's constraints.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AccommodationListing,
    IdentityVerification,
    ListingAuthorityVerification,
    Locality,
    RoommatePreferences,
    Society,
    StudentProfile,
    StudentVerification,
    User,
    UserSocietyPreference,
    VerificationDocument,
)
from app.models.enums import (
    AccountStatus,
    CleanlinessLevel,
    CommunityType,
    DirectoryStatus,
    DocumentType,
    FoodPreference,
    ListingCreatorType,
    ListingLifecycleStatus,
    ListingType,
    ModerationStatus,
    RoomType,
    SleepSchedule,
    StudentVerificationMethod,
    UserRole,
)

_counter = itertools.count(1)


def make_user(db: Session, *, role: UserRole = UserRole.MEMBER, **overrides: Any) -> User:
    number = next(_counter)
    values: dict[str, Any] = {
        "email": f"user{number}@example.com",
        "password_hash": "not-a-real-hash",
        "role": role,
    }
    user = User(**(values | overrides))
    db.add(user)
    db.flush()
    return user


def make_admin(db: Session) -> User:
    return make_user(db, role=UserRole.ADMIN)


def make_student(db: Session, full_name: str = "Rohan Mehta") -> User:
    user = make_user(db)
    db.add(StudentProfile(user_id=user.id, full_name=full_name, college_name="SRM IST"))
    db.flush()
    db.refresh(user)
    return user


_MEMBER_PREFERENCES: dict[str, Any] = {
    "min_budget": 8000,
    "max_budget": 12000,
    "move_in_date": date(2027, 1, 10),
    "room_type": RoomType.PRIVATE_ROOM,
    "food_preference": FoodPreference.VEGETARIAN,
    "sleep_schedule": SleepSchedule.EARLY_BIRD,
    "cleanliness_level": CleanlinessLevel.TIDY,
}


def make_member(
    db: Session,
    full_name: str = "Priya Sharma",
    *,
    societies: Sequence[Society] = (),
    published: bool = True,
    email_verified: bool = True,
    account_status: AccountStatus = AccountStatus.ACTIVE,
    role: UserRole = UserRole.MEMBER,
    password_hash: str = "not-a-real-hash",  # noqa: S107 - not a real password
    email: str | None = None,
    profile: dict[str, Any] | None = None,
    **preferences: Any,
) -> User:
    """A student others can discover, unless told otherwise: confirmed
    email, published profile, budget, move-in date and some habits.

    Pass a preference as None to leave it unanswered.
    """
    extra = {"email": email} if email else {}
    user = make_user(
        db,
        role=role,
        account_status=account_status,
        email_verified_at=datetime.now(UTC) if email_verified else None,
        password_hash=password_hash,
        **extra,
    )
    db.add(
        StudentProfile(
            user_id=user.id,
            full_name=full_name,
            college_name="SRM IST",
            course="B.Tech",
            department="Computer Science",
            academic_year=2,
            profile_completed=published,
            **(profile or {}),
        )
    )
    db.add(RoommatePreferences(user_id=user.id, **(_MEMBER_PREFERENCES | preferences)))
    for priority, society in enumerate(societies, start=1):
        db.add(UserSocietyPreference(user_id=user.id, society_id=society.id, priority=priority))
    db.flush()
    db.refresh(user)
    return user


def _directory_verifier(db: Session) -> User:
    """The admin recorded as having verified factory-made directory records."""
    existing = db.scalar(select(User).where(User.email == "directory-verifier@example.com"))
    return existing or make_user(db, email="directory-verifier@example.com", role=UserRole.ADMIN)


def make_locality(
    db: Session, name: str | None = None, *, verified: bool = True, active: bool = True
) -> Locality:
    number = next(_counter)
    locality = Locality(
        name=name or f"Locality {number}",
        city="Chengalpattu",
        state="Tamil Nadu",
        is_active=active,
    )
    if verified:
        locality.verification_status = DirectoryStatus.VERIFIED
        locality.verified_by = _directory_verifier(db).id
        locality.verified_at = datetime.now(UTC)
    db.add(locality)
    db.flush()
    return locality


def make_society(
    db: Session,
    name: str | None = None,
    *,
    locality: Locality | None = None,
    verified: bool = True,
    active: bool = True,
    community_type: CommunityType | None = CommunityType.APARTMENT_COMPLEX,
) -> Society:
    """A society students can choose (verified, active, in a public locality),
    unless told otherwise."""
    number = next(_counter)
    society = Society(
        locality_id=(locality or make_locality(db)).id,
        name=name or f"Society {number}",
        address="12 Private Lane, Flat 4B",
        community_type=community_type,
        is_active=active,
    )
    if verified:
        society.verification_status = DirectoryStatus.VERIFIED
        society.verified_by = _directory_verifier(db).id
        society.verified_at = datetime.now(UTC)
    db.add(society)
    db.flush()
    return society


def make_property_listing(
    db: Session,
    *,
    owner: User | None = None,
    creator_type: ListingCreatorType = ListingCreatorType.PROPERTY_OWNER,
    lifecycle_status: ListingLifecycleStatus = ListingLifecycleStatus.ACTIVE,
    moderation_status: ModerationStatus = ModerationStatus.PENDING,
    **overrides: Any,
) -> AccommodationListing:
    """A real room with space to fill."""
    values: dict[str, Any] = {
        "owner_id": (owner or make_user(db)).id,
        "listing_type": ListingType.EXISTING_ACCOMMODATION,
        "creator_type": creator_type,
        "title": "One room free in a 3BHK",
        "description": "Bright room, shared kitchen.",
        "society_id": make_society(db).id,
        "rent_per_person": 9000,
        "brokerage_applicable": False,
        "bedroom_count": 3,
        "available_bedrooms": 1,
        "available_from": date(2027, 1, 5),
        "current_group_size": 2,
        "required_roommates": 1,
        "lifecycle_status": lifecycle_status,
        "moderation_status": moderation_status,
    }
    listing = AccommodationListing(**(values | overrides))
    db.add(listing)
    db.flush()
    return listing


def make_search_listing(
    db: Session,
    *,
    owner: User | None = None,
    lifecycle_status: ListingLifecycleStatus = ListingLifecycleStatus.ACTIVE,
    moderation_status: ModerationStatus = ModerationStatus.PENDING,
    **overrides: Any,
) -> AccommodationListing:
    """A request from students who want to rent together."""
    values: dict[str, Any] = {
        "owner_id": (owner or make_user(db)).id,
        "listing_type": ListingType.LOOKING_TO_RENT_TOGETHER,
        "title": "Two of us looking for a third",
        "description": "Second-years planning to rent a 3BHK.",
        "rent_per_person": 10000,
        "available_from": date(2027, 1, 15),
        "current_group_size": 2,
        "required_roommates": 1,
        "lifecycle_status": lifecycle_status,
        "moderation_status": moderation_status,
    }
    listing = AccommodationListing(**(values | overrides))
    db.add(listing)
    db.flush()
    return listing


def make_identity_verification(db: Session, user: User) -> IdentityVerification:
    verification = IdentityVerification(user_id=user.id)
    db.add(verification)
    db.flush()
    return verification


def make_student_verification(db: Session, user: User, **overrides: Any) -> StudentVerification:
    values: dict[str, Any] = {
        "user_id": user.id,
        "method": StudentVerificationMethod.DOCUMENT,
        "institution_name": "SRM IST",
    }
    verification = StudentVerification(**(values | overrides))
    db.add(verification)
    db.flush()
    return verification


def make_authority_verification(
    db: Session, listing: AccommodationListing, **overrides: Any
) -> ListingAuthorityVerification:
    verification = ListingAuthorityVerification(listing_id=listing.id, **overrides)
    db.add(verification)
    db.flush()
    return verification


def add_document(
    db: Session,
    uploader: User,
    document_type: DocumentType,
    *,
    identity: IdentityVerification | None = None,
    student: StudentVerification | None = None,
    authority: ListingAuthorityVerification | None = None,
) -> VerificationDocument:
    number = next(_counter)
    document = VerificationDocument(
        identity_verification_id=identity.id if identity else None,
        student_verification_id=student.id if student else None,
        listing_authority_verification_id=authority.id if authority else None,
        document_type=document_type,
        storage_key=f"private/verification/{number}.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        uploaded_by=uploader.id,
    )
    db.add(document)
    db.flush()
    # Reload the parent's document list so it includes the new document.
    for parent in (identity, student, authority):
        if parent is not None:
            db.refresh(parent)
    return document
