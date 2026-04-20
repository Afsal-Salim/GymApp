from copy import deepcopy

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from assets.models import Asset
from assets.serializers import AssetSerializer
from businesses.models import Business, BusinessWebsitePayload
from businesses.gym_image_limits import (
    count_active_gym_images,
    max_gym_images_for_business,
)
from businesses.serializers import BusinessSerializer
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


ALLOWED_ASSET_TYPES = frozenset(
    {"logo", "dp", "hero", "background", "gallery"}
)


class GymImagesView(APIView):
    """
    Single media API for a business (gym site images + business branding logo).

    GET    /api/businesses/<slug>/images/ — public: active ``Asset`` rows (no auth).
    POST   /api/businesses/<slug>/images/ — owner upload (Bearer required).
    DELETE /api/businesses/<slug>/images/ — owner: single delete endpoint for all images (Bearer required).

    DELETE query or JSON body (one of):

    - ``id`` / ``pk`` — delete that ``Asset`` row (any ``asset_type``: dp, hero, background, gallery, …) and its S3 object.
    - ``asset_type=logo`` — remove **business branding logo** only (clears ``Business.logo_s3_key``; no ``Asset`` row).

    Examples: ``DELETE .../images/?id=42`` — ``DELETE .../images/?asset_type=logo``

    POST body:
    - multipart: ``file`` + optional ``asset_type``.
    - JSON: ``file_base64`` / ``image_base64`` / ``image`` + ``filename``, optional ``asset_type``.

    ``asset_type``: ``logo`` | ``dp`` | ``hero`` | ``background`` | ``gallery`` (default ``gallery``).
    S3 keys: ``{type}/{slug}/{uuid}.ext``.

    - ``logo``: sets ``Business.logo_s3_key`` (branding logo), clears ``website_content.logo.src``, does not create an ``Asset`` row. No subscription slot check (legacy ``/logo/`` behavior).
    - Other types: create ``Asset``; subscription / trial image limits apply.

    Trial: max 5 non-logo images. Paid plans: no cap for Assets (still 1 MB / type rules).
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

        asset_type = (request.data.get("asset_type") or "gallery").strip().lower()
        if asset_type not in ALLOWED_ASSET_TYPES:
            return Response(
                {
                    "detail": f"Invalid asset_type. Allowed: {', '.join(sorted(ALLOWED_ASSET_TYPES))}.",
                },
                status=status.HTTP_400_BAD_REQUEST,
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

        if asset_type == "logo":
            return self._post_business_logo(request, customer, slug, upload)

        business, denied = get_owned_business(customer, slug)
        if denied:
            return denied

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
                asset_type=asset_type,
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

    def _post_business_logo(self, request, customer, slug, upload):
        """Branding logo: ``logo/{slug}/…`` in S3, updates ``Business.logo_s3_key`` (no ``Asset`` row)."""
        business, denied = get_owned_business(
            customer, slug, with_serializer_relations=True
        )
        if denied:
            return denied

        try:
            raw, ext, mime = validate_gym_image_upload(upload)
        except ValidationError as e:
            return Response({"detail": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        old_key = (business.logo_s3_key or "").strip()
        try:
            _public_url, s3_key = upload_gym_image_to_s3(
                business_slug=business.slug,
                file_body=raw,
                extension_with_dot=ext,
                content_type=mime,
                asset_type="logo",
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
        """
        Remove one image: either an ``Asset`` by ``id`` / ``pk``, or business logo via ``asset_type=logo``.
        """
        customer, err = TokenAuthentication().authenticate(request)
        if err:
            return token_auth_error_response(err)

        qp = request.query_params
        data = getattr(request, "data", None)
        raw_id = qp.get("id") or qp.get("pk")
        if (raw_id is None or str(raw_id).strip() == "") and data is not None:
            raw_id = data.get("id") or data.get("pk")
        asset_type = (qp.get("asset_type") or "").strip().lower()
        if not asset_type and data is not None:
            asset_type = (data.get("asset_type") or "").strip().lower()

        if raw_id is not None and str(raw_id).strip() != "":
            if asset_type:
                return Response(
                    {
                        "detail": "Do not combine id with asset_type. Use id alone for Asset delete, or asset_type=logo alone for branding logo.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                pk = int(raw_id)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "id must be an integer (Asset primary key)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return self._delete_asset_by_id(request, customer, slug, pk)

        if asset_type == "logo":
            return self._delete_business_logo(request, customer, slug)

        return Response(
            {
                "detail": (
                    "Specify id (Asset primary key) or asset_type=logo (business branding logo)."
                ),
                "examples": [
                    "DELETE /api/businesses/<slug>/images/?id=42",
                    "DELETE /api/businesses/<slug>/images/?asset_type=logo",
                ],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _delete_asset_by_id(self, request, customer, slug, pk: int):
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
        return Response({"detail": "Image deleted.", "deleted": "asset", "id": pk})

    def _delete_business_logo(self, request, customer, slug):
        """Remove business branding logo (``logo_s3_key``); does not delete ``Asset`` rows."""
        business, denied = get_owned_business(
            customer, slug, with_serializer_relations=True
        )
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
        return Response(
            {
                "detail": "Business logo removed.",
                "deleted": "business_logo",
                "business": BusinessSerializer(refreshed).data,
            },
            status=status.HTTP_200_OK,
        )
