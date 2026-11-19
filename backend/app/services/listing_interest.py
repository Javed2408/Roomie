"""Students saying they are interested in a listing, and creators replying.

Rules:

* Only a listing the student can see (active, approved, not blocked either
  way, creator's account open) can receive interest.
* Expressing interest shares your public profile with the listing's
  creator, so it needs a published profile and a confirmed email.
* If the listing charges brokerage, the student must confirm they have
  seen it. The amount they saw is recorded with their interest.
* One interest per student per listing (a database constraint). A
  withdrawn interest can be renewed; a declined one cannot be repeated.
* Only the listing's creator sees who is interested, and never anyone
  blocked or suspended.

Messaging is roadmap Phase 7. Until then, accepting an interest notifies
the student; neither side's contact details are shared.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.core.errors import (
    BusinessRuleError,
    ConflictError,
    EmailNotVerifiedError,
    NotFoundError,
)
from app.models.enums import AccountStatus, ListingInterestStatus
from app.models.listing import AccommodationListing, ListingInterest
from app.models.user import User
from app.repositories import discovery as people
from app.repositories import listings as listings_repo
from app.schemas.interest import InterestedStudentOut
from app.schemas.listing import InterestOut, MyInterestOut
from app.services import discovery as discovery_service
from app.services import notifications
from app.services.compatibility import format_inr
from app.services.listings import display_name

_ACTIVE_INTEREST = {ListingInterestStatus.PENDING, ListingInterestStatus.ACCEPTED}


def express_interest(
    db: Session, user: User, listing_id: uuid.UUID, *, acknowledge_brokerage: bool
) -> InterestOut:
    listing = listings_repo.find_public_listing(db, listing_id, viewer_id=user.id)
    if listing is None:
        raise NotFoundError("This listing is not available.")
    if listing.owner_id == user.id:
        raise BusinessRuleError("This is your own listing.")
    discovery_service.require_published(user)
    if user.email_verified_at is None:
        raise EmailNotVerifiedError("Confirm your email address before expressing interest.")

    acknowledged: int | None = None
    if listing.brokerage_applicable:
        if not acknowledge_brokerage:
            raise BusinessRuleError(
                f"This listing charges brokerage of {format_inr(listing.brokerage_amount or 0)}. "
                "Confirm you have seen it before expressing interest."
            )
        acknowledged = listing.brokerage_amount

    existing = db.scalar(
        select(ListingInterest).where(
            ListingInterest.listing_id == listing.id, ListingInterest.user_id == user.id
        )
    )
    if existing is not None:
        if existing.status in _ACTIVE_INTEREST:
            raise ConflictError("You have already expressed interest in this listing.")
        if existing.status == ListingInterestStatus.DECLINED:
            raise ConflictError("The poster has already replied to your interest.")
        # Withdrawn earlier: renew it.
        existing.status = ListingInterestStatus.PENDING
        existing.acknowledged_brokerage_amount = acknowledged
        existing.responded_at = None
        interest = existing
    else:
        interest_id = db.scalar(
            insert(ListingInterest)
            .values(
                listing_id=listing.id,
                user_id=user.id,
                acknowledged_brokerage_amount=acknowledged,
            )
            .on_conflict_do_nothing(index_elements=["listing_id", "user_id"])
            .returning(ListingInterest.id)
        )
        if interest_id is None:  # a simultaneous duplicate request won
            raise ConflictError("You have already expressed interest in this listing.")
        interest = db.get(ListingInterest, interest_id)
        if interest is None:
            raise NotFoundError("This listing is not available.")

    notifications.notify(
        db,
        listing.owner_id,
        type=notifications.LISTING_INTEREST,
        title="Someone is interested in your listing",
        body=f'{display_name(user)} is interested in "{listing.title}".',
        reference_type="listing",
        reference_id=listing.id,
    )
    db.flush()
    db.refresh(interest)
    return InterestOut(
        listing_id=listing.id, status=interest.status, created_at=interest.created_at
    )


def withdraw_interest(db: Session, user: User, listing_id: uuid.UUID) -> None:
    interest = db.scalar(
        select(ListingInterest).where(
            ListingInterest.listing_id == listing_id, ListingInterest.user_id == user.id
        )
    )
    if interest is None or interest.status not in _ACTIVE_INTEREST:
        raise NotFoundError("You have no interest in this listing to withdraw.")
    interest.status = ListingInterestStatus.WITHDRAWN
    db.flush()


def my_interests(db: Session, user: User) -> list[MyInterestOut]:
    rows = db.scalars(
        select(ListingInterest)
        .where(
            ListingInterest.user_id == user.id,
            ListingInterest.status != ListingInterestStatus.WITHDRAWN,
        )
        .options(selectinload(ListingInterest.listing))
        .order_by(ListingInterest.created_at.desc(), ListingInterest.id)
    ).all()
    visible = {
        row.listing_id
        for row in rows
        if listings_repo.find_public_listing(db, row.listing_id, viewer_id=user.id) is not None
    }
    return [
        MyInterestOut(
            listing_id=row.listing_id,
            title=row.listing.title,
            type=row.listing.listing_type,
            status=row.status,
            listing_available=row.listing_id in visible,
            acknowledged_brokerage_amount=row.acknowledged_brokerage_amount,
            created_at=row.created_at,
            responded_at=row.responded_at,
        )
        for row in rows
    ]


def interest_status(db: Session, user: User, listing_id: uuid.UUID) -> ListingInterestStatus | None:
    status = db.scalar(
        select(ListingInterest.status).where(
            ListingInterest.listing_id == listing_id, ListingInterest.user_id == user.id
        )
    )
    return None if status == ListingInterestStatus.WITHDRAWN else status


# --- The listing's creator ---------------------------------------------------------------


def _visible_interests(
    db: Session, owner: User, listing: AccommodationListing
) -> list[ListingInterest]:
    """Interests the creator may see: not withdrawn, from open accounts that
    neither blocked nor were blocked by the creator."""
    return list(
        db.scalars(
            select(ListingInterest)
            .join(User, User.id == ListingInterest.user_id)
            .where(
                ListingInterest.listing_id == listing.id,
                ListingInterest.status != ListingInterestStatus.WITHDRAWN,
                User.account_status == AccountStatus.ACTIVE,
                ~people.blocked_between(owner.id, ListingInterest.user_id),
            )
            .order_by(ListingInterest.created_at, ListingInterest.id)
        )
    )


def interested_students(
    db: Session, owner: User, listing: AccommodationListing
) -> list[InterestedStudentOut]:
    """`listing` must be the owner's own (see find_own_listing)."""
    interests = _visible_interests(db, owner, listing)
    students = {
        person.id: person
        for person in (
            people.matched_person(db, owner.id, interest.user_id) for interest in interests
        )
        if person is not None
    }
    choices = people.society_choices(db, [owner.id, *students])
    owner_has_profile = owner.student_profile is not None
    results: list[InterestedStudentOut] = []
    for interest in interests:
        student = students.get(interest.user_id)
        if student is None:
            continue
        compatibility = None
        if owner_has_profile:
            compatibility = discovery_service.compatibility_out(
                discovery_service.score_pair(
                    owner, choices.get(owner.id, []), student, choices.get(student.id, [])
                )
            )
        results.append(
            InterestedStudentOut(
                interest_id=interest.id,
                status=interest.status,
                created_at=interest.created_at,
                responded_at=interest.responded_at,
                acknowledged_brokerage_amount=interest.acknowledged_brokerage_amount,
                student=discovery_service.student_public(student, choices.get(student.id, [])),
                compatibility=compatibility,
            )
        )
    return results


def respond_to_interest(
    db: Session,
    owner: User,
    listing: AccommodationListing,
    interest_id: uuid.UUID,
    status: ListingInterestStatus,
) -> None:
    interest = next(
        (item for item in _visible_interests(db, owner, listing) if item.id == interest_id), None
    )
    if interest is None:
        raise NotFoundError("That interest does not exist.")
    if interest.status != ListingInterestStatus.PENDING:
        raise ConflictError("You have already replied to this interest.")
    interest.status = status
    interest.responded_at = datetime.now(UTC)
    if status == ListingInterestStatus.ACCEPTED:
        notifications.notify(
            db,
            interest.user_id,
            type=notifications.INTEREST_ACCEPTED,
            title="Your interest was accepted",
            body=(
                f'{display_name(owner)} accepted your interest in "{listing.title}". '
                "Messaging opens in a later update."
            ),
            reference_type="listing",
            reference_id=listing.id,
        )
    db.flush()
