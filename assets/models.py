from django.db import models

from businesses.models import Business
from core.record_status import RECORD_STATUS_ACTIVE, RECORD_STATUS_CHOICES


class Asset(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="assets")
    image_url = models.URLField()
    asset_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    record_status = models.CharField(
        max_length=16,
        choices=RECORD_STATUS_CHOICES,
        default=RECORD_STATUS_ACTIVE,
        db_index=True,
    )

    def __str__(self) -> str:
        return f"{self.business.name} - {self.asset_type}"

