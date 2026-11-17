"""Administering the society directory.

Every change goes through this module, whether it comes from the admin API
or from the command-line tool, so the same rules always apply:

* Duplicates are refused, including spelling variants that differ only in
  case, spacing or punctuation.
* Every change is written to the history (`directory_events`), with who
  made it.
* Records start UNVERIFIED. Only an administrator can verify one, and must
  say how it was confirmed.
* Changing a verified record's core facts (its name, area or type) makes it
  unverified again, because the new facts have not been confirmed.

Nothing here commits; the caller does.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError, PermissionDeniedError
from app.models.enums import CommunityType, DirectoryAction, DirectoryStatus, UserRole
from app.models.listing import AccommodationListing, ListingSocietyPreference
from app.models.profile import UserSocietyPreference
from app.models.society import DirectoryEvent, Locality, Society, normalise_name
from app.models.user import User

# Changing any of these on a verified record makes it unverified again.
_LOCALITY_CORE_FIELDS = {"name", "city", "state"}
_SOCIETY_CORE_FIELDS = {"name", "locality_id", "community_type", "address"}

DirectoryRecord = Locality | Society


def _now() -> datetime:
    return datetime.now(UTC)


def require_admin(actor: User) -> None:
    if actor.role != UserRole.ADMIN:
        raise PermissionDeniedError("Only an administrator can change the society directory.")


def _json_safe(value: Any) -> Any:
    """Make a value storable in the JSON history column."""
    if isinstance(value, uuid.UUID | Decimal):
        return str(value)
    if hasattr(value, "value"):  # an enum member
        return value.value
    return value


def _record_event(
    db: Session,
    record: DirectoryRecord,
    action: DirectoryAction,
    *,
    actor: User | None,
    changes: dict[str, dict[str, Any]] | None = None,
    note: str | None = None,
) -> None:
    db.add(
        DirectoryEvent(
            locality_id=record.id if isinstance(record, Locality) else None,
            society_id=record.id if isinstance(record, Society) else None,
            actor_id=actor.id if actor else None,
            action=action,
            changes=changes,
            note=note,
        )
    )


def _clean(value: str | None) -> str | None:
    """Trim; an empty string means "not provided"."""
    if value is None:
        return None
    value = value.strip()
    return value or None


# --- Duplicate checks ---------------------------------------------------


def _check_locality_unique(
    db: Session, name: str, city: str, state: str, *, ignore_id: uuid.UUID | None = None
) -> None:
    key = normalise_name(name)
    if not key:
        raise BusinessRuleError("A locality name must contain letters or numbers.")
    statement = select(Locality).where(
        Locality.name_key == key,
        func.lower(Locality.city) == city.strip().lower(),
        func.lower(Locality.state) == state.strip().lower(),
    )
    if ignore_id is not None:
        statement = statement.where(Locality.id != ignore_id)
    existing = db.scalar(statement)
    if existing is not None:
        raise ConflictError(
            f"The locality “{existing.name}” is already in the directory.",
            details={"existing_id": str(existing.id)},
        )


def _check_society_unique(db: Session, name: str, *, ignore_id: uuid.UUID | None = None) -> None:
    key = normalise_name(name)
    if not key:
        raise BusinessRuleError("A society name must contain letters or numbers.")
    statement = select(Society).where(Society.name_key == key)
    if ignore_id is not None:
        statement = statement.where(Society.id != ignore_id)
    existing = db.scalar(statement)
    if existing is not None:
        raise ConflictError(
            f"The society “{existing.name}” is already in the directory, "
            f"in {existing.locality.name}.",
            details={"existing_id": str(existing.id)},
        )


def _require_locality(db: Session, locality_id: uuid.UUID) -> Locality:
    locality = db.get(Locality, locality_id)
    if locality is None:
        raise NotFoundError("That locality does not exist.")
    return locality


# --- Creating -----------------------------------------------------------


@dataclass
class LocalityFields:
    name: str
    city: str
    state: str
    postal_code: str | None = None
    description: str | None = None
    source_note: str | None = None


@dataclass
class SocietyFields:
    locality_id: uuid.UUID
    name: str
    community_type: CommunityType | None = None
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    description: str | None = None
    source_note: str | None = None


def create_locality(
    db: Session, fields: LocalityFields, *, actor: User | None, note: str | None = None
) -> Locality:
    """Add a locality. It starts unverified, so it is not public yet."""
    if actor is not None:
        require_admin(actor)
    name, city, state = fields.name.strip(), fields.city.strip(), fields.state.strip()
    _check_locality_unique(db, name, city, state)
    locality = Locality(
        name=name,
        city=city,
        state=state,
        postal_code=_clean(fields.postal_code),
        description=_clean(fields.description),
        source_note=_clean(fields.source_note),
    )
    db.add(locality)
    db.flush()
    _record_event(db, locality, DirectoryAction.CREATED, actor=actor, note=note)
    db.flush()
    return locality


def create_society(
    db: Session, fields: SocietyFields, *, actor: User | None, note: str | None = None
) -> Society:
    """Add a society to a locality. It starts unverified, so it is not public yet."""
    if actor is not None:
        require_admin(actor)
    _require_locality(db, fields.locality_id)
    name = fields.name.strip()
    _check_society_unique(db, name)
    society = Society(
        locality_id=fields.locality_id,
        name=name,
        community_type=fields.community_type,
        address=_clean(fields.address),
        latitude=fields.latitude,
        longitude=fields.longitude,
        description=_clean(fields.description),
        source_note=_clean(fields.source_note),
    )
    db.add(society)
    db.flush()
    _record_event(db, society, DirectoryAction.CREATED, actor=actor, note=note)
    db.flush()
    return society


# --- Editing ------------------------------------------------------------


def _apply_changes(record: DirectoryRecord, updates: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Set the given fields, returning {field: {from, to}} for real changes."""
    changes: dict[str, dict[str, Any]] = {}
    for name, new_value in updates.items():
        if isinstance(new_value, str) and name not in {"name", "city", "state"}:
            new_value = _clean(new_value)
        elif isinstance(new_value, str):
            new_value = new_value.strip()
        old_value = getattr(record, name)
        if old_value != new_value:
            changes[name] = {"from": _json_safe(old_value), "to": _json_safe(new_value)}
            setattr(record, name, new_value)
    return changes


def _reset_verification_if_needed(
    record: DirectoryRecord, changes: dict[str, dict[str, Any]], core_fields: set[str]
) -> None:
    if record.verification_status != DirectoryStatus.VERIFIED:
        return
    if not core_fields.intersection(changes):
        return
    changes["verification_status"] = {
        "from": DirectoryStatus.VERIFIED.value,
        "to": DirectoryStatus.UNVERIFIED.value,
    }
    record.verification_status = DirectoryStatus.UNVERIFIED
    record.verified_at = None
    record.verified_by = None


def update_locality(
    db: Session, locality: Locality, updates: dict[str, Any], *, actor: User, note: str | None
) -> Locality:
    require_admin(actor)
    if not updates:
        return locality
    if {"name", "city", "state"} & set(updates):
        _check_locality_unique(
            db,
            updates.get("name", locality.name),
            updates.get("city", locality.city),
            updates.get("state", locality.state),
            ignore_id=locality.id,
        )
    changes = _apply_changes(locality, updates)
    if changes:
        _reset_verification_if_needed(locality, changes, _LOCALITY_CORE_FIELDS)
        _record_event(
            db, locality, DirectoryAction.UPDATED, actor=actor, changes=changes, note=note
        )
        db.flush()
    return locality


def update_society(
    db: Session, society: Society, updates: dict[str, Any], *, actor: User, note: str | None
) -> Society:
    require_admin(actor)
    if not updates:
        return society
    if "locality_id" in updates:
        _require_locality(db, updates["locality_id"])
    if "name" in updates:
        _check_society_unique(db, updates["name"], ignore_id=society.id)
    changes = _apply_changes(society, updates)
    if changes:
        _reset_verification_if_needed(society, changes, _SOCIETY_CORE_FIELDS)
        _record_event(db, society, DirectoryAction.UPDATED, actor=actor, changes=changes, note=note)
        db.flush()
        db.refresh(society)  # reload the locality if it changed
    return society


# --- Verifying and activating -------------------------------------------


def _require_note(note: str | None, message: str) -> str:
    cleaned = _clean(note)
    if cleaned is None:
        raise BusinessRuleError(message)
    return cleaned


def verify(db: Session, record: DirectoryRecord, *, actor: User, note: str | None) -> None:
    """Mark a record as confirmed accurate. The note says how it was confirmed."""
    require_admin(actor)
    note = _require_note(note, "Say how this was confirmed, e.g. who visited and when.")
    if record.verification_status == DirectoryStatus.VERIFIED:
        raise ConflictError("This record is already verified.")
    if isinstance(record, Society) and record.community_type is None:
        raise BusinessRuleError(
            "Set the community type (apartment complex or villa community) before verifying."
        )
    record.verification_status = DirectoryStatus.VERIFIED
    record.verified_at = _now()
    record.verified_by = actor.id
    _record_event(db, record, DirectoryAction.VERIFIED, actor=actor, note=note)
    db.flush()


def unverify(db: Session, record: DirectoryRecord, *, actor: User, note: str | None) -> None:
    """Withdraw a verification, e.g. after finding the details were wrong."""
    require_admin(actor)
    note = _require_note(note, "Say why this record is no longer verified.")
    if record.verification_status == DirectoryStatus.UNVERIFIED:
        raise ConflictError("This record is not verified.")
    record.verification_status = DirectoryStatus.UNVERIFIED
    record.verified_at = None
    record.verified_by = None
    _record_event(db, record, DirectoryAction.UNVERIFIED, actor=actor, note=note)
    db.flush()


def set_active(
    db: Session, record: DirectoryRecord, active: bool, *, actor: User | None, note: str | None
) -> None:
    """Switch a record on or off. An inactive record is never shown publicly.

    Deactivating keeps the record and everyone's saved choices; it can be
    switched on again later.
    """
    if actor is not None:
        require_admin(actor)
    if record.is_active == active:
        raise ConflictError(f"This record is already {'active' if active else 'inactive'}.")
    record.is_active = active
    action = DirectoryAction.ACTIVATED if active else DirectoryAction.DEACTIVATED
    _record_event(db, record, action, actor=actor, note=_clean(note))
    db.flush()


# --- Importing candidate records ----------------------------------------


@dataclass
class ImportReport:
    localities_created: list[str] = field(default_factory=list)
    localities_existing: list[str] = field(default_factory=list)
    societies_created: list[str] = field(default_factory=list)
    societies_existing: list[str] = field(default_factory=list)


def _sources_text(entry: dict[str, Any]) -> str | None:
    lines: list[str] = []
    for source in entry.get("sources", []):
        lines.append(f"- {source}")
    if entry.get("notes"):
        lines.append(f"Notes: {entry['notes']}")
    return "\n".join(lines) or None


def import_candidates(db: Session, data: dict[str, Any], *, source_name: str) -> ImportReport:
    """Add the candidate localities and societies in `data`, unverified.

    Safe to run any number of times. A record that already exists (by the
    duplicate rules) is never overwritten, so an administrator's edits and
    verifications are kept. The one exception: an existing locality with
    no source note at all gets the file's sources, and that is recorded in
    its history.
    """
    report = ImportReport()
    note = f"Imported as an unverified candidate from {source_name}."
    accessed = data.get("sources_accessed")
    localities: dict[str, Locality] = {}

    for entry in data.get("localities", []):
        key = normalise_name(entry["name"])
        existing = db.scalar(
            select(Locality).where(
                Locality.name_key == key,
                Locality.city == entry["city"],
                Locality.state == entry["state"],
            )
        )
        if existing is not None:
            report.localities_existing.append(existing.name)
            sources = _sources_text(entry)
            if existing.source_note is None and sources is not None:
                existing.source_note = sources
                _record_event(
                    db,
                    existing,
                    DirectoryAction.UPDATED,
                    actor=None,
                    changes={"source_note": {"from": None, "to": sources}},
                    note=f"Sources added from {source_name}.",
                )
            localities[key] = existing
            continue
        locality = create_locality(
            db,
            LocalityFields(
                name=entry["name"],
                city=entry["city"],
                state=entry["state"],
                postal_code=entry.get("postal_code"),
                description=entry.get("description"),
                source_note=_sources_text(entry),
            ),
            actor=None,
            note=note,
        )
        localities[key] = locality
        report.localities_created.append(locality.name)

    for entry in data.get("societies", []):
        existing_society = db.scalar(
            select(Society).where(Society.name_key == normalise_name(entry["name"]))
        )
        if existing_society is not None:
            report.societies_existing.append(existing_society.name)
            continue
        locality = localities.get(normalise_name(entry["locality"]))
        if locality is None:
            raise BusinessRuleError(
                f"“{entry['name']}” names the locality “{entry['locality']}”, "
                "which is not in the import file."
            )
        source_note = _sources_text(entry)
        if accessed and source_note:
            source_note += f"\nSources accessed: {accessed}."
        society = create_society(
            db,
            SocietyFields(
                locality_id=locality.id,
                name=entry["name"],
                community_type=(
                    CommunityType(entry["community_type"]) if entry.get("community_type") else None
                ),
                description=entry.get("description"),
                source_note=source_note,
            ),
            actor=None,
            note=note,
        )
        report.societies_created.append(society.name)

    db.flush()
    return report


# --- Retiring the Phase 3 development samples ----------------------------

# Exactly what the old development seed wrote. Real records never match.
SAMPLE_DESCRIPTION = "Sample entry for development. Not a real property."
SAMPLE_NAME_SUFFIX = " (sample)"


@dataclass
class RetireReport:
    deleted: list[str] = field(default_factory=list)
    # Society name -> how many people still have it among their choices.
    deactivated: dict[str, int] = field(default_factory=dict)


def retire_sample_societies(db: Session) -> RetireReport:
    """Remove the invented sample societies added during development.

    * A sample that nobody has chosen and no listing uses is deleted.
    * A sample that is still referenced is NOT deleted, so nobody's saved
      choices are lost. It is deactivated instead: it disappears from the
      directory, and the people who chose it see it marked "no longer
      available" and can pick a real society.

    Safe to run more than once.
    """
    report = RetireReport()
    samples = db.scalars(
        select(Society).where(
            Society.description == SAMPLE_DESCRIPTION,
            Society.name.endswith(SAMPLE_NAME_SUFFIX),
        )
    ).all()
    for society in samples:
        chosen_by = db.scalar(
            select(func.count())
            .select_from(UserSocietyPreference)
            .where(UserSocietyPreference.society_id == society.id)
        )
        used_by_listing = db.scalar(
            select(
                exists().where(AccommodationListing.society_id == society.id)
                | exists().where(ListingSocietyPreference.society_id == society.id)
            )
        )
        if not chosen_by and not used_by_listing:
            report.deleted.append(society.name)
            db.delete(society)
        else:
            report.deactivated[society.name] = int(chosen_by or 0)
            if society.is_active:
                set_active(
                    db,
                    society,
                    False,
                    actor=None,
                    note="Development sample retired. Kept because it is still referenced.",
                )
    db.flush()
    return report
