"""The signed-in person's own account, profile, preferences and societies.

Every route here acts on "me": the user identified by the session. None of
them accepts a user id, so there is no id to tamper with.
"""

from fastapi import APIRouter, Response

from app.api.deps import CurrentUser, Database
from app.api.photos import (
    PhotoStorage,
    UploadedPhoto,
    photo_response,
    photo_upload_limit,
    save_photo,
)
from app.core.errors import NotFoundError
from app.schemas.account import AccountOut, PreferencesIn, ProfileIn, SocietyPreferencesIn
from app.services import account as account_service
from app.services.photos import (
    OUTPUT_CONTENT_TYPE,
    PROFILE_PHOTO_SIZE,
    process_photo,
    read_photo_upload,
)

router = APIRouter(prefix="/me", tags=["account"])


@router.get("", response_model=AccountOut)
def read_account(user: CurrentUser, db: Database) -> AccountOut:
    return account_service.get_account(db, user)


@router.put("/profile", response_model=AccountOut)
def save_profile(body: ProfileIn, user: CurrentUser, db: Database) -> AccountOut:
    account_service.save_profile(db, user, body)
    db.commit()
    return account_service.get_account(db, user)


@router.put("/preferences", response_model=AccountOut)
def save_preferences(body: PreferencesIn, user: CurrentUser, db: Database) -> AccountOut:
    account_service.save_preferences(db, user, body)
    db.commit()
    return account_service.get_account(db, user)


@router.put("/societies", response_model=AccountOut)
def save_societies(body: SocietyPreferencesIn, user: CurrentUser, db: Database) -> AccountOut:
    account_service.save_society_preferences(db, user, body)
    db.commit()
    return account_service.get_account(db, user)


@router.post("/profile/publish", response_model=AccountOut)
def publish_profile(user: CurrentUser, db: Database) -> AccountOut:
    """Mark the profile complete, once the required details are all present."""
    account_service.publish_profile(db, user)
    db.commit()
    return account_service.get_account(db, user)


# --- Profile photo -------------------------------------------------------------------


@router.put("/profile/photo", response_model=AccountOut, dependencies=[photo_upload_limit])
async def upload_profile_photo(
    file: UploadedPhoto, user: CurrentUser, db: Database, storage: PhotoStorage
) -> AccountOut:
    """Add or replace your photo. It is cleaned (all metadata, including
    location, removed) and cropped to a square before it is kept."""
    photo = process_photo(await read_photo_upload(file), square=PROFILE_PHOTO_SIZE)
    key = save_photo(storage, photo)
    try:
        previous = account_service.set_profile_photo(db, user, key=key)
        db.commit()
    except Exception:
        storage.delete(key)
        raise
    if previous:
        storage.delete(previous)
    return account_service.get_account(db, user)


@router.delete("/profile/photo", response_model=AccountOut)
def delete_profile_photo(user: CurrentUser, db: Database, storage: PhotoStorage) -> AccountOut:
    previous = account_service.remove_profile_photo(db, user)
    db.commit()
    if previous:
        storage.delete(previous)
    return account_service.get_account(db, user)


@router.get("/profile/photo")
def read_own_profile_photo(user: CurrentUser, storage: PhotoStorage) -> Response:
    profile = user.student_profile
    if profile is None or profile.profile_photo_key is None:
        raise NotFoundError("You have no photo.")
    return photo_response(storage.read(profile.profile_photo_key), OUTPUT_CONTENT_TYPE)
