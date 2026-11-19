"""Add FICTIONAL directory records for automated tests.

    python -m app.scripts.seed_test_fixtures [--practice-students]

With --practice-students it also adds six fictional students (see
PRACTICE_STUDENTS below) for trying Discover by hand.

Every name here is invented and obviously so ("Alpha Fixture Residency").
They exist only so the browser tests have something to choose. The script
refuses to run unless the database name ends in "_test" or "_e2e", so it
can never put fake records into a real or development directory.

Safe to run more than once.
"""

from __future__ import annotations

import os
import secrets
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import (
    CleanlinessLevel,
    CommunityType,
    FoodPreference,
    GuestFrequency,
    HabitFrequency,
    RoomType,
    SleepSchedule,
    SocialPreference,
    UserRole,
)
from app.models.profile import RoommatePreferences, StudentProfile, UserSocietyPreference
from app.models.society import Locality, Society, normalise_name
from app.models.user import User
from app.services import directory as directory_service

FIXTURE_ADMIN_EMAIL = "fixtures-admin@roomie.test"
CITY, STATE = "Fixture City", "Fixture State"


@dataclass(frozen=True)
class FixtureSociety:
    name: str
    locality: str
    community_type: CommunityType | None = CommunityType.APARTMENT_COMPLEX
    verified: bool = True
    active: bool = True


FIXTURE_LOCALITIES: dict[str, bool] = {
    # name -> verified
    "Fixture Town North": True,
    "Fixture Town South": True,
    # Never public: its locality is not verified.
    "Fixture Town Hidden": False,
}

FIXTURE_SOCIETIES = [
    FixtureSociety("Alpha Fixture Residency", "Fixture Town North"),
    FixtureSociety("Beta Fixture Towers", "Fixture Town North"),
    FixtureSociety("Gamma Fixture Gardens", "Fixture Town South", CommunityType.VILLA_COMMUNITY),
    FixtureSociety("Delta Fixture Court", "Fixture Town South"),
    FixtureSociety("Epsilon Fixture Lane", "Fixture Town North"),
    FixtureSociety("Zeta Fixture Villas", "Fixture Town South", CommunityType.VILLA_COMMUNITY),
    # These three must NEVER be visible to students.
    FixtureSociety("Unverified Fixture Heights", "Fixture Town North", verified=False),
    FixtureSociety("Inactive Fixture Park", "Fixture Town South", active=False),
    FixtureSociety("Hidden Area Fixture Homes", "Fixture Town Hidden"),
]


def _fixture_admin(db: Session) -> User:
    # Normally a random password nobody knows: the account only signs history
    # rows. The browser tests set E2E_ADMIN_PASSWORD so they can sign in as
    # this administrator and approve listings. This script only ever runs
    # against a database whose name ends in _test or _e2e (see main below).
    password = os.environ.get("E2E_ADMIN_PASSWORD") or secrets.token_urlsafe(32)
    admin = db.scalar(select(User).where(User.email == FIXTURE_ADMIN_EMAIL))
    if admin is None:
        admin = User(
            email=FIXTURE_ADMIN_EMAIL,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            email_verified_at=datetime.now(UTC),
        )
        db.add(admin)
    else:
        admin.password_hash = hash_password(password)
    db.flush()
    return admin


def seed(db: Session) -> None:
    admin = _fixture_admin(db)
    note = "Test fixture: fictional record for automated tests."

    localities: dict[str, Locality] = {}
    for name, verified in FIXTURE_LOCALITIES.items():
        locality = db.scalar(select(Locality).where(Locality.name_key == normalise_name(name)))
        if locality is None:
            locality = directory_service.create_locality(
                db,
                directory_service.LocalityFields(name=name, city=CITY, state=STATE),
                actor=admin,
                note=note,
            )
            if verified:
                directory_service.verify(db, locality, actor=admin, note=note)
        localities[name] = locality

    for fixture in FIXTURE_SOCIETIES:
        if db.scalar(select(Society).where(Society.name_key == normalise_name(fixture.name))):
            continue
        society = directory_service.create_society(
            db,
            directory_service.SocietyFields(
                locality_id=localities[fixture.locality].id,
                name=fixture.name,
                community_type=fixture.community_type,
                description="Fictional test record.",
            ),
            actor=admin,
            note=note,
        )
        if fixture.verified:
            directory_service.verify(db, society, actor=admin, note=note)
        if not fixture.active:
            directory_service.set_active(db, society, False, actor=admin, note=note)
    db.flush()


# --- Practice students -----------------------------------------------------------
#
# FICTIONAL people for trying Discover by hand in a practice database. Each
# name says "(practice)", the college is "Practice College", and every bio
# says they are not real. Their passwords are random and unknown, so nobody
# can sign in as them; they exist only to be discovered and liked.


@dataclass(frozen=True)
class PracticeStudent:
    name: str
    societies: tuple[str, ...]
    min_budget: int
    max_budget: int
    move_in: date
    room: RoomType
    food: FoodPreference
    sleep: SleepSchedule
    tidiness: CleanlinessLevel
    social: SocialPreference
    guests: GuestFrequency
    smoking: HabitFrequency = HabitFrequency.NEVER
    drinking: HabitFrequency = HabitFrequency.NEVER


PRACTICE_STUDENTS = [
    PracticeStudent(
        "Asha (practice)", ("Alpha Fixture Residency", "Beta Fixture Towers"),
        8000, 12000, date(2027, 1, 10), RoomType.PRIVATE_ROOM, FoodPreference.VEGETARIAN,
        SleepSchedule.EARLY_BIRD, CleanlinessLevel.TIDY, SocialPreference.QUIET,
        GuestFrequency.RARELY,
    ),
    PracticeStudent(
        "Rahul (practice)", ("Beta Fixture Towers",),
        9000, 14000, date(2027, 1, 20), RoomType.SHARED_ROOM, FoodPreference.NON_VEGETARIAN,
        SleepSchedule.NIGHT_OWL, CleanlinessLevel.RELAXED, SocialPreference.SOCIAL,
        GuestFrequency.OFTEN, drinking=HabitFrequency.OCCASIONALLY,
    ),
    PracticeStudent(
        "Meena (practice)", ("Gamma Fixture Gardens", "Delta Fixture Court"),
        7000, 10000, date(2027, 1, 5), RoomType.NO_PREFERENCE, FoodPreference.VEGAN,
        SleepSchedule.FLEXIBLE, CleanlinessLevel.VERY_TIDY, SocialPreference.BALANCED,
        GuestFrequency.SOMETIMES,
    ),
    PracticeStudent(
        "Karthik (practice)", ("Delta Fixture Court",),
        12000, 18000, date(2027, 3, 1), RoomType.PRIVATE_ROOM, FoodPreference.NON_VEGETARIAN,
        SleepSchedule.NIGHT_OWL, CleanlinessLevel.TIDY, SocialPreference.BALANCED,
        GuestFrequency.SOMETIMES, HabitFrequency.OCCASIONALLY, HabitFrequency.OCCASIONALLY,
    ),
    PracticeStudent(
        "Divya (practice)", ("Alpha Fixture Residency", "Epsilon Fixture Lane"),
        8000, 11000, date(2027, 1, 12), RoomType.PRIVATE_ROOM, FoodPreference.VEGETARIAN,
        SleepSchedule.EARLY_BIRD, CleanlinessLevel.VERY_TIDY, SocialPreference.QUIET,
        GuestFrequency.RARELY,
    ),
    PracticeStudent(
        "Arjun (practice)", ("Zeta Fixture Villas",),
        10000, 13000, date(2027, 2, 1), RoomType.SHARED_ROOM, FoodPreference.VEGETARIAN,
        SleepSchedule.FLEXIBLE, CleanlinessLevel.TIDY, SocialPreference.SOCIAL,
        GuestFrequency.OFTEN, drinking=HabitFrequency.REGULARLY,
    ),
]  # fmt: skip


def _practice_email(student: PracticeStudent) -> str:
    return f"practice-{student.name.split()[0].lower()}@roomie.test"


def seed_practice_students(db: Session) -> int:
    """Add the fictional students. Returns how many were added."""
    societies = {
        society.name: society
        for society in db.scalars(
            select(Society).where(Society.name.in_([s.name for s in FIXTURE_SOCIETIES]))
        )
    }
    added = 0
    for student in PRACTICE_STUDENTS:
        email = _practice_email(student)
        if db.scalar(select(User).where(User.email == email)):
            continue
        now = datetime.now(UTC)
        user = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            email_verified_at=now,
            terms_accepted_at=now,
        )
        db.add(user)
        db.flush()
        db.add(
            StudentProfile(
                user_id=user.id,
                full_name=student.name,
                college_name="Practice College",
                course="B.Tech",
                bio="A fictional practice profile for trying Roomie. Not a real person.",
                profile_completed=True,
            )
        )
        db.add(
            RoommatePreferences(
                user_id=user.id,
                min_budget=student.min_budget,
                max_budget=student.max_budget,
                move_in_date=student.move_in,
                room_type=student.room,
                food_preference=student.food,
                sleep_schedule=student.sleep,
                cleanliness_level=student.tidiness,
                social_preference=student.social,
                guest_frequency=student.guests,
                smoking_preference=student.smoking,
                drinking_preference=student.drinking,
            )
        )
        for priority, society_name in enumerate(student.societies, start=1):
            db.add(
                UserSocietyPreference(
                    user_id=user.id, society_id=societies[society_name].id, priority=priority
                )
            )
        added += 1
    db.flush()
    return added


def main(*, practice_students: bool = False) -> int:
    name = get_settings().postgres_db
    if not (name.endswith("_test") or name.endswith("_e2e")):
        print(f"Refusing to add test fixtures to '{name}': it is not a test database.")
        return 1
    with SessionLocal() as db:
        seed(db)
        added = seed_practice_students(db) if practice_students else 0
        db.commit()
    print(f"Test fixtures ready in {name}.")
    if practice_students:
        print(f"Practice students added: {added} (fictional, marked '(practice)').")
    return 0


if __name__ == "__main__":
    sys.exit(main(practice_students="--practice-students" in sys.argv))
