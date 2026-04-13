from rest_framework import status
from rest_framework.response import Response

from businesses.models import Business
from core.record_status import RECORD_STATUS_ACTIVE


def get_owned_business(
    customer,
    slug,
    *,
    require_active=True,
    with_serializer_relations=False,
    defer_website_payload=False,
):
    """
    Return (business, None) or (None, 404 Response).

    When ``require_active`` is True (default), inactive (soft-deleted) businesses
    are treated as missing. Use ``require_active=False`` for record-status /
    reactivation flows.

    When ``with_serializer_relations`` is True, loads ``owner`` and
    ``subscriptions`` + ``plan`` in the same query round-trips (for
    ``BusinessSerializer`` / detail PATCH responses) instead of a follow-up fetch.

    When ``defer_website_payload`` is True, ``website_content`` and ``website_theme``
    are not loaded from the DB (use with a serializer that omits those fields).
    """
    try:
        qs = Business.objects.filter(slug=slug, owner_id=customer.id)
        if require_active:
            qs = qs.filter(record_status=RECORD_STATUS_ACTIVE)
        if with_serializer_relations:
            qs = qs.select_related("owner").prefetch_related("subscriptions__plan")
        if defer_website_payload:
            qs = qs.defer("website_content", "website_theme")
        business = qs.get()
    except Business.DoesNotExist:
        return None, Response(
            {"detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return business, None
