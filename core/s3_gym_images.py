"""Upload validated gym images to S3 (folder per business slug, UUID filename)."""

from __future__ import annotations

import re
import uuid
from typing import Tuple

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

from core.logging import app_logger


_SLUG_SAFE = re.compile(r"^[-a-zA-Z0-9_]+$")

# SigV4 so presigned GET uses X-Amz-Expires (seconds). Legacy SigV2 URLs use a far-future Unix Expires= timestamp.
_S3_CLIENT_CONFIG = Config(signature_version="s3v4")

# Cache bucket AWS region for correct virtual-hosted URLs (avoids PermanentRedirect).
_bucket_region_cache: dict[str, str] = {}
# After get_bucket_location fails once, avoid hammering S3 on every serializer row.
_bucket_location_lookup_failed = False


def _explicit_gym_bucket_region() -> str:
    return (getattr(settings, "AWS_S3_GYM_IMAGES_BUCKET_REGION", "") or "").strip()


def region_for_gym_image_urls() -> str:
    """
    Region used in virtual-hosted public URLs for this app's gym image bucket.

    Order: ``AWS_S3_GYM_IMAGES_BUCKET_REGION`` → cached ``get_bucket_location`` → API call
    (when configured) → ``AWS_S3_REGION_NAME``. Drives ``https://{bucket}.s3.{region}.amazonaws.com/``.
    """
    bucket = (getattr(settings, "AWS_S3_GYM_IMAGES_BUCKET", "") or "").strip()
    explicit = _explicit_gym_bucket_region()
    if explicit:
        if bucket:
            _bucket_region_cache[bucket] = explicit
        return explicit
    if bucket and bucket in _bucket_region_cache:
        return _bucket_region_cache[bucket]
    global _bucket_location_lookup_failed
    if _bucket_location_lookup_failed:
        return _s3_region()
    if not bucket or not gym_s3_configured():
        return _s3_region()
    client = _s3_client()
    return _resolve_bucket_region_for_public_url(client, bucket)


def public_url_for_gym_s3_key(key: str) -> str:
    """Canonical HTTPS URL for ``key`` in ``AWS_S3_GYM_IMAGES_BUCKET`` (for API output)."""
    k = (key or "").strip()
    bucket = (getattr(settings, "AWS_S3_GYM_IMAGES_BUCKET", "") or "").strip()
    if not k or not bucket:
        return ""
    reg = region_for_gym_image_urls()
    return _public_object_url(bucket=bucket, key=k, region=reg)


def gym_image_browser_url(key: str) -> str:
    """
    URL safe to open in a browser for this object.

    If ``AWS_S3_GYM_IMAGES_USE_PRESIGNED_GET`` (default true) and S3 credentials are configured,
    returns a presigned GET URL (expires after ``AWS_S3_GYM_IMAGES_PRESIGNED_EXPIRES`` seconds).
    Otherwise returns the plain virtual-hosted URL (works only when the object is publicly readable).
    """
    k = (key or "").strip()
    bucket = (getattr(settings, "AWS_S3_GYM_IMAGES_BUCKET", "") or "").strip()
    if not k or not bucket:
        return ""
    use_presign = bool(getattr(settings, "AWS_S3_GYM_IMAGES_USE_PRESIGNED_GET", True))
    if not use_presign or not gym_s3_configured():
        return public_url_for_gym_s3_key(k)
    expires = int(getattr(settings, "AWS_S3_GYM_IMAGES_PRESIGNED_EXPIRES", 3600))
    reg = region_for_gym_image_urls()
    client = _s3_client(region_name=reg)
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": k},
            ExpiresIn=expires,
        )
    except (ClientError, BotoCoreError, ValueError, TypeError) as e:
        app_logger.warning("gym_image presigned URL failed; using plain URL", error=str(e))
        return public_url_for_gym_s3_key(k)


def _sanitize_slug_for_s3_key(slug: str) -> str:
    s = (slug or "").strip().lower()
    if not _SLUG_SAFE.match(s):
        raise ValueError("Invalid slug for storage key.")
    return s


def _s3_region() -> str:
    return (getattr(settings, "AWS_S3_REGION_NAME", "") or "ap-south-1").strip()


def _explicit_s3_credentials() -> tuple[str, str]:
    ak = (getattr(settings, "AWS_ACCESS_KEY_ID", "") or "").strip()
    sk = (getattr(settings, "AWS_SECRET_ACCESS_KEY", "") or "").strip()
    return ak, sk


def _implicit_aws_credentials_allowed() -> bool:
    """
    When True, we treat S3 as configured with only a bucket name (boto3 uses default chain).

    Avoids calling botocore ``get_credentials()`` on every upload check — that can block
    ~10s on laptops probing EC2 instance metadata. Set ``GYM_IMAGES_USE_DEFAULT_AWS_CREDENTIALS=true``
    on EC2/ECS with an IAM role, or when relying on ~/.aws/credentials.
    """
    return bool(getattr(settings, "GYM_IMAGES_USE_DEFAULT_AWS_CREDENTIALS", False))


def _s3_client(region_name: str | None = None):
    """S3 client: uses explicit env keys when set, otherwise default credential chain."""
    reg = (region_name or "").strip() or _s3_region()
    kwargs: dict = {"region_name": reg, "config": _S3_CLIENT_CONFIG}
    ak, sk = _explicit_s3_credentials()
    if ak:
        kwargs["aws_access_key_id"] = ak
    if sk:
        kwargs["aws_secret_access_key"] = sk
    return boto3.client("s3", **kwargs)


def gym_images_boto3_client():
    """Same S3 client as uploads; for management commands (e.g. bucket policy)."""
    return _s3_client()


def _resolve_bucket_region_for_public_url(client, bucket: str) -> str:
    """
    Region for ``https://bucket.s3...`` hostnames.

    Wrong region in the hostname (e.g. ``.s3.ap-south-1...`` for a ``us-east-1`` bucket)
    causes PermanentRedirect. Public URLs use the regional form
    ``https://{bucket}.s3.{region}.amazonaws.com/`` (same as the S3 console “Object URL”).
    Uses ``get_bucket_location`` when no explicit
    ``AWS_S3_GYM_IMAGES_BUCKET_REGION``; on API failure falls back to ``AWS_S3_REGION_NAME``
    without caching a wrong region.
    """
    global _bucket_location_lookup_failed
    explicit = _explicit_gym_bucket_region()
    if explicit:
        _bucket_region_cache[bucket] = explicit
        _bucket_location_lookup_failed = False
        return explicit
    if bucket in _bucket_region_cache:
        return _bucket_region_cache[bucket]
    if _bucket_location_lookup_failed:
        return _s3_region()
    try:
        resp = client.get_bucket_location(Bucket=bucket)
        loc = resp.get("LocationConstraint")
    except (ClientError, BotoCoreError):
        _bucket_location_lookup_failed = True
        return _s3_region()
    # us-east-1 returns None/empty; legacy EU (Ireland) returns "EU"
    if not loc:
        reg = "us-east-1"
    elif loc == "EU":
        reg = "eu-west-1"
    else:
        reg = str(loc)
    _bucket_region_cache[bucket] = reg
    return reg


def _public_object_url(*, bucket: str, key: str, region: str) -> str:
    prefix = (getattr(settings, "AWS_S3_GYM_IMAGES_URL_PREFIX", "") or "").strip()
    if prefix:
        return f"{prefix.rstrip('/')}/{key}"
    reg = (region or "").strip() or _s3_region()
    host = f"{bucket}.s3.{reg}.amazonaws.com"
    return f"https://{host}/{key}"


def gym_s3_configured() -> bool:
    return len(gym_s3_configuration_missing()) == 0


def gym_s3_configuration_missing() -> list[str]:
    """What blocks uploads (no secret values)."""
    missing: list[str] = []
    if not (getattr(settings, "AWS_S3_GYM_IMAGES_BUCKET", "") or "").strip():
        missing.append("AWS_S3_GYM_IMAGES_BUCKET")
        return missing
    ak, sk = _explicit_s3_credentials()
    if ak and sk:
        return missing
    if _implicit_aws_credentials_allowed():
        return missing
    missing.append(
        "AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (or S3_ACCESS_KEY + S3_SECRET_KEY), "
        "or set GYM_IMAGES_USE_DEFAULT_AWS_CREDENTIALS=true (IAM role / ~/.aws/credentials)."
    )
    return missing


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

    if not gym_s3_configured():
        raise RuntimeError("S3 is not configured (bucket and AWS credentials required).")

    slug_part = _sanitize_slug_for_s3_key(business_slug)
    ext = extension_with_dot if extension_with_dot.startswith(".") else f".{extension_with_dot}"
    key = f"{slug_part}/{uuid.uuid4().hex}{ext}"

    client = _s3_client()

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

    url_region = _resolve_bucket_region_for_public_url(client, bucket)
    public_url = _public_object_url(bucket=bucket, key=key, region=url_region)

    return public_url, key


def delete_gym_image_from_s3(*, s3_key: str) -> None:
    """Remove object from gym bucket. No-op if S3 not configured or ``s3_key`` empty."""
    key = (s3_key or "").strip()
    if not key:
        return
    if not gym_s3_configured():
        raise RuntimeError("S3 is not configured (bucket and AWS credentials required).")

    bucket = (getattr(settings, "AWS_S3_GYM_IMAGES_BUCKET", "") or "").strip()

    client = _s3_client()
    try:
        client.delete_object(Bucket=bucket, Key=key)
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"S3 delete failed: {e}") from e
