from django.db import models

from authentication.models import Customer
from core.record_status import RECORD_STATUS_ACTIVE, RECORD_STATUS_CHOICES


class BusinessEnquiry(models.Model):
    """Contact / enquiry form tied to a specific business (public gym page)."""

    ENQUIRY_OPEN = "open"
    ENQUIRY_RESOLVED = "resolved"
    ENQUIRY_STATUS_CHOICES = [
        (ENQUIRY_OPEN, "Open"),
        (ENQUIRY_RESOLVED, "Resolved"),
    ]

    business = models.ForeignKey(
        "Business",
        on_delete=models.CASCADE,
        related_name="enquiries",
    )
    name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField(max_length=5000)
    enquiry_status = models.CharField(
        max_length=16,
        choices=ENQUIRY_STATUS_CHOICES,
        default=ENQUIRY_OPEN,
        db_index=True,
    )
    record_status = models.CharField(
        max_length=16,
        choices=RECORD_STATUS_CHOICES,
        default=RECORD_STATUS_ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} → {self.business.slug}"


class Business(models.Model):
    owner = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="businesses")
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    location_map_url = models.URLField(max_length=2000, blank=True)
    website_theme = models.JSONField(default=dict, blank=True)
    website_content = models.JSONField(default=dict, blank=True)
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


class CrystalLead(models.Model):
    """
    Public lead / event capture (Crystal modals + WhatsApp taps).
    Store each POST as one row; use `quantity` for WhatsApp when click_count > 1.
    """

    LEAD_JOIN_NOW = "join_now"
    LEAD_BOOK_FREE_TRIAL = "book_free_trial"
    LEAD_PLAN_VISIT = "plan_visit"
    LEAD_WHATSAPP_CLICK = "whatsapp_click"
    LEAD_TYPE_CHOICES = [
        (LEAD_JOIN_NOW, "Join now"),
        (LEAD_BOOK_FREE_TRIAL, "Book free trial"),
        (LEAD_PLAN_VISIT, "Plan your visit"),
        (LEAD_WHATSAPP_CLICK, "WhatsApp click"),
    ]

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="crystal_leads",
    )
    lead_type = models.CharField(
        max_length=32,
        choices=LEAD_TYPE_CHOICES,
        db_index=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    submitted_at_ms = models.BigIntegerField(null=True, blank=True)
    quantity = models.PositiveSmallIntegerField(
        default=1,
        help_text="Usually 1; for whatsapp_click equals click_count (capped).",
    )
    record_status = models.CharField(
        max_length=16,
        choices=RECORD_STATUS_CHOICES,
        default=RECORD_STATUS_ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "lead_type", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.lead_type} @ {self.business.slug} ({self.created_at})"
