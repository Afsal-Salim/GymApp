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

    ``end_date`` uses the same rule as payment verify: ``start + duration_days``
    (matches existing ``Plan.duration`` semantics).

    Only rows with ``record_status=active`` are considered when finding the chain tip.
    """
    today = timezone.now().date()
    latest_end = (
        business.subscriptions.filter(record_status=RECORD_STATUS_ACTIVE).aggregate(
            m=Max("subscription_end_date")
        )["m"]
    )

    if latest_end is None or latest_end < today:
        start = today
    else:
        start = latest_end + timedelta(days=1)

    end = start + timedelta(days=duration_days)
    return start, end
