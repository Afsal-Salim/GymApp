from django.db import models

from core.record_status import RECORD_STATUS_ACTIVE, RECORD_STATUS_CHOICES


class SiteEnquiry(models.Model):
    """Public contact form submissions from the marketing home page."""

    ENQUIRY_OPEN = "open"
    ENQUIRY_RESOLVED = "resolved"
    ENQUIRY_STATUS_CHOICES = [
        (ENQUIRY_OPEN, "Open"),
        (ENQUIRY_RESOLVED, "Resolved"),
    ]

    KIND_GENERAL = "general"
    KIND_SERVICE = "service"
    ENQUIRY_KIND_CHOICES = [
        (KIND_GENERAL, "General contact"),
        (KIND_SERVICE, "Service enquiry"),
    ]

    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="10-digit mobile for service enquiries.",
    )
    service_topic = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="What service the visitor is asking about (home page service form).",
    )
    message = models.TextField(max_length=5000)
    enquiry_kind = models.CharField(
        max_length=32,
        choices=ENQUIRY_KIND_CHOICES,
        default=KIND_GENERAL,
        db_index=True,
    )
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
        verbose_name_plural = "Site enquiries"

    def __str__(self) -> str:
        return f"{self.name} <{self.email}> @ {self.created_at:%Y-%m-%d}"


class ClientSupportMessage(models.Model):
    """
    Logged-in customer support request or product feedback (stored + emailed to team).
    """

    KIND_SUPPORT = "support"
    KIND_FEEDBACK = "feedback"
    KIND_CHOICES = [
        (KIND_SUPPORT, "Support"),
        (KIND_FEEDBACK, "Feedback"),
    ]

    SUPPORT_OPEN = "open"
    SUPPORT_IN_PROGRESS = "in_progress"
    SUPPORT_RESOLVED = "resolved"
    SUPPORT_STATUS_CHOICES = [
        (SUPPORT_OPEN, "Open"),
        (SUPPORT_IN_PROGRESS, "In progress"),
        (SUPPORT_RESOLVED, "Resolved"),
    ]

    FEEDBACK_OPEN = "open"
    FEEDBACK_RESOLVED = "resolved"
    FEEDBACK_STATUS_CHOICES = [
        (FEEDBACK_OPEN, "Open"),
        (FEEDBACK_RESOLVED, "Resolved"),
    ]

    customer = models.ForeignKey(
        "authentication.Customer",
        on_delete=models.CASCADE,
        related_name="support_messages",
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, db_index=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField(max_length=5000)
    support_status = models.CharField(
        max_length=20,
        choices=SUPPORT_STATUS_CHOICES,
        blank=True,
        null=True,
        db_index=True,
    )
    feedback_status = models.CharField(
        max_length=20,
        choices=FEEDBACK_STATUS_CHOICES,
        blank=True,
        null=True,
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
        verbose_name = "Client support / feedback"
        verbose_name_plural = "Client support & feedback"

    def save(self, *args, **kwargs):
        if self.kind == self.KIND_SUPPORT:
            if self.feedback_status is not None:
                self.feedback_status = None
            if self.support_status is None:
                self.support_status = self.SUPPORT_OPEN
        elif self.kind == self.KIND_FEEDBACK:
            if self.support_status is not None:
                self.support_status = None
            if self.feedback_status is None:
                self.feedback_status = self.FEEDBACK_OPEN
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.kind} from {self.customer.email} @ {self.created_at:%Y-%m-%d}"
