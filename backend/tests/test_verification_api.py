"""Tests for submitting verification evidence, private document access and
the administrator review endpoints."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AccommodationListing, User, VerificationDocument
from app.models.enums import (
    ListingCreatorType,
    ListingLifecycleStatus,
    ModerationStatus,
)
from app.repositories.listings import find_public_listings
from app.services.listing_moderation import moderate_listing
from app.services.storage import LocalPrivateStorage
from tests import factories
from tests.helpers import (
    JPEG_BYTES,
    PDF_BYTES,
    PNG_BYTES,
    log_in,
    make_admin_account,
    pdf_upload,
    sign_up,
)

pytestmark = pytest.mark.integration

IDENTITY = "/api/v1/me/verifications/identity"
STUDENT = "/api/v1/me/verifications/student"


def user_for(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


def own_listing(db: Session, email: str, creator_type: ListingCreatorType) -> AccommodationListing:
    return factories.make_property_listing(db, owner=user_for(db, email), creator_type=creator_type)


def authority_url(listing: AccommodationListing) -> str:
    return f"/api/v1/me/listings/{listing.id}/authority-verification"


# --- Submitting ---------------------------------------------------------


def test_submitting_identity_evidence_waits_for_review(api: TestClient) -> None:
    headers = sign_up(api)

    response = api.post(IDENTITY, files=pdf_upload("passport.pdf"), headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"  # never approved automatically
    [document] = body["documents"]
    assert document["document_type"] == "GOVERNMENT_ID"
    assert document["original_filename"] == "passport.pdf"
    assert document["content_type"] == "application/pdf"


def test_identity_and_student_are_submitted_and_tracked_separately(api: TestClient) -> None:
    headers = sign_up(api)

    api.post(IDENTITY, files=pdf_upload(), headers=headers)
    after_identity = api.get("/api/v1/me/verifications").json()
    assert after_identity["identity"]["status"] == "PENDING"
    assert after_identity["student"]["status"] == "NOT_SUBMITTED"

    api.post(
        STUDENT,
        files=pdf_upload("id-card.pdf"),
        data={"institution_name": "SRM IST", "document_type": "STUDENT_ID"},
        headers=headers,
    )
    after_both = api.get("/api/v1/me/verifications").json()
    assert after_both["student"]["status"] == "PENDING"
    assert len(after_both["identity"]["documents"]) == 1
    assert len(after_both["student"]["documents"]) == 1


def test_each_verification_only_accepts_its_own_kinds_of_document(
    api: TestClient, db: Session
) -> None:
    headers = sign_up(api, "owner@example.com")
    listing = own_listing(db, "owner@example.com", ListingCreatorType.PROPERTY_OWNER)

    rental_as_identity = api.post(
        IDENTITY, files=pdf_upload(), data={"document_type": "RENTAL_AGREEMENT"}, headers=headers
    )
    passport_as_student = api.post(
        STUDENT,
        files=pdf_upload(),
        data={"institution_name": "SRM", "document_type": "GOVERNMENT_ID"},
        headers=headers,
    )
    student_id_as_authority = api.post(
        authority_url(listing),
        files=pdf_upload(),
        data={"document_type": "STUDENT_ID"},
        headers=headers,
    )

    assert rental_as_identity.status_code == 422
    assert passport_as_student.status_code == 422
    assert student_id_as_authority.status_code == 422
    assert db.scalar(select(VerificationDocument)) is None


def test_student_verification_needs_an_institution(api: TestClient) -> None:
    headers = sign_up(api)

    response = api.post(
        STUDENT, files=pdf_upload(), data={"institution_name": "   "}, headers=headers
    )

    assert response.status_code == 422


# --- File checks --------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "detected"),
    [(PDF_BYTES, "application/pdf"), (PNG_BYTES, "image/png"), (JPEG_BYTES, "image/jpeg")],
)
def test_pdf_and_images_are_accepted_by_their_real_content(
    api: TestClient, data: bytes, detected: str
) -> None:
    headers = sign_up(api)

    # The name and claimed type are deliberately misleading.
    response = api.post(IDENTITY, files={"file": ("x.txt", data, "text/plain")}, headers=headers)

    assert response.status_code == 201
    assert response.json()["documents"][0]["content_type"] == detected


@pytest.mark.parametrize(
    "data",
    [
        b"MZ\x90\x00 this is a Windows program",
        b"<html><script>alert(1)</script></html>",
        b"just some text",
        b"",
    ],
)
def test_other_files_are_refused_whatever_they_claim_to_be(
    api: TestClient, db: Session, data: bytes
) -> None:
    headers = sign_up(api)

    response = api.post(
        IDENTITY, files={"file": ("passport.pdf", data, "application/pdf")}, headers=headers
    )

    assert response.status_code == 422
    assert db.scalar(select(VerificationDocument)) is None


def test_a_file_over_the_size_limit_is_refused(api: TestClient, db: Session) -> None:
    headers = sign_up(api)
    too_big = PDF_BYTES + b"0" * get_settings().max_upload_bytes

    response = api.post(IDENTITY, files=pdf_upload(data=too_big), headers=headers)

    assert response.status_code == 422
    assert "too large" in response.json()["error"]["message"]
    assert db.scalar(select(VerificationDocument)) is None


def test_a_dangerous_filename_is_never_used_as_a_path(
    api: TestClient, db: Session, storage: LocalPrivateStorage
) -> None:
    headers = sign_up(api)

    response = api.post(
        IDENTITY, files=pdf_upload("..\\..\\..\\windows\\evil.pdf"), headers=headers
    )

    assert response.json()["documents"][0]["original_filename"] == "evil.pdf"
    document = db.scalar(select(VerificationDocument))
    assert document is not None
    # Stored under a random key, unrelated to anything the user supplied.
    assert "evil" not in document.storage_key
    assert storage.read(document.storage_key) == PDF_BYTES


# --- Private access -----------------------------------------------------


def test_responses_never_reveal_where_a_document_is_stored(api: TestClient, db: Session) -> None:
    headers = sign_up(api)
    submitted = api.post(IDENTITY, files=pdf_upload(), headers=headers)

    document = db.scalar(select(VerificationDocument))
    assert document is not None
    for text in (
        submitted.text,
        api.get("/api/v1/me").text,
        api.get("/api/v1/me/verifications").text,
    ):
        assert document.storage_key not in text
        assert "storage_key" not in text
        assert "sha256" not in text


def test_only_the_uploader_and_admins_can_download_a_document(
    api: TestClient, new_client: Callable[[], TestClient], db: Session
) -> None:
    headers = sign_up(api, "owner@example.com")
    document_id = api.post(IDENTITY, files=pdf_upload(), headers=headers).json()["documents"][0][
        "id"
    ]
    url = f"/api/v1/verification-documents/{document_id}/content"

    # The uploader can.
    mine = api.get(url)
    assert mine.status_code == 200
    assert mine.content == PDF_BYTES
    assert mine.headers["content-disposition"].startswith("attachment")
    assert mine.headers["x-content-type-options"] == "nosniff"
    assert mine.headers["cache-control"] == "no-store"

    # A visitor cannot.
    assert new_client().get(url).status_code == 401

    # Another signed-in member cannot, and is not even told it exists.
    stranger = new_client()
    sign_up(stranger, "stranger@example.com")
    refused = stranger.get(url)
    assert refused.status_code == 404
    assert PDF_BYTES not in refused.content

    # An administrator can.
    make_admin_account(db)
    admin = new_client()
    log_in(admin, "admin@example.com")
    assert admin.get(url).content == PDF_BYTES


def test_an_unknown_document_gets_the_same_answer_as_a_forbidden_one(
    api: TestClient, new_client: Callable[[], TestClient]
) -> None:
    headers = sign_up(api, "owner@example.com")
    real_id = api.post(IDENTITY, files=pdf_upload(), headers=headers).json()["documents"][0]["id"]
    stranger = new_client()
    sign_up(stranger, "stranger@example.com")

    forbidden = stranger.get(f"/api/v1/verification-documents/{real_id}/content")
    missing = stranger.get(
        "/api/v1/verification-documents/00000000-0000-0000-0000-000000000000/content"
    )

    assert forbidden.status_code == missing.status_code == 404
    assert forbidden.json() == missing.json()


# --- Listing authority --------------------------------------------------


def test_someone_elses_listing_looks_like_it_does_not_exist(
    api: TestClient, new_client: Callable[[], TestClient], db: Session
) -> None:
    sign_up(api, "owner@example.com")
    listing = own_listing(db, "owner@example.com", ListingCreatorType.PROPERTY_OWNER)
    intruder = new_client()
    intruder_headers = sign_up(intruder, "intruder@example.com")

    read = intruder.get(authority_url(listing))
    write = intruder.post(
        authority_url(listing),
        files=pdf_upload(),
        data={"document_type": "OWNERSHIP_PROOF"},
        headers=intruder_headers,
    )

    assert read.status_code == write.status_code == 404
    assert db.scalar(select(VerificationDocument)) is None


def test_a_search_request_cannot_have_listing_authority(api: TestClient, db: Session) -> None:
    headers = sign_up(api, "student@example.com")
    search = factories.make_search_listing(db, owner=user_for(db, "student@example.com"))

    response = api.post(
        authority_url(search),
        files=pdf_upload(),
        data={"document_type": "OWNERSHIP_PROOF"},
        headers=headers,
    )

    assert response.status_code == 422


def test_an_agent_must_name_the_owner(api: TestClient, db: Session) -> None:
    headers = sign_up(api, "agent@example.com")
    listing = own_listing(db, "agent@example.com", ListingCreatorType.AUTHORIZED_AGENT)
    form = {"document_type": "OWNER_AUTHORIZATION"}

    without_owner = api.post(authority_url(listing), files=pdf_upload(), data=form, headers=headers)
    with_owner = api.post(
        authority_url(listing),
        files=pdf_upload(),
        data=form | {"owner_name": "Mr Owner", "owner_contact": "+91 90000 00000"},
        headers=headers,
    )

    assert without_owner.status_code == 422
    assert with_owner.status_code == 201
    # The owner's details are stored for the admin but never sent back.
    assert "Mr Owner" not in with_owner.text
    assert "90000" not in with_owner.text


# --- Administrator review -----------------------------------------------


def test_members_cannot_use_admin_endpoints(api: TestClient) -> None:
    headers = sign_up(api)
    verification_id = "00000000-0000-0000-0000-000000000000"

    listing = api.get("/api/v1/admin/verifications", params={"kind": "identity"})
    review = api.post(
        f"/api/v1/admin/verifications/identity/{verification_id}/review",
        json={"status": "APPROVED"},
        headers=headers,
    )

    assert listing.status_code == review.status_code == 403


def test_a_member_cannot_approve_their_own_verification(api: TestClient, db: Session) -> None:
    headers = sign_up(api, "student@example.com")
    api.post(IDENTITY, files=pdf_upload(), headers=headers)
    verification = user_for(db, "student@example.com").identity_verification
    assert verification is not None

    response = api.post(
        f"/api/v1/admin/verifications/identity/{verification.id}/review",
        json={"status": "APPROVED"},
        headers=headers,
    )

    assert response.status_code == 403
    assert api.get("/api/v1/me/verifications").json()["identity"]["status"] == "PENDING"


def test_admin_reviews_identity_and_the_member_sees_the_outcome(
    api: TestClient, new_client: Callable[[], TestClient], db: Session
) -> None:
    headers = sign_up(api, "student@example.com")
    api.post(IDENTITY, files=pdf_upload(), headers=headers)
    make_admin_account(db)
    admin = new_client()
    admin_headers = log_in(admin, "admin@example.com")

    [queued] = admin.get("/api/v1/admin/verifications", params={"kind": "identity"}).json()
    assert queued["applicant_email"] == "student@example.com"
    # The student queue is a different queue, and it is empty.
    assert admin.get("/api/v1/admin/verifications", params={"kind": "student"}).json() == []

    review_url = f"/api/v1/admin/verifications/identity/{queued['id']}/review"
    needs_reason = admin.post(review_url, json={"status": "REJECTED"}, headers=admin_headers)
    assert needs_reason.status_code == 422

    rejected = admin.post(
        review_url,
        json={"status": "NEEDS_RESUBMISSION", "note": "Internal: photo looks edited"},
        headers=admin_headers,
    )
    assert rejected.status_code == 200

    # The member sees the status, but not the reviewer's internal note.
    mine = api.get("/api/v1/me/verifications")
    assert mine.json()["identity"]["status"] == "NEEDS_RESUBMISSION"
    assert "photo looks edited" not in mine.text

    # Resubmitting puts it back in the queue; it is not approved by itself.
    again = api.post(IDENTITY, files=pdf_upload("clearer.pdf"), headers=headers)
    assert again.json()["status"] == "PENDING"
    assert len(again.json()["documents"]) == 2

    approved = admin.post(review_url, json={"status": "APPROVED"}, headers=admin_headers)
    assert approved.status_code == 200
    assert api.get("/api/v1/me/verifications").json()["identity"]["status"] == "APPROVED"
    # Student verification was never touched.
    assert api.get("/api/v1/me/verifications").json()["student"]["status"] == "NOT_SUBMITTED"

    # Nothing more can be submitted once approved.
    assert api.post(IDENTITY, files=pdf_upload(), headers=headers).status_code == 409


def test_an_agents_listing_goes_public_only_after_every_check(
    api: TestClient, new_client: Callable[[], TestClient], db: Session
) -> None:
    """The full path for an authorised agent, through the API."""
    headers = sign_up(api, "agent@example.com")
    listing = own_listing(db, "agent@example.com", ListingCreatorType.AUTHORIZED_AGENT)
    listing.lifecycle_status = ListingLifecycleStatus.ACTIVE
    db.flush()
    admin_user = make_admin_account(db)
    admin = new_client()
    admin_headers = log_in(admin, "admin@example.com")

    api.post(
        authority_url(listing),
        files=pdf_upload("authorisation.pdf"),
        data={
            "document_type": "OWNER_AUTHORIZATION",
            "owner_name": "Mr Owner",
            "owner_contact": "+91 90000 00000",
        },
        headers=headers,
    )
    [queued] = admin.get("/api/v1/admin/verifications", params={"kind": "listing-authority"}).json()
    base = f"/api/v1/admin/verifications/listing-authority/{queued['id']}"

    detail = admin.get(base).json()
    assert detail["owner_contact"] == "+91 90000 00000"  # admins do see this
    assert detail["outstanding_requirements"] == [
        "The agent's identity has not been verified.",
        "The owner has not independently confirmed the authorisation.",
    ]

    # Approving too early is refused, and says why.
    early = admin.post(f"{base}/review", json={"status": "APPROVED"}, headers=admin_headers)
    assert early.status_code == 422
    assert len(early.json()["error"]["details"]) == 2

    # 1. The agent's identity is verified (a separate check).
    api.post("/api/v1/me/verifications/identity", files=pdf_upload(), headers=headers)
    [identity] = admin.get("/api/v1/admin/verifications", params={"kind": "identity"}).json()
    admin.post(
        f"/api/v1/admin/verifications/identity/{identity['id']}/review",
        json={"status": "APPROVED"},
        headers=admin_headers,
    )
    # 2. An administrator confirms directly with the owner.
    confirmed = admin.post(
        f"{base}/owner-confirmation",
        json={"confirmed": True, "note": "Called the number on the title deed."},
        headers=admin_headers,
    )
    assert confirmed.json()["outstanding_requirements"] == []

    # 3. Now listing authority can be approved...
    assert (
        admin.post(f"{base}/review", json={"status": "APPROVED"}, headers=admin_headers).status_code
        == 200
    )
    # ...and it is STILL not public until the listing itself is moderated.
    assert find_public_listings(db)[0] == []

    db.refresh(listing)
    moderate_listing(db, listing, new_status=ModerationStatus.APPROVED, actor=admin_user)
    assert [item.id for item in find_public_listings(db)[0]] == [listing.id]
