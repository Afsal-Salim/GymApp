from math import ceil
from typing import Any, Dict, List, Tuple

from django.db import connection
from django.db.models import IntegerField
from django.db.models.expressions import RawSQL
from django.http import HttpRequest

from rest_framework.response import Response


def _paginate_with_window_aggregate(queryset, page: int, page_size: int) -> Tuple[List[Any], int] | None:
    """
    PostgreSQL: one round-trip for both the page rows and total row count using
    ``COUNT(*) OVER ()``. Falls back to None when not supported.
    """
    if connection.vendor != "postgresql":
        return None
    start = (page - 1) * page_size
    end = start + page_size
    qs = queryset.annotate(
        _pg_pagination_total=RawSQL(
            "(COUNT(*) OVER ())::integer",
            [],
            output_field=IntegerField(),
        )
    )
    rows = list(qs[start:end])
    if rows:
        return rows, int(rows[0]._pg_pagination_total)
    # Empty slice: need total (e.g. page past end or no rows)
    return [], queryset.count()


class Paginator:
    """
    Reusable paginator: reads `page` and `page_size` from query params.
    Use paginate() to get (items, meta), or paginated_response() for a DRF Response.
    """

    default_page_size: int = 10
    max_page_size: int = 100

    def __init__(
        self,
        request: HttpRequest,
        queryset,
        default_page_size: int = 10,
        max_page_size: int = 100,
    ) -> None:
        self.request = request
        self.queryset = queryset
        self.default_page_size = default_page_size or self.default_page_size
        self.max_page_size = max_page_size or self.max_page_size

    def _get_page_params(self) -> Tuple[int, int]:
        try:
            page = int(self.request.GET.get("page", "1"))
        except (TypeError, ValueError):
            page = 1

        try:
            page_size = int(self.request.GET.get("page_size", str(self.default_page_size)))
        except (TypeError, ValueError):
            page_size = self.default_page_size

        page = max(page, 1)
        page_size = max(1, min(page_size, self.max_page_size))
        return page, page_size

    def paginate(self) -> Tuple[List[Any], Dict[str, Any]]:
        page, page_size = self._get_page_params()
        total_pages: int
        windowed = _paginate_with_window_aggregate(self.queryset, page, page_size)
        if windowed is not None:
            items, total = windowed
            total_pages = ceil(total / page_size) if total else 1
        else:
            total = self.queryset.count()
            total_pages = ceil(total / page_size) if total else 1
            start = (page - 1) * page_size
            end = start + page_size
            items = list(self.queryset[start:end])

        meta = {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        }
        return items, meta


def paginated_response(request: HttpRequest, queryset, serializer_class, many: bool = True):
    """
    Common helper for list APIs: paginate queryset and return DRF Response with
    { "results": [...], "meta": { page, page_size, total, total_pages, has_next, has_previous } }.
    """
    paginator = Paginator(request, queryset)
    items, meta = paginator.paginate()
    serializer = serializer_class(items, many=many)
    return Response({"results": serializer.data, "meta": meta})

