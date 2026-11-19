"""Shared pieces for routes that receive or send photos.

Photos have their own storage (separate from verification documents) and
their own access rules, applied by each route before it calls
`photo_response`. A photo is only ever sent by an API route that has
checked who is asking; there is no public address for any file.
"""

from typing import Annotated

from fastapi import Depends, File, Response, UploadFile

from app.core.rate_limit import rate_limit
from app.services.photos import ProcessedPhoto, get_photo_storage
from app.services.storage import PrivateStorage, new_storage_key

PhotoStorage = Annotated[PrivateStorage, Depends(get_photo_storage)]
UploadedPhoto = Annotated[UploadFile, File(description="A JPEG, PNG or WebP image")]

photo_upload_limit = Depends(rate_limit("photo-upload", limit=60, window_seconds=3600))


def save_photo(storage: PrivateStorage, photo: ProcessedPhoto) -> str:
    """Store a cleaned photo under a new random key and return the key."""
    key = new_storage_key()
    storage.save(key, photo.data)
    return key


def photo_response(data: bytes, content_type: str) -> Response:
    return Response(
        content=data,
        media_type=content_type,
        headers={
            # Only this browser may keep a copy, briefly. Photo addresses
            # change when a photo is replaced, so stale copies never show.
            "Cache-Control": "private, max-age=600",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )
