"""Small helpers shared by the API tests."""

from __future__ import annotations

import itertools
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from tests import factories

PASSWORD = "roomie2027"
_member_numbers = itertools.count(1)

# The smallest files that still begin like the real thing.
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32


def csrf(session_body: dict) -> dict[str, str]:
    """The header a browser must send with every change."""
    return {"X-CSRF-Token": session_body["csrf_token"]}


def sign_up(client: TestClient, email: str = "student@example.com") -> dict[str, str]:
    """Register (which also signs in) and return the CSRF header."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "accepted_terms": True},
    )
    assert response.status_code == 201, response.text
    return csrf(response.json())


def log_in(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return csrf(response.json())


@lru_cache
def password_hash() -> str:
    """One real hash of PASSWORD, shared by every test account (hashing is
    deliberately slow, so doing it once keeps the tests quick)."""
    return hash_password(PASSWORD)


@dataclass
class Member:
    """A discoverable student, signed in through their own browser."""

    user: User
    client: TestClient
    headers: dict[str, str]

    @property
    def id(self) -> str:
        return str(self.user.id)


def signed_in_member(
    new_client: Callable[[], TestClient],
    db: Session,
    full_name: str = "Priya Sharma",
    **options: Any,
) -> Member:
    """Create a member (see factories.make_member) and log them in."""
    number = next(_member_numbers)
    user = factories.make_member(
        db,
        full_name,
        email=f"member{number}@example.com",
        password_hash=password_hash(),
        **options,
    )
    client = new_client()
    return Member(user=user, client=client, headers=log_in(client, user.email))


def signed_in_user(
    new_client: Callable[[], TestClient],
    db: Session,
    *,
    email_verified: bool = True,
    role: UserRole = UserRole.MEMBER,
) -> Member:
    """Someone with an account but NO student profile, e.g. a property owner
    or an agent, logged in through their own browser."""
    number = next(_member_numbers)
    user = factories.make_user(
        db,
        email=f"owner{number}@example.com",
        password_hash=password_hash(),
        role=role,
        email_verified_at=datetime.now(UTC) if email_verified else None,
    )
    client = new_client()
    return Member(user=user, client=client, headers=log_in(client, user.email))


def make_admin_account(db: Session, email: str = "admin@example.com") -> User:
    """An administrator who can really log in (has a genuine password hash)."""
    return factories.make_user(
        db, email=email, password_hash=hash_password(PASSWORD), role=UserRole.ADMIN
    )


def token_in(body: str) -> str:
    """Pull the secret token out of an emailed link."""
    match = re.search(r"token=([\w-]+)", body)
    assert match, f"No token found in: {body}"
    return match.group(1)


def pdf_upload(name: str = "document.pdf", data: bytes = PDF_BYTES) -> dict:
    return {"file": (name, data, "application/pdf")}
