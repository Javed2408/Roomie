"""Tests for expressing interest in a listing, and the creator's replies."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Block, ListingInterest, Notification
from app.models.enums import AccountStatus
from tests import factories
from tests.helpers import Member, signed_in_member, signed_in_user
from tests.listing_helpers import ME, create, property_body, published_property

pytestmark = pytest.mark.integration

MakePerson = Callable[..., Member]


@pytest.fixture
def owner(new_client: Callable[[], TestClient], db: Session) -> Member:
    """A property owner with no student profile."""
    return signed_in_user(new_client, db)


@pytest.fixture
def student(new_client: Callable[[], TestClient], db: Session) -> MakePerson:
    def make(full_name: str = "Priya Sharma", **options: Any) -> Member:
        return signed_in_member(new_client, db, full_name, **options)

    return make


@pytest.fixture
def listing(owner: Member, db: Session) -> dict[str, Any]:
    return published_property(db, owner, factories.make_society(db, "Lancor Abode Valley"))


def express(member: Member, listing_id: str, **body: Any) -> Any:
    return member.client.post(
        f"/api/v1/listings/{listing_id}/interest", json=body, headers=member.headers
    )


def interested(owner: Member, listing_id: str) -> list[dict[str, Any]]:
    response = owner.client.get(f"{ME}/{listing_id}/interests")
    assert response.status_code == 200, response.text
    return response.json()


def test_a_student_expresses_interest_and_the_creator_sees_their_profile(
    owner: Member, student: MakePerson, listing: dict[str, Any], db: Session
) -> None:
    asha = student("Asha Kumar")

    response = express(asha, listing["id"])

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"
    [entry] = interested(owner, listing["id"])
    assert entry["student"]["full_name"] == "Asha Kumar"
    assert entry["student"]["preferences"]["min_budget"] == 8000
    # An owner without a student profile has nothing to compare with.
    assert entry["compatibility"] is None
    assert asha.user.email not in str(entry)
    # The creator was told, and can open the student's full profile even
    # without a student profile of their own.
    note = db.scalar(
        select(Notification).where(
            Notification.user_id == owner.user.id, Notification.type == "LISTING_INTEREST"
        )
    )
    assert note is not None and "Asha K." in note.body
    assert owner.client.get(f"/api/v1/students/{asha.id}").status_code == 200
    # The student sees it under their interests, and on the listing.
    mine = asha.client.get("/api/v1/me/interests").json()
    assert [(item["title"], item["status"]) for item in mine] == [
        ("Room free in a 3BHK", "PENDING")
    ]
    assert asha.client.get(f"/api/v1/listings/{listing['id']}").json()["your_interest"] == "PENDING"


def test_interest_cannot_be_sent_twice(
    student: MakePerson, listing: dict[str, Any], db: Session
) -> None:
    asha = student("Asha Kumar")
    express(asha, listing["id"])

    again = express(asha, listing["id"])

    assert again.status_code == 409
    count = db.scalar(select(func.count()).select_from(ListingInterest))
    assert count == 1


def test_withdrawn_interest_can_be_renewed_but_a_declined_one_cannot(
    owner: Member, student: MakePerson, listing: dict[str, Any]
) -> None:
    asha = student("Asha Kumar")
    express(asha, listing["id"])
    withdrawn = asha.client.delete(
        f"/api/v1/listings/{listing['id']}/interest", headers=asha.headers
    )
    assert withdrawn.status_code == 200
    assert interested(owner, listing["id"]) == []

    assert express(asha, listing["id"]).status_code == 201
    [entry] = interested(owner, listing["id"])
    owner.client.post(
        f"{ME}/{listing['id']}/interests/{entry['interest_id']}",
        json={"status": "DECLINED"},
        headers=owner.headers,
    )
    asha.client.delete(f"/api/v1/listings/{listing['id']}/interest", headers=asha.headers)

    assert express(asha, listing["id"]).status_code == 409


def test_the_creator_accepts_and_the_student_is_told(
    owner: Member, student: MakePerson, listing: dict[str, Any], db: Session
) -> None:
    asha = student("Asha Kumar")
    express(asha, listing["id"])
    [entry] = interested(owner, listing["id"])

    accepted = owner.client.post(
        f"{ME}/{listing['id']}/interests/{entry['interest_id']}",
        json={"status": "ACCEPTED"},
        headers=owner.headers,
    )

    assert accepted.json()[0]["status"] == "ACCEPTED"
    assert accepted.json()[0]["responded_at"] is not None
    note = db.scalar(
        select(Notification).where(
            Notification.user_id == asha.user.id, Notification.type == "INTEREST_ACCEPTED"
        )
    )
    assert note is not None
    # A reply is final.
    again = owner.client.post(
        f"{ME}/{listing['id']}/interests/{entry['interest_id']}",
        json={"status": "DECLINED"},
        headers=owner.headers,
    )
    assert again.status_code == 409


def test_brokerage_must_be_acknowledged_and_is_recorded(
    owner: Member, student: MakePerson, db: Session
) -> None:
    brokered = published_property(
        db,
        owner,
        factories.make_society(db),
        brokerage_applicable=True,
        brokerage_amount=7500,
        brokerage_payable_to="THIRD_PARTY_AGENT",
    )
    asha = student("Asha Kumar")

    refused = express(asha, brokered["id"])
    accepted = express(asha, brokered["id"], acknowledge_brokerage=True)

    assert refused.status_code == 422
    assert "₹7,500" in refused.json()["error"]["message"]
    assert accepted.status_code == 201
    interest = db.scalar(select(ListingInterest))
    assert interest is not None and interest.acknowledged_brokerage_amount == 7500


def test_you_cannot_be_interested_in_your_own_or_a_hidden_listing(
    owner: Member, student: MakePerson, db: Session
) -> None:
    member = student("Asha Kumar")
    own = published_property(db, member, factories.make_society(db))
    draft = create(owner, property_body(factories.make_society(db), title="A draft"))["listing"]

    assert express(member, own["id"]).status_code == 422
    assert express(member, draft["id"]).status_code == 404


def test_interest_needs_a_published_profile_and_a_confirmed_email(
    student: MakePerson, owner: Member, listing: dict[str, Any], new_client, db: Session
) -> None:
    unpublished = student("Draft Person", published=False)
    unconfirmed = student("Unconfirmed Person", email_verified=False)
    no_profile = signed_in_user(new_client, db)

    assert express(unpublished, listing["id"]).json()["error"]["code"] == "profile_incomplete"
    assert express(no_profile, listing["id"]).json()["error"]["code"] == "profile_incomplete"
    assert express(unconfirmed, listing["id"]).json()["error"]["code"] == "email_not_verified"


def test_blocks_and_suspensions_hide_interest_both_ways(
    owner: Member, student: MakePerson, listing: dict[str, Any], db: Session
) -> None:
    blocked_by_owner = student("Blocked Person")
    later_blocked = student("Later Blocked")
    suspended = student("Suspended Person")
    db.add(Block(blocker_id=owner.user.id, blocked_user_id=blocked_by_owner.user.id))
    db.flush()

    # Someone the owner blocked cannot see the listing, so cannot be interested.
    assert express(blocked_by_owner, listing["id"]).status_code == 404

    express(later_blocked, listing["id"])
    express(suspended, listing["id"])
    db.add(Block(blocker_id=later_blocked.user.id, blocked_user_id=owner.user.id))
    suspended.user.account_status = AccountStatus.SUSPENDED
    db.flush()

    # Neither appears to the owner any more.
    assert interested(owner, listing["id"]) == []


def test_only_the_creator_sees_who_is_interested(
    owner: Member,
    student: MakePerson,
    listing: dict[str, Any],
    new_client: Callable[[], TestClient],
    db: Session,
) -> None:
    asha = student("Asha Kumar")
    express(asha, listing["id"])
    other_student = student("Someone Else")
    unrelated_owner = signed_in_user(new_client, db)

    assert other_student.client.get(f"{ME}/{listing['id']}/interests").status_code == 404
    # The interest lets THIS listing's creator open Asha's profile. Another
    # account without a student profile gains nothing from it.
    assert owner.client.get(f"/api/v1/students/{asha.id}").status_code == 200
    refused = unrelated_owner.client.get(f"/api/v1/students/{asha.id}")
    assert refused.status_code == 403
    assert unrelated_owner.client.get(f"/api/v1/students/{asha.id}/photo").status_code == 404
