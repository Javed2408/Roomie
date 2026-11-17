"""Tests for likes, passes, matches, conversations and match notifications."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Block, Conversation, Match, Notification, Swipe
from app.models.enums import AccountStatus
from app.models.notification import NEW_MATCH
from app.repositories.discovery import ordered_pair
from tests import factories
from tests.helpers import Member, sign_up, signed_in_member

pytestmark = pytest.mark.integration

MakeMember = Callable[..., Member]


@pytest.fixture
def member(new_client: Callable[[], TestClient], db: Session) -> MakeMember:
    def make(full_name: str = "Priya Sharma", **options: object) -> Member:
        return signed_in_member(new_client, db, full_name, **options)

    return make


def like(actor: Member, target: Member | str) -> dict:
    target_id = target if isinstance(target, str) else target.id
    response = actor.client.post(f"/api/v1/discovery/{target_id}/like", headers=actor.headers)
    assert response.status_code == 200, response.text
    return response.json()


def pass_on(actor: Member, target: Member) -> dict:
    response = actor.client.post(f"/api/v1/discovery/{target.id}/pass", headers=actor.headers)
    assert response.status_code == 200, response.text
    return response.json()


def count(db: Session, model: type, *conditions: object) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)


# --- Likes and passes ---------------------------------------------------------------------


def test_a_one_way_like_is_saved_without_a_match(member: MakeMember, db: Session) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")

    result = like(asha, priya)

    assert result == {"decision": "LIKE", "matched": False, "match_id": None}
    swipe = db.scalar(select(Swipe).where(Swipe.actor_id == asha.user.id))
    assert swipe is not None and swipe.created_at is not None
    assert count(db, Match) == count(db, Notification) == 0


def test_a_mutual_like_creates_one_match_one_conversation_and_two_notifications(
    member: MakeMember, db: Session
) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")

    first = like(asha, priya)
    second = like(priya, asha)

    assert first["matched"] is False
    assert second["matched"] is True
    match = db.get(Match, second["match_id"])
    assert match is not None
    assert (match.user_one_id, match.user_two_id) == ordered_pair(asha.user.id, priya.user.id)
    assert match.compatibility_score == 100
    assert count(db, Match) == 1
    assert count(db, Conversation, Conversation.match_id == match.id) == 1

    notifications = db.scalars(select(Notification).order_by(Notification.body)).all()
    assert [(n.user_id, n.type, n.reference_id) for n in notifications] == [
        (priya.user.id, NEW_MATCH, match.id),  # "You and Asha..." goes to Priya
        (asha.user.id, NEW_MATCH, match.id),
    ]
    assert notifications[0].body == "You and Asha liked each other."
    assert notifications[1].body == "You and Priya liked each other."


def test_a_pass_never_makes_a_match(member: MakeMember, db: Session) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")
    like(asha, priya)  # Asha likes Priya...

    result = pass_on(priya, asha)  # ...but Priya passes.

    assert result == {"decision": "PASS", "matched": False, "match_id": None}
    assert count(db, Match) == 0


def test_liking_someone_who_passed_on_you_says_nothing_about_it(member: MakeMember) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")
    pass_on(priya, asha)

    # Exactly the same answer as liking someone who has not decided yet.
    assert like(asha, priya) == {"decision": "LIKE", "matched": False, "match_id": None}


def test_repeating_a_decision_changes_nothing(member: MakeMember, db: Session) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")

    assert like(asha, priya) == like(asha, priya)
    matched = like(priya, asha)
    assert like(priya, asha) == matched
    assert like(asha, priya) == matched  # Asha's repeat now reports the match

    assert count(db, Swipe) == 2
    assert count(db, Match) == count(db, Conversation) == 1
    assert count(db, Notification) == 2


def test_a_decision_cannot_be_changed(member: MakeMember) -> None:
    asha, priya, kavya = member("Asha Kumar"), member("Priya Sharma"), member("Kavya Nair")
    like(asha, priya)
    pass_on(asha, kavya)

    changed_like = asha.client.post(f"/api/v1/discovery/{priya.id}/pass", headers=asha.headers)
    changed_pass = asha.client.post(f"/api/v1/discovery/{kavya.id}/like", headers=asha.headers)

    assert changed_like.status_code == changed_pass.status_code == 409
    assert "already liked" in changed_like.json()["error"]["message"]
    assert "already passed on" in changed_pass.json()["error"]["message"]


def test_you_cannot_like_yourself(member: MakeMember) -> None:
    asha = member("Asha Kumar")

    response = asha.client.post(f"/api/v1/discovery/{asha.id}/like", headers=asha.headers)

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "You cannot like or pass on your own profile."


def test_ineligible_people_cannot_be_liked_or_passed(member: MakeMember, db: Session) -> None:
    asha = member("Asha Kumar")
    blocker = member("Blocks Asha")
    db.add(Block(blocker_id=blocker.user.id, blocked_user_id=asha.user.id))
    db.flush()
    targets = [
        blocker.id,
        str(factories.make_member(db, "Suspended", account_status=AccountStatus.SUSPENDED).id),
        str(factories.make_member(db, "Unpublished", published=False).id),
        str(factories.make_member(db, "Unconfirmed", email_verified=False).id),
        "00000000-0000-0000-0000-000000000000",
    ]

    for target in targets:
        for action in ("like", "pass"):
            response = asha.client.post(
                f"/api/v1/discovery/{target}/{action}", headers=asha.headers
            )
            assert response.status_code == 404, (target, action)
    assert count(db, Swipe) == 0


def test_a_block_after_one_like_stops_the_match(member: MakeMember, db: Session) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")
    like(asha, priya)
    db.add(Block(blocker_id=asha.user.id, blocked_user_id=priya.user.id))
    db.flush()

    response = priya.client.post(f"/api/v1/discovery/{asha.id}/like", headers=priya.headers)

    assert response.status_code == 404
    assert count(db, Match) == 0


def test_deciding_needs_a_confirmed_email_and_a_published_profile(
    member: MakeMember, db: Session
) -> None:
    target = member("Target Person")
    unconfirmed = member("Unconfirmed Person", email_verified=False)
    unpublished = member("Unpublished Person", published=False)

    first = unconfirmed.client.post(
        f"/api/v1/discovery/{target.id}/like", headers=unconfirmed.headers
    )
    second = unpublished.client.post(
        f"/api/v1/discovery/{target.id}/like", headers=unpublished.headers
    )

    assert first.status_code == second.status_code == 403
    assert first.json()["error"]["code"] == "email_not_verified"
    assert second.json()["error"]["code"] == "profile_incomplete"
    assert count(db, Swipe) == 0


def test_decisions_need_sign_in_and_the_anti_forgery_token(
    member: MakeMember, new_client: Callable[[], TestClient]
) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")

    visitor = new_client().post(f"/api/v1/discovery/{priya.id}/like")
    no_token = asha.client.post(f"/api/v1/discovery/{priya.id}/like")

    assert visitor.status_code == 401
    assert no_token.status_code == 403


# --- Matches ----------------------------------------------------------------------------------


def _match(asha: Member, priya: Member) -> str:
    like(asha, priya)
    return like(priya, asha)["match_id"]


def test_both_people_see_the_match(member: MakeMember) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")
    match_id = _match(asha, priya)

    for viewer, other in ((asha, "Priya Sharma"), (priya, "Asha Kumar")):
        matches = viewer.client.get("/api/v1/matches").json()
        assert [item["id"] for item in matches] == [match_id]
        assert matches[0]["student"]["full_name"] == other
        assert matches[0]["conversation_id"] is not None
        assert matches[0]["compatibility_score"] == 100
        assert "email" not in str(matches)


def test_match_details_are_for_the_two_people_only(member: MakeMember) -> None:
    asha, priya, stranger = member("Asha Kumar"), member("Priya Sharma"), member("Stranger")
    match_id = _match(asha, priya)

    mine = asha.client.get(f"/api/v1/matches/{match_id}")
    theirs = stranger.client.get(f"/api/v1/matches/{match_id}")

    assert mine.status_code == 200
    assert mine.json()["student"]["full_name"] == "Priya Sharma"
    assert mine.json()["compatibility"]["score"] == 100
    assert theirs.status_code == 404
    assert stranger.client.get("/api/v1/matches").json() == []
    assert new_list_is_empty(stranger)


def new_list_is_empty(person: Member) -> bool:
    return person.client.get("/api/v1/notifications").json() == {"items": [], "unread_count": 0}


def test_a_block_or_suspension_hides_the_match(member: MakeMember, db: Session) -> None:
    asha, priya, kavya = member("Asha Kumar"), member("Priya Sharma"), member("Kavya Nair")
    blocked_match = _match(asha, priya)
    suspended_match = _match(asha, kavya)
    db.add(Block(blocker_id=priya.user.id, blocked_user_id=asha.user.id))
    kavya.user.account_status = AccountStatus.SUSPENDED
    db.flush()

    assert asha.client.get("/api/v1/matches").json() == []
    assert priya.client.get("/api/v1/matches").json() == []
    for match_id in (blocked_match, suspended_match):
        assert asha.client.get(f"/api/v1/matches/{match_id}").status_code == 404


def test_matches_need_sign_in(api: TestClient) -> None:
    assert api.get("/api/v1/matches").status_code == 401
    sign_up(api)
    assert api.get("/api/v1/matches").json() == []


# --- Notifications ------------------------------------------------------------------------------


def test_match_notifications_can_be_read_and_marked_read(member: MakeMember) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")
    match_id = _match(asha, priya)

    inbox = asha.client.get("/api/v1/notifications").json()
    assert inbox["unread_count"] == 1
    notification = inbox["items"][0]
    assert notification["type"] == NEW_MATCH
    assert notification["reference_type"] == "match"
    assert notification["reference_id"] == match_id

    read = asha.client.post(
        f"/api/v1/notifications/{notification['id']}/read", headers=asha.headers
    )
    assert read.status_code == 200
    assert asha.client.get("/api/v1/notifications").json()["unread_count"] == 0
    assert asha.client.get("/api/v1/notifications?unread_only=true").json()["items"] == []
    # Priya's own notification is untouched...
    assert priya.client.get("/api/v1/notifications").json()["unread_count"] == 1
    # ...and Asha cannot touch it.
    priya_notification = priya.client.get("/api/v1/notifications").json()["items"][0]["id"]
    other = asha.client.post(
        f"/api/v1/notifications/{priya_notification}/read", headers=asha.headers
    )
    assert other.status_code == 404

    all_read = priya.client.post("/api/v1/notifications/read-all", headers=priya.headers)
    assert all_read.status_code == 200
    assert priya.client.get("/api/v1/notifications").json()["unread_count"] == 0


# --- The database's own guarantees ----------------------------------------------------------------


def test_the_database_refuses_a_second_match_for_the_same_pair(
    member: MakeMember, db: Session
) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")
    _match(asha, priya)
    user_one, user_two = ordered_pair(asha.user.id, priya.user.id)

    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Match(user_one_id=user_one, user_two_id=user_two, compatibility_score=50))
        db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():  # the reverse order
        db.add(Match(user_one_id=user_two, user_two_id=user_one, compatibility_score=50))
        db.flush()


def test_the_database_refuses_a_second_conversation_or_notification(
    member: MakeMember, db: Session
) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")
    match_id = _match(asha, priya)

    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Conversation(match_id=match_id))
        db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            Notification(
                user_id=asha.user.id,
                type=NEW_MATCH,
                title="Again",
                body="Again",
                reference_type="match",
                reference_id=match_id,
            )
        )
        db.flush()
    # The rule covers match notifications only; other kinds may repeat.
    db.add(
        Notification(
            user_id=asha.user.id,
            type="SOMETHING_ELSE",
            title="Other",
            body="Other",
            reference_type="match",
            reference_id=match_id,
        )
    )
    db.flush()


def test_the_database_refuses_a_second_decision_on_the_same_person(
    member: MakeMember, db: Session
) -> None:
    asha, priya = member("Asha Kumar"), member("Priya Sharma")
    like(asha, priya)

    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Swipe(actor_id=asha.user.id, target_id=priya.user.id, action="PASS"))
        db.flush()
