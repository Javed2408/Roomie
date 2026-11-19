"""Discovery: who a student sees, in what order, and full profiles.

Order (PRD section 1: discovery "prioritizes people whose accommodation
preferences overlap"):

1. people who chose at least one of the same societies,
2. then people who chose the same area (locality),
3. then everyone else,

and within each group, the highest compatibility score first. Nobody is
hidden for wanting a different area: the score says so, and the app tells
the student when the deck moves past people who share their societies.
"""

from __future__ import annotations

import base64
import binascii
import json
import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import BusinessRuleError, NotFoundError, ProfileIncompleteError
from app.models.profile import UserSocietyPreference
from app.models.user import User
from app.repositories import discovery as people
from app.schemas.discovery import (
    CompatibilityFactorOut,
    CompatibilityOut,
    DiscoveryCandidateOut,
    DiscoveryPageOut,
    PublicPreferencesOut,
    PublicSocietyChoiceOut,
    StudentPublicOut,
    StudentViewOut,
)
from app.services import compatibility
from app.services.compatibility import AreaOverlap, CompatibilityResult, Factor, SocietyChoice
from app.services.listings import public_society
from app.services.photos import photo_version
from app.services.verification import public_state

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50

_AREA_ORDER = {
    AreaOverlap.SAME_SOCIETY: 0,
    AreaOverlap.SAME_LOCALITY: 1,
    AreaOverlap.NONE: 2,
    AreaOverlap.UNKNOWN: 2,
}

SortKey = tuple[int, int, str]


def configured_weights() -> dict[Factor, int]:
    """The compatibility weights from settings (validated at start-up)."""
    return {Factor(name): weight for name, weight in get_settings().compatibility_weights.items()}


def require_published(user: User) -> None:
    profile = user.student_profile
    if profile is None or not profile.profile_completed:
        raise ProfileIncompleteError("Finish and publish your profile to see other students.")


# --- Building what is shown ------------------------------------------------------


def _is_public(choice: UserSocietyPreference) -> bool:
    return choice.society.is_listed and choice.society.locality.is_listed


def compatibility_input(
    user: User, choices: Sequence[UserSocietyPreference]
) -> compatibility.CompatibilityInput:
    societies = tuple(
        SocietyChoice(
            society_id=choice.society_id,
            society_name=choice.society.name,
            locality_id=choice.society.locality_id,
            locality_name=choice.society.locality.name,
            priority=choice.priority,
            is_public=_is_public(choice),
        )
        for choice in choices
    )
    preferences = user.roommate_preferences
    if preferences is None:
        return compatibility.CompatibilityInput(societies=societies)
    return compatibility.CompatibilityInput(
        min_budget=preferences.min_budget,
        max_budget=preferences.max_budget,
        move_in_date=preferences.move_in_date,
        room_type=preferences.room_type,
        food_preference=preferences.food_preference,
        smoking=preferences.smoking_preference,
        drinking=preferences.drinking_preference,
        sleep_schedule=preferences.sleep_schedule,
        cleanliness=preferences.cleanliness_level,
        social=preferences.social_preference,
        guests=preferences.guest_frequency,
        societies=societies,
    )


def student_photo_url(user_id: uuid.UUID, key: str | None) -> str | None:
    """An access-checked API address for a profile photo, never its key.
    The `v` part changes when the photo is replaced, so no old copy shows."""
    if key is None:
        return None
    return f"/api/v1/students/{user_id}/photo?v={photo_version(key)}"


def student_public(user: User, choices: Sequence[UserSocietyPreference]) -> StudentPublicOut:
    """The allow-listed public view of a student. Only call this for someone
    the viewer is allowed to see (see app/repositories/discovery.py)."""
    profile = user.student_profile
    if profile is None:  # every visible person has one; this is a safety net
        raise NotFoundError("This profile is not available.")
    preferences = user.roommate_preferences
    public_choices = sorted(
        (choice for choice in choices if _is_public(choice)), key=lambda c: c.priority
    )

    def preference(name: str) -> object:
        return getattr(preferences, name) if preferences is not None else None

    return StudentPublicOut(
        id=user.id,
        full_name=profile.full_name,
        college_name=profile.college_name,
        course=profile.course,
        department=profile.department,
        academic_year=profile.academic_year,
        bio=profile.bio,
        gender=profile.gender if profile.gender_visible else None,
        photo_url=student_photo_url(user.id, profile.profile_photo_key),
        preferences=PublicPreferencesOut.model_validate(
            {field: preference(field) for field in PublicPreferencesOut.model_fields}
        ),
        societies=[
            PublicSocietyChoiceOut(society=public_society(choice.society), priority=rank)
            for rank, choice in enumerate(public_choices, start=1)
        ],
        identity_verification=public_state(user.identity_verification),
        student_verification=public_state(user.student_verification),
    )


def compatibility_out(result: CompatibilityResult) -> CompatibilityOut:
    return CompatibilityOut(
        score=result.score,
        summary=result.summary,
        factors=[
            CompatibilityFactorOut(
                key=item.factor,
                label=item.label,
                score=item.score,
                available=item.available,
                weight=item.weight,
                effective_weight=item.effective_weight,
                explanation=item.explanation,
            )
            for item in result.factors
        ],
        unavailable=list(result.unavailable),
        area_overlap=result.area_overlap,
        shared_societies=list(result.shared_societies),
    )


def score_pair(
    viewer: User,
    viewer_choices: Sequence[UserSocietyPreference],
    other: User,
    other_choices: Sequence[UserSocietyPreference],
) -> CompatibilityResult:
    return compatibility.calculate(
        compatibility_input(viewer, viewer_choices),
        compatibility_input(other, other_choices),
        configured_weights(),
    )


# --- Paging -------------------------------------------------------------------------


def _sort_key(result: CompatibilityResult, person_id: uuid.UUID) -> SortKey:
    score = result.score if result.score is not None else -1
    return (_AREA_ORDER[result.area_overlap], -score, str(person_id))


def _encode_cursor(key: SortKey) -> str:
    return base64.urlsafe_b64encode(json.dumps(list(key)).encode()).decode()


def _decode_cursor(cursor: str) -> SortKey:
    """The position after which the next page starts.

    The cursor is a position in the ordering, not a count, so people
    dropping out of the list (because you liked or passed on them) never
    makes the next page skip anyone.
    """
    try:
        area, negative_score, person = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return (int(area), int(negative_score), str(uuid.UUID(person)))
    except (ValueError, TypeError, binascii.Error, json.JSONDecodeError) as error:
        raise BusinessRuleError("That page link is not valid. Start again.") from error


# --- Discovery and profiles ------------------------------------------------------------


def discover(
    db: Session, viewer: User, *, limit: int = DEFAULT_PAGE_SIZE, cursor: str | None = None
) -> DiscoveryPageOut:
    """The next people to decide on, best first."""
    require_published(viewer)
    after = _decode_cursor(cursor) if cursor else None

    candidates = people.discoverable_people(db, viewer.id)
    choices = people.society_choices(db, [viewer.id, *(person.id for person in candidates)])
    viewer_input = compatibility_input(viewer, choices.get(viewer.id, []))
    weights = configured_weights()

    ranked: list[tuple[SortKey, User, CompatibilityResult]] = []
    for person in candidates:
        result = compatibility.calculate(
            viewer_input, compatibility_input(person, choices.get(person.id, [])), weights
        )
        ranked.append((_sort_key(result, person.id), person, result))
    ranked.sort(key=lambda item: item[0])

    following = [item for item in ranked if after is None or item[0] > after]
    page = following[:limit]
    return DiscoveryPageOut(
        items=[
            DiscoveryCandidateOut(
                student=student_public(person, choices.get(person.id, [])),
                compatibility=compatibility_out(result),
            )
            for _, person, result in page
        ],
        next_cursor=_encode_cursor(page[-1][0]) if len(following) > limit else None,
        remaining=len(ranked),
    )


def viewable_student(
    db: Session, viewer: User, student_id: uuid.UUID
) -> tuple[User, uuid.UUID | None]:
    """The student, if the viewer may open their profile, and any match.

    Allowed when the two have matched, when the student is interested in
    one of the viewer's listings (an owner or agent need not have a
    student profile), or when the viewer may see them in discovery.
    Anything else answers "not available", the same as a profile that
    does not exist, so nothing is revealed.
    """
    match_id = people.active_match_id(db, viewer.id, student_id)
    if match_id is not None or people.has_active_interest_from(db, viewer.id, student_id):
        person = people.matched_person(db, viewer.id, student_id)
    else:
        require_published(viewer)
        person = people.visible_person(db, viewer.id, student_id)
    if person is None:
        raise NotFoundError("This profile is not available.")
    return person, match_id


def view_student(db: Session, viewer: User, student_id: uuid.UUID) -> StudentViewOut:
    """Another student's full profile, and how well they fit the viewer."""
    person, match_id = viewable_student(db, viewer, student_id)
    choices = people.society_choices(db, [viewer.id, person.id])
    result = score_pair(viewer, choices.get(viewer.id, []), person, choices.get(person.id, []))
    return StudentViewOut(
        student=student_public(person, choices.get(person.id, [])),
        compatibility=compatibility_out(result),
        your_decision=people.decision_of(db, viewer.id, person.id),
        match_id=match_id,
    )
