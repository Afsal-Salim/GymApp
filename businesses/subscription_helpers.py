"""Shared helpers for active (non-expired) business subscriptions."""

from django.utils import timezone

from core.record_status import RECORD_STATUS_ACTIVE


def subscription_plan_tier(plan) -> str:
    """
    Coarse plan bucket for APIs: ``trial`` | ``starter`` | ``pro`` | ``other``.
    """
    if not plan:
        return "none"
    from subscriptions.trial_subscription import TRIAL_PLAN_NAME

    name = (plan.name or "").strip()
    if name == TRIAL_PLAN_NAME:
        return "trial"
    low = name.lower()
    if low == "starter":
        return "starter"
    if low == "pro":
        return "pro"
    return "other"


def public_active_subscription_payload(subscription) -> dict:
    """
    JSON-ready detail for the public ``active-subscription`` endpoint (no auth).
    """
    plan = subscription.plan
    tier = subscription_plan_tier(plan)
    features = [
        {"id": f.id, "name": f.name}
        for f in plan.features.all()
        if f.record_status == RECORD_STATUS_ACTIVE
    ]
    return {
        "id": subscription.id,
        "plan_name": plan.name,
        "plan_tier": tier,
        "subscription_start_date": subscription.subscription_start_date.isoformat(),
        "subscription_end_date": subscription.subscription_end_date.isoformat(),
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "tier": tier,
            "duration_days": plan.duration,
            "currency": plan.currency,
            "price": str(plan.price),
            "features": features,
        },
    }


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
