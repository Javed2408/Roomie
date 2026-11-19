"""Likes, passes and matches.

Match creation (PRD 8.7, DATABASE_SCHEMA section 5 "Mutual match creation"):

    1. Lock the PAIR of people for the rest of this transaction.
    2. Check the target may still be seen (not blocked, suspended, ...).
    3. Save the decision. Repeating the same decision changes nothing;
       changing it is refused.
    4. If it is a like and the other person already liked back:
       create the match, its conversation, and one notification each.
    5. The caller commits, which releases the lock.

Why the lock: if two people like each other at the same instant, each
transaction could look for the other's like before the other has committed,
see nothing, and no match would ever be made. The lock (a PostgreSQL
transaction-level advisory lock, keyed on the pair) makes the second
request wait until the first has committed, so it then sees the first like.

The lock is not the only guard. The database also refuses duplicates by
itself: one decision per person per target (unique swipes), one match per
pair (unique, ordered user pair), one conversation per match (unique
match_id) and one "new match" notification per person per match (a unique
partial index). Every insert below says "if it already exists, do nothing".
"""

from __future__ import annotations

import uuid

from sqlalchemy import case, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.core.errors import (
    BusinessRuleError,
    ConflictError,
    EmailNotVerifiedError,
    NotFoundError,
)
from app.models.enums import AccountStatus, MatchStatus, SwipeAction
from app.models.matching import Conversation, Match, Swipe
from app.models.notification import NEW_MATCH, Notification
from app.models.user import User
from app.repositories import discovery as people
from app.schemas.discovery import DecisionOut, MatchDetailOut, MatchOut, MatchStudentOut
from app.services import discovery as discovery_service

_PAST_TENSE = {SwipeAction.LIKE: "liked", SwipeAction.PASS: "passed on"}


def lock_pair(db: Session, a: uuid.UUID, b: uuid.UUID) -> None:
    """Hold a lock on this pair of people until the transaction ends.

    Any other transaction asking for the same pair (in either order) waits.
    Different pairs never wait for each other (except, very rarely, when
    two keys share a hash, which only costs a moment's wait).
    """
    low, high = people.ordered_pair(a, b)
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"roomie-pair:{low}:{high}"},
    )


def _first_name(user: User) -> str:
    profile = user.student_profile
    if profile is None or not profile.full_name.strip():
        return "another student"
    return profile.full_name.split()[0]


def _ensure_match(db: Session, actor: User, target: User) -> uuid.UUID:
    """Create the match, its conversation and both notifications, or find
    them if they already exist. Safe to run any number of times."""
    user_one, user_two = people.ordered_pair(actor.id, target.id)
    choices = people.society_choices(db, [actor.id, target.id])
    score = discovery_service.score_pair(
        actor, choices.get(actor.id, []), target, choices.get(target.id, [])
    ).score

    match_id = db.scalar(
        insert(Match)
        .values(user_one_id=user_one, user_two_id=user_two, compatibility_score=score)
        .on_conflict_do_nothing(index_elements=["user_one_id", "user_two_id"])
        .returning(Match.id)
    )
    if match_id is None:  # it already existed
        match_id = db.scalar(
            select(Match.id).where(Match.user_one_id == user_one, Match.user_two_id == user_two)
        )
    if match_id is None:  # cannot happen: the row was just found to exist
        raise RuntimeError("The match could not be created or found.")

    db.execute(
        insert(Conversation)
        .values(match_id=match_id)
        .on_conflict_do_nothing(index_elements=["match_id"])
    )
    db.execute(
        insert(Notification)
        .values(
            [
                {
                    "user_id": person.id,
                    "type": NEW_MATCH,
                    "title": "New match",
                    "body": f"You and {_first_name(other)} liked each other.",
                    "reference_type": "match",
                    "reference_id": match_id,
                }
                for person, other in ((actor, target), (target, actor))
            ]
        )
        .on_conflict_do_nothing(
            index_elements=["user_id", "reference_id"],
            index_where=text(f"type = '{NEW_MATCH}'"),
        )
    )
    db.flush()
    return match_id


def decide(db: Session, actor: User, target_id: uuid.UUID, action: SwipeAction) -> DecisionOut:
    """Record a like or a pass, and make a match if the like is mutual."""
    discovery_service.require_published(actor)
    if actor.email_verified_at is None:
        raise EmailNotVerifiedError("Confirm your email address before liking or passing.")
    if target_id == actor.id:
        raise BusinessRuleError("You cannot like or pass on your own profile.")

    lock_pair(db, actor.id, target_id)

    target = people.visible_person(db, actor.id, target_id)
    if target is None:
        raise NotFoundError("This profile is not available.")

    existing = people.decision_of(db, actor.id, target.id)
    if existing is not None and existing != action:
        raise ConflictError(
            f"You have already {_PAST_TENSE[existing]} this person. Decisions cannot be changed."
        )
    if existing is None:
        db.execute(
            insert(Swipe)
            .values(actor_id=actor.id, target_id=target.id, action=action)
            .on_conflict_do_nothing(index_elements=["actor_id", "target_id"])
        )

    if (
        action == SwipeAction.LIKE
        and people.decision_of(db, target.id, actor.id) == SwipeAction.LIKE
    ):
        match_id = _ensure_match(db, actor, target)
        return DecisionOut(decision=action, matched=True, match_id=match_id)
    return DecisionOut(decision=action, matched=False, match_id=None)


# --- Matches ----------------------------------------------------------------------------


def _visible_matches(db: Session, user: User) -> list[tuple[Match, uuid.UUID | None, User]]:
    """The user's active matches whose other person is still open and has
    not blocked (or been blocked by) the user. Newest first."""
    other_id = case((Match.user_one_id == user.id, Match.user_two_id), else_=Match.user_one_id)
    rows = db.execute(
        select(Match, Conversation.id, other_id)
        .outerjoin(Conversation, Conversation.match_id == Match.id)
        .where(
            or_(Match.user_one_id == user.id, Match.user_two_id == user.id),
            Match.status == MatchStatus.ACTIVE,
        )
        .order_by(Match.matched_at.desc(), Match.id)
    ).all()
    if not rows:
        return []

    others = {
        person.id: person
        for person in db.scalars(
            select(User)
            .where(
                User.id.in_([row[2] for row in rows]),
                User.account_status == AccountStatus.ACTIVE,
                ~people.blocked_between(user.id, User.id),
            )
            .options(selectinload(User.student_profile))
        )
    }
    return [
        (match, conversation_id, others[person_id])
        for match, conversation_id, person_id in rows
        if person_id in others and others[person_id].student_profile is not None
    ]


def list_matches(db: Session, user: User) -> list[MatchOut]:
    results: list[MatchOut] = []
    for match, conversation_id, other in _visible_matches(db, user):
        profile = other.student_profile
        if profile is None:  # filtered out above; kept for the type checker
            continue
        results.append(
            MatchOut(
                id=match.id,
                matched_at=match.matched_at,
                compatibility_score=match.compatibility_score,
                conversation_id=conversation_id,
                student=MatchStudentOut(
                    id=other.id,
                    full_name=profile.full_name,
                    photo_url=discovery_service.student_photo_url(
                        other.id, profile.profile_photo_key
                    ),
                    college_name=profile.college_name,
                    course=profile.course,
                    department=profile.department,
                    academic_year=profile.academic_year,
                ),
            )
        )
    return results


def match_detail(db: Session, user: User, match_id: uuid.UUID) -> MatchDetailOut:
    """One of the user's own matches. Anyone else's answers "not found"."""
    found = next((item for item in _visible_matches(db, user) if item[0].id == match_id), None)
    if found is None:
        raise NotFoundError("This match is not available.")
    match, conversation_id, other = found

    person = people.matched_person(db, user.id, other.id)
    if person is None:
        raise NotFoundError("This match is not available.")
    choices = people.society_choices(db, [user.id, person.id])
    result = discovery_service.score_pair(
        user, choices.get(user.id, []), person, choices.get(person.id, [])
    )
    return MatchDetailOut(
        id=match.id,
        matched_at=match.matched_at,
        compatibility_score=match.compatibility_score,
        conversation_id=conversation_id,
        student=discovery_service.student_public(person, choices.get(person.id, [])),
        compatibility=discovery_service.compatibility_out(result),
    )
