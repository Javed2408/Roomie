"""One consistent shape for every error the API returns.

Whatever goes wrong, the response body looks like this:

    {"error": {"code": "not_found", "message": "...", "details": null}}

`code` is a stable identifier for programs, `message` is for people, and
`details` carries extras such as which fields failed validation. The
frontend can therefore handle every error the same way.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for errors that services raise on purpose.

    Services know nothing about HTTP. They raise one of the subclasses
    below, and the handlers at the bottom of this file turn it into a
    response with the right status code.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class AuthenticationError(AppError):
    """Nobody is signed in, or the sign-in details were wrong."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "not_authenticated"


class RateLimitError(AppError):
    """Too many attempts in a short time."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "too_many_requests"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"


class ProfileIncompleteError(AppError):
    """The person must publish their own profile before using this."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "profile_incomplete"


class EmailNotVerifiedError(AppError):
    """The person must confirm their email address before doing this."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "email_not_verified"


class ConflictError(AppError):
    """The request clashes with the current state, e.g. a duplicate."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class BusinessRuleError(AppError):
    """The request is well-formed but breaks one of Roomie's rules."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "rule_violation"


def error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


async def _handle_app_error(_request: Request, error: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content=error_body(error.code, error.message, error.details),
    )


async def _handle_http_error(_request: Request, error: StarletteHTTPException) -> JSONResponse:
    # Raised by FastAPI itself, e.g. for an address that does not exist.
    code = "not_found" if error.status_code == status.HTTP_404_NOT_FOUND else "http_error"
    return JSONResponse(
        status_code=error.status_code,
        content=error_body(code, str(error.detail)),
        headers=error.headers,
    )


async def _handle_validation_error(
    _request: Request, error: RequestValidationError
) -> JSONResponse:
    # Say which fields are wrong, but never echo the submitted values back:
    # they might include a password.
    details = [
        {
            "field": ".".join(str(part) for part in item["loc"] if part != "body"),
            "message": item["msg"],
        }
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=error_body(
            "validation_error", "Some of the information sent is not valid.", details
        ),
    )


async def _handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    # Record everything for developers, tell the caller nothing internal.
    logger.exception(
        "Unhandled error",
        extra={"method": request.method, "path": request.url.path},
        exc_info=error,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_body("internal_error", "Something went wrong on our side."),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected_error)
