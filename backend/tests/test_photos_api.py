"""Tests for profile and listing photos: what is accepted, what is removed
from them, and who may see them."""

import io
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AccommodationListing, Block, ListingImage
from app.models.enums import ModerationStatus
from app.services.listing_moderation import moderate_listing
from app.services.storage import LocalPrivateStorage
from tests import factories
from tests.helpers import PDF_BYTES, Member, signed_in_member, signed_in_user
from tests.listing_helpers import (
    ME,
    create,
    gps_exif,
    image_bytes,
    photo_file,
    property_body,
    published_property,
)

pytestmark = pytest.mark.integration

PROFILE_PHOTO = "/api/v1/me/profile/photo"
MakePerson = Callable[..., Member]


@pytest.fixture
def owner(new_client: Callable[[], TestClient], db: Session) -> Member:
    return signed_in_user(new_client, db)


@pytest.fixture
def student(new_client: Callable[[], TestClient], db: Session) -> MakePerson:
    def make(full_name: str = "Priya Sharma", **options: Any) -> Member:
        return signed_in_member(new_client, db, full_name, **options)

    return make


@pytest.fixture
def society(db: Session):  # noqa: ANN201 - a fixture
    return factories.make_society(db, "Lancor Abode Valley")


def add_photo(member: Member, listing_id: str, data: bytes, **file: Any) -> Any:
    return member.client.post(
        f"{ME}/{listing_id}/photos", files=photo_file(data, **file), headers=member.headers
    )


def fetch(member: Member, url: str) -> Any:
    return member.client.get(url)


# --- What is accepted -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("image_format", "content_type"),
    [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")],
)
def test_jpeg_png_and_webp_are_accepted_and_kept_as_jpeg(
    owner: Member, society, image_format: str, content_type: str
) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]

    response = add_photo(owner, listing_id, image_bytes(image_format), content_type=content_type)

    assert response.status_code == 201, response.text
    [photo] = response.json()["listing"]["photos"]
    served = fetch(owner, photo["url"])
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/jpeg"
    assert served.headers["x-content-type-options"] == "nosniff"
    assert served.content.startswith(b"\xff\xd8\xff")
    assert (photo["width"], photo["height"]) == (800, 600)


@pytest.mark.parametrize(
    ("data", "name"),
    [
        (b"#!/bin/sh\nrm -rf /\n", "photo.jpg"),  # a script pretending to be a photo
        (b"MZ\x90\x00" + b"\x00" * 64, "photo.png"),  # a Windows program
        (PDF_BYTES, "photo.jpg"),
        (b"\xff\xd8\xff\xe0" + b"\x00" * 40, "broken.jpg"),  # starts like a JPEG, is not one
        (b"GIF89a" + b"\x00" * 40, "animation.gif"),
    ],
)
def test_files_that_are_not_real_images_are_refused(
    owner: Member, society, data: bytes, name: str
) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]

    response = add_photo(owner, listing_id, data, name=name)

    assert response.status_code == 422
    assert owner.client.get(f"{ME}/{listing_id}").json()["listing"]["photos"] == []


def test_an_oversized_photo_is_refused(
    owner: Member, society, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "max_photo_bytes", 2000)
    listing_id = create(owner, property_body(society))["listing"]["id"]

    response = add_photo(owner, listing_id, image_bytes("PNG", (400, 400)) + b"\x00" * 3000)

    assert response.status_code == 422
    assert "too large" in response.json()["error"]["message"]


def test_a_decompression_bomb_is_refused(owner: Member, society) -> None:
    # A tiny file that would expand to 48 million pixels in memory.
    bomb = image_bytes("PNG", (8000, 6000), mode="1")
    listing_id = create(owner, property_body(society))["listing"]["id"]

    response = add_photo(owner, listing_id, bomb, name="bomb.png", content_type="image/png")

    assert len(bomb) < 100_000
    assert response.status_code == 422


def test_large_photos_are_shrunk(owner: Member, society) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]

    [photo] = add_photo(owner, listing_id, image_bytes("JPEG", (4000, 3000))).json()["listing"][
        "photos"
    ]

    assert (photo["width"], photo["height"]) == (1600, 1200)


# --- What is removed --------------------------------------------------------------------------


def test_location_and_camera_metadata_are_removed(
    owner: Member, society, photo_storage: LocalPrivateStorage, db: Session
) -> None:
    original = image_bytes("JPEG", exif=gps_exif())
    assert Image.open(io.BytesIO(original)).getexif().get_ifd(0x8825)  # it has GPS
    listing_id = create(owner, property_body(society))["listing"]["id"]

    [photo] = add_photo(owner, listing_id, original).json()["listing"]["photos"]
    image = db.get(ListingImage, photo["id"])
    assert image is not None
    stored = photo_storage.read(image.object_key)
    served = fetch(owner, photo["url"]).content

    for data in (stored, served):
        cleaned = Image.open(io.BytesIO(data))
        assert dict(cleaned.getexif()) == {}
        assert b"Exif" not in data
        assert b"Secret Phone Model" not in data


def test_responses_never_reveal_where_a_photo_is_stored(
    owner: Member, society, db: Session
) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]

    response = add_photo(owner, listing_id, image_bytes(), name="../../etc/passwd.jpg")
    [photo] = response.json()["listing"]["photos"]
    image = db.get(ListingImage, photo["id"])

    assert response.status_code == 201
    assert image is not None
    assert image.object_key not in response.text
    assert "passwd" not in response.text
    assert "photo-storage" not in response.text


# --- Who may see listing photos -------------------------------------------------------------------


def test_a_draft_listings_photos_are_private(
    owner: Member, student: MakePerson, society, new_client: Callable[[], TestClient]
) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]
    [photo] = add_photo(owner, listing_id, image_bytes()).json()["listing"]["photos"]

    assert fetch(owner, photo["url"]).status_code == 200
    assert fetch(student("Curious Person"), photo["url"]).status_code == 404
    assert new_client().get(photo["url"]).status_code == 401


def test_a_public_listings_photos_follow_its_visibility(
    owner: Member, student: MakePerson, society, db: Session
) -> None:
    listing = published_property(db, owner, society)
    viewer = student("Viewer Person")
    blocked = student("Blocked Person")
    db.add(Block(blocker_id=owner.user.id, blocked_user_id=blocked.user.id))
    db.flush()

    response = add_photo(owner, listing["id"], image_bytes())
    [photo] = response.json()["listing"]["photos"]
    # Adding a photo sent the listing back for review: hidden for now.
    assert response.json()["moderation_status"] == "PENDING"
    assert fetch(viewer, photo["url"]).status_code == 404

    record = db.get(AccommodationListing, listing["id"])
    assert record is not None
    moderate_listing(
        db, record, new_status=ModerationStatus.APPROVED, actor=factories.make_admin(db)
    )
    assert fetch(viewer, photo["url"]).status_code == 200
    assert fetch(blocked, photo["url"]).status_code == 404


def test_photos_can_be_removed_and_are_deleted_from_storage(
    owner: Member, society, photo_storage: LocalPrivateStorage, db: Session
) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]
    [photo] = add_photo(owner, listing_id, image_bytes()).json()["listing"]["photos"]
    image = db.get(ListingImage, photo["id"])
    assert image is not None
    key = image.object_key

    response = owner.client.delete(f"{ME}/{listing_id}/photos/{photo['id']}", headers=owner.headers)

    assert response.status_code == 200
    assert response.json()["listing"]["photos"] == []
    with pytest.raises(Exception, match="no longer available"):
        photo_storage.read(key)


def test_a_listing_has_a_photo_limit(
    owner: Member, society, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "max_listing_photos", 2)
    listing_id = create(owner, property_body(society))["listing"]["id"]
    for _ in range(2):
        assert add_photo(owner, listing_id, image_bytes()).status_code == 201

    third = add_photo(owner, listing_id, image_bytes())

    assert third.status_code == 422
    assert "at most 2 photos" in third.json()["error"]["message"]


def test_nobody_can_add_photos_to_someone_elses_listing(
    owner: Member, student: MakePerson, society
) -> None:
    listing_id = create(owner, property_body(society))["listing"]["id"]
    intruder = student("Intruder Person")

    assert add_photo(intruder, listing_id, image_bytes()).status_code == 404


# --- Profile photos ---------------------------------------------------------------------------------


def upload_profile_photo(member: Member, data: bytes) -> Any:
    return member.client.put(PROFILE_PHOTO, files=photo_file(data), headers=member.headers)


def test_a_profile_photo_is_cropped_square_and_can_be_replaced_and_removed(
    student: MakePerson, photo_storage: LocalPrivateStorage, db: Session
) -> None:
    member = student("Asha Kumar")

    first = upload_profile_photo(member, image_bytes("JPEG", (1200, 800), exif=gps_exif()))
    assert first.status_code == 200
    first_url = first.json()["profile"]["photo_url"]
    served = Image.open(io.BytesIO(member.client.get(first_url).content))
    assert served.size == (512, 512)
    assert dict(served.getexif()) == {}
    db.refresh(member.user)
    first_key = member.user.student_profile.profile_photo_key  # type: ignore[union-attr]

    second = upload_profile_photo(member, image_bytes("PNG"))
    second_url = second.json()["profile"]["photo_url"]
    assert second_url != first_url  # a new address, so no stale copy shows
    with pytest.raises(Exception, match="no longer available"):
        photo_storage.read(first_key)  # the old file is gone

    removed = member.client.delete(PROFILE_PHOTO, headers=member.headers)
    assert removed.json()["profile"]["photo_url"] is None
    assert member.client.get(PROFILE_PHOTO).status_code == 404


def test_a_profile_photo_needs_a_profile(owner: Member) -> None:
    assert upload_profile_photo(owner, image_bytes()).status_code == 422


def test_profile_photos_follow_profile_visibility(student: MakePerson, db: Session) -> None:
    asha = student("Asha Kumar")
    url = upload_profile_photo(asha, image_bytes()).json()["profile"]["photo_url"]
    student_url = url.replace("/me/profile/photo", f"/students/{asha.id}/photo")
    viewer = student("Viewer Person")
    unpublished = student("Draft Person", published=False)
    blocked = student("Blocked Person")
    db.add(Block(blocker_id=asha.user.id, blocked_user_id=blocked.user.id))
    db.flush()

    # Shown wherever the profile is: on Discover cards...
    cards = viewer.client.get("/api/v1/discovery").json()["items"]
    card = next(item["student"] for item in cards if item["student"]["id"] == asha.id)
    assert card["photo_url"] == student_url
    assert viewer.client.get(student_url).status_code == 200
    # ...and to nobody who cannot see the profile.
    assert unpublished.client.get(student_url).status_code == 404
    assert blocked.client.get(student_url).status_code == 404


def test_profile_photos_and_documents_are_kept_apart(
    student: MakePerson,
    photo_storage: LocalPrivateStorage,
    storage: LocalPrivateStorage,
    db: Session,
) -> None:
    member = student("Asha Kumar")
    upload_profile_photo(member, image_bytes())
    db.refresh(member.user)
    key = member.user.student_profile.profile_photo_key  # type: ignore[union-attr]

    assert photo_storage.read(key)
    with pytest.raises(Exception, match="no longer available"):
        storage.read(key)
