"""Shapes used only by administrator endpoints.

These include reviewer notes and the owner's contact details, which is
why they are separate classes that no public or member endpoint returns.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import (
    ListingCreatorType,
    OwnerConfirmationStatus,
    VerificationStatus,
)
from app.schemas.account import DocumentOut

VerificationKind = Literal["identity", "student", "listing-authority"]


class AdminVerificationSummary(BaseModel):
    kind: VerificationKind
    id: uuid.UUID
    status: VerificationStatus
    submitted_at: datetime
    applicant_id: uuid.UUID
    applicant_email: str
    # Set for listing authority only.
    listing_id: uuid.UUID | None = None
    listing_title: str | None = None


class AdminVerificationDetail(AdminVerificationSummary):
    documents: list[DocumentOut]
    reviewer_note: str | None
    reviewed_at: datetime | None
    # --- Student only ---
    institution_name: str | None = None
    # --- Listing authority only ---
    creator_type: ListingCreatorType | None = None
    owner_name: str | None = None
    owner_contact: str | None = None
    owner_confirmation_status: OwnerConfirmationStatus | None = None
    owner_confirmation_note: str | None = None
    # What still blocks approval, e.g. "Proof of ownership has not been provided."
    outstanding_requirements: list[str] = []


class ReviewRequest(BaseModel):
    status: Literal["APPROVED", "REJECTED", "NEEDS_RESUBMISSION"]
    note: str | None = Field(default=None, max_length=2000)


class OwnerConfirmationRequest(BaseModel):
    confirmed: bool
    # How the owner was reached, so the check can be audited later.
    note: str = Field(min_length=1, max_length=2000)
