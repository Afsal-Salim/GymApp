"""Automatic trial when a new Business (website) is created."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from core.logging import app_logger
from core.record_status import RECORD_STATUS_ACTIVE

TRIAL_PLAN_NAME = "7-day free trial"
TRIAL_PAYMENT_ID = "trial"


def get_trial_plan():
    from plans.models import Plan

    return (
        Plan.objects.filter(
            name=TRIAL_PLAN_NAME,
            record_status=RECORD_STATUS_ACTIVE,
        )
        .first()
    )


def create_trial_subscription_for_new_business(business):
    from subscriptions.models import Subscription

    if Subscription.objects.filter(business=business).exists():
        return None
    plan = get_trial_plan()
    if not plan:
        app_logger.warning(
            "Trial subscription skipped: trial plan missing",
            business_id=business.pk,
            slug=business.slug,
        )
        return None
    today = timezone.now().date()
    sub = Subscription.objects.create(
        business=business,
        plan=plan,
        payment_id=TRIAL_PAYMENT_ID,
        subscription_start_date=today,
        subscription_end_date=today + timedelta(days=plan.duration),
        record_status=RECORD_STATUS_ACTIVE,
    )
    app_logger.info(
        "Trial subscription created",
        business_id=business.pk,
        slug=business.slug,
        subscription_id=sub.pk,
    )
    return sub


def business_has_non_trial_subscription(business) -> bool:
    """True if any subscription row is not the automatic free trial."""
    from subscriptions.models import Subscription

    return (
        Subscription.objects.filter(business=business)
        .exclude(payment_id=TRIAL_PAYMENT_ID)
        .exists()
    )
