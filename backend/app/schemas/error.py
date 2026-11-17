"""The shape of every error response. See app/core/errors.py."""

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    # A stable identifier for programs, e.g. "not_found".
    code: str
    # A sentence for people.
    message: str
    # Extras, e.g. which fields failed validation.
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
