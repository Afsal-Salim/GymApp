from django.conf import settings
from django.views.generic import TemplateView

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication
from core.email_notifications import notify_client_support_feedback, notify_site_enquiry
from core.models import ClientSupportMessage, SiteEnquiry
from core.serializers import (
    ClientSupportMessageCreateSerializer,
    ClientSupportMessageListSerializer,
    SiteEnquiryCreateSerializer,
)


class HomePageView(TemplateView):
    """Marketing home with login / sign-up links and enquiry modal."""

    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["google_client_id"] = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "") or ""
        return ctx


class SiteEnquiryCreateView(APIView):
    """
    POST /api/public/enquiries/

    Public. Saves enquiry and emails CRYSTAL_TEAM_NOTIFY_EMAIL.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = SiteEnquiryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        enquiry = SiteEnquiry.objects.create(**serializer.validated_data)
        notify_site_enquiry(
            name=enquiry.name,
            email=enquiry.email,
            message=enquiry.message,
        )

        return Response(
            {"ok": True, "id": enquiry.id},
            status=status.HTTP_201_CREATED,
        )


class ClientSupportFeedbackView(APIView):
    """
    GET  /api/support/  — list this client’s recent support & feedback (newest first, capped).
    POST /api/support/  — submit support or feedback (Bearer access token).
    """

    def get(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return Response(err, status=status.HTTP_401_UNAUTHORIZED)

        qs = ClientSupportMessage.objects.filter(customer=customer)[:100]
        return Response(
            {"results": ClientSupportMessageListSerializer(qs, many=True).data}
        )

    def post(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return Response(err, status=status.HTTP_401_UNAUTHORIZED)

        serializer = ClientSupportMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        row = ClientSupportMessage.objects.create(
            customer=customer,
            **serializer.validated_data,
        )
        notify_client_support_feedback(
            customer_email=customer.email,
            customer_username=customer.username,
            customer_id=customer.id,
            kind=row.kind,
            subject=row.subject,
            message=row.message,
            message_id=row.id,
        )
        return Response(
            ClientSupportMessageListSerializer(row).data,
            status=status.HTTP_201_CREATED,
        )
