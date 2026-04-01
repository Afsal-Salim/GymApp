from django.db import models


class SiteEnquiry(models.Model):
    """Public contact form submissions from the marketing home page."""

    name = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)

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

    customer = models.ForeignKey(
        "authentication.Customer",
        on_delete=models.CASCADE,
        related_name="support_messages",
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, db_index=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Client support / feedback"
        verbose_name_plural = "Client support & feedback"

    def __str__(self) -> str:
        return f"{self.kind} from {self.customer.email} @ {self.created_at:%Y-%m-%d}"
