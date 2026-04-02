from authentication.models import Customer


def is_admin_customer(customer: Customer | None) -> bool:
    return bool(customer and customer.role == Customer.ROLE_ADMIN)
