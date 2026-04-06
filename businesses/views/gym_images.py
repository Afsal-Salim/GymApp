from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from assets.models import Asset
from assets.serializers import AssetSerializer
from businesses.gym_image_limits import (
    count_active_gym_images,
    max_gym_images_for_business,
)
from businesses.views.owned_business import get_owned_business
from core.authentication import TokenAuthentication, token_auth_error_response
from core.gym_image_validation import validate_gym_image_upload
from core.record_status import RECORD_STATUS_ACTIVE
from core.s3_gym_images import gym_s3_configured, upload_gym_image_to_s3


ALLOWED_ASSET_TYPES = frozenset({"logo", "hero", "background", "gallery"})


class GymImagesView(APIView):
    """
    GET  /api/businesses/<slug>/images/ — list uploads + slot usage
    POST /api/businesses/<slug>/images/ — upload (multipart)
    """

    parser_classes = (MultiPartParser, FormParser)

    def get(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        limit = max_gym_images_for_business(business)
        used = count_active_gym_images(business)
        qs = Asset.objects.filter(business=business, record_status=RECORD_STATUS_ACTIVE).order_by(
            "-uploaded_at"
        )
        return Response(
            {
                "images": AssetSerializer(qs, many=True).data,
                "slots_used": used,
                "slots_limit": limit,
            }
        )

    def post(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        if not gym_s3_configured():
            return Response(
                {
                    "detail": "Image upload is not configured. Set AWS_S3_GYM_IMAGES_BUCKET and AWS credentials.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        limit = max_gym_images_for_business(business)
        if limit <= 0:
            return Response(
                {
                    "detail": "No active subscription. Subscribe to upload gym images.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        used = count_active_gym_images(business)
        if used >= limit:
            return Response(
                {
                    "detail": f"Image limit reached ({limit} for your current plan).",
                    "slots_used": used,
                    "slots_limit": limit,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": "Missing file field (multipart)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset_type = (request.data.get("asset_type") or "gallery").strip().lower()
        if asset_type not in ALLOWED_ASSET_TYPES:
            return Response(
                {
                    "detail": f"Invalid asset_type. Allowed: {', '.join(sorted(ALLOWED_ASSET_TYPES))}.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            raw, ext, mime = validate_gym_image_upload(upload)
        except ValidationError as e:
            return Response({"detail": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        try:
            public_url, s3_key = upload_gym_image_to_s3(
                business_slug=business.slug,
                file_body=raw,
                extension_with_dot=ext,
                content_type=mime,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        asset = Asset.objects.create(
            business=business,
            image_url=public_url,
            s3_key=s3_key,
            asset_type=asset_type,
            record_status=RECORD_STATUS_ACTIVE,
        )

        return Response(
            {
                "image_url": public_url,
                "s3_key": s3_key,
                "asset": AssetSerializer(asset).data,
                "slots_used": used + 1,
                "slots_limit": limit,
            },
            status=status.HTTP_201_CREATED,
        )
