from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.core import signing
from django.utils import timezone


def _get_secret() -> str:
    return settings.SECRET_KEY


def _make_token(user_id: int, token_type: str, lifetime: timedelta) -> str:
    payload = {
        "sub": user_id,
        "type": token_type,
        "exp": (timezone.now() + lifetime).timestamp(),
    }
    return signing.dumps(payload, key=_get_secret())


def _verify(raw_token: str, expected_type: str) -> Optional[dict]:
    try:
        payload = signing.loads(raw_token, key=_get_secret())
    except signing.BadSignature:
        return None

    if payload.get("type") != expected_type:
        return None

    exp_ts = payload.get("exp")
    if exp_ts is None:
        return None

    if timezone.now().timestamp() > exp_ts:
        return None

    return payload


def create_access_token(user, lifetime: Optional[timedelta] = None) -> str:
    lifetime = lifetime or getattr(settings, "AUTH_ACCESS_TOKEN_LIFETIME", timedelta(minutes=15))
    return _make_token(user.id, "access", lifetime)


def create_refresh_token(user, lifetime: Optional[timedelta] = None) -> str:
    lifetime = lifetime or getattr(settings, "AUTH_REFRESH_TOKEN_LIFETIME", timedelta(days=7))
    return _make_token(user.id, "refresh", lifetime)


def verify_token(token: str, expected_type: str) -> Optional[dict]:
    return _verify(token, expected_type)


def create_password_reset_token(user, lifetime: Optional[timedelta] = None) -> str:
    lifetime = lifetime or getattr(
        settings, "AUTH_PASSWORD_RESET_TOKEN_LIFETIME", timedelta(hours=1)
    )
    return _make_token(user.id, "password_reset", lifetime)

