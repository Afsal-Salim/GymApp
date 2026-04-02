"""Query helpers for non-deleted (active) business rows."""

from businesses.models import Business
from core.record_status import RECORD_STATUS_ACTIVE


def active_businesses():
    """Businesses that are not soft-deleted (``record_status=active``)."""
    return Business.objects.filter(record_status=RECORD_STATUS_ACTIVE)
