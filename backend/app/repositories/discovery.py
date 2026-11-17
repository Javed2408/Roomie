"""Database queries for discovery and matching.

The visibility rule lives here, once, and every discovery query, profile
view and like/pass request uses it. A member can see another member only if
that person:

* is not themselves,
* has an ACTIVE account (not suspended or deleted) with the MEMBER role,
* has confirmed their email address,
* has a published (complete) student profile, and
* has not blocked them, and is not blocked by them.

Student or identity verification is NOT required (PRD 8.1 asks only for a
confirmed email before full discovery access).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence

from sqlalchemy import ColumnElement, Select, and_, exists, or_, select
from sqlalchemy.orm import Session, contains_eager, selectinload

from app.models.enums import AccountStatus, MatchStatus, SwipeAction, UserRole
from app.models.matching import Match, Swipe
from app.models.profile import StudentProfile, UserSocietyPreference
from app.models.safety import Block
from app.models.society import Society
from app.models.user import User


def blocked_between(
    viewer_id: uuid.UUID, other_id: uuid.UUID | ColumnElement[uuid.UUID]
) -> ColumnElement[bool]:
    """True if either person has blocked the other."""
    return exists().where(
        or_(
            and_(Block.blocker_id == viewer_id, Block.blocked_user_id == other_id),
            and_(Block.blocker_id == other_id, Block.blocked_user_id == viewer_id),
        )
    )


def account_usable() -> list[ColumnElement[bool]]:
    """An account that is open, not staff, and has a confirmed email."""
    return [
        User.account_status == AccountStatus.ACTIVE,
        User.role == UserRole.MEMBER,
        User.email_verified_at.is_not(None),
    ]


def visibility_conditions(viewer_id: uuid.UUID) -> list[ColumnElement[bool]]:
    """Who `viewer_id` may see at all. Needs StudentProfile joined."""
    return [
        User.id != viewer_id,
        *account_usable(),
        StudentProfile.profile_completed.is_(True),
        ~blocked_between(viewer_id, User.id),
    ]


def _with_profile_data(statement: Select[tuple[User]]) -> Select[tuple[User]]:
    """Load everything a public profile and a score need, in few queries."""
    return statement.options(
        contains_eager(User.student_profile),
        selectinload(User.roommate_preferences),
        selectinload(User.identity_verification),
        selectinload(User.student_verification),
    )


def discoverable_people(db: Session, viewer_id: uuid.UUID) -> Sequence[User]:
    """Everyone the viewer may see and has not yet liked or passed on."""
    already_decided = exists().where(Swipe.actor_id == viewer_id, Swipe.target_id == User.id)
    statement = (
        select(User)
        .join(User.student_profile)
        .where(*visibility_conditions(viewer_id), ~already_decided)
    )
    return db.scalars(_with_profile_data(statement)).unique().all()


def visible_person(db: Session, viewer_id: uuid.UUID, person_id: uuid.UUID) -> User | None:
    """One person, if the viewer may see them (whether or not already decided)."""
    statement = (
        select(User)
        .join(User.student_profile)
        .where(User.id == person_id, *visibility_conditions(viewer_id))
    )
    return db.scalars(_with_profile_data(statement)).unique().one_or_none()


def matched_person(db: Session, viewer_id: uuid.UUID, person_id: uuid.UUID) -> User | None:
    """Someone the viewer has matched with, while neither has blocked the
    other and their account is still open. Their profile may since have
    become incomplete; a match can still see it."""
    statement = (
        select(User)
        .join(User.student_profile)
        .where(
            User.id == person_id,
            User.id != viewer_id,
            User.account_status == AccountStatus.ACTIVE,
            ~blocked_between(viewer_id, User.id),
        )
    )
    return db.scalars(_with_profile_data(statement)).unique().one_or_none()


def society_choices(
    db: Session, user_ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, list[UserSocietyPreference]]:
    """Each person's saved societies, in their order, with societies and
    localities loaded. Includes ones no longer public; callers filter."""
    ids = list(set(user_ids))
    found: dict[uuid.UUID, list[UserSocietyPreference]] = defaultdict(list)
    if not ids:
        return found
    rows = db.scalars(
        select(UserSocietyPreference)
        .where(UserSocietyPreference.user_id.in_(ids))
        .options(selectinload(UserSocietyPreference.society).selectinload(Society.locality))
        .order_by(UserSocietyPreference.user_id, UserSocietyPreference.priority)
    )
    for row in rows:
        found[row.user_id].append(row)
    return found


def decision_of(db: Session, actor_id: uuid.UUID, target_id: uuid.UUID) -> SwipeAction | None:
    """The actor's own like or pass on the target, if any."""
    return db.scalar(
        select(Swipe.action).where(Swipe.actor_id == actor_id, Swipe.target_id == target_id)
    )


def ordered_pair(a: uuid.UUID, b: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """Matches store the smaller id first. Python orders UUIDs by their
    128-bit value, which is the same order PostgreSQL uses."""
    return (a, b) if a < b else (b, a)


def active_match_id(db: Session, a: uuid.UUID, b: uuid.UUID) -> uuid.UUID | None:
    user_one, user_two = ordered_pair(a, b)
    return db.scalar(
        select(Match.id).where(
            Match.user_one_id == user_one,
            Match.user_two_id == user_two,
            Match.status == MatchStatus.ACTIVE,
        )
    )
