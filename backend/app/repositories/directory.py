"""Database queries for the society directory.

The public rule lives here, in one place: a society is shown only when it
AND its locality are both verified and active. Every query that serves
students goes through `public_societies_query`.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, contains_eager

from app.models.society import Locality, Society

MAX_PAGE_SIZE = 100


def public_societies_query() -> Select[tuple[Society]]:
    """Every society students may see, with its locality loaded."""
    return (
        select(Society)
        .join(Society.locality)
        .options(contains_eager(Society.locality))
        .where(Society.is_listed, Locality.is_listed)
    )


def find_public_societies(
    db: Session,
    *,
    query: str | None = None,
    locality_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Society]:
    """Search the public directory by society name or locality name."""
    statement = public_societies_query()
    if locality_id is not None:
        statement = statement.where(Society.locality_id == locality_id)
    if query and query.strip():
        # autoescape stops "%" or "_" typed by a person acting as wildcards.
        term = query.strip()
        statement = statement.where(
            or_(
                Society.name.icontains(term, autoescape=True),
                Locality.name.icontains(term, autoescape=True),
            )
        )
    statement = (
        statement.order_by(Locality.name, Society.name)
        .limit(min(max(limit, 1), MAX_PAGE_SIZE))
        .offset(max(offset, 0))
    )
    return list(db.scalars(statement))


def find_public_society(db: Session, society_id: uuid.UUID) -> Society | None:
    return db.scalar(public_societies_query().where(Society.id == society_id))


def public_society_ids(db: Session, society_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Which of these ids are societies students may currently choose."""
    if not society_ids:
        return set()
    statement = (
        select(Society.id)
        .join(Society.locality)
        .where(Society.id.in_(society_ids), Society.is_listed, Locality.is_listed)
    )
    return set(db.scalars(statement))


def find_public_localities(db: Session) -> list[tuple[Locality, int]]:
    """Every public locality, with how many public societies it has."""
    counts = (
        select(Society.locality_id, func.count(Society.id).label("society_count"))
        .where(Society.is_listed)
        .group_by(Society.locality_id)
        .subquery()
    )
    statement = (
        select(Locality, func.coalesce(counts.c.society_count, 0))
        .outerjoin(counts, counts.c.locality_id == Locality.id)
        .where(Locality.is_listed)
        .order_by(Locality.name)
    )
    return [(locality, int(count)) for locality, count in db.execute(statement).all()]
