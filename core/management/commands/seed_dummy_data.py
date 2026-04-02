"""
Seed dummy data for local/testing. Safe to run multiple times (uses get_or_create).

Creates:
- 2 test customers (login: test@example.com / password123, demo@example.com / password123)
- 3 businesses with slugs: my-gym, fit-life, crossfit-zone
- 1 payment + 1 subscription for my-gym (Starter plan)

Usage:
  python manage.py seed_dummy_data
"""
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from authentication.models import Customer
from businesses.models import Business
from plans.models import Plan
from payments.models import Payment
from subscriptions.models import Subscription


class Command(BaseCommand):
    help = "Load dummy data for testing (customers, businesses, payment, subscription)."

    def handle(self, *args, **options):
        self.stdout.write("Seeding dummy data...")

        # --- Customers ---
        c1, _ = Customer.objects.get_or_create(
            email="test@example.com",
            defaults={"username": "testuser"},
        )
        if _:
            c1.set_password("password123")
            c1.save()
            self.stdout.write("  Created customer: test@example.com (password: password123)")
        else:
            self.stdout.write("  Customer exists: test@example.com")

        c2, _ = Customer.objects.get_or_create(
            email="demo@example.com",
            defaults={"username": "demouser"},
        )
        if _:
            c2.set_password("password123")
            c2.save()
            self.stdout.write("  Created customer: demo@example.com (password: password123)")
        else:
            self.stdout.write("  Customer exists: demo@example.com")

        # --- Businesses (owned by first customer; one by second) ---
        biz_data = [
            ("my-gym", "My Gym", c1, "Friendly neighbourhood gym."),
            ("fit-life", "Fit Life Studio", c1, "Yoga and fitness studio."),
            ("crossfit-zone", "CrossFit Zone", c2, "CrossFit box."),
        ]
        businesses = {}
        for slug, name, owner, desc in biz_data:
            obj, created = Business.objects.get_or_create(
                slug=slug,
                defaults={
                    "owner": owner,
                    "name": name,
                    "description": desc,
                    "phone": "9876543210",
                    "address": "123 Main St, City",
                },
            )
            businesses[slug] = obj
            if created:
                self.stdout.write(f"  Created business: {slug} ({name})")
            else:
                self.stdout.write(f"  Business exists: {slug}")

        # --- One dummy Payment + Subscription for my-gym (Starter) ---
        starter = Plan.objects.filter(name="Starter").first()
        if not starter:
            self.stdout.write(self.style.WARNING("  No Starter plan found; skip payment/subscription."))
        else:
            my_gym = businesses["my-gym"]
            payment, p_created = Payment.objects.get_or_create(
                razorpay_order_id="order_dummy_test_001",
                defaults={
                    "business": my_gym,
                    "razorpay_payment_id": "pay_dummy_test_001",
                    "razorpay_signature": "dummy_sig_001",
                    "amount": starter.price,
                    "currency": "INR",
                    "payment_status": "captured",
                    "payment_method": "razorpay",
                },
            )
            if p_created:
                self.stdout.write("  Created dummy payment for my-gym")

            start = timezone.now().date()
            end = start + timedelta(days=starter.duration)
            sub, s_created = Subscription.objects.get_or_create(
                business=my_gym,
                payment_id=payment.razorpay_payment_id,
                defaults={
                    "plan": starter,
                    "subscription_start_date": start,
                    "subscription_end_date": end,
                },
            )
            if s_created:
                self.stdout.write("  Created dummy subscription (Starter) for my-gym")

        self.stdout.write(self.style.SUCCESS("Done. You can login with test@example.com / password123 and use business_slug: my-gym"))
