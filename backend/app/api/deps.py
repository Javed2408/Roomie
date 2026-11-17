"""Checks that routes declare they need: "signed in", "an admin", and so on.

A route asks for one of these as a parameter, for example
`user: CurrentUser`. FastAPI runs the check first, and the route's own
code only runs if it passed. Because the check is part of the route's
signature, it cannot be forgotten halfway through writing the route.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import csrf_token_for, tokens_match
from app.db.session import get_db
from app.models.auth import UserSession
from app.models.enums import UserRole
from app.models.user import User
from app.services import auth as auth_service

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

Database = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@dataclass(frozen=True)
class SessionContext:
    token: str
    session: UserSession
    user: User


def verify_origin(request: Request, settings: AppSettings) -> None:
    """Refuse changes that come from a web page we do not recognise.

    Browsers attach an Origin header saying which site a request came
    from. If it names a site that is not our frontend, the request is a
    forgery attempt (CSRF) and is stopped here. Requests without the
    header (command-line tools, tests) carry no cookies a browser would
    have added for them, and are covered by the token check below.
    """
    if request.method in SAFE_METHODS:
        return
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.cors_allowed_origins:
        raise PermissionDeniedError("This request did not come from the Roomie website.")


def get_session_context(
    request: Request, db: Database, settings: AppSettings
) -> SessionContext | None:
    """Who is signed in, if anyone, according to the session cookie."""
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    found = auth_service.find_active_session(db, token, settings)
    if found is None:
        return None
    session, user = found
    return SessionContext(token=token, session=session, user=user)


def require_session(
    request: Request,
    settings: AppSettings,
    context: Annotated[SessionContext | None, Depends(get_session_context)],
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> SessionContext:
    """Require a signed-in user and, for any change, the anti-forgery token.

    The token is unique to the session and is only obtainable by reading
    an API response, which a malicious third-party site cannot do. So a
    request that carries it must have been made by our own frontend.
    """
    if context is None:
        raise AuthenticationError("Please log in to continue.")
    if request.method not in SAFE_METHODS:
        expected = csrf_token_for(context.token, settings.secret_key.get_secret_value())
        if csrf_token is None or not tokens_match(csrf_token, expected):
            raise PermissionDeniedError("Your session could not be confirmed. Please reload.")
    return context


def require_user(context: Annotated[SessionContext, Depends(require_session)]) -> User:
    return context.user


def require_admin(user: Annotated[User, Depends(require_user)]) -> User:
    if user.role != UserRole.ADMIN:
        raise PermissionDeniedError("This area is for administrators only.")
    return user


CurrentSession = Annotated[SessionContext, Depends(require_session)]
CurrentUser = Annotated[User, Depends(require_user)]
CurrentAdmin = Annotated[User, Depends(require_admin)]
