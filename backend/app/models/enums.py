"""Every fixed set of values used in the database, in one place.

Each class lists the only values a column may hold. `StrEnum` members are
ordinary strings, so `ModerationStatus.APPROVED == "APPROVED"` is true.
These must stay in step with docs/DATABASE_SCHEMA.md and with the matching
TypeScript types in frontend/types/.
"""

from enum import StrEnum


class UserRole(StrEnum):
    # A member may be a student, a property owner or an agent. Which one
    # is established by their profile and verifications, not by this role.
    MEMBER = "MEMBER"
    ADMIN = "ADMIN"


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class AccountTokenPurpose(StrEnum):
    """What a single-use emailed token is for."""

    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    PASSWORD_RESET = "PASSWORD_RESET"  # noqa: S105 - a purpose, not a password


# --- Roommate preferences ---------------------------------------------


class RoomType(StrEnum):
    PRIVATE_ROOM = "PRIVATE_ROOM"
    SHARED_ROOM = "SHARED_ROOM"
    NO_PREFERENCE = "NO_PREFERENCE"


class FoodPreference(StrEnum):
    VEGETARIAN = "VEGETARIAN"
    NON_VEGETARIAN = "NON_VEGETARIAN"
    VEGAN = "VEGAN"


class HabitFrequency(StrEnum):
    """Used for both smoking and drinking."""

    NEVER = "NEVER"
    OCCASIONALLY = "OCCASIONALLY"
    REGULARLY = "REGULARLY"


class SleepSchedule(StrEnum):
    EARLY_BIRD = "EARLY_BIRD"
    NIGHT_OWL = "NIGHT_OWL"
    FLEXIBLE = "FLEXIBLE"


class CleanlinessLevel(StrEnum):
    RELAXED = "RELAXED"
    TIDY = "TIDY"
    VERY_TIDY = "VERY_TIDY"


class SocialPreference(StrEnum):
    QUIET = "QUIET"
    BALANCED = "BALANCED"
    SOCIAL = "SOCIAL"


class GuestFrequency(StrEnum):
    RARELY = "RARELY"
    SOMETIMES = "SOMETIMES"
    OFTEN = "OFTEN"


# --- Society directory -------------------------------------------------


class DirectoryStatus(StrEnum):
    """Whether an administrator has confirmed a directory record is accurate.

    Only VERIFIED records that are also active are shown to students. New
    and imported records always start UNVERIFIED.
    """

    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"


class CommunityType(StrEnum):
    """What kind of place a directory "society" record actually is.

    A locality is an AREA (such as Potheri) and is a different table. A
    society record is one named residential development inside an area.
    """

    # A named development of apartment buildings, gated or not.
    APARTMENT_COMPLEX = "APARTMENT_COMPLEX"
    # A named, gated development of independent houses or villas.
    VILLA_COMMUNITY = "VILLA_COMMUNITY"


class DirectoryAction(StrEnum):
    """What an entry in the directory change history records."""

    CREATED = "CREATED"
    UPDATED = "UPDATED"
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    ACTIVATED = "ACTIVATED"
    DEACTIVATED = "DEACTIVATED"


# --- Listings ----------------------------------------------------------


class ListingType(StrEnum):
    # A real room or flat with space to fill.
    EXISTING_ACCOMMODATION = "EXISTING_ACCOMMODATION"
    # A request from students who have no flat yet. Not a property.
    LOOKING_TO_RENT_TOGETHER = "LOOKING_TO_RENT_TOGETHER"


class ListingCreatorType(StrEnum):
    """Who is offering a property. Unauthorised brokers are not allowed."""

    PROPERTY_OWNER = "PROPERTY_OWNER"
    EXISTING_TENANT = "EXISTING_TENANT"
    AUTHORIZED_AGENT = "AUTHORIZED_AGENT"


class ListingLifecycleStatus(StrEnum):
    """Controlled by the listing's creator: "is this still available?"."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    FILLED = "FILLED"
    CLOSED = "CLOSED"


class ModerationStatus(StrEnum):
    """Controlled by administrators: "is this allowed to be shown?".

    Deliberately a separate set from ListingLifecycleStatus. The two
    answer different questions and must never be merged.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class Furnishing(StrEnum):
    UNFURNISHED = "UNFURNISHED"
    SEMI_FURNISHED = "SEMI_FURNISHED"
    FULLY_FURNISHED = "FULLY_FURNISHED"


class Facility(StrEnum):
    """What a property offers. A fixed list, so listings can be filtered and
    compared, and nobody can slip contact details into a "facility"."""

    WIFI = "WIFI"
    AIR_CONDITIONING = "AIR_CONDITIONING"
    WASHING_MACHINE = "WASHING_MACHINE"
    REFRIGERATOR = "REFRIGERATOR"
    KITCHEN = "KITCHEN"
    WATER_PURIFIER = "WATER_PURIFIER"
    GEYSER = "GEYSER"
    POWER_BACKUP = "POWER_BACKUP"
    LIFT = "LIFT"
    PARKING = "PARKING"
    SECURITY = "SECURITY"
    HOUSEKEEPING = "HOUSEKEEPING"


class TenantPermissionBasis(StrEnum):
    """Why a tenant may take another person into their home.

    A genuine rental agreement proves tenancy, not permission to share or
    sublet. The reviewer records which of these they actually saw.
    """

    AGREEMENT_PERMITS_SHARING = "AGREEMENT_PERMITS_SHARING"
    LANDLORD_PERMISSION = "LANDLORD_PERMISSION"


class BrokeragePayableTo(StrEnum):
    """Who receives a brokerage fee, when one applies.

    LISTING_CREATOR is allowed only when the creator is an authorised
    agent: an owner or tenant charging "brokerage" would be acting as an
    unauthorised broker.
    """

    LISTING_CREATOR = "LISTING_CREATOR"
    THIRD_PARTY_AGENT = "THIRD_PARTY_AGENT"


class ListingInterestStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    WITHDRAWN = "WITHDRAWN"


# --- Verification ------------------------------------------------------


class VerificationStatus(StrEnum):
    """Shared by all three verification types.

    There is no "not verified" value: that is expressed by there being no
    verification record at all.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_RESUBMISSION = "NEEDS_RESUBMISSION"


class StudentVerificationMethod(StrEnum):
    COLLEGE_EMAIL = "COLLEGE_EMAIL"
    DOCUMENT = "DOCUMENT"
    MANUAL = "MANUAL"


class OwnerConfirmationStatus(StrEnum):
    """Whether Roomie has confirmed an agent's authority with the owner.

    CONFIRMED means an administrator reached the owner directly, using
    details checked independently of the agent, and the owner agreed.
    """

    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    DENIED = "DENIED"


class DocumentType(StrEnum):
    GOVERNMENT_ID = "GOVERNMENT_ID"
    STUDENT_ID = "STUDENT_ID"
    ENROLMENT_PROOF = "ENROLMENT_PROOF"
    OWNERSHIP_PROOF = "OWNERSHIP_PROOF"
    RENTAL_AGREEMENT = "RENTAL_AGREEMENT"
    LANDLORD_PERMISSION = "LANDLORD_PERMISSION"
    OWNER_AUTHORIZATION = "OWNER_AUTHORIZATION"


# --- Matching and safety -----------------------------------------------


class SwipeAction(StrEnum):
    LIKE = "LIKE"
    PASS = "PASS"  # noqa: S105 - a swipe action, not a password


class MatchStatus(StrEnum):
    ACTIVE = "ACTIVE"
    UNMATCHED = "UNMATCHED"


class ReportReason(StrEnum):
    FAKE_OR_MISLEADING = "FAKE_OR_MISLEADING"
    HARASSMENT = "HARASSMENT"
    SCAM_OR_FRAUD = "SCAM_OR_FRAUD"
    UNAUTHORISED_BROKER = "UNAUTHORISED_BROKER"
    INAPPROPRIATE_CONTENT = "INAPPROPRIATE_CONTENT"
    OTHER = "OTHER"


class ReportStatus(StrEnum):
    OPEN = "OPEN"
    ACTIONED = "ACTIONED"
    DISMISSED = "DISMISSED"
