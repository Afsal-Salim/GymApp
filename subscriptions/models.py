from django.db import models
from django.utils import timezone

from businesses.models import Business
from core.record_status import RECORD_STATUS_ACTIVE, RECORD_STATUS_CHOICES
from plans.models import Plan


class Subscription(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    payment_id = models.CharField(max_length=255, blank=True)
    subscription_start_date = models.DateField()
    subscription_end_date = models.DateField()
    record_status = models.CharField(
        max_length=16,
        choices=RECORD_STATUS_CHOICES,
        default=RECORD_STATUS_ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.business.name} - {self.plan.name}"

