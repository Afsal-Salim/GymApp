import hashlib
import os
import secrets

from django.db import models


class Customer(models.Model):
    username = models.CharField(max_length=150, default="", unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
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

