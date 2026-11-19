"""SQLAlchemy models: one class per database table.

Importing this package imports every model, which registers every table
with `Base.metadata`. Alembic relies on that to see the whole schema, so a
new model file must be added to the imports below.
"""

from app.models.auth import AccountToken, UserSession
from app.models.listing import (
    AccommodationListing,
    ListingChange,
    ListingImage,
    ListingInterest,
    ListingSocietyPreference,
)
from app.models.matching import Conversation, Match, Message, Swipe
from app.models.notification import Notification
from app.models.profile import RoommatePreferences, StudentProfile, UserSocietyPreference
from app.models.review import ReviewEvent
from app.models.safety import Block, Report
from app.models.society import DirectoryEvent, Locality, Society
from app.models.user import User
from app.models.verification import (
    IdentityVerification,
    ListingAuthorityVerification,
    StudentVerification,
    VerificationDocument,
)

__all__ = [
    "AccountToken",
    "UserSession",
    "AccommodationListing",
    "Block",
    "Conversation",
    "DirectoryEvent",
    "IdentityVerification",
    "ListingAuthorityVerification",
    "ListingChange",
    "ListingImage",
    "ListingInterest",
    "ListingSocietyPreference",
    "Locality",
    "Match",
    "Message",
    "Notification",
    "Report",
    "ReviewEvent",
    "RoommatePreferences",
    "Society",
    "StudentProfile",
    "StudentVerification",
    "Swipe",
    "User",
    "UserSocietyPreference",
    "VerificationDocument",
]
