from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Plan
from .serializers import PlanSerializer


class PlanListView(APIView):
    """
    GET /api/plans/

    Returns all subscription plans (public, no auth required).
    """

    def get(self, request):
        plans = Plan.objects.prefetch_related("features").order_by("price")
        serializer = PlanSerializer(plans, many=True)
        return Response(serializer.data)
