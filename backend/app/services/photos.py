"""Profile and listing photos: checking, cleaning and storing them.

Every uploaded photo is decoded and re-encoded before it is kept. That one
step does several jobs at once:

* It proves the file really is an image. A file that only *starts* like a
  JPEG, or a program renamed to ".jpg", fails to decode and is refused.
* It removes all metadata. The new file is built from the pixels alone, so
  EXIF data (camera details, and above all GPS location) cannot survive.
* It applies the camera's rotation first, so photos are not shown sideways.
* It shrinks large photos, so nobody downloads a 12-megapixel original.

The original upload is never stored. Photos live in their own private
storage area, separate from verification documents, with their own access
rules (see app/api/v1/listings.py and app/api/v1/account.py). Nothing is
ever served from a public address.
"""

from __future__ import annotations

import hashlib
import io
import warnings
from dataclasses import dataclass
from functools import lru_cache

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import BusinessRuleError
from app.services.storage import LocalPrivateStorage, PrivateStorage

# Refuse "decompression bombs": a small file that expands to billions of
# pixels in memory. 40 megapixels is far above any phone camera.
MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

PROFILE_PHOTO_SIZE = 512  # square, pixels
LISTING_PHOTO_MAX_SIDE = 1600  # pixels
OUTPUT_CONTENT_TYPE = "image/jpeg"
ALLOWED_TEXT = "JPEG, PNG or WebP"

# Real image types are recognised by their first bytes, never by the name
# or the type the browser claims.
_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def _looks_like_image(data: bytes) -> bool:
    return (
        data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"\x89PNG\r\n\x1a\n")
        or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )


@dataclass(frozen=True)
class ProcessedPhoto:
    data: bytes
    width: int
    height: int
    content_type: str = OUTPUT_CONTENT_TYPE


def _flatten(image: Image.Image) -> Image.Image:
    """RGB on a white background (transparent PNGs would turn black)."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def process_photo(data: bytes, *, square: int | None = None) -> ProcessedPhoto:
    """Turn uploaded bytes into a clean, metadata-free JPEG.

    `square` crops to a centred square of that size (profile photos);
    otherwise the photo keeps its shape and its longer side is reduced to
    at most LISTING_PHOTO_MAX_SIDE.
    """
    if not _looks_like_image(data):
        raise BusinessRuleError(f"Upload a {ALLOWED_TEXT} image.")

    try:
        with warnings.catch_warnings():
            # Pillow only *warns* below twice the pixel limit; treat that as
            # a refusal too.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                if probe.format not in _ALLOWED_FORMATS:
                    raise BusinessRuleError(f"Upload a {ALLOWED_TEXT} image.")
                probe.verify()  # structural check of the whole file
            with Image.open(io.BytesIO(data)) as source:
                source.seek(0)  # the first frame only, for animated images
                source.load()
                upright = ImageOps.exif_transpose(source)
                pixels = _flatten(upright)
    except BusinessRuleError:
        raise
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
    ) as error:
        raise BusinessRuleError("That file is not a valid image.") from error

    if square:
        pixels = ImageOps.fit(pixels, (square, square), method=Image.Resampling.LANCZOS)
    else:
        pixels.thumbnail((LISTING_PHOTO_MAX_SIDE, LISTING_PHOTO_MAX_SIDE), Image.Resampling.LANCZOS)

    # A brand-new image holds only pixels: no EXIF, no GPS, no comments, no
    # embedded thumbnails, nothing copied from the upload's metadata.
    clean = Image.new("RGB", pixels.size)
    clean.paste(pixels)
    output = io.BytesIO()
    clean.save(output, format="JPEG", quality=85, optimize=True, progressive=True)
    return ProcessedPhoto(data=output.getvalue(), width=clean.width, height=clean.height)


async def read_photo_upload(upload: UploadFile) -> bytes:
    """Read an uploaded photo, refusing it if it is empty or too large."""
    limit = get_settings().max_photo_bytes
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise BusinessRuleError(f"The photo is too large. The limit is {limit / 1024 / 1024:g} MB.")
    if not data:
        raise BusinessRuleError("The file is empty.")
    return data


@lru_cache
def get_photo_storage() -> PrivateStorage:
    """Photos are kept apart from verification documents."""
    return LocalPrivateStorage(get_settings().photo_storage_dir)


def photo_version(key: str) -> str:
    """A short tag that changes whenever a photo is replaced, so browsers
    never show an old cached copy. Derived from the private key by a
    one-way hash, so the key itself is never revealed."""
    return hashlib.sha256(key.encode()).hexdigest()[:12]
