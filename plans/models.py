from django.db import models

from core.record_status import RECORD_STATUS_ACTIVE, RECORD_STATUS_CHOICES


class Plan(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    first_activation_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional discounted price for first-time website activation (e.g. Starter promo).",
    )
    currency = models.CharField(max_length=10, default="INR")
    duration = models.PositiveIntegerField(help_text="Duration of plan in days")
    coming_soon = models.BooleanField(
        default=False,
        help_text="When true, plan is listed but not available for purchase yet.",
    )
    record_status = models.CharField(
        max_length=16,
        choices=RECORD_STATUS_CHOICES,
        default=RECORD_STATUS_ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Feature(models.Model):
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name="features"
    )
    name = models.CharField(max_length=255)
    record_status = models.CharField(
        max_length=16,
        choices=RECORD_STATUS_CHOICES,
        default=RECORD_STATUS_ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

