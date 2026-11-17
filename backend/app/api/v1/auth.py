"""Sign-up, sign-in, sign-out, email verification and password reset."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status

from app.api.deps import AppSettings, CurrentSession, CurrentUser, Database
from app.core.config import Settings
from app.core.rate_limit import rate_limit
from app.core.security import csrf_token_for
from app.models.enums import AccountTokenPurpose
from app.models.user import User
from app.schemas.account import (
    EmailRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    SessionOut,
    TokenRequest,
)
from app.services import auth as auth_service
from app.services.account import user_out
from app.services.email import (
    EmailSender,
    get_email_sender,
    password_reset_email,
    send_safely,
    verification_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])

Mailer = Annotated[EmailSender, Depends(get_email_sender)]

MINUTE = 60
HOUR = 60 * MINUTE


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_lifetime_hours * HOUR,
        # HttpOnly: page scripts cannot read the cookie, so a script
        # injected into the site cannot steal the session.
        httponly=True,
        # Secure: only ever sent over HTTPS (switched on outside local use).
        secure=settings.cookie_secure,
        # SameSite: other websites cannot make the browser send it.
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def _session_out(user: User, token: str, settings: Settings) -> SessionOut:
    return SessionOut(
        user=user_out(user),
        csrf_token=csrf_token_for(token, settings.secret_key.get_secret_value()),
    )


def _queue_verification_email(
    db: Database, user: User, settings: Settings, mailer: EmailSender, tasks: BackgroundTasks
) -> None:
    token = auth_service.issue_account_token(
        db,
        user,
        AccountTokenPurpose.EMAIL_VERIFICATION,
        valid_for=timedelta(hours=settings.email_verification_hours),
    )
    # Sent after the response, so a slow mail server never delays the page.
    tasks.add_task(send_safely, mailer, verification_email(user.email, token, settings))


@router.post(
    "/register",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register", limit=10, window_seconds=HOUR))],
)
def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: Database,
    settings: AppSettings,
    mailer: Mailer,
    tasks: BackgroundTasks,
) -> SessionOut:
    """Create an account, send the verification email and sign the person in."""
    user = auth_service.register_user(
        db, email=body.email, password=body.password, accepted_terms=body.accepted_terms
    )
    _queue_verification_email(db, user, settings, mailer, tasks)
    token = auth_service.create_session(
        db, user, settings, user_agent=request.headers.get("user-agent")
    )
    db.commit()
    _set_session_cookie(response, token, settings)
    return _session_out(user, token, settings)


@router.post(
    "/login",
    response_model=SessionOut,
    dependencies=[Depends(rate_limit("login", limit=10, window_seconds=5 * MINUTE))],
)
def login(
    body: LoginRequest, request: Request, response: Response, db: Database, settings: AppSettings
) -> SessionOut:
    user = auth_service.authenticate(db, email=body.email, password=body.password)
    token = auth_service.create_session(
        db, user, settings, user_agent=request.headers.get("user-agent")
    )
    db.commit()
    _set_session_cookie(response, token, settings)
    return _session_out(user, token, settings)


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response, context: CurrentSession, db: Database, settings: AppSettings
) -> MessageResponse:
    """End this session on the server, then remove the cookie."""
    auth_service.revoke_session(db, context.session)
    db.commit()
    _clear_session_cookie(response, settings)
    return MessageResponse(message="You have been logged out.")


@router.get("/session", response_model=SessionOut)
def read_session(context: CurrentSession, db: Database, settings: AppSettings) -> SessionOut:
    """Who is signed in. The frontend calls this when a page loads."""
    # Saves the "last used" time that keeps an active session alive.
    db.commit()
    return _session_out(context.user, context.token, settings)


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(body: TokenRequest, db: Database) -> MessageResponse:
    auth_service.verify_email(db, body.token)
    db.commit()
    return MessageResponse(message="Your email address is confirmed.")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("resend-verification", limit=5, window_seconds=HOUR))],
)
def resend_verification(
    user: CurrentUser, db: Database, settings: AppSettings, mailer: Mailer, tasks: BackgroundTasks
) -> MessageResponse:
    if user.email_verified_at is None:
        _queue_verification_email(db, user, settings, mailer, tasks)
        db.commit()
    return MessageResponse(
        message="If your email still needs confirming, a new link is on its way."
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("forgot-password", limit=5, window_seconds=HOUR))],
)
def forgot_password(
    body: EmailRequest, db: Database, settings: AppSettings, mailer: Mailer, tasks: BackgroundTasks
) -> MessageResponse:
    """Always answers the same way, whether or not the email has an account,
    so this cannot be used to discover who is registered."""
    user = auth_service.find_user_for_password_reset(db, body.email)
    if user is not None:
        token = auth_service.issue_account_token(
            db,
            user,
            AccountTokenPurpose.PASSWORD_RESET,
            valid_for=timedelta(minutes=settings.password_reset_minutes),
        )
        db.commit()
        tasks.add_task(send_safely, mailer, password_reset_email(user.email, token, settings))
    return MessageResponse(
        message="If an account exists for that email, a reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("reset-password", limit=10, window_seconds=HOUR))],
)
def reset_password(
    body: ResetPasswordRequest, response: Response, db: Database, settings: AppSettings
) -> MessageResponse:
    auth_service.reset_password(db, token=body.token, new_password=body.new_password)
    db.commit()
    # Every session was just ended, including this browser's if it had one.
    _clear_session_cookie(response, settings)
    return MessageResponse(message="Your password has been changed. Please log in.")
