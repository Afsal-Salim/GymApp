import hashlib
import os
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.record_status import RECORD_STATUS_ACTIVE, RECORD_STATUS_CHOICES


class Customer(models.Model):
    ROLE_ADMIN = 0
    ROLE_CLIENT = 1
    ROLE_CLIENT_CUSTOMER = 2
    ROLE_CHOICES = [
        (ROLE_ADMIN, "admin"),
        (ROLE_CLIENT, "client"),
        (ROLE_CLIENT_CUSTOMER, "client_customer"),
    ]

    AUTH_PROVIDER_EMAIL = "email"
    AUTH_PROVIDER_GOOGLE = "google"
    AUTH_PROVIDER_CHOICES = [
        (AUTH_PROVIDER_EMAIL, "Email"),
        (AUTH_PROVIDER_GOOGLE, "Google"),
    ]

    username = models.CharField(max_length=150, default="", unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    auth_provider = models.CharField(
        max_length=20,
        choices=AUTH_PROVIDER_CHOICES,
        default=AUTH_PROVIDER_EMAIL,
    )
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    user_content_policy_accepted = models.BooleanField(default=False)
    privacy_policy_accepted = models.BooleanField(default=False)
    record_status = models.CharField(
        max_length=16,
        choices=RECORD_STATUS_CHOICES,
        default=RECORD_STATUS_ACTIVE,
        db_index=True,
    )
    role = models.PositiveSmallIntegerField(
        choices=ROLE_CHOICES,
        default=ROLE_CLIENT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def hash_password(raw_password: str) -> str:
        passkey = os.getenv("CUSTOMER_PASSKEY", "")
        data = (passkey + raw_password).encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def set_password(self, raw_password: str) -> None:
        self.password = self.hash_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return secrets.compare_digest(self.password, self.hash_password(raw_password))

    def save(self, *args, **kwargs):
        # If password looks like plain text (not a 64-char hex digest), hash it.
        if self.password and len(self.password) != 64:
            self.password = self.hash_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email


class EmailOTP(models.Model):
    PURPOSE_SIGNUP = "signup"
    PURPOSE_PASSWORD_RESET = "password_reset"
    PURPOSE_CHOICES = [
        (PURPOSE_SIGNUP, "Signup"),
        (PURPOSE_PASSWORD_RESET, "Password reset"),
    ]

    email = models.EmailField()
    otp = models.CharField(max_length=6)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        default=PURPOSE_SIGNUP,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    record_status = models.CharField(
        max_length=16,
        choices=RECORD_STATUS_CHOICES,
        default=RECORD_STATUS_ACTIVE,
        db_index=True,
    )
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        minutes = max(1, getattr(settings, "OTP_EXPIRE_MINUTES", 10))
        created = self.created_at
        # Ensure we compare aware datetimes (SQLite can return naive in some setups)
        if timezone.is_naive(created):
            created = timezone.make_aware(created, timezone=timezone.utc)
        expiry_at = created + timezone.timedelta(minutes=minutes)
        now = timezone.now()
        if timezone.is_naive(now):
            now = timezone.make_aware(now, timezone=timezone.utc)
        return now > expiry_at
