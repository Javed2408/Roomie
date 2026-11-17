"""Accounts, sessions and emailed tokens.

Nothing here knows about HTTP or cookies. The routes in app/api/v1/auth.py
call these functions and deal with the cookie themselves.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AuthenticationError, BusinessRuleError, ConflictError
from app.core.security import (
    hash_password,
    hash_token,
    new_token,
    password_needs_rehash,
    password_problem,
    verify_password,
)
from app.models.auth import AccountToken, UserSession
from app.models.enums import AccountStatus, AccountTokenPurpose
from app.models.user import User

_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
# How long a session may go without `last_used_at` being rewritten. Saves
# a database write on every single request.
_TOUCH_INTERVAL = timedelta(minutes=5)

_BAD_LOGIN = "The email or password is not correct."
_BAD_TOKEN = "This link is not valid or has expired. Please request a new one."  # noqa: S105


def normalise_email(email: str) -> str:
    """Trim and lower-case, so "A@x.com " and "a@x.com" are one account."""
    cleaned = email.strip().lower()
    if len(cleaned) > 320 or not _EMAIL_PATTERN.fullmatch(cleaned):
        raise BusinessRuleError("Enter a valid email address.")
    return cleaned


def _now() -> datetime:
    return datetime.now(UTC)


# --- Registration and login --------------------------------------------


def register_user(db: Session, *, email: str, password: str, accepted_terms: bool) -> User:
    if not accepted_terms:
        raise BusinessRuleError("Please accept the terms to continue.")
    problem = password_problem(password)
    if problem:
        raise BusinessRuleError(problem)

    email = normalise_email(email)
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise ConflictError("An account with this email already exists. Try logging in instead.")

    user = User(email=email, password_hash=hash_password(password), terms_accepted_at=_now())
    db.add(user)
    db.flush()
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    """Check an email and password. The same error covers every failure,
    so the response never reveals whether the email has an account."""
    try:
        normalised = normalise_email(email)
    except BusinessRuleError:
        normalised = ""
    user = db.scalar(select(User).where(User.email == normalised)) if normalised else None

    # Always runs, even with no user, so timing does not give it away.
    if not verify_password(password, user.password_hash if user else None) or user is None:
        raise AuthenticationError(_BAD_LOGIN)

    if user.account_status == AccountStatus.SUSPENDED:
        raise AuthenticationError("This account has been suspended.")
    if user.account_status != AccountStatus.ACTIVE:
        raise AuthenticationError(_BAD_LOGIN)

    # Quietly upgrade the stored hash if the hashing settings have improved.
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = _now()
    db.flush()
    return user


# --- Sessions ----------------------------------------------------------


def create_session(
    db: Session, user: User, settings: Settings, *, user_agent: str | None = None
) -> str:
    """Start a session and return its token. Only the hash is stored."""
    token = new_token()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=_now() + timedelta(hours=settings.session_lifetime_hours),
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    db.flush()
    return token


def find_active_session(
    db: Session, token: str, settings: Settings
) -> tuple[UserSession, User] | None:
    """The session and user for a token, or None if it should not work.

    A session stops working when it is revoked, when it reaches its
    expiry, when it has been idle too long, or when the account is no
    longer active.
    """
    row = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.token_hash == hash_token(token))
    ).first()
    if row is None:
        return None
    session, user = row
    now = _now()

    if session.revoked_at is not None or session.expires_at <= now:
        return None
    if session.last_used_at <= now - timedelta(hours=settings.session_idle_hours):
        return None
    if user.account_status != AccountStatus.ACTIVE:
        return None

    if now - session.last_used_at >= _TOUCH_INTERVAL:
        session.last_used_at = now
        db.flush()
    return session, user


def revoke_session(db: Session, session: UserSession) -> None:
    session.revoked_at = _now()
    db.flush()


def revoke_all_sessions(db: Session, user: User) -> None:
    """Sign the user out everywhere, e.g. after a password reset."""
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    db.flush()


# --- Emailed tokens ----------------------------------------------------


def issue_account_token(
    db: Session, user: User, purpose: AccountTokenPurpose, *, valid_for: timedelta
) -> str:
    """Create a single-use token. Any earlier unused one stops working."""
    now = _now()
    db.execute(
        update(AccountToken)
        .where(
            AccountToken.user_id == user.id,
            AccountToken.purpose == purpose,
            AccountToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    token = new_token()
    db.add(
        AccountToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(token),
            expires_at=now + valid_for,
        )
    )
    db.flush()
    return token


def _consume_account_token(db: Session, token: str, purpose: AccountTokenPurpose) -> User:
    """Use a token up and return its user, or refuse.

    Wrong, expired, already-used and wrong-purpose tokens all get the same
    message.
    """
    now = _now()
    # FOR UPDATE: if two requests arrive with the same token at once, the
    # second waits for the first and then sees the token already used.
    record = db.scalar(
        select(AccountToken)
        .where(AccountToken.token_hash == hash_token(token), AccountToken.purpose == purpose)
        .with_for_update()
    )
    if record is None or record.used_at is not None or record.expires_at <= now:
        raise BusinessRuleError(_BAD_TOKEN)
    user = db.get(User, record.user_id)
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise BusinessRuleError(_BAD_TOKEN)
    record.used_at = now
    db.flush()
    return user


def verify_email(db: Session, token: str) -> User:
    user = _consume_account_token(db, token, AccountTokenPurpose.EMAIL_VERIFICATION)
    if user.email_verified_at is None:
        user.email_verified_at = _now()
        db.flush()
    return user


def find_user_for_password_reset(db: Session, email: str) -> User | None:
    """The active account for an email, or None. Callers must respond the
    same way in both cases."""
    try:
        normalised = normalise_email(email)
    except BusinessRuleError:
        return None
    user = db.scalar(select(User).where(User.email == normalised))
    if user is None or user.account_status != AccountStatus.ACTIVE:
        return None
    return user


def reset_password(db: Session, *, token: str, new_password: str) -> User:
    problem = password_problem(new_password)
    if problem:
        raise BusinessRuleError(problem)
    user = _consume_account_token(db, token, AccountTokenPurpose.PASSWORD_RESET)
    user.password_hash = hash_password(new_password)
    # Being able to open the emailed link also proves the address works.
    if user.email_verified_at is None:
        user.email_verified_at = _now()
    # Whoever knew the old password is signed out everywhere.
    revoke_all_sessions(db, user)
    return user
