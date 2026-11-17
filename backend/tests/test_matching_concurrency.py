"""Simultaneous likes, with real transactions on separate connections.

The usual `db` fixture runs a whole test inside one transaction, which
cannot show a race between two transactions. These tests use their own
connections, commit for real, and empty the test database afterwards.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models import Conversation, Match, Notification, Swipe, User
from app.models.enums import SwipeAction
from app.services import matching
from tests import factories

pytestmark = pytest.mark.integration

PAIRS = 12


@pytest.fixture
def committed(test_engine: Engine) -> Iterator[sessionmaker[Session]]:
    """Sessions that really commit. Every table is emptied afterwards, so
    the next test starts from nothing, as with the usual fixture."""
    if not (test_engine.url.database or "").endswith("_test"):
        raise RuntimeError("Refusing to run against a database that is not a test database.")
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    yield factory
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with test_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} CASCADE"))


def _make_people(factory: sessionmaker[Session], count: int) -> list[uuid.UUID]:
    with factory() as db:
        ids = [factories.make_member(db, f"Racer {number}").id for number in range(count)]
        db.commit()
    return ids


def _run_together(*jobs: Callable[[], None]) -> list[BaseException]:
    """Start every job at the same moment, wait for all, return any errors."""
    barrier = threading.Barrier(len(jobs))
    errors: list[BaseException] = []

    def run(job: Callable[[], None]) -> None:
        try:
            barrier.wait(timeout=10)
            job()
        except BaseException as error:  # noqa: BLE001 - reported by the test
            errors.append(error)

    threads = [threading.Thread(target=run, args=(job,)) for job in jobs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return errors


def _like_job(
    factory: sessionmaker[Session], actor_id: uuid.UUID, target_id: uuid.UUID
) -> Callable[[], None]:
    def job() -> None:
        with factory() as db:
            actor = db.get(User, actor_id)
            assert actor is not None
            matching.decide(db, actor, target_id, SwipeAction.LIKE)
            db.commit()

    return job


def test_simultaneous_mutual_likes_make_exactly_one_match(
    committed: sessionmaker[Session],
) -> None:
    people = _make_people(committed, PAIRS * 2)
    pairs = list(zip(people[::2], people[1::2], strict=True))

    for first, second in pairs:
        errors = _run_together(
            _like_job(committed, first, second), _like_job(committed, second, first)
        )
        assert errors == []

    with committed() as db:
        # Every pair liked each other, so every pair has exactly one match...
        assert db.scalar(select(func.count()).select_from(Match)) == PAIRS
        matches = db.scalars(select(Match)).all()
        assert {(m.user_one_id, m.user_two_id) for m in matches} == {
            tuple(sorted(pair)) for pair in pairs
        }
        # ...exactly one conversation each...
        conversations = db.scalars(select(Conversation.match_id)).all()
        assert sorted(conversations) == sorted(m.id for m in matches)
        # ...and exactly one notification per person per match.
        notifications = db.execute(select(Notification.user_id, Notification.reference_id)).all()
        assert len(notifications) == len(set(notifications)) == PAIRS * 2


def test_a_double_click_saves_one_like(committed: sessionmaker[Session]) -> None:
    actor, target = _make_people(committed, 2)

    errors = _run_together(*(_like_job(committed, actor, target) for _ in range(4)))

    assert errors == []
    with committed() as db:
        assert db.scalar(select(func.count()).select_from(Swipe)) == 1
        assert db.scalar(select(func.count()).select_from(Match)) == 0
