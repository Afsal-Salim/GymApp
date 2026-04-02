"""Shared record lifecycle for soft-disable without deleting rows."""

RECORD_STATUS_ACTIVE = "active"
RECORD_STATUS_INACTIVE = "inactive"

RECORD_STATUS_CHOICES = [
    (RECORD_STATUS_ACTIVE, "Active"),
    (RECORD_STATUS_INACTIVE, "Inactive"),
]
