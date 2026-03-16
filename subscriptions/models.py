from django.db import models

from businesses.models import Business
from plans.models import Plan


class Subscription(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    payment_id = models.CharField(max_length=255, blank=True)
    subscription_start_date = models.DateField()
    subscription_end_date = models.DateField()

    def __str__(self) -> str:
        return f"{self.business.name} - {self.plan.name}"

