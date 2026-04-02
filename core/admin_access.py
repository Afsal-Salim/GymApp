from django.conf import settings

from authentication.models import Customer


def admin_email_set() -> set[str]:
    return {e for e in getattr(settings, "ADMIN_EMAILS", []) if e}


def is_admin_customer(customer: Customer | None) -> bool:
    if not customer or not customer.email:
        return False
    return customer.email.strip().lower() in admin_email_set()
