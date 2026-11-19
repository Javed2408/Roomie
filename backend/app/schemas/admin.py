"""Shapes used only by administrator endpoints.

These include reviewer notes and the owner's contact details, which is
why they are separate classes that no public or member endpoint returns.
"""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.enums import (
    ListingCreatorType,
    ListingLifecycleStatus,
    ListingType,
    ModerationStatus,
    OwnerConfirmationStatus,
    TenantPermissionBasis,
    VerificationStatus,
)
from app.schemas.account import DocumentOut
from app.schemas.listing import ListingPublic

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
    # Tenants: recorded by the reviewer on approval.
    tenant_permission_basis: TenantPermissionBasis | None = None
    rental_agreement_valid_until: date | None = None
    # What still blocks approval, e.g. "Proof of ownership has not been provided."
    outstanding_requirements: list[str] = []


class ReviewRequest(BaseModel):
    status: Literal["APPROVED", "REJECTED", "NEEDS_RESUBMISSION"]
    # Required to reject or ask for resubmission. For listing authority it
    # is shown to the listing's creator as the reason, so write it for them.
    note: str | None = Field(default=None, max_length=2000)
    # --- Approving a TENANT's listing authority only ---
    # What the reviewer saw that lets the tenant take someone in.
    tenant_permission_basis: TenantPermissionBasis | None = None
    # When the rental agreement ends.
    rental_agreement_valid_until: date | None = None


class OwnerConfirmationRequest(BaseModel):
    confirmed: bool
    # How the owner was reached, so the check can be audited later.
    note: str = Field(min_length=1, max_length=2000)


# --- Listing moderation ------------------------------------------------------------


class AdminListingSummary(BaseModel):
    id: uuid.UUID
    type: ListingType
    title: str
    creator_type: ListingCreatorType | None
    owner_id: uuid.UUID
    owner_email: str
    lifecycle_status: ListingLifecycleStatus
    moderation_status: ModerationStatus
    # Property listings only: the separate listing authority check.
    authority_status: VerificationStatus | None
    authority_verification_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class AdminReviewEventOut(BaseModel):
    at: datetime
    actor_email: str
    subject: Literal["listing", "listing-authority"]
    from_status: str | None
    to_status: str
    note: str | None


class AdminListingChangeOut(BaseModel):
    at: datetime
    actor_email: str
    changes: dict[str, Any]
    note: str | None


class AdminListingDetail(AdminListingSummary):
    # Everything the public would see, once approved.
    listing: ListingPublic
    # What still blocks approving the listing authority (property only).
    authority_requirements: list[str]
    owner_confirmation_status: OwnerConfirmationStatus | None
    review_history: list[AdminReviewEventOut]
    change_history: list[AdminListingChangeOut]
    interest_count: int


class ModerationRequest(BaseModel):
    status: Literal["APPROVED", "REJECTED", "SUSPENDED", "PENDING"]
    # Required to reject or suspend. Shown to the listing's creator.
    note: str | None = Field(default=None, max_length=2000)
