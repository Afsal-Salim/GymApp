"""
Seed analytics-style demo rows for one real customer, only on their **active** businesses.

Creates:
  - 500 BusinessEnquiry (public gym page enquiries)
  - 100 ClientSupportMessage (kind=support) for that customer
  - 500 CrystalLead: join_now, book_free_trial, plan_visit (167 / 167 / 166)
  - 1000 CrystalLead whatsapp_click

Timestamps are spread over the last 90 days.

Usage:
  python manage.py seed_owner_demo --email=afsalsalim564@gmail.com
  python manage.py seed_owner_demo --email=... --purge   # remove prior seed rows for this owner, then insert
"""
from __future__ import annotations

import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from authentication.models import Customer
from businesses.models import Business, BusinessEnquiry, CrystalLead
from core.models import ClientSupportMessage
from core.record_status import RECORD_STATUS_ACTIVE

SEED_ENQUIRY_EMAIL_PREFIX = "seedownereq-"
SEED_SUPPORT_SUBJECT_PREFIX = "seed-owner-support-"
SEED_PAYLOAD_KEY = "seed_owner_demo"


class Command(BaseCommand):
    help = "Seed enquiries, support, and Crystal leads for one owner's active websites only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            default="afsalsalim564@gmail.com",
            help="Customer email (must exist).",
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Delete prior rows marked with this seed for this owner before inserting.",
        )

    def _rand_dt(self, days_back: int = 90):
        return timezone.now() - timedelta(
            seconds=random.randint(0, max(1, days_back) * 86400)
        )

    def _purge(self, customer: Customer) -> None:
        self.stdout.write("Purging prior seed_owner_demo rows for this customer…")
        biz_ids = list(
            Business.objects.filter(owner=customer).values_list("pk", flat=True)
        )
        if not biz_ids:
            self.stdout.write("  No businesses to purge against.")
            return
        n_enq = BusinessEnquiry.objects.filter(
            business_id__in=biz_ids,
            email__startswith=SEED_ENQUIRY_EMAIL_PREFIX,
        ).delete()[0]
        n_sup = ClientSupportMessage.objects.filter(
            customer=customer,
            subject__startswith=SEED_SUPPORT_SUBJECT_PREFIX,
        ).delete()[0]
        n_lead = CrystalLead.objects.filter(
            business_id__in=biz_ids,
            **{f"payload__{SEED_PAYLOAD_KEY}": True},
        ).delete()[0]
        self.stdout.write(
            f"  Deleted {n_enq} business enquiries, {n_sup} support messages, {n_lead} crystal leads."
        )

    def _spread_timestamps(self, businesses: list[Business], customer: Customer) -> None:
        self.stdout.write("  Randomizing timestamps (last 90 days)…")

        def spread_qs(qs, batch: int = 500):
            rows = list(qs.only("pk", "created_at", "updated_at"))
            for obj in rows:
                obj.created_at = self._rand_dt(90)
                obj.updated_at = obj.created_at + timedelta(
                    minutes=random.randint(0, 120)
                )
            qs.model.objects.bulk_update(
                rows, ["created_at", "updated_at"], batch_size=batch
            )

        biz_ids = [b.pk for b in businesses]
        spread_qs(
            BusinessEnquiry.objects.filter(
                business_id__in=biz_ids,
                email__startswith=SEED_ENQUIRY_EMAIL_PREFIX,
            )
        )
        spread_qs(
            ClientSupportMessage.objects.filter(
                customer=customer,
                subject__startswith=SEED_SUPPORT_SUBJECT_PREFIX,
            )
        )
        spread_qs(
            CrystalLead.objects.filter(
                business_id__in=biz_ids,
                **{f"payload__{SEED_PAYLOAD_KEY}": True},
            ),
            batch=400,
        )
        self.stdout.write("  Timestamps updated.")

    def handle(self, *args, **options):
        email = (options["email"] or "").strip()
        if not email:
            raise CommandError("--email is required.")

        customer = Customer.objects.filter(email__iexact=email).first()
        if not customer:
            raise CommandError(f"No customer with email: {email}")

        businesses = list(
            Business.objects.filter(
                owner=customer,
                record_status=RECORD_STATUS_ACTIVE,
            )
        )
        if not businesses:
            raise CommandError(
                f"No active businesses (record_status={RECORD_STATUS_ACTIVE!r}) for {email}."
            )

        if options["purge"]:
            self._purge(customer)

        seed_marker = {SEED_PAYLOAD_KEY: True}

        with transaction.atomic():
            enquiries: list[BusinessEnquiry] = []
            for i in range(500):
                b = businesses[i % len(businesses)]
                enquiries.append(
                    BusinessEnquiry(
                        business=b,
                        name=f"Demo visitor {i:04d}",
                        email=f"{SEED_ENQUIRY_EMAIL_PREFIX}{i:05d}@example.test",
                        message=f"Seeded business-page enquiry #{i} for analytics.",
                        enquiry_status=random.choice(
                            [
                                BusinessEnquiry.ENQUIRY_OPEN,
                                BusinessEnquiry.ENQUIRY_RESOLVED,
                            ]
                        ),
                        record_status=RECORD_STATUS_ACTIVE,
                    )
                )
            BusinessEnquiry.objects.bulk_create(enquiries, batch_size=250)
            self.stdout.write(f"  Created {len(enquiries)} business enquiries.")

            support_rows: list[ClientSupportMessage] = []
            for i in range(100):
                support_rows.append(
                    ClientSupportMessage(
                        customer=customer,
                        kind=ClientSupportMessage.KIND_SUPPORT,
                        subject=f"{SEED_SUPPORT_SUBJECT_PREFIX}{i:04d}",
                        message=f"Seeded support request #{i} for dashboard testing.",
                        support_status=random.choice(
                            [
                                ClientSupportMessage.SUPPORT_OPEN,
                                ClientSupportMessage.SUPPORT_IN_PROGRESS,
                                ClientSupportMessage.SUPPORT_RESOLVED,
                            ]
                        ),
                        feedback_status=None,
                        record_status=RECORD_STATUS_ACTIVE,
                    )
                )
            ClientSupportMessage.objects.bulk_create(support_rows, batch_size=100)
            self.stdout.write(f"  Created {len(support_rows)} support messages.")

            lead_objs: list[CrystalLead] = []
            modal_types = [
                (CrystalLead.LEAD_JOIN_NOW, 167),
                (CrystalLead.LEAD_BOOK_FREE_TRIAL, 167),
                (CrystalLead.LEAD_PLAN_VISIT, 166),
            ]
            for lead_type, count in modal_types:
                for _ in range(count):
                    b = random.choice(businesses)
                    lead_objs.append(
                        CrystalLead(
                            business=b,
                            lead_type=lead_type,
                            payload={
                                **seed_marker,
                                "lead_type": lead_type,
                            },
                            quantity=1,
                            record_status=RECORD_STATUS_ACTIVE,
                        )
                    )

            for _ in range(1000):
                b = random.choice(businesses)
                lead_objs.append(
                    CrystalLead(
                        business=b,
                        lead_type=CrystalLead.LEAD_WHATSAPP_CLICK,
                        payload=seed_marker,
                        quantity=random.randint(1, 5),
                        record_status=RECORD_STATUS_ACTIVE,
                    )
                )

            CrystalLead.objects.bulk_create(lead_objs, batch_size=500)
            self.stdout.write(
                f"  Created {len(lead_objs)} crystal leads (500 modal + 1000 whatsapp)."
            )

        self._spread_timestamps(businesses, customer)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done for {email}: {len(businesses)} active site(s); "
                "use --purge before re-running to avoid duplicate counts."
            )
        )
