"""Tests for creating, editing, submitting and closing listings, the anti-
broker evidence rules, and which listings the public can see."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AccommodationListing, Block, ListingChange, Notification
from app.models.enums import (
    AccountStatus,
    DirectoryStatus,
    DocumentType,
    ModerationStatus,
    UserRole,
)
from app.models.enums import VerificationStatus as VS
from app.services.listing_moderation import moderate_listing
from app.services.verification import record_owner_confirmation, review_verification
from tests import factories
from tests.helpers import Member, log_in, make_admin_account, signed_in_member, signed_in_user
from tests.listing_helpers import (
    ME,
    approve_everything,
    create,
    property_body,
    published_property,
    search_body,
    submit,
    upload_evidence,
)

pytestmark = pytest.mark.integration

LISTINGS = "/api/v1/listings"
MakePerson = Callable[..., Member]


@pytest.fixture
def owner(new_client: Callable[[], TestClient], db: Session) -> Member:
    """A property owner: an account with a confirmed email, not a student."""
    return signed_in_user(new_client, db)


@pytest.fixture
def student(new_client: Callable[[], TestClient], db: Session) -> MakePerson:
    def make(full_name: str = "Priya Sharma", **options: Any) -> Member:
        return signed_in_member(new_client, db, full_name, **options)

    return make


@pytest.fixture
def society(db: Session):  # noqa: ANN201 - a fixture
    return factories.make_society(db, "Lancor Abode Valley")


def browse(member: Member, **params: Any) -> dict[str, Any]:
    response = member.client.get(LISTINGS, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def titles(page: dict[str, Any]) -> list[str]:
    return [item["title"] for item in page["items"]]


# --- Creating ---------------------------------------------------------------------------


def test_an_owner_creates_a_private_draft(
    owner: Member, student: MakePerson, db: Session, society
) -> None:
    body = create(owner, property_body(society))

    assert body["lifecycle_status"] == "DRAFT"
    assert body["moderation_status"] == "PENDING"
    assert body["is_public"] is False
    assert body["authority"]["status"] == "NOT_SUBMITTED"
    listing = db.get(AccommodationListing, body["listing"]["id"])
    assert listing is not None and listing.authority_declared_at is not None
    assert body["listing"]["facilities"] == ["WIFI", "POWER_BACKUP"]
    # Nobody else can find it.
    viewer = student("Viewer Person")
    assert browse(viewer)["total"] == 0
    assert viewer.client.get(f"{LISTINGS}/{body['listing']['id']}").status_code == 404
    # Its creation is the first entry in its history.
    assert body["history"][0]["summary"] == "Created as a draft."


@pytest.mark.parametrize("creator_type", ["EXISTING_TENANT", "AUTHORIZED_AGENT"])
def test_tenants_and_agents_can_create_property_listings(
    owner: Member, society, creator_type: str
) -> None:
    body = create(owner, property_body(society, creator_type=creator_type))

    assert body["listing"]["creator_type"] == creator_type


def test_a_find_together_request_has_no_property_fields(student: MakePerson, db: Session) -> None:
    first, second = factories.make_society(db), factories.make_society(db)
    member = student("Asha Kumar")

    body = create(member, search_body(first, second))

    listing = body["listing"]
    assert listing["type"] == "LOOKING_TO_RENT_TOGETHER"
    assert listing["creator_type"] is None
    assert listing["brokerage"] is None
    assert listing["society"] is None
    assert [item["id"] for item in listing["preferred_societies"]] == [
        str(first.id),
        str(second.id),
    ]
    assert body["authority"] is None


def test_a_find_together_request_needs_a_published_profile(
    student: MakePerson, owner: Member, society
) -> None:
    unpublished = student("Draft Person", published=False)

    for person in (unpublished, owner):
        response = person.client.post(ME, json=search_body(society), headers=person.headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "profile_incomplete"


def test_creating_needs_a_confirmed_email_and_a_member_account(
    new_client: Callable[[], TestClient], db: Session, society
) -> None:
    unconfirmed = signed_in_user(new_client, db, email_verified=False)
    make_admin_account(db, "listing-admin@example.com")
    admin_client = new_client()
    admin_headers = log_in(admin_client, "listing-admin@example.com")
    visitor = new_client()

    assert (
        unconfirmed.client.post(ME, json=property_body(society), headers=unconfirmed.headers)
    ).json()["error"]["code"] == "email_not_verified"
    assert (
        admin_client.post(ME, json=property_body(society), headers=admin_headers).status_code == 403
    )
    assert visitor.post(ME, json=property_body(society)).status_code == 401


def test_changes_need_the_anti_forgery_token(owner: Member, society) -> None:
    assert owner.client.post(ME, json=property_body(society)).status_code == 403


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"creator_type": "BROKER"}, "creator_type"),
        ({"brokerage_applicable": True}, "brokerage amount"),
        ({"brokerage_applicable": True, "brokerage_amount": 9000}, "who receives"),
        (
            {
                "brokerage_applicable": True,
                "brokerage_amount": 9000,
                "brokerage_payable_to": "LISTING_CREATOR",
            },
            "Only an authorised agent can collect brokerage",
        ),
        ({"brokerage_amount": 5000}, "Leave the brokerage details empty"),
        (
            {
                "brokerage_applicable": True,
                "brokerage_amount": 0,
                "brokerage_payable_to": "THIRD_PARTY_AGENT",
            },
            "brokerage_amount",
        ),
        ({"available_bedrooms": 4}, "cannot be more than the bedrooms"),
        ({"available_from": "2020-01-01"}, "cannot be in the past"),
        ({"description": "Call me on 98765 43210 to book."}, "Remove phone numbers"),
        ({"title": "Mail flats@example.com"}, "Remove phone numbers"),
        ({"facilities": ["WIFI", "WIFI"]}, "only be chosen once"),
        ({"facilities": ["HELIPAD"]}, "facilities"),
        ({"confirmed_authority": False}, "confirmed_authority"),
        ({"rent_per_person": 50}, "rent_per_person"),
    ],
)
def test_invalid_listings_are_refused(
    owner: Member, society, override: dict[str, Any], message: str
) -> None:
    response = owner.client.post(ME, json=property_body(society, **override), headers=owner.headers)

    assert response.status_code == 422, response.text
    assert message in response.text


def test_an_unverified_society_cannot_be_chosen(owner: Member, db: Session) -> None:
    hidden = factories.make_society(db, "Unverified Heights", verified=False)

    response = owner.client.post(ME, json=property_body(hidden), headers=owner.headers)

    assert response.status_code == 422
    assert "directory" in response.json()["error"]["message"]


def test_a_duplicate_listing_is_refused(owner: Member, society) -> None:
    create(owner, property_body(society))

    again = owner.client.post(ME, json=property_body(society), headers=owner.headers)

    assert again.status_code == 409


def test_too_many_open_listings_are_refused(owner: Member, society) -> None:
    for number in range(10):
        create(owner, property_body(society, title=f"Room number {number}"))

    response = owner.client.post(
        ME, json=property_body(society, title="One too many"), headers=owner.headers
    )

    assert response.status_code == 422
    assert "at most 10" in response.json()["error"]["message"]


# --- Ownership ---------------------------------------------------------------------------


def test_someone_elses_listing_does_not_exist_for_you(
    owner: Member, new_client: Callable[[], TestClient], db: Session, society
) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]
    intruder = signed_in_user(new_client, db)

    for method, path, body in [
        ("get", f"{ME}/{listing_id}", None),
        ("put", f"{ME}/{listing_id}", property_body(society, title="Mine now")),
        ("delete", f"{ME}/{listing_id}", None),
        ("post", f"{ME}/{listing_id}/submit", None),
        ("post", f"{ME}/{listing_id}/lifecycle", {"status": "CLOSED"}),
        ("get", f"{ME}/{listing_id}/interests", None),
        ("get", f"{ME}/{listing_id}/authority-verification", None),
    ]:
        response = intruder.client.request(method, path, json=body, headers=intruder.headers)
        assert response.status_code == 404, (method, path)


# --- Submitting and the evidence rules --------------------------------------------------------


def test_an_owner_must_upload_proof_and_submit_identity_before_submitting(
    owner: Member, db: Session, society
) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]

    refused = owner.client.post(f"{ME}/{listing_id}/submit", headers=owner.headers)
    assert refused.status_code == 422
    assert refused.json()["error"]["details"] == [
        "Upload proof that you own the property.",
        "Submit your identity verification (Profile, then Verification).",
    ]

    upload_evidence(owner, listing_id, "OWNERSHIP_PROOF")
    factories.make_identity_verification(db, owner.user)  # submitted, not yet approved
    body = submit(owner, listing_id)

    # Submitted, waiting for a person, and still not public.
    assert body["lifecycle_status"] == "ACTIVE"
    assert body["moderation_status"] == "PENDING"
    assert body["is_public"] is False
    assert body["authority"]["status"] == "PENDING"
    assert body["authority"]["documents"] == ["OWNERSHIP_PROOF"]


def test_uploading_evidence_never_approves_anything(owner: Member, db: Session, society) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]
    factories.approve_identity(db, owner.user)
    upload_evidence(owner, listing_id, "OWNERSHIP_PROOF")
    submit(owner, listing_id)
    listing = db.get(AccommodationListing, listing_id)
    assert listing is not None
    db.refresh(listing)

    assert listing.authority_verification is not None
    assert listing.authority_verification.status == VS.PENDING
    # An admin cannot approve the listing until the authority is verified.
    with pytest.raises(Exception, match="listing authority has been verified"):
        moderate_listing(
            db, listing, new_status=ModerationStatus.APPROVED, actor=factories.make_admin(db)
        )


def test_a_tenant_listing_is_approved_only_with_permission_to_share(
    owner: Member, student: MakePerson, db: Session, society
) -> None:
    listing_id = create(owner, property_body(society, creator_type="EXISTING_TENANT"))["listing"][
        "id"
    ]
    refused = owner.client.post(f"{ME}/{listing_id}/submit", headers=owner.headers)
    assert refused.json()["error"]["details"] == ["Upload your current rental agreement."]

    upload_evidence(owner, listing_id, "RENTAL_AGREEMENT")
    upload_evidence(owner, listing_id, "LANDLORD_PERMISSION")
    submit(owner, listing_id)
    approve_everything(db, listing_id)

    assert titles(browse(student("Viewer Person"))) == ["Room free in a 3BHK"]


def test_an_agent_needs_identity_owner_authorisation_and_owner_confirmation(
    owner: Member, student: MakePerson, db: Session, society
) -> None:
    body = property_body(
        society,
        creator_type="AUTHORIZED_AGENT",
        brokerage_applicable=True,
        brokerage_amount=9000,
        brokerage_payable_to="LISTING_CREATOR",
        brokerage_note="One month's rent, paid once",
    )
    listing_id = create(owner, body)["listing"]["id"]
    refused = owner.client.post(f"{ME}/{listing_id}/submit", headers=owner.headers)
    assert refused.json()["error"]["details"] == [
        "Upload the owner's written authorisation for this property.",
        "Give the owner's name and contact details, so Roomie can confirm with them directly.",
        "Submit your identity verification (Profile, then Verification).",
    ]

    upload_evidence(
        owner,
        listing_id,
        "OWNER_AUTHORIZATION",
        owner_name="Lakshmi Narayanan",
        owner_contact="+91 90000 11111",
    )
    factories.make_identity_verification(db, owner.user)
    submit(owner, listing_id)
    admin = factories.make_admin(db)
    listing = db.get(AccommodationListing, listing_id)
    assert listing is not None and listing.authority_verification is not None
    authority = listing.authority_verification

    # The agent's own paperwork is not enough: identity and the owner's
    # independent confirmation are still missing.
    with pytest.raises(Exception) as failure:
        review_verification(db, authority, new_status=VS.APPROVED, reviewer=admin)
    assert "owner has not independently confirmed" in str(failure.value.details)

    factories.approve_identity(db, owner.user, admin)
    record_owner_confirmation(db, authority, confirmed=True, admin=admin, note="Called owner.")
    review_verification(db, authority, new_status=VS.APPROVED, reviewer=admin)
    moderate_listing(db, listing, new_status=ModerationStatus.APPROVED, actor=admin)

    shown = browse(student("Viewer Person"))["items"][0]
    assert shown["creator_type"] == "AUTHORIZED_AGENT"
    assert shown["listing_authority"] == "VERIFIED"
    assert shown["brokerage"] == {
        "applicable": True,
        "amount": 9000,
        "note": "One month's rent, paid once",
        "payable_to": "LISTING_CREATOR",
    }
    # The owner's private details never reach the public.
    assert "Lakshmi" not in str(shown)
    assert "90000" not in str(shown)


def test_submitting_twice_is_refused(owner: Member, db: Session, society) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]
    factories.approve_identity(db, owner.user)
    upload_evidence(owner, listing_id, "OWNERSHIP_PROOF")
    submit(owner, listing_id)

    again = owner.client.post(f"{ME}/{listing_id}/submit", headers=owner.headers)

    assert again.status_code == 409


def test_rejected_evidence_must_be_replaced_before_resubmitting(
    owner: Member, db: Session, society
) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]
    factories.approve_identity(db, owner.user)
    upload_evidence(owner, listing_id, "OWNERSHIP_PROOF")
    submit(owner, listing_id)
    admin = factories.make_admin(db)
    listing = db.get(AccommodationListing, listing_id)
    assert listing is not None and listing.authority_verification is not None
    review_verification(
        db,
        listing.authority_verification,
        new_status=VS.REJECTED,
        reviewer=admin,
        note="The document is unreadable. Upload a clearer scan.",
    )
    moderate_listing(
        db,
        listing,
        new_status=ModerationStatus.REJECTED,
        actor=admin,
        note="Evidence not accepted.",
    )

    body = owner.client.get(f"{ME}/{listing_id}").json()
    assert body["moderation_reason"] == "Evidence not accepted."
    assert body["authority"]["reason"] == "The document is unreadable. Upload a clearer scan."
    assert body["can_submit"] is False
    # The creator was told what to do.
    kinds = set(db.scalars(select(Notification.type).where(Notification.user_id == owner.user.id)))
    assert {"AUTHORITY_NEEDS_ATTENTION", "LISTING_REJECTED"} <= kinds

    upload_evidence(owner, listing_id, "OWNERSHIP_PROOF")  # back to pending review
    resubmitted = submit(owner, listing_id)
    assert resubmitted["moderation_status"] == "PENDING"
    assert resubmitted["authority"]["status"] == "PENDING"


def test_members_cannot_approve_anything(
    owner: Member, student: MakePerson, db: Session, society
) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]
    factories.approve_identity(db, owner.user)
    upload_evidence(owner, listing_id, "OWNERSHIP_PROOF")
    submit(owner, listing_id)
    listing = db.get(AccommodationListing, listing_id)
    assert listing is not None and listing.authority_verification is not None
    verification_id = listing.authority_verification.id

    for person in (owner, student("Someone Else")):
        moderation = person.client.post(
            f"/api/v1/admin/listings/{listing_id}/moderation",
            json={"status": "APPROVED"},
            headers=person.headers,
        )
        review = person.client.post(
            f"/api/v1/admin/verifications/listing-authority/{verification_id}/review",
            json={"status": "APPROVED"},
            headers=person.headers,
        )
        assert moderation.status_code == review.status_code == 403
    # Statuses sent by the creator are ignored, not obeyed.
    owner.client.put(
        f"{ME}/{listing_id}",
        json=property_body(society, moderation_status="APPROVED", lifecycle_status="ACTIVE"),
        headers=owner.headers,
    )
    db.refresh(listing)
    assert listing.moderation_status == ModerationStatus.PENDING


def test_an_administrator_can_review_and_publish_through_the_api(
    owner: Member, new_client: Callable[[], TestClient], db: Session, society
) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]
    factories.approve_identity(db, owner.user)
    upload_evidence(owner, listing_id, "OWNERSHIP_PROOF")
    submit(owner, listing_id)
    make_admin_account(db, "moderator@example.com")
    admin = new_client()
    headers = log_in(admin, "moderator@example.com")

    queue = admin.get("/api/v1/admin/listings").json()
    assert [item["id"] for item in queue] == [listing_id]
    detail = admin.get(f"/api/v1/admin/listings/{listing_id}").json()
    authority_id = detail["authority_verification_id"]
    assert detail["authority_requirements"] == []

    early = admin.post(
        f"/api/v1/admin/listings/{listing_id}/moderation",
        json={"status": "APPROVED"},
        headers=headers,
    )
    assert early.status_code == 422
    admin.post(
        f"/api/v1/admin/verifications/listing-authority/{authority_id}/review",
        json={"status": "APPROVED"},
        headers=headers,
    )
    approved = admin.post(
        f"/api/v1/admin/listings/{listing_id}/moderation",
        json={"status": "APPROVED"},
        headers=headers,
    )
    assert approved.status_code == 200
    assert approved.json()["moderation_status"] == "APPROVED"
    assert owner.client.get(f"{ME}/{listing_id}").json()["is_public"] is True


# --- Editing ----------------------------------------------------------------------------------


def test_editing_an_approved_listing_sends_it_back_for_review(
    owner: Member, student: MakePerson, db: Session, society
) -> None:
    listing = published_property(db, owner, society)
    viewer = student("Viewer Person")
    assert browse(viewer)["total"] == 1

    edited = owner.client.put(
        f"{ME}/{listing['id']}",
        json=property_body(
            society,
            brokerage_applicable=True,
            brokerage_amount=5000,
            brokerage_payable_to="THIRD_PARTY_AGENT",
        ),
        headers=owner.headers,
    ).json()

    # Hidden until an administrator has looked at the new version...
    assert edited["moderation_status"] == "PENDING"
    assert edited["is_public"] is False
    assert browse(viewer)["total"] == 0
    # ...and the brokerage change is on record, field by field.
    change = db.scalars(
        select(ListingChange)
        .where(ListingChange.listing_id == listing["id"])
        .order_by(ListingChange.sequence.desc())
    ).first()
    assert change is not None
    assert change.changes["brokerage_amount"] == {"from": None, "to": 5000}
    assert change.changes["brokerage_payable_to"] == {"from": None, "to": "THIRD_PARTY_AGENT"}


def test_moving_the_property_to_another_society_rechecks_authority(
    owner: Member, db: Session, society
) -> None:
    listing = published_property(db, owner, society)
    elsewhere = factories.make_society(db, "DAC Urban Park")

    edited = owner.client.put(
        f"{ME}/{listing['id']}", json=property_body(elsewhere), headers=owner.headers
    ).json()

    assert edited["authority"]["status"] == "PENDING"
    assert edited["moderation_status"] == "PENDING"


def test_a_listing_type_cannot_change(owner: Member, student: MakePerson, society) -> None:
    member = student("Asha Kumar")
    listing_id = create(member, search_body(society))["listing"]["id"]

    response = member.client.put(
        f"{ME}/{listing_id}", json=property_body(society), headers=member.headers
    )

    assert response.status_code == 422


# --- Lifecycle --------------------------------------------------------------------------------


def _lifecycle(member: Member, listing_id: str, status: str) -> Any:
    return member.client.post(
        f"{ME}/{listing_id}/lifecycle", json={"status": status}, headers=member.headers
    )


def test_filled_and_closed_listings_leave_public_view(
    owner: Member, student: MakePerson, db: Session, society
) -> None:
    listing = published_property(db, owner, society)
    viewer = student("Viewer Person")

    assert _lifecycle(owner, listing["id"], "FILLED").status_code == 200
    assert browse(viewer)["total"] == 0
    # Reopening a filled listing needs no new review: nothing changed.
    assert _lifecycle(owner, listing["id"], "ACTIVE").json()["is_public"] is True
    assert _lifecycle(owner, listing["id"], "CLOSED").status_code == 200
    assert browse(viewer)["total"] == 0
    # Closed is final.
    assert _lifecycle(owner, listing["id"], "ACTIVE").status_code == 422
    assert (
        owner.client.put(
            f"{ME}/{listing['id']}", json=property_body(society), headers=owner.headers
        ).status_code
        == 409
    )


def test_a_draft_becomes_active_only_by_submitting(owner: Member, society) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]

    response = _lifecycle(owner, listing_id, "ACTIVE")

    assert response.status_code == 422
    assert "Submit the draft" in response.json()["error"]["message"]


def test_a_suspended_listing_can_only_be_closed(owner: Member, db: Session, society) -> None:
    listing = published_property(db, owner, society)
    record = db.get(AccommodationListing, listing["id"])
    assert record is not None
    moderate_listing(
        db,
        record,
        new_status=ModerationStatus.SUSPENDED,
        actor=factories.make_admin(db),
        note="Reported as a scam.",
    )

    body = owner.client.get(f"{ME}/{listing['id']}").json()
    assert body["moderation_reason"] == "Reported as a scam."
    assert body["can_edit"] is False
    assert (
        owner.client.put(
            f"{ME}/{listing['id']}", json=property_body(society), headers=owner.headers
        ).status_code
        == 409
    )
    assert _lifecycle(owner, listing["id"], "FILLED").status_code == 409
    assert _lifecycle(owner, listing["id"], "CLOSED").status_code == 200


def test_only_an_unsubmitted_draft_can_be_deleted(owner: Member, db: Session, society) -> None:
    draft_id = create(owner, property_body(society, title="Just a draft"))["listing"]["id"]
    evidenced_id = create(owner, property_body(society, title="Has evidence"))["listing"]["id"]
    upload_evidence(owner, evidenced_id, "OWNERSHIP_PROOF")

    assert owner.client.delete(f"{ME}/{draft_id}", headers=owner.headers).status_code == 200
    assert db.get(AccommodationListing, draft_id) is None
    assert owner.client.delete(f"{ME}/{evidenced_id}", headers=owner.headers).status_code == 409


# --- Public visibility ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("lifecycle", "moderation", "visible"),
    [
        ("ACTIVE", "APPROVED", True),
        ("DRAFT", "APPROVED", False),
        ("ACTIVE", "PENDING", False),
        ("ACTIVE", "REJECTED", False),
        ("ACTIVE", "SUSPENDED", False),
        ("FILLED", "APPROVED", False),
        ("CLOSED", "APPROVED", False),
    ],
)
def test_only_active_and_approved_listings_are_public(
    student: MakePerson, db: Session, lifecycle: str, moderation: str, visible: bool
) -> None:
    listing = factories.make_property_listing(
        db, lifecycle_status=lifecycle, moderation_status=moderation
    )
    viewer = student("Viewer Person")

    assert (browse(viewer)["total"] == 1) is visible
    assert (viewer.client.get(f"{LISTINGS}/{listing.id}").status_code == 200) is visible


def _public(db: Session, **overrides: Any) -> AccommodationListing:
    return factories.make_property_listing(
        db, lifecycle_status="ACTIVE", moderation_status="APPROVED", **overrides
    )


def test_a_suspended_creator_takes_their_listings_down(student: MakePerson, db: Session) -> None:
    owner = factories.make_user(db)
    _public(db, owner=owner)
    viewer = student("Viewer Person")
    assert browse(viewer)["total"] == 1

    owner.account_status = AccountStatus.SUSPENDED
    db.flush()

    assert browse(viewer)["total"] == 0


def test_a_listing_whose_society_left_the_directory_is_hidden(
    student: MakePerson, db: Session
) -> None:
    society = factories.make_society(db)
    _public(db, society_id=society.id)
    viewer = student("Viewer Person")

    society.verification_status = DirectoryStatus.UNVERIFIED
    society.verified_by = None
    society.verified_at = None
    db.flush()

    assert browse(viewer)["total"] == 0


def test_blocking_hides_listings_both_ways(student: MakePerson, db: Session) -> None:
    viewer = student("Viewer Person")
    poster = factories.make_user(db)
    _public(db, owner=poster)
    db.add(Block(blocker_id=poster.id, blocked_user_id=viewer.user.id))
    db.flush()

    assert browse(viewer)["total"] == 0


def test_browsing_filters_and_pages(student: MakePerson, db: Session) -> None:
    potheri, guduvanchery = (
        factories.make_locality(db, "Potheri"),
        factories.make_locality(db, "Guduvanchery"),
    )
    lancor = factories.make_society(db, "Lancor Abode Valley", locality=potheri)
    lumina = factories.make_society(db, "Lancor Lumina", locality=guduvanchery)
    _public(db, title="Cheap room", society_id=lancor.id, rent_per_person=7000)
    _public(db, title="Pricey room", society_id=lumina.id, rent_per_person=15000)
    factories.make_search_listing(
        db, title="Looking together", lifecycle_status="ACTIVE", moderation_status="APPROVED"
    )
    viewer = student("Viewer Person")

    assert browse(viewer)["total"] == 3
    assert titles(browse(viewer, type="EXISTING_ACCOMMODATION", sort="rent_low")) == [
        "Cheap room",
        "Pricey room",
    ]
    assert titles(browse(viewer, society_id=str(lancor.id))) == ["Cheap room"]
    assert titles(browse(viewer, locality_id=str(guduvanchery.id))) == ["Pricey room"]
    assert titles(browse(viewer, max_rent=10000, type="EXISTING_ACCOMMODATION")) == ["Cheap room"]
    assert titles(browse(viewer, q="lumina")) == ["Pricey room"]
    first = browse(viewer, limit=2)
    second = browse(viewer, limit=2, offset=2)
    assert first["total"] == 3
    assert len(first["items"]) == 2
    assert len(second["items"]) == 1


def test_browsing_needs_sign_in(api: TestClient) -> None:
    assert api.get(LISTINGS).status_code == 401


def test_a_public_listing_shows_no_private_details(
    owner: Member, student: MakePerson, db: Session, society
) -> None:
    published_property(db, owner, society)
    viewer = student("Viewer Person")

    text = viewer.client.get(LISTINGS).text

    assert owner.user.email not in text
    assert "12 Private Lane" not in text  # the society's private address
    for private in ("moderation", "storage", "object_key", "owner_contact", "reviewer"):
        assert private not in text
    count = db.scalar(select(func.count()).select_from(AccommodationListing))
    assert count == 1
    assert UserRole.ADMIN.value not in text
    assert DocumentType.OWNERSHIP_PROOF.value not in text
