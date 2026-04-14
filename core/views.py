from django.conf import settings
from django.views.generic import TemplateView

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication, token_auth_error_response
from core.record_status import RECORD_STATUS_ACTIVE
from core.email_notifications import notify_client_support_feedback, notify_site_enquiry
from core.mail_background import run_in_background
from core.models import ClientSupportMessage, SiteEnquiry
from core.serializers import (
    ClientSupportMessageCreateSerializer,
    ClientSupportMessageListSerializer,
    ServiceEnquiryCreateSerializer,
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

        enquiry = serializer.save()
        run_in_background(
            lambda: notify_site_enquiry(
                name=enquiry.name,
                email=enquiry.email,
                message=enquiry.message,
                enquiry_kind=enquiry.enquiry_kind,
            ),
            thread_name="site_enquiry_email",
        )

        return Response(
            {"ok": True, "id": enquiry.id},
            status=status.HTTP_201_CREATED,
        )


class ServiceEnquiryCreateView(APIView):
    """
    POST /api/public/service-enquiries/

    Public. Home page “services” enquiry: name, email, phone, message,
    optional service_topic. Stored as SiteEnquiry with enquiry_kind=service.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = ServiceEnquiryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        enquiry = serializer.save()
        run_in_background(
            lambda: notify_site_enquiry(
                name=enquiry.name,
                email=enquiry.email,
                message=enquiry.message,
                phone=enquiry.phone,
                service_topic=enquiry.service_topic,
                enquiry_kind=enquiry.enquiry_kind,
            ),
            thread_name="service_enquiry_email",
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
            return token_auth_error_response(err)

        qs = ClientSupportMessage.objects.filter(
            customer=customer,
            record_status=RECORD_STATUS_ACTIVE,
        )[:100]
        return Response(
            {"results": ClientSupportMessageListSerializer(qs, many=True).data}
        )

    def post(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        serializer = ClientSupportMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        row = ClientSupportMessage.objects.create(
            customer=customer,
            **serializer.validated_data,
        )
        run_in_background(
            lambda: notify_client_support_feedback(
                customer_email=customer.email,
                customer_username=customer.username,
                customer_id=customer.id,
                kind=row.kind,
                subject=row.subject,
                message=row.message,
                message_id=row.id,
            ),
            thread_name="client_support_email",
        )
        return Response(
            ClientSupportMessageListSerializer(row).data,
            status=status.HTTP_201_CREATED,
        )
