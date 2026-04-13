"""Shared helpers for active (non-expired) business subscriptions."""

from django.db.models import Prefetch
from django.utils import timezone

from core.record_status import RECORD_STATUS_ACTIVE
from plans.models import Feature


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
    features = [{"id": f.id, "name": f.name} for f in plan.features.all()]
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
    Prefetches plan + active features in one go (avoids N+1 and loads fewer rows).
    """
    today = timezone.now().date()
    return (
        business.subscriptions.filter(
            subscription_end_date__gte=today,
            record_status=RECORD_STATUS_ACTIVE,
        )
        .select_related("plan")
        .prefetch_related(
            Prefetch(
                "plan__features",
                queryset=Feature.objects.filter(
                    record_status=RECORD_STATUS_ACTIVE
                ).order_by("id"),
            )
        )
        .order_by("-subscription_end_date")
        .first()
    )


def get_active_public_subscription_for_slug(slug: str):
    """
    Resolve active subscription for the **public** ``active-subscription`` API with minimal queries.

    Returns ``(subscription | None, not_found)``:
    - ``not_found`` is True when no **active** business exists for ``slug`` (HTTP 404).
    - Otherwise ``not_found`` is False; ``subscription`` is None when the gym exists but has no
      qualifying active subscription (HTTP 200 empty body).

    When ``subscription`` is not None, ``plan`` and active ``plan.features`` are prefetched.
    """
    from businesses.models import Business
    from subscriptions.models import Subscription

    today = timezone.now().date()
    sub = (
        Subscription.objects.filter(
            business__slug=slug,
            business__record_status=RECORD_STATUS_ACTIVE,
            subscription_end_date__gte=today,
            record_status=RECORD_STATUS_ACTIVE,
        )
        .select_related("plan", "business")
        .prefetch_related(
            Prefetch(
                "plan__features",
                queryset=Feature.objects.filter(
                    record_status=RECORD_STATUS_ACTIVE
                ).order_by("id"),
            )
        )
        .order_by("-subscription_end_date")
        .first()
    )
    if sub is not None:
        return sub, False
    if not Business.objects.filter(
        slug=slug, record_status=RECORD_STATUS_ACTIVE
    ).exists():
        return None, True
    return None, False
