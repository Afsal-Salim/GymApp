from rest_framework import status
from rest_framework.response import Response

from businesses.models import Business
from core.record_status import RECORD_STATUS_ACTIVE


def get_owned_business(customer, slug, *, require_active=True):
    """
    Return (business, None) or (None, 404 Response).

    When ``require_active`` is True (default), inactive (soft-deleted) businesses
    are treated as missing. Use ``require_active=False`` for record-status /
    reactivation flows.
    """
    try:
        qs = Business.objects.filter(slug=slug)
        if require_active:
            qs = qs.filter(record_status=RECORD_STATUS_ACTIVE)
        business = qs.get()
    except Business.DoesNotExist:
        return None, Response(
            {"detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if business.owner_id != customer.id:
        return None, Response(
            {"detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return business, None
