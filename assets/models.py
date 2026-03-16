from django.db import models

from businesses.models import Business


class Asset(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="assets")
    image_url = models.URLField()
    asset_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.business.name} - {self.asset_type}"

