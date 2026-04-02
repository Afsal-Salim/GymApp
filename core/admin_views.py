from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import Customer
from businesses.models import Business
from core.admin_access import is_admin_customer
from core.admin_serializers import (
    AdminBusinessPatchSerializer,
    AdminBusinessSerializer,
    AdminClientSupportPatchSerializer,
    AdminClientSupportSerializer,
    AdminCustomerPatchSerializer,
    AdminCustomerSerializer,
    AdminSiteEnquiryPatchSerializer,
    AdminSiteEnquirySerializer,
)
from core.authentication import TokenAuthentication, token_auth_error_response
from core.models import ClientSupportMessage, SiteEnquiry
from core.pagination import paginated_response


class _AdminMixin:
    def _guard(self, request):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return None, token_auth_error_response(err)
        if not is_admin_customer(customer):
            return None, Response(
                {"detail": "Admin access only. Your account must have role admin (0)."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return customer, None


class AdminSupportFeedbackListView(_AdminMixin, APIView):
    """GET — list support + feedback with filters."""

    def get(self, request):
        _, denied = self._guard(request)
        if denied:
            return denied

        qs = ClientSupportMessage.objects.select_related("customer").order_by("-created_at")
        kind = (request.query_params.get("kind") or "").strip().lower()
        if kind in (ClientSupportMessage.KIND_SUPPORT, ClientSupportMessage.KIND_FEEDBACK):
            qs = qs.filter(kind=kind)
        ss = request.query_params.get("support_status")
        if ss:
            qs = qs.filter(support_status=ss)
        fs = request.query_params.get("feedback_status")
        if fs:
            qs = qs.filter(feedback_status=fs)
        rs = request.query_params.get("record_status")
        if rs:
            qs = qs.filter(record_status=rs)

        return paginated_response(request, qs, AdminClientSupportSerializer)


class AdminSupportFeedbackDetailView(_AdminMixin, APIView):
    """PATCH — update support_status / feedback_status / record_status."""

    def patch(self, request, pk):
        _, denied = self._guard(request)
        if denied:
            return denied

        row = get_object_or_404(ClientSupportMessage.objects.select_related("customer"), pk=pk)
        ser = AdminClientSupportPatchSerializer(row, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        ser.save()
        return Response(AdminClientSupportSerializer(row).data)


class AdminEnquiryListView(_AdminMixin, APIView):
    def get(self, request):
        _, denied = self._guard(request)
        if denied:
            return denied

        qs = SiteEnquiry.objects.all().order_by("-created_at")
        es = request.query_params.get("enquiry_status")
        if es:
            qs = qs.filter(enquiry_status=es)
        rs = request.query_params.get("record_status")
        if rs:
            qs = qs.filter(record_status=rs)
        ek = (request.query_params.get("enquiry_kind") or "").strip()
        if ek in (SiteEnquiry.KIND_GENERAL, SiteEnquiry.KIND_SERVICE):
            qs = qs.filter(enquiry_kind=ek)

        return paginated_response(request, qs, AdminSiteEnquirySerializer)


class AdminEnquiryDetailView(_AdminMixin, APIView):
    def patch(self, request, pk):
        _, denied = self._guard(request)
        if denied:
            return denied

        row = get_object_or_404(SiteEnquiry, pk=pk)
        ser = AdminSiteEnquiryPatchSerializer(row, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        ser.save()
        return Response(AdminSiteEnquirySerializer(row).data)


class AdminWebsiteListView(_AdminMixin, APIView):
    def get(self, request):
        _, denied = self._guard(request)
        if denied:
            return denied

        qs = Business.objects.select_related("owner").order_by("-created_at")
        rs = request.query_params.get("record_status")
        if rs:
            qs = qs.filter(record_status=rs)

        return paginated_response(request, qs, AdminBusinessSerializer)


class AdminWebsiteDetailView(_AdminMixin, APIView):
    def patch(self, request, slug):
        _, denied = self._guard(request)
        if denied:
            return denied

        row = get_object_or_404(Business.objects.select_related("owner"), slug=slug)
        ser = AdminBusinessPatchSerializer(row, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        ser.save()
        return Response(AdminBusinessSerializer(row).data)


class AdminUserListView(_AdminMixin, APIView):
    def get(self, request):
        _, denied = self._guard(request)
        if denied:
            return denied

        qs = Customer.objects.all().order_by("-created_at")
        rs = request.query_params.get("record_status")
        if rs:
            qs = qs.filter(record_status=rs)

        return paginated_response(request, qs, AdminCustomerSerializer)


class AdminUserDetailView(_AdminMixin, APIView):
    def patch(self, request, pk):
        _, denied = self._guard(request)
        if denied:
            return denied

        row = get_object_or_404(Customer, pk=pk)
        ser = AdminCustomerPatchSerializer(row, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        ser.save()
        return Response(AdminCustomerSerializer(row).data)
