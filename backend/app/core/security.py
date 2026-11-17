"""Passwords and secret tokens.

Two rules run through this file:

1. A password is never stored. Only an Argon2 hash is, which cannot be
   turned back into the password.
2. A secret token (a session, an email link) is never stored either. The
   database keeps only its SHA-256 hash, so someone who read the database
   could not use what they found to sign in as anyone.
"""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Argon2id with the library's recommended settings. It is deliberately
# slow and memory-hungry, which makes guessing passwords in bulk expensive.
_hasher = PasswordHasher()

# Checked when someone logs in with an email that has no account, so that
# request takes as long as a real one. Otherwise the response time would
# reveal which email addresses are registered.
_DUMMY_HASH = _hasher.hash("not-a-real-password")

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """True if the password matches. Pass `None` when there is no account."""
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and bool(password_hash)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True if the hash was made with older settings than today's."""
    return _hasher.check_needs_rehash(password_hash)


def password_problem(password: str) -> str | None:
    """Say what is wrong with a new password, or None if it is acceptable.

    Mirrors the rules shown in the frontend (frontend/lib/validation.ts).
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Use at least {PASSWORD_MIN_LENGTH} characters."
    if len(password) > PASSWORD_MAX_LENGTH:
        return f"Use {PASSWORD_MAX_LENGTH} characters or fewer."
    if not any(character.isalpha() for character in password) or not any(
        character.isdigit() for character in password
    ):
        return "Add a letter and a number."
    return None


def new_token() -> str:
    """A long, unguessable random string, safe to put in a link or cookie."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """What is stored in the database in place of the token itself."""
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token_for(session_token: str, secret_key: str) -> str:
    """The anti-forgery token that belongs to one session.

    It is derived from the session token and the server's secret key, so
    nothing extra needs storing, and only someone who can read the API's
    responses (the real frontend) can obtain it.
    """
    return hmac.new(secret_key.encode(), session_token.encode(), hashlib.sha256).hexdigest()


def tokens_match(first: str, second: str) -> bool:
    """Compare in constant time, so timing cannot leak the right answer."""
    return hmac.compare_digest(first.encode(), second.encode())
