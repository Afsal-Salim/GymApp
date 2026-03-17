from rest_framework.views import APIView

from core.pagination import paginated_response

from .models import Plan
from .serializers import PlanSerializer


class PlanListView(APIView):
    """
    GET /api/plans/plan_list/
    Returns subscription plans (public). Supports ?page=1&page_size=10.
    """

    def get(self, request):
        queryset = Plan.objects.prefetch_related("features").order_by("price")
        return paginated_response(request, queryset, PlanSerializer)
