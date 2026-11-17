"""Submitting verification evidence, and fetching one's own documents.

Three separate verification types, three separate endpoints. Submitting
never approves anything: every submission waits for an administrator.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status

from app.api.deps import AppSettings, CurrentUser, Database
from app.core.errors import NotFoundError
from app.core.rate_limit import rate_limit
from app.models.enums import DocumentType, UserRole
from app.models.verification import VerificationDocument
from app.schemas.account import OwnVerificationOut, OwnVerificationsOut
from app.services import verification_submission as submission
from app.services.account import own_verification
from app.services.storage import PrivateStorage, get_storage, read_validated_upload

router = APIRouter(tags=["verification"])

Storage = Annotated[PrivateStorage, Depends(get_storage)]
UploadedFile = Annotated[UploadFile, File(description="A PDF, JPEG or PNG")]

# Uploads are the most expensive thing a person can ask the API to do.
_upload_limit = Depends(rate_limit("verification-upload", limit=20, window_seconds=3600))


@router.get("/me/verifications", response_model=OwnVerificationsOut)
def read_own_verifications(user: CurrentUser, db: Database) -> OwnVerificationsOut:
    db.refresh(user)
    return OwnVerificationsOut(
        identity=own_verification(user.identity_verification),
        student=own_verification(user.student_verification),
    )


@router.post(
    "/me/verifications/identity",
    response_model=OwnVerificationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_upload_limit],
)
async def submit_identity(
    user: CurrentUser,
    db: Database,
    storage: Storage,
    settings: AppSettings,
    file: UploadedFile,
    document_type: Annotated[DocumentType, Form()] = DocumentType.GOVERNMENT_ID,
) -> OwnVerificationOut:
    validated = await read_validated_upload(file, settings.max_upload_bytes)
    verification = submission.submit_identity_document(
        db, storage, user=user, document_type=document_type, file=validated
    )
    db.commit()
    return own_verification(verification)


@router.post(
    "/me/verifications/student",
    response_model=OwnVerificationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_upload_limit],
)
async def submit_student(
    user: CurrentUser,
    db: Database,
    storage: Storage,
    settings: AppSettings,
    file: UploadedFile,
    institution_name: Annotated[str, Form(max_length=180)],
    document_type: Annotated[DocumentType, Form()] = DocumentType.STUDENT_ID,
) -> OwnVerificationOut:
    validated = await read_validated_upload(file, settings.max_upload_bytes)
    verification = submission.submit_student_document(
        db,
        storage,
        user=user,
        institution_name=institution_name,
        document_type=document_type,
        file=validated,
    )
    db.commit()
    return own_verification(verification)


@router.get("/me/listings/{listing_id}/authority-verification", response_model=OwnVerificationOut)
def read_listing_authority(
    listing_id: uuid.UUID, user: CurrentUser, db: Database
) -> OwnVerificationOut:
    listing = submission.get_own_property_listing(db, user, listing_id)
    return own_verification(listing.authority_verification)


@router.post(
    "/me/listings/{listing_id}/authority-verification",
    response_model=OwnVerificationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_upload_limit],
)
async def submit_listing_authority(
    listing_id: uuid.UUID,
    user: CurrentUser,
    db: Database,
    storage: Storage,
    settings: AppSettings,
    file: UploadedFile,
    document_type: Annotated[DocumentType, Form()],
    owner_name: Annotated[str | None, Form(max_length=120)] = None,
    owner_contact: Annotated[str | None, Form(max_length=255)] = None,
) -> OwnVerificationOut:
    """Evidence of the right to list one property the caller created.

    Owners send proof of ownership, tenants a rental agreement (and the
    landlord's permission), agents the owner's written authorisation plus
    the owner's contact details for independent confirmation.
    """
    # Checked first: someone else's listing answers "not found" before any
    # file is even read.
    listing = submission.get_own_property_listing(db, user, listing_id)
    validated = await read_validated_upload(file, settings.max_upload_bytes)
    verification = submission.submit_listing_authority_document(
        db,
        storage,
        user=user,
        listing=listing,
        document_type=document_type,
        file=validated,
        owner_name=owner_name,
        owner_contact=owner_contact,
    )
    db.commit()
    return own_verification(verification)


@router.get("/verification-documents/{document_id}/content")
def download_document(
    document_id: uuid.UUID, user: CurrentUser, db: Database, storage: Storage
) -> Response:
    """Return a document's file to its uploader or to an administrator.

    This is the ONLY way a document leaves private storage. There is no
    public address for it and the storage location is never disclosed.
    Anyone else gets "not found", the same answer as for a document that
    does not exist, so ids cannot be used to discover documents.
    """
    document = db.get(VerificationDocument, document_id)
    allowed = document is not None and (
        document.uploaded_by == user.id or user.role == UserRole.ADMIN
    )
    if document is None or not allowed or document.deleted_at is not None:
        raise NotFoundError("That document does not exist.")

    data = storage.read(document.storage_key)
    extension = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}.get(
        document.content_type, "bin"
    )
    return Response(
        content=data,
        media_type=document.content_type,
        headers={
            # Download rather than display, under a neutral name.
            "Content-Disposition": f'attachment; filename="document-{document.id}.{extension}"',
            # The browser must not guess a different type...
            "X-Content-Type-Options": "nosniff",
            # ...and nothing may keep a copy.
            "Cache-Control": "no-store",
        },
    )
