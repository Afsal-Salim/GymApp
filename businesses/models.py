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
            # Owner list: WHERE business_id = ? AND record_status = ? ORDER BY created_at DESC
            models.Index(
                fields=["business", "record_status", "-created_at"],
                name="biz_enquiry_biz_rs_crt_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} → {self.business.slug}"


class Business(models.Model):
    """
    Core gym row (identity, contact, status). Heavy Crystal builder JSON lives in
    :class:`BusinessWebsitePayload` so list/join queries avoid loading megabytes of JSON.
    """

    owner = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="businesses")
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    phone = models.CharField(
        max_length=10,
        blank=True,
        help_text="10-digit mobile number (no spaces or country code stored).",
    )
    address = models.TextField(blank=True)
    location_map_url = models.URLField(max_length=2000, blank=True)
    logo_s3_key = models.CharField(
        max_length=1024,
        blank=True,
        default="",
        help_text="S3 object key for owner-uploaded logo (logos/<slug>/<uuid>.ext). Empty if using website_content only.",
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
        indexes = [
            models.Index(
                fields=["owner", "record_status"],
                name="business_owner_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class BusinessWebsitePayload(models.Model):
    """
    Crystal website theme + content (large JSON). One row per business; optional so
    legacy code paths can use ``get_or_create``. API responses still expose
    ``website_theme`` / ``website_content`` on the business object via serializers.
    """

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="website_payload",
    )
    website_theme = models.JSONField(default=dict, blank=True)
    website_content = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"WebsitePayload({self.business.slug})"


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
            # Range filters for analytics: WHERE business_id = ? AND created_at >= ? AND created_at <= ?
            models.Index(
                fields=["business", "created_at"],
                name="crystallead_biz_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.lead_type} @ {self.business.slug} ({self.created_at})"
