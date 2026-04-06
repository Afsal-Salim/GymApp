"""Gym image upload limits from active subscription (trial vs paid)."""

from __future__ import annotations

from businesses.subscription_helpers import get_active_subscription_for_business
from subscriptions.trial_subscription import TRIAL_PLAN_NAME

TRIAL_MAX_GYM_IMAGES = 5


def max_gym_images_for_business(business) -> int | None:
    """
    Trial (7-day free trial plan): 5 images total (logo, hero, background, gallery, etc.).
    Any other active plan (Starter, Pro, …): no cap (``None`` in API as ``slots_limit: null``).
    No active subscription: ``0`` (uploads blocked).
    """
    active = get_active_subscription_for_business(business)
    if not active:
        return 0
    if active.plan.name == TRIAL_PLAN_NAME:
        return TRIAL_MAX_GYM_IMAGES
    return None


def count_active_gym_images(business) -> int:
    from assets.models import Asset
    from core.record_status import RECORD_STATUS_ACTIVE

    return Asset.objects.filter(business=business, record_status=RECORD_STATUS_ACTIVE).count()
