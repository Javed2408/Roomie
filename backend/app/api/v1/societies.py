"""The public society directory: read-only, verified and active records only.

People choose from the directory but cannot add to it. Administrators
manage it through app/api/v1/admin_directory.py.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import Database
from app.core.errors import NotFoundError
from app.models.society import Society
from app.repositories import directory as directory_repo
from app.schemas.directory import LocalityPublicOut, SocietyDirectoryOut
from app.services.listings import public_society

router = APIRouter(tags=["directory"])


def _society_out(society: Society) -> SocietyDirectoryOut:
    # Name, area, type and description. Never the address or coordinates.
    return SocietyDirectoryOut(
        **public_society(society).model_dump(),
        community_type=society.community_type,
        description=society.description,
    )


@router.get("/localities", response_model=list[LocalityPublicOut])
def list_localities(db: Database) -> list[LocalityPublicOut]:
    """Areas students can choose from, with how many societies each has."""
    return [
        LocalityPublicOut(
            id=locality.id,
            name=locality.name,
            city=locality.city,
            description=locality.description,
            society_count=count,
        )
        for locality, count in directory_repo.find_public_localities(db)
    ]


@router.get("/societies", response_model=list[SocietyDirectoryOut])
def list_societies(
    db: Database,
    q: Annotated[str | None, Query(max_length=100, description="Name or locality")] = None,
    locality_id: Annotated[uuid.UUID | None, Query(description="Only this locality")] = None,
    limit: Annotated[int, Query(ge=1, le=directory_repo.MAX_PAGE_SIZE)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SocietyDirectoryOut]:
    """Search verified, active societies by name or locality name."""
    societies = directory_repo.find_public_societies(
        db, query=q, locality_id=locality_id, limit=limit, offset=offset
    )
    return [_society_out(society) for society in societies]


@router.get("/societies/{society_id}", response_model=SocietyDirectoryOut)
def read_society(society_id: uuid.UUID, db: Database) -> SocietyDirectoryOut:
    society = directory_repo.find_public_society(db, society_id)
    if society is None:
        # Unverified and inactive records look exactly like missing ones.
        raise NotFoundError("That society is not in the directory.")
    return _society_out(society)
