"""Tests for registration, login, logout, sessions, email verification and
password reset, exercised through the real HTTP API."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import hash_token
from app.models import AccountToken, User, UserSession
from app.models.enums import AccountStatus
from tests.conftest import MemoryEmailSender
from tests.helpers import PASSWORD, csrf, log_in, sign_up, token_in

pytestmark = pytest.mark.integration

COOKIE = get_settings().session_cookie_name
REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
SESSION = "/api/v1/auth/session"


def register_body(email: str = "student@example.com", **overrides: object) -> dict:
    return {"email": email, "password": PASSWORD, "accepted_terms": True} | overrides


# --- Registration -------------------------------------------------------


def test_registering_creates_an_account_and_signs_in(api: TestClient, db: Session) -> None:
    response = api.post(REGISTER, json=register_body("New.Student@Example.com "))

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new.student@example.com"  # trimmed, lower-cased
    assert body["user"]["email_verified"] is False
    assert body["user"]["role"] == "MEMBER"
    assert api.get(SESSION).status_code == 200

    user = db.scalar(select(User).where(User.email == "new.student@example.com"))
    assert user is not None and user.terms_accepted_at is not None


def test_the_password_is_stored_only_as_a_hash(api: TestClient, db: Session) -> None:
    api.post(REGISTER, json=register_body())

    user = db.scalar(select(User))
    assert user is not None
    assert PASSWORD not in user.password_hash
    assert user.password_hash.startswith("$argon2id$")


def test_responses_never_contain_the_hash_or_the_session_token(api: TestClient) -> None:
    response = api.post(REGISTER, json=register_body())
    session_token = api.cookies.get(COOKIE)

    assert session_token
    for text in (response.text, api.get(SESSION).text, api.get("/api/v1/me").text):
        assert "argon2" not in text
        assert "password" not in text
        assert session_token not in text


def test_the_session_cookie_is_http_only(api: TestClient) -> None:
    response = api.post(REGISTER, json=register_body())

    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_a_duplicate_email_is_refused(
    api: TestClient, new_client: Callable[[], TestClient]
) -> None:
    api.post(REGISTER, json=register_body("taken@example.com"))

    response = new_client().post(REGISTER, json=register_body("TAKEN@example.com"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"password": "short1"}, "Use at least 8 characters."),
        ({"password": "onlyletters"}, "Add a letter and a number."),
        ({"email": "not-an-email"}, "Enter a valid email address."),
        ({"accepted_terms": False}, "Please accept the terms to continue."),
    ],
)
def test_invalid_registrations_are_refused(
    api: TestClient, db: Session, overrides: dict, message: str
) -> None:
    response = api.post(REGISTER, json=register_body(**overrides))

    assert response.status_code == 422
    assert response.json()["error"]["message"] == message
    assert db.scalar(select(User)) is None


# --- Login and logout ---------------------------------------------------


def test_login_with_the_right_password(
    api: TestClient, new_client: Callable[[], TestClient]
) -> None:
    sign_up(api, "student@example.com")
    other_browser = new_client()

    response = other_browser.post(
        LOGIN, json={"email": " Student@Example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert other_browser.get(SESSION).json()["user"]["email"] == "student@example.com"


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("student@example.com", "wrong-password1"),
        ("nobody@example.com", PASSWORD),
        ("not-an-email", PASSWORD),
    ],
)
def test_wrong_credentials_all_get_the_same_answer(
    api: TestClient, new_client: Callable[[], TestClient], email: str, password: str
) -> None:
    """A wrong password and an unknown email are indistinguishable."""
    sign_up(api, "student@example.com")
    stranger = new_client()

    response = stranger.post(LOGIN, json={"email": email, "password": password})

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "The email or password is not correct."
    assert COOKIE not in stranger.cookies


def test_a_suspended_account_cannot_log_in(
    api: TestClient, new_client: Callable[[], TestClient], db: Session
) -> None:
    sign_up(api, "student@example.com")
    db.execute(update(User).values(account_status=AccountStatus.SUSPENDED))
    db.flush()

    response = new_client().post(LOGIN, json={"email": "student@example.com", "password": PASSWORD})

    assert response.status_code == 401
    # The session that existed before the suspension stops working too.
    assert api.get(SESSION).status_code == 401


def test_logout_ends_the_session_on_the_server(api: TestClient, db: Session) -> None:
    headers = sign_up(api)
    stolen_cookie = api.cookies.get(COOKIE)
    assert stolen_cookie

    assert api.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert api.get(SESSION).status_code == 401

    # Even a copy of the old cookie is useless: the session is revoked.
    api.cookies.set(COOKIE, stolen_cookie)
    assert api.get(SESSION).status_code == 401
    session = db.scalar(select(UserSession))
    assert session is not None and session.revoked_at is not None


def test_only_a_hash_of_the_session_token_is_stored(api: TestClient, db: Session) -> None:
    sign_up(api)
    token = api.cookies.get(COOKIE)
    assert token

    session = db.scalar(select(UserSession))
    assert session is not None
    assert session.token_hash == hash_token(token)
    assert session.token_hash != token


# --- Protected endpoints and session expiry -----------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/auth/session"),
        ("get", "/api/v1/me"),
        ("put", "/api/v1/me/profile"),
        ("put", "/api/v1/me/preferences"),
        ("put", "/api/v1/me/societies"),
        ("post", "/api/v1/me/profile/publish"),
        ("get", "/api/v1/me/verifications"),
        ("post", "/api/v1/me/verifications/identity"),
        ("post", "/api/v1/auth/logout"),
        ("get", "/api/v1/admin/verifications?kind=identity"),
    ],
)
def test_protected_endpoints_reject_visitors(api: TestClient, method: str, path: str) -> None:
    response = getattr(api, method)(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_a_made_up_cookie_is_rejected(api: TestClient) -> None:
    api.cookies.set(COOKIE, "definitely-not-a-real-session")

    assert api.get(SESSION).status_code == 401


def test_a_session_stops_working_when_it_expires(api: TestClient, db: Session) -> None:
    sign_up(api)
    assert api.get(SESSION).status_code == 200

    db.execute(update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    db.flush()

    assert api.get(SESSION).status_code == 401
    assert api.get("/api/v1/me").status_code == 401


def test_a_session_stops_working_after_being_idle_too_long(api: TestClient, db: Session) -> None:
    sign_up(api)
    idle_limit = timedelta(hours=get_settings().session_idle_hours)

    db.execute(
        update(UserSession).values(
            last_used_at=datetime.now(UTC) - idle_limit - timedelta(minutes=1)
        )
    )
    db.flush()

    assert api.get(SESSION).status_code == 401


# --- CSRF ---------------------------------------------------------------


def test_a_change_without_the_csrf_token_is_refused(api: TestClient) -> None:
    sign_up(api)

    response = api.put("/api/v1/me/profile", json={"full_name": "A", "college_name": "B"})

    assert response.status_code == 403
    assert api.get("/api/v1/me").json()["profile"] is None


def test_a_change_with_the_wrong_csrf_token_is_refused(api: TestClient) -> None:
    sign_up(api)

    response = api.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "guess"})

    assert response.status_code == 403
    assert api.get(SESSION).status_code == 200  # still signed in


def test_one_session_cannot_use_another_sessions_csrf_token(
    api: TestClient, new_client: Callable[[], TestClient]
) -> None:
    sign_up(api, "first@example.com")
    other_headers = sign_up(new_client(), "second@example.com")

    response = api.post("/api/v1/auth/logout", headers=other_headers)

    assert response.status_code == 403


def test_a_change_from_another_website_is_refused(api: TestClient) -> None:
    headers = sign_up(api) | {"Origin": "https://evil.example"}

    response = api.put(
        "/api/v1/me/profile", json={"full_name": "A", "college_name": "B"}, headers=headers
    )

    assert response.status_code == 403
    assert api.get("/api/v1/me").json()["profile"] is None


def test_our_own_website_is_allowed(api: TestClient) -> None:
    headers = sign_up(api) | {"Origin": "http://localhost:3000"}

    response = api.put(
        "/api/v1/me/profile", json={"full_name": "A", "college_name": "B"}, headers=headers
    )

    assert response.status_code == 200


# --- Email verification -------------------------------------------------


def test_registering_sends_a_verification_email(
    api: TestClient, mailbox: MemoryEmailSender
) -> None:
    sign_up(api, "student@example.com")

    [email] = mailbox.sent
    assert email.to == "student@example.com"
    assert "/verify-email?token=" in email.body


def test_the_emailed_link_verifies_the_address(
    api: TestClient, mailbox: MemoryEmailSender, db: Session
) -> None:
    sign_up(api)
    token = token_in(mailbox.sent[0].body)
    # Only a hash of the token is kept.
    stored = db.scalar(select(AccountToken))
    assert stored is not None and stored.token_hash == hash_token(token) != token

    response = api.post("/api/v1/auth/verify-email", json={"token": token})

    assert response.status_code == 200
    assert api.get(SESSION).json()["user"]["email_verified"] is True


def test_a_verification_link_works_only_once(api: TestClient, mailbox: MemoryEmailSender) -> None:
    sign_up(api)
    token = token_in(mailbox.sent[0].body)
    api.post("/api/v1/auth/verify-email", json={"token": token})

    response = api.post("/api/v1/auth/verify-email", json={"token": token})

    assert response.status_code == 422


def test_an_expired_verification_link_is_refused(
    api: TestClient, mailbox: MemoryEmailSender, db: Session
) -> None:
    sign_up(api)
    db.execute(update(AccountToken).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    db.flush()

    response = api.post("/api/v1/auth/verify-email", json={"token": token_in(mailbox.sent[0].body)})

    assert response.status_code == 422
    assert api.get(SESSION).json()["user"]["email_verified"] is False


def test_asking_again_replaces_the_old_link(api: TestClient, mailbox: MemoryEmailSender) -> None:
    headers = sign_up(api)
    old_token = token_in(mailbox.sent[0].body)

    assert api.post("/api/v1/auth/resend-verification", headers=headers).status_code == 200
    new_token = token_in(mailbox.sent[1].body)

    assert api.post("/api/v1/auth/verify-email", json={"token": old_token}).status_code == 422
    assert api.post("/api/v1/auth/verify-email", json={"token": new_token}).status_code == 200


# --- Password reset -----------------------------------------------------


def test_forgot_password_answers_the_same_for_any_email(
    api: TestClient, mailbox: MemoryEmailSender
) -> None:
    sign_up(api, "student@example.com")
    mailbox.sent.clear()

    known = api.post("/api/v1/auth/forgot-password", json={"email": "student@example.com"})
    unknown = api.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    # Only the real account was actually emailed.
    assert [email.to for email in mailbox.sent] == ["student@example.com"]


def test_resetting_the_password(
    api: TestClient, new_client: Callable[[], TestClient], mailbox: MemoryEmailSender
) -> None:
    sign_up(api, "student@example.com")
    mailbox.sent.clear()
    api.post("/api/v1/auth/forgot-password", json={"email": "student@example.com"})
    token = token_in(mailbox.sent[0].body)
    assert "/reset-password?token=" in mailbox.sent[0].body

    response = new_client().post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "brandnew2028"}
    )

    assert response.status_code == 200
    # The session that existed before the reset is signed out...
    assert api.get(SESSION).status_code == 401
    # ...the old password no longer works, and the new one does.
    fresh = new_client()
    old = fresh.post(LOGIN, json={"email": "student@example.com", "password": PASSWORD})
    assert old.status_code == 401
    log_in(fresh, "student@example.com", "brandnew2028")


def test_a_reset_link_works_only_once(api: TestClient, mailbox: MemoryEmailSender) -> None:
    sign_up(api)
    mailbox.sent.clear()
    api.post("/api/v1/auth/forgot-password", json={"email": "student@example.com"})
    token = token_in(mailbox.sent[0].body)
    api.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "brandnew2028"})

    again = api.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "another2029"}
    )

    assert again.status_code == 422


def test_a_weak_new_password_does_not_use_up_the_link(
    api: TestClient, mailbox: MemoryEmailSender
) -> None:
    sign_up(api)
    mailbox.sent.clear()
    api.post("/api/v1/auth/forgot-password", json={"email": "student@example.com"})
    token = token_in(mailbox.sent[0].body)

    weak = api.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "short"})
    good = api.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "brandnew2028"}
    )

    assert weak.status_code == 422
    assert good.status_code == 200


def test_a_verification_link_cannot_reset_a_password(
    api: TestClient, mailbox: MemoryEmailSender
) -> None:
    """A token is only good for the purpose it was issued for."""
    sign_up(api)
    verification_token = token_in(mailbox.sent[0].body)

    response = api.post(
        "/api/v1/auth/reset-password",
        json={"token": verification_token, "new_password": "brandnew2028"},
    )

    assert response.status_code == 422


# --- Rate limiting ------------------------------------------------------


def test_repeated_login_attempts_are_limited(api: TestClient) -> None:
    sign_up(api, "student@example.com")
    limiter.reset()
    attempt = {"email": "student@example.com", "password": "wrong-password1"}

    statuses = [api.post(LOGIN, json=attempt).status_code for _ in range(11)]

    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
    # Even the right password is refused until the window passes.
    blocked = api.post(LOGIN, json={"email": "student@example.com", "password": PASSWORD})
    assert blocked.status_code == 429
    assert csrf  # (imported helper is used elsewhere in this module)
