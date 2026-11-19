"""What a listing's creator sees about the people interested in it.

Only the creator of that listing ever receives this. It shows each
student's public profile (the same allow-list Discover uses), never their
email address or anything else private.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ListingInterestStatus
from app.schemas.discovery import CompatibilityOut, StudentPublicOut


class InterestedStudentOut(BaseModel):
    interest_id: uuid.UUID
    status: ListingInterestStatus
    created_at: datetime
    responded_at: datetime | None
    # The brokerage they were shown and accepted (None if there is none).
    acknowledged_brokerage_amount: int | None
    student: StudentPublicOut
    # How well their preferences fit the creator's. None when the creator
    # has no student profile to compare with (an owner or agent, say).
    compatibility: CompatibilityOut | None
