"""Shared helpers for the listing tests: request bodies, sample photos and
taking a listing all the way through review."""

from __future__ import annotations

import io
from datetime import date, timedelta
from typing import Any

from PIL import Image
from sqlalchemy.orm import Session

from app.models import AccommodationListing, Society, User
from app.models.enums import DocumentType, ModerationStatus, TenantPermissionBasis
from app.models.enums import VerificationStatus as VS
from app.services.listing_moderation import moderate_listing
from app.services.verification import record_owner_confirmation, review_verification
from tests import factories
from tests.helpers import PDF_BYTES, Member

ME = "/api/v1/me/listings"
IN_A_MONTH = (date.today() + timedelta(days=30)).isoformat()
NEXT_YEAR = date(date.today().year + 1, 12, 31)


def property_body(society: Society, **overrides: Any) -> dict[str, Any]:
    """A valid "I have a room" listing from a property owner."""
    return {
        "listing_type": "EXISTING_ACCOMMODATION",
        "creator_type": "PROPERTY_OWNER",
        "title": "Room free in a 3BHK",
        "description": "Bright room with a balcony, shared kitchen. Ten minutes to SRM.",
        "society_id": str(society.id),
        "rent_per_person": 9000,
        "deposit": 18000,
        "brokerage_applicable": False,
        "bedroom_count": 3,
        "available_bedrooms": 1,
        "furnishing": "SEMI_FURNISHED",
        "facilities": ["WIFI", "POWER_BACKUP"],
        "available_from": IN_A_MONTH,
        "current_occupants": 2,
        "roommates_wanted": 1,
        "confirmed_authority": True,
    } | overrides


def search_body(*societies: Society, **overrides: Any) -> dict[str, Any]:
    """A valid "let's find a place together" request."""
    return {
        "listing_type": "LOOKING_TO_RENT_TOGETHER",
        "title": "Two of us looking for a 3BHK",
        "description": "Second-year students, tidy and quiet. Looking for one more.",
        "society_ids": [str(society.id) for society in societies],
        "budget_per_person": 9000,
        "desired_bedrooms": 3,
        "current_group_size": 2,
        "roommates_wanted": 1,
        "move_in_date": IN_A_MONTH,
    } | overrides


def create(member: Member, body: dict[str, Any]) -> dict[str, Any]:
    response = member.client.post(ME, json=body, headers=member.headers)
    assert response.status_code == 201, response.text
    return response.json()


def upload_evidence(
    member: Member, listing_id: str, document_type: str, **form: str
) -> dict[str, Any]:
    response = member.client.post(
        f"{ME}/{listing_id}/authority-verification",
        data={"document_type": document_type, **form},
        files={"file": ("evidence.pdf", PDF_BYTES, "application/pdf")},
        headers=member.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def submit(member: Member, listing_id: str) -> dict[str, Any]:
    response = member.client.post(f"{ME}/{listing_id}/submit", headers=member.headers)
    assert response.status_code == 200, response.text
    return response.json()


def approve_everything(
    db: Session, listing_id: str, admin: User | None = None
) -> AccommodationListing:
    """What an administrator does: approve the evidence (and, for an agent,
    record the owner's confirmation), then approve the listing."""
    admin = admin or factories.make_admin(db)
    listing = db.get(AccommodationListing, listing_id)
    assert listing is not None
    db.refresh(listing)
    authority = listing.authority_verification
    if authority is not None:
        if authority.owner_confirmation_status.value == "PENDING":
            record_owner_confirmation(
                db, authority, confirmed=True, admin=admin, note="Called the owner."
            )
        tenant = {}
        if listing.creator_type and listing.creator_type.value == "EXISTING_TENANT":
            tenant = {
                "tenant_permission_basis": TenantPermissionBasis.AGREEMENT_PERMITS_SHARING,
                "rental_agreement_valid_until": NEXT_YEAR,
            }
        review_verification(db, authority, new_status=VS.APPROVED, reviewer=admin, **tenant)
    moderate_listing(db, listing, new_status=ModerationStatus.APPROVED, actor=admin)
    db.flush()
    return listing


def published_property(
    db: Session, member: Member, society: Society, **overrides: Any
) -> dict[str, Any]:
    """An owner's property listing, created, evidenced, submitted and
    approved: publicly visible."""
    factories.approve_identity(db, member.user)
    listing = create(member, property_body(society, **overrides))
    upload_evidence(member, listing["listing"]["id"], DocumentType.OWNERSHIP_PROOF.value)
    submit(member, listing["listing"]["id"])
    approve_everything(db, listing["listing"]["id"])
    return listing["listing"]


def image_bytes(
    image_format: str = "JPEG",
    size: tuple[int, int] = (800, 600),
    *,
    exif: bytes | None = None,
    mode: str = "RGB",
) -> bytes:
    image = Image.new(mode, size, "white" if mode != "1" else 1)
    output = io.BytesIO()
    options: dict[str, Any] = {}
    if exif is not None:
        options["exif"] = exif
    image.save(output, format=image_format, **options)
    return output.getvalue()


def gps_exif() -> bytes:
    """EXIF data with a camera model and a GPS position, like a phone adds."""
    exif = Image.Exif()
    exif[0x0110] = "Secret Phone Model"  # camera model
    gps = {1: "N", 2: (12.0, 49.0, 22.0), 3: "E", 4: (80.0, 2.0, 30.0)}
    exif[0x8825] = gps  # GPS information
    return exif.tobytes()


def photo_file(data: bytes, name: str = "photo.jpg", content_type: str = "image/jpeg") -> dict:
    return {"file": (name, data, content_type)}
