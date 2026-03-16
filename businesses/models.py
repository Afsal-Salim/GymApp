from django.db import models

from authentication.models import Customer


class Business(models.Model):
    owner = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="businesses")
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

