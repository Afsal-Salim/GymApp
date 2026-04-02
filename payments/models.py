from django.db import models

from businesses.models import Business
from core.record_status import RECORD_STATUS_ACTIVE, RECORD_STATUS_CHOICES


class Payment(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="payments")
    razorpay_order_id = models.CharField(max_length=255, blank=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    payment_status = models.CharField(max_length=50)
    payment_method = models.CharField(max_length=50, blank=True)
    record_status = models.CharField(
        max_length=16,
        choices=RECORD_STATUS_CHOICES,
        default=RECORD_STATUS_ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.business.name} - {self.amount} {self.currency}"

