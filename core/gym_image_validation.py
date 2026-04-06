"""Validate uploaded gym images: size, extension, and real image bytes (Pillow)."""

from __future__ import annotations

import io
from typing import BinaryIO, Tuple

from django.core.exceptions import ValidationError
from django.conf import settings
from PIL import Image

# Limit decompression bomb (pixels); can override via Django settings.
_MAX_PX = int(getattr(settings, "GYM_IMAGE_MAX_PIXELS", 40_000_000))
Image.MAX_IMAGE_PIXELS = _MAX_PX

MAX_IMAGE_BYTES = 1024 * 1024  # 1 MB

ALLOWED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})

_EXPECTED_EXT_FOR_FORMAT = {
    "JPEG": frozenset({".jpg", ".jpeg"}),
    "PNG": frozenset({".png"}),
    "WEBP": frozenset({".webp"}),
    "GIF": frozenset({".gif"}),
}

# Pillow format string -> normalized extension + MIME for S3
FORMAT_MAP = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
    "GIF": (".gif", "image/gif"),
}


def validate_gym_image_upload(
    uploaded_file,
    *,
    max_bytes: int = MAX_IMAGE_BYTES,
) -> Tuple[bytes, str, str]:
    """
    Read and validate ``uploaded_file`` (Django UploadedFile).

    Returns ``(raw_bytes, extension_with_dot, content_type)``.

    Raises ``django.core.exceptions.ValidationError`` on failure.
    """
    name = (getattr(uploaded_file, "name", "") or "").strip()
    if "." not in name:
        raise ValidationError("Filename must include an extension (e.g. .jpg, .png).")
    ext_from_name = "." + name.rsplit(".", 1)[-1].lower()
    if ext_from_name not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Invalid file extension. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    declared = getattr(uploaded_file, "size", None)
    if declared is not None and declared > max_bytes:
        raise ValidationError(f"Image must be at most {max_bytes // (1024 * 1024)} MB.")

    raw = uploaded_file.read()
    if len(raw) > max_bytes:
        raise ValidationError(f"Image must be at most {max_bytes // (1024 * 1024)} MB.")

    if len(raw) == 0:
        raise ValidationError("Empty file.")

    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.verify()
    except Exception as e:
        raise ValidationError("File is not a valid image.") from e

    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.load()
            fmt = (img.format or "").upper()
    except Exception as e:
        raise ValidationError("File is not a valid image.") from e

    if fmt not in FORMAT_MAP:
        raise ValidationError(
            "Image type not allowed. Use JPEG, PNG, WebP, or GIF."
        )

    allowed_for_content = _EXPECTED_EXT_FOR_FORMAT.get(fmt)
    if ext_from_name not in allowed_for_content:
        raise ValidationError("File content does not match the file extension.")

    ext, mime = FORMAT_MAP[fmt]
    return raw, ext, mime
