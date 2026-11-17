"""Administrator decisions about whether a listing may be shown.

This changes ONLY `moderation_status`. The creator's `lifecycle_status`
is a separate question and is never touched here.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, PermissionDeniedError
from app.models.enums import ListingType, ModerationStatus, UserRole, VerificationStatus
from app.models.listing import AccommodationListing
from app.models.review import ReviewEvent
from app.models.user import User

_NOTE_REQUIRED = {ModerationStatus.REJECTED, ModerationStatus.SUSPENDED}


def moderate_listing(
    db: Session,
    listing: AccommodationListing,
    *,
    new_status: ModerationStatus,
    actor: User,
    note: str | None = None,
) -> ReviewEvent:
    """Approve, reject, suspend or re-queue a listing, and record why.

    The key safeguard against unauthorised brokers lives here: a property
    listing cannot be approved until its listing authority verification
    has been approved. No verified authority, no public listing.
    """
    if actor.role != UserRole.ADMIN:
        raise PermissionDeniedError("Only an administrator can moderate a listing.")
    if listing.moderation_status == new_status:
        raise ConflictError(f"This listing is already {new_status.value.lower()}.")
    if new_status in _NOTE_REQUIRED and not (note and note.strip()):
        raise BusinessRuleError("A reason is required to reject or suspend a listing.")

    if (
        new_status == ModerationStatus.APPROVED
        and listing.listing_type == ListingType.EXISTING_ACCOMMODATION
    ):
        authority = listing.authority_verification
        if authority is None or authority.status != VerificationStatus.APPROVED:
            raise BusinessRuleError(
                "A property listing can only be approved after its listing "
                "authority has been verified."
            )

    event = ReviewEvent(
        listing_id=listing.id,
        actor_id=actor.id,
        from_status=listing.moderation_status.value,
        to_status=new_status.value,
        note=note,
    )
    listing.moderation_status = new_status

    db.add(event)
    db.flush()
    return event
