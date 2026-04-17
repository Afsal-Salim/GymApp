"""Owner-only business logo upload to S3 (logos/<slug>/<uuid>.ext)."""

from copy import deepcopy

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from businesses.models import BusinessWebsitePayload
from businesses.serializers import BusinessSerializer
from businesses.views.owned_business import get_owned_business
from core.authentication import TokenAuthentication, token_auth_error_response
from core.gym_image_validation import (
    try_gym_image_as_json_uploaded_file,
    validate_gym_image_upload,
)
from core.s3_gym_images import (
    delete_gym_image_from_s3,
    gym_s3_configured,
    gym_s3_configuration_missing,
    upload_business_logo_to_s3,
)


class BusinessLogoView(APIView):
    """
    POST   /api/businesses/<slug>/logo/ — upload logo (multipart ``file`` or JSON base64).
    DELETE /api/businesses/<slug>/logo/ — remove S3 logo (``logo_s3_key`` cleared); external URLs in JSON unchanged.

    Stores objects under ``logos/<slug>/<uuid>.<ext>`` in the gym images bucket.
    """

    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug, with_serializer_relations=True)
        if denied:
            return denied

        if not gym_s3_configured():
            return Response(
                {
                    "detail": "Logo upload requires S3. Configure the same variables as gym images.",
                    "missing_configuration": gym_s3_configuration_missing(),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        upload = request.FILES.get("file")
        if not upload:
            try:
                json_upload = try_gym_image_as_json_uploaded_file(request.data)
            except ValidationError as e:
                return Response({"detail": e.messages}, status=status.HTTP_400_BAD_REQUEST)
            if json_upload:
                upload = json_upload

        if not upload:
            return Response(
                {
                    "detail": "No image provided.",
                    "multipart": "Use multipart/form-data with field name 'file'.",
                    "json": "Use application/json with file_base64 / image_base64 / image plus filename.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            raw, ext, mime = validate_gym_image_upload(upload)
        except ValidationError as e:
            return Response({"detail": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        old_key = (business.logo_s3_key or "").strip()
        try:
            _public_url, s3_key = upload_business_logo_to_s3(
                business_slug=business.slug,
                file_body=raw,
                extension_with_dot=ext,
                content_type=mime,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        if old_key and old_key != s3_key:
            try:
                delete_gym_image_from_s3(s3_key=old_key)
            except RuntimeError:
                pass

        business.logo_s3_key = s3_key
        business.save(update_fields=["logo_s3_key", "updated_at"])

        payload, _ = BusinessWebsitePayload.objects.get_or_create(business=business)
        wc = deepcopy(payload.website_content) if payload.website_content else {}
        if not isinstance(wc, dict):
            wc = {}
        logo_inner = dict(wc.get("logo") or {})
        logo_inner["src"] = ""
        wc["logo"] = logo_inner
        payload.website_content = wc
        payload.save(update_fields=["website_content", "updated_at"])

        refreshed, denied = get_owned_business(
            customer, business.slug, with_serializer_relations=True
        )
        if denied:
            return denied
        return Response(BusinessSerializer(refreshed).data, status=status.HTTP_200_OK)

    def delete(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug, with_serializer_relations=True)
        if denied:
            return denied

        key = (business.logo_s3_key or "").strip()
        if not key:
            return Response(
                {"detail": "No uploaded logo to remove."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if gym_s3_configured():
            try:
                delete_gym_image_from_s3(s3_key=key)
            except RuntimeError as e:
                return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        business.logo_s3_key = ""
        business.save(update_fields=["logo_s3_key", "updated_at"])

        refreshed, denied = get_owned_business(
            customer, business.slug, with_serializer_relations=True
        )
        if denied:
            return denied
        return Response(BusinessSerializer(refreshed).data, status=status.HTTP_200_OK)
