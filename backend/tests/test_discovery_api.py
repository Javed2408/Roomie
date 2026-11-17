"""Tests for discovery: who appears, in what order, paging, privacy, and
full profile views."""

from collections.abc import Callable
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Block, Locality, Society
from app.models.enums import AccountStatus, DirectoryStatus, UserRole
from tests import factories
from tests.helpers import Member, sign_up, signed_in_member

pytestmark = pytest.mark.integration

DISCOVERY = "/api/v1/discovery"

MakeMember = Callable[..., Member]


@pytest.fixture
def member(new_client: Callable[[], TestClient], db: Session) -> MakeMember:
    """Make a signed-in, discoverable member: member("Name", **options)."""

    def make(full_name: str = "Priya Sharma", **options: object) -> Member:
        return signed_in_member(new_client, db, full_name, **options)

    return make


def names(response_body: dict) -> list[str]:
    return [item["student"]["full_name"] for item in response_body["items"]]


def discover(viewer: Member, **params: object) -> dict:
    response = viewer.client.get(DISCOVERY, params=params)
    assert response.status_code == 200, response.text
    return response.json()


# --- Who may use discovery ------------------------------------------------------------


def test_discovery_needs_a_signed_in_member(api: TestClient) -> None:
    assert api.get(DISCOVERY).status_code == 401


def test_discovery_needs_a_published_profile(member: MakeMember, api: TestClient) -> None:
    unpublished = member("Draft Person", published=False)
    sign_up(api)  # no profile at all

    for client in (unpublished.client, api):
        response = client.get(DISCOVERY)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "profile_incomplete"


# --- Who appears ----------------------------------------------------------------------------


def test_eligible_people_appear_but_never_yourself(member: MakeMember) -> None:
    viewer = member("Viewer Person")
    member("Asha Kumar")

    body = discover(viewer)

    assert names(body) == ["Asha Kumar"]
    assert body["remaining"] == 1


def test_ineligible_people_never_appear(member: MakeMember, db: Session) -> None:
    viewer = member("Viewer Person")
    # These people never sign in here, so they are made directly.
    factories.make_member(db, "Shown Person")
    factories.make_member(db, "Unpublished Person", published=False)
    factories.make_member(db, "Unconfirmed Email Person", email_verified=False)
    factories.make_member(db, "Suspended Person", account_status=AccountStatus.SUSPENDED)
    factories.make_member(db, "Deleted Person", account_status=AccountStatus.DELETED)
    factories.make_member(db, "Admin Person", role=UserRole.ADMIN)
    factories.make_student(db, "No Preferences Person")  # profile not published

    assert names(discover(viewer)) == ["Shown Person"]


def test_a_block_in_either_direction_hides_both_people(member: MakeMember, db: Session) -> None:
    viewer = member("Viewer Person")
    blocked_by_viewer = member("Blocked By Viewer")
    blocked_viewer = member("Blocked The Viewer")
    member("Unrelated Person")
    db.add_all(
        [
            Block(blocker_id=viewer.user.id, blocked_user_id=blocked_by_viewer.user.id),
            Block(blocker_id=blocked_viewer.user.id, blocked_user_id=viewer.user.id),
        ]
    )
    db.flush()

    assert names(discover(viewer)) == ["Unrelated Person"]
    # ...and the viewer does not appear to either of them.
    assert "Viewer Person" not in names(discover(blocked_by_viewer))
    assert "Viewer Person" not in names(discover(blocked_viewer))


def test_people_already_liked_or_passed_do_not_come_back(member: MakeMember) -> None:
    viewer = member("Viewer Person")
    liked, passed = member("Liked Person"), member("Passed Person")
    member("Undecided Person")

    viewer.client.post(f"{DISCOVERY}/{liked.id}/like", headers=viewer.headers)
    viewer.client.post(f"{DISCOVERY}/{passed.id}/pass", headers=viewer.headers)

    assert names(discover(viewer)) == ["Undecided Person"]


def test_someone_who_passed_on_you_still_appears(member: MakeMember) -> None:
    # Their decision is private: hiding them would reveal it.
    viewer, other = member("Viewer Person"), member("Other Person")
    other.client.post(f"{DISCOVERY}/{viewer.id}/pass", headers=other.headers)

    assert names(discover(viewer)) == ["Other Person"]


# --- Order and paging ---------------------------------------------------------------------


def test_shared_societies_come_first_then_the_same_area(member: MakeMember, db: Session) -> None:
    potheri, guduvanchery = factories.make_locality(db), factories.make_locality(db)
    lancor = factories.make_society(db, "Lancor Abode Valley", locality=potheri)
    dac = factories.make_society(db, "DAC Urban Park", locality=potheri)
    lumina = factories.make_society(db, "Lancor Lumina", locality=guduvanchery)

    viewer = member("Viewer Person", societies=[lancor])
    # A different area but otherwise identical: a high score.
    member("Elsewhere Person", societies=[lumina])
    # Same society but a budget that does not overlap: a lower score.
    member("Same Society Person", societies=[lancor], min_budget=20000, max_budget=25000)
    member("Same Area Person", societies=[dac])

    body = discover(viewer)

    assert names(body) == ["Same Society Person", "Same Area Person", "Elsewhere Person"]
    assert [item["compatibility"]["area_overlap"] for item in body["items"]] == [
        "SAME_SOCIETY",
        "SAME_LOCALITY",
        "NONE",
    ]


def test_higher_scores_come_first_within_a_group(member: MakeMember) -> None:
    viewer = member("Viewer Person")
    member("Far Budget", min_budget=20000, max_budget=25000)
    member("Same Budget")
    member("Near Budget", min_budget=11000, max_budget=16000)

    scores = [item["compatibility"]["score"] for item in discover(viewer)["items"]]

    assert names(discover(viewer)) == ["Same Budget", "Near Budget", "Far Budget"]
    assert scores == sorted(scores, reverse=True)


def test_pages_cover_everyone_once(member: MakeMember) -> None:
    viewer = member("Viewer Person")
    for number in range(5):
        member(f"Person {number}", min_budget=8000 + number * 1000, max_budget=14000)

    first = discover(viewer, limit=2)
    second = discover(viewer, limit=2, cursor=first["next_cursor"])
    third = discover(viewer, limit=2, cursor=second["next_cursor"])

    seen = names(first) + names(second) + names(third)
    assert len(seen) == len(set(seen)) == 5
    assert third["next_cursor"] is None
    assert first["remaining"] == 5


def test_deciding_between_pages_does_not_skip_anyone(member: MakeMember) -> None:
    viewer = member("Viewer Person")
    for number in range(4):
        member(f"Person {number}", min_budget=8000 + number * 1000, max_budget=14000)

    first = discover(viewer, limit=2)
    for item in first["items"]:
        viewer.client.post(f"{DISCOVERY}/{item['student']['id']}/pass", headers=viewer.headers)
    second = discover(viewer, limit=2, cursor=first["next_cursor"])

    assert len(set(names(first) + names(second))) == 4
    assert second["remaining"] == 2


@pytest.mark.parametrize("cursor", ["not-a-cursor", "W10=", "WzEsICJ4IiwgM10="])
def test_a_broken_page_link_is_refused(member: MakeMember, cursor: str) -> None:
    viewer = member("Viewer Person")

    response = viewer.client.get(DISCOVERY, params={"cursor": cursor})

    assert response.status_code == 422


def test_page_size_is_limited(member: MakeMember) -> None:
    viewer = member("Viewer Person")

    assert viewer.client.get(DISCOVERY, params={"limit": 51}).status_code == 422
    assert viewer.client.get(DISCOVERY, params={"limit": 0}).status_code == 422


# --- What is shown ------------------------------------------------------------------------


def test_cards_hold_public_information_only(member: MakeMember, db: Session) -> None:
    viewer = member("Viewer Person")
    hidden = factories.make_society(db, "Unverified Heights", verified=False)
    shown = factories.make_society(db, "Shown Residency")
    other = member(
        "Kavya Nair",
        societies=[hidden, shown],
        profile={
            "date_of_birth": date(2004, 5, 17),
            "gender": "WOMAN",
            "gender_visible": False,
            "profile_photo_key": "private/photos/secret-key.jpg",
        },
    )

    response = viewer.client.get(DISCOVERY)
    text = response.text
    student = response.json()["items"][0]["student"]

    assert other.user.email not in text
    assert "2004-05-17" not in text
    assert "secret-key" not in text
    assert "12 Private Lane" not in text  # the society's private address
    assert "Unverified Heights" not in text
    assert student["gender"] is None
    assert [item["society"]["name"] for item in student["societies"]] == ["Shown Residency"]
    assert student["societies"][0]["priority"] == 1  # ranked among public ones
    assert student["identity_verification"] == "NOT_VERIFIED"
    assert set(student) == {
        "id",
        "full_name",
        "college_name",
        "course",
        "department",
        "academic_year",
        "bio",
        "gender",
        "preferences",
        "societies",
        "identity_verification",
        "student_verification",
    }


def test_a_gender_the_student_chose_to_show_is_shown(member: MakeMember) -> None:
    viewer = member("Viewer Person")
    member("Shown Gender", profile={"gender": "WOMAN", "gender_visible": True})

    assert discover(viewer)["items"][0]["student"]["gender"] == "WOMAN"


def test_cards_carry_an_explained_score(member: MakeMember, db: Session) -> None:
    society = factories.make_society(db, "Lancor Abode Valley")
    viewer = member("Viewer Person", societies=[society])
    member("Asha Kumar", societies=[society], food_preference=None)

    compatibility = discover(viewer)["items"][0]["compatibility"]

    assert compatibility["score"] == 100
    assert compatibility["unavailable"] == ["food"]
    assert "You both prefer Lancor Abode Valley." in compatibility["summary"]
    factors = {factor["key"]: factor for factor in compatibility["factors"]}
    assert set(factors) == {"budget", "societies", "lifestyle", "move_in", "room", "food"}
    assert factors["food"]["available"] is False
    assert factors["food"]["effective_weight"] == 0
    assert factors["budget"]["weight"] == 25


# --- Societies that no longer count ----------------------------------------------------------


def test_a_shared_but_unverified_society_never_raises_the_score(
    member: MakeMember, db: Session
) -> None:
    potheri, guduvanchery = factories.make_locality(db), factories.make_locality(db)
    shared = factories.make_society(db, "Shared Then Unverified", locality=potheri)
    mine = factories.make_society(db, "Viewer Choice", locality=potheri)
    theirs = factories.make_society(db, "Their Choice", locality=guduvanchery)
    viewer = member("Viewer Person", societies=[shared, mine])
    member("Other Person", societies=[shared, theirs])

    _withdraw(db, shared)
    compatibility = discover(viewer)["items"][0]["compatibility"]

    assert compatibility["area_overlap"] == "NONE"
    assert compatibility["shared_societies"] == []
    societies = next(f for f in compatibility["factors"] if f["key"] == "societies")
    assert societies["score"] == 0


def test_an_inactive_locality_makes_the_society_factor_unavailable(
    member: MakeMember, db: Session
) -> None:
    potheri = factories.make_locality(db)
    shared = factories.make_society(db, "Shared Society", locality=potheri)
    viewer = member("Viewer Person", societies=[shared])
    member("Other Person", societies=[shared])

    potheri.is_active = False  # the whole area switched off
    db.flush()
    compatibility = discover(viewer)["items"][0]["compatibility"]

    assert compatibility["unavailable"] == ["societies"]
    assert compatibility["area_overlap"] == "UNKNOWN"
    # The other five factors are all perfect, and are all that count now.
    assert compatibility["score"] == 100
    assert "Could not compare: societies." in compatibility["summary"]


def _withdraw(db: Session, record: Society | Locality) -> None:
    record.verification_status = DirectoryStatus.UNVERIFIED
    record.verified_at = None
    record.verified_by = None
    db.flush()


# --- Full profiles ------------------------------------------------------------------------------


def test_a_full_profile_opens_with_the_score(member: MakeMember) -> None:
    viewer, other = member("Viewer Person"), member("Asha Kumar")

    response = viewer.client.get(f"/api/v1/students/{other.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["student"]["full_name"] == "Asha Kumar"
    assert body["compatibility"]["score"] == 100
    assert body["your_decision"] is None
    assert body["match_id"] is None


def test_hidden_profiles_look_exactly_like_missing_ones(member: MakeMember, db: Session) -> None:
    viewer = member("Viewer Person")
    blocked = member("Blocked Person")
    db.add(Block(blocker_id=blocked.user.id, blocked_user_id=viewer.user.id))
    db.flush()
    hidden = [
        blocked.id,
        factories.make_member(db, "Suspended", account_status=AccountStatus.SUSPENDED).id,
        factories.make_member(db, "Unpublished", published=False).id,
        factories.make_member(db, "Unconfirmed", email_verified=False).id,
        viewer.id,
        "00000000-0000-0000-0000-000000000000",
    ]

    for student_id in hidden:
        response = viewer.client.get(f"/api/v1/students/{student_id}")
        assert response.status_code == 404, student_id
        assert response.json()["error"]["message"] == "This profile is not available."


def test_a_profile_shows_your_decision_but_never_theirs(member: MakeMember) -> None:
    viewer, other = member("Viewer Person"), member("Other Person")
    # The other person likes the viewer. The viewer must not find out.
    other.client.post(f"{DISCOVERY}/{viewer.id}/like", headers=other.headers)

    before = viewer.client.get(f"/api/v1/students/{other.id}").json()
    viewer.client.post(f"{DISCOVERY}/{other.id}/pass", headers=viewer.headers)
    after = viewer.client.get(f"/api/v1/students/{other.id}").json()

    assert before["your_decision"] is None
    assert before["match_id"] is None
    assert "LIKE" not in str(before)
    assert after["your_decision"] == "PASS"


def test_a_match_can_still_see_a_profile_that_was_later_unpublished(
    member: MakeMember, db: Session
) -> None:
    viewer, other = member("Viewer Person"), member("Other Person")
    other.client.post(f"{DISCOVERY}/{viewer.id}/like", headers=other.headers)
    viewer.client.post(f"{DISCOVERY}/{other.id}/like", headers=viewer.headers)

    other.user.student_profile.profile_completed = False  # type: ignore[union-attr]
    db.flush()
    stranger = member("Stranger Person")

    assert viewer.client.get(f"/api/v1/students/{other.id}").status_code == 200
    assert stranger.client.get(f"/api/v1/students/{other.id}").status_code == 404


def test_viewing_profiles_needs_a_published_profile(member: MakeMember) -> None:
    viewer = member("Draft Person", published=False)
    other = member("Other Person")

    response = viewer.client.get(f"/api/v1/students/{other.id}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "profile_incomplete"


def test_a_suspended_viewer_cannot_use_discovery(member: MakeMember, db: Session) -> None:
    viewer = member("Viewer Person")
    member("Other Person")

    viewer.user.account_status = AccountStatus.SUSPENDED
    viewer.user.updated_at = datetime.now(UTC)
    db.flush()

    assert viewer.client.get(DISCOVERY).status_code == 401
