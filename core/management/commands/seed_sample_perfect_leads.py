"""
Insert 10 realistic **modal** CrystalLead rows on a single business (slug ``sample`` by default)
for one owner — full payloads (name, phone, email, message, type-specific fields), min/mid/max lengths.
All 10 appear on ``GET /api/businesses/<slug>/crystal-leads/`` (join_now, book_free_trial, plan_visit).

Usage:
  python manage.py seed_sample_perfect_leads
  python manage.py seed_sample_perfect_leads --email=... --slug=sample --purge
"""
from __future__ import annotations

import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from authentication.models import Customer
from businesses.models import Business, CrystalLead
from core.record_status import RECORD_STATUS_ACTIVE

SEED_FLAG = "seed_perfect_sample"

# Align with model / typical forms
NAME_MAX = 200
MSG_MAX = 5000


def _ms_days_ago(days: float) -> int:
    return int((timezone.now() - timedelta(days=days)).timestamp() * 1000)


class Command(BaseCommand):
    help = "Seed 10 perfect modal Crystal leads (join_now, book_free_trial, plan_visit) on one slug."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            default="afsalsalim564@gmail.com",
            help="Owner customer email.",
        )
        parser.add_argument(
            "--slug",
            type=str,
            default="sample",
            help="Business slug (no leading slash).",
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Remove prior rows with this seed flag on this business before insert.",
        )

    def _purge(self, business: Business) -> None:
        n, _ = CrystalLead.objects.filter(
            business=business,
            **{f"payload__{SEED_FLAG}": True},
        ).delete()
        self.stdout.write(f"  Purged {n} prior seed_perfect_sample leads.")

    def _spread(self, business: Business) -> None:
        qs = CrystalLead.objects.filter(
            business=business,
            **{f"payload__{SEED_FLAG}": True},
        ).only("pk", "created_at", "updated_at")
        rows = list(qs)
        for i, obj in enumerate(rows):
            obj.created_at = timezone.now() - timedelta(
                days=14 - i, hours=random.randint(0, 20), minutes=random.randint(0, 59)
            )
            obj.updated_at = obj.created_at + timedelta(minutes=random.randint(1, 90))
        if rows:
            CrystalLead.objects.bulk_update(rows, ["created_at", "updated_at"])

    def handle(self, *args, **options):
        email = (options["email"] or "").strip()
        slug = (options["slug"] or "").strip().lstrip("/")
        if not email or not slug:
            raise CommandError("--email and --slug required.")

        customer = Customer.objects.filter(email__iexact=email).first()
        if not customer:
            raise CommandError(f"No customer with email: {email}")

        business = (
            Business.objects.filter(
                owner=customer,
                slug=slug,
                record_status=RECORD_STATUS_ACTIVE,
            )
            .first()
        )
        if not business:
            raise CommandError(
                f"No active business with slug {slug!r} for {email}. "
                "Create the site or fix the slug."
            )

        if options["purge"]:
            self._purge(business)

        base_email_short = "a@b.co"
        base_email_long = f"{'n' * 200}@ex.co"  # valid shape, long local part
        name_min = "Z"
        name_mid = "Jordan Rivera-Smith"
        name_max = "N" * NAME_MAX
        phone_min = "1000000000"
        phone_mid = "9876543210"
        phone_max = "9999999999"
        msg_min = "OK"
        msg_mid = (
            "I would like to schedule a tour next week after 5pm on weekdays. "
            "Please confirm availability."
        )
        msg_max = "W" * MSG_MAX

        leads: list[CrystalLead] = []

        def wrap(extra: dict) -> dict:
            return {**extra, SEED_FLAG: True, "business_slug": slug}

        # 1–3 join_now: min / mid / max-ish
        leads.append(
            CrystalLead(
                business=business,
                lead_type=CrystalLead.LEAD_JOIN_NOW,
                payload=wrap(
                    {
                        "lead_type": CrystalLead.LEAD_JOIN_NOW,
                        "name": name_min,
                        "phone": phone_min,
                        "email": base_email_short,
                        "message": msg_min,
                        "focus": "X",
                        "frequency": "1",
                        "submitted_at_ms": _ms_days_ago(13.5),
                    }
                ),
                submitted_at_ms=_ms_days_ago(13.5),
                quantity=1,
                record_status=RECORD_STATUS_ACTIVE,
            )
        )
        leads.append(
            CrystalLead(
                business=business,
                lead_type=CrystalLead.LEAD_JOIN_NOW,
                payload=wrap(
                    {
                        "lead_type": CrystalLead.LEAD_JOIN_NOW,
                        "name": name_mid,
                        "phone": phone_mid,
                        "email": "jordan.rivera@example.com",
                        "message": msg_mid,
                        "focus": "Strength & conditioning",
                        "frequency": "4–5 days per week",
                        "submitted_at_ms": _ms_days_ago(11.0),
                    }
                ),
                submitted_at_ms=_ms_days_ago(11.0),
                quantity=1,
                record_status=RECORD_STATUS_ACTIVE,
            )
        )
        leads.append(
            CrystalLead(
                business=business,
                lead_type=CrystalLead.LEAD_JOIN_NOW,
                payload=wrap(
                    {
                        "lead_type": CrystalLead.LEAD_JOIN_NOW,
                        "name": name_max,
                        "phone": phone_max,
                        "email": base_email_long,
                        "message": msg_max,
                        "focus": "F" * 500,
                        "frequency": "Daily morning sessions preferred " * 20,
                        "submitted_at_ms": _ms_days_ago(9.2),
                    }
                ),
                submitted_at_ms=_ms_days_ago(9.2),
                quantity=1,
                record_status=RECORD_STATUS_ACTIVE,
            )
        )

        # 4–6 book_free_trial
        leads.append(
            CrystalLead(
                business=business,
                lead_type=CrystalLead.LEAD_BOOK_FREE_TRIAL,
                payload=wrap(
                    {
                        "lead_type": CrystalLead.LEAD_BOOK_FREE_TRIAL,
                        "name": name_min,
                        "phone": phone_min,
                        "email": base_email_short,
                        "message": msg_min,
                        "visit_when": "2026-04-02 at 09:00",
                        "interests": ["x"],
                        "notes": "Y",
                        "submitted_at_ms": _ms_days_ago(8.0),
                    }
                ),
                submitted_at_ms=_ms_days_ago(8.0),
                quantity=1,
                record_status=RECORD_STATUS_ACTIVE,
            )
        )
        leads.append(
            CrystalLead(
                business=business,
                lead_type=CrystalLead.LEAD_BOOK_FREE_TRIAL,
                payload=wrap(
                    {
                        "lead_type": CrystalLead.LEAD_BOOK_FREE_TRIAL,
                        "name": name_mid,
                        "phone": phone_mid,
                        "email": "trial.user@example.org",
                        "message": msg_mid,
                        "visit_when": "2026-04-05 at 18:30 (time flexible)",
                        "interests": ["HIIT", "Free weights", "Recovery zone"],
                        "notes": "First time at this gym; need parking info.",
                        "submitted_at_ms": _ms_days_ago(6.5),
                    }
                ),
                submitted_at_ms=_ms_days_ago(6.5),
                quantity=1,
                record_status=RECORD_STATUS_ACTIVE,
            )
        )
        leads.append(
            CrystalLead(
                business=business,
                lead_type=CrystalLead.LEAD_BOOK_FREE_TRIAL,
                payload=wrap(
                    {
                        "lead_type": CrystalLead.LEAD_BOOK_FREE_TRIAL,
                        "name": name_max,
                        "phone": phone_max,
                        "email": base_email_long,
                        "message": msg_max,
                        "visit_when": "2026-04-10 at 07:00",
                        "interests": ["Cardio", "Yoga"] * 15,
                        "notes": "N" * MSG_MAX,
                        "submitted_at_ms": _ms_days_ago(5.0),
                    }
                ),
                submitted_at_ms=_ms_days_ago(5.0),
                quantity=1,
                record_status=RECORD_STATUS_ACTIVE,
            )
        )

        # 7–9 plan_visit (same contact keys + visit-specific)
        leads.append(
            CrystalLead(
                business=business,
                lead_type=CrystalLead.LEAD_PLAN_VISIT,
                payload=wrap(
                    {
                        "lead_type": CrystalLead.LEAD_PLAN_VISIT,
                        "name": name_min,
                        "phone": phone_min,
                        "email": base_email_short,
                        "message": msg_min,
                        "preferred_date": "2026-04-03",
                        "visit_notes": "P",
                        "party_size": 1,
                        "submitted_at_ms": _ms_days_ago(4.0),
                    }
                ),
                submitted_at_ms=_ms_days_ago(4.0),
                quantity=1,
                record_status=RECORD_STATUS_ACTIVE,
            )
        )
        leads.append(
            CrystalLead(
                business=business,
                lead_type=CrystalLead.LEAD_PLAN_VISIT,
                payload=wrap(
                    {
                        "lead_type": CrystalLead.LEAD_PLAN_VISIT,
                        "name": name_mid,
                        "phone": phone_mid,
                        "email": "visit.plan@example.net",
                        "message": msg_mid,
                        "preferred_date": "2026-04-08",
                        "visit_notes": "Bringing a friend; interested in family plans.",
                        "party_size": 2,
                        "submitted_at_ms": _ms_days_ago(3.0),
                    }
                ),
                submitted_at_ms=_ms_days_ago(3.0),
                quantity=1,
                record_status=RECORD_STATUS_ACTIVE,
            )
        )
        leads.append(
            CrystalLead(
                business=business,
                lead_type=CrystalLead.LEAD_PLAN_VISIT,
                payload=wrap(
                    {
                        "lead_type": CrystalLead.LEAD_PLAN_VISIT,
                        "name": name_max,
                        "phone": phone_max,
                        "email": base_email_long,
                        "message": msg_max,
                        "preferred_date": "2026-04-12",
                        "visit_notes": "V" * 2000,
                        "party_size": 5,
                        "submitted_at_ms": _ms_days_ago(2.0),
                    }
                ),
                submitted_at_ms=_ms_days_ago(2.0),
                quantity=1,
                record_status=RECORD_STATUS_ACTIVE,
            )
        )

        # 10 join_now — balanced “perfect” row (all keys filled, typical lengths)
        leads.append(
            CrystalLead(
                business=business,
                lead_type=CrystalLead.LEAD_JOIN_NOW,
                payload=wrap(
                    {
                        "lead_type": CrystalLead.LEAD_JOIN_NOW,
                        "name": "Priya Nair",
                        "phone": "9988776655",
                        "email": "priya.nair.work@example.com",
                        "message": (
                            "Moving to the area next month. Want full access plus "
                            "one PT intro session — please share fees and joining offer."
                        ),
                        "focus": "Fat loss and mobility",
                        "frequency": "3 evenings per week",
                        "submitted_at_ms": _ms_days_ago(1.0),
                    }
                ),
                submitted_at_ms=_ms_days_ago(1.0),
                quantity=1,
                record_status=RECORD_STATUS_ACTIVE,
            )
        )

        with transaction.atomic():
            CrystalLead.objects.bulk_create(leads)

        self._spread(business)
        self.stdout.write(
            self.style.SUCCESS(
                f"Inserted {len(leads)} leads on {slug!r} for {email}. "
                f"Use --purge to replace this batch."
            )
        )
