"""Manage the society directory from the command line.

Run from backend/ with the virtual environment active:

    python -m app.scripts.directory status
    python -m app.scripts.directory import
    python -m app.scripts.directory retire-samples
    python -m app.scripts.directory verify society "Lancor Abode Valley" \
        --admin you@example.com --note "Visited on 20 Nov 2026; 22 towers, active RWA."
    python -m app.scripts.directory unverify society "..." --admin ... --note "..."
    python -m app.scripts.directory activate locality "Potheri" --admin ...
    python -m app.scripts.directory deactivate society "..." --admin ... --note "..."

These do exactly what the admin API does (same rules, same history),
for people with access to the server. Verifying and (de)activating need
the email of an administrator account, which is recorded in the history.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.db.session import SessionLocal
from app.models.enums import DirectoryStatus, UserRole
from app.models.profile import UserSocietyPreference
from app.models.society import Locality, Society, normalise_name
from app.models.user import User
from app.services import directory as directory_service

DEFAULT_FILE = Path(__file__).resolve().parent / "data" / "srm_ktr_directory_candidates.json"


def _find(db: Session, kind: str, name_or_id: str) -> Locality | Society:
    model = Locality if kind == "locality" else Society
    try:
        record_id = uuid.UUID(name_or_id)
    except ValueError:
        record_id = None
    if record_id is not None:
        record = db.get(model, record_id)
    else:
        matches = db.scalars(
            select(model).where(model.name_key == normalise_name(name_or_id))
        ).all()
        if len(matches) > 1:
            raise SystemExit(f"More than one {kind} is called “{name_or_id}”. Use its id.")
        record = matches[0] if matches else None
    if record is None:
        raise SystemExit(f"No {kind} called “{name_or_id}” was found. Try: status")
    return record


def _admin(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or user.role != UserRole.ADMIN:
        raise SystemExit(
            f"“{email}” is not an administrator account. "
            "Create one with: python -m app.scripts.create_admin <email>"
        )
    return user


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def command_status(db: Session, _args: argparse.Namespace) -> None:
    localities = db.scalars(
        select(Locality).options(selectinload(Locality.societies)).order_by(Locality.name)
    ).all()
    public_societies = 0
    for locality in localities:
        print(
            f"\n{locality.name} ({locality.city}, {locality.state})  "
            f"verified={_yes_no(locality.verification_status == DirectoryStatus.VERIFIED)}  "
            f"active={_yes_no(locality.is_active)}  public={_yes_no(locality.is_listed)}"
        )
        if not locality.societies:
            print("    (no societies)")
        for society in sorted(locality.societies, key=lambda item: item.name):
            chosen = db.scalar(
                select(func.count())
                .select_from(UserSocietyPreference)
                .where(UserSocietyPreference.society_id == society.id)
            )
            is_public = society.is_listed and locality.is_listed
            public_societies += int(is_public)
            print(
                f"    - {society.name}  "
                f"type={society.community_type.value if society.community_type else 'unknown'}  "
                f"verified={_yes_no(society.verification_status == DirectoryStatus.VERIFIED)}  "
                f"active={_yes_no(society.is_active)}  public={_yes_no(is_public)}  "
                f"chosen by {chosen}"
            )
    total = sum(len(locality.societies) for locality in localities)
    print(
        f"\n{len(localities)} localities, {total} societies, "
        f"{public_societies} societies visible to students."
    )


def command_import(db: Session, args: argparse.Namespace) -> None:
    path = Path(args.file)
    data = json.loads(path.read_text(encoding="utf-8"))
    report = directory_service.import_candidates(db, data, source_name=path.name)
    db.commit()
    print(f"Localities added: {len(report.localities_created)}  {report.localities_created}")
    print(f"Localities already present: {report.localities_existing}")
    print(f"Societies added: {len(report.societies_created)}  {report.societies_created}")
    print(f"Societies already present: {report.societies_existing}")
    print("Everything added is UNVERIFIED and hidden from students until verified.")


def command_retire_samples(db: Session, _args: argparse.Namespace) -> None:
    report = directory_service.retire_sample_societies(db)
    db.commit()
    print(f"Deleted (nobody had chosen them): {report.deleted or 'none'}")
    if report.deactivated:
        print("Kept but switched off, because people still have them in their choices:")
        for name, count in report.deactivated.items():
            print(f"    - {name}: chosen by {count}")
    else:
        print("Nothing needed switching off.")


def command_verify(db: Session, args: argparse.Namespace) -> None:
    record = _find(db, args.kind, args.name)
    directory_service.verify(db, record, actor=_admin(db, args.admin), note=args.note)
    db.commit()
    print(f"Verified: {record.name}")


def command_unverify(db: Session, args: argparse.Namespace) -> None:
    record = _find(db, args.kind, args.name)
    directory_service.unverify(db, record, actor=_admin(db, args.admin), note=args.note)
    db.commit()
    print(f"No longer verified: {record.name}")


def command_set_active(db: Session, args: argparse.Namespace) -> None:
    record = _find(db, args.kind, args.name)
    active = args.command == "activate"
    directory_service.set_active(db, record, active, actor=_admin(db, args.admin), note=args.note)
    db.commit()
    print(f"{'Activated' if active else 'Deactivated'}: {record.name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.scripts.directory")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("status", help="List every locality and society and its state")

    importer = commands.add_parser("import", help="Add the candidate records, unverified")
    importer.add_argument("--file", default=str(DEFAULT_FILE))

    commands.add_parser("retire-samples", help="Remove the old development sample societies")

    for name, needs_note in (
        ("verify", True),
        ("unverify", True),
        ("activate", False),
        ("deactivate", False),
    ):
        sub = commands.add_parser(name)
        sub.add_argument("kind", choices=["locality", "society"])
        sub.add_argument("name", help="The record's name, or its id")
        sub.add_argument("--admin", required=True, help="Email of the administrator doing this")
        sub.add_argument("--note", required=needs_note, help="How it was confirmed, or why")
    return parser


HANDLERS = {
    "status": command_status,
    "import": command_import,
    "retire-samples": command_retire_samples,
    "verify": command_verify,
    "unverify": command_unverify,
    "activate": command_set_active,
    "deactivate": command_set_active,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with SessionLocal() as db:
        try:
            HANDLERS[args.command](db, args)
        except AppError as error:
            db.rollback()
            print(f"Not done: {error.message}")
            if error.details:
                print(f"Details: {error.details}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
