"""Crystal lead ingestion + WhatsApp analytics helpers."""

from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone

from .models import CrystalLead


def parse_submitted_at_ms(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def whatsapp_analytics_for_business(business):
    """
    Aggregates for whatsapp_click events. Uses Sum(quantity) so batched click_count > 1 still counts.
    """
    now = timezone.now()
    wa = CrystalLead.objects.filter(
        business=business,
        lead_type=CrystalLead.LEAD_WHATSAPP_CLICK,
    )

    def sum_qty(qs):
        return qs.aggregate(t=Sum("quantity"))["t"] or 0

    start_90 = now - timedelta(days=90)

    by_day = (
        wa.filter(created_at__gte=start_90)
        .annotate(bucket=TruncDate("created_at"))
        .values("bucket")
        .annotate(clicks=Sum("quantity"))
        .order_by("bucket")
    )
    by_week = (
        wa.filter(created_at__gte=start_90)
        .annotate(bucket=TruncWeek("created_at"))
        .values("bucket")
        .annotate(clicks=Sum("quantity"))
        .order_by("bucket")
    )
    by_month = (
        wa.filter(created_at__gte=start_90)
        .annotate(bucket=TruncMonth("created_at"))
        .values("bucket")
        .annotate(clicks=Sum("quantity"))
        .order_by("bucket")
    )

    def serialize_buckets(qs):
        out = []
        for row in qs:
            b = row["bucket"]
            out.append(
                {
                    "period_start": b.isoformat() if hasattr(b, "isoformat") else str(b),
                    "clicks": row["clicks"] or 0,
                }
            )
        return out

    return {
        "totals": {
            "today": sum_qty(wa.filter(created_at__date=now.date())),
            "last_7_days": sum_qty(wa.filter(created_at__gte=now - timedelta(days=7))),
            "last_30_days": sum_qty(wa.filter(created_at__gte=now - timedelta(days=30))),
            "last_90_days": sum_qty(wa.filter(created_at__gte=start_90)),
        },
        "last_90_days_by_day": serialize_buckets(by_day),
        "last_90_days_by_week": serialize_buckets(by_week),
        "last_90_days_by_month": serialize_buckets(by_month),
    }


def lead_event_counts_by_type(business):
    rows = (
        CrystalLead.objects.filter(business=business)
        .values("lead_type")
        .annotate(events=Count("id"), units=Sum("quantity"))
    )
    return {
        row["lead_type"]: {"events": row["events"], "units": row["units"] or 0}
        for row in rows
    }


def website_analytics_for_business(business):
    """
    Full analytics payload for one website (Crystal leads + WhatsApp aggregates).
    Used by GET /api/businesses/<slug>/analytics/ and the multi-site overview.
    """
    qs = CrystalLead.objects.filter(business=business)
    total_units = qs.aggregate(t=Sum("quantity"))["t"] or 0
    return {
        "business": {
            "slug": business.slug,
            "name": business.name,
        },
        "whatsapp": whatsapp_analytics_for_business(business),
        "leads_by_type": lead_event_counts_by_type(business),
        "totals": {
            "lead_events": qs.count(),
            "units": int(total_units),
        },
        "computed_at": timezone.now().isoformat(),
    }
