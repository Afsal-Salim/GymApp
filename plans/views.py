from django.db.models import Prefetch
from rest_framework.views import APIView

from core.pagination import paginated_response
from core.record_status import RECORD_STATUS_ACTIVE

from .models import Feature, Plan
from .serializers import PlanSerializer


class PlanListView(APIView):
    """
    GET /api/plans/plan_list/
    Returns subscription plans (public). Supports ?page=1&page_size=10.
    """

    def get(self, request):
        queryset = (
            Plan.objects.filter(record_status=RECORD_STATUS_ACTIVE, internal_only=False)
            .prefetch_related(
                Prefetch(
                    "features",
                    queryset=Feature.objects.filter(record_status=RECORD_STATUS_ACTIVE),
                )
            )
            .order_by("price")
        )
        return paginated_response(request, queryset, PlanSerializer)
