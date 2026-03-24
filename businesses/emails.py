"""Owner notifications for Crystal leads."""

import re
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone as django_timezone

from core.logging import app_logger

from .models import CrystalLead


def _format_timestamp_ms(ms) -> str | None:
    """Turn epoch milliseconds into a readable local datetime string."""
    try:
        v = int(ms)
    except (TypeError, ValueError):
        return None
    # Heuristic: treat values < year ~2001 in ms as seconds
    if v < 1_000_000_000_000:
        v = v * 1000
    dt = datetime.fromtimestamp(v / 1000.0, tz=dt_timezone.utc)
    if getattr(settings, "USE_TZ", True):
        dt = django_timezone.localtime(dt)
    tz_name = dt.tzname() or ""
    base = dt.strftime("%A, %B %d, %Y at %I:%M %p")
    if tz_name:
        return f"{base} ({tz_name})"
    return base


def _prettify_date_time_string(value: str) -> str:
    """
    Parse common client strings (e.g. '2025-03-24 at 14:30') into readable English.
    Falls back to the original string if parsing fails.
    """
    raw = (value or "").strip()
    if not raw:
        return raw
    if raw.isdigit():
        formatted = _format_timestamp_ms(int(raw))
        return formatted if formatted else raw

    flexible_suffix = ""
    rest = raw
    if re.search(r"time flexible", raw, re.I):
        flexible_suffix = " (time flexible)"
        rest = re.sub(r"\s*\(?\s*time flexible\s*\)?\s*", "", raw, flags=re.I).strip()

    parse_attempts = (
        ("%Y-%m-%d at %H:%M", True),
        ("%Y-%m-%d %H:%M", True),
        ("%d/%m/%Y at %H:%M", True),
        ("%d/%m/%Y %H:%M", True),
        ("%Y-%m-%d", False),
        ("%d/%m/%Y", False),
    )
    for fmt, has_time in parse_attempts:
        try:
            dt = datetime.strptime(rest, fmt)
            if has_time:
                pretty = dt.strftime("%A, %B %d, %Y at %I:%M %p")
            else:
                pretty = dt.strftime("%A, %B %d, %Y")
            return pretty + flexible_suffix
        except ValueError:
            continue

    return raw


def _format_interests(value):
    if isinstance(value, list):
        return ", ".join(str(x) for x in value)
    return str(value) if value is not None else ""


def _build_detail_rows(lead_type: str, payload: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    p = payload or {}

    name = (p.get("name") or "").strip()
    phone = (p.get("phone") or "").strip()
    if name:
        rows.append(("Name", name))
    if phone:
        rows.append(("Phone", phone))

    if lead_type == CrystalLead.LEAD_JOIN_NOW:
        if p.get("focus"):
            rows.append(("Focus", str(p["focus"])))
        if p.get("frequency"):
            rows.append(("Frequency", str(p["frequency"])))
    elif lead_type == CrystalLead.LEAD_BOOK_FREE_TRIAL:
        if p.get("visit_when"):
            rows.append(
                ("Visit when", _prettify_date_time_string(str(p["visit_when"])))
            )
        interests = _format_interests(p.get("interests"))
        if interests:
            rows.append(("Interests", interests))
        notes = (p.get("notes") or "").strip()
        if notes:
            rows.append(("Notes", notes))

    if p.get("submitted_at_ms") is not None:
        ms = p["submitted_at_ms"]
        readable = _format_timestamp_ms(ms)
        rows.append(
            (
                "Submitted at",
                readable if readable else str(ms),
            )
        )

    return rows


def send_crystal_lead_owner_email(business, lead_type: str, payload: dict) -> None:
    if lead_type not in (
        CrystalLead.LEAD_JOIN_NOW,
        CrystalLead.LEAD_BOOK_FREE_TRIAL,
    ):
        return

    owner = getattr(business, "owner", None)
    owner_email = (owner.email if owner else "") or ""
    if not owner_email:
        app_logger.warning(
            "Crystal lead owner email skipped — no owner email",
            business_id=business.id,
            slug=business.slug,
        )
        return

    if lead_type == CrystalLead.LEAD_JOIN_NOW:
        lead_title = "New “Join now” lead"
        subject_prefix = "Join now"
    else:
        lead_title = "New “Book free trial” lead"
        subject_prefix = "Free trial"

    custom = (getattr(settings, "CRYSTAL_LEAD_OWNER_EMAIL_SUBJECT", "") or "").strip()
    subject = custom if custom else f"[GymApp] {subject_prefix} — {business.name}"

    detail_rows = _build_detail_rows(lead_type, payload)
    context = {
        "lead_title": lead_title,
        "lead_type": lead_type,
        "business_name": business.name,
        "business_slug": business.slug,
        "detail_rows": detail_rows,
    }

    html_message = render_to_string("businesses/email_crystal_lead_owner.html", context)
    plain_lines = [
        lead_title,
        f"Business: {business.name} ({business.slug})",
        "",
    ]
    for label, value in detail_rows:
        plain_lines.append(f"{label}: {value}")
    plain_message = "\n".join(plain_lines)

    try:
        sent = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner_email],
            fail_silently=True,
            html_message=html_message,
        )
        if sent < 1:
            app_logger.warning(
                "Crystal lead owner email was not sent (check EMAIL_* / SMTP)",
                business_id=business.id,
                lead_type=lead_type,
                owner_email=owner_email,
            )
        else:
            app_logger.info(
                "Crystal lead owner email sent",
                business_id=business.id,
                lead_type=lead_type,
                owner_email=owner_email,
            )
    except Exception as e:
        app_logger.warning(
            "Crystal lead owner email failed",
            business_id=business.id,
            lead_type=lead_type,
            error=str(e),
        )
