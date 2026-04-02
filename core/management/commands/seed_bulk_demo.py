"""
Bulk demo data for analytics / admin testing.

Creates (by default in one run):
  - 100 customers (bulkdemo_0000@example.test … bulkdemo_0099, password: bulkdemo123)
  - 300 businesses (slugs bulkdemo-biz-0000 …), spread across those owners
  - 500 site enquiries
  - 100 support tickets (ClientSupportMessage, kind=support)
  - 500 CrystalLead rows: join_now, book_free_trial, plan_visit (~167 each)
  - 1000 CrystalLead whatsapp_click rows

Timestamps are randomized over the last 90 days for charts.

Usage:
  python manage.py seed_bulk_demo
  python manage.py seed_bulk_demo --purge   # remove prior bulkdemo_* rows, then seed again
"""
from __future__ import annotations

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from authentication.models import Customer
from businesses.models import Business, CrystalLead
from core.models import ClientSupportMessage, SiteEnquiry
from core.record_status import RECORD_STATUS_ACTIVE

BIZ_SLUG_PREFIX = "bulkdemo-biz-"


class Command(BaseCommand):
    help = "Seed bulk demo users, websites, enquiries, support, and Crystal leads."

    def add_arguments(self, parser):
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Delete existing bulkdemo_* seed rows before inserting.",
        )

    def handle(self, *args, **options):
        purge = options["purge"]
        if purge:
            self._purge()
        self._seed()

    def _purge(self):
        self.stdout.write("Purging prior bulkdemo seed data…")
        demo_customers = Customer.objects.filter(
            email__startswith="bulkdemo_",
            email__endswith="@example.test",
        ).exclude(email__contains="enquiry")
        n_cust = demo_customers.count()
        demo_customers.delete()
        self.stdout.write(f"  Deleted {n_cust} customers (cascaded businesses, leads, support).")
        n_enq = SiteEnquiry.objects.filter(email__startswith="bulkdemo-enquiry-").delete()[0]
        self.stdout.write(f"  Deleted {n_enq} site enquiries.")

    def _rand_dt(self, days_back: int = 90):
        return timezone.now() - timedelta(seconds=random.randint(0, max(1, days_back) * 86400))

    def _seed(self):
        if (
            Business.objects.filter(slug__startswith=BIZ_SLUG_PREFIX).count() >= 300
            and SiteEnquiry.objects.filter(email__startswith="bulkdemo-enquiry-").count()
            >= 500
        ):
            self.stdout.write(
                self.style.WARNING(
                    "Bulk demo seed already present (300+ businesses, 500+ enquiries). "
                    "Run with --purge to remove and recreate."
                )
            )
            return

        pw = Customer.hash_password("bulkdemo123")

        with transaction.atomic():
            customers: list[Customer] = []
            for i in range(100):
                email = f"bulkdemo_{i:04d}@example.test"
                username = f"bulkdemo_{i:04d}"
                c, created = Customer.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": username,
                        "password": pw,
                        "auth_provider": Customer.AUTH_PROVIDER_EMAIL,
                        "record_status": RECORD_STATUS_ACTIVE,
                    },
                )
                if not created and c.username != username:
                    c.username = username
                    c.save(update_fields=["username"])
                if not created and len(c.password) != 64:
                    c.set_password("bulkdemo123")
                    c.save(update_fields=["password"])
                customers.append(c)
            self.stdout.write(f"  Customers ready: {len(customers)}")

            businesses: list[Business] = []
            for i in range(300):
                slug = f"{BIZ_SLUG_PREFIX}{i:04d}"
                owner = customers[i % len(customers)]
                b, created = Business.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "owner": owner,
                        "name": f"Demo Gym {i:04d}",
                        "description": f"Seeded demo business #{i}.",
                        "phone": f"+91 {9000000000 + (i % 99999999):08d}",
                        "address": f"{100 + i} Seed Street, Demo City",
                        "record_status": RECORD_STATUS_ACTIVE,
                    },
                )
                businesses.append(b)
            self.stdout.write(f"  Businesses ready: {len(businesses)}")

            enquiries: list[SiteEnquiry] = []
            for i in range(500):
                enquiries.append(
                    SiteEnquiry(
                        name=f"Enquiry Person {i:04d}",
                        email=f"bulkdemo-enquiry-{i:04d}@example.test",
                        message=f"I am interested in Crystal Gym demo message #{i}.",
                        enquiry_status=random.choice(
                            [SiteEnquiry.ENQUIRY_OPEN, SiteEnquiry.ENQUIRY_RESOLVED]
                        ),
                        record_status=RECORD_STATUS_ACTIVE,
                    )
                )
            SiteEnquiry.objects.bulk_create(enquiries, batch_size=250)
            self.stdout.write("  Created 500 site enquiries.")

            support_rows: list[ClientSupportMessage] = []
            for i in range(100):
                cust = customers[i % len(customers)]
                support_rows.append(
                    ClientSupportMessage(
                        customer=cust,
                        kind=ClientSupportMessage.KIND_SUPPORT,
                        subject=f"Support topic {i:04d}",
                        message=f"Please help with demo support request #{i}.",
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
            self.stdout.write("  Created 100 support requests.")

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
                            payload={"seed": True, "lead_type": lead_type},
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
                        payload={"seed": True},
                        quantity=random.randint(1, 5),
                        record_status=RECORD_STATUS_ACTIVE,
                    )
                )

            CrystalLead.objects.bulk_create(lead_objs, batch_size=500)
            self.stdout.write(
                f"  Created {len(lead_objs)} crystal leads (500 modal + 1000 whatsapp)."
            )

        # Spread created_at in separate updates (bulk_create uses DB default "now" for auto_now_add).
        self._spread_timestamps()

        self.stdout.write(
            self.style.SUCCESS(
                "Done. Login any bulkdemo_0000@example.test … bulkdemo_0099 with password bulkdemo123"
            )
        )

    def _spread_timestamps(self):
        self.stdout.write("  Randomizing timestamps (last 90 days)…")

        def spread_qs(qs, batch: int = 500):
            rows = list(qs.only("pk"))
            for obj in rows:
                obj.created_at = self._rand_dt(90)
                obj.updated_at = obj.created_at + timedelta(minutes=random.randint(0, 120))
            type(qs.model).objects.bulk_update(
                rows, ["created_at", "updated_at"], batch_size=batch
            )

        spread_qs(SiteEnquiry.objects.filter(email__startswith="bulkdemo-enquiry-"))
        spread_qs(
            ClientSupportMessage.objects.filter(
                customer__email__startswith="bulkdemo_",
                customer__email__endswith="@example.test",
                kind=ClientSupportMessage.KIND_SUPPORT,
            ).exclude(customer__email__contains="enquiry")
        )
        spread_qs(
            CrystalLead.objects.filter(business__slug__startswith=BIZ_SLUG_PREFIX),
            batch_size=400,
        )

        demo_cust = list(
            Customer.objects.filter(
                email__startswith="bulkdemo_",
                email__endswith="@example.test",
            ).exclude(email__contains="enquiry")
        )
        for c in demo_cust:
            c.created_at = self._rand_dt(120)
            c.updated_at = c.created_at + timedelta(hours=random.randint(1, 48))
        Customer.objects.bulk_update(demo_cust, ["created_at", "updated_at"], batch_size=100)

        for b in Business.objects.filter(slug__startswith=BIZ_SLUG_PREFIX):
            b.created_at = self._rand_dt(120)
            b.updated_at = b.created_at + timedelta(hours=random.randint(1, 72))
        Business.objects.bulk_update(
            list(Business.objects.filter(slug__startswith=BIZ_SLUG_PREFIX)),
            ["created_at", "updated_at"],
            batch_size=200,
        )

        self.stdout.write("  Timestamps updated.")
