from decimal import Decimal

import razorpay
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from authentication.models import Customer
from subscriptions.models import Subscription
from subscriptions.utils import next_stacked_subscription_dates

from .models import Payment
from .serializers import (
    PaymentSerializer,
    CreateOrderSerializer,
    VerifyPaymentSerializer,
)


def _get_razorpay_client():
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "") or ""
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "") or ""
    return razorpay.Client(auth=(key_id, key_secret))


def _mask_payment_id(payment_id):
    """Show last 4 chars for privacy, e.g. pay_****xyz1."""
    if not payment_id or len(payment_id) <= 4:
        return payment_id or "—"
    return payment_id[:4] + "****" + payment_id[-4:]


def _send_payment_success_email(customer, business, payment, subscription, plan):
    """Send styled HTML email with payment and (optional) subscription details."""
    customer_name = customer.username or customer.email.split("@")[0]
    amount = f"{payment.amount:.2f}"
    payment_id_masked = _mask_payment_id(payment.razorpay_payment_id)
    context = {
        "customer_name": customer_name,
        "business_name": business.name,
        "amount": amount,
        "currency": payment.currency,
        "payment_id": payment_id_masked,
        "payment_status": payment.payment_status or "captured",
        "plan_name": plan.name if plan else None,
        "subscription_start_date": subscription.subscription_start_date.isoformat() if subscription else None,
        "subscription_end_date": subscription.subscription_end_date.isoformat() if subscription else None,
    }
    subject = getattr(
        settings,
        "PAYMENT_CONFIRMATION_EMAIL_SUBJECT",
        f"Payment confirmed – {business.name}",
    )
    plain_message = (
        f"Hi {customer_name}, your payment of {payment.currency} {amount} for {business.name} "
        f"has been confirmed. Payment ID: {payment_id_masked}."
    )
    html_message = render_to_string(
        "payments/email_payment_success.html",
        context,
    )
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            fail_silently=True,
            html_message=html_message,
        )
    except Exception:
        pass  # fail_silently already; avoid breaking the API response


class CreateOrderView(APIView):
    """
    POST /api/payments/create-order/

    No login required. Creates a Razorpay order if the email owns the business
    for the given slug. Only the account that owns the business (email match)
    can create an order for that slug.
    """

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].lower()
        try:
            customer = Customer.objects.get(email__iexact=email)
        except Customer.DoesNotExist:
            return Response(
                {"detail": "No account found for this email."},
                status=status.HTTP_403_FORBIDDEN,
            )

        business = serializer.validated_data["business_id"]
        if business.owner_id != customer.id:
            return Response(
                {"detail": "This business is not linked to this email."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            return Response(
                {"detail": "Razorpay is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        amount = serializer.validated_data["amount"]
        currency = serializer.validated_data.get("currency", "INR")
        # Razorpay expects amount in smallest currency unit (paise for INR)
        amount_paise = int(amount * 100)

        try:
            client = _get_razorpay_client()
            order = client.order.create(
                data={
                    "amount": amount_paise,
                    "currency": currency,
                }
            )
        except Exception as e:
            return Response(
                {"detail": "Failed to create order.", "error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "order_id": order["id"],
                "amount": amount_paise,
                "currency": currency,
                "key_id": settings.RAZORPAY_KEY_ID,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyPaymentView(APIView):
    """
    POST /api/payments/verify/

    No login required. Verifies Razorpay signature and creates Payment
    (and optionally Subscription). Email must be the owner of the business
    for the given slug.
    """

    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].lower()
        try:
            customer = Customer.objects.get(email__iexact=email)
        except Customer.DoesNotExist:
            return Response(
                {"detail": "No account found for this email."},
                status=status.HTTP_403_FORBIDDEN,
            )

        business = serializer.validated_data["business_id"]
        if business.owner_id != customer.id:
            return Response(
                {"detail": "This business is not linked to this email."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not settings.RAZORPAY_KEY_SECRET:
            return Response(
                {"detail": "Razorpay is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        order_id = serializer.validated_data["razorpay_order_id"]
        payment_id = serializer.validated_data["razorpay_payment_id"]
        signature = serializer.validated_data["razorpay_signature"]
        plan = serializer.validated_data.get("plan_id")

        try:
            client = _get_razorpay_client()
            util = razorpay.Utility(client)
            util.verify_payment_signature(
                {
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": signature,
                }
            )
        except razorpay.errors.SignatureVerificationError:
            return Response(
                {"detail": "Payment signature verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"detail": "Verification failed.", "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch order to get amount and currency
        try:
            order = client.order.fetch(order_id)
            amount_decimal = Decimal(order["amount"]) / 100
            currency = order.get("currency", "INR")
        except Exception:
            amount_decimal = Decimal("0")
            currency = "INR"

        payment = Payment.objects.create(
            business=business,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
            amount=amount_decimal,
            currency=currency,
            payment_status="captured",
            payment_method="razorpay",
        )

        subscription = None
        if plan:
            start, end = next_stacked_subscription_dates(business, plan.duration)
            subscription = Subscription.objects.create(
                business=business,
                plan=plan,
                payment_id=payment_id,
                subscription_start_date=start,
                subscription_end_date=end,
            )

        # Send payment confirmation email to the customer
        _send_payment_success_email(
            customer=customer,
            business=business,
            payment=payment,
            subscription=subscription,
            plan=plan,
        )

        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "subscription": (
                    {
                        "id": subscription.id,
                        "plan": plan.name,
                        "subscription_start_date": subscription.subscription_start_date.isoformat(),
                        "subscription_end_date": subscription.subscription_end_date.isoformat(),
                    }
                    if subscription
                    else None
                ),
            },
            status=status.HTTP_201_CREATED,
        )
