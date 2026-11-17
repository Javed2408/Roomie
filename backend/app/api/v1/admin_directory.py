"""Administrator endpoints for managing the society directory.

Every route requires an administrator. Changes go through
app/services/directory.py, which enforces the duplicate rules and writes
the change history. The admin screens for this arrive with the admin
dashboard (roadmap Phase 8); until then, use these endpoints or the
command-line tool (python -m app.scripts.directory).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import CurrentAdmin, Database
from app.core.errors import NotFoundError
from app.models.enums import DirectoryStatus
from app.models.profile import UserSocietyPreference
from app.models.society import DirectoryEvent, Locality, Society
from app.models.user import User
from app.schemas.directory import (
    DirectoryActionIn,
    DirectoryEventOut,
    LocalityAdminDetail,
    LocalityAdminOut,
    LocalityCreateIn,
    LocalityUpdateIn,
    SocietyAdminDetail,
    SocietyAdminOut,
    SocietyCreateIn,
    SocietyUpdateIn,
)
from app.services import directory as directory_service

router = APIRouter(prefix="/admin/directory", tags=["admin: directory"])


# --- Building responses -------------------------------------------------


def _email(db: Session, user_id: uuid.UUID | None) -> str | None:
    if user_id is None:
        return None
    user = db.get(User, user_id)
    return user.email if user else None


def _locality_out(db: Session, locality: Locality) -> LocalityAdminOut:
    society_count = db.scalar(
        select(func.count()).select_from(Society).where(Society.locality_id == locality.id)
    )
    return LocalityAdminOut(
        id=locality.id,
        name=locality.name,
        city=locality.city,
        state=locality.state,
        postal_code=locality.postal_code,
        description=locality.description,
        is_active=locality.is_active,
        verification_status=locality.verification_status,
        verified_at=locality.verified_at,
        verified_by_email=_email(db, locality.verified_by),
        source_note=locality.source_note,
        is_public=locality.is_listed,
        created_at=locality.created_at,
        updated_at=locality.updated_at,
        society_count=int(society_count or 0),
    )


def _society_out(db: Session, society: Society) -> SocietyAdminOut:
    chosen_by = db.scalar(
        select(func.count())
        .select_from(UserSocietyPreference)
        .where(UserSocietyPreference.society_id == society.id)
    )
    return SocietyAdminOut(
        id=society.id,
        name=society.name,
        locality_id=society.locality_id,
        locality_name=society.locality.name,
        community_type=society.community_type,
        address=society.address,
        latitude=society.latitude,
        longitude=society.longitude,
        description=society.description,
        is_active=society.is_active,
        verification_status=society.verification_status,
        verified_at=society.verified_at,
        verified_by_email=_email(db, society.verified_by),
        source_note=society.source_note,
        is_public=society.is_listed and society.locality.is_listed,
        created_at=society.created_at,
        updated_at=society.updated_at,
        chosen_by_count=int(chosen_by or 0),
    )


def _history(
    db: Session, *, locality_id: uuid.UUID | None = None, society_id: uuid.UUID | None = None
) -> list[DirectoryEventOut]:
    statement = select(DirectoryEvent).options(selectinload(DirectoryEvent.actor))
    if locality_id is not None:
        statement = statement.where(DirectoryEvent.locality_id == locality_id)
    else:
        statement = statement.where(DirectoryEvent.society_id == society_id)
    events = db.scalars(statement.order_by(DirectoryEvent.sequence))
    return [
        DirectoryEventOut(
            action=event.action,
            actor_email=event.actor.email if event.actor else None,
            changes=event.changes,
            note=event.note,
            created_at=event.created_at,
        )
        for event in events
    ]


def _locality_detail(db: Session, locality: Locality) -> LocalityAdminDetail:
    return LocalityAdminDetail(
        **_locality_out(db, locality).model_dump(),
        history=_history(db, locality_id=locality.id),
    )


def _society_detail(db: Session, society: Society) -> SocietyAdminDetail:
    return SocietyAdminDetail(
        **_society_out(db, society).model_dump(),
        history=_history(db, society_id=society.id),
    )


def _load_locality(db: Session, locality_id: uuid.UUID) -> Locality:
    locality = db.get(Locality, locality_id)
    if locality is None:
        raise NotFoundError("That locality does not exist.")
    return locality


def _load_society(db: Session, society_id: uuid.UUID) -> Society:
    society = db.get(Society, society_id)
    if society is None:
        raise NotFoundError("That society does not exist.")
    return society


# --- Localities ---------------------------------------------------------


@router.get("/localities", response_model=list[LocalityAdminOut])
def list_localities(_admin: CurrentAdmin, db: Database) -> list[LocalityAdminOut]:
    """Every locality, including unverified and inactive ones."""
    localities = db.scalars(select(Locality).order_by(Locality.name))
    return [_locality_out(db, locality) for locality in localities]


@router.post("/localities", response_model=LocalityAdminDetail, status_code=status.HTTP_201_CREATED)
def create_locality(
    body: LocalityCreateIn, admin: CurrentAdmin, db: Database
) -> LocalityAdminDetail:
    locality = directory_service.create_locality(
        db,
        directory_service.LocalityFields(**body.model_dump(exclude={"note"})),
        actor=admin,
        note=body.note,
    )
    db.commit()
    return _locality_detail(db, locality)


@router.get("/localities/{locality_id}", response_model=LocalityAdminDetail)
def read_locality(
    locality_id: uuid.UUID, _admin: CurrentAdmin, db: Database
) -> LocalityAdminDetail:
    return _locality_detail(db, _load_locality(db, locality_id))


@router.patch("/localities/{locality_id}", response_model=LocalityAdminDetail)
def update_locality(
    locality_id: uuid.UUID, body: LocalityUpdateIn, admin: CurrentAdmin, db: Database
) -> LocalityAdminDetail:
    """Change only the fields sent. Changing the name, city or state of a
    verified locality makes it unverified again."""
    locality = _load_locality(db, locality_id)
    updates = body.model_dump(exclude_unset=True, exclude={"note"})
    directory_service.update_locality(db, locality, updates, actor=admin, note=body.note)
    db.commit()
    return _locality_detail(db, locality)


# --- Societies ----------------------------------------------------------


@router.get("/societies", response_model=list[SocietyAdminOut])
def list_societies(
    _admin: CurrentAdmin,
    db: Database,
    q: Annotated[str | None, Query(max_length=100)] = None,
    locality_id: uuid.UUID | None = None,
    verification_status: DirectoryStatus | None = None,
    is_active: bool | None = None,
) -> list[SocietyAdminOut]:
    """Every society, including unverified and inactive ones, with filters."""
    statement = select(Society).options(selectinload(Society.locality)).order_by(Society.name)
    if q and q.strip():
        statement = statement.where(Society.name.icontains(q.strip(), autoescape=True))
    if locality_id is not None:
        statement = statement.where(Society.locality_id == locality_id)
    if verification_status is not None:
        statement = statement.where(Society.verification_status == verification_status)
    if is_active is not None:
        statement = statement.where(Society.is_active.is_(is_active))
    return [_society_out(db, society) for society in db.scalars(statement)]


@router.post("/societies", response_model=SocietyAdminDetail, status_code=status.HTTP_201_CREATED)
def create_society(body: SocietyCreateIn, admin: CurrentAdmin, db: Database) -> SocietyAdminDetail:
    society = directory_service.create_society(
        db,
        directory_service.SocietyFields(**body.model_dump(exclude={"note"})),
        actor=admin,
        note=body.note,
    )
    db.commit()
    return _society_detail(db, society)


@router.get("/societies/{society_id}", response_model=SocietyAdminDetail)
def read_society(society_id: uuid.UUID, _admin: CurrentAdmin, db: Database) -> SocietyAdminDetail:
    return _society_detail(db, _load_society(db, society_id))


@router.patch("/societies/{society_id}", response_model=SocietyAdminDetail)
def update_society(
    society_id: uuid.UUID, body: SocietyUpdateIn, admin: CurrentAdmin, db: Database
) -> SocietyAdminDetail:
    """Change only the fields sent. Changing the name, locality, type or
    address of a verified society makes it unverified again."""
    society = _load_society(db, society_id)
    updates = body.model_dump(exclude_unset=True, exclude={"note"})
    directory_service.update_society(db, society, updates, actor=admin, note=body.note)
    db.commit()
    return _society_detail(db, society)


# --- Verify, unverify, activate, deactivate (both kinds) ------------------


def _record(db: Session, kind: str, record_id: uuid.UUID) -> Locality | Society:
    return _load_locality(db, record_id) if kind == "localities" else _load_society(db, record_id)


def _detail(db: Session, record: Locality | Society) -> LocalityAdminDetail | SocietyAdminDetail:
    if isinstance(record, Locality):
        return _locality_detail(db, record)
    return _society_detail(db, record)


@router.post(
    "/{kind}/{record_id}/verify",
    response_model=LocalityAdminDetail | SocietyAdminDetail,
)
def verify(
    kind: str, record_id: uuid.UUID, body: DirectoryActionIn, admin: CurrentAdmin, db: Database
) -> LocalityAdminDetail | SocietyAdminDetail:
    """Confirm a record is accurate. The note must say how it was confirmed."""
    record = _record(db, _check_kind(kind), record_id)
    directory_service.verify(db, record, actor=admin, note=body.note)
    db.commit()
    return _detail(db, record)


@router.post(
    "/{kind}/{record_id}/unverify",
    response_model=LocalityAdminDetail | SocietyAdminDetail,
)
def unverify(
    kind: str, record_id: uuid.UUID, body: DirectoryActionIn, admin: CurrentAdmin, db: Database
) -> LocalityAdminDetail | SocietyAdminDetail:
    record = _record(db, _check_kind(kind), record_id)
    directory_service.unverify(db, record, actor=admin, note=body.note)
    db.commit()
    return _detail(db, record)


@router.post(
    "/{kind}/{record_id}/activate",
    response_model=LocalityAdminDetail | SocietyAdminDetail,
)
def activate(
    kind: str, record_id: uuid.UUID, body: DirectoryActionIn, admin: CurrentAdmin, db: Database
) -> LocalityAdminDetail | SocietyAdminDetail:
    record = _record(db, _check_kind(kind), record_id)
    directory_service.set_active(db, record, True, actor=admin, note=body.note)
    db.commit()
    return _detail(db, record)


@router.post(
    "/{kind}/{record_id}/deactivate",
    response_model=LocalityAdminDetail | SocietyAdminDetail,
)
def deactivate(
    kind: str, record_id: uuid.UUID, body: DirectoryActionIn, admin: CurrentAdmin, db: Database
) -> LocalityAdminDetail | SocietyAdminDetail:
    """Hide a record from students. It and everyone's saved choices are kept."""
    record = _record(db, _check_kind(kind), record_id)
    directory_service.set_active(db, record, False, actor=admin, note=body.note)
    db.commit()
    return _detail(db, record)


def _check_kind(kind: str) -> str:
    if kind not in {"localities", "societies"}:
        raise NotFoundError("Not found.")
    return kind
