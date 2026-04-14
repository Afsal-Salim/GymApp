from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from assets.models import Asset
from assets.serializers import AssetSerializer
from businesses.models import Business
from businesses.gym_image_limits import (
    count_active_gym_images,
    max_gym_images_for_business,
)
from businesses.visibility import active_businesses
from businesses.views.owned_business import get_owned_business
from core.authentication import TokenAuthentication, token_auth_error_response
from core.logging import app_logger
from core.gym_image_validation import (
    try_gym_image_as_json_uploaded_file,
    validate_gym_image_upload,
)
from core.record_status import RECORD_STATUS_ACTIVE
from core.s3_gym_images import (
    delete_gym_image_from_s3,
    gym_image_browser_url,
    gym_image_browser_urls_for_keys,
    gym_s3_configured,
    gym_s3_configuration_missing,
    upload_gym_image_to_s3,
)


ALLOWED_ASSET_TYPES = frozenset({"logo", "hero", "background", "gallery"})


class GymImagesView(APIView):
    """
    GET  /api/businesses/<slug>/images/ — public: active gym images for this slug (no auth).
    POST /api/businesses/<slug>/images/ — owner upload (Bearer required).

    - multipart/form-data: field ``file`` (optional ``asset_type``).
    - application/json: ``file_base64`` | ``image_base64`` | ``image`` (string, optional data URL),
      plus ``filename`` (or ``name``) with extension, optional ``asset_type``.

    Trial: max 5 images. Paid plans (Starter, Pro, …): no image count cap (still 1 MB / type rules).
    """

    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, slug):
        try:
            business = active_businesses().get(slug=slug)
        except Business.DoesNotExist:
            return Response(
                {"detail": "No business found for this slug.", "slug": slug},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = list(
            Asset.objects.filter(
                business=business, record_status=RECORD_STATUS_ACTIVE
            ).order_by("-uploaded_at")
        )
        url_by_key = gym_image_browser_urls_for_keys(a.s3_key for a in qs if a.s3_key)
        return Response(
            {
                "images": AssetSerializer(
                    qs,
                    many=True,
                    context={"gym_image_browser_url_by_s3_key": url_by_key},
                ).data
            }
        )

    def post(self, request, slug):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

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
                    "multipart": "Use multipart/form-data with field name 'file' (optional 'asset_type').",
                    "json": (
                        "Use application/json with file_base64 or image_base64 or image (base64 string), "
                        "plus filename (e.g. photo.jpg), optional asset_type."
                    ),
                    "received_content_type": request.content_type or "",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not gym_s3_configured():
            return Response(
                {
                    "detail": "Image upload requires S3. Set the missing environment variables on the server and restart.",
                    "missing_configuration": gym_s3_configuration_missing(),
                    "hint": "Set AWS_S3_GYM_IMAGES_BUCKET plus AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or S3_ACCESS_KEY/S3_SECRET_KEY, or GYM_IMAGES_USE_DEFAULT_AWS_CREDENTIALS=true with IAM role or ~/.aws/credentials. Restart the app after changing .env.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        limit = max_gym_images_for_business(business)
        if limit == 0:
            return Response(
                {
                    "detail": "No active subscription. Subscribe to upload gym images.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        used = count_active_gym_images(business)
        if limit is not None and used >= limit:
            return Response(
                {
                    "detail": f"Image limit reached ({limit} for your current plan).",
                    "slots_used": used,
                    "slots_limit": limit,
                },
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

        browser_url = gym_image_browser_url(s3_key) or public_url
        return Response(
            {
                "image_url": browser_url,
                "s3_key": s3_key,
                "asset": AssetSerializer(asset).data,
                "slots_used": used + 1,
                "slots_limit": limit,
            },
            status=status.HTTP_201_CREATED,
        )


class GymImageDeleteView(APIView):
    """
    POST /api/businesses/<slug>/images/<pk>/

    Owner only. Deletes the asset row and removes the object from S3 when ``s3_key`` is set.
    (POST instead of DELETE for clients that do not send DELETE reliably.)
    """

    def post(self, request, slug, pk):
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

        asset = get_object_or_404(Asset, pk=pk, business=business)

        if asset.s3_key and gym_s3_configured():
            try:
                delete_gym_image_from_s3(s3_key=asset.s3_key)
            except RuntimeError as e:
                return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        elif asset.s3_key:
            app_logger.warning(
                "Gym image delete: skipping S3 (not configured), removing DB row only",
                asset_id=asset.pk,
                s3_key=asset.s3_key,
            )

        asset.delete()
        return Response({"detail": "Image deleted."}, status=status.HTTP_200_OK)
