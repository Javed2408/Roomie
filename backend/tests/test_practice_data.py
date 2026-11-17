"""The practice data scripts: fictional students, and their safety guards."""

import sys

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import StudentProfile, User
from app.scripts import prepare_database, seed_test_fixtures
from app.services import discovery as discovery_service
from tests import factories

pytestmark = pytest.mark.integration


def test_practice_students_are_fictional_discoverable_and_added_once(db: Session) -> None:
    seed_test_fixtures.seed(db)

    first = seed_test_fixtures.seed_practice_students(db)
    second = seed_test_fixtures.seed_practice_students(db)

    assert first == len(seed_test_fixtures.PRACTICE_STUDENTS)
    assert second == 0
    profiles = db.scalars(select(StudentProfile)).all()
    assert all("(practice)" in profile.full_name for profile in profiles)
    assert all(profile.college_name == "Practice College" for profile in profiles)
    assert all("Not a real person" in (profile.bio or "") for profile in profiles)
    emails = db.scalars(select(User.email).where(User.email.like("practice-%"))).all()
    assert all(email.endswith("@roomie.test") for email in emails)

    viewer = factories.make_member(db, "Viewer Person")
    page = discovery_service.discover(db, viewer, limit=50)
    assert page.remaining == len(seed_test_fixtures.PRACTICE_STUDENTS)


@pytest.mark.parametrize("option", ["--reset", "--test-fixtures", "--practice-students"])
def test_test_only_options_refuse_a_real_database(
    monkeypatch: pytest.MonkeyPatch, option: str
) -> None:
    monkeypatch.setattr(get_settings(), "postgres_db", "roomie")
    monkeypatch.setattr(sys, "argv", ["prepare_database", option])

    # Refused before any connection is made, so nothing can be deleted.
    assert prepare_database.main() == 1


def test_practice_students_refuse_a_real_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "postgres_db", "roomie")

    assert seed_test_fixtures.main(practice_students=True) == 1
