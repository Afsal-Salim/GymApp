"""Shared helpers for active (non-expired) business subscriptions."""

from django.utils import timezone

from core.record_status import RECORD_STATUS_ACTIVE


def get_active_subscription_for_business(business):
    """
    Latest **active** subscription row whose end date is today or later.
    Prefetches plan + features for serializers.
    """
    today = timezone.now().date()
    return (
        business.subscriptions.filter(
            subscription_end_date__gte=today,
            record_status=RECORD_STATUS_ACTIVE,
        )
        .select_related("plan")
        .prefetch_related("plan__features")
        .order_by("-subscription_end_date")
        .first()
    )
