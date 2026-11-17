"""The signed-in person's own account, profile, preferences and societies.

Every route here acts on "me": the user identified by the session. None of
them accepts a user id, so there is no id to tamper with.
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, Database
from app.schemas.account import AccountOut, PreferencesIn, ProfileIn, SocietyPreferencesIn
from app.services import account as account_service

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
