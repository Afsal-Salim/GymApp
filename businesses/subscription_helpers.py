"""Shared helpers for active (non-expired) business subscriptions."""

from django.utils import timezone


def get_active_subscription_for_business(business):
    """
    Latest subscription row whose end date is today or later.
    Prefetches plan + features for serializers.
    """
    today = timezone.now().date()
    return (
        business.subscriptions.filter(subscription_end_date__gte=today)
        .select_related("plan")
        .prefetch_related("plan__features")
        .order_by("-subscription_end_date")
        .first()
    )
