from django.db import models


class Plan(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.PositiveIntegerField(help_text="Duration of plan in days")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name

