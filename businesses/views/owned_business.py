from django.db.models import Prefetch
from rest_framework import status
from rest_framework.response import Response

from businesses.models import Business
from core.record_status import RECORD_STATUS_ACTIVE
from subscriptions.models import Subscription


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

    When ``with_serializer_relations`` is True, loads ``subscriptions`` + ``plan``
    in the same query round-trips (for ``BusinessSerializer`` / detail PATCH responses).

    When ``defer_website_payload`` is True, large JSON on ``BusinessWebsitePayload``
    is not loaded (use with a serializer that omits ``website_theme`` / ``website_content``).
    """
    try:
        qs = Business.objects.filter(slug=slug, owner_id=customer.id)
        if require_active:
            qs = qs.filter(record_status=RECORD_STATUS_ACTIVE)

        qs = qs.select_related("owner")

        if defer_website_payload:
            qs = qs.select_related("website_payload").defer(
                "website_payload__website_content",
                "website_payload__website_theme",
            )
        elif with_serializer_relations:
            qs = qs.select_related("website_payload")

        if with_serializer_relations:
            qs = qs.prefetch_related(
                Prefetch(
                    "subscriptions",
                    queryset=Subscription.objects.select_related("plan").order_by(
                        "-subscription_end_date"
                    ),
                )
            )

        business = qs.get()
    except Business.DoesNotExist:
        return None, Response(
            {"detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return business, None
