from django.db import models


class Plan(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    duration = models.PositiveIntegerField(help_text="Duration of plan in days")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Feature(models.Model):
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name="features"
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name

