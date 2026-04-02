from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication import TokenAuthentication, token_auth_error_response
from core.record_status import RECORD_STATUS_ACTIVE

from businesses.models import Business, BusinessEnquiry
from businesses.serializers import (
    BusinessEnquiryCreateSerializer,
    BusinessEnquiryOwnerSerializer,
    BusinessEnquiryPatchSerializer,
    BusinessEnquirySerializer,
)
from businesses.search_filters import enquiry_search_q
from businesses.views.owned_business import get_owned_business
from businesses.visibility import active_businesses
from core.pagination import paginated_response


class BusinessEnquiryPublicCreateView(APIView):
    """
    POST /api/businesses/public/<slug>/enquiries/

    Public. Creates an enquiry for that business (gym page contact form).
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request, slug):
        try:
            business = active_businesses().get(slug=slug)
        except Business.DoesNotExist:
            return Response(
                {"detail": "No business found for this slug.", "slug": slug},
                status=status.HTTP_404_NOT_FOUND,
            )

        ser = BusinessEnquiryCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        enquiry = BusinessEnquiry.objects.create(
            business=business,
            **ser.validated_data,
        )
        return Response(
            BusinessEnquirySerializer(enquiry).data,
            status=status.HTTP_201_CREATED,
        )


class BusinessEnquiryOwnerListView(APIView):
    """
    GET /api/businesses/<slug>/enquiries/

    Owner only. Paginated list; query: enquiry_status, record_status,
    search or q (optional) — case-insensitive match on name, email, or message.
    """

    def get(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        qs = BusinessEnquiry.objects.filter(business=business).order_by("-created_at")
        es = request.query_params.get("enquiry_status")
        if es:
            qs = qs.filter(enquiry_status=es)
        rs = request.query_params.get("record_status")
        if rs:
            qs = qs.filter(record_status=rs)
        else:
            qs = qs.filter(record_status=RECORD_STATUS_ACTIVE)

        search = (
            request.query_params.get("search") or request.query_params.get("q") or ""
        ).strip()
        if search:
            qs = qs.filter(enquiry_search_q(search))

        return paginated_response(request, qs, BusinessEnquiryOwnerSerializer)


class BusinessEnquiryOwnerDetailView(APIView):
    """
    GET, PATCH /api/businesses/<slug>/enquiries/<id>/

    Owner only.
    """

    def get(self, request, slug, pk):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        enquiry = get_object_or_404(
            BusinessEnquiry.objects.filter(business=business),
            pk=pk,
        )
        return Response(BusinessEnquiryOwnerSerializer(enquiry).data)

    def patch(self, request, slug, pk):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        enquiry = get_object_or_404(
            BusinessEnquiry.objects.filter(business=business),
            pk=pk,
        )
        ser = BusinessEnquiryPatchSerializer(enquiry, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        ser.save()
        return Response(BusinessEnquiryOwnerSerializer(enquiry).data)
