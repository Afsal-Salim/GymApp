"""Subscription period calculation (stacked renewals)."""

from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Max
from django.utils import timezone

from core.record_status import RECORD_STATUS_ACTIVE


def next_stacked_subscription_dates(business, duration_days: int) -> tuple[date, date]:
    """
    Compute (start_date, end_date) for a new subscription row after a successful payment.

    - If the business already has **active-record** coverage that ends on or after
      **today**, the new period starts the **day after** the latest such end date.
      So two payments on the same day stack: second month follows the first.
    - If there is no prior row or the latest end date is **before today** (lapsed),
      the new period starts **today**.

    **Recharge during free trial:** if the stacking tip is the automatic trial row
    (``payment_id="trial"``), the paid window is anchored to the trial's last day:
    ``start = trial_end + 1 day`` and ``end = trial_end + duration_days`` (e.g. last
    trial day + 28 days for a 28-day plan). Otherwise ``end = start + duration_days``.

    Only rows with ``record_status=active`` are considered when finding the chain tip.
    """
    from subscriptions.trial_subscription import TRIAL_PAYMENT_ID

    today = timezone.now().date()
    latest_end = (
        business.subscriptions.filter(record_status=RECORD_STATUS_ACTIVE).aggregate(
            m=Max("subscription_end_date")
        )["m"]
    )

    if latest_end is None or latest_end < today:
        start = today
        end = start + timedelta(days=duration_days)
        return start, end

    start = latest_end + timedelta(days=1)

    trial_covers_tip = business.subscriptions.filter(
        record_status=RECORD_STATUS_ACTIVE,
        payment_id=TRIAL_PAYMENT_ID,
        subscription_end_date=latest_end,
    ).exists()

    if trial_covers_tip:
        end = latest_end + timedelta(days=duration_days)
    else:
        end = start + timedelta(days=duration_days)
    return start, end
