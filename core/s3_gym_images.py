"""Upload validated gym images to S3 (folder per business slug, UUID filename)."""

from __future__ import annotations

import re
import uuid
from typing import Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings


_SLUG_SAFE = re.compile(r"^[-a-zA-Z0-9_]+$")


def _sanitize_slug_for_s3_key(slug: str) -> str:
    s = (slug or "").strip().lower()
    if not _SLUG_SAFE.match(s):
        raise ValueError("Invalid slug for storage key.")
    return s


def gym_s3_configured() -> bool:
    return bool(
        (getattr(settings, "AWS_S3_GYM_IMAGES_BUCKET", "") or "").strip()
        and (getattr(settings, "AWS_ACCESS_KEY_ID", "") or "").strip()
        and (getattr(settings, "AWS_SECRET_ACCESS_KEY", "") or "").strip()
    )


def upload_gym_image_to_s3(
    *,
    business_slug: str,
    file_body: bytes,
    extension_with_dot: str,
    content_type: str,
) -> Tuple[str, str]:
    """
    Upload bytes to ``{slug}/{uuid}{ext}``.

    Returns ``(public_url, s3_key)``.
    """
    bucket = (getattr(settings, "AWS_S3_GYM_IMAGES_BUCKET", "") or "").strip()
    region = (getattr(settings, "AWS_S3_REGION_NAME", "") or "us-east-1").strip()
    prefix = (getattr(settings, "AWS_S3_GYM_IMAGES_URL_PREFIX", "") or "").strip()

    if not gym_s3_configured():
        raise RuntimeError("S3 is not configured (bucket and AWS credentials required).")

    slug_part = _sanitize_slug_for_s3_key(business_slug)
    ext = extension_with_dot if extension_with_dot.startswith(".") else f".{extension_with_dot}"
    key = f"{slug_part}/{uuid.uuid4().hex}{ext}"

    client = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=(settings.AWS_ACCESS_KEY_ID or "").strip(),
        aws_secret_access_key=(settings.AWS_SECRET_ACCESS_KEY or "").strip(),
    )

    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_body,
            ContentType=content_type,
            CacheControl="max-age=31536000,public",
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"S3 upload failed: {e}") from e

    if prefix:
        public_url = f"{prefix.rstrip('/')}/{key}"
    else:
        if region == "us-east-1":
            host = f"{bucket}.s3.amazonaws.com"
        else:
            host = f"{bucket}.s3.{region}.amazonaws.com"
        public_url = f"https://{host}/{key}"

    return public_url, key
