"""Crystal lead ingestion + WhatsApp analytics helpers."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncHour, TruncMonth, TruncWeek
from django.utils import timezone

from .models import CrystalLead

# Line-chart presets: min 1 day, max 3 months (90 days).
ANALYTICS_RANGE_PRESETS: dict[str, timedelta] = {
    "1d": timedelta(days=1),
    "3d": timedelta(days=3),
    "5d": timedelta(days=5),
    "10d": timedelta(days=10),
    "1m": timedelta(days=30),
    "3m": timedelta(days=90),
}

ANALYTICS_RANGE_LABELS: dict[str, str] = {
    "1d": "1 day",
    "3d": "3 days",
    "5d": "5 days",
    "10d": "10 days",
    "1m": "1 month",
    "3m": "3 months",
}

DEFAULT_ANALYTICS_RANGE = "10d"


def resolve_analytics_preset(raw: str | None) -> tuple[str | None, list[str]]:
    """
    Returns (preset_key, allowed_keys). preset_key is None if invalid.
    Empty/missing raw → default ``10d``.
    """
    allowed = sorted(ANALYTICS_RANGE_PRESETS.keys())
    if raw is None or not str(raw).strip():
        return DEFAULT_ANALYTICS_RANGE, allowed
    key = str(raw).strip().lower()
    if key not in ANALYTICS_RANGE_PRESETS:
        return None, allowed
    return key, allowed


def _utc(dt):
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone()).astimezone(dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc)


def _iter_hour_buckets(start, end):
    t = _utc(start).replace(minute=0, second=0, microsecond=0)
    end_u = _utc(end).replace(minute=0, second=0, microsecond=0)
    while t <= end_u:
        yield t
        t += timedelta(hours=1)


def _iter_day_buckets(start, end):
    d = _utc(start).date()
    end_d = _utc(end).date()
    while d <= end_d:
        yield d
        d += timedelta(days=1)


def _normalize_bucket_key(bucket, hourly: bool):
    if bucket is None:
        return None
    if hourly:
        if isinstance(bucket, datetime):
            return _utc(bucket).replace(minute=0, second=0, microsecond=0)
        return bucket
    if hasattr(bucket, "isoformat") and not isinstance(bucket, datetime):
        return bucket
    if isinstance(bucket, datetime):
        return _utc(bucket).date()
    return bucket


def line_graph_series_for_business(business, preset: str):
    """
    Time series for line charts: one point per hour (1d) or per day (other presets).
    Missing buckets are zero-filled for continuous axes.
    """
    now = timezone.now()
    delta = ANALYTICS_RANGE_PRESETS[preset]
    start = now - delta
    hourly = preset == "1d"

    qs = CrystalLead.objects.filter(
        business=business,
        created_at__gte=start,
        created_at__lte=now,
    )

    if hourly:
        rows = (
            qs.annotate(bucket=TruncHour("created_at"))
            .values("bucket", "lead_type")
            .annotate(events=Count("id"), units=Sum("quantity"))
            .order_by("bucket", "lead_type")
        )
    else:
        rows = (
            qs.annotate(bucket=TruncDate("created_at"))
            .values("bucket", "lead_type")
            .annotate(events=Count("id"), units=Sum("quantity"))
            .order_by("bucket", "lead_type")
        )

    agg: dict = defaultdict(
        lambda: {"events": 0, "units": 0, "by_lead_type": defaultdict(int)}
    )
    for row in rows:
        b = _normalize_bucket_key(row["bucket"], hourly)
        if b is None:
            continue
        lt = row["lead_type"]
        ev = row["events"] or 0
        u = row["units"] or 0
        agg[b]["events"] += ev
        agg[b]["units"] += u
        agg[b]["by_lead_type"][lt] += u

    if hourly:
        all_keys = list(_iter_hour_buckets(start, now))
    else:
        all_keys = list(_iter_day_buckets(start, now))

    known = set(agg.keys())
    ordered = sorted(set(all_keys) | known)

    out = []
    for k in ordered:
        cell = agg.get(k)
        if cell is None:
            events, units, by_lt = 0, 0, {}
        else:
            events = cell["events"]
            units = cell["units"]
            by_lt = dict(cell["by_lead_type"])
        if hourly:
            ps = k.isoformat()
        else:
            ps = k.isoformat() if hasattr(k, "isoformat") else str(k)
        out.append(
            {
                "period_start": ps,
                "events": events,
                "units": units,
                "by_lead_type": by_lt,
            }
        )
    return out, start, now


def lead_event_counts_by_type_in_range(business, start, end):
    rows = (
        CrystalLead.objects.filter(
            business=business,
            created_at__gte=start,
            created_at__lte=end,
        )
        .values("lead_type")
        .annotate(events=Count("id"), units=Sum("quantity"))
    )
    return {
        row["lead_type"]: {"events": row["events"], "units": row["units"] or 0}
        for row in rows
    }


def totals_in_range(business, start, end):
    qs = CrystalLead.objects.filter(
        business=business,
        created_at__gte=start,
        created_at__lte=end,
    )
    total_units = qs.aggregate(t=Sum("quantity"))["t"] or 0
    return {
        "lead_events": qs.count(),
        "units": int(total_units),
    }


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


def website_analytics_for_business(business, range_preset: str = DEFAULT_ANALYTICS_RANGE):
    """
    Full analytics payload for one website (Crystal leads + WhatsApp aggregates).
    Used by GET /api/businesses/<slug>/analytics/ and the multi-site overview.

    ``range_preset`` must be a key in ANALYTICS_RANGE_PRESETS (1d–3m). Drives
    ``line_graph``, ``totals_in_range``, and ``leads_by_type_in_range``.
    """
    preset = range_preset if range_preset in ANALYTICS_RANGE_PRESETS else DEFAULT_ANALYTICS_RANGE
    line_graph, range_start, range_end = line_graph_series_for_business(business, preset)

    qs = CrystalLead.objects.filter(business=business)
    total_units = qs.aggregate(t=Sum("quantity"))["t"] or 0

    return {
        "business": {
            "slug": business.slug,
            "name": business.name,
        },
        "time_range": {
            "preset": preset,
            "label": ANALYTICS_RANGE_LABELS.get(preset, preset),
            "start": range_start.isoformat(),
            "end": range_end.isoformat(),
            "bucket": "hour" if preset == "1d" else "day",
            "allowed_presets": sorted(ANALYTICS_RANGE_PRESETS.keys()),
        },
        "line_graph": line_graph,
        "totals_in_range": totals_in_range(business, range_start, range_end),
        "leads_by_type_in_range": lead_event_counts_by_type_in_range(
            business, range_start, range_end
        ),
        "whatsapp": whatsapp_analytics_for_business(business),
        "leads_by_type": lead_event_counts_by_type(business),
        "totals": {
            "lead_events": qs.count(),
            "units": int(total_units),
        },
        "computed_at": timezone.now().isoformat(),
    }
